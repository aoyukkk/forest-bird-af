"""Device adapter for a separately obtained, hash-pinned E7 implementation.

No upstream source, weights or DLL is distributed here. CUDA execution is only
accepted after the independent validation script passes the physical fixtures.
"""
import hashlib
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

PIN = '8ced43b19edb845baef39a80c45d40be0b49efba'
BODY_SHA = 'e8d371e77efc3035d0c633c8c90aa4851f1675e5abcf7999edb23adc6439722b'


class Backend:
    def __init__(self, upstream, device='cuda', threads=4):
        self.root = Path(upstream).resolve()
        if hashlib.sha256((self.root / 'resource744.body.bin').read_bytes()).hexdigest() != BODY_SHA:
            raise ValueError('Unexpected model body')
        manifest = json.loads((self.root / 'manifest.json').read_text())
        for name, expected in manifest['files'].items():
            if hashlib.sha256((self.root / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Modified upstream file: ' + name)
        sys.path.insert(0, str(self.root))
        core = importlib.import_module('core')
        torch.set_num_threads(threads)
        self.device = torch.device(device)
        if self.device.type == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA requested but not available; no implicit fallback')
        original = getattr(core, '_original_rounded', core.rounded)
        core._original_rounded = original

        def device_rounded(x, mode='rne', ftz=False):
            if x.device.type != 'cuda' or x.dtype != torch.float64:
                return original(x, mode, ftz)
            h = x.to(torch.float16)
            if mode == 'rtz':
                exceeds = h.to(torch.float64).abs() > x.abs()
                h = torch.where(exceeds, (h.view(torch.int16) - 1).view(torch.float16), h)
            elif mode != 'rne':
                raise ValueError('Unvalidated CUDA rounding mode: ' + mode)
            y = h.float()
            if ftz:
                y = torch.where(y.abs() < 2.0 ** -14, torch.copysign(torch.zeros_like(y), y), y)
            return y

        core.rounded = core.round_half = device_rounded
        self.model = core.PhysicalStream()
        for _, kind, value in self.model.events:
            if kind == 'matrix':
                value['weight'] = value['weight'].to(self.device)
                if value['bias'] is not None:
                    value['bias'] = value['bias'].to(self.device)
        self.consumer = importlib.import_module('consumer').Consumer()
        self.pack_heads = importlib.import_module('consumer').pack_heads

    def infer_many(self, raws, include_workspace=False):
        if not raws or any(len(raw) != 294912 for raw in raws):
            raise ValueError('Expected CHW u8 [3,256,384]')
        values = np.frombuffer(b''.join(raws), np.uint8).reshape(len(raws), 3, 256, 384).astype(np.float32) / 256
        pixels = torch.from_numpy(values).to(self.device)
        holder = {}

        def trace(batch, layer, bank, x, y, z, banks, work):
            holder['work'] = work

        with torch.inference_mode(), torch.device(self.device):
            outputs = self.model(pixels, trace if include_workspace else None)
        heads = {name: value.cpu().numpy().astype('<f2').view('<u2').copy()
                 for name, value in zip(('fine', 'coarse'), outputs)}
        if not all(np.isfinite(value.view('<f2')).all() for value in heads.values()):
            raise RuntimeError('Nonfinite output; stop')
        result = {'heads': heads}
        if include_workspace:
            result['workspace'] = holder['work'][:, :0x60000 // 2].cpu().numpy().astype('<f2').view('<u2').copy()
        return result

    def infer(self, raw, include_workspace=False):
        result = self.infer_many([raw], include_workspace)
        result['heads'] = {key: value[0] for key, value in result['heads'].items()}
        if include_workspace:
            result['workspace'] = result['workspace'][0]
        return result

    def decode(self, heads):
        packed = self.pack_heads(heads['fine'].view('<f2'), heads['coarse'].view('<f2'))
        report = self.consumer.consume(packed)
        if report['status'] != 0:
            raise RuntimeError('Decoder failed: ' + str(report))
        return report, packed
