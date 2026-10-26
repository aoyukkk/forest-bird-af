"""Create a private, partial-label dataset from CUB and the frozen community split.

Original images, official splits and the production database are never modified.
Public head rectangles are explicitly weak, derived labels rather than human boxes.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weak_head(parts, width, height):
    visible = [p[:2] for k, p in parts.items() if k in (2, 5, 6, 7, 10, 11, 15) and p[2]]
    if len(visible) < 2:
        return None
    points = np.asarray(visible)
    lo, hi = points.min(0), points.max(0)
    span = hi - lo
    if max(span) < 3:
        return None
    # Landmarks lie inside the head, not on its outline. Nearly horizontal
    # bill/eye/nape points must not become a thin eye-band rectangle.
    pad = np.array([max(span[0] * .2, max(span) * .35, 2.),
                    max(span[1] * .5, max(span) * .35, 2.)])
    return [max(0., lo[0] - pad[0]), max(0., lo[1] - pad[1]),
            min(float(width), hi[0] + pad[0]), min(float(height), hi[1] + pad[1])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cub', type=Path, required=True)
    parser.add_argument('--community', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    repo = Path(__file__).resolve().parents[2]
    if out.is_relative_to(repo) or out.is_relative_to(args.cub.resolve()) or out.is_relative_to(args.workspace.resolve()):
        parser.error('Derived dataset must be outside sources and public repository')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'images').mkdir()
    cub = args.cub
    names = dict(line.split(maxsplit=1) for line in (cub / 'images.txt').read_text().splitlines())
    official = dict(line.split() for line in (cub / 'train_test_split.txt').read_text().splitlines())
    boxes = {v[0]: list(map(float, v[1:])) for line in (cub / 'bounding_boxes.txt').read_text().splitlines() if (v := line.split())}
    parts = {}
    for line in (cub / 'parts/part_locs.txt').read_text().splitlines():
        image_id, part_id, x, y, visible = line.split()
        parts.setdefault(image_id, {})[int(part_id)] = [float(x), float(y), int(visible)]
    frozen = json.loads(args.community.read_text(encoding='utf-8'))
    protected = {r['metadata']['original_sha256'] for r in frozen['images'] if r['split'] != 'train'}
    rng = np.random.default_rng(20261026)
    by_species = {}
    for idx, name in names.items():
        if official[idx] == '1':
            by_species.setdefault(name.split('/')[0], []).append(idx)
    public_val = set()
    for ids in by_species.values():
        rng.shuffle(ids)
        public_val.update(ids[:max(1, round(len(ids) * .1))])
    rows, excluded, errors = [], [], []
    for idx, relative in names.items():
        if official[idx] != '1':
            continue  # official test is not consumed for fitting or selection
        path = cub / 'images' / relative
        digest = sha(path)
        if digest in protected:
            excluded.append({'id': idx, 'reason': 'exact overlap with held-out community asset'})
            continue
        try:
            with Image.open(path) as im:
                im = im.convert('RGB')
                width, height = im.size
                pixels = im.resize((384, 256), Image.Resampling.BILINEAR)
            image_id = 'cub_' + idx.zfill(5)
            pixels.save(out / 'images' / (image_id + '.png'))
            sx, sy = 384 / width, 256 / height
            def scale(b):
                return [float(b[0] * sx), float(b[1] * sy), float(b[2] * sx), float(b[3] * sy)]
            x, y, w, h = boxes[idx]
            bird = scale([x, y, x + w, y + h])
            head = weak_head(parts[idx], width, height)
            objects = [{'kind': 'bird', 'box': bird, 'weight': 1., 'source': 'public_human'}]
            if head:
                objects.append({'kind': 'head', 'box': scale(head), 'weight': .35, 'source': 'derived_landmarks_v3'})
            eyes = [[parts[idx][k][0] * sx, parts[idx][k][1] * sy] for k in (7, 11) if parts[idx][k][2]]
            # Visibility is source evidence. At insufficient input scale use unknown,
            # rather than teaching the network to recover invisible fine detail.
            eye_usable = head is not None and min(scale(head)[2] - scale(head)[0], scale(head)[3] - scale(head)[1]) >= 8
            rows.append(dict(image_id=image_id, path=str(out / 'images' / (image_id + '.png')),
                             source='CUB-200-2011', source_sha256=digest,
                             split='public_val' if idx in public_val else 'public_train',
                             group=relative.split('/')[0], objects=objects,
                             eyes=eyes if eye_usable else [],
                             eye_complete=bool(eye_usable), absent=False,
                             negative_regions=[bird], uncertain=[],
                             head_labels_are_weak=True))
        except Exception as exc:
            errors.append({'id': idx, 'error': str(exc)})
    for row in frozen['images']:
        if row['split'] == 'test':
            continue  # old test is quarantined, including image pixels
        doc, ident = row['document'], row['image_id']
        path = args.workspace / 'images' / (ident + '.png')
        if sha(path) != row['metadata']['png_sha256']:
            raise ValueError('Community input hash mismatch: ' + ident)
        objects, eyes, uncertain = [], [], []
        for item in doc['items']:
            kind = item['kind']
            if kind in ('bird', 'head') and item.get('box_xyxy'):
                objects.append(dict(kind=kind, box=item['box_xyxy'], weight=1., source='human_review'))
            elif kind == 'eye':
                b = item.get('box_xyxy')
                eyes.append(item.get('point_xy') or [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2])
            elif item.get('box_xyxy'):
                uncertain.append(item['box_xyxy'])
        rows.append(dict(image_id=ident, path=str(path), source='community',
                         source_sha256=row['metadata']['original_sha256'],
                         split='community_train' if row['split'] == 'train' else 'community_val',
                         group=row['leakage_group_id'], objects=objects, eyes=eyes,
                         eye_complete=False, absent=doc['presence'] == 'absent',
                         negative_regions=[x['box'] for x in objects if x['kind'] == 'bird'],
                         uncertain=uncertain, head_labels_are_weak=False))
    counts = {s: sum(r['split'] == s for r in rows) for s in sorted({r['split'] for r in rows})}
    result = dict(schema='bird-parts-partial-v1', width=384, height=256,
                  seed=20261026, community_sha256=sha(args.community),
                  input='RGB bilinear stretch u8 /256, same community pixels as native baseline',
                  counts=counts, records=rows, errors=errors, excluded=excluded,
                  limits=['CUB labels cover focal bird, not guaranteed all birds in scene',
                          'negative supervision restricted to annotated regions; outside unknown',
                          'weak head boxes are not human truth',
                          'public internal validation is stratified, not independent capture groups',
                          'cross-source near-duplicate screening still required before claims'])
    (out / 'dataset.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'counts': counts, 'failed': len(errors), 'excluded': len(excluded)}, indent=2))
    if errors:
        raise RuntimeError('Public image failures recorded; do not silently omit')


if __name__ == '__main__':
    main()
