"""Check that batched CUDA execution preserves the physical fixture bits."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from e7_backend import Backend


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--upstream', required=True, type=Path)
    p.add_argument('--validation', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--batch-size', type=int, default=16)
    a = p.parse_args()
    if not json.loads(a.validation.read_text())['passed']:
        raise RuntimeError('Single-image validation must pass first')
    if a.output.exists():
        raise RuntimeError('Do not overwrite previous validation')
    inputs, expected = [], []
    for index in range(a.batch_size):
        name = ('stripe', 'random')[index % 2]
        root = a.upstream / 'fixtures' / name
        inputs.append((root / 'input-chw-u8.bin').read_bytes())
        expected.append(np.load(root / 'expected.npz'))
    model = Backend(a.upstream, 'cuda')
    start = time.perf_counter()
    got = model.infer_many(inputs, True)
    seconds = time.perf_counter() - start
    mask = np.load(a.upstream / 'fixtures/workspace-mask.npy')
    differences = []
    for i, want in enumerate(expected):
        row = {key: int(np.count_nonzero(got['heads'][key][i] != want[key])) for key in ('fine', 'coarse')}
        row['workspace'] = int(np.count_nonzero(got['workspace'][i][mask] != want['defined_workspace']))
        differences.append(row)
    report = {'passed': not any(any(row.values()) for row in differences),
              'batch_size': a.batch_size, 'seconds': seconds,
              'seconds_per_image': seconds / len(inputs),
              'max_gpu_memory_bytes': torch.cuda.max_memory_allocated(), 'differences': differences}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)
    if not report['passed']:
        raise RuntimeError('Batch validation failed; do not batch annotate')


if __name__ == '__main__':
    main()
