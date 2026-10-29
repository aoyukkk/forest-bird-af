"""Validate explicit point reviews; support is not an eye-coordinate label."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def load_review(manifest_path, review_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    payload = json.loads(Path(review_path).read_text(encoding='utf-8'))
    expected = {}
    for item in manifest['records']:
        key = item['image_id']
        if key in expected:
            raise ValueError('Duplicate manifest ID')
        if hashlib.sha256(Path(item['source_path']).read_bytes()).hexdigest() != item['source_sha256']:
            raise ValueError('Review input bytes changed: ' + key)
        identity = json.dumps([key, item['source_sha256'], item['point_xy']], separators=(',', ':'))
        expected[key] = dict(candidate_id=hashlib.sha256(identity.encode()).hexdigest(),
                             input_sha256=item['source_sha256'], point_xy=item['point_xy'])
    dataset = hashlib.sha256(json.dumps([v['candidate_id'] for v in expected.values()]).encode()).hexdigest()
    if (payload.get('schema') != 'point-surface-human-review-v1' or payload.get('dataset_id') != dataset
            or payload.get('accepted_for_training') is not False or payload.get('old_development_data') is not True):
        raise ValueError('Review dataset or role mismatch')
    records = {}
    for record in payload['records']:
        key = record['image_id']
        if key in records or key not in expected:
            raise ValueError('Duplicate or unknown review ID')
        if any(record.get(k) != v for k, v in expected[key].items()):
            raise ValueError('Reviewed point identity changed: ' + key)
        if (record.get('actor_kind') != 'human' or record.get('accepted_for_training') is not False
                or record.get('status') != 'confirmed' or record.get('human_confirmed') is not True
                or type(record.get('revision')) is not int or record['revision'] < 1
                or not isinstance(record.get('history'), list)):
            raise ValueError('Explicit human confirmation required')
        if (record.get('choice') not in ('supported', 'unsupported', 'unknown')
                or record.get('eye_localizable_input') not in ('yes', 'no', 'unknown')
                or record.get('part') not in ('eye', 'head', 'body', 'unknown')):
            raise ValueError('Invalid review choices')
        confirmed = datetime.fromisoformat(record['confirmed_at_utc'].replace('Z', '+00:00'))
        if confirmed.tzinfo is None:
            raise ValueError('Confirmation time requires timezone')
        records[key] = record
    if set(records) != set(expected):
        raise ValueError('Review is incomplete')
    return payload, records


def annotate_surface(report, records):
    """Bind decisions only to exact points; caller verifies images with load_review.

    Strict geometry and eye counts stay intact. Surface support never supplies
    an eye location, and a moved point cannot inherit an old human decision.
    """
    counts = Counter(matched=0, supported=0, unsupported=0, unknown=0,
                     unassessed_eye_supported=0, unassessed_eye_unsupported=0)
    for row in report['detail']:
        decision = records.get(row['image_id'])
        chosen = row['selected']
        if not decision or chosen is None or chosen['point_xy'] != decision['point_xy']:
            continue
        counts['matched'] += 1
        counts[decision['choice']] += 1
        if chosen['kind'] == 'eye' and not row['eye_known']:
            if decision['choice'] in ('supported', 'unsupported'):
                counts['unassessed_eye_' + decision['choice']] += 1
    report['human_surface'] = dict(counts)
    report['human_surface']['unreviewed_eye_selections'] = (
        report['counts']['eye_unassessed_selected'] - counts['unassessed_eye_supported'])
    return report
