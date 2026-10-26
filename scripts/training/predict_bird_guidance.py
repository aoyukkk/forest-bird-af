"""Independent one/two-model B/H + eye guidance experiment, without vendor code."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch

from bird_parts_model import as_raw, build_model, decode
from bird_guidance_metrics import GATES, select_candidate


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--box-weights', type=Path, required=True)
    p.add_argument('--eye-weights', type=Path, required=True)
    p.add_argument('--calibration', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[2]):
        p.error('Predictions must stay outside public Git')
    if out.exists() or out in [q.resolve() for q in (a.image, a.box_weights, a.eye_weights, a.calibration)]:
        p.error('Preserve inputs and previous outputs')
    if not torch.cuda.is_available():
        p.error('CUDA required; no automatic backend substitution')
    calibration = json.loads(a.calibration.read_text(encoding='utf-8'))
    thresholds = calibration['thresholds']
    gate = calibration.get('eye_gate', 'none')
    if gate not in GATES or set(thresholds) != {'bird', 'head', 'eye'} or any(not 0 <= v <= 1 for v in thresholds.values()):
        p.error('Invalid calibration')
    hashes = {'box_weights_sha256': checksum(a.box_weights), 'eye_weights_sha256': checksum(a.eye_weights)}
    for key, value in hashes.items():
        if calibration.get(key) != value:
            p.error('Weights do not match calibration: ' + key)
    torch.set_num_threads(4)
    started = time.perf_counter()
    with Image.open(a.image) as source:
        source = ImageOps.exif_transpose(source).convert('RGB').resize((384, 256), Image.Resampling.BILINEAR)
    tensor = torch.from_numpy(np.asarray(source).transpose(2, 0, 1).copy()).float()[None].cuda() / 256
    cache = {}
    for path, sha in ((a.box_weights, hashes['box_weights_sha256']), (a.eye_weights, hashes['eye_weights_sha256'])):
        if sha in cache:
            continue
        payload = torch.load(path, map_location='cpu', weights_only=True)
        model = build_model(payload['size']).cuda().eval()
        model.load_state_dict(payload['state_dict'])
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            raw = as_raw(model(tensor))
        cache[sha] = decode(raw, model.model[-1].stride)[0]
    predictions = [q for q in cache[hashes['box_weights_sha256']] if q['kind'] in ('bird', 'head')]
    predictions += [q for q in cache[hashes['eye_weights_sha256']] if q['kind'] == 'eye']
    predictions = [q for q in predictions if q['score'] >= thresholds[q['kind']]]
    chosen = select_candidate(predictions, thresholds['eye'], gate, thresholds['bird'], thresholds['head'])
    torch.cuda.synchronize()
    result = dict(predictions=predictions, selected_candidate=chosen, thresholds=thresholds,
                  eye_gate=gate, **hashes, model_calls=len(cache), input_image_sha256=checksum(a.image),
                  output_role=calibration.get('output_role','part-candidate hypothesis'),
                  input='EXIF RGB bilinear-stretched 384x256 /256',
                  pipeline_wall_ms=(time.perf_counter() - started) * 1000,
                  timing_scope='one cold invocation including construction and image read; not camera latency',
                  camera_AF_verified=False, vendor_code_required=False,
                  limits=['selected position is an offline E/H/B hypothesis',
                          'no visible-surface, designated-bird, depth or temporal guarantee'])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(model_calls=len(cache), candidates=len(predictions), selected=chosen)))


if __name__ == '__main__':
    main()
