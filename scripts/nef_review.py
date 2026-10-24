"""Verify preserved TIFF image segments and extract a Nikon embedded JPEG."""
import hashlib
import io
import struct
import subprocess

from PIL import Image, ImageOps
from sanitize_jpeg import sanitize


def image_segments(path):
    """Hash every strip/tile and JPEG range referenced by standard TIFF IFDs.

    This checks compressed bytes without claiming a decoded sensor-sample check.
    Offsets may change when metadata is rewritten; image payloads must not.
    """
    blob = path.read_bytes()
    endian = {'little': '<', 'big': '>'}[
        'little' if blob[:2] == b'II' else 'big']
    assert blob[:2] in (b'II', b'MM')
    u16 = lambda p: struct.unpack_from(endian + 'H', blob, p)[0]
    u32 = lambda p: struct.unpack_from(endian + 'I', blob, p)[0]
    assert u16(2) == 42, 'Only classic TIFF is supported'
    pending, seen, records = [u32(4)], set(), []
    while pending:
        offset = pending.pop(0)
        if not offset or offset in seen:
            continue
        seen.add(offset)
        count = u16(offset)
        assert count < 10000 and offset + 2 + count * 12 + 4 <= len(blob)
        tags = {}
        for index in range(count):
            pos = offset + 2 + index * 12
            tag, kind, length = u16(pos), u16(pos + 2), u32(pos + 4)
            if tag not in {256, 257, 259, 273, 279, 324, 325, 330, 513, 514}:
                continue
            assert kind in (3, 4, 13), (tag, kind)
            size = 2 if kind == 3 else 4
            loc = pos + 8 if size * length <= 4 else u32(pos + 8)
            assert loc + size * length <= len(blob)
            read = u16 if size == 2 else u32
            tags[tag] = [read(loc + size * i) for i in range(length)]
        pending.extend(tags.get(330, []))
        pending.append(u32(offset + 2 + count * 12))
        for offsets, sizes, label in [(273, 279, 'strip'), (324, 325, 'tile'), (513, 514, 'jpeg')]:
            if offsets not in tags and sizes not in tags:
                continue
            assert offsets in tags and sizes in tags and len(tags[offsets]) == len(tags[sizes])
            segments = []
            for start, size in zip(tags[offsets], tags[sizes]):
                if size == 0:
                    assert tags.get(256) == [0] and tags.get(257) == [0], 'Unexpected empty image range'
                    assert 0 <= start <= len(blob), 'Empty placeholder offset outside TIFF'
                    continue
                assert size > 0 and start + size <= len(blob)
                segments.append({'bytes': size, 'sha256': hashlib.sha256(blob[start:start + size]).hexdigest()})
            if not segments:
                continue
            records.append({'kind': label, 'width': tags.get(256), 'height': tags.get(257),
                            'compression': tags.get(259), 'segments': segments})
    assert records and any(r['kind'] in ('strip', 'tile') for r in records)
    return records


def embedded_review(source, output, exiftool):
    proc = subprocess.run([str(exiftool), '-b', '-JpgFromRaw', str(source)], capture_output=True)
    if proc.returncode or not proc.stdout.startswith(b'\xff\xd8'):
        raise RuntimeError('JpgFromRaw extraction failed')
    original = proc.stdout
    with Image.open(io.BytesIO(original)) as image:
        orientation = image.getexif().get(274)
        expected = ImageOps.exif_transpose(image).convert('RGB')
    cleaned = sanitize(original, orientation)
    output.write_bytes(cleaned)
    with Image.open(output) as image:
        actual = ImageOps.exif_transpose(image).convert('RGB')
    assert actual.size == expected.size and actual.tobytes() == expected.tobytes()
    return actual, {'review_origin': 'NEF JpgFromRaw camera-embedded JPEG',
                    'embedded_jpeg_sha256': hashlib.sha256(original).hexdigest(),
                    'embedded_jpeg_decoded_pixels_unchanged': True}
