"""Import verified NABirds parquet images against separately sourced original labels.

Mirror license fields never replace Cornell's original research terms. Only
official training IDs are admitted, with a deterministic internal validation.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

from prepare_bird_parts import weak_head


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--parquet-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error('Images and private manifests must stay outside public repository')
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'images').mkdir()
    meta = args.metadata
    names = dict(line.split(maxsplit=1) for line in (meta / 'images.txt').read_text().splitlines())
    by_name = {Path(path).name: idx for idx, path in names.items()}
    official = dict(line.split() for line in (meta / 'train_test_split.txt').read_text().splitlines())
    boxes = {v[0]: list(map(float, v[1:])) for line in (meta / 'bounding_boxes.txt').read_text().splitlines() if (v := line.split())}
    sizes = {v[0]: list(map(int, v[1:])) for line in (meta / 'sizes.txt').read_text().splitlines() if (v := line.split())}
    parts = {}
    remap = {0: 2, 1: 5, 2: 10, 3: 7, 4: 11}
    for line in (meta / 'parts/part_locs.txt').read_text().splitlines():
        idx, k, x, y, visible = line.split()
        if int(k) in remap:
            parts.setdefault(idx, {})[remap[int(k)]] = [float(x), float(y), int(visible)]
    doc = json.loads(args.base.read_text(encoding='utf-8'))
    rows, rejected, seen = [], [], set()
    sources = []
    for path in sorted(args.parquet_dir.glob('train-*.parquet')):
        sources.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for batch in pq.ParquetFile(path).iter_batches(batch_size=32):
            for item in batch.to_pylist():
                filename = Path(item['image']['path']).name
                idx = by_name.get(filename)
                if idx is None or official[idx] != '1':
                    rejected.append({'file': filename, 'reason': 'missing metadata or non-training ID'})
                    continue
                if idx in seen:
                    raise ValueError('Repeated NABirds ID: ' + idx)
                seen.add(idx)
                raw = item['image']['bytes']
                with Image.open(io.BytesIO(raw)) as im:
                    im = im.convert('RGB'); width, height = im.size
                    original_width, original_height = sizes[idx]
                    if abs(width / height - original_width / original_height) > .01:
                        raise ValueError('Unverified crop/aspect ratio: ' + filename)
                    im = im.resize((384, 256), Image.Resampling.BILINEAR)
                image_id = 'nab_' + idx.replace('-', '')
                image_path = args.output / 'images' / (image_id + '.png')
                im.save(image_path)
                def scale(b):
                    return [max(0., min(float(v * (384 / original_width if j % 2 == 0 else 256 / original_height)),
                                         384. if j % 2 == 0 else 256.)) for j, v in enumerate(b)]
                x, y, w, h = boxes[idx]; bird = scale([x, y, x + w, y + h])
                head = weak_head(parts[idx], original_width, original_height)
                objects = [dict(kind='bird', box=bird, weight=1., source='public_human')]
                usable = False
                if head:
                    b = scale(head)
                    objects.append(dict(kind='head', box=b, weight=.35, source='derived_landmarks_v3'))
                    usable = min(b[2] - b[0], b[3] - b[1]) >= 8
                eyes = [[parts[idx][k][0] * 384 / original_width, parts[idx][k][1] * 256 / original_height]
                        for k in (7, 11) if parts[idx][k][2]] if usable else []
                internal_val = int(hashlib.sha256(idx.encode()).hexdigest()[:8], 16) % 10 == 0
                rows.append(dict(image_id=image_id, path=str(image_path), source='NABirds',
                                 source_sha256=hashlib.sha256(raw).hexdigest(), original_id=idx,
                                 split='public_val' if internal_val else 'public_train',
                                 group=names[idx].split('/')[0], objects=objects, eyes=eyes,
                                 eye_complete=bool(usable), absent=False,
                                 negative_regions=[bird], uncertain=[], head_labels_are_weak=True,
                                 image_dimensions=[width, height], annotation_dimensions=sizes[idx]))
        print(json.dumps({'file': path.name, 'accepted': len(rows), 'rejected': len(rejected)}), flush=True)
    doc['records'].extend(rows)
    doc['counts'] = {s: sum(r['split'] == s for r in doc['records']) for s in sorted({r['split'] for r in doc['records']})}
    doc['nabirds_import'] = {'parquet_sources': sources, 'metadata_sha256': {
        str(p.relative_to(meta)): hashlib.sha256(p.read_bytes()).hexdigest() for p in meta.rglob('*.txt')},
        'rejected': rejected, 'original_terms': 'https://dl.allaboutbirds.org/merlin-computer-vision-terms-of-use',
        'research_only': True, 'all_imported_ids_official_train': True,
        'limit': 'part labels and image IDs checked; no claim mirror is a new authoritative dataset'}
    output = args.output / 'dataset.v2.json'
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'counts': doc['counts'], 'rejected': len(rejected)}, indent=2))


if __name__ == '__main__':
    main()
