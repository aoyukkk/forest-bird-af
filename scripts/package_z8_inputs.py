"""Publish preserved input bytes and lossless PNGs without rerunning inference."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from PIL import Image, __version__ as pillow_version
from z8_input import INPUT_BYTES, PREPROCESS_ID, image_from_chw


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True, help='Prepared manifest.json (not CSV)')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive-name', default='z8-inputs-384x256-20261024.zip')
    args = parser.parse_args()
    summary = json.loads((args.run / 'summary.json').read_text(encoding='utf-8'))
    if not summary['complete'] or summary['failed']:
        raise ValueError('Run must be complete')
    predictions = [json.loads(line) for line in
                   (args.run / 'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
    metadata = json.loads(args.manifest.read_text(encoding='utf-8'))
    by_id = {row['image_id']: row for row in metadata}
    ids = [row['image_id'] for row in predictions]
    if (len(set(ids)) != len(ids) or len(by_id) != len(metadata)
            or set(ids) != set(by_id) or len(ids) != summary['images_completed']):
        raise ValueError('Manifest and run IDs must match exactly')
    if any(not re.fullmatch(r'fb_\d{4,}', image_id) for image_id in ids):
        raise ValueError('Unsafe image ID')
    if {p.stem for p in (args.run / 'inputs').glob('*.bin')} != set(ids):
        raise ValueError('Saved input file set differs from predictions')
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'input-png').mkdir()
    (args.output / 'input-chw-u8').mkdir()
    rows = []
    for prediction in predictions:
        image_id = prediction['image_id']
        meta = by_id[image_id]
        raw = (args.run / 'inputs' / (image_id + '.bin')).read_bytes()
        if (len(raw) != INPUT_BYTES or sha256(raw) != prediction['input_sha256']
                or prediction['preprocess_id'] != PREPROCESS_ID
                or prediction['review_sha256'] != meta['review_sha256']):
            raise ValueError('Saved input mismatch: ' + image_id)
        png_file = 'input-png/' + image_id + '.png'
        bin_file = 'input-chw-u8/' + image_id + '.bin'
        image_from_chw(raw).save(args.output / png_file)
        (args.output / bin_file).write_bytes(raw)
        with Image.open(args.output / png_file) as image:
            roundtrip = b''.join(channel.tobytes() for channel in image.split())
            if image.mode != 'RGB' or image.size != (384, 256) or roundtrip != raw:
                raise ValueError('PNG pixel round-trip mismatch: ' + image_id)
        rows.append({'image_id': image_id, 'png_file': png_file, 'bin_file': bin_file,
                     'width': 384, 'height': 256,
                     'input_chw_u8_sha256': sha256(raw),
                     'png_sha256': sha256((args.output / png_file).read_bytes()),
                     'original_sha256': meta['original_sha256'],
                     'public_sha256': meta['public_sha256'],
                     'review_sha256': meta['review_sha256'],
                     'review_width': meta['width'], 'review_height': meta['height'],
                     'preprocess_id': PREPROCESS_ID})
    manifest_raw = ''.join(json.dumps(row) + '\n' for row in rows).encode('utf-8')
    (args.output / 'input-manifest.jsonl').write_bytes(manifest_raw)
    validation = {'passed': True, 'images': len(rows), 'width': 384, 'height': 256,
                  'saved_input_hash_mismatches': 0, 'png_roundtrip_mismatches': 0,
                  'input_bytes_per_image': INPUT_BYTES, 'dtype': 'uint8', 'layout': 'CHW',
                  'network_normalization': 'float32(u8) / 256',
                  'preprocess_id': PREPROCESS_ID, 'pillow': pillow_version,
                  'inference_rerun': False, 'human_review_complete': False,
                  'input_manifest_sha256': sha256(manifest_raw)}
    (args.output / 'input-validation.json').write_text(json.dumps(validation, indent=2) + '\n', encoding='utf-8')
    (args.output / 'README.md').write_text(f'''# Z8 simulation input dataset

{len(rows)} lossless RGB PNGs at 384 x 256 and their preserved CHW uint8 buffers.
Each PNG decodes to exactly the bytes used for the published prelabel run after
HWC-to-CHW rearrangement. PNG file hashes and input-buffer hashes are separate.

The network receives float32(u8) / 256. Do not JPEG-recompress these PNGs.
IDs match the original-resolution image archives. input-manifest.jsonl links
each image to its original asset, public copy, review image, and input hashes.

The simulation converts EXIF-oriented review images to RGB, then stretches them
to 384 x 256 with Pillow bilinear interpolation. NEF uses the fixed review JPEG
recorded by the batch manifest and image-validation.json: either the specified
rawpy render or an explicitly selected camera-embedded JPEG. This freezes the simulation inputs; the full
camera sensor-to-network preprocessing has not been established.

For regeneration, see scripts/z8_input.py and the dataset README in:
https://github.com/aoyukkk/forest-bird-af

Labels are pending human review. Photographs retain contributor copyrights.
''', encoding='utf-8')
    archive_path = args.output.parent / args.archive_name
    with archive_path.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(args.output.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(args.output).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != 2 * len(rows) + 3:
            raise ValueError('Archive integrity check failed')
    result = {'file': archive_path.name, 'bytes': archive_path.stat().st_size,
              'sha256': sha256(archive_path.read_bytes()), 'images': len(rows),
              'validation': validation}
    (args.output.parent / 'input-bundle.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
