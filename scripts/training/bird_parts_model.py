"""YOLO26 pose-derived B/H detector and independent unordered eye-point grid.

Uses the official backbone, neck and one-to-many detection/pose branches.
Custom eye decoding is cell-local, independent of body availability. Unused
one-to-one/RLE branches are removed; this is not stock YOLO26 pose training.
"""
import itertools
import math
import random
from types import SimpleNamespace

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torch import nn
from torch.utils.data import Dataset

from ultralytics.nn.tasks import PoseModel
from ultralytics.utils.loss import v8DetectionLoss
from ultralytics.utils.tal import make_anchors


def build_model(size, initial=None):
    model = PoseModel(f'yolo26{size}-pose.yaml', nc=2, data_kpt_shape=[2, 3], verbose=False)
    if initial:
        model.load_state_dict(torch.load(initial, map_location='cpu', weights_only=True))
    head = model.model[-1]
    for attr in list(head._modules):
        if attr.startswith('one2one_'):
            setattr(head, attr, None)
    head.end2end = False
    head.flow_model = None
    for name, parameter in model.named_parameters():
        if 'cv4_sigma' in name:
            parameter.requires_grad_(False)
    with torch.no_grad():
        for layer in head.cv4_kpts:
            layer.weight.zero_()
            layer.bias.zero_()
            layer.bias[2::3] = -4.
    model.args = SimpleNamespace(box=7.5, cls=.5, dfl=1.5)
    return model


def as_raw(output):
    if isinstance(output, tuple):
        output = output[1]
    return output.get('one2many', output)


def grid_points(raw):
    """Two point hypotheses per stride-8 cell, no fabricated eye extents."""
    h, w = raw['feats'][0].shape[-2:]
    values = raw['kpts'][..., :h * w].reshape(-1, 2, 3, h, w).permute(0, 3, 4, 1, 2)
    return values


class BirdDataset(Dataset):
    def __init__(self, rows, augment=False, scale_reference=None):
        self.rows = rows
        self.augment = augment
        self.scale_reference = scale_reference

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(row['path']) as im:
            pixels = np.asarray(im.convert('RGB')).copy()
        objects = [dict(obj, box=list(obj['box'])) for obj in row['objects']]
        eyes = [list(p) for p in row['eyes']]
        regions = [list(b) for b in row['negative_regions']]
        uncertain = [list(b) for b in row['uncertain']]
        complete = row['eye_complete']
        scale_matched, target_size, applied_scale = False, None, 1.
        if self.augment:
            if np.random.random() < .5:
                pixels = pixels[:, ::-1].copy()
                for collection in (objects,):
                    for obj in collection:
                        a, b, c, d = obj['box']; obj['box'] = [384 - c, b, 384 - a, d]
                for boxes in (regions, uncertain):
                    for n, (a, b, c, d) in enumerate(boxes):
                        boxes[n] = [384 - c, b, 384 - a, d]
                eyes = [[384 - x, y] for x, y in eyes]
            match_public = self.scale_reference is not None and row['source'] != 'community'
            if np.random.random() < (.7 if match_public else .35):
                if match_public and any(obj['kind'] == 'bird' for obj in objects):
                    target_size = max(16., float(np.random.choice(self.scale_reference)))
                    original_size = max(max(obj['box'][2] - obj['box'][0], obj['box'][3] - obj['box'][1])
                                        for obj in objects if obj['kind'] == 'bird')
                    scale = max(.1, min(1., target_size / original_size))
                    scale_matched = True
                else:
                    scale = np.random.uniform(.65, .95)
                applied_scale = scale
                w, h = round(384 * scale), round(256 * scale)
                dx, dy = np.random.randint(385 - w), np.random.randint(257 - h)
                canvas = np.full_like(pixels, np.median(pixels.reshape(-1, 3), axis=0))
                canvas[dy:dy + h, dx:dx + w] = cv2.resize(pixels, (w, h), interpolation=cv2.INTER_AREA)
                pixels = canvas
                sx, sy = w / 384, h / 256
                for obj in objects:
                    a, b, c, d = obj['box']; obj['box'] = [a * sx + dx, b * sy + dy, c * sx + dx, d * sy + dy]
                for boxes in (regions, uncertain):
                    for n, (a, b, c, d) in enumerate(boxes):
                        boxes[n] = [a * sx + dx, b * sy + dy, c * sx + dx, d * sy + dy]
                eyes = [[x * sx + dx, y * sy + dy] for x, y in eyes]
            if np.random.random() < .25:
                sigma = np.random.uniform(.4, 1.15)
                pixels = cv2.GaussianBlur(pixels, (0, 0), sigma)
                heads = [o['box'] for o in objects if o['kind'] == 'head']
                if sigma > .9 and heads and min(min(b[2] - b[0], b[3] - b[1]) for b in heads) < 12:
                    eyes, complete = [], False  # unresolvable -> unknown, not invisible GT
            if np.random.random() < .2 and objects:
                box = random.choice(objects)['box']
                cx, cy = round((box[0] + box[2]) / 2), round((box[1] + box[3]) / 2)
                ax = max(1, round((box[2] - box[0]) * .09))
                ay = max(1, round((box[3] - box[1]) * .09))
                mask = np.zeros((256, 384), np.uint8)
                cv2.ellipse(mask, (cx, cy), (ax, ay), random.randrange(180), 0, 360, 1, -1)
                color = tuple(int(v) for v in pixels[random.randrange(256), random.randrange(384)])
                pixels[mask > 0] = color
                eyes = [p for p in eyes if not mask[min(255, max(0, int(p[1]))), min(383, max(0, int(p[0])))]]
                # These are controlled synthetic occluders, not verified real foliage.
        if self.augment:
            heads = [obj['box'] for obj in objects if obj['kind'] == 'head']
            if heads and min(min(b[2] - b[0], b[3] - b[1]) for b in heads) < 8:
                eyes, complete = [], False
            if scale_matched:
                objects = [obj for obj in objects if obj['kind'] != 'head' or
                           min(obj['box'][2] - obj['box'][0], obj['box'][3] - obj['box'][1]) >= 4]
        sample = dict(row, objects=objects, eyes=eyes, eye_complete=complete,
                      negative_regions=regions, uncertain=uncertain,
                      augmentation={'scale_matched': scale_matched, 'target_size': target_size,
                                    'scale_factor': applied_scale})
        return torch.from_numpy(pixels.transpose(2, 0, 1).copy()).float() / 256, sample


def collate(batch):
    return torch.stack([x for x, _ in batch]), [s for _, s in batch]


def regions_mask(regions, points):
    result = torch.zeros(points.shape[:-1], dtype=torch.bool, device=points.device)
    for x1, y1, x2, y2 in regions:
        result |= ((points[..., 0] >= x1) & (points[..., 0] < x2) &
                   (points[..., 1] >= y1) & (points[..., 1] < y2))
    return result


def derived_community_background(sample, points, margin=32.):
    """Conservative reviewed-frame background, never a new human truth label.

    A reviewed body is required. All existing boxes, points and uncertain
    regions are protected; head/eye-only frames supply no global negatives.
    Public focal-bird annotations do not enable this coverage assumption.
    """
    empty = torch.zeros(points.shape[:-1], dtype=torch.bool, device=points.device)
    if sample.get('source') != 'community' or not any(obj['kind'] == 'bird' for obj in sample['objects']):
        return empty
    regions = [obj['box'] for obj in sample['objects']] + sample['uncertain']
    regions += [[x, y, x, y] for x, y in sample['eyes']]
    protected = [[x1 - margin, y1 - margin, x2 + margin, y2 + margin] for x1, y1, x2, y2 in regions]
    return ~regions_mask(protected, points)


def classification_validity(samples, centers):
    valid = torch.zeros((len(samples), len(centers), 2), dtype=torch.bool, device=centers.device)
    for b, sample in enumerate(samples):
        region = regions_mask(sample['negative_regions'], centers)
        region &= ~regions_mask(sample['uncertain'], centers)
        background = derived_community_background(sample, centers)
        for kind, class_id in [('bird', 0), ('head', 1)]:
            known = any(obj['kind'] == kind for obj in sample['objects'])
            valid[b, :, class_id] = background | (region if known else False)
            if sample['absent']:
                valid[b, :, class_id] = True
    return valid


class MaskedClassification(nn.Module):
    def __init__(self):
        super().__init__()
        self.valid = None

    def forward(self, logits, target):
        valid = self.valid | (target > 0)
        return F.binary_cross_entropy_with_logits(logits.float(), target.float(), reduction='none') * valid


class BirdLoss:
    def __init__(self, model):
        self.det = v8DetectionLoss(model)
        self.det.bce = MaskedClassification()

    def __call__(self, raw, samples):
        # TAL/box arithmetic and partial-label losses use float32 under AMP.
        raw = {k: v.float() if torch.is_tensor(v) else v for k, v in raw.items()}
        device = raw['scores'].device
        anchors, strides = make_anchors(raw['feats'], self.det.stride, .5)
        centers = anchors * strides
        valid = classification_validity(samples, centers)
        idx, cls, boxes = [], [], []
        for b, sample in enumerate(samples):
            for obj in sample['objects']:
                x1, y1, x2, y2 = obj['box']
                if x2 <= x1 or y2 <= y1:
                    continue
                idx.append(b); cls.append(0 if obj['kind'] == 'bird' else 1)
                boxes.append([(x1 + x2) / 768, (y1 + y2) / 512, (x2 - x1) / 384, (y2 - y1) / 256])
        self.det.bce.valid = valid
        batch = dict(batch_idx=torch.tensor(idx, device=device),
                     cls=torch.tensor(cls, device=device).reshape(-1, 1),
                     bboxes=torch.tensor(boxes, device=device).reshape(-1, 4))
        # Weak public head supervision has a lower classification weight. Its
        # geometry remains a derived assumption and is reported separately.
        self.det.class_weights = torch.tensor(
            [[1., .35 if sample['head_labels_are_weak'] else 1.] for sample in samples],
            device=device).reshape(len(samples), 1, 2)
        det_loss, _ = self.det.loss(raw, batch)
        eye, components = eye_loss(grid_points(raw), samples)
        total = det_loss.sum() / len(samples) + eye
        components['detection'] = float(det_loss.detach().sum() / len(samples))
        return total, components


def eye_loss(values, samples):
    """Partial-label focal point loss with unordered two-slot assignment.

    Only public complete eye coverage supplies derived negatives inside the
    annotated bird region. Missing community eyes remain entirely unknown.
    """
    batch_size, h, w, _, _ = values.shape
    device = values.device
    ys, xs = torch.meshgrid(torch.arange(h, device=device), torch.arange(w, device=device), indexing='ij')
    centers = torch.stack(((xs + .5) * 8, (ys + .5) * 8), -1)
    target = torch.zeros(values.shape[:-1], device=device)
    known = torch.zeros_like(target, dtype=torch.bool)
    regressions = []
    overflow = 0
    for b, sample in enumerate(samples):
        if sample['absent']:
            known[b] = True
        elif sample['eye_complete']:
            known[b] = regions_mask(sample['negative_regions'], centers)[..., None]
            known[b] &= ~regions_mask(sample['uncertain'], centers)[..., None]
        known[b] |= derived_community_background(sample, centers, margin=20.)[..., None]
        cells = {}
        for x, y in sample['eyes']:
            if not (0 <= x < 384 and 0 <= y < 256):
                continue
            r, c = min(h - 1, int(y / 8)), min(w - 1, int(x / 8))
            cells.setdefault((r, c), []).append([x / 8 - c, y / 8 - r])
            # Neighbouring cells may contain the same eye; leave an ignore ring
            # instead of encouraging duplicate suppression at uncertain locations.
            known[b, max(0, r - 1):r + 2, max(0, c - 1):c + 2] = False
        for (r, c), points in cells.items():
            if len(points) > 2:
                overflow += len(points) - 2
            points = points[:2]
            truth = values.new_tensor(points)
            predicted = values[b, r, c, :, :2].sigmoid()
            routes = list(itertools.permutations(range(2), len(points)))
            best = min(routes, key=lambda route: float((predicted[list(route)].detach() - truth).square().sum()))
            for n, slot in enumerate(best):
                target[b, r, c, slot] = 1
                known[b, r, c, slot] = True
                regressions.append(F.smooth_l1_loss(predicted[slot], truth[n]))
    conf = values[..., 2]
    probabilities = conf.sigmoid()
    bce = F.binary_cross_entropy_with_logits(conf, target, reduction='none')
    pt = torch.where(target > 0, probabilities, 1 - probabilities)
    weights = torch.where(target > 0, 1., .25)
    classification = (bce * (1 - pt).square() * weights * known).sum() / target.sum().clamp(min=1)
    regression = torch.stack(regressions).mean() if regressions else values[..., :2].sum() * 0
    result = classification + regression * 4
    return result, {'eye_confidence': float(classification.detach()), 'eye_xy': float(regression.detach()), 'overflow': overflow}


def distillation_loss(student, teacher, samples, threshold=.5):
    """Positive teacher guidance only where existing human points corroborate it.

    No teacher miss becomes a negative and no contradictory eye is introduced.
    """
    s, t = grid_points(student).float(), grid_points(teacher).float().detach()
    # Slots have no left/right identity. Route both models through the same
    # human points, and permit each teacher slot/human point at most once.
    student_xy = s[..., :2].sigmoid().detach().cpu().numpy()
    teacher_xy = t[..., :2].sigmoid().cpu().numpy()
    teacher_probability = t[..., 2].sigmoid().cpu().numpy()
    selected_student, selected_teacher = [], []
    for b, sample in enumerate(samples):
        cells = {}
        for x, y in sample['eyes']:
            if not (0 <= x < s.shape[2] * 8 and 0 <= y < s.shape[1] * 8):
                continue
            r, c = int(y / 8), int(x / 8)
            cells.setdefault((r, c), []).append([x / 8 - c, y / 8 - r])
        for (r, c), points in cells.items():
            truth = np.asarray(points[:2], np.float32)
            routes = list(itertools.permutations(range(2), len(truth)))
            student_route = min(routes, key=lambda route: float(
                np.square(student_xy[b, r, c, list(route)] - truth).sum()))
            options = []
            for route in itertools.product((-1, 0, 1), repeat=len(truth)):
                assigned = [slot for slot in route if slot >= 0]
                if len(assigned) != len(set(assigned)):
                    continue
                distances, probabilities = [], []
                for index, slot in enumerate(route):
                    if slot < 0:
                        continue
                    distance = float(np.linalg.norm((teacher_xy[b, r, c, slot] - truth[index]) * 8))
                    probability = float(teacher_probability[b, r, c, slot])
                    if distance > 4 or probability < threshold:
                        break
                    distances.append(distance); probabilities.append(probability)
                else:
                    options.append(((-len(assigned), sum(distances), -sum(probabilities)), route))
            _, teacher_route = min(options, key=lambda choice: choice[0])
            for index, slot in enumerate(teacher_route):
                if slot >= 0:
                    selected_student.append(s[b, r, c, student_route[index]])
                    selected_teacher.append(t[b, r, c, slot])
    if not selected_student:
        return s.sum() * 0, 0
    a, b = torch.stack(selected_student), torch.stack(selected_teacher)
    loss = F.binary_cross_entropy_with_logits(a[:, 2], b[:, 2].sigmoid())
    loss += F.smooth_l1_loss(a[:, :2].sigmoid(), b[:, :2].sigmoid()) * 4
    return loss, len(selected_student)


def numpy_iou(a, b):
    intersection = max(0., min(a[2], b[2]) - max(a[0], b[0])) * max(0., min(a[3], b[3]) - max(a[1], b[1]))
    aa = max(0., a[2] - a[0]) * max(0., a[3] - a[1])
    bb = max(0., b[2] - b[0]) * max(0., b[3] - b[1])
    return intersection / max(1e-6, aa + bb - intersection)


def decode(raw, strides, floor=.05):
    anchors, stride = make_anchors(raw['feats'], strides, .5)
    from ultralytics.utils.tal import dist2bbox
    boxes = dist2bbox(raw['boxes'].permute(0, 2, 1).float(), anchors, xywh=False) * stride
    scores = raw['scores'].float().sigmoid().permute(0, 2, 1)
    points = grid_points(raw).float()
    h, w = points.shape[1:3]
    ys, xs = torch.meshgrid(torch.arange(h, device=points.device), torch.arange(w, device=points.device), indexing='ij')
    origin = torch.stack((xs, ys), -1)[None, :, :, None]
    coordinates = (points[..., :2].sigmoid() + origin) * 8
    result = []
    for b in range(len(boxes)):
        predictions = []
        for cls, kind in enumerate(('bird', 'head')):
            values, indices = torch.topk(scores[b, :, cls], min(100, len(anchors)))
            candidates = [(float(v), boxes[b, i].detach().cpu().tolist()) for v, i in zip(values, indices) if v >= floor]
            kept = []
            for score, box in candidates:
                box = [max(0., min(float(v), 384. if j % 2 == 0 else 256.)) for j, v in enumerate(box)]
                if any(numpy_iou(box, k['box_xyxy']) > .5 for k in kept):
                    continue
                kept.append(dict(kind=kind, score=score, box_xyxy=box, point_xy=None))
                if len(kept) >= 20:
                    break
            predictions.extend(kept)
        conf = points[b, ..., 2].sigmoid().reshape(-1)
        values, indices = torch.topk(conf, min(100, len(conf)))
        coords = coordinates[b].reshape(-1, 2)
        kept = []
        for value, idx in zip(values, indices):
            if value < floor:
                continue
            point = coords[idx].detach().cpu().tolist()
            if any(math.dist(point, old['point_xy']) <= 4 for old in kept):
                continue
            kept.append(dict(kind='eye', score=float(value), point_xy=point, box_xyxy=None))
            if len(kept) >= 20:
                break
        predictions.extend(kept)
        result.append(predictions)
    return result
