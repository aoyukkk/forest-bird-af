"""Interleaved local emulator timing; not camera latency or hardware TOPS."""
import argparse
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from e7_backend import Backend, BODY_SHA
from z8_trainable_heads import apply_body_copy, head_events


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', required=True, type=Path)
    p.add_argument('--upstream', required=True, type=Path)
    p.add_argument('--body', required=True, type=Path)
    p.add_argument('--workspace', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    rows = [r for r in json.loads((a.dataset / 'dataset.json').read_text(encoding='utf-8'))['images'] if r['split'] == 'val'][::5]
    raws = []
    for row in rows:
        with Image.open(a.workspace / 'images' / (row['image_id'] + '.png')) as im:
            raw = np.asarray(im).transpose(2, 0, 1).copy().tobytes()
            if hashlib.sha256(raw).hexdigest() != row['metadata']['input_sha256']:
                raise ValueError('Input changed')
            raws.append(raw)
    backend = Backend(a.upstream, 'cuda')
    events = head_events(backend.model)
    original = [(e['weight'].clone(), e['bias'].clone() if e['bias'] is not None else None) for e in events]
    # Warm the same complete graph and memory sizes before paired measurement.
    backend.infer_many(raws)
    times = []
    report = {'scope': 'local CUDA native emulator, full forward including transfer back to CPU, batch throughput, not single-image latency or real-camera FPS',
              'gpu': torch.cuda.get_device_name(), 'torch': torch.__version__, 'batch_size': len(rows),
              'image_ids': [r['image_id'] for r in rows], 'warmup_batches': 1, 'runs': times}
    for round_number in range(3):
        for kind in (('original', 'candidate') if round_number % 2 == 0 else ('candidate', 'original')):
            if kind == 'candidate':
                apply_body_copy(backend, a.body)
            else:
                for event, (weight, bias) in zip(events, original):
                    event['weight'], event['bias'] = weight, bias
            torch.cuda.synchronize()
            started = time.perf_counter()
            heads = backend.infer_many(raws)['heads']
            torch.cuda.synchronize()
            cnn_seconds = time.perf_counter() - started
            started = time.perf_counter()
            for n in range(len(rows)):
                backend.decode({k: v[n] for k, v in heads.items()})
            post_seconds = time.perf_counter() - started
            record = dict(round=round_number + 1, model=kind, full_forward_batch_seconds=cnn_seconds,
                          forward_seconds_per_image_at_batch=cnn_seconds / len(rows), decoder_batch_seconds=post_seconds)
            times.append(record)
            a.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(record), flush=True)
    report['summary'] = {kind: {'mean_forward_batch_seconds': float(np.mean([r['full_forward_batch_seconds'] for r in times if r['model'] == kind])),
                             'mean_decoder_batch_seconds': float(np.mean([r['decoder_batch_seconds'] for r in times if r['model'] == kind]))} for kind in ('original', 'candidate')}
    report['candidate_to_original_forward_ratio'] = report['summary']['candidate']['mean_forward_batch_seconds'] / report['summary']['original']['mean_forward_batch_seconds']
    report['original_body_unchanged'] = hashlib.sha256((a.upstream / 'resource744.body.bin').read_bytes()).hexdigest() == BODY_SHA
    report['same_body_byte_length'] = a.body.stat().st_size == (a.upstream / 'resource744.body.bin').stat().st_size
    report['peak_cuda_allocated_mb'] = torch.cuda.max_memory_allocated() / 2**20
    a.output.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
