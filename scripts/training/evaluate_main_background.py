"""Reload both independent networks and replay a locked development candidate.

Recomputes the eye branch instead of trusting cached predictions. Optional
batch-one timing covers transfer, both forwards, decoding and selection.
"""
import argparse
import time
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from bird_surface import read, write, digest, outside_git
from bird_parts_model import build_model, as_raw, decode
from bird_guidance_metrics import select_candidate
from train_main_background import measure


def load(path):
    model = build_model('n').cuda().eval()
    model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True)['state_dict'])
    return model


def pixels(row):
    with Image.open(row['path']) as im:
        v = np.asarray(im.convert('RGB')).transpose(2, 0, 1).copy()
    return torch.from_numpy(v).float()[None] / 256


def combined(box, eye, image):
    image = image.cuda()
    bh = decode(as_raw(box(image)), box.model[-1].stride)[0]
    ep = decode(as_raw(eye(image)), eye.model[-1].stride)[0]
    predictions = [p for p in bh if p['kind'] != 'eye'] + [p for p in ep if p['kind'] == 'eye']
    return select_candidate(predictions, .8, 'none', .4, .4)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'eyes', 'box', 'eye-parent', 'expected', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--reference-box', type=Path)
    p.add_argument('--benchmark-repeats', type=int, default=0)
    a = p.parse_args()
    out = outside_git(a.output)
    if out.is_relative_to(a.dataset.resolve().parent):
        p.error('Keep evaluation outside the frozen dataset')
    if not torch.cuda.is_available():
        p.error('CUDA required; no fallback')
    if a.benchmark_repeats and (not a.reference_box or a.benchmark_repeats < 100):
        p.error('Timing needs a reference box network and at least 100 repeats')
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    document, cached = read(a.dataset), read(a.eyes)
    if digest(a.eye_parent) != document['eye_parent_sha256'] or digest(a.eye_parent) != cached['parent_sha256']:
        raise ValueError('Eye network identity differs')
    ids = set(document['eval_ids'])
    rows = [r for r in document['records'] if r['image_id'] in ids]
    if len(rows) != len(ids) or set(cached['predictions']) != ids:
        raise ValueError('Evaluation IDs differ')
    if any(digest(r['path']) != cached['input_hashes'][r['image_id']] for r in rows):
        raise ValueError('Evaluation input changed')
    box, eye = load(a.box), load(a.eye_parent)
    fresh = {}
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
        for row in rows:
            predictions = decode(as_raw(eye(pixels(row).cuda())), eye.model[-1].stride)[0]
            fresh[row['image_id']] = [q for q in predictions if q['kind'] == 'eye']
    if fresh != cached['predictions']:
        raise RuntimeError('Actual fixed-eye predictions differ from cache')
    result = measure(box, document, fresh)
    if result != read(a.expected):
        raise RuntimeError('Reloaded candidate predictions differ from selected checkpoint')
    write(out / 'actual-replay.json', result)
    status = dict(status='passed', images=len(rows), all_predictions_equal=True,
                  actual_eye_forward_equal=True, box_sha256=digest(a.box),
                  eye_sha256=digest(a.eye_parent), dataset_sha256=digest(a.dataset),
                  old_test_used=False, camera_AF_verified=False)
    if a.benchmark_repeats:
        if digest(a.reference_box) != document['box_parent_sha256']:
            raise ValueError('Reference box identity differs')
        parent = load(a.reference_box)
        inputs = [pixels(r) for r in sorted(rows, key=lambda r: r['image_id'])
                  if r['source'] == 'community'][:8]
        samples = dict(parent=[], candidate=[])
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            for i in range(20):
                for model in (parent, box):
                    combined(model, eye, inputs[i % len(inputs)])
            torch.cuda.synchronize()
            for i in range(a.benchmark_repeats):
                arms = [('parent', parent), ('candidate', box)]
                if i % 2:
                    arms.reverse()
                for name, model in arms:
                    torch.cuda.synchronize(); start = time.perf_counter()
                    combined(model, eye, inputs[i % len(inputs)])
                    torch.cuda.synchronize()
                    samples[name].append((time.perf_counter() - start) * 1000)
        write(out / 'timing.json', dict(samples_ms=samples, summary={name: dict(
            p50_ms=float(np.percentile(v, 50)), p95_ms=float(np.percentile(v, 95)))
            for name, v in samples.items()}, repeats_per_arm=a.benchmark_repeats,
            scope='batch one: host-to-device, two forwards, both decoders and selection; image loading excluded',
            order='alternating arms; 20 warmup pairs; eight fixed community inputs',
            device=torch.cuda.get_device_name(), precision='float16 autocast',
            parameters_in_two_networks=sum(x.numel() for x in box.parameters()) + sum(x.numel() for x in eye.parameters())))
        status['timing_completed'] = True
    write(out / 'status.json', status)
    print(status, flush=True)


if __name__ == '__main__':
    main()
