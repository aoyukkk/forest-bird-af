#!/usr/bin/env python3
"""Export exactly the images a human reviewed and confirmed, with their labels.

This is not a "best images" ranking: every human-confirmed record is exported,
including ones where the frozen vendor boxes were already correct. Nothing is
scored, filtered by quality or ordered by interest, because the point is the
complete set of human-calibrated ground truth for the frozen 384 x 256 input.

Outputs, all inside the given directory:

* ``confirmed.jsonl``             - all source geometry including points/auxiliary
* ``confirmed.csv``               - flat index (id, split, verdict, part counts)
* ``summary.json``                - counts, part totals, per-split breakdown
* ``coco/confirmed.coco.json``    - measured boxes plus point_annotations extension
* ``yolo/<image_id>.txt``         - partial box view, not complete BHE targets
* ``yolo/classes.txt``            - class order
* ``yolo-labels.zip``             - deterministic boxes + point-only-eye sidecar

The set is 547 images today (545 with shapes plus 2 explicitly bird-free), of
which 12 were folded out of the annotation queue by the similarity grouping;
``in_queue`` records that so a consumer can decide, and nothing is silently
dropped.

Usage::

    python scripts/publish/export_confirmed_labels.py \\
        --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \\
        --dedupe data/annotations-2026-10-25/curation/dedupe-queue-v1.json \\
        --split data/annotations-2026-10-25/splits/evaluation-split-v1.json \\
        --output data/annotations-2026-10-25/confirmed
"""
import argparse
import csv
import hashlib
import json
import sys
import copy
import zipfile
from pathlib import Path

from export_label_formats import measured_boxes, to_coco, to_yolo

WIDTH, HEIGHT = 384, 256
CATEGORIES = [{'id': 1, 'name': 'bird'}, {'id': 2, 'name': 'head'}, {'id': 3, 'name': 'eye'}]
CLASS_INDEX = {'bird': 0, 'head': 1, 'eye': 2}
SPLITS = ('train', 'val', 'test')


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

    records, coco_images, coco_annotations, coco_points, annotation_id = [], [], [], [], 1
    yolo_files = {}
    eye_points = []
    part_totals = {name: 0 for name in CLASS_INDEX}
    per_split = {name: 0 for name in SPLITS}
    per_verdict = {}
    for row in confirmed:
        image_id = row['image_id']
        queue_row = queue.get(image_id, {})
        items = copy.deepcopy(row['items'])
        for kind in part_totals:
            part_totals[kind] += sum(i['kind'] == kind for i in items)
        converted = to_coco(row)
        for entry in converted['annotations']:
            entry['id'] = annotation_id
            annotation_id += 1
            coco_annotations.append(entry)
        for entry in converted['point_annotations']:
            entry['id'] = annotation_id
            annotation_id += 1
            coco_points.append(entry)
            eye_points.append({'image_id': image_id, 'item_id': entry['source_item_id'], 'point_xy': entry['point_xy']})
        image_split = split.get(image_id)
        if image_split:
            per_split[image_split] += 1
        per_verdict[row['decision']] = per_verdict.get(row['decision'], 0) + 1

        text = to_yolo(row)
        (output / 'yolo' / (image_id + '.txt')).write_text(text, encoding='utf-8', newline='\n')
        yolo_files['yolo/' + image_id + '.txt'] = text.encode('utf-8')

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
                for row in records), encoding='utf-8', newline='\n')

    with (output / 'confirmed.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(['image_id', 'split', 'in_queue', 'z8_verdict', 'presence',
                         'bird', 'head', 'eye', 'frozen_candidates'])
        for row in records:
            writer.writerow([row['image_id'], row['split'] or '', row['in_queue'],
                             row['z8_verdict'], row['presence'], row['parts']['bird'],
                             row['parts']['head'], row['parts']['eye'],
                             sum(row['frozen_z8_candidates'].values())])

    (output / 'yolo' / 'classes.txt').write_text('bird\nhead\neye\n', encoding='utf-8', newline='\n')
    yolo_files['yolo/classes.txt'] = b'bird\nhead\neye\n'
    yolo_files['eye-points.jsonl'] = ''.join(json.dumps(p, sort_keys=True) + '\n' for p in eye_points).encode('utf-8')
    yolo_files['README.txt'] = b'Partial box view only; eyes without measured extent are in eye-points.jsonl. Do not use missing eye boxes as negatives. Canonical confirmed.jsonl preserves all geometry. YOLO boxes clip half-pixel edges to the input.\n'
    with zipfile.ZipFile(output / 'yolo-labels.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(yolo_files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, yolo_files[name])
    (output / 'coco' / 'confirmed.coco.json').write_text(json.dumps({
        'info': {'description': 'Human-confirmed Z8-assisted labels, frozen 384x256 input',
                 'date': '2026-10-25'},
        'licenses': [],
        'images': coco_images,
        'annotations': coco_annotations,
        'point_annotations': coco_points,
        'geometry_policy': 'Source boxes only; point_annotations is a custom extension. Use confirmed.jsonl for complete partial-label supervision.',
        'categories': CATEGORIES,
    }, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')

    body = (output / 'confirmed.jsonl').read_bytes()
    summary = {
        'schema': 'forest-bird-af-confirmed-v2',
        'confirmed_images': len(records),
        'with_shapes': sum(1 for row in records if row['items']),
        'explicitly_no_bird': sum(1 for row in records if not row['items']
                                 and row['presence'] == 'absent'),
        'in_queue': sum(1 for row in records if row['in_queue']),
        'folded_by_similarity': sum(1 for row in records if not row['in_queue']),
        'z8_verdict': dict(sorted(per_verdict.items())),
        'parts': part_totals,
        'objects_in_coco': len(coco_annotations),
        'point_only_eyes': len(coco_points),
        'auxiliary_items': sum(i['kind'] == 'auxiliary' for r in records for i in r['items']),
        'source_labels_sha256': hashlib.sha256(args.labels.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
        'yolo_archive_sha256': hashlib.sha256((output / 'yolo-labels.zip').read_bytes()).hexdigest(),
        'per_split': per_split,
        'confirmed_sha256': hashlib.sha256(body).hexdigest(),
        'omitted_in_database': 'draft and needs_adjudication records are not labels',
        'notes': [
            'This is the full human-confirmed set, not a quality ranking.',
            'Labels describe the frozen 384 x 256 input, not the original photo.',
            'Confirmed by a human after seeing the frozen vendor boxes: assisted '
            'review, not independent blind annotation.',
            'Source items, ids, points and boxes are preserved exactly in confirmed.jsonl, including auxiliary regions.',
            'Point-only eyes have no fabricated extent. COCO keeps them in point_annotations; YOLO keeps eye-points.jsonl beside its partial box view. These are not complete standalone BHE detector targets.',
            '12 confirmed images are folded out of the annotation queue by the '
            'similarity grouping; in_queue keeps that visible instead of dropping them.',
        ],
    }
    (output / 'summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: summary[k] for k in
                      ('confirmed_images', 'with_shapes', 'explicitly_no_bird',
                       'in_queue', 'folded_by_similarity', 'parts', 'per_split',
                       'confirmed_sha256')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
