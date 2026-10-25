"""Conservative positive-only label adapter for the native-head smoke test.

This is not a complete detector training target builder. Missing annotations
never become negatives; unresolved native slots and eye direction stay unknown.
"""
import math
import struct
from pathlib import Path

import torch
import torch.nn.functional as F


def numbers(value, n):
    return isinstance(value, list) and len(value) == n and all(type(x) in (float, int) and math.isfinite(x) for x in value)


def box(value):
    if not numbers(value, 4) or not (0 <= value[0] < value[2] <= 384 and 0 <= value[1] < value[3] <= 256):
        raise ValueError('Target box must be finite and inside 384x256')
    return value


def point(value):
    if not numbers(value, 2) or not (0 <= value[0] < 384 and 0 <= value[1] < 256):
        raise ValueError('Eye point must be finite and inside 384x256')
    return value


def adapt(document, allow_unreviewed=False):
    schema = document['schema_version']
    if schema == 'forest-bird-input-manual-v1':
        approved = document.get('annotation_status') == 'reviewed'
    elif schema == 'forest-bird-z8-correction-v1':
        approved = document.get('status') == 'confirmed'
    else:
        raise ValueError('Unsupported annotation schema')
    if not approved and not allow_unreviewed:
        raise ValueError('Unreviewed annotations are not accepted as training ground truth')
    result = {'schema_version': schema, 'image_id': document['image_id'],
              'human_confirmed': approved, 'engineering_only': not approved,
              'positive_only': True, 'targets': [], 'ignored': [], 'warnings': []}

    def head(ident, bbox, instance):
        if bbox is not None:
            b = box(bbox)
            result['targets'].append({'source_id': ident, 'instance_id': instance, 'kind': 'head',
                                      'box_xyxy': b, 'point_xy': None, 'class_slots': [1]})

    def eye(ident, center, bbox, instance):
        if bbox is not None:
            box(bbox)
        if center is None:
            if bbox is None:
                raise ValueError('An eye requires actual geometry')
            center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
        result['targets'].append({'source_id': ident, 'instance_id': instance, 'kind': 'eye',
                                  'box_xyxy': bbox, 'point_xy': point(center), 'class_slots': [2, 3]})

    if schema == 'forest-bird-input-manual-v1':
        for bird in document.get('instances') or []:
            ident = bird['instance_id']
            if bird.get('bird_bbox_xyxy') is not None:
                box(bird['bird_bbox_xyxy'])
                result['ignored'].append({'source_id': ident, 'reason': 'whole-bird boundary is not a verified native slot 0/4/5 target'})
            head(ident + '/head', bird.get('head_bbox_xyxy'), ident)
            for e in bird.get('eyes') or []:
                eye(ident + '/' + e['eye_id'], e['center_xy'], e.get('bbox_xyxy'), ident)
    else:
        for item in document.get('items') or []:
            kind, ident = item['kind'], item['id']
            if kind == 'head':
                head(ident, item['box_xyxy'], None)
            elif kind == 'eye':
                eye(ident, item['point_xy'], item['box_xyxy'], None)
            else:
                result['ignored'].append({'source_id': ident, 'reason': 'unresolved native bird subtype, auxiliary boundary, or uncertainty'})
        result['warnings'].append('This correction schema has no bird-instance associations; do not use it to evaluate multi-bird AF association.')
    result['warnings'] += ['Eye slots 2/3 remain an unresolved pair; no hard directional class target.',
                           'No background negatives, no invented eye size, no supervision for unknown native slots.']
    return result


def native_tables(upstream):
    import json
    root = Path(upstream); manifest = json.loads((root / 'manifest.json').read_text())
    ipu = bytearray(0x80000)
    for row in manifest['consumer_tables']:
        raw = (root / row['file']).read_bytes()
        ipu[row['offset']:row['offset'] + len(raw)] = raw
    entries = struct.unpack_from('<24H', ipu, 0x4ee48)
    anchors = list(zip(*[iter(struct.unpack_from('<10H', ipu, 0x665a2))] * 2))
    allowed = {}
    for global_anchor in range(5):
        token = global_anchor if global_anchor < 2 else 16 + global_anchor
        allowed[global_anchor] = [slot for slot in range(6) if (slot << 8) + token in entries]
    return {'anchors': anchors, 'allowed_slots': allowed, 'table_entries': list(entries)}


def assign(adapted, tables):
    result = []
    occupied = set()
    for target in adapted['targets']:
        bbox, center = target['box_xyxy'], target['point_xy']
        if center is None:
            center = [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]
        eligible = [i for i in range(5) if set(target['class_slots']).issubset(tables['allowed_slots'][i])]
        if not eligible:
            raise ValueError('No native anchor permits the target class')
        if bbox is None:
            # Point-only supervision uses the small-eye anchor without making
            # a bounding-box target from its size.
            order = sorted(eligible, key=lambda i: tables['anchors'][i][0] * tables['anchors'][i][1])
        else:
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            def mismatch(i):
                aw, ah = tables['anchors'][i]
                return abs(math.log(w / aw)) + abs(math.log(h / ah))
            order = sorted(eligible, key=mismatch)
        for a in order:
            name, local, width, height = ('fine', a, 24, 16) if a < 2 else ('coarse', a - 2, 12, 8)
            gx, gy = center[0] / 384 * width, center[1] / 256 * height
            col, row = min(width - 1, int(gx)), min(height - 1, int(gy))
            key = name, local, row, col
            if key not in occupied:
                occupied.add(key)
                break
        else:
            raise ValueError('Positive anchor collision; no silent target overwrite')
        aw, ah = tables['anchors'][a]
        target_wh = None if bbox is None else [math.log((bbox[2] - bbox[0]) / aw), math.log((bbox[3] - bbox[1]) / ah)]
        result.append({**target, 'head': name, 'anchor': local, 'native_anchor': a, 'row': row, 'col': col,
                       'target_xy': [gx - col, gy - row], 'target_log_wh': target_wh,
                       'supervised_fields': ['x', 'y'] + (['w', 'h'] if bbox is not None else []) + (['objectness', 'class_1'] if target['kind'] == 'head' else [])})
    return result


def loss_for(outputs, targets):
    losses = []
    for t in targets:
        y = outputs[t['head']][0, t['anchor'] * 11:(t['anchor'] + 1) * 11, t['row'], t['col']]
        xy = torch.tensor(t['target_xy'], device=y.device)
        loss = F.mse_loss(torch.sigmoid(y[:2]), xy)
        if t['target_log_wh'] is not None:
            wh = torch.tensor(t['target_log_wh'], device=y.device)
            loss = loss + .25 * F.smooth_l1_loss(y[2:4], wh)
        if t['kind'] == 'head':
            # Only the positive known head class. Unlabelled cells/classes do
            # not receive negative gradients in this engineering smoke test.
            loss = loss + .02 * F.softplus(-y[4]) + .02 * F.softplus(-y[6])
        losses.append(loss)
    if not losses:
        raise ValueError('No supported positive targets; training must not start')
    return torch.stack(losses).mean()
