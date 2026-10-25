#!/usr/bin/env python3
"""Convert one label record into COCO, YOLO and plain JSON annotation files.

The published labels describe the frozen 384 x 256 review input, so the helper
writes exactly three outputs for one ``image_id``:

* ``<id>.coco.json``   - COCO detection with three categories
* ``<id>.yolo.txt``    - YOLO txt rows ``class cx cy w h`` normalised 0-1
* ``<id>.json``        - the source record plus a portable summary

Part semantics follow the published data: bird and head are boxes, an eye is a
centre point (a visible-boundary box is kept when it exists). Auxiliary vendor
regions are not bird labels and are excluded from COCO/YOLO output.

Usage::

    python scripts/export_label_formats.py --labels <jsonl> --image fb_0241 --output <dir>
    python scripts/export_label_formats.py --labels <jsonl> --output <dir>   # every record
"""
import argparse
import json
import sys
from pathlib import Path

WIDTH, HEIGHT = 384, 256
CATEGORIES = [{'id': 1, 'name': 'bird'}, {'id': 2, 'name': 'head'}, {'id': 3, 'name': 'eye'}]
CLASS_INDEX = {'bird': 0, 'head': 1, 'eye': 2}
EYE_BOX_PX = 12.0


def eye_box(item):
    if item.get('box_xyxy'):
        return [float(v) for v in item['box_xyxy']]
    x, y = item['point_xy']
    half = EYE_BOX_PX / 2
    return [max(0.0, x - half), max(0.0, y - half),
            min(float(WIDTH), x + half), min(float(HEIGHT), y + half)]


def to_coco(row):
    annotations, index = [], 1
    for item in row['items']:
        kind = item['kind']
        if kind not in CLASS_INDEX:
            continue
        box = eye_box(item) if kind == 'eye' else [float(v) for v in item['box_xyxy']]
        x1, y1, x2, y2 = box
        annotations.append({
            'id': index,
            'image_id': row['image_id'],
            'category_id': CLASS_INDEX[kind] + 1,
            'bbox': [round(x1, 3), round(y1, 3), round(x2 - x1, 3), round(y2 - y1, 3)],
            'area': round((x2 - x1) * (y2 - y1), 3),
            'iscrowd': 0,
            'source': 'eye_center_boxed' if kind == 'eye' and not item.get('box_xyxy') else 'human',
        })
        index += 1
    return {
        'info': {'description': 'Z8-assisted human correction, frozen 384x256 input',
                 'width': WIDTH, 'height': HEIGHT},
        'licenses': [],
        'images': [{'id': row['image_id'], 'file_name': row['image_id'] + '.png',
                    'width': WIDTH, 'height': HEIGHT,
                    'input_chw_u8_sha256': row['annotation_image']['input_chw_u8_sha256']}],
        'annotations': annotations,
        'categories': CATEGORIES,
    }


def to_yolo(row):
    lines = []
    for item in row['items']:
        kind = item['kind']
        if kind not in CLASS_INDEX:
            continue
        x1, y1, x2, y2 = eye_box(item) if kind == 'eye' else [float(v) for v in item['box_xyxy']]
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
                        help='skip draft and unconfirmed records')
    args = parser.parse_args()

    rows = []
    for line in args.labels.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if args.image and row['image_id'] != args.image:
            continue
        if args.confirmed_only and row['review_status'] != 'confirmed':
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
            json.dumps(coco, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (stem.parent / (row['image_id'] + '.yolo.txt')).write_text(
            to_yolo(row), encoding='utf-8')
        portable = {k: row[k] for k in ('image_id', 'annotation_image', 'review_status',
                                        'presence', 'decision', 'parts', 'items')}
        portable['coordinate_space'] = row['annotation_image']['coordinate_space']
        (stem.parent / (row['image_id'] + '.json')).write_text(
            json.dumps(portable, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        written += 1
    print(json.dumps({'records': written, 'directory': str(output),
                      'categories': [c['name'] for c in CATEGORIES]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
