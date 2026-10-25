#!/usr/bin/env python3
"""Build the published evaluation-split manifest from a frozen training dataset.

The training run freezes ``dataset.json`` (per-image split assignment and
leakage-group id) together with ``split-lock.json``. This script publishes the
*assignment only*: no absolute paths, no original-asset hashes, no reference
image hashes, no annotation text. Everything a reader needs to re-download the
inputs already exists in the release packages and in
``data/registry.csv``.

Usage::

    python scripts/publish/export_split_manifest.py --dataset <dataset.json> \\
        --lock <split-lock.json> --output data/annotations-2026-10-25

Like the label exporter this is read-only for its inputs.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

PRIVATE_METADATA = ('reference_path', 'original_sha256', 'reference_sha256',
                    'baseline', 'document', 'document_sha256')


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', required=True, type=Path)
    parser.add_argument('--lock', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
    lock = json.loads(args.lock.read_text(encoding='utf-8'))
    recorded = dataset.get('annotation_snapshot_sha256')
    if lock.get('dataset_sha256') != sha_file(args.dataset):
        sys.exit('dataset.json does not match the split lock; refusing to publish')

    images = []
    groups = {}
    for row in dataset['images']:
        metadata = row.get('metadata') or {}
        split = row['split']
        images.append({
            'image_id': row['image_id'],
            'split': split,
            'leakage_group_id': row['leakage_group_id'],
            'batch': metadata.get('batch'),
            'input_sha256': metadata.get('input_sha256'),
            'png_sha256': metadata.get('png_sha256'),
            'preprocess_id': metadata.get('preprocess_id'),
            'parts': {
                'bird': sum(1 for i in (row.get('document') or {}).get('items', [])
                            if i.get('kind') == 'bird'),
                'head': sum(1 for i in (row.get('document') or {}).get('items', [])
                            if i.get('kind') == 'head'),
                'eye': sum(1 for i in (row.get('document') or {}).get('items', [])
                           if i.get('kind') == 'eye'),
            },
            'review_status': (row.get('document') or {}).get('status'),
            'presence': (row.get('document') or {}).get('presence'),
            'frozen_candidates': len(row.get('baseline') or []),
        })
        groups.setdefault(row['leakage_group_id'], set()).add(split)

    leaked = sorted(g for g, s in groups.items() if len(s) > 1)
    if leaked:
        sys.exit('Leakage groups span splits: %s' % leaked[:5])

    counts = {name: sum(1 for i in images if i['split'] == name) for name in
              ('train', 'val', 'test')}
    parts = {name: {kind: sum(i['parts'][kind] for i in images if i['split'] == name)
                    for kind in ('bird', 'head', 'eye')} for name in counts}
    manifest = {
        'schema': 'forest-bird-af-eval-split-v1',
        'dataset_sha256': lock['dataset_sha256'],
        'annotation_snapshot_sha256': recorded,
        'counts': counts,
        'group_counts': {name: len({i['leakage_group_id'] for i in images
                                    if i['split'] == name}) for name in counts},
        'group_part_item_counts': parts,
        'selection': lock.get('selection'),
        'test_policy': lock.get('test_policy'),
        'grouping_limits': dataset.get('grouping_limits'),
        'excluded_images': len(dataset.get('excluded_ids') or {}),
        'images': images,
        'omitted_fields': list(PRIVATE_METADATA),
        'notes': [
            'Splits were frozen before training; test was opened once after '
            'validation-only candidate selection.',
            'Grouping is an engineering anti-leakage approximation, not verified '
            'photographer or capture-event identity.',
            'Labels are Z8-assisted human corrections, not independent blind '
            'annotation, and are bound to the frozen 384 x 256 input.',
        ],
    }
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'evaluation-split-v1.json'
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n',
                      encoding='utf-8')
    print(json.dumps({'counts': counts, 'groups': manifest['group_counts'],
                      'path': str(target),
                      'sha256': sha_file(target)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
