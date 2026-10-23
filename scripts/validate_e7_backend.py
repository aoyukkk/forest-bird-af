"""Validate resource identity, public physical fixtures and CPU/CUDA agreement."""
import argparse
import hashlib
import json
import struct
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

from e7_backend import Backend, PIN, BODY_SHA


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--z8-resource', type=Path, required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    report = {'passed': False, 'upstream_commit': PIN, 'torch': torch.__version__,
              'numpy': np.__version__, 'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              'cases': [], 'class_semantics_confirmed': False}

    def save():
        (a.output / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    save()
    try:
        resource = a.z8_resource.read_bytes()
        off, size = struct.unpack_from('<QQ', resource, 0x18)
        body = resource[off:off + size]
        report['body_byte_identical'] = body == (a.upstream / 'resource744.body.bin').read_bytes()
        report['body_sha256'] = hashlib.sha256(body).hexdigest()
        if not report['body_byte_identical'] or report['body_sha256'] != BODY_SHA:
            raise ValueError('Model identity gate failed')
        gpu = Backend(a.upstream, 'cuda')
        index = json.loads((a.upstream / 'fixtures/index.json').read_text())
        mask = np.load(a.upstream / 'fixtures/workspace-mask.npy')
        for case in index['cases']:
            root = a.upstream / 'fixtures' / case['name']
            raw = (root / 'input-chw-u8.bin').read_bytes()
            start = time.perf_counter()
            got = gpu.infer(raw, True)
            wanted = np.load(root / 'expected.npz')
            differences = {key: int(np.count_nonzero(got['heads'][key] != wanted[key])) for key in ('fine', 'coarse')}
            differences['workspace'] = int(np.count_nonzero(got['workspace'][mask] != wanted['defined_workspace']))
            decoded, _ = gpu.decode(got['heads'])
            row = {'case': case['name'], 'differences': differences,
                   'decoder_equal': decoded['records'] == case['expected_records'],
                   'seconds': time.perf_counter() - start}
            report['cases'].append(row)
            save()
            print(json.dumps(row), flush=True)
            if any(differences.values()) or not row['decoder_equal']:
                raise RuntimeError('CUDA physical fixture mismatch; do not batch annotate')
        with Image.open(a.image) as image:
            rgb = ImageOps.exif_transpose(image).convert('RGB').resize((384, 256), Image.Resampling.BILINEAR)
            raw = np.asarray(rgb).transpose(2, 0, 1).copy().tobytes()
        start = time.perf_counter()
        first = gpu.infer(raw)
        report['real_image_gpu_seconds'] = time.perf_counter() - start
        again = gpu.infer(raw)
        cpu = Backend(a.upstream, 'cpu')
        start = time.perf_counter()
        reference = cpu.infer(raw)
        report['real_image_cpu_seconds'] = time.perf_counter() - start
        report['real_image_cpu_gpu_differences'] = {
            key: int(np.count_nonzero(first['heads'][key] != reference['heads'][key])) for key in ('fine', 'coarse')}
        report['gpu_repeat_differences'] = {
            key: int(np.count_nonzero(first['heads'][key] != again['heads'][key])) for key in ('fine', 'coarse')}
        report['real_image_input_sha256'] = hashlib.sha256(raw).hexdigest()
        decoded, packed = gpu.decode(first['heads'])
        report['real_image_records'] = decoded['records']
        (a.output / 'real-head-buffer.bin').write_bytes(packed)
        np.savez_compressed(a.output / 'real-heads.npz', **first['heads'])
        if any(report['real_image_cpu_gpu_differences'].values()) or any(report['gpu_repeat_differences'].values()):
            raise RuntimeError('CPU/GPU or repeat gate failed')
        report['passed'] = True
    except BaseException as error:
        report['error'] = repr(error)
        save()
        raise
    save()
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
