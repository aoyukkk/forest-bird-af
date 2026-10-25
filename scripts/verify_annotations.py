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


def verify_queue(problems, path, known_ids, splits):
    """The folded queue may hide images from the list view, never invent one."""
    if not path.exists():
        return None
    queue = json.loads(path.read_text(encoding='utf-8'))
    seen = set()
    for row in queue['images']:
        image_id = row['image_id']
        if image_id in seen:
            fail(problems, image_id, 'duplicate image in dedupe queue')
        seen.add(image_id)
        if known_ids is not None and image_id not in known_ids:
            fail(problems, image_id, 'dedupe queue entry missing from the label file')
        root = row.get('dedupe_root')
        if root is not None:
            if root not in known_ids:
                fail(problems, image_id, 'dedupe root is not a published image')
            if row['in_queue']:
                fail(problems, image_id, 'folded image still marked in_queue')
            if splits and splits.get(image_id) and splits.get(root) \
                    and splits[image_id] != splits[root]:
                fail(problems, image_id, 'dedupe group spans published splits')
        elif not row['in_queue']:
            fail(problems, image_id, 'image out of queue without a representative')
    for group in queue.get('groups', []):
        if group['representative'] not in group['members']:
            fail(problems, group['representative'],
                 'group representative missing from its own member list')
        if len(set(group['members'])) != len(group['members']):
            fail(problems, group['representative'], 'group repeats a member id')
    scanned = int(queue['summary']['images'])
    if scanned != len(queue['images']):
        fail(problems, 'summary', 'summary.images disagrees with the record list')
    scan_for_private_text(problems, 'dedupe-queue', queue)
    return queue


def verify_best(problems, path, known_ids):
    if not path.exists():
        return None
    best = json.loads(path.read_text(encoding='utf-8'))
    seen = set()
    for row in best['images']:
        image_id = row['image_id']
        if image_id in seen:
            fail(problems, image_id, 'image listed twice in best-images')
        seen.add(image_id)
        if known_ids is not None and image_id not in known_ids:
            fail(problems, image_id, 'best-image entry missing from the label file')
        if not any((row.get('parts') or {}).get(k) for k in COORDINATE_KINDS):
            fail(problems, image_id, 'best-image entry has no bird/head/eye part')
    if len(best['images']) != best['listed']:
        fail(problems, 'best-images', 'listed count disagrees with the record list')
    scan_for_private_text(problems, 'best-images', best)
    return best


def verify_confirmed(problems, path, records):
    """Every confirmed label must appear in the confirmed export, unchanged."""
    if not path.exists():
        return None
    expected = {row['image_id']: row for row in records
                if row['review_status'] == 'confirmed'}
    exported = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        image_id = row['image_id']
        if image_id in exported:
            fail(problems, image_id, 'duplicate image in confirmed export')
        exported[image_id] = row
        if image_id not in expected:
            fail(problems, image_id, 'confirmed export holds an unconfirmed image')
            continue
        if row.get('parts') != expected[image_id]['parts']:
            fail(problems, image_id, 'confirmed part counts differ from the label file')
        for item in row.get('items') or []:
            x1, y1, x2, y2 = item['box_xyxy']
            if not (x1 < x2 and y1 < y2):
                fail(problems, image_id, 'confirmed box is not positive-area')
            if not (-0.5 <= x1 and -0.5 <= y1 and x2 <= 384 + -0.5 and y2 <= 256 + -0.5):
                fail(problems, image_id, 'confirmed box leaves the input')
        scan_for_private_text(problems, image_id, row)
    missing = sorted(set(expected) - set(exported))
    for image_id in missing:
        fail(problems, image_id, 'confirmed label missing from the confirmed export')
    return exported


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
    splits = {}.fromkeys(()) if manifest is None else \
        {row['image_id']: row['split'] for row in manifest['images']}
    queue = verify_queue(problems, root / 'dedupe-queue-v1.json', known, splits)
    best = verify_best(problems, root / 'best-images-v1.json', known)
    confirmed = verify_confirmed(problems, root / 'confirmed' / 'confirmed.jsonl', records)
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
        'queue': queue['summary']['queue'] if queue else None,
        'folded': queue['summary']['folded'] if queue else None,
        'best_listed': best['listed'] if best else None,
        'confirmed_exported': len(confirmed) if confirmed else None,
        'violations': len(problems),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for problem in problems[:50]:
        print('  ' + problem)
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
