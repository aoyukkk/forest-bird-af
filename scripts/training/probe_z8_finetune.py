"""Run a bounded local, positive-only resource744 head fine-tuning smoke test.

No production annotation writes. Output weights must stay outside the public
repository. This validates an engineering path, not detection accuracy.
"""
import argparse
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from e7_backend import Backend, BODY_SHA
from z8_trainable_heads import TrainableHeads, capture_features, bits, apply_body_copy
from z8_probe_labels import adapt, assign, native_tables, loss_for


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', required=True, type=Path)
    p.add_argument('--z8-package', required=True, type=Path)
    p.add_argument('--workspace', required=True, type=Path)
    p.add_argument('--frozen-runs', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--parent-run', type=Path)
    p.add_argument('--ids', nargs='+', required=True)
    p.add_argument('--steps', type=int, default=12)
    p.add_argument('--learning-rate', type=float, default=.001)
    p.add_argument('--engineering-labels', action='store_true', help='Explicitly permit unreviewed labels for I/O testing only')
    a = p.parse_args()
    if not 1 <= len(a.ids) <= 4 or len(set(a.ids)) != len(a.ids) or not 1 <= a.steps <= 20:
        p.error('Bounded probe supports 1..4 distinct images and 1..20 steps')
    if not 0 < a.learning_rate <= .01:
        p.error('Use a learning rate in (0,.01]')
    out = a.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo) or out.is_relative_to(a.upstream.resolve()) or out.is_relative_to(a.z8_package.resolve()) or out.is_relative_to(a.workspace.resolve()):
        p.error('Experiment output must be separate from source packages, public repo and production annotations')
    out.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'stage': 'initializing', 'steps_requested': a.steps,
              'learning_rate': a.learning_rate, 'scope': 'frozen native backbone, original detection-head parameters only',
              'backward': 'explicit STE for quantized dot/add/storage; not exact integer derivatives',
              'parent_run': str(a.parent_run.resolve()) if a.parent_run else None,
              'annotation_quality_claim': False, 'accuracy_claim': False, 'camera_deployment': False,
              'production_annotation_writes': 0, 'engineering_labels_allowed': a.engineering_labels,
              'cases': [], 'training': [], 'roundtrip': [], 'code_sha256': {
                  f: sha(Path(__file__).with_name(f).read_bytes()) for f in
                  ['probe_z8_finetune.py', 'z8_trainable_heads.py', 'z8_probe_labels.py']}}

    def save(stage=None):
        if stage:
            report['stage'] = stage
        (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    def emit(row):
        print(json.dumps(row, ensure_ascii=True), flush=True)

    save()
    started = time.perf_counter()
    try:
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is required for this bounded probe; no silent fallback')
        torch.manual_seed(744)
        backend = Backend(a.upstream, 'cuda')
        model = TrainableHeads(backend)
        report.update(gpu=torch.cuda.get_device_name(), torch=torch.__version__,
                      body_sha256=sha((a.upstream / 'resource744.body.bin').read_bytes()),
                      trainable_parameter_count=sum(p.numel() for p in model.parameters()))
        if report['body_sha256'] != BODY_SHA:
            raise RuntimeError('Source model identity mismatch')
        tables = native_tables(a.upstream)
        report['native_anchor_tables'] = tables
        samples = []
        uri = (a.workspace / 'annotations.sqlite3').resolve().as_uri() + '?mode=ro'
        with sqlite3.connect(uri, uri=True) as c:
            label_count = c.execute('SELECT COUNT(*) FROM z8_reviews WHERE json_extract(document,\'$.status\')=\'confirmed\'').fetchone()[0]
            report['human_confirmed_correction_count'] = label_count
            for ident in a.ids:
                row = c.execute('SELECT metadata,predictions FROM images WHERE id=?', (ident,)).fetchone()
                if row is None:
                    raise RuntimeError('Unknown registered image: ' + ident)
                meta, preds = json.loads(row[0]), json.loads(row[1])
                record = c.execute('SELECT document FROM z8_reviews WHERE id=?', (ident,)).fetchone()
                if not record:
                    record = c.execute('SELECT document FROM annotations WHERE id=?', (ident,)).fetchone()
                if not record:
                    raise RuntimeError('No saved annotation, including no engineering label: ' + ident)
                doc = json.loads(record[0])
                png = (a.workspace / 'images' / (ident + '.png')).read_bytes()
                with Image.open(a.workspace / 'images' / (ident + '.png')) as im:
                    if im.size != (384, 256) or im.mode != 'RGB':
                        raise RuntimeError('Input dimensions or color mode changed')
                    raw = np.asarray(im).transpose(2, 0, 1).copy().tobytes()
                identity = doc['annotation_image']
                if sha(png) != meta['png_sha256'] or sha(raw) != meta['input_sha256'] or identity['sha256'] != meta['png_sha256'] or identity['input_chw_u8_sha256'] != meta['input_sha256']:
                    raise RuntimeError('Annotation/input identity mismatch')
                converted = adapt(doc, a.engineering_labels)
                targets = assign(converted, tables)
                if not targets:
                    raise RuntimeError('No supported targets: ' + ident)
                (out / (ident + '-label.json')).write_text(json.dumps({'source_annotation': doc, 'source_sha256': sha(record[0].encode()), 'adapter': converted, 'assigned_targets': targets}, indent=2, ensure_ascii=False), encoding='utf-8')
                samples.append({'id': ident, 'raw': raw, 'targets': targets, 'adapter': converted, 'frozen_predictions': preds})
        save('native-forward-gate')
        for sample in samples:
            stamp = time.perf_counter()
            captures, original = capture_features(backend, sample['raw'])
            sample.update(features=captures, baseline=original)
            with torch.no_grad():
                replay = bits(model(captures))
            mismatch = {k: int(np.count_nonzero(replay[k] != original[k])) for k in replay}
            paths = list(a.frozen_runs.glob('run_*/heads/' + sample['id'] + '.npz'))
            if len(paths) != 1:
                raise RuntimeError('Expected one immutable original head buffer: ' + sample['id'])
            with np.load(paths[0]) as frozen:
                frozen_diff = {k: int(np.count_nonzero(original[k] != frozen[k])) for k in original}
            row = {'image_id': sample['id'], 'input_sha256': sha(sample['raw']), 'targets': len(sample['targets']),
                   'human_confirmed': sample['adapter']['human_confirmed'], 'head_replay_bit_differences': mismatch,
                   'frozen_original_bit_differences': frozen_diff, 'seconds': time.perf_counter() - stamp}
            report['cases'].append(row); save(); emit(row)
            if any(mismatch.values()) or any(frozen_diff.values()):
                raise RuntimeError('Native forward gate failed; training stopped')
        report['native_forward_gate_passed'] = True
        w = model.weights[0].detach().clone().requires_grad_(True)
        native_dot = backend.model.dot(w, samples[0]['features'][0])
        native_dot.square().mean().backward()
        report['original_integer_dot_has_autograd_path'] = bool(native_dot.requires_grad)
        report['original_integer_dot_nonzero_weight_gradients'] = int(torch.count_nonzero(w.grad)) if w.grad is not None else 0
        save('bounded-head-updates')
        optimizer = torch.optim.SGD(model.parameters(), lr=a.learning_rate)
        initial = {k: v.detach().clone() for k, v in model.state_dict().items()}

        def loss():
            return torch.stack([loss_for(model(s['features']), s['targets']) for s in samples]).mean()

        with torch.no_grad():
            report['initial_loss'] = float(loss())
        for step in range(a.steps):
            optimizer.zero_grad(set_to_none=True)
            value = loss()
            if not torch.isfinite(value):
                raise RuntimeError('Nonfinite loss; stop')
            value.backward()
            grads = [p.grad for p in model.parameters() if p.grad is not None]
            if not grads or any(not torch.isfinite(g).all() for g in grads):
                raise RuntimeError('Missing/nonfinite gradients; stop')
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            nonzero = sum(int(torch.count_nonzero(g)) for g in grads)
            if not nonzero:
                raise RuntimeError('All gradients are zero; stop')
            optimizer.step()
            row = {'step': step + 1, 'loss_before_step': float(value.detach()),
                   'gradient_norm_before_clip': float(norm), 'nonzero_gradient_parameters': nonzero}
            report['training'].append(row); save(); emit(row)
        with torch.no_grad():
            report['final_loss'] = float(loss())
        report['changed_float_master_parameters'] = sum(int(torch.count_nonzero(v != initial[k])) for k, v in model.state_dict().items())
        if not report['changed_float_master_parameters'] or not report['final_loss'] < report['initial_loss']:
            raise RuntimeError('Bounded update did not reduce its training loss; do not claim a working optimization gate')
        save('export-and-full-native-roundtrip')
        target = out / 'resource744.head-probe.body.bin'
        report['body_export'] = model.export_body(a.upstream, target)
        if not report['body_export']['changed_bytes']:
            raise RuntimeError('FP16 storage erased every update')
        torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, out / 'head-master-parameters.pt')
        reloaded = Backend(a.upstream, 'cuda')
        report['reloaded_body_sha256'] = apply_body_copy(reloaded, target)
        sys.path.insert(0, str(a.z8_package.resolve()))
        from z8models.native_post import decode_raw
        for sample in samples:
            updated = reloaded.infer(sample['raw'])['heads']
            with torch.no_grad():
                replay = bits(model(sample['features']))
            differences = {k: int(np.count_nonzero(updated[k] != replay[k])) for k in updated}
            original_delta = {k: int(np.count_nonzero(updated[k] != sample['baseline'][k])) for k in updated}
            packed = reloaded.pack_heads(updated['fine'].view('<f2'), updated['coarse'].view('<f2'))
            decoded = decode_raw(packed, 744)
            np.savez_compressed(out / (sample['id'] + '-updated-heads.npz'), **updated)
            (out / (sample['id'] + '-updated-predictions.json')).write_text(json.dumps(decoded, indent=2), encoding='utf-8')
            row = {'image_id': sample['id'], 'reloaded_full_network_vs_trainable_head_bit_differences': differences,
                   'changed_head_values': original_delta, 'original_BA2_decode_return_code': decoded['return_code'],
                   'candidates': decoded['kept_count']}
            report['roundtrip'].append(row); save(); emit(row)
            if any(differences.values()) or decoded['return_code']:
                raise RuntimeError('Export/reload/native-decoder gate failed')
        if sha((a.upstream / 'resource744.body.bin').read_bytes()) != BODY_SHA:
            raise RuntimeError('Pinned original model was modified')
        report.update(passed=True, stage='complete', elapsed_seconds=time.perf_counter() - started,
                      peak_allocated_GPU_MB=torch.cuda.max_memory_allocated() / 1024**2,
                      peak_reserved_GPU_MB=torch.cuda.max_memory_reserved() / 1024**2,
                      original_body_unchanged=True)
        save(); emit({'passed': True, 'initial_loss': report['initial_loss'], 'final_loss': report['final_loss'], 'output': str(out)})
    except BaseException as e:
        report.update(error=repr(e), elapsed_seconds=time.perf_counter() - started)
        save(); raise


if __name__ == '__main__':
    main()
