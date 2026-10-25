#!/usr/bin/env python3
"""Export exactly the images a human reviewed and confirmed, with their labels.

This is not a "best images" ranking: every human-confirmed record is exported,
including ones where the frozen vendor boxes were already correct. Nothing is
scored, filtered by quality or ordered by interest, because the point is the
complete set of human-calibrated ground truth for the frozen 384 x 256 input.

Outputs, all inside the given directory:

* ``confirmed.jsonl``             - one record per confirmed image, labels intact
* ``confirmed.csv``               - flat index (id, split, verdict, part counts)
* ``summary.json``                - counts, part totals, per-split breakdown
* ``coco/confirmed.coco.json``    - one COCO file for the whole confirmed set
* ``yolo/<image_id>.txt``         - YOLO rows per image (class cx cy w h)
* ``yolo/classes.txt``            - class order

The set is 547 images today (545 with shapes plus 2 explicitly bird-free), of
which 12 were folded out of the annotation queue by the similarity grouping;
``in_queue`` records that so a consumer can decide, and nothing is silently
dropped.

Usage::

    python scripts/export_confirmed_labels.py \\
        --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \\
        --dedupe data/annotations-2026-10-25/dedupe-queue-v1.json \\
        --split data/annotations-2026-10-25/evaluation-split-v1.json \\
        --output data/annotations-2026-10-25/confirmed
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

WIDTH, HEIGHT = 384, 256
CATEGORIES = [{'id': 1, 'name': 'bird'}, {'id': 2, 'name': 'head'}, {'id': 3, 'name': 'eye'}]
CLASS_INDEX = {'bird': 0, 'head': 1, 'eye': 2}
EYE_BOX_PX = 12.0
SPLITS = ('train', 'val', 'test')


def eye_box(item):
    if item.get('box_xyxy'):
        return [float(v) for v in item['box_xyxy']]
    x, y = item['point_xy']
    half = EYE_BOX_PX / 2
    return [max(0.0, x - half), max(0.0, y - half),
            min(float(WIDTH), x + half), min(float(HEIGHT), y + half)]


def boxes(row):
    for item in row['items']:
        kind = item['kind']
        if kind not in CLASS_INDEX:
            continue
        box = eye_box(item) if kind == 'eye' else [float(v) for v in item['box_xyxy']]
        yield kind, item, box


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--dedupe', required=True, type=Path)
    parser.add_argument('--split', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    labels = []
    for line in args.labels.read_text(encoding='utf-8').splitlines():
        if line.strip():
            labels.append(json.loads(line))
    queue = {row['image_id']: row for row in
             json.loads(args.dedupe.read_text(encoding='utf-8'))['images']}
    split = {row['image_id']: row['split'] for row in
             json.loads(args.split.read_text(encoding='utf-8'))['images']}

    confirmed = [row for row in labels if row['review_status'] == 'confirmed']
    confirmed.sort(key=lambda row: row['image_id'])

    output = args.output.resolve()
    (output / 'coco').mkdir(parents=True, exist_ok=True)
    (output / 'yolo').mkdir(parents=True, exist_ok=True)

    records, coco_images, coco_annotations, annotation_id = [], [], [], 1
    part_totals = {name: 0 for name in CLASS_INDEX}
    per_split = {name: 0 for name in SPLITS}
    per_verdict = {}
    for row in confirmed:
        image_id = row['image_id']
        queue_row = queue.get(image_id, {})
        items = []
        for kind, item, box in boxes(row):
            x1, y1, x2, y2 = box
            items.append({'kind': kind, 'box_xyxy': [round(v, 3) for v in box],
                          'source': 'eye_center_boxed'
                          if kind == 'eye' and not item.get('box_xyxy') else 'human'})
            part_totals[kind] += 1
            coco_annotations.append({
                'id': annotation_id, 'image_id': image_id,
                'category_id': CLASS_INDEX[kind] + 1,
                'bbox': [round(x1, 3), round(y1, 3), round(x2 - x1, 3), round(y2 - y1, 3)],
                'area': round((x2 - x1) * (y2 - y1), 3), 'iscrowd': 0,
            })
            annotation_id += 1
        image_split = split.get(image_id)
        if image_split:
            per_split[image_split] += 1
        per_verdict[row['decision']] = per_verdict.get(row['decision'], 0) + 1

        (output / 'yolo' / (image_id + '.txt')).write_text(''.join(
            '%d %.6f %.6f %.6f %.6f\n' % (
                CLASS_INDEX[it['kind']],
                (it['box_xyxy'][0] + it['box_xyxy'][2]) / 2 / WIDTH,
                (it['box_xyxy'][1] + it['box_xyxy'][3]) / 2 / HEIGHT,
                (it['box_xyxy'][2] - it['box_xyxy'][0]) / WIDTH,
                (it['box_xyxy'][3] - it['box_xyxy'][1]) / HEIGHT)
            for it in items), encoding='utf-8')

        coco_images.append({
            'id': image_id, 'file_name': image_id + '.png',
            'width': WIDTH, 'height': HEIGHT,
            'input_chw_u8_sha256': row['annotation_image']['input_chw_u8_sha256'],
        })
        records.append({
            'image_id': image_id,
            'split': image_split,
            'in_queue': bool(queue_row.get('in_queue')),
            'dedupe_root': queue_row.get('dedupe_root'),
            'z8_verdict': row['decision'],
            'presence': row['presence'],
            'revision': row['revision'],
            'parts': row['parts'],
            'items': items,
            'frozen_z8_candidates': row['frozen_z8_candidates'],
            'annotation_image': row['annotation_image'],
            'label_provenance': 'Z8-assisted human review; confirmed by a human reviewer',
        })

    (output / 'confirmed.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n'
                for row in records), encoding='utf-8')

    with (output / 'confirmed.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['image_id', 'split', 'in_queue', 'z8_verdict', 'presence',
                         'bird', 'head', 'eye', 'frozen_candidates'])
        for row in records:
            writer.writerow([row['image_id'], row['split'] or '', row['in_queue'],
                             row['z8_verdict'], row['presence'], row['parts']['bird'],
                             row['parts']['head'], row['parts']['eye'],
                             sum(row['frozen_z8_candidates'].values())])

    (output / 'yolo' / 'classes.txt').write_text('bird\nhead\neye\n', encoding='utf-8')
    (output / 'coco' / 'confirmed.coco.json').write_text(json.dumps({
        'info': {'description': 'Human-confirmed Z8-assisted labels, frozen 384x256 input',
                 'date': '2026-10-25'},
        'licenses': [],
        'images': coco_images,
        'annotations': coco_annotations,
        'categories': CATEGORIES,
    }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    body = (output / 'confirmed.jsonl').read_bytes()
    summary = {
        'schema': 'forest-bird-af-confirmed-v1',
        'confirmed_images': len(records),
        'with_shapes': sum(1 for row in records if row['items']),
        'explicitly_no_bird': sum(1 for row in records if not row['items']
                                 and row['presence'] == 'absent'),
        'in_queue': sum(1 for row in records if row['in_queue']),
        'folded_by_similarity': sum(1 for row in records if not row['in_queue']),
        'z8_verdict': dict(sorted(per_verdict.items())),
        'parts': part_totals,
        'objects_in_coco': len(coco_annotations),
        'per_split': per_split,
        'confirmed_sha256': hashlib.sha256(body).hexdigest(),
        'omitted_in_database': 'draft and needs_adjudication records are not labels',
        'notes': [
            'This is the full human-confirmed set, not a quality ranking.',
            'Labels describe the frozen 384 x 256 input, not the original photo.',
            'Confirmed by a human after seeing the frozen vendor boxes: assisted '
            'review, not independent blind annotation.',
            'Eyes without a visible boundary are exported as 12 x 12 boxes flagged '
            'eye_center_boxed; that size is a container, not a measured eye.',
            '12 confirmed images are folded out of the annotation queue by the '
            'similarity grouping; in_queue keeps that visible instead of dropping them.',
        ],
    }
    (output / 'summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in
                      ('confirmed_images', 'with_shapes', 'explicitly_no_bird',
                       'in_queue', 'folded_by_similarity', 'parts', 'per_split',
                       'confirmed_sha256')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
