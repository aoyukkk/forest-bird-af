"""Validation-only full/low-detail/high-detail crop diagnostic; frozen model."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch

from bird_parts_model import build_model, as_raw, decode
from bird_parts_regions import automatic_regions, context_region, tiles, render_region, map_predictions, merge_predictions
from train_bird_parts import metric_rows, selection_diagnostic, THRESHOLDS
from z8_training_targets import records_to_predictions, match_metrics


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--weights', type=Path, required=True)
    p.add_argument('--native-validation', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--batch-size', type=int, default=1)
    a = p.parse_args()
    if a.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        p.error('Outputs must be outside repository')
    a.output.mkdir(exist_ok=False, parents=True)
    rows = read(a.dataset)['records']
    if any(r['split'] != 'community_val' for r in rows):
        raise ValueError('Only frozen community validation is permitted')
    native = {k: [dict(p, score=p['score']/1000.) for p in records_to_predictions(v)]
              for k, v in read(a.native_validation)['records'].items()}
    torch.set_num_threads(4)
    payload = torch.load(a.weights, map_location='cpu', weights_only=True)
    model = build_model(payload['size']).cuda().eval()
    model.load_state_dict(payload['state_dict'])
    names = ['full', 'auto_low', 'auto_high', 'tiles_low', 'tiles_high', 'oracle_high', 'hybrid_guarded']
    predictions = {k: {} for k in names}
    timings, audits = [], []
    with torch.inference_mode():
        for index, row in enumerate(rows):
            started = time.perf_counter()
            raw = Path(row['reference_path']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['reference_sha256']:
                raise ValueError('Reference hash changed: '+row['image_id'])
            with Image.open(row['path']) as im:
                low = im.convert('RGB')
            with Image.open(row['reference_path']) as im:
                high = ImageOps.exif_transpose(im).convert('RGB')
            full_from_high = np.asarray(high.resize((384, 256), Image.Resampling.BILINEAR))
            pixel_diff = np.abs(full_from_high.astype(np.int16)-np.asarray(low).astype(np.int16))
            auto = automatic_regions(native[row['image_id']])
            birds = [o['box'] for o in row['objects'] if o['kind'] == 'bird']
            heads = [o['box'] for o in row['objects'] if o['kind'] == 'head']
            oracle = [context_region(b) for b in (birds or heads)[:2]]
            jobs = [('full', [0., 0., 384., 256.], low)]
            for name, regions, image in [('auto_low',auto,low),('auto_high',auto,high),
                                         ('tiles_low',tiles(),low),('tiles_high',tiles(),high),
                                         ('oracle_high',oracle,high)]:
                jobs.extend((name, region, render_region(image, region)) for region in regions)
            images = torch.from_numpy(np.stack([np.asarray(im).transpose(2,0,1) for _,_,im in jobs]).copy()).float().cuda()/256.
            torch.cuda.synchronize(); start = time.perf_counter()
            result = []
            with torch.autocast('cuda', dtype=torch.float16):
                for first in range(0,len(images),a.batch_size):
                    result.extend(decode(as_raw(model(images[first:first+a.batch_size])), model.model[-1].stride))
            torch.cuda.synchronize(); inference_time = time.perf_counter()-start
            gathered = {k: [] for k in names}
            for (name, region, _), out in zip(jobs, result):
                gathered[name].extend(map_predictions(out,region))
            for name in names[:-1]:
                predictions[name][row['image_id']] = merge_predictions(gathered[name])
            # A declared conservative selector hypothesis, not camera AF logic.
            # Body/head stay native; eyes need two-scale agreement and a native head.
            native_boxes = [p for p in native[row['image_id']] if p['kind'] in ('bird','head')]
            native_heads = [p['box_xyxy'] for p in native_boxes if p['kind']=='head' and p['score']>=.5]
            lo = [p for p in gathered['auto_low'] if p['kind']=='eye' and p['score']>=.8]
            eyes = []
            for point in gathered['auto_high']:
                if point['kind']!='eye' or point['score']<.8:
                    continue
                x,y=point['point_xy']
                if any(math.dist(point['point_xy'],q['point_xy'])<=2 for q in lo) and any(b[0]<=x<=b[2] and b[1]<=y<=b[3] for b in native_heads):
                    eyes.append(point)
            predictions['hybrid_guarded'][row['image_id']] = merge_predictions(native_boxes+eyes)
            timings.append(dict(image_id=row['image_id'],calls=len(jobs),model_decode_seconds=inference_time,
                                all_views_io_model_seconds=time.perf_counter()-started))
            audits.append(dict(image_id=row['image_id'],auto_regions=auto,
                               high_to_frozen_exact=bool(not pixel_diff.any()),
                               high_to_frozen_mean_abs=float(pixel_diff.mean()),reference_size=list(high.size)))
            if (index+1)%10 == 0:
                print(json.dumps(dict(images=index+1,total=len(rows))),flush=True)
    truth = metric_rows(rows)
    reports={}
    for name, pred in dict(native=native, **predictions).items():
        thresholds = dict(bird=.4,head=.5,eye=.6) if name=='native' else dict(bird=.6,head=.15,eye=.8)
        if name=='hybrid_guarded':thresholds=dict(bird=.4,head=.5,eye=.8)
        selected={k:[p for p in v if p['score']>=thresholds[p['kind']]] for k,v in pred.items()}
        m,detail=match_metrics(truth,selected)
        loose,_=match_metrics(truth,selected,box_iou=.3,eye_pixels=8)
        tight,_=match_metrics(truth,selected,eye_pixels=2)
        curve=[]
        for threshold in THRESHOLDS:
            q={k:[p for p in v if p['score']>=threshold] for k,v in pred.items()}
            metric,_=match_metrics(truth,q);curve.append(dict(threshold=threshold,metrics=metric))
        reports[name]=dict(metrics=m,loose_metrics=loose,eye_2px=tight['eye'],thresholds=thresholds,
                           selection_diagnostic=selection_diagnostic(truth,selected),threshold_curve=curve,
                           no_proposal=sum(not v for v in selected.values()),
                           candidate_coverage=dict(matched_images=sum(any(v['tp'] for v in d['parts'].values()) for d in detail),images=len(rows)))
    output=dict(reports=reports,reference_audit=audits,timing=timings,
                weights_sha256=hashlib.sha256(a.weights.read_bytes()).hexdigest(),
                validation_only=True,test_used=False,oracle_is_upper_bound=True,
                batch_size=a.batch_size,
                timing_scope='all views in one diagnostic loop; not independent variant latency or camera latency',
                limits=['high-detail labels remain mapped from assisted 384 input, not new high-resolution truth',
                        'hybrid is a conservative two-scale eye agreement hypothesis, not recovered camera control'])
    (a.output/'report.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    (a.output/'predictions.json').write_text(json.dumps(predictions),encoding='utf-8')
    print(json.dumps({k:v['metrics']['eye'] for k,v in reports.items()}),flush=True)


if __name__=='__main__':main()
