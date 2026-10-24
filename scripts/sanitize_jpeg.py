"""Remove JPEG metadata segments without changing compressed image samples.

Keep JFIF, ICC, and Adobe color markers. Preserve EXIF orientation in a new
minimal EXIF segment so downstream EXIF-oriented pixel decoding stays stable.
"""
import argparse
from pathlib import Path

from PIL import Image


def sanitize(raw, orientation):
    if raw[:2] != b'\xff\xd8':
        raise ValueError('Expected JPEG SOI')
    output = bytearray(raw[:2])
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        payload = exif.tobytes()
        output += b'\xff\xe1' + (len(payload) + 2).to_bytes(2, 'big') + payload
    offset = 2
    while offset < len(raw):
        start = offset
        if raw[offset] != 255:
            raise ValueError('Invalid JPEG marker')
        while offset < len(raw) and raw[offset] == 255:
            offset += 1
        marker = raw[offset]
        offset += 1
        if marker == 0xDA:
            output += raw[start:]
            return bytes(output)
        if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
            output += raw[start:offset]
            continue
        size = int.from_bytes(raw[offset:offset + 2], 'big')
        end = offset + size
        if size < 2 or end > len(raw):
            raise ValueError('Invalid JPEG segment length')
        payload = raw[offset + 2:end]
        metadata = 0xE0 <= marker <= 0xEF or marker == 0xFE
        keep = (marker == 0xE0 and payload.startswith(b'JFIF\x00')
                or marker == 0xE2 and payload.startswith(b'ICC_PROFILE\x00')
                or marker == 0xEE and payload.startswith(b'Adobe'))
        if not metadata or keep:
            output += raw[start:end]
        offset = end
    raise ValueError('Missing JPEG SOS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with Image.open(args.source) as image:
        orientation = image.getexif().get(274)
    result = sanitize(args.source.read_bytes(), orientation)
    with args.output.open('xb') as stream:
        stream.write(result)


if __name__ == '__main__':
    main()
