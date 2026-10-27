"""Matched resident-CUDA wall timings for primary-only and residual ranking."""
import argparse
import time
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from bird_surface import FrozenSurface, read, write, digest, outside_git
from bird_parts_model import build_model, as_raw, decode
from bird_guidance_metrics import select_candidate
from bird_residual import PointRanker, proposal_pool, patches, context_vectors


def statistics(values):
    return dict(samples=len(values), p50_ms=float(np.percentile(values, 50)),
                p95_ms=float(np.percentile(values, 95)), mean_ms=float(np.mean(values))) if values else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'parent', 'surface-head', 'box-parent', 'native-predictions',
                 'small', 'large', 'small-calibration', 'large-calibration', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--samples', type=int, default=500)
    args = parser.parse_args()
    output = outside_git(args.output)
    if output.exists() or args.samples < 500:
        parser.error('Use a new output and at least 500 samples')
    output.mkdir(parents=True)
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required; no backend fallback')
    base = FrozenSurface(args.parent).cuda().eval()
    base.head.load_state_dict(torch.load(args.surface_head, map_location='cpu', weights_only=True)['head_state_dict'])
    box = build_model('n').cuda().eval()
    box.load_state_dict(torch.load(args.box_parent, map_location='cpu', weights_only=True)['state_dict'])
    rankers, thresholds = {}, {}
    for name in ('small', 'large'):
        path = getattr(args, name)
        cal = read(getattr(args, name + '_calibration'))
        for key, source in [('parent_sha256', args.parent), ('surface_head_sha256', args.surface_head), ('ranker_sha256', path)]:
            if cal[key] != digest(source):
                raise ValueError('Calibration identity mismatch: ' + key)
        payload = torch.load(path, map_location='cpu', weights_only=True)
        ranker = PointRanker(payload['large']).cuda().eval()
        ranker.load_state_dict(payload['state_dict'])
        rankers[name], thresholds[name] = ranker, cal['threshold']
    rows = [r for r in read(args.dataset)['records'] if r['split'] == 'community_val']
    native = read(args.native_predictions)
    modes = [(policy + '_' + kind, two, kind) for policy, two in [('single', False), ('two_n', True)]
             for kind in ('base', 'small', 'large')]
    wall, trigger = {m[0]: [] for m in modes}, {m[0]: [] for m in modes}
    selections = {m[0]: {} for m in modes}
    with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
        for i in range(args.samples + 40):
            row = rows[i % len(rows)]
            # Rotate and reverse policy order to reduce order and thermal effects.
            order = modes[i % len(modes):] + modes[:i % len(modes)]
            if i % 2:
                order = list(reversed(order))
            for name, two, kind in order:
                torch.cuda.synchronize()
                start = time.perf_counter()
                with Image.open(row['path']) as image:
                    pixels = np.asarray(image.convert('RGB')).copy()
                value = torch.from_numpy(pixels.transpose(2, 0, 1).copy()).cuda().float()[None] / 256
                p2, p3, raw = base.encode(value)
                parts = decode(raw, base.base.model[-1].stride)[0]
                bh = [p for p in (decode(as_raw(box(value)), box.model[-1].stride)[0] if two else native[row['image_id']])
                      if p['kind'] in ('bird', 'head')]
                chosen = select_candidate(bh + [p for p in parts if p['kind'] == 'eye'], .8, 'none', .4, .4 if two else .5)
                fallback = chosen is None
                if fallback and kind != 'base':
                    pool = proposal_pool(parts, base.head(p2, p3))
                    rgb = torch.from_numpy(patches(pixels, [p['point_xy'] for p in pool])).cuda()
                    context = torch.from_numpy(context_vectors(p2, p3, pool)).cuda()
                    scores = rankers[kind](rgb, context).float().sigmoid().cpu().tolist() if pool else []
                    if scores:
                        index = int(np.argmax(scores))
                        if scores[index] >= thresholds[kind]:
                            chosen = dict(pool[index], score=scores[index], kind='capture_hint')
                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - start) * 1000
                if i >= 40:
                    wall[name].append(elapsed)
                    if fallback:
                        trigger[name].append(elapsed)
                    selections[name][row['image_id']] = chosen
            if (i + 1) % 100 == 0:
                print('matched repetitions', i + 1, flush=True)
    summary = dict(timings={name: statistics(v) for name, v in wall.items()},
                   on_primary_abstention={name: statistics(v) for name, v in trigger.items()},
                   trigger_counts={name: len(v) for name, v in trigger.items()},
                   gpu=torch.cuda.get_device_name(), precision='CUDA autocast float16', batch_size=1,
                   samples=args.samples, thresholds=thresholds,
                   limits=['hot PNG read, preprocess, resident models, decode and conditional ranking',
                           'single policy excludes native B/H compute; native predictions cached',
                           'all models resident for matched comparisons; not a deployment memory measurement',
                           'not camera NPU latency or achieved camera focus'])
    summary['p95_overhead'] = {policy + '_' + size: summary['timings'][policy + '_' + size]['p95_ms'] /
                               summary['timings'][policy + '_base']['p95_ms'] - 1
                               for policy in ('single', 'two_n') for size in ('small', 'large')}
    write(output / 'summary.json', summary)
    write(output / 'samples.json', dict(wall=wall, on_primary_abstention=trigger))
    write(output / 'selections.json', selections)
    print(summary, flush=True)


if __name__ == '__main__':
    main()
