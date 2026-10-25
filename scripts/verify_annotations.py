#!/usr/bin/env python3
"""Check the published annotation manifests for schema, geometry and leakage.

Runs offline with no third-party dependencies and no image access::

    python scripts/verify_annotations.py [published_dir]

Default directory is ``data/annotations-2026-10-25``. Exit code 0 means every
record is structurally valid and the published splits stay leakage-free; 1
means at least one violation, printed with its image id.
"""
import argparse
import json
import sys
from pathlib import Path

INPUT_WIDTH, INPUT_HEIGHT = 384, 256
KINDS = {'bird', 'head', 'eye', 'auxiliary'}
COORDINATE_KINDS = ('bird', 'head', 'eye')
STATUSES = {'draft', 'confirmed', 'needs_adjudication'}
PRESENCES = {'present', 'absent', 'uncertain'}
FORBIDDEN_KEYS = {
    'reference_path', 'original_sha256', 'reference_sha256', 'confirmed_by',
    'actor', 'reviewer', 'email', 'gps', 'serial', 'camera_serial',
}
# Substrings that must never appear in a published record value.
FORBIDDEN_TEXT = ('E:\\', 'E:/Z8', 'C:\\Users', '\\\\?\\')


def fail(problems, image_id, message):
    problems.append('%s: %s' % (image_id, message))


def check_point(problems, image_id, item):
    point = item.get('point_xy')
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        fail(problems, image_id, 'point_xy must be [x, y] for %s' % item.get('id'))
        return
    x, y = point
    if not (0 <= x < INPUT_WIDTH and 0 <= y < INPUT_HEIGHT):
        fail(problems, image_id, 'point outside input: %s' % (point,))


def check_box(problems, image_id, item):
    # Native candidate boxes are inclusive pixel coordinates in [-0.5, 383.5];
    # manual boxes are exclusive xyxy in [0, 384] x [0, 256]. Both are legal.
    box = item.get('box_xyxy')
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        fail(problems, image_id, 'box_xyxy must be 4 numbers for %s' % item.get('id'))
        return
    x1, y1, x2, y2 = box
    if not (x1 < x2 and y1 < y2):
        fail(problems, image_id, 'box not positive-area: %s' % (box,))
        return
    tolerance = -.5
    if not (-0.5 <= x1 < x2 <= INPUT_WIDTH + tolerance
            and -0.5 <= y1 < y2 <= INPUT_HEIGHT + tolerance):
        fail(problems, image_id, 'box out of range: %s' % (box,))


def check_item(problems, image_id, item):
    kind = item.get('kind')
    if kind not in KINDS:
        fail(problems, image_id, 'unknown kind %r' % (kind,))
        return
    if not item.get('id'):
        fail(problems, image_id, 'item without id')
    if item.get('box_xyxy') is None and item.get('point_xy') is None:
        fail(problems, image_id, 'item %s has neither box nor point' % item.get('id'))
    if kind == 'eye':
        if item.get('point_xy') is not None:
            check_point(problems, image_id, item)
        if item.get('box_xyxy') is None and item.get('point_xy') is None:
            fail(problems, image_id, 'eye without point')
    else:
        check_box(problems, image_id, item)


def scan_for_private_text(problems, image_id, value, path=''):
    if isinstance(value, dict):
        for key, inner in value.items():
            if key in FORBIDDEN_KEYS:
                fail(problems, image_id, 'private key leaked at %s%s' % (path, key))
            scan_for_private_text(problems, image_id, inner, path + key + '.')
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            scan_for_private_text(problems, image_id, inner, path + str(index) + '.')
    elif isinstance(value, str):
        for token in FORBIDDEN_TEXT:
            if token in value:
                fail(problems, image_id, 'path-like value leaked at %s' % path)


def verify_labels(problems, path):
    records = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            fail(problems, 'line %d' % number, 'invalid JSON: %s' % error)
            continue
        image_id = row.get('image_id', 'line %d' % number)
        if row.get('review_status') not in STATUSES:
            fail(problems, image_id, 'bad review_status %r' % row.get('review_status'))
        if row.get('presence') is not None and row['presence'] not in PRESENCES:
            fail(problems, image_id, 'bad presence %r' % row.get('presence'))
        image = row.get('annotation_image') or {}
        if (image.get('width'), image.get('height')) != (INPUT_WIDTH, INPUT_HEIGHT):
            fail(problems, image_id, 'annotation image is not %dx%d'
                 % (INPUT_WIDTH, INPUT_HEIGHT))
        if image.get('coordinate_space') != 'z8_input_384x256':
            fail(problems, image_id, 'unexpected coordinate space')
        items = row.get('items') or []
        seen = set()
        for item in items:
            if item.get('id') in seen:
                fail(problems, image_id, 'duplicate item id %s' % item.get('id'))
            seen.add(item.get('id'))
            check_item(problems, image_id, item)
        counted = {kind: sum(1 for i in items if i.get('kind') == kind)
                   for kind in ('bird', 'head', 'eye')}
        if row.get('parts') and counted != {k: row['parts'].get(k, 0) for k in counted}:
            fail(problems, image_id, 'parts counts disagree with items')
        scan_for_private_text(problems, image_id, row)
        records.append(row)
    return records


def verify_split(problems, path, known_ids):
    manifest = json.loads(path.read_text(encoding='utf-8'))
    group_split = {}
    seen = set()
    for row in manifest['images']:
        image_id = row['image_id']
        if image_id in seen:
            fail(problems, image_id, 'duplicate image in split manifest')
        seen.add(image_id)
        if known_ids is not None and image_id not in known_ids:
            fail(problems, image_id, 'not present in the published label file')
        if row['split'] not in ('train', 'val', 'test'):
            fail(problems, image_id, 'bad split %r' % row['split'])
        group_split.setdefault(row['leakage_group_id'], set()).add(row['split'])
        if len(row.get('input_sha256') or '') != 64:
            fail(problems, image_id, 'input_sha256 is not a sha256 hex digest')
        scan_for_private_text(problems, image_id, row)
    leaked = sorted(group for group, splits in group_split.items() if len(splits) > 1)
    for group in leaked:
        fail(problems, group, 'leakage group spans splits')
    for name, expected in (manifest.get('counts') or {}).items():
        actual = sum(1 for row in manifest['images'] if row['split'] == name)
        if actual != expected:
            fail(problems, 'counts', '%s says %d, manifest holds %d'
                 % (name, expected, actual))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('directory', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[1]
                        / 'data' / 'annotations-2026-10-25')
    args = parser.parse_args()
    root = args.directory
    labels_path = root / 'labels' / 'community-corrections-v1.jsonl'
    split_path = root / 'evaluation-split-v1.json'
    problems = []
    records = verify_labels(problems, labels_path)
    known = {row['image_id'] for row in records}
    manifest = verify_split(problems, split_path, known) if split_path.exists() else None
    counts = {}
    for row in records:
        counts[row['review_status']] = counts.get(row['review_status'], 0) + 1
    summary = {
        'labels': len(records),
        'by_status': counts,
        'confirmed_items': sum(len(row['items']) for row in records
                               if row['review_status'] == 'confirmed'),
        'split_images': len(manifest['images']) if manifest else 0,
        'split_counts': manifest['counts'] if manifest else None,
        'violations': len(problems),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for problem in problems[:50]:
        print('  ' + problem)
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
