"""Run an exported custom B/H/eye checkpoint, without a vendor package."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
import torch

from bird_parts_model import as_raw, build_model, decode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--calibration', type=Path, required=True,
                        help='JSON containing validation-selected thresholds for bird/head/eye')
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error('Predictions must stay outside the public repository')
    if output in {args.weights.resolve(), args.calibration.resolve(), args.image.resolve()}:
        parser.error('Output must not overwrite an input')
    if output.exists():
        parser.error('Output exists; use a new path to preserve previous evidence')
    if args.device == 'cuda' and not torch.cuda.is_available():
        parser.error('CUDA requested but unavailable; choose --device cpu explicitly')
    thresholds = json.loads(args.calibration.read_text(encoding='utf-8'))['thresholds']
    if set(thresholds) != {'bird', 'head', 'eye'} or any(not 0 <= x <= 1 for x in thresholds.values()):
        parser.error('Expected bird/head/eye thresholds in [0,1]')
    torch.set_num_threads(4)
    payload = torch.load(args.weights, map_location='cpu', weights_only=True)
    model = build_model(payload['size'])
    model.load_state_dict(payload['state_dict'])
    model.to(args.device).eval()
    with Image.open(args.image) as source:
        source = ImageOps.exif_transpose(source).convert('RGB')
        source_size = source.size
        pixels = np.asarray(source.resize((384, 256), Image.Resampling.BILINEAR)).transpose(2, 0, 1).copy()
    value = torch.from_numpy(pixels.astype(np.float32)/256.)[None].to(args.device)
    with torch.inference_mode(), torch.autocast(args.device, dtype=torch.float16, enabled=args.device == 'cuda'):
        predictions = decode(as_raw(model(value)), model.model[-1].stride)[0]
    kept = [p for p in predictions if p['score'] >= thresholds[p['kind']]]
    report = dict(weights_sha256=hashlib.sha256(args.weights.read_bytes()).hexdigest(),
                  input_image_sha256=hashlib.sha256(args.image.read_bytes()).hexdigest(),
                  source_size=list(source_size), input_size=[384, 256],
                  preprocessing='EXIF orientation, RGB, bilinear stretch, CHW u8 /256',
                  coordinate_system='384x256 input pixels; no source-space remapping',
                  thresholds=thresholds, device=args.device, predictions=kept,
                  camera_AF_verified=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(output=str(output), candidates=len(kept), camera_AF_verified=False)))


if __name__ == '__main__':
    main()
