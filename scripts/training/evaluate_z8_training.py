"""One locked test evaluation after validation-only checkpoint selection.

Resume is allowed only for the identical selected checkpoint. Original native
instructions validate both original and tuned test outputs. No threshold fit.
"""
import argparse
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import hashlib
import importlib
import json
import sqlite3
import sys
import time
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def bootstrap_groups(original, updated):
    groups = defaultdict(list)
    for i, before in enumerate(original['detail']):
        after = updated['detail'][i]
        if before['image_id'] != after['image_id']:
            raise ValueError('Metric row mismatch')
        groups[before['leakage_group_id']].append((before, after))

    def score(rows, side):
        parts = {k: Counter() for k in ('bird', 'head', 'eye')}
        for pair in rows:
            for k, counts in pair[side]['parts'].items():
                parts[k].update(counts)
        f1 = [2 * v['tp'] / max(1, 2 * v['tp'] + v['fp'] + v['fn']) for v in parts.values()]
        return sum(f1) / 3

    rng = np.random.default_rng(744)
    names = sorted(groups)
    differences = []
    for _ in range(5000):
        rows = [pair for g in rng.choice(names, len(names), replace=True) for pair in groups[g]]
        differences.append(score(rows, 1) - score(rows, 0))
    return {'engineering_groups': len(names), 'resamples': len(differences),
            'delta_macro_f1_percentile_95': np.percentile(differences, [2.5, 97.5]).tolist(),
            'limitation': 'Few conservative source/visual groups; assisted labels, not an independently blinded camera AF benchmark.'}


def eye_error_breakdown(samples, records, converter):
    counts = Counter()
    for row in samples:
        truth = [t for t in row['document']['items'] if t['kind'] == 'eye']
        if not truth and row['document']['presence'] != 'absent':
            continue
        centers = [t['point_xy'] if t['point_xy'] is not None else [(t['box_xyxy'][0] + t['box_xyxy'][2]) / 2, (t['box_xyxy'][1] + t['box_xyxy'][3]) / 2] for t in truth]
        used = set()
        for prediction in sorted(converter(records[row['image_id']]), key=lambda p: -p['score']):
            if prediction['kind'] != 'eye':
                continue
            distances = sorted((math.dist(prediction['point_xy'], t), n) for n, t in enumerate(centers))
            free = [(d, n) for d, n in distances if d <= 4 and n not in used]
            if free:
                used.add(free[0][1]); counts['true_positive'] += 1
            elif distances and distances[0][0] <= 4:
                counts['duplicate_near_already_matched_eye'] += 1
            else:
                counts['unmatched_location_false_positive'] += 1
    return dict(counts)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--trial', type=Path, required=True)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--z8-package', type=Path, required=True)
    p.add_argument('--workspace', type=Path, required=True)
    a = p.parse_args()
    config = json.loads((a.trial / 'config.json').read_text(encoding='utf-8'))
    report = json.loads((a.trial / 'report.json').read_text(encoding='utf-8'))
    if not report['validation_improved'] or len(report.get('roundtrip', [])) != 3:
        raise RuntimeError('Validation/roundtrip gates did not pass')
    for name, digest in config['source_hashes'].items():
        if sha((a.trial / 'executed-code' / name).read_bytes()) != digest:
            raise ValueError('Frozen executed source changed')
    sys.path.insert(0, str(a.trial / 'executed-code'))
    runner = importlib.import_module('train_z8_heads')
    from e7_backend import Backend, BODY_SHA
    from z8_trainable_heads import TrainableHeads
    from z8_training_targets import records_to_predictions
    data_bytes = (a.dataset / 'dataset.json').read_bytes()
    if sha(data_bytes) != config['dataset_sha256']:
        raise ValueError('Locked dataset changed')
    checkpoint = a.trial / 'best-head.pt'
    selected_sha = sha(checkpoint.read_bytes())
    lock_path = a.dataset / 'test-opened.json'
    lock = {'selected_trial': str(a.trial.resolve()), 'selected_checkpoint_sha256': selected_sha,
            'selected_body_sha256': report['body_export']['updated_sha256'],
            'selection': 'validation only; original thresholds; one model selected before test open'}
    if lock_path.exists():
        if json.loads(lock_path.read_text(encoding='utf-8')) != lock:
            raise RuntimeError('Test lock belongs to another model; no test-driven replacement')
        if (a.trial / 'test-report.json').exists():
            print('Identical checkpoint already evaluated: ' + str(a.trial / 'test-report.json'))
            return
    else:
        write(lock_path, lock)
    started = time.perf_counter()
    backend = Backend(a.upstream, 'cuda')
    model = TrainableHeads(backend)
    reference = TrainableHeads(backend)
    model.load_state_dict(torch.load(checkpoint, map_location='cuda', weights_only=True))
    masks = runner.gradient_masks(model, config.get('update_mode', 'all'))
    parameter_check = {'float_master_changed': 0, 'fp16_values_changed': 0, 'non_allowed_fp16_values_changed': 0}
    originals = dict(reference.named_parameters())
    for name, value in model.named_parameters():
        before = originals[name]
        parameter_check['float_master_changed'] += int((value != before).sum())
        diff = value.detach().half().view(torch.int16) != before.detach().half().view(torch.int16)
        parameter_check['fp16_values_changed'] += int(diff.sum())
        if name in masks:
            parameter_check['non_allowed_fp16_values_changed'] += int(diff[~masks[name]].sum())
    if parameter_check['non_allowed_fp16_values_changed']:
        raise RuntimeError('A frozen parameter row changed')
    samples = []
    for row in json.loads(data_bytes)['images']:
        if row['split'] == 'test':
            payload = torch.load(a.dataset / 'features' / (row['image_id'] + '.pt'), map_location='cpu', weights_only=True)
            samples.append({**row, **payload, 'features': {k: v.to('cuda') for k, v in payload['features'].items()}})
    original, original_buffers = runner.predict(model, backend, samples, 32, baseline=True)
    updated, updated_buffers = runner.predict(model, backend, samples, 32)
    write(a.trial / 'test-original.json', original)
    write(a.trial / 'test-finetuned.json', updated)
    sys.path.insert(0, str(a.z8_package.resolve()))
    from z8models.native_post import decode_raw
    checks = []
    for sample in samples:
        ident = sample['image_id']
        for label, buffers, predictions in [('original', original_buffers, original), ('finetuned', updated_buffers, updated)]:
            decoded = decode_raw(buffers[ident], 744)
            records = [[*x['center_xy'], *x['size_wh'], x['score_milli'], x['ipu_class_id']] for x in decoded['candidates']]
            if records != predictions['records'][ident]:
                raise RuntimeError('Original BA2 interpreter parity failed: ' + ident + '/' + label)
        checks.append(ident)
        if len(checks) % 10 == 0:
            write(a.trial / 'test-native-parity-progress.json', {'passed': False, 'verified_images': checks})
            print(json.dumps({'stage': 'test-native-parity', 'completed': len(checks), 'total': len(samples)}), flush=True)
    write(a.trial / 'test-native-parity-progress.json', {'passed': True, 'verified_images': checks})
    # Logical comparison avoids mistaking SQLite page bookkeeping for label
    # changes. This does not write to the live database.
    live = sqlite3.connect((a.workspace / 'annotations.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
    snapshot = sqlite3.connect(a.dataset / 'annotations.snapshot.sqlite3')
    preserved = {}
    for table, columns in [('images', 'id,metadata,predictions'), ('z8_reviews', 'id,revision,document,updated'), ('z8_review_history', '*'), ('annotations', '*'), ('history', '*')]:
        before = snapshot.execute('SELECT ' + columns + ' FROM ' + table + ' ORDER BY 1').fetchall()
        after = live.execute('SELECT ' + columns + ' FROM ' + table + ' ORDER BY 1').fetchall()
        preserved[table] = dict(rows_before=len(before), rows_after=len(after), logically_identical=before == after)
    live.close(); snapshot.close()
    result = {'passed_native_parity': True, 'verified_original_and_finetuned_images': len(checks), 'selection_lock': lock,
              'original': original['metrics'], 'finetuned': updated['metrics'], 'original_loose': original['loose_metrics'], 'finetuned_loose': updated['loose_metrics'],
              'macro_f1_delta': updated['metrics']['macro_f1'] - original['metrics']['macro_f1'],
              'recall_guard_passed': runner.allowed_selection(updated['metrics'], original['metrics']),
              'quality_guard_passed': runner.allowed_selection(updated['metrics'], original['metrics']),
              'eye_error_breakdown': {'original': eye_error_breakdown(samples, original['records'], records_to_predictions), 'finetuned': eye_error_breakdown(samples, updated['records'], records_to_predictions)},
              'parameter_freeze_check': parameter_check,
              'group_bootstrap': bootstrap_groups(original, updated), 'production_data_preservation': preserved,
              'original_body_unchanged': sha((a.upstream / 'resource744.body.bin').read_bytes()) == BODY_SHA,
              'dedupe_unchanged': sha((a.workspace / 'dedupe/current.json').read_bytes()) == sha((a.dataset / 'dedupe.snapshot.json').read_bytes()),
              'seconds': time.perf_counter() - started, 'camera_AF_verified': False,
              'compute_change': 'No architectural/shape/instruction change; only original head FP16 weight/bias spans change.'}
    write(a.trial / 'test-report.json', result)
    print(json.dumps({'stage': 'test-complete', **result}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
