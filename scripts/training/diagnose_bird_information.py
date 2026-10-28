"""Frozen-input information/scale diagnostic. Oracle crops are never policies.

Only reused community development data and existing empty calibration are read.
All coordinates and metric tolerances are mapped to the original 384x256 plane.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import time
import numpy as np
from PIL import Image, ImageOps
import torch
from bird_parts_model import build_model, as_raw, decode
from bird_parts_regions import context_region, render_region, merge_predictions
from bird_guidance_metrics import select_candidate, assess_guidance
from bird_surface import read, write, digest, outside_git
from e7_backend import Backend
from z8_training_targets import records_to_predictions, iou

SUPPORTED = {'strict_eye_geometry', 'near_eye_geometry', 'head_region', 'bird_region'}
FULL = [0., 0., 384., 256.]


def transform(predictions, region=FULL, size=(384, 256)):
    """Map both native explicit centers and boxes, including non-eye centers."""
    x, y, right, bottom = region
    sx, sy = (right-x)/size[0], (bottom-y)/size[1]
    result = []
    for p in predictions:
        q = dict(p)
        if p.get('point_xy') is not None:
            a, b = p['point_xy']; q['point_xy'] = [x+a*sx, y+b*sy]
        if p.get('box_xyxy') is not None:
            a, b, c, d = p['box_xyxy']; q['box_xyxy'] = [x+a*sx, y+b*sy, x+c*sx, y+d*sy]
        result.append(q)
    return result


def proposal_regions(predictions):
    """Two B/H proposals at >=.1, body first; no label-dependent fallback."""
    proposals = [p for p in predictions if p['kind'] in ('bird', 'head') and p['score'] >= .1]
    proposals.sort(key=lambda p: (p['kind'] == 'bird', p['score']), reverse=True)
    regions = []
    for p in proposals:
        region = context_region(p['box_xyxy'])
        if not any(iou(region, r) > .7 for r in regions):
            regions.append(region)
        if len(regions) == 2:
            break
    return regions


def select(predictions, native=False):
    return select_candidate(predictions, .6 if native else .8, 'none', .4, .5 if native else .4)


def snapshot(files, database):
    result = dict(files={str(p): digest(p) for p in sorted(set(map(Path, files)))}, tables={})
    with sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro', uri=True) as con:
        con.execute('BEGIN')
        for table in ('images', 'z8_reviews', 'z8_review_history', 'annotations', 'history'):
            rows = con.execute('SELECT * FROM '+table).fetchall()
            encoded = sorted(json.dumps(r, ensure_ascii=False, default=str) for r in rows)
            result['tables'][table] = dict(count=len(rows), sha256=hashlib.sha256('\n'.join(encoded).encode()).hexdigest())
    return result


def paired(rows, parent, candidate):
    a = {r['image_id']: r for r in parent['detail']}
    b = {r['image_id']: r for r in candidate['detail']}
    gain, loss = [], []
    groups = {}
    for row in rows:
        key = row['image_id']; old, new = a[key]['category'] in SUPPORTED, b[key]['category'] in SUPPORTED
        if new and not old: gain.append(key)
        if old and not new: loss.append(key)
        groups.setdefault(row['group'], []).append(int(new)-int(old))
    return dict(gained=gain, lost=loss, group_mean_delta={k:sum(v)/len(v) for k,v in groups.items()},
                macro_group_delta=float(np.mean([sum(v)/len(v) for v in groups.values()])))


def choose_cases(rows, reference, count=48):
    detail = {r['image_id']: r for r in reference['detail']}
    chosen = [r['image_id'] for r in rows if detail[r['image_id']]['category'] not in SUPPORTED]
    ranked = sorted(rows, key=lambda r: (min([max(o['box'][2]-o['box'][0], o['box'][3]-o['box'][1]) for o in r['objects']] or [999]), r['image_id']))
    group_use = Counter(r['group'] for r in rows if r['image_id'] in chosen)
    remaining = [r for r in ranked if r['image_id'] not in chosen]
    while len(chosen) < min(count, len(rows)):
        item = min(remaining, key=lambda r: (group_use[r['group']], ranked.index(r)))
        chosen.append(item['image_id']); group_use[item['group']] += 1; remaining.remove(item)
    return chosen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('regions', 'dataset', 'box', 'eye', 'parent-evaluation', 'native-validation', 'upstream', 'database', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); out = outside_git(a.output); out.mkdir(parents=True, exist_ok=False)
    rows = read(a.regions)['records']; document = read(a.dataset)
    assert len(rows) == 80 and all(r['split'] == 'community_val' for r in rows)
    empty = [r for r in document['records'] if r['source'] == 'CCT' and r['split'] == 'public_val']
    assert len(empty) == 172
    previous = read(a.parent_evaluation)
    reference = assess_guidance(rows, {r['image_id']:previous['predictions'][r['image_id']] for r in rows}, head_threshold=.4)
    assert reference['counts']['geometry_supported'] == 68
    cases = choose_cases(rows, reference)
    files = [a.regions, a.dataset, a.box, a.eye, a.parent_evaluation, a.native_validation]
    files += [Path(r['path']) for r in rows+empty] + [Path(r['reference_path']) for r in rows]
    files += [a.upstream/'manifest.json', a.upstream/'resource744.body.bin']
    before = snapshot(files, a.database); write(out/'protected-before.json', before)
    plan = dict(status='frozen-before-new-predictions', cases=cases, community_ids=[r['image_id'] for r in rows],
                empty_ids=[r['image_id'] for r in empty], community_groups=len({r['group'] for r in rows}),
                variant_thresholds=dict(native=dict(eye=.6,head=.5,bird=.4),dual=dict(eye=.8,head=.4,bird=.4)),
                high_input=[768,512], high_eye_nms_pixels=8, normalized_metric_plane=[384,256],native_batch_size=8,
                oracle='all labelled body crops; head crops only if no body; no identity/original-resolution truth added',
                routes=['parent abstention -> high full frame', 'parent abstention -> up to two proposal crops'],
                selection='diagnostic only; no tuning on new predictions; preserve parent output whenever present',
                case_selection='all previous unsupported frames, then small-part/group-balanced fill; aggregate uses all 80',
                native_high_full='unsupported fixed graph; no fake 768 inference',
                new_independent_test_available=False, old_test_used=False, A12_labels=0)
    write(out/'plan.json', plan)
    (out/'executed-code').mkdir()
    for name in ('diagnose_bird_information.py','bird_parts_model.py','bird_parts_regions.py','bird_guidance_metrics.py','e7_backend.py'):
        shutil.copyfile(Path(__file__).with_name(name),out/'executed-code'/name)
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required; no fallback')
    torch.set_num_threads(4)
    models=[]
    for path in (a.box,a.eye):
        payload=torch.load(path,map_location='cpu',weights_only=True)
        model=build_model(payload['size']).cuda().eval();model.load_state_dict(payload['state_dict']);models.append(model)
    backend=Backend(a.upstream,'cuda')
    native_expected=read(a.native_validation)['records']
    variants={k:{} for k in ('dual_full','dual_upscaled_low','dual_high','dual_oracle_low','dual_oracle_high',
                              'dual_auto_low','dual_auto_high','native_full','native_oracle_low','native_oracle_high')}
    times=[]; audit=[]; native_jobs=[]; start=time.perf_counter()

    def dual(image, region=FULL):
        torch.cuda.synchronize(); started=time.perf_counter()
        value=torch.from_numpy(np.asarray(image).transpose(2,0,1).copy()).cuda().float()[None]/256.
        result=[]
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            for index,model in enumerate(models):
                raw=as_raw(model(value))
                predictions=decode(raw,model.model[-1].stride,input_size=image.size,eye_nms_radius=4*image.width/384)[0]
                result.extend(q for q in predictions if (q['kind']=='eye') == bool(index))
        torch.cuda.synchronize(); times.append(dict(backend='dual',size=list(image.size),ms=(time.perf_counter()-started)*1000))
        return transform(result,region,image.size)

    for i,row in enumerate(rows):
        key=row['image_id']
        if digest(row['reference_path']) != row['reference_sha256']:raise ValueError('Reference changed')
        with Image.open(row['path']) as im:low=im.convert('RGB')
        with Image.open(row['reference_path']) as im:high=ImageOps.exif_transpose(im).convert('RGB')
        assert np.array_equal(np.asarray(low),np.asarray(high.resize((384,256),Image.Resampling.BILINEAR)))
        full=dual(low);variants['dual_full'][key]=full
        if full!=previous['predictions'][key]:raise RuntimeError('Parent actual replay changed: '+key)
        variants['dual_upscaled_low'][key]=dual(low.resize((768,512),Image.Resampling.BILINEAR))
        variants['dual_high'][key]=dual(high.resize((768,512),Image.Resampling.BILINEAR))
        native_jobs.append((key,'native_full',FULL,low))
        objects=[o for o in row['objects'] if o['kind']=='bird'] or [o for o in row['objects'] if o['kind']=='head']
        oracle=[context_region(o['box']) for o in objects]; auto=proposal_regions(full)
        for prefix,regions in [('oracle',oracle),('auto',auto)]:
            for quality,image in [('low',low),('high',high)]:
                results=[]
                for region in regions:
                    view=render_region(image,region);results.extend(dual(view,region))
                    if prefix=='oracle':native_jobs.append((key,f'native_oracle_{quality}',region,view))
                variants[f'dual_{prefix}_{quality}'][key]=merge_predictions(results)
                if prefix=='oracle':variants[f'native_{prefix}_{quality}'][key]=[]
        audit.append(dict(image_id=key,reference_size=list(high.size),oracle_regions=oracle,auto_regions=auto,low_reconstruction_equal=True))
        if (i+1)%10==0: print(json.dumps(dict(stage='community',done=i+1,total=80,seconds=time.perf_counter()-start)),flush=True)
    write(out/'dual-community-checkpoint.json',{k:v for k,v in variants.items() if k.startswith('dual')})
    write(out/'reference-audit.json',audit)
    for first in range(0,len(native_jobs),8):
        jobs=native_jobs[first:first+8]
        torch.cuda.synchronize();started=time.perf_counter()
        result=backend.infer_many([np.asarray(im).transpose(2,0,1).copy().tobytes() for key,name,region,im in jobs])
        for j,(key,name,region,image) in enumerate(jobs):
            report,_=backend.decode({k:v[j] for k,v in result['heads'].items()})
            pred=[dict(q,score=q['score']/1000.) for q in records_to_predictions(report['records'])]
            if name=='native_full':
                if report['records']!=native_expected[key]:raise RuntimeError('Batched native replay changed: '+key)
                variants[name][key]=pred
            else:variants[name][key].extend(transform(pred,region))
        times.append(dict(backend='native-emulator-batch',views=len(jobs),ms=(time.perf_counter()-started)*1000))
        write(out/'native-progress.json',dict(done=min(first+8,len(native_jobs)),total=len(native_jobs),baseline_checks_completed=len(variants['native_full'])))
        print(json.dumps(dict(stage='native-batched',done=min(first+8,len(native_jobs)),total=len(native_jobs),seconds=time.perf_counter()-start)),flush=True)
    for name in ('native_oracle_low','native_oracle_high'):
        variants[name]={k:merge_predictions(v) for k,v in variants[name].items()}
    reports={}
    for name,pred in variants.items():
        report=assess_guidance(rows,pred,threshold=.6 if name.startswith('native') else .8,head_threshold=.5 if name.startswith('native') else .4)
        report['paired_vs_dual_parent']=paired(rows,reference,report);reports[name]=report
    policies={}
    for name,view in [('fallback_high','dual_high'),('fallback_auto_high','dual_auto_high')]:
        chosen={r['image_id']:select(variants['dual_full'][r['image_id']]) or select(variants[view][r['image_id']]) for r in rows}
        policies[name]=assess_guidance(rows,variants['dual_full'],selected_by_id=chosen)
        policies[name]['paired_vs_dual_parent']=paired(rows,reference,policies[name])
    write(out/'community-predictions.json',variants);write(out/'community-reports.json',dict(views=reports,policies=policies))
    write(out/'reference-audit.json',audit)
    empty_results={}
    # Empty calibration has only a frozen low input here: high is upsampling,
    # not a claim of original-resolution CCT evidence. Record that separately.
    for i,row in enumerate(empty):
        key=row['image_id']
        with Image.open(row['path']) as im:low=im.convert('RGB')
        full=dual(low)
        if full!=previous['predictions'][key]:raise RuntimeError('Empty parent replay differs')
        high=dual(low.resize((768,512),Image.Resampling.BILINEAR));auto=[]
        for region in proposal_regions(full):auto.extend(dual(render_region(low,region),region))
        auto=merge_predictions(auto)
        empty_results[key]=dict(parent=select(full),fallback_high=select(full) or select(high),
                               fallback_auto_high=select(full) or select(auto),
                               resolution_evidence='frozen low image only; upscale/crop stress control')
        if (i+1)%40==0:print(json.dumps(dict(stage='empty-low-control',done=i+1,total=172)),flush=True)
    write(out/'empty-controls.json',empty_results);write(out/'timings.json',times)
    after=snapshot(files,a.database);write(out/'protected-after.json',after)
    if after!=before:raise RuntimeError('Protected inputs or production tables changed')
    summary=dict(views={k:v['counts'] for k,v in reports.items()},
                 policies={k:dict(counts=v['counts'],paired=v['paired_vs_dual_parent']) for k,v in policies.items()},
                 empty_low_controls={k:sum(v[k] is not None for v in empty_results.values()) for k in ('parent','fallback_high','fallback_auto_high')},
                 native_replay_equal=80,dual_parent_replay_equal=252,protected_equal=True,
                 seconds=time.perf_counter()-start,cases=cases,new_independent_test_available=False,
                 original_resolution_empty_validation_complete=False)
    write(out/'summary.json',summary);write(out/'status.json',dict(status='completed'))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
