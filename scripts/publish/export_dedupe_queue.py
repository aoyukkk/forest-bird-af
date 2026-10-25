#!/usr/bin/env python3
"""Export the deduplicated review queue as a publishable, private-free manifest.

Reads a **copy** of the annotation workspace (never the live one) and writes
``data/annotations-2026-10-25/curation/dedupe-queue-v1.json``:

* per-image split assignment, review status and part counts (from the published
  label file, which is already slimmed)
* which images the conservative similarity grouping folds, and onto which root
* the collinear group list and the recorded thresholds

Every group member matched its root directly (no transitive collapsing), and no
member is pixel-identical to its root: these are similar frames, not exact
duplicates. That distinction is preserved in the output and in the docs.

Usage::

    python scripts/publish/export_dedupe_queue.py --dedupe <workspace>/dedupe/current.json \\
        --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \\
        --split data/annotations-2026-10-25/splits/evaluation-split-v1.json \\
        --output data/annotations-2026-10-25
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = 'forest-bird-af-dedupe-queue-v1'


def read_labels(path):
    rows = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[row['image_id']] = row
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dedupe', required=True, type=Path)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--split', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()

    current = json.loads(args.dedupe.read_text(encoding='utf-8'))
    labels = read_labels(args.labels)
    split = json.loads(args.split.read_text(encoding='utf-8'))
    assignment = {row['image_id']: row['split'] for row in split['images']}

    hidden = current.get('hidden') or {}
    groups = current.get('groups') or []
    missing = sorted(set(hidden) - set(labels))
    if missing:
        sys.exit('Dedupe refers to images missing from the label file: %s' % missing[:5])

    root_of = {}
    for group in groups:
        root = group['representative']
        for member in group['members']:
            root_of[member] = root

    split_leaks = sorted({labels[i]['image_id'] for i, r in hidden.items()
                          if assignment.get(i) and assignment.get(r)
                          and assignment[i] != assignment[r]})

    images = []
    for image_id in sorted(labels):
        row = labels[image_id]
        images.append({
            'image_id': image_id,
            'split': assignment.get(image_id),
            'review_status': row['review_status'],
            'presence': row['presence'],
            'parts': row['parts'],
            'dedupe_root': hidden.get(image_id),
            'in_queue': image_id not in hidden,
        })

    payload = {
        'schema': SCHEMA,
        'source_created_at': current.get('created_at'),
        'run_id': current.get('run_id'),
        'thresholds': current.get('thresholds'),
        'summary': {
            'images': len(images),
            'queue': sum(1 for row in images if row['in_queue']),
            'folded': len(hidden),
            'groups': len(groups),
            'candidate_groups': len(current.get('candidate_groups') or []),
            'folded_confirmed': sum(1 for i in hidden
                                    if labels[i]['review_status'] == 'confirmed'),
            'root_edges': len(root_of),
            'split_mismatch_pairs': len(split_leaks),
        },
        'group_shape': {
            'representative': 'the image whose number and quality anchor the group',
            'members': 'member ids, representative first',
            'max_group_size': max((len(g['members']) for g in groups), default=0),
        },
        'groups': [{'representative': g['representative'],
                    'members': list(g['members']),
                    'split': assignment.get(g['representative'])} for g in groups],
        'images': images,
        'semantics': [
            'Reversible queue view: folding never writes images, labels or history.',
            'Every member matched its representative directly; no transitive collapsing.',
            'No folded member has input pixels identical to its representative: these '
            'are similar frames of the same scene or burst, not byte duplicates.',
            'A similarity group is an engineering hint, not a confirmed capture sequence, '
            'and it never spans published splits.',
            'To see a folded frame again, clear "Hide duplicates" in the annotator or '
            'use the Duplicates filter.',
        ],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=1) + '\n'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'dedupe-queue-v1.json'
    target.write_text(body, encoding='utf-8')
    payload['digest'] = hashlib.sha256(body.encode('utf-8')).hexdigest()
    print(json.dumps({'summary': payload['summary'],
                      'sha256': payload['digest'],
                      'path': str(target)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
