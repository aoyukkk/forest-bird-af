"""Local YOLO26 parts training with frozen community validation and no test use."""
import argparse
import copy
import hashlib
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, WeightedRandomSampler

from bird_parts_model import BirdDataset, BirdLoss, as_raw, build_model, collate, decode, distillation_loss
from z8_training_targets import match_metrics, center, iou

THRESHOLDS = (.05, .1, .15, .2, .25, .3, .4, .5, .6, .7, .8, .9, .95, .975, .99, .995)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


def metric_rows(rows):
    result = []
    for row in rows:
        items = [{'kind': obj['kind'], 'box_xyxy': obj['box'], 'point_xy': None} for obj in row['objects']]
        items += [{'kind': 'eye', 'point_xy': p, 'box_xyxy': None} for p in row['eyes']]
        result.append(dict(image_id=row['image_id'], leakage_group_id=row['group'],
                           document={'items': items, 'presence': 'absent' if row['absent'] else 'present',
                                     'known_absent_parts': ['eye'] if row['eye_complete'] and not row['eyes'] else []}))
    return result


def selection_diagnostic(truth, predictions):
    """Audit the proposed E>H>B rule where the selected part has actual labels.

    This is an offline selection hypothesis, not recovered vendor AF control.
    Missing parts never become known unavailable parts.
    """
    result = dict(assessed=0, matched=0, unmatched=0, unknown=0,
                  no_proposal=0, wrong_eye_over_available_head_or_body=0)
    for row in truth:
        doc = row['document']; items = doc['items']
        pred = predictions[row['image_id']]
        chosen = None
        for kind in ('eye', 'head', 'bird'):
            candidates = [p for p in pred if p['kind'] == kind]
            if candidates:
                chosen = max(candidates, key=lambda p: p['score']); break
        if chosen is None:
            result['no_proposal'] += 1; continue
        targets = [p for p in items if p['kind'] == chosen['kind']]
        if not targets and doc['presence'] != 'absent' and chosen['kind'] not in doc.get('known_absent_parts', []):
            result['unknown'] += 1; continue
        result['assessed'] += 1
        matched = any(math.dist(center(chosen), center(t)) <= 4 if chosen['kind'] == 'eye'
                      else iou(chosen['box_xyxy'], t['box_xyxy']) >= .5 for t in targets)
        result['matched' if matched else 'unmatched'] += 1
        if chosen['kind'] == 'eye' and not matched:
            fallback = any(p['kind'] in ('head', 'bird') and t['kind'] == p['kind'] and
                           iou(p['box_xyxy'], t['box_xyxy']) >= .5 for p in pred for t in items)
            result['wrong_eye_over_available_head_or_body'] += int(fallback)
    result['limits'] = 'selected labelled part only; no designated-subject/instance proof or confirmed missing-part availability'
    return result


@torch.no_grad()
def evaluate(model, rows, batch_size=16):
    model.eval()
    predictions = {}
    loader = DataLoader(BirdDataset(rows), batch_size=batch_size, shuffle=False, collate_fn=collate, num_workers=0)
    for images, samples in loader:
        images = images.cuda()
        with torch.autocast('cuda', dtype=torch.float16):
            raw = as_raw(model(images))
        for sample, prediction in zip(samples, decode(raw, model.model[-1].stride)):
            predictions[sample['image_id']] = prediction
    truth = metric_rows(rows)
    curve = []
    for threshold in THRESHOLDS:
        filtered = {k: [p for p in v if p['score'] >= threshold] for k, v in predictions.items()}
        metric, _ = match_metrics(truth, filtered)
        curve.append({'threshold': threshold, 'metrics': metric})
    selected = {}
    for kind in ('bird', 'head', 'eye'):
        best = max(curve, key=lambda p: (p['metrics'][kind]['f1'], p['threshold']))
        selected[kind] = best['threshold']
    filtered = {k: [p for p in v if p['score'] >= selected[p['kind']]] for k, v in predictions.items()}
    metric, detail = match_metrics(truth, filtered)
    loose, _ = match_metrics(truth, filtered, box_iou=.3, eye_pixels=8)
    strict_eye, _ = match_metrics(truth, filtered, eye_pixels=2)
    # Candidate coverage is a geometric diagnostic; no unlabelled fallback
    # visibility or lens success is inferred from it.
    applicable = [d for d in detail if any(v.get('labels', 0) for v in d['parts'].values())]
    covered = sum(any(v['tp'] for v in d['parts'].values()) for d in applicable)
    return dict(metrics=metric, loose_metrics=loose, eye_2px=strict_eye['eye'],
                thresholds=selected, threshold_curve=curve, predictions=predictions,
                selection_diagnostic=selection_diagnostic(truth, filtered),
                candidate_coverage={'matched_images': covered, 'applicable_images': len(applicable)},
                scope='validation only; conditional part precision; not complete AF or independently verified fallback')


def load_checkpoint(model, path):
    payload = torch.load(path, map_location='cpu', weights_only=True)
    model.load_state_dict(payload['state_dict'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pretrained', type=Path, required=True)
    parser.add_argument('--size', choices=['n', 's'], default='n')
    parser.add_argument('--epochs', type=int, default=40)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--public-limit', type=int, default=0)
    parser.add_argument('--community-repeat', type=float, default=0., help='Relative community sampling weight; 0 balances sources 50:50')
    parser.add_argument('--epoch-samples', type=int, default=4096)
    parser.add_argument('--augment', action='store_true')
    parser.add_argument('--scale-match', action='store_true', help='Match public bird size to community training objects')
    parser.add_argument('--teacher', type=Path)
    parser.add_argument('--teacher-threshold', type=float, default=.5)
    parser.add_argument('--initial', type=Path)
    parser.add_argument('--lr', type=float, default=.0008)
    parser.add_argument('--patience', type=int, default=12)
    parser.add_argument('--seed', type=int, default=20261026)
    parser.add_argument('--amp-scale', type=float, default=128.)
    args = parser.parse_args()
    if args.scale_match and not args.augment:
        parser.error('--scale-match requires --augment')
    out = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo) or out.is_relative_to(args.dataset.resolve().parent):
        parser.error('Weights and run artifacts must be outside public repository and frozen input dataset')
    if not torch.cuda.is_available():
        parser.error('CUDA required; no silent backend substitution')
    out.mkdir(parents=True, exist_ok=False)
    source_dir = out / 'executed-code'; source_dir.mkdir()
    for name in ('train_bird_parts.py', 'bird_parts_model.py', 'z8_training_targets.py'):
        shutil.copyfile(Path(__file__).with_name(name), source_dir / name)
    torch.set_num_threads(4)
    torch.manual_seed(args.seed); np.random.seed(args.seed); random.seed(args.seed)
    document = json.loads(args.dataset.read_text(encoding='utf-8'))
    community = [r for r in document['records'] if r['split'] == 'community_train']
    public = [r for r in document['records'] if r['split'] == 'public_train']
    random.Random(args.seed).shuffle(public)
    if args.public_limit:
        public = public[:args.public_limit]
    rows = public + community
    community_weight = args.community_repeat or len(public) / max(1, len(community))
    validation = [r for r in document['records'] if r['split'] == 'community_val']
    public_validation = [r for r in document['records'] if r['split'] == 'public_val'][:200]
    config = dict(vars(args), architecture='official YOLO26 pose backbone/neck, one2many B/H and custom independent 2-slot eye grid',
                  input='RGB 384x256 /256', loss='TAL boxes, masked class BCE, unordered eye focal+offset; reviewed-body frames add derived protected-background negatives; no RLE or end2end branch',
                  selection='per-part thresholds on same validation only, maximize macro F1; report precision/coverage separately',
                  datasets={'community_unique_train': len(community), 'public_train': len(public),
                            'epoch_samples': args.epoch_samples, 'community_sampling_weight': community_weight,
                            'community_val': len(validation), 'public_val_diagnostic': len(public_validation)},
                  dataset_sha256=hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                  torch=torch.__version__, test_used=False, camera_AF_verified=False,
                  weak_head_note='derived public head geometry; classification downweighted, box geometry remains weak-label assumption')
    write(out / 'config.json', {k: str(v) if isinstance(v, Path) else v for k, v in config.items()})
    model = build_model(args.size, args.pretrained / f'{args.size}-initial-state.pt').cuda()
    if args.initial:
        load_checkpoint(model, args.initial)
    config['trainable_parameters'] = sum(p.numel() for p in model.parameters() if p.requires_grad)
    config['total_parameters'] = sum(p.numel() for p in model.parameters())
    write(out / 'config.json', {k: str(v) if isinstance(v, Path) else v for k, v in config.items()})
    teacher = None
    if args.teacher:
        teacher = build_model('s', args.pretrained / 's-initial-state.pt').cuda()
        load_checkpoint(teacher, args.teacher)
        teacher.eval()
        for p in teacher.parameters():
            p.requires_grad_(False)
    # Teacher construction must not change the student's stochastic sequence.
    torch.manual_seed(args.seed); np.random.seed(args.seed); random.seed(args.seed)
    loss_fn = BirdLoss(model)
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=.0001)
    scaler = torch.amp.GradScaler('cuda', init_scale=args.amp_scale, growth_interval=10**9)
    scale_reference = None
    if args.scale_match:
        scale_reference = [max(obj['box'][2] - obj['box'][0], obj['box'][3] - obj['box'][1])
                           for row in community for obj in row['objects'] if obj['kind'] == 'bird']
        config['scale_reference'] = {'source': 'community train only', 'count': len(scale_reference),
                                     'quantiles': np.quantile(scale_reference, [.1, .5, .9]).tolist(),
                                     'public_scale_probability': .7, 'canvas': 'median-colour padding; synthetic, not generated context'}
        write(out / 'config.json', {k: str(v) if isinstance(v, Path) else v for k, v in config.items()})
    dataset = BirdDataset(rows, args.augment, scale_reference)
    sampler = WeightedRandomSampler([1.] * len(public) + [community_weight] * len(community),
                                    args.epoch_samples, replacement=True,
                                    generator=torch.Generator().manual_seed(args.seed))
    loader = DataLoader(dataset, batch_size=args.batch_size, sampler=sampler, collate_fn=collate, num_workers=0)
    best, best_epoch, no_gain = -1., 0, 0
    start = time.perf_counter()
    history, step_times = [], []
    parent_score = None
    if args.initial:
        parent = evaluate(model, validation, args.batch_size)
        parent_score = best = parent['metrics']['macro_f1']
        write(out / 'validation-parent.json', parent)
        write(out / 'validation-best.json', parent)
        torch.save({'state_dict': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                    'epoch': 0, 'size': args.size, 'seed': args.seed}, out / 'best.pt')
    write(out / 'status.json', {'status': 'running', 'epoch': 0})
    try:
        for epoch in range(1, args.epochs + 1):
            epoch_start = time.perf_counter(); model.train()
            rate = args.lr * (.1 + .9 * (1 + math.cos(math.pi * (epoch - 1) / args.epochs)) / 2)
            for group in optimizer.param_groups:
                group['lr'] = rate
            losses, stats, kd_matches = [], [], 0
            for step, (images, samples) in enumerate(loader):
                stamp = time.perf_counter(); images = images.cuda()
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda', dtype=torch.float16):
                    raw = as_raw(model(images))
                loss, components = loss_fn(raw, samples)
                if teacher is not None:
                    with torch.no_grad(), torch.autocast('cuda', dtype=torch.float16):
                        reference = as_raw(teacher(images))
                    guidance, matches = distillation_loss(raw, reference, samples, args.teacher_threshold)
                    loss = loss + guidance * .25; kd_matches += matches
                    components['distillation'] = float(guidance.detach())
                if not torch.isfinite(loss):
                    raise RuntimeError('Nonfinite loss')
                scaler.scale(loss).backward(); scaler.unscale_(optimizer)
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 10.)
                if not torch.isfinite(norm):
                    raise RuntimeError('Nonfinite gradient')
                scaler.step(optimizer); scaler.update()
                losses.append(float(loss.detach())); stats.append(components)
                step_times.append(time.perf_counter() - stamp)
                if (step + 1) % 50 == 0:
                    emit({'stage': 'train', 'epoch': epoch, 'step': step + 1, 'steps': len(loader), 'loss': losses[-1]})
            measured = evaluate(model, validation, args.batch_size)
            score = measured['metrics']['macro_f1']
            selected = score > best + 1e-8
            checkpoint = {'state_dict': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                          'epoch': epoch, 'size': args.size, 'seed': args.seed}
            torch.save(checkpoint, out / 'last.pt')
            if selected:
                best, best_epoch, no_gain = score, epoch, 0
                torch.save(checkpoint, out / 'best.pt')
                write(out / 'validation-best.json', measured)
            else:
                no_gain += 1
            record = dict(epoch=epoch, loss=float(np.mean(losses)),
                          components={k: float(np.mean([s.get(k, 0) for s in stats])) for k in stats[0]},
                          macro_f1=score, val={k: measured['metrics'][k] for k in ('bird', 'head', 'eye')},
                          thresholds=measured['thresholds'], selected=selected, best_epoch=best_epoch,
                          teacher_correlated_points=kd_matches, seconds=time.perf_counter() - epoch_start)
            history.append(record); write(out / 'history.json', history)
            write(out / 'status.json', {'status': 'running', 'epoch': epoch, 'best_epoch': best_epoch})
            emit(record)
            if no_gain >= args.patience:
                break
        load_checkpoint(model, out / 'best.pt')
        repeated = evaluate(model, validation, args.batch_size)
        write(out / 'validation-reloaded.json', repeated)
        stored = json.loads((out / 'validation-best.json').read_text(encoding='utf-8'))
        if repeated['metrics'] != stored['metrics']:
            raise RuntimeError('Reloaded checkpoint changed metrics')
        diagnostic = evaluate(model, public_validation, args.batch_size)
        write(out / 'public-validation-diagnostic.json', diagnostic)
        calibration = evaluate(model, community[:200], args.batch_size)
        write(out / 'train-calibration-200.json', calibration)
        # Measure clean single-image GPU latency with CUDA synchronization.
        pixels, _ = BirdDataset(validation)[0]; pixels = pixels[None].cuda()
        model.eval()
        with torch.no_grad():
            for _ in range(5):
                with torch.autocast('cuda', dtype=torch.float16):
                    model(pixels)
            times = []
            for _ in range(30):
                torch.cuda.synchronize(); stamp = time.perf_counter()
                with torch.autocast('cuda', dtype=torch.float16):
                    raw = as_raw(model(pixels))
                decode(raw, model.model[-1].stride)
                torch.cuda.synchronize(); times.append((time.perf_counter() - stamp) * 1000)
        result = dict(status='completed', best_epoch=best_epoch, epochs=len(history),
                      improved_over_parent=bool(parent_score is not None and best > parent_score),
                      validation_metrics=repeated['metrics'], validation_thresholds=repeated['thresholds'],
                      elapsed_seconds=time.perf_counter() - start,
                      optimizer_step_median_seconds=float(np.median(step_times)),
                      peak_cuda_allocated_MiB=torch.cuda.max_memory_allocated() / 2**20,
                      inference_ms={'p50': float(np.percentile(times, 50)), 'p95': float(np.percentile(times, 95)),
                                    'scope': 'GPU input already resident; model+custom decode; image load excluded'},
                      checkpoint_sha256=hashlib.sha256((out / 'best.pt').read_bytes()).hexdigest(),
                      original_test_evaluated=False, new_independent_test_available=False, camera_AF_verified=False)
        write(out / 'report.json', result); write(out / 'status.json', {'status': 'completed'})
        emit(result)
    except Exception as exc:
        write(out / 'status.json', {'status': 'failed', 'error': repr(exc)})
        raise


if __name__ == '__main__':
    main()
