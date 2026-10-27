"""Fit B/H classification towers only, preserving fit-side positive cues."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
import torch
import torch.nn.functional as F
from ultralytics.utils.tal import make_anchors, dist2bbox
from bird_surface import read, write, digest, outside_git
from bird_parts_model import build_model, as_raw, BirdDataset, regions_mask
from bird_guidance_metrics import assess_guidance
from train_main_background import BoxOnlyLoss, measure, rank, grouped, choice


def freeze_except_classification(model):
    model.requires_grad_(False)
    model.model[-1].cv3.requires_grad_(True)
    model.eval()  # Autograd remains enabled; all BN and feature behavior stay fixed.
    return [p for p in model.parameters() if p.requires_grad]


def positive_guard(raw, teacher, samples, stride, hard_ids):
    anchors, scales = make_anchors(raw['feats'], stride, .5)
    boxes = dist2bbox(teacher['boxes'].permute(0, 2, 1).float(), anchors, xywh=False) * scales
    centers = (boxes[..., :2] + boxes[..., 2:]) / 2
    per_image, anchors_kept = [], 0
    for b, sample in enumerate(samples):
        if sample['source'] == 'CCT':
            continue
        terms = []
        for obj in sample['objects']:
            c = 0 if obj['kind'] == 'bird' else 1
            mask = regions_mask([obj['box']], centers[b])
            candidates = torch.where(mask & (teacher['scores'][b, c].float().sigmoid() >= .1))[0]
            if not candidates.numel():
                continue
            _, order = torch.topk(teacher['scores'][b, c, candidates], min(3, len(candidates)))
            indices = candidates[order]
            # Preserve a parent cue inside a labelled part; never pseudo-label other pixels.
            delta = teacher['scores'][b, c, indices].float() - raw['scores'][b, c, indices].float()
            terms.append(F.relu(delta).square().mean())
            anchors_kept += len(indices)
        if terms:
            weight = 2 if sample['image_id'] in hard_ids else 1
            per_image.append(torch.stack(terms).mean() * weight)
    value = torch.stack(per_image).mean() if per_image else raw['scores'].sum() * 0
    return value, anchors_kept


def batches(document, hard_ids, seed, epoch, count=96):
    rows = document['records']
    community = grouped([r for r in rows if r['split'] == 'community_train'])
    hard = grouped([r for r in rows if r['image_id'] in hard_ids])
    public = [[r for r in rows if r['source'] == s and r['split'] == 'public_train']
              for s in ('CUB-200-2011', 'NABirds', 'COCO-2017')]
    empty = grouped([r for r in rows if r['source'] == 'CCT' and r['split'] == 'public_train'])
    rng = np.random.default_rng(seed + epoch * 1000003)
    for _ in range(count):
        batch = []
        for j in range(16):
            u = rng.random(5)
            if j >= 12:
                r = choice(choice(empty, u[1]), u[2])
            elif j >= 8:
                r = choice(choice(hard, u[1]), u[2])
            elif u[0] < .7:
                r = choice(choice(community, u[1]), u[2])
            else:
                r = choice(choice(public, u[1]), u[2])
            batch.append(r)
        yield batch


def fit_document(document, excluded):
    fit_ids = {r['image_id'] for r in document['records'] if r['split'] == 'community_train'}
    if not set(excluded) <= fit_ids:
        raise ValueError('Only community fit IDs may be quarantined')
    return dict(document, records=[r for r in document['records'] if r['image_id'] not in excluded])


def support_ids(result, regions):
    report = assess_guidance(regions, {r['image_id']: result['predictions'][r['image_id']] for r in regions},
                             selected_by_id=result['community_selected'])
    kinds = {'strict_eye_geometry', 'near_eye_geometry', 'head_region', 'bird_region'}
    return {r['image_id'] for r in report['detail'] if r['category'] in kinds}


def guarded_rank(result, reference, regions):
    key = rank(result, reference)
    lost = support_ids(reference, regions) - support_ids(result, regions)
    return (int(bool(key[0]) and not lost), *key[1:]), sorted(lost)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dataset', 'eyes', 'hard', 'initial', 'eye-parent', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--condition', choices=('control', 'empty'), required=True)
    p.add_argument('--seed', type=int, default=20261028)
    p.add_argument('--epochs', type=int, default=8)
    p.add_argument('--batches', type=int, default=96)
    p.add_argument('--pilot-steps', type=int, default=0)
    a = p.parse_args(); out = outside_git(a.output)
    if out.is_relative_to(a.dataset.resolve().parent):
        p.error('Keep outputs outside the frozen dataset')
    if not torch.cuda.is_available():
        p.error('CUDA required; no fallback')
    out.mkdir(parents=True, exist_ok=False); (out/'checkpoints').mkdir(); (out/'executed-code').mkdir()
    for n in ('train_classification_guard.py', 'train_main_background.py', 'bird_parts_model.py', 'bird_guidance_metrics.py'):
        shutil.copyfile(Path(__file__).with_name(n), out/'executed-code'/n)
    torch.set_num_threads(4); torch.manual_seed(a.seed)
    document, eye_record, hard = read(a.dataset), read(a.eyes), read(a.hard)
    if hard['dataset_sha256'] != digest(a.dataset):
        raise ValueError('Hard replay dataset differs')
    hard_ids = set(hard['hard_ids']); fit_ids = {r['image_id'] for r in document['records'] if r['split'] == 'community_train'}
    if not hard_ids or not hard_ids <= fit_ids:
        raise ValueError('Hard replay must come from community fit only')
    fit = fit_document(document, hard.get('excluded_fit_ids', []))
    if hard_ids & set(hard.get('excluded_fit_ids', [])):
        raise ValueError('Quarantined frames cannot be hard replay')
    if document['box_parent_sha256'] != digest(a.initial) or document['eye_parent_sha256'] != digest(a.eye_parent) or eye_record['parent_sha256'] != digest(a.eye_parent):
        raise ValueError('Parent model identity differs')
    original = torch.load(a.initial, map_location='cpu', weights_only=True)['state_dict']
    model = build_model('n').cuda(); model.load_state_dict(original)
    trainable = freeze_except_classification(model)
    teacher = build_model('n').cuda().eval(); teacher.load_state_dict(original); teacher.requires_grad_(False)
    allowed = {n for n, q in model.named_parameters() if q.requires_grad}
    frozen = {k: v for k, v in original.items() if k not in allowed}
    optimizer = torch.optim.AdamW(trainable, lr=5e-6, weight_decay=1e-4)
    scaler = torch.amp.GradScaler('cuda', init_scale=128., growth_interval=10**9)
    criterion = BoxOnlyLoss(model, a.condition == 'empty')
    config = dict(condition=a.condition, seed=a.seed, epochs=a.epochs, batches_per_epoch=a.batches, batch=16,
        lr=5e-6, preservation_weight=2., hard_preservation_multiplier=2., empty_classification_weight=.1,
        ordinary_replay=8, hard_replay=4, empty_replay=4, allowed_parameter_names=sorted(allowed),
        trainable_parameters=sum(q.numel() for q in trainable), dataset_sha256=digest(a.dataset),
        hard_sha256=digest(a.hard), eyes_sha256=digest(a.eyes), initial_sha256=digest(a.initial),
        eye_parent_sha256=digest(a.eye_parent), no_augmentation=True, new_A12_labels=0)
    config.update(excluded_fit_ids=hard.get('excluded_fit_ids', []), eligible_community_fit=len(fit_ids)-len(hard.get('excluded_fit_ids', [])))
    write(out/'config.json', config)
    reference = None; best = None
    if not a.pilot_steps:
        reference = measure(model, document, eye_record['predictions'])
        if reference['community']['geometry_supported'] != 68 or reference['empty_selected'] != 60:
            raise RuntimeError('Parent replay differs')
        write(out/'validation-parent.json', reference); write(out/'validation-best.json', reference)
        shutil.copyfile(a.initial, out/'best.pt'); best, _ = guarded_rank(reference, reference, document['community_regions'])
    history = []; start = time.perf_counter()
    try:
        for epoch in range(1 if a.pilot_steps else a.epochs):
            model.eval(); losses = []; guards = []; anchors = 0; sources = Counter(); order = hashlib.sha256()
            for rows in batches(fit, hard_ids, a.seed, epoch, a.pilot_steps or a.batches):
                order.update(('\n'.join(r['image_id'] for r in rows)+'\n').encode()); sources.update(r['source'] for r in rows)
                examples = [BirdDataset([r])[0] for r in rows]
                images = torch.stack([x for x, s in examples]).cuda(); samples = [s for x, s in examples]
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda', dtype=torch.float16):
                    raw = as_raw(model(images))
                    with torch.no_grad(): frozen_raw = as_raw(teacher(images))
                if not torch.equal(raw['boxes'], frozen_raw['boxes']):
                    raise RuntimeError('Frozen raw box regression differs')
                detection = criterion(raw, samples)
                guard, count = positive_guard(raw, frozen_raw, samples, model.model[-1].stride, hard_ids)
                loss = detection + 2 * guard; anchors += count
                if not torch.isfinite(loss): raise RuntimeError('Nonfinite loss')
                scaler.scale(loss).backward(); scaler.unscale_(optimizer)
                if not torch.isfinite(torch.nn.utils.clip_grad_norm_(trainable, 10.)): raise RuntimeError('Nonfinite gradient')
                scaler.step(optimizer); scaler.update(); losses.append(float(loss.detach())); guards.append(float(guard.detach()))
            state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            if not all(torch.equal(state[k], v) for k, v in frozen.items()): raise RuntimeError('Frozen state changed')
            path = out/'checkpoints'/f'epoch-{epoch+1:03d}.pt'
            torch.save(dict(state_dict=state, size='n', epoch=epoch+1, condition=a.condition, seed=a.seed), path)
            saved = torch.load(path, map_location='cpu', weights_only=True)['state_dict']
            if not all(torch.equal(v, saved[k]) for k, v in state.items()): raise RuntimeError('Checkpoint readback differs')
            row = dict(epoch=epoch+1, loss=float(np.mean(losses)), positive_guard=float(np.mean(guards)),
                       preserved_anchor_presentations=anchors, sample_order_sha256=order.hexdigest(), presentations=dict(sources))
            if not a.pilot_steps and (epoch+1) % 2 == 0:
                result = measure(model, document, eye_record['predictions']); key, lost = guarded_rank(result, reference, document['community_regions'])
                write(out/f'validation-{epoch+1:03d}.json', result)
                row.update(community=result['community'], empty_selected=result['empty_selected'], rank=list(key), lost_parent_support=lost,
                           COCO_bird_box_TP=result['COCO_bird_box_TP'], COCO_bird_box_labels=result['COCO_bird_box_labels'])
                if key > best:
                    best = key; shutil.copyfile(path, out/'best.pt'); write(out/'validation-best.json', result)
            history.append(row); write(out/'history.json', history); print(json.dumps(row), flush=True)
        if digest(a.eye_parent) != config['eye_parent_sha256']: raise RuntimeError('Eye network changed')
        write(out/'status.json', dict(status='completed', epochs=len(history), seconds=time.perf_counter()-start,
            frozen_state_equal=True, raw_regression_equal=True, checkpoints_readback_equal=True,
            eye_parent_unchanged=True, peak_gpu_bytes=torch.cuda.max_memory_allocated()))
    except Exception as exc:
        write(out/'status.json', dict(status='failed', error=repr(exc), completed_epochs=len(history))); raise


if __name__ == '__main__':
    main()
