"""Validate public copies, render NEF review JPEGs, and build bounded ZIP assets."""
import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image, ImageOps
from prepare_community_release import digest


def rgb(path):
    if path.suffix.lower() == '.nef':
        with rawpy.imread(str(path)) as raw:
            value = raw.postprocess(use_camera_wb=True, output_bps=8,
                                    no_auto_bright=True, output_color=rawpy.ColorSpace.sRGB,
                                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD)
        return Image.fromarray(value)
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert('RGB')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot', type=Path, required=True)
    a = p.parse_args()
    root = a.snapshot
    source_rows = json.loads((root / 'private-source-map.json').read_text(encoding='utf-8'))
    (root / 'review-images').mkdir(exist_ok=False)
    (root / 'packages').mkdir(exist_ok=False)
    public, private_review, errors = [], [], []
    for index, row in enumerate(source_rows):
        if row['duplicate_occurrence']:
            continue
        try:
            source = Path(row['source_path'])
            path = root / 'public-images' / row['public_name']
            if path.suffix.lower() == '.nef':
                with rawpy.imread(str(source)) as original, rawpy.imread(str(path)) as cleaned:
                    if not np.array_equal(original.raw_image, cleaned.raw_image):
                        raise RuntimeError('NEF sensor samples changed')
                review = root / 'review-images' / (row['image_id'] + '.render-v1.jpg')
                rgb(path).save(review, quality=98, subsampling=0)
                canonical = rgb(review)
            else:
                canonical = rgb(path)
                source_rgb = rgb(source)
                if source_rgb.size != canonical.size or source_rgb.tobytes() != canonical.tobytes():
                    raise RuntimeError('Decoded RGB pixels changed while cleaning metadata')
                review = path
            public.append({'image_id': row['image_id'], 'file': row['public_name'],
                           'format': path.suffix.lower()[1:], 'width': canonical.width,
                           'height': canonical.height, 'public_bytes': path.stat().st_size,
                           'public_sha256': digest(path), 'original_sha256': row['original_sha256'],
                           'review_file': str(review.relative_to(root)).replace('\\', '/'),
                           'review_sha256': digest(review),
                           'review_rgb_sha256': hashlib.sha256(canonical.tobytes()).hexdigest(),
                           'annotation_status': 'pending', 'split': ''})
            private_review.append({'image_id': row['image_id'], 'path': str(review),
                                   'width': canonical.width, 'height': canonical.height})
        except Exception as error:
            errors.append({'image_id': row['image_id'], 'error': repr(error)})
        if (index + 1) % 25 == 0:
            print(json.dumps({'checked': index + 1, 'total': len(source_rows), 'errors': len(errors)}), flush=True)
    (root / 'private-review-map.json').write_text(json.dumps(private_review, indent=2), encoding='utf-8')
    (root / 'image-validation.json').write_text(json.dumps({'passed': not errors, 'checked': len(public),
        'errors': errors, 'jpeg_png_decoded_pixels_unchanged': not errors,
        'nef_sensor_samples_unchanged': not errors, 'rawpy': rawpy.__version__,
        'raw_render': {'camera_wb': True, 'output_bps': 8, 'no_auto_bright': True,
                       'color': 'sRGB', 'demosaic': 'AHD', 'jpeg_quality': 98, 'subsampling': 0}}, indent=2), encoding='utf-8')
    if errors:
        raise RuntimeError('Image validation failed; do not publish: ' + str(errors))
    public.sort(key=lambda row: int(row['image_id'].split('_')[1]))
    with (root / 'manifest.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(public[0]))
        writer.writeheader()
        writer.writerows(public)
    (root / 'manifest.json').write_text(json.dumps(public, indent=2), encoding='utf-8')
    report = {'files': len(public), 'public_bytes': sum(r['public_bytes'] for r in public),
              'metadata_cleaned': True, 'human_annotation_complete': False,
              'license': 'Contributor copyrights retained; no blanket image license is granted.',
              'scope': 'All images in the current community collection snapshot; excludes CUB and vendor assets.'}
    (root / 'RELEASE.md').write_text('# Community image snapshot 2026-10-24\n\n'
        + json.dumps(report, indent=2) + '\n\nPublic copies have identifying EXIF fields removed. '
        'JPEG/PNG pixels and NEF sensor samples were checked against originals. '
        'Original files remain local and unchanged. No training or reviewed ground truth is included.\n', encoding='utf-8')
    chunks, current, size = [], [], 0
    for row in public:
        path = root / 'public-images' / row['file']
        if current and size + path.stat().st_size > 1_300_000_000:
            chunks.append(current)
            current, size = [], 0
        current.append(path)
        size += path.stat().st_size
    if current:
        chunks.append(current)
    packages = []
    for index, paths in enumerate(chunks, 1):
        target = root / 'packages' / f'community-images-20261024-part{index:02d}-of{len(chunks):02d}.zip'
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_STORED, allowZip64=True) as archive:
            for path in paths:
                archive.write(path, 'images/' + path.name)
            for name in ['manifest.csv', 'RELEASE.md', 'image-validation.json']:
                archive.write(root / name, name)
        assert target.stat().st_size < 2 * 1024 ** 3
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
        packages.append({'file': target.name, 'bytes': target.stat().st_size,
                         'sha256': digest(target), 'images': len(paths)})
        print(json.dumps(packages[-1]), flush=True)
    (root / 'packages.json').write_text(json.dumps(packages, indent=2), encoding='utf-8')
    (root / 'packages' / 'SHA256SUMS.txt').write_text(''.join(r['sha256'] + '  ' + r['file'] + '\n' for r in packages), encoding='ascii')
    print(json.dumps({'passed': True, 'images': len(public), 'packages': len(packages)}), flush=True)


if __name__ == '__main__':
    main()
