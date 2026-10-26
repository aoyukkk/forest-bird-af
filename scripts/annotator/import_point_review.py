"""Validate an offline human point-review export and preserve it outside Git."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_export(payload, manifest, verify_inputs=True):
    """Bind decisions to the complete frozen cohort; never promote training labels."""
    expected = {}
    for source in manifest['records']:
        image_id = source['image_id']
        if image_id in expected:
            raise ValueError('Duplicate manifest ID')
        identity = json.dumps([image_id, source['source_sha256'], source['point_xy']], separators=(',', ':'))
        expected[image_id] = dict(candidate_id=sha256(identity.encode()),
                                  input_sha256=source['source_sha256'], point_xy=source['point_xy'])
        if verify_inputs and sha256(Path(source['source_path']).read_bytes()) != source['source_sha256']:
            raise ValueError('Frozen input changed: ' + image_id)
    dataset_id = sha256(json.dumps([x['candidate_id'] for x in expected.values()]).encode())
    if (not expected or payload.get('schema') != 'point-surface-human-review-v1'
            or payload.get('dataset_id') != dataset_id
            or payload.get('accepted_for_training') is not False
            or payload.get('old_development_data') is not True):
        raise ValueError('Export schema, dataset or usage boundary mismatch')
    records = payload.get('records')
    if not isinstance(records, list) or len(records) != len(expected):
        raise ValueError('Export must cover the complete cohort, including drafts')
    seen = set()
    counts = Counter()
    confirmed_ids, pending_ids = [], []
    for record in records:
        image_id = record.get('image_id')
        if image_id not in expected or image_id in seen:
            raise ValueError('Unexpected or duplicate export ID')
        seen.add(image_id)
        frozen = expected[image_id]
        revision = record.get('revision')
        history = record.get('history')
        if (type(revision) is not int or not 0 <= revision <= 100000
                or not isinstance(history, list) or len(history) != revision):
            raise ValueError('Invalid revision history: ' + image_id)
        for index, value in enumerate([*history, record]):
            point = value.get('point_xy')
            if (value.get('image_id') != image_id
                    or any(value.get(k) != frozen[k] for k in frozen)
                    or not isinstance(point, list) or len(point) != 2
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in point)
                    or type(value.get('revision')) is not int or value['revision'] != index):
                raise ValueError('Input, point or history identity mismatch: ' + image_id)
            if value.get('actor_kind') != 'human' or value.get('accepted_for_training') is not False:
                raise ValueError('Invalid actor or training promotion: ' + image_id)
            if (value.get('eye_localizable_input') not in ('yes', 'no', 'unknown')
                    or value.get('part') not in ('eye', 'head', 'body', 'unknown')
                    or not isinstance(value.get('note'), str) or len(value['note']) > 2000):
                raise ValueError('Invalid review fields: ' + image_id)
            if value.get('status') == 'confirmed':
                if value.get('human_confirmed') is not True or value.get('choice') not in ('supported', 'unsupported', 'unknown'):
                    raise ValueError('Confirmation is incomplete: ' + image_id)
                try:
                    stamp = datetime.fromisoformat(value['confirmed_at_utc'].replace('Z', '+00:00'))
                    if stamp.utcoffset() is None:
                        raise ValueError('Timezone required')
                except (KeyError, TypeError, ValueError, AttributeError) as exc:
                    raise ValueError('Invalid confirmation timestamp: ' + image_id) from exc
            elif value.get('status') != 'draft' or value.get('human_confirmed') is not False:
                raise ValueError('Draft cannot count as confirmation: ' + image_id)
        if record['status'] == 'confirmed':
            counts[record['choice']] += 1
            confirmed_ids.append(image_id)
        else:
            pending_ids.append(image_id)
    return dict(dataset_id=dataset_id, total=len(records), human_confirmed=len(confirmed_ids),
                counts={k: counts[k] for k in ('supported', 'unsupported', 'unknown')},
                pending_ids=pending_ids, accepted_for_training=0,
                old_development_data=True, production_annotation_writes=0)


def import_export(source, workspace, output):
    repo = Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(repo) or output.exists():
        raise ValueError('Use a new import directory outside public Git')
    raw = source.read_bytes()
    payload = json.loads(raw.decode('utf-8-sig'))
    manifest = json.loads((workspace / 'manifest.json').read_text(encoding='utf-8-sig'))
    summary = validate_export(payload, manifest)
    summary['export_sha256'] = sha256(raw)
    summary['schema'] = 'validated-point-surface-human-import-v1'
    output.mkdir(parents=True, exist_ok=False)
    (output / 'export.json').write_bytes(raw)
    if (output / 'export.json').read_bytes() != raw:
        raise OSError('Export copy readback failed')
    (output / 'validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(import_export(args.source, args.workspace, args.output)))


if __name__ == '__main__':
    main()
