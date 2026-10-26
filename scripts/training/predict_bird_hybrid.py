"""Offline native bird/head candidates plus a custom n eye module; no camera AF."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image,ImageOps
import torch

from e7_backend import Backend
from bird_parts_model import build_model,as_raw,decode
from bird_parts_regions import tiles,render_region,map_predictions,combine_native_boxes_and_eyes
from z8_training_targets import records_to_predictions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--eye-weights',type=Path,required=True)
    p.add_argument('--calibration',type=Path,required=True)
    p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[2]) or out.is_relative_to(a.upstream.resolve()):p.error('Keep predictions outside Git and vendor package')
    if out.exists() or out in [a.image.resolve(),a.eye_weights.resolve(),a.calibration.resolve()]:p.error('Preserve existing inputs and outputs')
    config=json.loads(a.calibration.read_text(encoding='utf-8'))
    thresholds=config['thresholds'];views=config.get('eye_views','full')
    if set(thresholds)!={'bird','head','eye'} or any(not 0<=v<=1 for v in thresholds.values()):p.error('Invalid per-part thresholds')
    if views not in ('full','full-tiles'):p.error('Unknown eye-view policy')
    weight_sha=hashlib.sha256(a.eye_weights.read_bytes()).hexdigest()
    if config.get('eye_weights_sha256',weight_sha)!=weight_sha:p.error('Eye weights do not match calibration lock')
    if not torch.cuda.is_available():p.error('Validated CUDA path required; no implicit backend change')
    torch.set_num_threads(4)
    started=time.perf_counter()
    with Image.open(a.image) as im:im=ImageOps.exif_transpose(im).convert('RGB').resize((384,256),Image.Resampling.BILINEAR)
    pixels=np.asarray(im).transpose(2,0,1).copy()
    backend=Backend(a.upstream,'cuda')
    heads=backend.infer(pixels.tobytes())['heads'];native,_=backend.decode(heads)
    boxes=[p for p in records_to_predictions(native['records']) if p['kind'] in ('bird','head')]
    boxes=[dict(p,score=p['score']/1000.) for p in boxes]
    boxes=[p for p in boxes if p['score']>=thresholds[p['kind']]]
    payload=torch.load(a.eye_weights,map_location='cpu',weights_only=True)
    model=build_model(payload['size']).cuda().eval();model.load_state_dict(payload['state_dict'])
    regions=[[0.,0.,384.,256.]]+(tiles() if views=='full-tiles' else [])
    eyes=[]
    with torch.inference_mode():
        for region in regions:
            image=im if region==[0.,0.,384.,256.] else render_region(im,region)
            value=torch.from_numpy(np.asarray(image).transpose(2,0,1).copy()).float()[None].cuda()/256.
            with torch.autocast('cuda',dtype=torch.float16):raw=as_raw(model(value))
            eyes.extend(p for p in map_predictions(decode(raw,model.model[-1].stride)[0],region)
                        if p['kind']=='eye' and p['score']>=thresholds['eye'])
    proposals=combine_native_boxes_and_eyes(boxes,eyes)
    chosen=None
    for kind in ('eye','head','bird'):
        candidates=[q for q in proposals if q['kind']==kind]
        if candidates:chosen=max(candidates,key=lambda q:q['score']);break
    report=dict(predictions=proposals,selected_candidate=chosen,thresholds=thresholds,
                eye_weights_sha256=weight_sha,eye_views=views,eye_network_calls=len(regions),native_network_calls=1,
                input_image_sha256=hashlib.sha256(a.image.read_bytes()).hexdigest(),
                coordinate_system='384x256 EXIF RGB bilinear-stretched input pixels',
                body_head_from_native=True,eye_from_custom_model=True,camera_AF_verified=False,
                pipeline_wall_ms=(time.perf_counter()-started)*1000,
                timing_scope='one cold invocation including image read, model construction, native software replay and n eye calls; not camera latency',
                limitations=['eye-first selection is a hypothesis, not recovered vendor control',
                             'part availability, bird identity and temporal/lens control are not verified',
                             'native software emulator cost does not measure camera latency'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(candidates=len(proposals),eye_network_calls=len(regions),camera_AF_verified=False)))


if __name__=='__main__':main()
