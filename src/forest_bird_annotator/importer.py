"""Import exact saved 384x256 inputs without invoking a network."""
import csv
import hashlib
import io
import json
from pathlib import Path
import os
from PIL import Image
from .store import Store, Problem, ID, dumps


def sha(data):
    return hashlib.sha256(data).hexdigest()


def import_runs(workspace, runs, registry):
    store = Store(workspace)
    with Path(registry).open(encoding='utf-8-sig', newline='') as f:
        registered = {r['image_id']: r for r in csv.DictReader(f)}
    rows, seen, failures = [], set(), []
    for run in sorted(Path(runs).glob('run_*')):
        if not (run / 'predictions.jsonl').is_file():
            continue
        summary = json.loads((run / 'summary.json').read_text(encoding='utf-8'))
        if not summary.get('complete') or summary.get('failed'):
            raise Problem(f'Prelabel run is incomplete: {run.name}')
        for line in (run / 'predictions.jsonl').read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            ident = row['image_id']
            try:
                if not ID.fullmatch(ident) or ident in seen or ident not in registered:
                    raise ValueError('Duplicate, unsafe or unregistered image ID')
                seen.add(ident)
                raw = (run / 'inputs' / (ident + '.bin')).read_bytes()
                if len(raw) != 3*256*384 or sha(raw) != row['input_sha256']:
                    raise ValueError('Saved CHW input hash/size mismatch')
                if row['preprocess_id'] != 'review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1':
                    raise ValueError('Unknown preprocessing definition')
                reference = (run / row['review_relative_path']).resolve()
                if not reference.is_file() or sha(reference.read_bytes()) != row['review_sha256']:
                    raise ValueError('Frozen reference image missing or changed')
                if registered[ident]['review_sha256'] != row['review_sha256']:
                    raise ValueError('Registry reference hash mismatch')
                plane = 384*256
                im = Image.merge('RGB', tuple(Image.frombytes('L', (384,256), raw[i*plane:(i+1)*plane]) for i in range(3)))
                stream = io.BytesIO(); im.save(stream, 'PNG'); png = stream.getvalue()
                with Image.open(io.BytesIO(png)) as check:
                    if check.size != (384,256) or check.mode != 'RGB' or b''.join(c.tobytes() for c in check.split()) != raw:
                        raise ValueError('Input PNG does not round-trip to saved bytes')
                meta = {'image_id': ident, 'width': 384, 'height': 256,
                        'png_sha256': sha(png), 'input_sha256': sha(raw), 'preprocess_id': row['preprocess_id'],
                        'original_sha256': registered[ident]['original_sha256'],
                        'batch': registered[ident]['release_tag'],
                        'reference_path': str(reference), 'reference_sha256': row['review_sha256'],
                        'reference_width': row['width'], 'reference_height': row['height']}
                rows.append((meta, row['candidates'], png))
            except Exception as e:
                failures.append({'image_id': ident, 'error': str(e)})
    if seen != set(registered):
        failures.append({'error': 'Run IDs must match the full registry', 'missing': sorted(set(registered)-seen),
                         'extra': sorted(seen-set(registered))})
    report = {'passed': not failures, 'expected': len(registered), 'validated': len(rows),
              'failed': failures, 'inference_rerun': False, 'human_annotations_created': False,
              'coordinate_space': 'z8_input_384x256'}
    if failures:
        (store.root/'import-failed.json').write_text(dumps(report), encoding='utf-8')
        raise Problem('Import validation failed', details=failures)
    images = store.root/'images'; images.mkdir(exist_ok=True)
    with store.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        for meta, predictions, png in rows:
            old = c.execute('SELECT metadata FROM images WHERE id=?', (meta['image_id'],)).fetchone()
            if old:
                old = json.loads(old[0])
                if any(old[k] != meta[k] for k in ('input_sha256','png_sha256','original_sha256','preprocess_id')):
                    raise Problem('Existing input identity changed: '+meta['image_id'])
            target = images/(meta['image_id']+'.png')
            if target.exists():
                if sha(target.read_bytes()) != meta['png_sha256']:
                    raise Problem('Workspace PNG modified: '+meta['image_id'])
            else:
                temp = target.with_suffix('.png.tmp')
                temp.write_bytes(png); os.replace(temp,target)
            c.execute('INSERT INTO images VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET metadata=excluded.metadata,predictions=excluded.predictions',
                      (meta['image_id'], dumps(meta), dumps(predictions)))
    report['imported'] = len(rows)
    (store.root/'import-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
