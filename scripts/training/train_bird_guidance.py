"""Matched parent continuations selected by explicit top-one guidance proxies."""
import argparse
import hashlib
import json
import math
import random
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from bird_parts_model import BirdDataset, BirdLoss, as_raw, build_model, collate
from bird_guidance_metrics import assess_guidance, guidance_rank, policy_curve
from train_bird_parts import evaluate


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


class CaptureBlurDataset(Dataset):
    """Mild whole-frame blur; affected eyes become unknown, never negatives.

    This is a cheap appearance augmentation, not a depth-aware defocus simulator.
    B/H boxes are inherited geometry. No visibility labels are invented.
    """
    def __init__(self, rows, probability=.35):
        self.base = BirdDataset(rows)
        self.probability = probability

    def __len__(self):
        return len(self.base)

    def __getitem__(self, index):
        pixels, sample = self.base[index]
        sample = dict(sample, capture_blur=False)
        if np.random.random() < self.probability:
            sigma = float(np.random.uniform(.45, 1.15))
            value = (pixels.numpy().transpose(1, 2, 0) * 256).astype(np.uint8)
            value = cv2.GaussianBlur(value, (0, 0), sigma)
            sample['uncertain'] = sample['uncertain'] + [[max(0, x - 8), max(0, y - 8),
                min(384, x + 8), min(256, y + 8)] for x, y in sample['eyes']]
            sample.update(eyes=[], eye_complete=False, capture_blur=True, blur_sigma=sigma)
            pixels = torch.from_numpy(value.transpose(2, 0, 1).copy()).float() / 256
        return pixels, sample


def mixed_predictions(predictions, native):
    return {key: [p for p in native[key] if p['kind'] in ('bird', 'head')] +
            [p for p in value if p['kind'] == 'eye'] for key, value in predictions.items()}


def eye_rank(counts, reference):
    r = reference['counts']
    return (int(counts['eye_unmatched_4px'] <= r['eye_unmatched_4px'] and
                counts['eye_unassessed_selected'] <= r['eye_unassessed_selected']),
            counts['eye_4px'], -counts['eye_unmatched_4px'], counts['eye_2px'])


def measure(model, rows, native, reference):
    # Fixed batch one prevents changing batch-shape arithmetic near thresholds.
    traditional = evaluate(model, rows, batch_size=1)
    combined = mixed_predictions(traditional['predictions'], native)
    selected, curve = policy_curve(rows, combined, reference)
    eye_policy = max(curve, key=lambda q: (eye_rank(q['counts'], reference), q['threshold']))
    eye_policy = assess_guidance(rows, combined, eye_policy['threshold'], eye_policy['gate'])
    return dict(traditional=traditional, guidance=selected, policy_curve=curve,
                rank=guidance_rank(selected, reference), eye_policy=eye_policy)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--initial', type=Path, required=True)
    p.add_argument('--native-validation', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--condition', choices=('control', 'quality', 'quality-blur'), required=True)
    p.add_argument('--epochs', type=int, default=18)
    p.add_argument('--patience', type=int, default=8)
    p.add_argument('--epoch-samples', type=int, default=4096)
    p.add_argument('--batch-size', type=int, default=32)
    p.add_argument('--lr', type=float, default=.0001)
    p.add_argument('--seed', type=int, default=20261026)
    a = p.parse_args()
    out = a.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo) or out.is_relative_to(a.dataset.resolve().parent):
        p.error('Keep run artifacts outside Git and frozen dataset')
    if not torch.cuda.is_available():
        p.error('CUDA required; no automatic fallback')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'checkpoints').mkdir()
    source = out / 'executed-code'
    source.mkdir()
    for name in ('train_bird_guidance.py', 'bird_parts_model.py', 'bird_guidance_metrics.py',
                 'train_bird_parts.py', 'z8_training_targets.py'):
        shutil.copyfile(Path(__file__).with_name(name), source / name)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()}
    config.update(dataset_sha256=hashlib.sha256(a.dataset.read_bytes()).hexdigest(),
                  initial_sha256=hashlib.sha256(a.initial.read_bytes()).hexdigest(),
                  selection='top-one guidance proxies, protect fixed-parent coverage/errors/unknown promotion',
                  quality_sigma_pixels=None if a.condition == 'control' else 2.,
                  torch=torch.__version__, test_used=False, camera_AF_verified=False)
    write(out / 'config.json', config)
    torch.set_num_threads(4)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    random.seed(a.seed)
    document = read(a.dataset)
    public = [r for r in document['records'] if r['split'] == 'public_train']
    community = [r for r in document['records'] if r['split'] == 'community_train']
    validation = [r for r in document['records'] if r['split'] == 'community_val']
    if not public or not community or len(validation) != 80:
        raise ValueError('Unexpected frozen dataset partitions')
    rows = public + community
    native, reference = read(a.native_validation), read(a.reference)
    if set(native) != {r['image_id'] for r in validation}:
        raise ValueError('Native validation IDs do not match')
    payload = torch.load(a.initial, map_location='cpu', weights_only=True)
    model = build_model('n').cuda()
    model.load_state_dict(payload['state_dict'])
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    random.seed(a.seed)
    dataset = CaptureBlurDataset(rows) if a.condition == 'quality-blur' else BirdDataset(rows)
    sampler = WeightedRandomSampler([1.] * len(public) + [len(public) / len(community)] * len(community),
        a.epoch_samples, replacement=True, generator=torch.Generator().manual_seed(a.seed))
    loader = DataLoader(dataset, batch_size=a.batch_size, sampler=sampler, num_workers=0, collate_fn=collate)
    loss_fn = BirdLoss(model, config['quality_sigma_pixels'])
    optimizer = torch.optim.AdamW([q for q in model.parameters() if q.requires_grad], lr=a.lr, weight_decay=.0001)
    scaler = torch.amp.GradScaler('cuda', init_scale=128., growth_interval=10**9)
    start = time.perf_counter()
    measured = measure(model, validation, native, reference)
    if measured['guidance']['counts'] != reference['counts']:
        # The selected policy may differ, but fixed parent predictions must replay.
        fixed = assess_guidance(validation, mixed_predictions(measured['traditional']['predictions'], native), .8)
        if fixed['counts'] != reference['counts']:
            raise RuntimeError('Parent replay changed fixed batch-one guidance counts')
    best_rank = tuple(measured['rank'])
    initial_rank = best_rank
    def eye_key(m):
        return eye_rank(m['eye_policy']['counts'], reference)
    best_eye, best_macro = eye_key(measured), measured['traditional']['metrics']['macro_f1']
    epochs_best = dict(guidance=0, eye=0, macro=0)
    write(out / 'validation-parent.json', measured)
    for name in ('guidance', 'eye', 'macro'):
        shutil.copyfile(a.initial, out / ('best-' + name + '.pt'))
        write(out / ('validation-best-' + name + '.json'), measured)
    write(out / 'status.json', dict(status='running', epoch=0))
    history, no_gain = [], 0
    try:
        for epoch in range(1, a.epochs + 1):
            stamp = time.perf_counter()
            model.train()
            rate = a.lr * (.1 + .9 * (1 + math.cos(math.pi * (epoch - 1) / a.epochs)) / 2)
            for group in optimizer.param_groups:
                group['lr'] = rate
            losses, components, order, blurred = [], [], hashlib.sha256(), 0
            for images, samples in loader:
                order.update(('\n'.join(s['image_id'] for s in samples) + '\n').encode())
                blurred += sum(s.get('capture_blur', False) for s in samples)
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda', dtype=torch.float16):
                    raw = as_raw(model(images.cuda()))
                loss, component = loss_fn(raw, samples)
                if not torch.isfinite(loss):
                    raise RuntimeError('Nonfinite loss')
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 10.)
                if not torch.isfinite(norm):
                    raise RuntimeError('Nonfinite gradient')
                scaler.step(optimizer)
                scaler.update()
                losses.append(float(loss.detach()))
                components.append(component)
            measured = measure(model, validation, native, reference)
            rank = tuple(measured['rank'])
            checkpoint = dict(state_dict={k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                              epoch=epoch, size='n', seed=a.seed, condition=a.condition)
            path = out / 'checkpoints' / f'epoch-{epoch:03d}.pt'
            torch.save(checkpoint, path)
            shutil.copyfile(path, out / 'last.pt')
            improved = rank > best_rank
            if improved:
                best_rank, no_gain = rank, 0
                epochs_best['guidance'] = epoch
                shutil.copyfile(path, out / 'best-guidance.pt')
                write(out / 'validation-best-guidance.json', measured)
            else:
                no_gain += 1
            if eye_key(measured) > best_eye:
                best_eye = eye_key(measured)
                epochs_best['eye'] = epoch
                shutil.copyfile(path, out / 'best-eye.pt')
                write(out / 'validation-best-eye.json', measured)
            if measured['traditional']['metrics']['macro_f1'] > best_macro:
                best_macro = measured['traditional']['metrics']['macro_f1']
                epochs_best['macro'] = epoch
                shutil.copyfile(path, out / 'best-macro.pt')
                write(out / 'validation-best-macro.json', measured)
            record = dict(epoch=epoch, loss=float(np.mean(losses)), lr=rate,
                          components={k: float(np.mean([c[k] for c in components])) for k in components[0]},
                          guidance=measured['guidance'], rank=rank, selected=improved,
                          thresholds=measured['traditional']['thresholds'],
                          traditional=measured['traditional']['metrics'],
                          sample_order_sha256=order.hexdigest(), blur_presentations=blurred,
                          seconds=time.perf_counter() - stamp)
            # Per-image detail and predictions stay in private validation files.
            record['guidance'] = {k: v for k, v in record['guidance'].items() if k != 'detail'}
            history.append(record)
            write(out / 'history.json', history)
            write(out / 'status.json', dict(status='running', epoch=epoch, best_epochs=epochs_best))
            print(json.dumps(record), flush=True)
            if no_gain >= a.patience:
                break
        payload = torch.load(out / 'best-guidance.pt', map_location='cpu', weights_only=True)
        model.load_state_dict(payload['state_dict'])
        repeated = measure(model, validation, native, reference)
        stored = read(out / 'validation-best-guidance.json')
        if (repeated['guidance']['counts'] != stored['guidance']['counts'] or
                tuple(repeated['rank']) != tuple(stored['rank'])):
            raise RuntimeError('Reloaded guidance checkpoint changed selected metrics')
        write(out / 'validation-reloaded.json', repeated)
        report = dict(status='completed', condition=a.condition, seed=a.seed, epochs=len(history),
                      best_epochs=epochs_best, rank=best_rank, parent_rank=initial_rank,
                      improved_over_parent=best_rank > initial_rank, guidance=repeated['guidance'],
                      elapsed_seconds=time.perf_counter() - start,
                      peak_cuda_allocated_MiB=torch.cuda.max_memory_allocated() / 2**20,
                      checkpoint_sha256=hashlib.sha256((out / 'best-guidance.pt').read_bytes()).hexdigest(),
                      test_used=False, new_real_event_data_available=False, camera_AF_verified=False)
        write(out / 'report.json', report)
        write(out / 'status.json', dict(status='completed'))
        print(json.dumps({k: v for k, v in report.items() if k != 'guidance'}), flush=True)
    except Exception as error:
        write(out / 'status.json', dict(status='failed', error=repr(error)))
        raise


if __name__ == '__main__':
    main()
