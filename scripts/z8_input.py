"""Convert review images to the frozen resource744 simulation input format."""
import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageOps

WIDTH, HEIGHT = 384, 256
PLANE_BYTES = WIDTH * HEIGHT
INPUT_BYTES = 3 * PLANE_BYTES
PREPROCESS_ID = 'review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1'


def prepare_review_image(path):
    """Match prelabel_community.py; NEF requires its fixed review JPEG first."""
    with Image.open(path) as image:
        rgb = ImageOps.exif_transpose(image).convert('RGB')
        resized = rgb.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)
        return b''.join(channel.tobytes() for channel in resized.split())


def image_from_chw(raw):
    if len(raw) != INPUT_BYTES:
        raise ValueError(f'Expected {INPUT_BYTES} bytes, got {len(raw)}')
    channels = [Image.frombytes('L', (WIDTH, HEIGHT), raw[i:i + PLANE_BYTES])
                for i in range(0, INPUT_BYTES, PLANE_BYTES)]
    return Image.merge('RGB', channels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review_image', type=Path)
    parser.add_argument('--output', type=Path, required=True,
                        help='New output directory for input.bin and input.png')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    raw = prepare_review_image(args.review_image)
    sha = hashlib.sha256(raw).hexdigest()
    if args.expected_sha256 and sha != args.expected_sha256:
        raise ValueError('Converted bytes do not match the expected input hash')
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'input.bin').write_bytes(raw)
    image_from_chw(raw).save(args.output / 'input.png')
    print(sha)


if __name__ == '__main__':
    main()
