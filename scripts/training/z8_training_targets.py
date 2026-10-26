"""Partial-label targets and explicit offline metrics for native Z8 heads.

Bird slots 0/4 and eye slots 2/3 are operational unions from the review UI.
No subtype/direction claim is made. Auxiliary regions never become positives.
Unannotated parts are unknown, not hard background labels.
"""
import math
from collections import Counter

import numpy as np
import torch
import torch.nn.functional as F

SLOTS = {'bird': [0, 4], 'head': [1], 'eye': [2, 3]}


def iou(a, b):
    intersection = max(0., min(a[2], b[2]) - max(a[0], b[0])) * max(0., min(a[3], b[3]) - max(a[1], b[1]))
    aa = max(0., a[2] - a[0]) * max(0., a[3] - a[1])
    bb = max(0., b[2] - b[0]) * max(0., b[3] - b[1])
    return intersection / max(aa + bb - intersection, 1e-9)


def center(item):
    p = item.get('point_xy')
    b = item.get('box_xyxy')
    return p if p is not None else [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]


def target_builder(row, baseline, tables):
    doc = row['document']
    if doc['status'] != 'confirmed' or not doc.get('confirmed_by', {}).get('kind') == 'human':
        raise ValueError('Human-confirmed labels required')
    items = [i for i in doc['items'] if i['kind'] in SLOTS]
    # Allocate specific small parts first; each anchor/cell can have one target.
    items.sort(key=lambda t: ({'eye': 0, 'head': 1, 'bird': 2}[t['kind']], t['id']))
    result, occupied = [], set()
    for item in items:
        x, y = center(item)
        b = item.get('box_xyxy')
        if not (0 <= x < 384 and 0 <= y < 256):
            raise ValueError('Invalid visible-part center')
        choices = []
        for a, (aw, ah) in enumerate(tables['anchors']):
            allowed = sorted(set(SLOTS[item['kind']]) & set(tables['allowed_slots'][a]))
            if not allowed:
                continue
            name, local, w, h = ('fine', a, 24, 16) if a < 2 else ('coarse', a - 2, 12, 8)
            gx, gy = x / 384 * w, y / 256 * h
            col, r = min(w - 1, int(gx)), min(h - 1, int(gy))
            key = name, local, r, col
            if key in occupied:
                continue
            pred = baseline[name][0, local * 11:(local + 1) * 11, r, col]
            if b is not None:
                bw, bh = b[2] - b[0], b[3] - b[1]
                if bw <= 0 or bh <= 0:
                    raise ValueError('Invalid box extent')
                mismatch = abs(math.log(bw / aw)) + abs(math.log(bh / ah))
                wh = [math.log(bw / aw), math.log(bh / ah)]
            else:
                mismatch = math.log(aw * ah / 49) * .3
                wh = None
            # Native subclasses are not invented. Route the union to the
            # strongest original eligible logit at this location, then freeze
            # that latent choice for this run. Record it in the target audit.
            cls = max(allowed, key=lambda c: float(pred[5 + c]))
            # Prefer an already plausible native detection at the labelled
            # location. Size-only reassignment can create a second positive
            # anchor while teacher preservation keeps the original proposal.
            px = (float(pred[0].sigmoid()) + col) * 384 / w
            py = (float(pred[1].sigmoid()) + r) * 256 / h
            probability_gate = float(pred[4].sigmoid()) > .1 and float(pred[5 + cls].sigmoid()) > .1
            affinity = 0.
            if probability_gate:
                if b is not None:
                    pw = aw * math.exp(max(-20, min(10, float(pred[2]))))
                    ph = ah * math.exp(max(-20, min(10, float(pred[3]))))
                    affinity = iou([px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2], b)
                elif item['kind'] == 'eye':
                    affinity = max(0., 1 - math.dist([px, py], [x, y]) / 8)
            mismatch = .5 * mismatch - 4 * affinity
            choices.append((mismatch, name, local, a, r, col, gx - col, gy - r, wh, cls, allowed))
        if not choices:
            raise ValueError('Anchor collision with no free eligible location')
        _, name, local, a, r, col, tx, ty, wh, cls, allowed = min(choices)
        occupied.add((name, local, r, col))
        result.append(dict(source_id=item['id'], kind=item['kind'], head=name, anchor=local, native_anchor=a,
                           row=r, col=col, xy=[tx, ty], log_wh=wh, class_slot=cls, operational_union=allowed,
                           allowed_slots=tables['allowed_slots'][a]))
    return result


def negative_builder(row, baseline, tables, positives):
    """Use only explicitly removed, geometrically recoverable false proposals.

    Missing part labels alone never create negatives. A removed proposal near
    any retained same-part target is ignored, including a corrected box.
    """
    doc = row['document']
    unchanged = set(doc.get('diff', {}).get('unchanged_ids', []))
    occupied = {(t['head'], t['anchor'], t['row'], t['col'], t['class_slot']) for t in positives}
    result, seen = [], set()
    for n, old in enumerate(row['baseline']):
        if 'p' + str(n) in unchanged:
            continue
        slot = old['class_slot']
        kind = next((k for k, v in SLOTS.items() if slot in v), None)
        if kind is None:
            continue
        truth = [t for t in doc['items'] if t['kind'] == kind]
        if not truth and doc['presence'] != 'absent':
            continue
        b = old['box_input_xyxy']
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if any((math.dist([cx, cy], center(t)) <= 8 if kind == 'eye' else iou(b, t['box_xyxy']) > .05 or (t['box_xyxy'][0] <= cx <= t['box_xyxy'][2] and t['box_xyxy'][1] <= cy <= t['box_xyxy'][3])) for t in truth):
            continue
        choices = []
        for a, (aw, ah) in enumerate(tables['anchors']):
            if slot not in tables['allowed_slots'][a]:
                continue
            name, local, w, h = ('fine', a, 24, 16) if a < 2 else ('coarse', a - 2, 12, 8)
            raw = baseline[name][0, local * 11:(local + 1) * 11].float().numpy()
            px = (1 / (1 + np.exp(-np.clip(raw[0], -30, 30))) + np.arange(w)[None, :]) * 384 / w
            py = (1 / (1 + np.exp(-np.clip(raw[1], -30, 30))) + np.arange(h)[:, None]) * 256 / h
            pw, ph = aw * np.exp(np.clip(raw[2], -20, 10)), ah * np.exp(np.clip(raw[3], -20, 10))
            error = np.hypot(px - cx, py - cy) + 4 * np.abs(np.log(pw / max(b[2] - b[0], 1))) + 4 * np.abs(np.log(ph / max(b[3] - b[1], 1)))
            r, c = np.unravel_index(np.argmin(error), error.shape)
            if error[r, c] <= 5:
                choices.append((float(error[r, c]), name, local, int(r), int(c)))
        if choices:
            error, name, a, r, c = min(choices)
            key = name, a, r, c, slot
            if key not in occupied and key not in seen:
                seen.add(key)
                result.append(dict(source_id='p' + str(n), kind=kind, head=name, anchor=a, row=r, col=c, class_slot=slot, source_recovery_error=error))
    return result


def protected_eye_regions(row, margin=16.):
    """Derived, conservative coverage assumption; never a new human label.

    Only confirmed frames with a whole-bird box (or explicit absence) qualify.
    All current shapes protect their expanded region, including unknown and
    auxiliary shapes. Head/eye-only frames remain entirely unknown outside.
    """
    doc = row['document']
    if doc['status'] != 'confirmed' or doc.get('presence') not in ('present', 'absent') or doc.get('confirmed_by', {}).get('kind') != 'human':
        return None
    if doc['presence'] == 'absent':
        return []
    if not any(t['kind'] == 'bird' and t.get('box_xyxy') is not None for t in doc['items']):
        return None
    regions = []
    for item in doc['items']:
        b = item.get('box_xyxy')
        if b is None and item.get('point_xy') is not None:
            x, y = item['point_xy']
            b = [x, y, x, y]
        if b is not None:
            regions.append([max(0., b[0] - margin), max(0., b[1] - margin), min(384., b[2] + margin), min(256., b[3] + margin)])
    return regions


def background_eye_masks(row, margin=16.):
    regions = protected_eye_regions(row, margin)
    result = {}
    for name, anchors, w, h in [('fine', 2, 24, 16), ('coarse', 3, 12, 8)]:
        mask = torch.ones(anchors, h, w, dtype=torch.bool) if regions is not None else torch.zeros(anchors, h, w, dtype=torch.bool)
        if regions:
            # A negative cell's entire possible center range must be outside
            # every protected region; coordinate updates cannot invalidate it.
            for x1, y1, x2, y2 in regions:
                for r in range(h):
                    for c in range(w):
                        if c * 384 / w <= x2 and (c + 1) * 384 / w >= x1 and r * 256 / h <= y2 and (r + 1) * 256 / h >= y1:
                            mask[:, r, c] = False
        result[name] = mask
    return result


def regional_eye_errors(rows, records, margin=16.):
    errors, images = 0, 0
    for row in rows:
        regions = protected_eye_regions(row, margin)
        if regions is None:
            continue
        images += 1
        for x, y, _, _, _, slot in records[row['image_id']]:
            if slot in (2, 3) and not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in regions):
                errors += 1
    return {'derived_background_eye_candidates': errors, 'evaluated_images': images, 'margin_pixels': margin,
            'label_status': 'derived from coverage assumption, not separately human-labelled background'}


def local_eye_supervision(row):
    """Derived completeness assumption only within an explicitly labelled head.

    Exactly one head and one eye, point inside head, no uncertain shapes. Other
    birds/heads, missing eye labels, and the whole rest of the image stay unknown.
    """
    doc = row['document']
    if doc['status'] != 'confirmed' or doc['presence'] != 'present' or doc.get('confirmed_by', {}).get('kind') != 'human' or any(t['kind'] == 'uncertain' for t in doc['items']):
        return None
    heads = [t for t in doc['items'] if t['kind'] == 'head']
    eyes = [t for t in doc['items'] if t['kind'] == 'eye']
    if len(heads) != 1 or len(eyes) != 1:
        return None
    b, p = heads[0]['box_xyxy'], center(eyes[0])
    if b is None or not (b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]):
        return None
    return {'head_box': b, 'eye_point': p, 'derived_not_new_human_truth': True}


def head_local_negative_mask(raw, supervision, targets, name, radius=8.):
    # Selection is detached: only eye logits, not coordinates/objectness, get
    # a negative gradient. Positive assigned anchor/cells are always excluded.
    mask = torch.zeros_like(raw[:, 4], dtype=torch.bool)
    if supervision is None:
        return mask
    h, w = raw.shape[-2:]
    x = (raw[:, 0].detach().sigmoid() + torch.arange(w, device=raw.device)[None, None, :]) * 384 / w
    y = (raw[:, 1].detach().sigmoid() + torch.arange(h, device=raw.device)[None, :, None]) * 256 / h
    b, p = supervision['head_box'], supervision['eye_point']
    mask = (x > b[0]) & (x < b[2]) & (y > b[1]) & (y < b[3]) & ((x - p[0]).square() + (y - p[1]).square() > radius**2)
    for target in targets:
        if target['head'] == name and target['kind'] == 'eye':
            mask[target['anchor'], target['row'], target['col']] = False
    return mask


def partial_loss(outputs, samples, preservation=1., competition=0., background_weight=0., background_topk=16, head_local_weight=0., head_local_radius=8.):
    positive = []
    teacher = []
    absent = []
    explicit_false = []
    background = []
    local_negatives = []
    for n, sample in enumerate(samples):
        mask = {k: torch.ones_like(v[n], dtype=torch.bool) for k, v in outputs.items()}
        for target in sample['targets']:
            k, a, r, c = target['head'], target['anchor'], target['row'], target['col']
            start = a * 11
            pred = outputs[k][n, start:start + 11, r, c]
            xy = pred.new_tensor(target['xy'])
            loss = F.smooth_l1_loss(pred[:2].sigmoid(), xy) * 2
            mask[k][start:start + 2, r, c] = False
            if target['log_wh'] is not None:
                loss = loss + .25 * F.smooth_l1_loss(pred[2:4], pred.new_tensor(target['log_wh']))
                mask[k][start + 2:start + 4, r, c] = False
            cls = target['class_slot']
            # Positive-only class/objectness terms. No missing part is a
            # negative, and no opposite eye-direction label is synthesized.
            loss = loss + .15 * F.softplus(-pred[4]) + .15 * F.softplus(-pred[5 + cls])
            mask[k][start + 4, r, c] = False
            mask[k][start + 5 + cls, r, c] = False
            if competition:
                # One native anchor emits one selected semantic part. Compete
                # against other known part groups at a positive location only;
                # never split the unresolved same-part subtype/eye union and
                # never synthesize an auxiliary-class negative.
                competing = [c for c in target['allowed_slots'] if c != 5 and c not in SLOTS[target['kind']]]
                if competing:
                    loss = loss + competition * F.softplus(pred[[5 + c for c in competing]]).mean()
                    for competitor_slot in competing:
                        mask[k][start + 5 + competitor_slot, r, c] = False
            positive.append(loss)
        for target in sample.get('negative_targets', []):
            k, a, r, c, slot = target['head'], target['anchor'], target['row'], target['col'], target['class_slot']
            channel = a * 11 + 5 + slot
            explicit_false.append(F.softplus(outputs[k][n, channel, r, c]))
            mask[k][channel, r, c] = False
        for k, out in outputs.items():
            if background_weight:
                raw = out[n].reshape(-1, 11, *out.shape[-2:])
                eligible = sample['background_masks'][k].to(out.device)
                if eligible.any():
                    eye_logits = raw[:, 7:9].permute(0, 2, 3, 1)[eligible]
                    objectness = raw[:, 4][eligible].detach().sigmoid()
                    hardness = eye_logits.detach().sigmoid().amax(dim=1) * objectness
                    indices = torch.topk(hardness, min(background_topk, len(hardness))).indices
                    background.append(F.softplus(eye_logits[indices]).mean())
                    # Do not distil known false-region eye logits back toward
                    # the original model. Other classes/fields remain retained.
                    for a in range(len(raw)):
                        mask[k][a * 11 + 7][eligible[a]] = False
                        mask[k][a * 11 + 8][eligible[a]] = False
            if head_local_weight:
                raw = out[n].reshape(-1, 11, *out.shape[-2:])
                eligible = head_local_negative_mask(raw, sample.get('local_eye_supervision'), sample['targets'], k, head_local_radius)
                if eligible.any():
                    logits = raw[:, 7:9].permute(0, 2, 3, 1)[eligible]
                    hardness = logits.detach().sigmoid().amax(dim=1) * raw[:, 4][eligible].detach().sigmoid()
                    indices = torch.topk(hardness, min(background_topk, len(hardness))).indices
                    local_negatives.append(F.softplus(logits[indices]).mean())
                    for a in range(len(raw)):
                        mask[k][a * 11 + 7][eligible[a]] = False
                        mask[k][a * 11 + 8][eligible[a]] = False
            original = sample['heads'][k][0].to(out.device)
            # Preserve all unmodified outputs, including auxiliary and unknown
            # subclasses. Human-positive channels are excluded above.
            teacher.append(F.smooth_l1_loss(out[n][mask[k]], original[mask[k]]))
            if sample['document']['presence'] == 'absent':
                obj = out[n].reshape(-1, 11, *out.shape[-2:])[:, 4]
                absent.append(F.softplus(obj).mean())
    zero = next(iter(outputs.values())).sum() * 0
    pos = torch.stack(positive).mean() if positive else zero
    distill = torch.stack(teacher).mean()
    neg = torch.stack(absent).mean() if absent else zero
    false = torch.stack(explicit_false).mean() if explicit_false else zero
    bg = torch.stack(background).mean() if background else zero
    local = torch.stack(local_negatives).mean() if local_negatives else zero
    total = pos + preservation * distill + .15 * neg + .15 * false + background_weight * bg + head_local_weight * local
    return total, {'positive': float(pos.detach()), 'preservation': float(distill.detach()), 'explicit_absent': float(neg.detach()), 'explicit_false': float(false.detach()), 'derived_background': float(bg.detach()), 'derived_head_local': float(local.detach())}


def records_to_predictions(records):
    result = []
    for x, y, w, h, score, slot in records:
        kind = next((k for k, slots in SLOTS.items() if slot in slots), None)
        if kind is not None:
            result.append(dict(kind=kind, point_xy=[x, y], box_xyxy=[x - w / 2, y - h / 2, x + w / 2, y + h / 2], score=score, slot=slot))
    return result


def match_metrics(rows, prediction_by_id, box_iou=.5, eye_pixels=4.):
    counts = {k: Counter() for k in SLOTS}
    detail = []
    for row in rows:
        doc = row['document']
        predictions = prediction_by_id[row['image_id']]
        per_image = {}
        for kind in SLOTS:
            truth = [x for x in doc['items'] if x['kind'] == kind]
            # Partial annotation: precision is conditional on this part having
            # visible labels, or an explicitly confirmed no-bird frame.
            if not truth and doc['presence'] != 'absent' and kind not in doc.get('known_absent_parts', []):
                continue
            pred = [x for x in predictions if x['kind'] == kind]
            used = set()
            tp = 0
            for p in sorted(pred, key=lambda p: -p['score']):
                choices = []
                for j, t in enumerate(truth):
                    if j in used:
                        continue
                    quality = -math.dist(center(p), center(t)) if kind == 'eye' else iou(p['box_xyxy'], t['box_xyxy'])
                    if (quality >= -eye_pixels if kind == 'eye' else quality >= box_iou):
                        choices.append((quality, j))
                if choices:
                    _, j = max(choices)
                    used.add(j)
                    tp += 1
            values = dict(tp=tp, fp=len(pred) - tp, fn=len(truth) - tp, labels=len(truth), images=1)
            counts[kind].update(values)
            per_image[kind] = values
        detail.append({'image_id': row['image_id'], 'leakage_group_id': row['leakage_group_id'], 'parts': per_image})
    result = {}
    for kind, c in counts.items():
        precision = c['tp'] / max(1, c['tp'] + c['fp'])
        recall = c['tp'] / max(1, c['labels'])
        result[kind] = {**dict(c), 'precision': precision, 'recall': recall, 'f1': 2 * precision * recall / max(1e-12, precision + recall)}
    result['macro_f1'] = float(np.mean([result[k]['f1'] for k in SLOTS]))
    result['criteria'] = {'box_iou': box_iou, 'eye_distance_pixels': eye_pixels, 'precision_scope': 'part-labelled images, explicit no-bird frames and known-absent parts; unknown parts ignored', 'subclass_unions': SLOTS, 'not_camera_AF': True}
    return result, detail
