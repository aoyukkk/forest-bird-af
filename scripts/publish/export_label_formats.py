#!/usr/bin/env python3
"""Convert one label record into COCO, YOLO and plain JSON annotation files.

The published labels describe the frozen 384 x 256 review input, so the helper
writes exactly three outputs for one ``image_id``:

* ``<id>.coco.json``   - source boxes plus a custom point_annotations extension
* ``<id>.yolo.txt``    - partial measured-box view, normalised 0-1
* ``<id>.json``        - the source record plus a portable summary

Part semantics follow the published data: bird and head are boxes, an eye is a
centre point (a visible-boundary box is kept when it exists). Auxiliary vendor
regions are not bird labels and are excluded from COCO/YOLO output.

Usage::

    python scripts/publish/export_label_formats.py --labels <jsonl> --image fb_0241 --output <dir>
    python scripts/publish/export_label_formats.py --labels <jsonl> --output <dir>   # confirmed records
"""
import argparse
import json
import sys
from pathlib import Path

WIDTH, HEIGHT = 384, 256
CATEGORIES = [{'id': 1, 'name': 'bird'}, {'id': 2, 'name': 'head'}, {'id': 3, 'name': 'eye'}]
CLASS_INDEX = {'bird': 0, 'head': 1, 'eye': 2}
def measured_boxes(row):
    """Only actual source boxes; point annotations never acquire an extent."""
    for item in row['items']:
        if item['kind'] in CLASS_INDEX and item.get('box_xyxy') is not None:
            yield item['kind'], item, [float(v) for v in item['box_xyxy']]


def to_coco(row):
    annotations, points, index = [], [], 1
    for item in row['items']:
        kind = item['kind']
        if kind not in CLASS_INDEX:
            continue
        if item.get('box_xyxy') is None:
            if kind == 'eye' and item.get('point_xy') is not None:
                points.append({'id': index, 'image_id': row['image_id'], 'source_item_id': item['id'],
                               'category_id': 3, 'point_xy': list(item['point_xy'])})
                index += 1
            continue
        box = [float(v) for v in item['box_xyxy']]
        x1, y1, x2, y2 = box
        annotations.append({
            'id': index,
            'image_id': row['image_id'],
            'category_id': CLASS_INDEX[kind] + 1,
            'bbox': [round(x1, 3), round(y1, 3), round(x2 - x1, 3), round(y2 - y1, 3)],
            'area': round((x2 - x1) * (y2 - y1), 3),
            'iscrowd': 0,
            'source_item_id': item['id'],
        })
        index += 1
    return {
        'info': {'description': 'Z8-assisted human correction, frozen 384x256 input',
                 'review_status': row['review_status'],
                 'width': WIDTH, 'height': HEIGHT},
        'licenses': [],
        'images': [{'id': row['image_id'], 'file_name': row['image_id'] + '.png',
                    'width': WIDTH, 'height': HEIGHT,
                    'input_chw_u8_sha256': row['annotation_image']['input_chw_u8_sha256']}],
        'annotations': annotations,
        'point_annotations': points,
        'geometry_policy': 'COCO annotations contain source boxes only. point_annotations is a custom extension; use JSONL for complete partial-label supervision.',
        'categories': CATEGORIES,
    }


def to_yolo(row):
    lines = []
    for kind, item, box in measured_boxes(row):
        x1, y1, x2, y2 = box
        x1, y1, x2, y2 = max(0., x1), max(0., y1), min(WIDTH, x2), min(HEIGHT, y2)
        cx, cy = (x1 + x2) / 2 / WIDTH, (y1 + y2) / 2 / HEIGHT
        w, h = (x2 - x1) / WIDTH, (y2 - y1) / HEIGHT
        lines.append('%d %.6f %.6f %.6f %.6f' % (CLASS_INDEX[kind], cx, cy, w, h))
    return '\n'.join(lines) + ('\n' if lines else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--image', help='one image id, e.g. fb_0241')
    parser.add_argument('--confirmed-only', action='store_true',
                        help='compatibility alias; confirmed-only is the default')
    parser.add_argument('--include-unconfirmed', action='store_true',
                        help='inspection only: also export drafts/adjudication, with status in the JSON')
    args = parser.parse_args()

    rows = []
    for line in args.labels.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if args.image and row['image_id'] != args.image:
            continue
        if (args.confirmed_only or not args.include_unconfirmed) and row['review_status'] != 'confirmed':
            continue
        rows.append(row)
    if not rows:
        sys.exit('No matching label record')

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    written = 0
    for row in rows:
        stem = output / row['image_id']
        coco = to_coco(row)
        (stem.parent / (row['image_id'] + '.coco.json')).write_text(
            json.dumps(coco, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
        (stem.parent / (row['image_id'] + '.yolo.txt')).write_text(
            to_yolo(row), encoding='utf-8', newline='\n')
        portable = {k: row[k] for k in ('image_id', 'annotation_image', 'review_status',
                                        'presence', 'decision', 'parts', 'items')}
        portable['coordinate_space'] = row['annotation_image']['coordinate_space']
        (stem.parent / (row['image_id'] + '.json')).write_text(
            json.dumps(portable, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
        written += 1
    print(json.dumps({'records': written, 'directory': str(output),
                      'categories': [c['name'] for c in CATEGORIES]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
