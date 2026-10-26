"""Evaluate one validation-selected student on a locked public held-out test.

Native packages remain external. Original and repaired native outputs are
cross-checked against the BA2 consumer. No test threshold/model fitting occurs.
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from bird_parts_model import BirdDataset, as_raw, build_model, collate, decode
from train_bird_parts import THRESHOLDS, metric_rows, selection_diagnostic
from z8_training_targets import match_metrics, records_to_predictions
from e7_backend import Backend, BODY_SHA
from z8_trainable_heads import TrainableHeads, head_events, apply_body_copy


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_native_packet(package, job):
    """Independent CPU instruction execution; never changes predictions."""
    sys.path.insert(0, package)
    from z8models.native_post import decode_raw
    result = decode_raw(bytes.fromhex(job['packed_hex']), 744)
    actual = [[*x['center_xy'], *x['size_wh'], x['score_milli'], x['ipu_class_id']]
              for x in result['candidates']]
    if actual != job['expected']:
        raise RuntimeError('Native postprocessor parity failure: ' + job['key'])
    return job['key']


def capture_native_batch(backend, raws):
    events = head_events(backend.model)
    mapping = {id(e['weight']): i for i, e in enumerate(events)}
    captures = {}
    original = backend.model.dot

    def tapped(weight, value):
        if id(weight) in mapping:
            captures[mapping[id(weight)]] = value.detach().clone()
        return original(weight, value)

    backend.model.dot = tapped
    try:
        outputs = backend.infer_many(raws)
    finally:
        del backend.model.dot
    if len(captures) != len(events):
        raise RuntimeError('Incomplete batched head captures')
    return {i: value.clone() for i, value in captures.items()}, outputs['heads']


def normalized_native(records):
    return {key: [dict(p, score=p['score'] / 1000.) for p in records_to_predictions(value)] for key, value in records.items()}


def fixed_score(rows, predictions, thresholds):
    selected = {k: [p for p in v if p['score'] >= thresholds[p['kind']]] for k, v in predictions.items()}
    truth = metric_rows(rows)
    strict, detail = match_metrics(truth, selected)
    loose, _ = match_metrics(truth, selected, box_iou=.3, eye_pixels=8)
    tight, _ = match_metrics(truth, selected, eye_pixels=2)
    return dict(metrics=strict, loose_metrics=loose, eye_2px=tight['eye'],
                bird_eye_macro_f1=(strict['bird']['f1'] + strict['eye']['f1']) / 2,
                thresholds=thresholds, threshold_fitting_on_test=False,
                selection_diagnostic=selection_diagnostic(truth, selected),
                predictions=predictions, detail=detail,
                head_test_truth=False, source_landmark_visibility_used=True)


def calibrate_native(rows, records):
    predictions = normalized_native(records)
    curves = []
    for threshold in THRESHOLDS:
        selected = {k: [p for p in v if p['score'] >= threshold] for k, v in predictions.items()}
        metric, _ = match_metrics(rows, selected)
        curves.append(dict(threshold=threshold, metrics=metric))
    thresholds = {kind: max(curves, key=lambda p: (p['metrics'][kind]['f1'], p['threshold']))['threshold']
                  for kind in ('bird', 'head', 'eye')}
    selected = {k: [p for p in v if p['score'] >= thresholds[p['kind']]] for k, v in predictions.items()}
    metric, _ = match_metrics(rows, selected)
    return dict(thresholds=thresholds, metrics=metric, curve=curves,
                limit='native consumer floor remains in force; calibration only filters emitted proposals')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--public-test', type=Path, required=True)
    parser.add_argument('--community', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--z8-package', type=Path, required=True)
    parser.add_argument('--view', choices=['original', 'scale-stress'], default='original')
    parser.add_argument('--parity-workers', type=int, default=8)
    args = parser.parse_args()
    root = args.run_root.resolve()
    if root.is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error('Evaluation artifacts must stay outside public repository')
    selection = read(root / 'yolo-selection-before-test.json')
    student_path = Path(selection['trial_root']) / selection['selected'] / 'best.pt'
    if sha(student_path) != selection['sha256']:
        raise RuntimeError('Selected student changed after validation')
    source = read(args.public_test)
    rows = source['records']
    community = read(args.community)
    validation = [r for r in community['images'] if r['split'] == 'val']
    old_root = args.community.parent.parent
    original_val = read(old_root / 'trial_005/validation-original.json')
    repaired_val = read(root / 'native_001_mask_fix/validation-best.json')
    calibration = {
        'original': calibrate_native(validation, original_val['records']),
        'repaired': calibrate_native(validation, repaired_val['records'])}
    output = root / ('public-test-results' if args.view == 'original' else 'public-scale-stress-results')
    output.mkdir(exist_ok=True)
    write(output / 'native-validation-calibration.json', calibration)
    repaired_body = root / 'native_001_mask_fix/resource744.finetuned.body.bin'
    lock = dict(dataset_sha256=sha(args.public_test), original_body_sha256=BODY_SHA,
                repaired_body_sha256=sha(repaired_body), student_sha256=sha(student_path),
                input_sha256={r['image_id']: sha(Path(r['path'])) for r in rows},
                thresholds={'original': calibration['original']['thresholds'],
                            'repaired': calibration['repaired']['thresholds'], 'student': selection['thresholds']},
                selected_before_test=True, old_community_test_evaluated=False)
    lock_path = output / 'test-opened.json'
    if lock_path.exists():
        if read(lock_path) != lock:
            raise RuntimeError('Test lock already exists for different assets/thresholds')
    else:
        write(lock_path, lock)
    # Only selected/frozen model assets are used after this point.
    if not 1 <= args.parity_workers <= 32:
        parser.error('--parity-workers must be between 1 and 32')
    torch.set_num_threads(4)
    if not (output / 'native-predictions.json').exists():
        forward_path = output / 'native-forward.json'
        if not forward_path.exists():
            generate_native_forward(args, rows, root, output, repaired_body)
        forward = read(forward_path)
        if sha(forward_path) != (output / 'native-forward.sha256').read_text().strip():
            raise RuntimeError('Saved native forward checkpoint changed')
        progress_path = output / 'native-parity-progress.json'
        passed = set(read(progress_path)['verified_packets']) if progress_path.exists() else set()
        jobs = forward.pop('parity_jobs')
        if not passed.issubset({j['key'] for j in jobs}):
            raise RuntimeError('Unexpected parity checkpoint keys')
        started = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.parity_workers) as pool:
            pending = [pool.submit(verify_native_packet, str(args.z8_package.resolve()), j)
                       for j in jobs if j['key'] not in passed]
            for future in as_completed(pending):
                passed.add(future.result())
                if len(passed) % 10 == 0 or len(passed) == len(jobs):
                    write(progress_path, dict(verified_packets=sorted(passed), total=len(jobs)))
                    print(json.dumps(dict(stage='native-BA2-parity', packets=len(passed), total=len(jobs))), flush=True)
        if len(passed) != 2 * len(rows):
            raise RuntimeError('Incomplete native instruction checks')
        for entry in forward['parity']:
            entry['ba2_parity'] = True
        forward['parity_resume_segment_seconds'] = time.perf_counter() - started
        forward['parity_workers'] = args.parity_workers
        write(output / 'native-predictions.json', forward)
    native = read(output / 'native-predictions.json')
    if not (output / 'student-predictions.json').exists():
        model = build_model('n', root / 'pretrained/n-initial-state.pt').cuda()
        model.load_state_dict(torch.load(student_path, map_location='cuda', weights_only=True)['state_dict'])
        model.eval(); predictions = {}
        dataset = BirdDataset(rows)
        with torch.no_grad():
            for start in range(0, len(rows), 32):
                images, samples = collate([dataset[n] for n in range(start, min(start + 32, len(rows)))])
                with torch.autocast('cuda', dtype=torch.float16):
                    raw = as_raw(model(images.cuda()))
                for row, pred in zip(samples, decode(raw, model.model[-1].stride)):
                    predictions[row['image_id']] = pred
        write(output / 'student-predictions.json', predictions)
    student = read(output / 'student-predictions.json')
    report = {'original': fixed_score(rows, native['original'], lock['thresholds']['original']),
              'repaired': fixed_score(rows, native['repaired'], lock['thresholds']['repaired']),
              'student': fixed_score(rows, student, lock['thresholds']['student']),
              'original_native_settings': fixed_score(rows, native['original'], {k: 0 for k in ('bird', 'head', 'eye')}),
              'repaired_native_settings': fixed_score(rows, native['repaired'], {k: 0 for k in ('bird', 'head', 'eye')}),
              'limits': ['public-dataset domain test, not new independent forest-bird AF data',
                         'no human head boxes in this test', 'vendor/pretrained exposure to CUB unknown',
                         'source-visible eye eligibility uses declared input-scale heuristic',
                         'focal-bird annotations do not certify all other birds absent'],
              'test_images': len(rows), 'test_eye_points': sum(len(r['eyes']) for r in rows),
              'input_view': args.view, 'paired_views_are_not_independent_images': True,
              'no_training_after_test': True, 'old_community_test_evaluated': False,
              'camera_AF_verified': False, 'all_native_BA2_parity_passed': all(p['ba2_parity'] for p in native['parity'])}
    write(output / 'report.json', report)
    print(json.dumps({'stage': 'public-test-complete', 'models': {k: {'bird': report[k]['metrics']['bird'], 'eye': report[k]['metrics']['eye']} for k in ('original', 'repaired', 'student')}}), flush=True)


def generate_native_forward(args, rows, root, output, repaired_body):
    """Batch transport preserves the physical replay; verify singleton parity."""
    backend = Backend(args.upstream, 'cuda')
    frozen = TrainableHeads(backend)
    repaired = TrainableHeads(backend)
    repaired.load_state_dict(torch.load(root / 'native_001_mask_fix/best-head.pt', map_location='cuda', weights_only=True))
    predictions = {'original': {}, 'repaired': {}}
    parity, jobs, singleton_samples = [], [], []
    start = time.perf_counter()
    with torch.no_grad():
        for first in range(0, len(rows), 32):
            batch = rows[first:first + 32]
            raws = []
            for row in batch:
                with Image.open(row['path']) as im:
                    raws.append(np.asarray(im.convert('RGB')).transpose(2, 0, 1).copy().tobytes())
            features, originals = capture_native_batch(backend, raws)
            replay, corrected = frozen(features), repaired(features)
            fixed = {k: v.cpu().numpy().astype('<f2').view('<u2').copy() for k, v in corrected.items()}
            replay_bits = {k: v.cpu().numpy().astype('<f2').view('<u2') for k, v in replay.items()}
            for n, (row, raw) in enumerate(zip(batch, raws)):
                bits = {k: int(np.count_nonzero(replay_bits[k][n] != originals[k][n])) for k in replay}
                if any(bits.values()):
                    raise RuntimeError('Original head cache parity failure')
                expected_original = {k: v[n].copy() for k, v in originals.items()}
                expected_fixed = {k: v[n].copy() for k, v in fixed.items()}
                for name, heads in [('original', expected_original), ('repaired', expected_fixed)]:
                    report, packed = backend.decode(heads)
                    jobs.append(dict(key=row['image_id'] + '/' + name, packed_hex=packed.hex(), expected=report['records']))
                    predictions[name][row['image_id']] = [dict(p, score=p['score'] / 1000.) for p in records_to_predictions(report['records'])]
                if len(singleton_samples) < 3:
                    singleton_samples.append((raw, expected_original, expected_fixed))
                parity.append(dict(image_id=row['image_id'], original_head_bit_differences=bits, ba2_parity=False))
            print(json.dumps(dict(stage='native-public-test-forward', images=first + len(batch), total=len(rows))), flush=True)
        for raw, expected, _ in singleton_samples:
            actual = backend.infer(raw)['heads']
            if any(np.any(actual[k] != expected[k]) for k in expected):
                raise RuntimeError('Original batch/singleton parity failure')
        reload = Backend(args.upstream, 'cuda')
        apply_body_copy(reload, repaired_body)
        for raw, _, expected in singleton_samples:
            actual = reload.infer(raw)['heads']
            if any(np.any(actual[k] != expected[k]) for k in expected):
                raise RuntimeError('Repaired exported body/batch parity failure')
    forward_path = output / 'native-forward.json'
    write(forward_path, dict(**predictions, parity=parity, parity_jobs=jobs,
                            forward_and_export_checks_seconds=time.perf_counter() - start,
                            exported_body_full_reload_samples=len(singleton_samples),
                            original_batch_singleton_parity_samples=len(singleton_samples), batch_size=32))
    (output / 'native-forward.sha256').write_text(sha(forward_path), encoding='ascii')
    del backend, reload, frozen, repaired
    torch.cuda.empty_cache()


if __name__ == '__main__':
    main()
