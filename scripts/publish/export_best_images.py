#!/usr/bin/env python3
"""Rank the reviewed stills most worth sharing as examples.

Selection is deliberately mechanical and inspectable. An image qualifies only
when it is human-confirmed, sits in the deduplicated queue, and has at least one
bird/head/eye shape. It is then scored on how much the frozen Z8 candidates
differed from the human correction, how many parts are annotated, and whether
the frame is one where foliage made the vendor model work hard.

Scores are a review-order aid, not an accuracy measure: nothing here says a
photo is "good" artistically or that the model succeeded.

Usage::

    python scripts/publish/export_best_images.py \\
        --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \\
        --dedupe data/annotations-2026-10-25/curation/dedupe-queue-v1.json \\
        --output data/annotations-2026-10-25
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = 'forest-bird-af-best-images-v1'
MAX_LIST = 120


def score(row, queue_row):
    diff = row.get('diff') or {}
    added = len(diff.get('added') or [])
    removed = len(diff.get('removed') or [])
    changed = len(diff.get('changed') or [])
    parts = row.get('parts') or {}
    eye, head, bird = parts.get('eye', 0), parts.get('head', 0), parts.get('bird', 0)
    occupied = sum(row.get('frozen_z8_candidates', {}).values())
    # Full instruction coverage first (eye+head+bird), then correction effort.
    coverage = (2 if eye else 0) + (1 if head else 0) + (1 if bird else 0)
    effort = 3 * removed + 2 * added + changed
    value = 4 * coverage + effort + (2 if occupied == 0 else 0)
    return value, {'coverage': coverage, 'correction_effort': effort,
                   'added': added, 'removed': removed, 'changed': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--dedupe', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--limit', type=int, default=MAX_LIST)
    args = parser.parse_args()

    labels = {}
    for line in args.labels.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            labels[row['image_id']] = row
    queue = {row['image_id']: row for row in
             json.loads(args.dedupe.read_text(encoding='utf-8'))['images']}

    ranked, rejected = [], {'draft_or_unconfirmed': 0, 'folded_out_of_queue': 0,
                            'no_eye_head_bird_shape': 0}
    for image_id, row in labels.items():
        if row['review_status'] != 'confirmed':
            rejected['draft_or_unconfirmed'] += 1
            continue
        if not queue.get(image_id, {}).get('in_queue'):
            rejected['folded_out_of_queue'] += 1
            continue
        parts = row.get('parts') or {}
        if not any(parts.get(k) for k in ('bird', 'head', 'eye')):
            rejected['no_eye_head_bird_shape'] += 1
            continue
        value, detail = score(row, queue[image_id])
        ranked.append({'image_id': image_id, 'score': value, 'split': queue[image_id]['split'],
                       'parts': parts, 'frozen_z8_candidates': row.get('frozen_z8_candidates'),
                       'decision': row['decision'], **detail})
    ranked.sort(key=lambda r: (-r['score'], r['image_id']))
    chosen = ranked[:args.limit]
    payload = {
        'schema': SCHEMA,
        'ranked_total': len(ranked),
        'listed': len(chosen),
        'rejected': rejected,
        'rule': {
            'eligible': 'human-confirmed, in the deduplicated queue, at least one '
                        'bird/head/eye shape',
            'score': '4*coverage + (3*removed + 2*added + changed) + 2 if the vendor '
                     'model produced no candidate in this frame',
            'coverage': '2 for an annotated eye, +1 head, +1 bird',
            'meaning': 'review priors and correction effort, not detection accuracy',
        },
        'images': chosen,
        'per_split': {name: sum(1 for r in chosen if r['split'] == name)
                      for name in ('train', 'val', 'test')},
        'images_in_release': 'download the batch release that contains the ids; see data/registry.csv',
    }
    body = json.dumps(payload, ensure_ascii=False, indent=1) + '\n'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'best-images-v1.json'
    target.write_text(body, encoding='utf-8', newline='\n')
    print(json.dumps({'ranked_total': len(ranked), 'listed': len(chosen),
                      'rejected': rejected, 'per_split': payload['per_split'],
                      'sha256': hashlib.sha256(body.encode()).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
