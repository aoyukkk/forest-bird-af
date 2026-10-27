"""Conservative identity-only admission of new public training assets.

Reference images, including old holdouts, are used only for contamination
signatures. No model inference or holdout label is used for admission.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from bird_surface import read, write, digest, outside_git


class BKTree:
    def __init__(self):
        self.root = None

    def add(self, value, index):
        if self.root is None:
            self.root = [value, [index], {}]
            return
        node = self.root
        while True:
            distance = (node[0] ^ value).bit_count()
            if distance == 0:
                node[1].append(index)
                return
            if distance not in node[2]:
                node[2][distance] = [value, [index], {}]
                return
            node = node[2][distance]

    def query(self, value, radius=4):
        result, stack = [], [self.root] if self.root else []
        while stack:
            node = stack.pop()
            distance = (node[0] ^ value).bit_count()
            if distance <= radius:
                result.extend(node[1])
            stack.extend(v for d, v in node[2].items() if distance-radius <= d <= distance+radius)
        return result


def signature(row):
    path = Path(row['path'])
    actual = digest(path)
    if row.get('input_sha256') and row['input_sha256'] != actual:
        raise ValueError('Input identity mismatch: ' + row['image_id'])
    with Image.open(path) as image:
        pixels = np.asarray(image.convert('RGB'))
        if pixels.shape != (256, 384, 3):
            raise ValueError('Expected frozen 384x256 RGB input')
        gray = np.asarray(image.convert('L').resize((32, 32), Image.Resampling.BILINEAR), np.float32)
        thumb = np.asarray(image.convert('RGB').resize((32, 24), Image.Resampling.BILINEAR)).copy()
    coeff = cv2.dct(gray)[:8, :8].flatten()[1:]
    bits = coeff > np.median(coeff)
    phash = sum(int(v) << i for i, v in enumerate(bits))
    return dict(input_sha256=actual, pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
                phash=phash, thumb=thumb)


def close(a, b):
    if a['pixel_sha256'] == b['pixel_sha256']:
        return True
    if (a['phash'] ^ b['phash']).bit_count() > 4:
        return False
    x, y = a['thumb'].astype(np.float32), b['thumb'].astype(np.float32)
    if float(np.mean((x-y)**2)**.5)/255 > .10:
        return False
    x, y = x.mean(2), y.mean(2)
    mx, my = x.mean(), y.mean()
    similarity = ((2*mx*my+6.5025)*(2*((x-mx)*(y-my)).mean()+58.5225) /
                  ((mx*mx+my*my+6.5025)*(x.var()+y.var()+58.5225)))
    return float(similarity) >= .94


def split_empty_locations(records):
    groups = sorted({r['group'] for r in records if r['source'] == 'CCT'},
                    key=lambda g: hashlib.sha256(('cct-cal-20261027:'+g).encode()).hexdigest())
    if len(groups) < 10:
        raise ValueError('Insufficient independent camera locations')
    calibration = set(groups[:max(3, round(len(groups)*.2))])
    return calibration


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'nabirds', 'coco-cct', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--reference', type=Path, action='append', default=[])
    p.add_argument('--workers', type=int, default=8)
    a = p.parse_args(); out = outside_git(a.output)
    out.mkdir(parents=True, exist_ok=False)
    base, nab, extra = read(a.base), read(a.nabirds), read(a.coco_cct)
    base_ids = {r['image_id'] for r in base['records']}
    references = list(base['records'])
    for path in a.reference:
        references.extend(read(path)['records'])
    references = list({str(Path(r['path']).resolve()).casefold(): r for r in references}.values())
    newcomers = [dict(r) for r in nab['records'] if r['image_id'] not in base_ids]
    newcomers.extend(dict(r) for r in extra['records'])
    newcomers.sort(key=lambda r: ({'COCO-2017': 0, 'NABirds': 1, 'CCT': 2}[r['source']], r['image_id']))
    write(out/'plan-before-signatures.json', dict(reference_images=len(references),
          execution_source_sha256=digest(__file__),
          newcomers=len(newcomers), reference_use='contamination signatures only; no predictions',
          dataset_sha256={str(path): digest(path) for path in [a.base, a.nabirds, a.coco_cct, *a.reference]},
          phash_radius=4, global_gray_similarity_floor=.94, rgb_rmse_ceiling=.10,
          reference_policy='quarantine newcomer; preserve frozen reference',
          new_family_policy='keep first direct representative; retain all original assets',
          empty_calibration_policy='20% of admitted camera locations, metadata-only seed 20261027'))
    cv2.setNumThreads(1)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        sigs = list(pool.map(signature, references + newcomers))
    ref_sigs, new_sigs = sigs[:len(references)], sigs[len(references):]
    tree = BKTree()
    for i, sig in enumerate(ref_sigs):
        tree.add(sig['phash'], i)
    accepted, quarantined, kept_sigs = [], [], []
    new_tree = BKTree()
    for row, sig in zip(newcomers, new_sigs):
        matches = [i for i in tree.query(sig['phash']) if close(sig, ref_sigs[i])]
        if matches:
            quarantined.append(dict(image_id=row['image_id'], reason='frozen_reference_similarity',
                 reference_ids=[references[i]['image_id'] for i in matches]))
            continue
        matches = [i for i in new_tree.query(sig['phash']) if close(sig, kept_sigs[i])]
        if matches:
            quarantined.append(dict(image_id=row['image_id'], reason='new_direct_representative_similarity',
                 representative_id=accepted[matches[0]]['image_id']))
            continue
        row.update(input_sha256=sig['input_sha256'], admission='identity_screened',
                   previous_group=row['group'], group='new_photo_'+row['image_id'] if row['source']!='CCT' else row['group'])
        if row['source'] == 'NABirds':
            row['objects'] = [o for o in row['objects'] if o['kind']=='bird']
            row['head_labels_are_weak'] = False
            row['new_coarse_supervision'] = 'positive visible human eye anchors only; no inferred background'
        new_tree.add(sig['phash'], len(accepted)); kept_sigs.append(sig); accepted.append(row)
    cct_cal = split_empty_locations(accepted)
    for row in accepted:
        if row['source']=='CCT':
            row['split'] = 'public_val' if row['group'] in cct_cal else 'public_train'
        else:
            row['split'] = 'public_val' if int(hashlib.sha256(row['group'].encode()).hexdigest()[:8],16)%10==0 else 'public_train'
    write(out/'newcomers.json', dict(schema='public-expansion-admitted-v1', width=384, height=256,
          records=accepted, teacher_predictions_used=False, camera_AF_verified=False,
          old_splits_modified=False, weak_heads_removed=True))
    write(out/'quarantined.json', dict(records=quarantined, physical_files_removed=False))
    fingerprints = [{k:v for k,v in s.items() if k!='thumb'} for s in sigs]
    write(out/'identity-signatures.json', dict(records=[dict(image_id=row['image_id'], **sig)
          for row,sig in zip(references+newcomers, fingerprints)]))
    write(out/'summary.json', dict(proposed=len(newcomers), admitted=len(accepted), quarantined=len(quarantined),
          by_source=dict(Counter(r['source'] for r in accepted)),
          by_source_split=dict(Counter(r['source']+':'+r['split'] for r in accepted)),
          cct_calibration_locations=sorted(cct_cal), reference_images=len(references),
          identity_screening_is_not_capture_event_identity=True, production_changed=False,
          test_predictions_or_labels_used=False))
    print(read(out/'summary.json'), flush=True)


if __name__=='__main__':
    main()
