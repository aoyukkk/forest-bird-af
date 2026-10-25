"""Train native head copies using a locked reviewed dataset and cached backbone.

CUDA and the caller-supplied pinned native package are required. No production
annotation writes, remote jobs, alternate backbone, or deployment are performed.
"""
import argparse
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import copy
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from e7_backend import Backend, BODY_SHA
from z8_probe_labels import native_tables
from z8_trainable_heads import TrainableHeads, apply_body_copy, HEAD_BATCHES
from z8_training_targets import target_builder, negative_builder, partial_loss, records_to_predictions, match_metrics, background_eye_masks, regional_eye_errors, local_eye_supervision


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def emit(obj):
    print(json.dumps(obj, ensure_ascii=True), flush=True)


def batch_features(samples):
    return {k: torch.cat([s['features'][k] for s in samples], dim=0) for k in samples[0]['features']}


def cpu_heads(outputs):
    return {k: v.detach().cpu().numpy().astype('<f2').view('<u2').copy() for k, v in outputs.items()}


def predict(model, backend, samples, size, baseline=False):
    predictions, records, buffers = {}, {}, {}
    for start in range(0, len(samples), size):
        batch = samples[start:start + size]
        with torch.no_grad():
            heads = cpu_heads({k: torch.cat([s['heads'][k] for s in batch]) for k in ('fine', 'coarse')}) if baseline else cpu_heads(model(batch_features(batch)))
        for n, sample in enumerate(batch):
            single = {k: v[n] for k, v in heads.items()}
            report, packed = backend.decode(single)
            ident = sample['image_id']
            records[ident] = report['records']
            predictions[ident] = records_to_predictions(report['records'])
            buffers[ident] = packed
    metric, detail = match_metrics(samples, predictions)
    loose, _ = match_metrics(samples, predictions, box_iou=.3, eye_pixels=8.)
    return dict(metrics=metric, loose_metrics=loose, detail=detail, records=records), buffers


def allowed_selection(metrics, baseline):
    # Validation-only amendment before trial 4: native duplicate-head errors
    # motivated an additional F1 regression guard. Test remains unopened.
    return all(metrics[k]['recall'] >= baseline[k]['recall'] - .05 and metrics[k]['f1'] >= baseline[k]['f1'] - .03 for k in ('bird', 'head', 'eye'))


def gradient_masks(model, mode):
    if mode == 'all':
        return {}
    masks = {}
    for i, event in enumerate(model.events):
        name = next(k for k, batches in HEAD_BATCHES.items() if event['batch'] in batches)
        offset = HEAD_BATCHES[name].index(event['batch']) * 16
        channels = 33 if name == 'coarse' else 22
        allowed = torch.tensor([offset + row < channels and ((offset + row) % 11 in (7, 8) or
                                (mode == 'eye-small-anchor' and name == 'fine' and offset + row < 10))
                                for row in range(16)], device=model.weights[i].device)
        masks['weights.' + str(i)] = allowed[:, None].expand_as(model.weights[i])
        if str(i) in model.biases:
            masks['biases.' + str(i)] = allowed
    return masks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', required=True, type=Path)
    p.add_argument('--upstream', required=True, type=Path)
    p.add_argument('--workspace', required=True, type=Path)
    p.add_argument('--z8-package', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--epochs', type=int, default=30)
    p.add_argument('--batch-size', type=int, default=32)
    p.add_argument('--lr', type=float, default=.0003)
    p.add_argument('--preservation', type=float, default=1.)
    p.add_argument('--competition', type=float, default=0.)
    p.add_argument('--update-mode', choices=['all', 'eye-class-only', 'eye-small-anchor'], default='all')
    p.add_argument('--patience', type=int, default=8)
    p.add_argument('--min-epochs', type=int, default=0)
    p.add_argument('--initial-head', type=Path)
    p.add_argument('--background-weight', type=float, default=0.)
    p.add_argument('--background-topk', type=int, default=16)
    p.add_argument('--background-margin', type=float, default=16.)
    p.add_argument('--precision-guard', action='store_true')
    p.add_argument('--head-local-weight', type=float, default=0.)
    p.add_argument('--head-local-radius', type=float, default=8.)
    a = p.parse_args()
    if not torch.cuda.is_available():
        p.error('CUDA required; no alternate backend')
    root, out = a.dataset.resolve(), a.output.resolve()
    if any(out.is_relative_to(v.resolve()) for v in (a.upstream, a.workspace, Path(__file__).parents[2])):
        p.error('Output must be outside original packages, annotations and public repository')
    lock = json.loads((root / 'split-lock.json').read_text(encoding='utf-8'))
    dataset_bytes = (root / 'dataset.json').read_bytes()
    if sha(dataset_bytes) != lock['dataset_sha256']:
        raise ValueError('Dataset lock mismatch')
    cache = json.loads((root / 'cache-report.json').read_text(encoding='utf-8'))
    if not cache['passed']:
        raise ValueError('Feature parity gate has not passed')
    out.mkdir(parents=True, exist_ok=False)
    source_names = ['train_z8_heads.py', 'z8_training_targets.py', 'z8_trainable_heads.py', 'e7_backend.py', 'z8_probe_labels.py']
    (out / 'executed-code').mkdir()
    hashes = {}
    for name in source_names:
        raw = Path(__file__).with_name(name).read_bytes()
        hashes[name] = sha(raw)
        (out / 'executed-code' / name).write_bytes(raw)
    config = dict(dataset_sha256=sha(dataset_bytes), dataset=str(root), python=sys.executable, torch=torch.__version__, gpu=torch.cuda.get_device_name(),
                  epochs=a.epochs, batch_size=a.batch_size, lr=a.lr, preservation=a.preservation, competition=a.competition, patience=a.patience, seed=744,
                  target_assignment='size mismatch plus frozen-native geometry affinity',
                  update_mode=a.update_mode,
                  initial_head_sha256=sha(a.initial_head.read_bytes()) if a.initial_head else None,
                  background_weight=a.background_weight, background_topk=a.background_topk, background_margin=a.background_margin,
                  precision_guard=a.precision_guard,
                  head_local_weight=a.head_local_weight, head_local_radius=a.head_local_radius,
                  min_epochs=a.min_epochs,
                  source_hashes=hashes, backbone='frozen exact native resource744', backward='STE for FP16 storage and integer dot/add; approximate gradients',
                  trainable='original 8784 head parameters only', postprocessor='pinned native consumer; all original thresholds and tables unchanged',
                  selection='maximize validation macro F1 at IoU .5 / eye distance 4px, constrain each part recall drop <= .05 and F1 drop <= .03 absolute; amended on val before trial 4/test opening',
                  annotation_limits='Z8-assisted human labels, no verified multi-bird associations; part-unlabelled images ignored for that part precision',
                  supervision='bird operational union 0/4; eye union 2/3 with frozen latent branch, head 1, no invented eye-box size; teacher preserve other outputs; explicit absent only hard negatives')
    write(out / 'config.json', config)
    torch.manual_seed(744)
    random.seed(744)
    backend = Backend(a.upstream, 'cuda')
    model = TrainableHeads(backend)
    masks = gradient_masks(model, a.update_mode)
    config['updated_parameter_capacity'] = sum(int(masks[k].sum()) if k in masks else v.numel() for k, v in model.named_parameters())
    write(out / 'config.json', config)
    original = copy.deepcopy(model.state_dict())
    data = json.loads(dataset_bytes)
    tables = native_tables(a.upstream)
    samples = {s: [] for s in ('train', 'val', 'test')}
    audits = []
    for row in data['images']:
        # Do not load or derive targets from test features before final test.
        if row['split'] == 'test':
            continue
        payload = torch.load(root / 'features' / (row['image_id'] + '.pt'), map_location='cpu', weights_only=True)
        targets = target_builder(row, payload['heads'], tables)
        if a.update_mode == 'eye-small-anchor':
            targets = [t for t in targets if t['kind'] == 'eye']
        negative_targets = negative_builder(row, payload['heads'], tables, targets)
        sample = {**row, **payload, 'targets': targets, 'negative_targets': negative_targets}
        sample['background_masks'] = background_eye_masks(row, a.background_margin)
        sample['local_eye_supervision'] = local_eye_supervision(row)
        for target in targets:
            if sample['background_masks'][target['head']][target['anchor'], target['row'], target['col']]:
                raise ValueError('A positive target was labelled derived background')
        sample['features'] = {k: v.to('cuda') for k, v in payload['features'].items()}
        sample['heads'] = {k: v.to('cuda') for k, v in payload['heads'].items()}
        samples[row['split']].append(sample)
        audits.append({'image_id': row['image_id'], 'split': row['split'], 'targets': targets, 'negative_targets': negative_targets,
                       'derived_background_cells': {k: int(v.sum()) for k, v in sample['background_masks'].items()},
                       'derived_background_is_human_truth': False})
        audits[-1]['head_local_supervision'] = sample['local_eye_supervision']
    write(out / 'target-audit.json', audits)
    baseline, _ = predict(model, backend, samples['val'], a.batch_size, baseline=True)
    replay, _ = predict(model, backend, samples['val'], a.batch_size)
    if replay['records'] != baseline['records']:
        raise RuntimeError('Initial native head replay mismatch')
    # Confirm original C-consumer output agrees with the frozen human-review
    # baseline, before comparing trained outputs to labels from that baseline.
    for row in samples['val']:
        frozen = row['baseline']
        decoded = baseline['records'][row['image_id']]
        expected = [[int(round((p['box_input_xyxy'][0] + p['box_input_xyxy'][2]) / 2)), int(round((p['box_input_xyxy'][1] + p['box_input_xyxy'][3]) / 2)),
                     int(round(p['box_input_xyxy'][2] - p['box_input_xyxy'][0])), int(round(p['box_input_xyxy'][3] - p['box_input_xyxy'][1])), p['native_integer_score'], p['class_slot']] for p in frozen]
        if expected != decoded:
            raise RuntimeError('Frozen consumer baseline mismatch: ' + row['image_id'])
    write(out / 'validation-original.json', baseline)
    baseline_background = regional_eye_errors(samples['val'], baseline['records'], a.background_margin)
    write(out / 'validation-background-original.json', baseline_background)
    emit({'stage': 'validation-original', 'metrics': baseline['metrics']})
    optimizer = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.)
    best_score = baseline['metrics']['macro_f1']
    best_epoch = 0
    best = copy.deepcopy(original)
    parent_metrics = None
    if a.initial_head:
        model.load_state_dict(torch.load(a.initial_head, map_location='cuda', weights_only=True))
        for name, value in model.named_parameters():
            if name in masks and not torch.equal(value.detach()[~masks[name]], original[name][~masks[name]]):
                raise ValueError('Initial checkpoint changed currently frozen parameters')
        parent_metrics, _ = predict(model, backend, samples['val'], a.batch_size)
        write(out / 'validation-parent.json', parent_metrics)

    def eligible_result(result):
        m = result['metrics']
        ok = allowed_selection(m, baseline['metrics'])
        if a.precision_guard:
            bg = regional_eye_errors(samples['val'], result['records'], a.background_margin)
            ok = ok and m['eye']['precision'] >= baseline['metrics']['eye']['precision'] and bg['derived_background_eye_candidates'] <= baseline_background['derived_background_eye_candidates']
        return ok

    if parent_metrics and eligible_result(parent_metrics) and parent_metrics['metrics']['macro_f1'] > best_score:
        best_score = parent_metrics['metrics']['macro_f1']
        best_epoch = -1
        best = copy.deepcopy(model.state_dict())
        write(out / 'validation-best.json', parent_metrics)
        torch.save({k: v.cpu() for k, v in best.items()}, out / 'best-head.pt')
    history = []
    no_gain = 0
    start_time = time.perf_counter()
    train = samples['train']
    for epoch in range(1, a.epochs + 1):
        stamp = time.perf_counter()
        order = list(range(len(train)))
        random.shuffle(order)
        losses, components, gradients = [], [], []
        for start in range(0, len(order), a.batch_size):
            batch = [train[n] for n in order[start:start + a.batch_size]]
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch_features(batch))
            loss, component = partial_loss(outputs, batch, a.preservation, a.competition, a.background_weight, a.background_topk, a.head_local_weight, a.head_local_radius)
            if not torch.isfinite(loss):
                raise RuntimeError('Nonfinite training loss')
            loss.backward()
            for name, parameter in model.named_parameters():
                if name in masks and parameter.grad is not None:
                    parameter.grad.mul_(masks[name])
            grads = [p.grad for p in model.parameters() if p.grad is not None]
            if not grads or any(not torch.isfinite(g).all() for g in grads):
                raise RuntimeError('Nonfinite or missing gradient')
            gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            losses.append(float(loss.detach()))
            components.append(component)
            gradients.append(float(gradient_norm))
        metrics, _ = predict(model, backend, samples['val'], a.batch_size)
        m = metrics['metrics']
        eligible = eligible_result(metrics)
        background_metric = regional_eye_errors(samples['val'], metrics['records'], a.background_margin)
        improved = eligible and m['macro_f1'] > best_score + 1e-8
        if improved:
            best_score, best_epoch = m['macro_f1'], epoch
            best = copy.deepcopy(model.state_dict())
            torch.save({k: v.cpu() for k, v in best.items()}, out / 'best-head.pt')
            write(out / 'validation-best.json', metrics)
            no_gain = 0
        else:
            no_gain += 1
        record = dict(epoch=epoch, train_loss=float(np.mean(losses)), train_components={k: float(np.mean([c[k] for c in components])) for k in components[0]},
                      gradient_norm=float(np.mean(gradients)), val_macro_f1=m['macro_f1'], val={k: m[k] for k in ('bird', 'head', 'eye')},
                      recall_guard_passed=eligible, derived_background=background_metric, selected=improved, best_epoch=best_epoch, seconds=time.perf_counter() - stamp)
        history.append(record)
        write(out / 'history.json', history)
        torch.save({'epoch': epoch, 'state_dict': model.state_dict(), 'optimizer': optimizer.state_dict(), 'rng': random.getstate(), 'best_epoch': best_epoch}, out / 'last-checkpoint.pt')
        emit(record)
        if no_gain >= a.patience and epoch >= a.min_epochs:
            break
    model.load_state_dict(best)
    report = dict(training_completed=True, selected_epoch=best_epoch, validation_improved=best_epoch != 0,
                  refinement_improved_over_parent=bool(parent_metrics and best_score > parent_metrics['metrics']['macro_f1']),
                  validation_macro_f1_before=baseline['metrics']['macro_f1'], validation_macro_f1_after=best_score,
                  epochs_completed=len(history), elapsed_seconds=time.perf_counter() - start_time,
                  peak_cuda_allocated_mb=torch.cuda.max_memory_allocated() / 2**20, peak_cuda_reserved_mb=torch.cuda.max_memory_reserved() / 2**20,
                  production_annotation_writes=0, remote_jobs=0, original_body_unchanged=sha((a.upstream / 'resource744.body.bin').read_bytes()) == BODY_SHA,
                  test_evaluated=False, camera_AF_verified=False)
    if best_epoch:
        final_reference = TrainableHeads(backend)
        reference_params = dict(final_reference.named_parameters())
        frozen_changed = sum(int((v.detach().half().view(torch.int16)[~masks[k]] != reference_params[k].detach().half().view(torch.int16)[~masks[k]]).sum()) for k, v in model.named_parameters() if k in masks)
        if frozen_changed:
            raise RuntimeError('Frozen parameter row changed')
        report['non_allowed_fp16_parameter_changes'] = frozen_changed
        report['body_export'] = model.export_body(a.upstream, out / 'resource744.finetuned.body.bin')
        # Explicitly read back the exported FP16 copy through the full native
        # graph, including original backbone and original postprocessor.
        reload = Backend(a.upstream, 'cuda')
        apply_body_copy(reload, out / 'resource744.finetuned.body.bin')
        checks = []
        sys.path.insert(0, str(a.z8_package.resolve()))
        from z8models.native_post import decode_raw
        for sample in samples['val'][:3]:
            with Image.open(a.workspace / 'images' / (sample['image_id'] + '.png')) as im:
                raw = np.asarray(im).transpose(2, 0, 1).copy().tobytes()
            native = reload.infer(raw)['heads']
            with torch.no_grad():
                replay = cpu_heads(model(sample['features']))
            diffs = {k: int(np.count_nonzero(native[k] != replay[k][0])) for k in native}
            if any(diffs.values()):
                raise RuntimeError('Exported full native graph differs from head cache')
            c_report, packed = reload.decode(native)
            ba2 = decode_raw(packed, 744)
            decoded = [[*x['center_xy'], *x['size_wh'], x['score_milli'], x['ipu_class_id']] for x in ba2['candidates']]
            if decoded != c_report['records']:
                raise RuntimeError('C consumer and original BA2 instruction interpreter differ')
            checks.append(dict(image_id=sample['image_id'], bit_differences=diffs, original_BA2_return_code=ba2['return_code'], candidates=len(decoded)))
        report['roundtrip'] = checks
    write(out / 'report.json', report)
    emit({'stage': 'complete', **report})


if __name__ == '__main__':
    main()
