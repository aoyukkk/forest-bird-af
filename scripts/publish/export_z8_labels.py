#!/usr/bin/env python3
"""Export the Z8-assisted human review state into publishable label files.

Reads a read-only copy of the local annotation database (never the original
path) and writes, in the caller's output directory:

* ``labels/community-corrections-v1.jsonl`` - one record per reviewed image
* ``labels/community-corrections-v1.json`` - counts and hashes
* ``labels/summary.md`` - a short human summary

The export is deliberately lossy about anything private: original absolute
paths, reference-image hashes and reviewer identifiers are dropped. Coordinates
stay bound to the frozen 384 x 256 input described by ``coordinate_space``.

Usage::

    python scripts/publish/export_z8_labels.py --database <copy-of-annotations.sqlite3> \\
        --output data/annotations-2026-10-25

The script is read-only with respect to both the upstream packages and the
production annotation database; it refuses to run against a live database that
still has a ``-wal`` sidecar.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

SCHEMA = 'forest-bird-z8-corrections-v1'
KINDS = ('bird', 'head', 'eye')
PARTS = ('bird', 'head', 'eye')
# Auxiliary candidates are kept verbatim so a consumer can tell a reviewed box
# from an unreviewed vendor region; they are never bird/head/eye truth.
FROZEN_KINDS = ('bird', 'head', 'eye', 'auxiliary')
BASELINE_ACTOR = 'z8-baseline-import-'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load_documents(connection, table):
    """Rows are (id, revision, document); store the raw document per image."""
    out = {}
    for image_id, revision, raw in connection.execute(
            'select id, revision, document from ' + table):
        out[image_id] = (revision, json.loads(raw) if isinstance(raw, str) else raw)
    return out


def load_history(connection):
    """Return per-image (first_items, last_items, last_actor, revision_count).

    The first revision carries the imported frozen Z8 baseline; the last one is
    the current state. Reviewer identity is used only to classify the row and is
    never written to the export.
    """
    out = {}
    for image_id, revision, raw, actor in connection.execute(
            'select id, revision, document, actor from z8_review_history '
            'order by id, revision'):
        document = json.loads(raw) if isinstance(raw, str) else raw
        parts = document.get('items') or []
        entry = out.setdefault(image_id, {'first': [], 'last': [], 'actor': '',
                                          'count': 0, 'baseline_actor': ''})
        if revision == 1:
            entry['first'] = parts
            entry['baseline_actor'] = actor or ''
        entry['last'] = parts
        entry['actor'] = actor or ''
        entry['count'] += 1
    return out


def clean_item(item):
    """Keep geometry and part kind; drop nothing else because nothing else exists."""
    out = {'id': item['id'], 'kind': item['kind']}
    if item.get('box_xyxy') is not None:
        out['box_xyxy'] = [float(v) for v in item['box_xyxy']]
    if item.get('point_xy') is not None:
        out['point_xy'] = [float(v) for v in item['point_xy']]
    return out


def clean_diff(diff):
    return {
        'added': [clean_item(i) for i in diff.get('added', [])],
        'removed': [clean_item(i) for i in diff.get('removed', [])],
        'changed': [{'id': c['id'],
                     'before': clean_item(c['before']),
                     'after': clean_item(c['after'])} for c in diff.get('changed', [])],
        'unchanged': [clean_item(i) for i in diff.get('unchanged', [])]
        if isinstance(diff.get('unchanged'), list) else [],
        'changed_parts': list(diff.get('changed_parts', [])),
    }


def record_for(image_id, review, history_entry):
    revision, document = review
    diff = document.get('diff') or {}
    items = [clean_item(i) for i in document.get('items', [])]
    current = [clean_item(i) for i in history_entry['last']]
    frozen = [clean_item(i) for i in history_entry['first']]
    counts = {kind: sum(1 for i in items if i['kind'] == kind) for kind in KINDS}
    return {
        'image_id': image_id,
        'annotation_image': {
            'width': document['annotation_image']['width'],
            'height': document['annotation_image']['height'],
            'png_sha256': document['annotation_image']['sha256'],
            'input_chw_u8_sha256': document['annotation_image']['input_chw_u8_sha256'],
            'preprocess_id': document['annotation_image']['preprocess_id'],
            'coordinate_space': document['annotation_image']['coordinate_space'],
        },
        'review_status': document.get('status'),
        'presence': document.get('presence'),
        'decision': document.get('decision'),
        'revision': revision,
        'revisions': history_entry['count'],
        # A needs-adjudication row is written by a human but is explicitly not
        # usable truth, so it must never read as a confirmed label.
        'confirmed': document.get('status') == 'confirmed',
        'parts': counts,
        'items': items,
        'frozen_z8_candidates': {kind: sum(1 for i in frozen if i['kind'] == kind)
                                 for kind in FROZEN_KINDS},
        'frozen_z8_candidate_total': len(frozen),
        'frozen_baseline_matches_current': frozen == current,
        'review_changes': diff.get('modified_count'),
        'diff': clean_diff(diff) if diff else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--database', required=True, type=Path,
                        help='read-only copy of annotations.sqlite3')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--notes', default='',
                        help='free-text scope note stored in the summary')
    args = parser.parse_args()
    database = args.database.resolve()
    output = args.output.resolve()
    if (database.parent / (database.name + '-wal')).exists():
        wal = database.parent / (database.name + '-wal')
        if wal.stat().st_size:
            sys.exit('Refusing a live database: %s holds pending writes. Copy it first.' % wal)
    if not database.is_file():
        sys.exit('Missing database: %s' % database)
    connection = sqlite3.connect('file:%s?mode=ro' % database.as_posix(), uri=True)
    reviews = load_documents(connection, 'z8_reviews')
    history = load_history(connection)
    connection.close()

    labels_dir = output / 'labels'
    labels_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for image_id in sorted(reviews):
        entry = history.get(image_id, {'first': [], 'last': [], 'count': 0,
                                       'baseline_actor': ''})
        review = reviews[image_id]
        row = record_for(image_id, reviews[image_id], entry)
        row['record_sha256'] = sha(json.dumps(row, sort_keys=True, ensure_ascii=False))
        records.append(row)

    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in records]
    body = '\n'.join(lines) + '\n'
    (labels_dir / 'community-corrections-v1.jsonl').write_text(body, encoding='utf-8', newline='\n')

    def counter(key):
        out = {}
        for row in records:
            value = row[key]
            key_name = 'unset' if value is None else str(value)
            out[key_name] = out.get(key_name, 0) + 1
        return dict(sorted(out.items()))

    selected = [row for row in records if row['review_status'] == 'confirmed']
    counts = {
        'schema': SCHEMA,
        'images': len(records),
        'by_review_status': counter('review_status'),
        'by_decision': counter('decision'),
        'by_presence': counter('presence'),
        'confirmed_images': len(selected),
        'confirmed_parts': {kind: sum(row['parts'][kind] for row in selected)
                            for kind in PARTS},
        'confirmed_items_total': sum(sum(row['parts'].values()) for row in selected),
        'frozen_candidates_total': sum(row['frozen_z8_candidate_total'] for row in records),
        'frozen_baseline_matches_current': sum(1 for row in records
                                               if row['frozen_baseline_matches_current']),
        'coordinate_space': 'z8_input_384x256',
        'labels_sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
        'source_database_sha256': hashlib.sha256(database.read_bytes()).hexdigest(),
        'removed_fields': ['reference_path', 'original_sha256', 'reference_sha256',
                           'confirmed_by', 'notes', 'baseline_sha256'],
        'notes': args.notes,
        'label_provenance': 'Z8-assisted human review; not independent blind annotation',
        'allowed_uses': 'offline research and evaluation of bird body/head/eye detection',
        'forbidden_claims': ['camera autofocus accuracy', 'in-camera verification',
                             'photographer identity or capture event'],
    }
    (labels_dir / 'community-corrections-v1.json').write_text(
        json.dumps(counts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    summary = [
        '# 已标注结果摘要 / Annotation summary',
        '',
        '- schema: `%s`' % SCHEMA,
        '- 图像记录 / records: %d' % counts['images'],
        '- 已确认 / confirmed: %d' % counts['confirmed_images'],
        '- 状态 / review status: %s' % json.dumps(counts['by_review_status'], ensure_ascii=False),
        '- 判定 / decision: %s' % json.dumps(counts['by_decision'], ensure_ascii=False),
        '- 确认样本部位数 / confirmed parts: %s'
        % json.dumps(counts['confirmed_parts'], ensure_ascii=False),
        '- 标签文件 / labels: `community-corrections-v1.jsonl` (%s)'
        % counts['labels_sha256'],
        '',
        '坐标绑定冻结 384×256 输入；标签来自 Z8 辅助人工纠错，不是独立盲标。',
        'Coordinates are bound to the frozen 384 × 256 input; labels are Z8-assisted',
        'human corrections, not independent blind annotation.',
        '',
    ]
    (labels_dir / 'summary.md').write_text('\n'.join(summary), encoding='utf-8', newline='\n')
    print(json.dumps({k: counts[k] for k in
                      ('images', 'confirmed_images', 'confirmed_parts',
                       'by_review_status', 'labels_sha256')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
