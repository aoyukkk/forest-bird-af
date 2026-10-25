"""Freeze reviewed local data and cache the exact native detection-head inputs.

Private artifacts stay outside the repository. Source-directory grouping is a
conservative leakage safeguard, not a claim of verified photographer identity.
"""
import argparse
import hashlib
import json
import random
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
import torch

from e7_backend import Backend, BODY_SHA
from z8_trainable_heads import TrainableHeads, head_events


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def capture_batch(backend, raws):
    events = head_events(backend.model)
    mapping = {id(e['weight']): i for i, e in enumerate(events)}
    captured = {}
    original = backend.model.dot

    def tapped(w, x):
        if id(w) in mapping:
            captured[mapping[id(w)]] = x.detach().clone()
        return original(w, x)

    backend.model.dot = tapped
    try:
        outputs = backend.infer_many(raws)['heads']
    finally:
        del backend.model.dot
    if set(captured) != set(range(len(events))):
        raise RuntimeError('Incomplete feature cache')
    return {k: v.clone() for k, v in captured.items()}, outputs


def freeze(args):
    out = args.output.resolve()
    if any(out.is_relative_to(x.resolve()) for x in (args.workspace, args.upstream, Path(__file__).parents[1])):
        raise ValueError('Output must be outside production data, upstream, and public repository')
    out.mkdir(parents=True, exist_ok=False)
    db = sqlite3.connect((args.workspace / 'annotations.sqlite3').resolve().as_uri() + '?mode=ro', uri=True)
    with sqlite3.connect(out / 'annotations.snapshot.sqlite3') as copy:
        db.backup(copy)
    db.close()
    db = sqlite3.connect(out / 'annotations.snapshot.sqlite3')
    dedupe_bytes = (args.workspace / 'dedupe/current.json').read_bytes()
    (out / 'dedupe.snapshot.json').write_bytes(dedupe_bytes)
    dedupe = json.loads(dedupe_bytes)
    if dedupe.get('stale') or not dedupe.get('available'):
        raise ValueError('Refresh dedupe before freezing')
    all_rows = {}
    for ident, metadata, predictions, document in db.execute('SELECT i.id,i.metadata,i.predictions,r.document FROM images i JOIN z8_reviews r ON r.id=i.id ORDER BY i.id'):
        all_rows[ident] = dict(image_id=ident, metadata=json.loads(metadata), baseline=json.loads(predictions), document=json.loads(document), document_sha256=sha(document.encode()))
    usable = {i: r for i, r in all_rows.items() if i not in dedupe['hidden'] and r['document']['status'] == 'confirmed' and r['document']['presence'] in ('present', 'absent')}
    if len(usable) < 100:
        raise RuntimeError('Insufficient confirmed data')
    parent = {i: i for i in all_rows}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    links = []

    def join(a, b, reason):
        if a not in parent or b not in parent:
            return
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
            links.append([a, b, reason])

    for group in dedupe.get('candidate_groups', []):
        for i in group[1:]:
            join(group[0], i, 'dedupe_candidate_family')
    for a, b in dedupe['hidden'].items():
        join(a, b, 'dedupe_hidden_relation')
    sources = {}
    rejected_historical_maps = []
    for path in sorted(args.analysis.glob('community_release_*/**/private-source-map.json')):
        for row in json.loads(path.read_text(encoding='utf-8')):
            if row['image_id'] in all_rows:
                if row['original_sha256'] != all_rows[row['image_id']]['metadata']['original_sha256']:
                    rejected_historical_maps.append({'image_id': row['image_id'], 'historical_map': str(path), 'reason': 'hash differs from current immutable registry; not used'})
                    continue
                sources[row['image_id']] = row
    families = defaultdict(list)
    unresolved = set()
    for i in all_rows:
        if i not in sources:
            unresolved.add(i)
            continue
        source = Path(sources[i]['source_path'])
        if source.parent.resolve() == args.intake.resolve():
            unresolved.add(i)
        else:
            # Entire submitted subdirectory stays together, even if it contains
            # multiple bursts. This sacrifices sample balance for separation.
            families[str(source.parent.resolve())].append(i)
    for ids in families.values():
        for i in ids[1:]:
            join(ids[0], i, 'same_private_source_directory')
    hashes, colors = {}, {}
    for i, row in all_rows.items():
        path = args.workspace / 'images' / (i + '.png')
        if sha(path.read_bytes()) != row['metadata']['png_sha256']:
            raise ValueError('Frozen PNG identity mismatch: ' + i)
        with Image.open(path) as im:
            if im.size != (384, 256) or im.mode != 'RGB':
                raise ValueError('Frozen input changed')
            pix = np.asarray(im)
            raw = pix.transpose(2, 0, 1).copy().tobytes()
            if sha(raw) != row['metadata']['input_sha256']:
                raise ValueError('Frozen CHW identity mismatch: ' + i)
            small = np.asarray(im.convert('L').resize((9, 8)), dtype=np.int16)
            hashes[i] = int.from_bytes(np.packbits(small[:, 1:] > small[:, :-1]).tobytes(), 'big')
            colors[i] = pix.mean(axis=(0, 1))
        if i in usable:
            identity = row['document']['annotation_image']
            if identity['sha256'] != row['metadata']['png_sha256'] or identity['input_chw_u8_sha256'] != sha(raw):
                raise ValueError('Annotation identity mismatch')
            row['raw'] = raw
    ids = sorted(all_rows)
    for n, a in enumerate(ids):
        for b in ids[n + 1:]:
            if root(a) != root(b) and (hashes[a] ^ hashes[b]).bit_count() <= 8 and np.abs(colors[a] - colors[b]).mean() <= 30:
                join(a, b, 'conservative_cross_directory_visual_similarity')
    groups = defaultdict(list)
    for i in usable:
        groups[root(i)].append(i)
    forced_train = {root(i) for i in unresolved}
    # Try group-only allocations using counts/part coverage, never predictions
    # or model scores. Unresolved source families cannot enter held-out sets.
    rng = random.Random(20261025)
    keys = sorted(g for g in groups if g not in forced_train)
    best = None
    for _ in range(10000):
        rng.shuffle(keys)
        split = {'train': [], 'val': [], 'test': []}
        for g in groups:
            if g in forced_train:
                split['train'].append(g)
        for g in keys:
            counts = {s: sum(len(groups[x]) for x in split[s]) for s in split}
            deficits = {s: len(usable) * f - counts[s] for s, f in [('train', .7), ('val', .15), ('test', .15)]}
            s = max(deficits, key=deficits.get)
            split[s].append(g)
        score = sum(abs(sum(len(groups[g]) for g in split[s]) / len(usable) - f) for s, f in [('train', .7), ('val', .15), ('test', .15)])
        for s in ('val', 'test'):
            kinds = Counter(item['kind'] for g in split[s] for i in groups[g] for item in usable[i]['document']['items'])
            score += max(0, 18 - kinds['eye']) / 100
            score += max(0, 30 - kinds['head']) / 100
            score += max(0, 3 - len(split[s])) / 10
        if best is None or score < best[0]:
            best = score, {s: list(v) for s, v in split.items()}
    assignments = {i: s for s, gs in best[1].items() for g in gs for i in groups[g]}
    for i in usable:
        usable[i]['split'] = assignments[i]
        usable[i]['leakage_group_id'] = root(i)
    manifest = {
        'schema': 'z8-native-head-training-v1', 'seed': 20261025,
        'source_body_sha256': BODY_SHA, 'dedupe_sha256': sha(dedupe_bytes),
        'annotation_snapshot_sha256': sha((out / 'annotations.snapshot.sqlite3').read_bytes()),
        'counts': dict(Counter(assignments.values())),
        'group_counts': {s: len(gs) for s, gs in best[1].items()},
        'unresolved_groups_forced_to_train': sorted(forced_train),
        'excluded_ids': {i: 'dedupe_hidden' if i in dedupe['hidden'] else all_rows[i]['document']['status'] for i in all_rows if i not in usable},
        'grouping_limits': 'Directory families and visual candidate relations are conservative engineering groups; not verified independent capture identities. Z8-assisted human review is not blind ground truth.',
        'images': [{k: v for k, v in usable[i].items() if k != 'raw'} for i in sorted(usable)],
        'leakage_links': links,
        'rejected_historical_source_rows': rejected_historical_maps,
    }
    write(out / 'dataset.json', manifest)
    write(out / 'split-lock.json', {'dataset_sha256': sha((out / 'dataset.json').read_bytes()), 'counts': manifest['counts'], 'group_counts': manifest['group_counts'], 'selection': 'pre-training group-only, label-coverage stratified; no prediction metrics consulted', 'test_policy': 'evaluate once after candidate selection using val only'})
    print(json.dumps({'stage': 'frozen', 'counts': manifest['counts'], 'groups': manifest['group_counts']}, ensure_ascii=True), flush=True)
    return [usable[i] for i in sorted(usable)]


def cache(args, rows):
    backend = Backend(args.upstream, 'cuda')
    model = TrainableHeads(backend)
    cache_dir = args.output / 'features'
    cache_dir.mkdir()
    report = {'passed': False, 'batches': [], 'cuda': torch.cuda.get_device_name(), 'torch': torch.__version__, 'python': sys.executable}
    write(args.output / 'cache-report.json', report)
    stamp = time.perf_counter()
    for start in range(0, len(rows), args.batch_size):
        batch = rows[start:start + args.batch_size]
        before = time.perf_counter()
        features, outputs = capture_batch(backend, [r['raw'] for r in batch])
        with torch.no_grad():
            replay = {k: v.cpu().numpy().astype('<f2').view('<u2') for k, v in model(features).items()}
        for j, row in enumerate(batch):
            paths = list(args.frozen_runs.glob('run_*/heads/' + row['image_id'] + '.npz'))
            if len(paths) != 1:
                raise ValueError('Expected one frozen prediction buffer')
            with np.load(paths[0]) as frozen:
                for k in ('fine', 'coarse'):
                    if not np.array_equal(frozen[k], outputs[k][j]) or not np.array_equal(replay[k][j], outputs[k][j]):
                        raise RuntimeError('Native forward parity failed: ' + row['image_id'])
            torch.save({'features': {k: v[j:j + 1].detach().cpu().clone() for k, v in features.items()},
                        'heads': {k: torch.from_numpy(v[j:j + 1].view('<f2').astype(np.float32)) for k, v in outputs.items()}}, cache_dir / (row['image_id'] + '.pt'))
        detail = dict(start=start, count=len(batch), seconds=time.perf_counter() - before, bit_differences=0)
        report['batches'].append(detail)
        write(args.output / 'cache-report.json', report)
        print(json.dumps({'stage': 'cache', **detail}, ensure_ascii=True), flush=True)
        del features, outputs, replay
    report.update(passed=True, images=len(rows), seconds=time.perf_counter() - stamp,
                  peak_cuda_allocated_mb=torch.cuda.max_memory_allocated() / 2**20,
                  peak_cuda_reserved_mb=torch.cuda.max_memory_reserved() / 2**20,
                  original_body_unchanged=sha((args.upstream / 'resource744.body.bin').read_bytes()) == BODY_SHA)
    if not report['original_body_unchanged']:
        raise RuntimeError('Pinned model changed')
    write(args.output / 'cache-report.json', report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--analysis', type=Path, required=True)
    p.add_argument('--intake', type=Path, required=True)
    p.add_argument('--frozen-runs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--batch-size', type=int, default=32)
    a = p.parse_args()
    if not torch.cuda.is_available():
        p.error('CUDA required; no silent fallback')
    rows = freeze(a)
    cache(a, rows)


if __name__ == '__main__':
    main()
