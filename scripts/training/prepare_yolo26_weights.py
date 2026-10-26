"""Create seeded, hash-locked B/H plus two-eye initialization snapshots.

Official open YOLO26 pose weights are obtained through Ultralytics. This is a
CPU preparation step, not vendor firmware extraction or GPU training.
"""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from ultralytics import YOLO
from ultralytics.nn.tasks import PoseModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261026)
    parser.add_argument('--size', choices=['n', 's', 'both'], default='both')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error('Initialization weights must remain outside public Git checkout')
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    manifest = dict(schema='yolo26-parts-initialization-v1', preparation_device='cpu', snapshots=[])
    sizes = ['n', 's'] if args.size == 'both' else [args.size]
    for size in sizes:
        seed = args.seed + (size == 's')
        source = args.output / f'yolo26{size}-pose.pt'
        pretrained = YOLO(str(source))
        torch.manual_seed(seed)
        model = PoseModel(f'yolo26{size}-pose.yaml', nc=2, data_kpt_shape=[2, 3], verbose=False)
        model.load(pretrained.model, verbose=True)
        target = args.output / f'{size}-initial-state.pt'
        torch.save(model.state_dict(), target)
        manifest['snapshots'].append(dict(size=size, seed=seed,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            initialization_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            note='build_model subsequently removes unused branches and zero-initializes cell-local eye outputs'))
    (args.output / 'initialization-lock.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
