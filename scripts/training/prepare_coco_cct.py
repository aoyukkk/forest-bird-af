"""Download explicit public supervision; no model predictions become truth.

COCO bird masks carry no eye/head labels. CCT emptiness comes only from the
upstream explicit category, never from a detector abstention. Original images,
receipts, derivatives and annotation manifests must remain outside Git.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
import zipfile

import numpy as np
from PIL import Image
import requests

from bird_surface import outside_git, read, write, digest

ALLOWED_COCO_LICENSES = {1, 2, 4, 5, 8}


def coco_records(document):
    bird_ids = {c['id'] for c in document['categories'] if c['name'] == 'bird'}
    if len(bird_ids) != 1:
        raise ValueError('Expected the explicit COCO bird category')
    bird_id = next(iter(bird_ids))
    annotations = defaultdict(list)
    for annotation in document['annotations']:
        if annotation['category_id'] == bird_id:
            annotations[annotation['image_id']].append(annotation)
    return [(image, annotations[image['id']]) for image in document['images']
            if image['id'] in annotations and image['license'] in ALLOWED_COCO_LICENSES
            and any(not a.get('iscrowd', 0) and a.get('segmentation') for a in annotations[image['id']])]


def cct_records(document, splits, limit):
    empty_ids = {c['id'] for c in document['categories'] if c['name'].lower() == 'empty'}
    if len(empty_ids) != 1:
        raise ValueError('An explicit empty category is required')
    labels = defaultdict(set)
    for annotation in document['annotations']:
        labels[annotation['image_id']].add(annotation['category_id'])
    train_locations = set(map(str, splits['splits']['train']))
    by_location = defaultdict(list)
    for image in document['images']:
        stamp = image.get('date_captured', '')
        if (labels[image['id']] != empty_ids or str(image['location']) not in train_locations
                or len(stamp) < 13 or not 8 <= int(stamp[11:13]) <= 17):
            continue
        by_location[str(image['location'])].append(image)
    # One frame per camera-day and sequence. Round robin prevents a large
    # location from dominating. All decisions precede prediction or fitting.
    queues = []
    for location in sorted(by_location):
        days, sequences, chosen = set(), set(), []
        for image in sorted(by_location[location], key=lambda r: hashlib.sha256(r['id'].encode()).hexdigest()):
            day = image['date_captured'][:10]
            sequence = image.get('seq_id', image['id'])
            if day in days or sequence in sequences:
                continue
            days.add(day); sequences.add(sequence); chosen.append(image)
        queues.append(chosen)
    result = []
    for index in range(max(map(len, queues), default=0)):
        for queue in queues:
            if index < len(queue):
                result.append(queue[index])
                if len(result) == limit:
                    return result
    return result


def fetch(url, destination, max_bytes):
    receipt = destination.with_suffix(destination.suffix + '.download.json')
    if destination.exists():
        old = read(receipt)
        if old['source_url'] != url or old['sha256'] != digest(destination):
            raise ValueError('Existing image identity mismatch')
        return old
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.part')
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=(20, 60)) as response:
                response.raise_for_status()
                count = 0
                with partial.open('wb') as stream:
                    for block in response.iter_content(1024 * 1024):
                        count += len(block)
                        if count > max_bytes:
                            raise ValueError('Public image exceeds size bound')
                        stream.write(block)
            break
        except requests.RequestException as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if attempt == 2 or status in (401, 403, 404):
                raise RuntimeError(f'Image download: {type(exc).__name__}, HTTP {status}') from None
            time.sleep(attempt + 1)
    with Image.open(partial) as image:
        image.verify()
    partial.rename(destination)
    record = dict(source_url=url, sha256=digest(destination), bytes=destination.stat().st_size)
    write(receipt, record)
    return record


def binary_mask(annotations, width, height):
    from pycocotools import mask as mask_api
    union = np.zeros((height, width), np.uint8)
    for annotation in annotations:
        if annotation.get('iscrowd', 0):
            continue
        segmentation = annotation['segmentation']
        if isinstance(segmentation, list):
            rle = mask_api.merge(mask_api.frPyObjects(segmentation, height, width))
        elif isinstance(segmentation.get('counts'), list):
            rle = mask_api.frPyObjects(segmentation, height, width)
        else:
            rle = segmentation
        decoded = mask_api.decode(rle)
        if decoded.ndim == 3:
            decoded = decoded.any(axis=2)
        union |= decoded.astype(np.uint8)
    return union


def prepare_one(task, output, downloads):
    dataset, image, annotations = task
    name = Path(image['file_name']).name
    ident = ('coco_' + str(image['id']).zfill(12)) if dataset == 'COCO-2017' else 'cct_' + image['id']
    if dataset == 'COCO-2017':
        url = 'https://s3.amazonaws.com/images.cocodataset.org/train2017/' + name
    else:
        url = 'https://lilawildlife.blob.core.windows.net/lila-wildlife/caltech-unzipped/cct_images/' + name
    original = downloads / dataset / name
    receipt = fetch(url, original, 30 * 1024 * 1024)
    with Image.open(original) as loaded:
        if loaded.size != (image['width'], image['height']):
            raise ValueError('Image and annotation dimensions differ: ' + ident)
        pixels = loaded.convert('RGB').resize((384, 256), Image.Resampling.BILINEAR)
    array = np.asarray(pixels)
    if dataset != 'COCO-2017':
        chroma = float((array.max(axis=2).astype(float) - array.min(axis=2)).mean())
        if chroma < 3 or not 20 <= float(array.mean()) <= 235:
            return dict(image_id=ident, status='excluded_grayscale_or_extreme_exposure', source=dataset)
    path = output / 'images' / (ident + '.png'); pixels.save(path)
    w, h = image['width'], image['height']
    def box(ann):
        x, y, bw, bh = ann['bbox']
        return [float(np.clip(x * 384 / w, 0, 384)), float(np.clip(y * 256 / h, 0, 256)),
                float(np.clip((x + bw) * 384 / w, 0, 384)), float(np.clip((y + bh) * 256 / h, 0, 256))]
    group = ('coco_photo_' + image['file_name']) if dataset == 'COCO-2017' else 'cct_location_' + str(image['location'])
    internal_val = int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 10 == 0
    row = dict(image_id=ident, path=str(path), source=dataset, original_id=image['id'],
               split='public_val' if internal_val else 'public_train', group=group,
               source_sha256=receipt['sha256'], input_sha256=digest(path), source_url=url,
               objects=[], eyes=[], eye_complete=False, absent=dataset != 'COCO-2017',
               negative_regions=[], uncertain=[], head_labels_are_weak=False,
               original_dimensions=[w, h], annotation_provenance='upstream_public_human',
               teacher_predictions_used=False, camera_AF_verified=False)
    if dataset == 'COCO-2017':
        mask = binary_mask(annotations, w, h)
        if not mask.any():
            raise ValueError('Empty annotated bird mask: ' + ident)
        mask_path = output / 'masks' / (ident + '.png')
        input_mask = Image.fromarray(mask * 255).resize((384, 256), Image.Resampling.NEAREST)
        input_mask.save(mask_path)
        input_foreground_pixels = int((np.asarray(input_mask) > 0).sum())
        row.update(foreground_mask=str(mask_path), foreground_mask_sha256=digest(mask_path),
                   license_id=image['license'], flickr_url=image.get('flickr_url'),
                   objects=[dict(kind='bird', box=box(a), weight=1., source='COCO_human_box')
                            for a in annotations if not a.get('iscrowd', 0)],
                   uncertain=[box(a) for a in annotations if a.get('iscrowd', 0)],
                   mask_scope='visible annotated bird instances; not an exhaustive whole-scene absence label',
                   input_foreground_pixels=input_foreground_pixels,
                   mask_has_reliable_foreground=input_foreground_pixels >= 9,
                   mask_background_weight=.5 if input_foreground_pixels >= 9 else 0.)
        row['negative_regions'] = [o['box'] for o in row['objects']]
    else:
        row.update(eye_complete=True, negative_regions=[[0., 0., 384., 256.]],
                   label_source='CCT_explicit_empty', rights_holder=image.get('rights_holder'),
                   sequence_id=image.get('seq_id'), date_captured=image['date_captured'],
                   location=str(image['location']), license='CDLA-Permissive-1.0')
    return dict(image_id=ident, status='prepared', record=row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('coco-json', 'cct-zip', 'cct-splits', 'downloads', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--cct-limit', type=int, default=1000)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    output, downloads = outside_git(args.output), outside_git(args.downloads)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'images').mkdir(); (output / 'masks').mkdir()
    coco = read(args.coco_json)
    with zipfile.ZipFile(args.cct_zip) as archive:
        if len(archive.namelist()) != 1:
            raise ValueError('Unexpected CCT annotation archive')
        cct = json.loads(archive.read(archive.namelist()[0]))
    selected_coco = coco_records(coco)
    selected_cct = cct_records(cct, read(args.cct_splits), args.cct_limit)
    tasks = [('COCO-2017', image, annotations) for image, annotations in selected_coco]
    tasks.extend(('CCT', image, None) for image in selected_cct)
    write(output / 'plan-before-download.json', dict(coco_images=len(selected_coco), cct_candidates=len(selected_cct),
          coco_licenses=coco['licenses'], allowed_coco_license_ids=sorted(ALLOWED_COCO_LICENSES),
          coco_annotation_sha256=digest(args.coco_json), cct_annotation_zip_sha256=digest(args.cct_zip),
          cct_split_sha256=digest(args.cct_splits),
          records=[dict(dataset=t[0], original_id=t[1]['id']) for t in tasks],
          old_community_changed=False, teacher_predictions_used=False))
    records, excluded, failures = [], [], []
    # Test both official image services before queueing the complete cohort.
    preflight = [tasks[0], next(t for t in tasks if t[0] == 'CCT')]
    for task in preflight:
        result = prepare_one(task, output, downloads)
        if result['status'] == 'prepared': records.append(result['record'])
        else: excluded.append(result)
    tested = {(t[0], t[1]['id']) for t in preflight}
    pending = [t for t in tasks if (t[0], t[1]['id']) not in tested]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(prepare_one, task, output, downloads): task for task in pending}
        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
                if result['status'] == 'prepared': records.append(result['record'])
                else: excluded.append(result)
            except Exception as exc:
                failures.append(dict(source=task[0], original_id=task[1]['id'], error=str(exc)))
            if (len(records) + len(excluded) + len(failures)) % 100 == 0:
                print('prepared', len(records), 'excluded', len(excluded), 'failed', len(failures), flush=True)
    records.sort(key=lambda r: r['image_id'])
    write(output / 'dataset.json', dict(schema='bird-public-expansion-v1', width=384, height=256,
          records=records, counts=dict(Counter(r['source'] for r in records)),
          eye_labels_added=0, teacher_predictions_used=False,
          limits=['COCO backgrounds and mask contours retain annotation uncertainty',
                  'CCT empty frames have an upstream human label, not verified camera AF',
                  'internal splits need cross-source duplicate grouping before formal training',
                  'no new independent community holdout']))
    write(output / 'status.json', dict(prepared=len(records), excluded=excluded, failures=failures,
          planned=len(tasks), complete=not failures, input_count_accounted=len(records)+len(excluded)+len(failures)==len(tasks)))
    if failures:
        raise RuntimeError('Image failures retained; incomplete dataset cannot be admitted')
    print('COMPLETE', len(records), 'excluded', len(excluded), flush=True)


if __name__ == '__main__':
    main()
