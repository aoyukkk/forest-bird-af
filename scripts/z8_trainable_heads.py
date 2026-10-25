"""Bounded head-only fine-tuning with the pinned resource744 forward arithmetic.

The original backbone and command stream remain frozen. Backward uses explicit
straight-through estimators (STE); it is not a derivative of integer arithmetic.
No vendor assets are included. Source packages must be supplied separately.
"""
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn


HEAD_BATCHES = {'coarse': (89, 90, 91), 'fine': (112, 113)}


class NativeSTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, a, b, operation):
        ctx.operation = operation
        ctx.a_shape, ctx.b_shape = a.shape, b.shape
        if operation == 'dot':
            ctx.save_for_backward(a, b)
            return ctx.core_model.dot(a, b)
        return ctx.core_model.add_carry(a, b)

    @staticmethod
    def backward(ctx, grad):
        if ctx.operation == 'dot':
            w, x = ctx.saved_tensors
            dw = torch.einsum('nohw,nihw->oi', grad.float(), x.float())
            dx = torch.einsum('oi,nohw->nihw', w.float(), grad.float())
            return dw, dx, None
        return grad.sum_to_size(ctx.a_shape), grad.sum_to_size(ctx.b_shape), None


class StorageSTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, value):
        return value.half().float()

    @staticmethod
    def backward(ctx, grad):
        return grad


def native_operation(model, a, b, kind):
    # Bind per-call rather than changing the frozen upstream functions.
    class BoundSTE(NativeSTE):
        @staticmethod
        def forward(ctx, a, b, operation):
            ctx.core_model = model
            return NativeSTE.forward(ctx, a, b, operation)
    return BoundSTE.apply(a, b, kind)


def head_events(model):
    batches = {x for v in HEAD_BATCHES.values() for x in v}
    return [v for _, kind, v in model.events if kind == 'matrix' and v['batch'] in batches]


def capture_features(backend, raw):
    """Capture actual matrix inputs without reconstructing a float backbone."""
    events = head_events(backend.model)
    mapping = {id(e['weight']): i for i, e in enumerate(events)}
    captures = {}
    original = backend.model.dot

    def tapped(w, x):
        if id(w) in mapping:
            captures[mapping[id(w)]] = x.detach().clone()
        return original(w, x)

    backend.model.dot = tapped
    try:
        outputs = backend.infer(raw)
    finally:
        # Restore the instance to the class implementation, avoiding recursion.
        del backend.model.dot
    if len(captures) != len(events):
        raise RuntimeError('Not every frozen head input was captured')
    # infer() deliberately uses inference_mode; materialize ordinary frozen
    # tensors outside that context so autograd may save them for STE backward.
    return {i: x.clone() for i, x in captures.items()}, outputs['heads']


class TrainableHeads(nn.Module):
    def __init__(self, backend):
        super().__init__()
        self.native = backend.model
        self.core = importlib.import_module('core')
        self.events = head_events(backend.model)
        self.weights = nn.ParameterList([nn.Parameter(e['weight'].detach().clone()) for e in self.events])
        self.biases = nn.ParameterDict({str(i): nn.Parameter(e['bias'].detach().clone())
                                       for i, e in enumerate(self.events) if e['bias'] is not None})
        self.groups = {}
        for i, event in enumerate(self.events):
            self.groups.setdefault(event['batch'], []).append(i)
        if set(self.groups) != {x for v in HEAD_BATCHES.values() for x in v}:
            raise ValueError('Unexpected native detection-head structure')
        for batch in self.groups:
            if any(lane[0] != 0 for lane in self.native.activations[batch]):
                raise ValueError('Only verified linear detection heads are supported')

    def forward(self, captures):
        outputs = {}
        for batch, indices in self.groups.items():
            acc = None
            for i in indices:
                event = self.events[i]
                flags = int(event['block']['flags'], 16)
                w = StorageSTE.apply(self.weights[i])
                part = native_operation(self.native, w, captures[i], 'dot')
                if flags & 512:
                    if acc is not None or str(i) not in self.biases:
                        raise RuntimeError('Unexpected accumulator start')
                    bias = StorageSTE.apply(self.biases[str(i)])[None, :, None, None]
                    acc = native_operation(self.native, bias, part, 'add')
                else:
                    if acc is None:
                        raise RuntimeError('Missing accumulator start')
                    acc = native_operation(self.native, acc, part, 'add')
                # Native additions already produce FTZ half values; the
                # subsequent RTZ/bank round is exactly idempotent here.
                if flags & 1024:
                    outputs[batch] = acc
                    acc = None
            if acc is not None:
                raise RuntimeError('Unfinished head accumulator')
        return {name: torch.cat([outputs[b] for b in batches], dim=1)[:, :channels]
                for (name, batches), channels in zip(HEAD_BATCHES.items(), (33, 22))}

    def export_body(self, upstream, target):
        """Change only the original head matrix/bias byte ranges in a copy."""
        source = (Path(upstream) / 'resource744.body.bin').read_bytes()
        result = bytearray(source)
        allowed = np.zeros(len(source), dtype=bool)
        segments = []
        for i, event in enumerate(self.events):
            block = event['block']
            pairs = [('weight', int(block['data_body_offset'], 16), self.weights[i])]
            if str(i) in self.biases:
                pairs.append(('bias', int(block['bias_body_offset'], 16), self.biases[str(i)]))
            for kind, offset, value in pairs:
                raw = value.detach().cpu().numpy().astype('<f2').tobytes()
                end = offset + len(raw)
                if end > len(source) or allowed[offset:end].any():
                    raise RuntimeError('Overlapping or out-of-range export segment')
                allowed[offset:end] = True
                result[offset:end] = raw
                segments.append({'batch': event['batch'], 'kind': kind, 'offset': offset,
                                 'length': len(raw), 'changed_bytes': sum(a != b for a, b in zip(source[offset:end], raw))})
        old = np.frombuffer(source, np.uint8)
        new = np.frombuffer(result, np.uint8)
        if np.any(old[~allowed] != new[~allowed]):
            raise RuntimeError('Export changed non-head bytes')
        Path(target).write_bytes(result)
        return {'original_sha256': hashlib.sha256(source).hexdigest(),
                'updated_sha256': hashlib.sha256(result).hexdigest(),
                'changed_bytes': int(np.count_nonzero(old != new)),
                'non_head_bytes_identical': True, 'segments': segments}


def apply_body_copy(backend, path):
    """Explicit local experiment loader; never overwrite the pinned package."""
    raw = Path(path).read_bytes()
    original = (backend.root / 'resource744.body.bin').read_bytes()
    allowed = np.zeros(len(original), dtype=bool)
    if len(raw) != len(original):
        raise RuntimeError('Model body size changed')
    events = head_events(backend.model)
    for e in events:
        block = e['block']
        offset = int(block['data_body_offset'], 16)
        allowed[offset:offset + 512] = True
        offset = block['bias_body_offset']
        if offset:
            offset = int(offset, 16)
            allowed[offset:offset + 32] = True
    if np.any(np.frombuffer(raw, np.uint8)[~allowed] != np.frombuffer(original, np.uint8)[~allowed]):
        raise RuntimeError('Changed instructions or backbone weights are not permitted')
    for e in events:
        block = e['block']; offset = int(block['data_body_offset'], 16)
        e['weight'] = torch.from_numpy(np.frombuffer(raw, '<f2', 256, offset).astype(np.float32).reshape(16, 16)).to(backend.device)
        if block['bias_body_offset']:
            offset = int(block['bias_body_offset'], 16)
            e['bias'] = torch.from_numpy(np.frombuffer(raw, '<f2', 16, offset).astype(np.float32)).to(backend.device)
    return hashlib.sha256(raw).hexdigest()


def bits(outputs):
    return {name: x.detach().cpu().numpy()[0].astype('<f2').view('<u2').copy() for name, x in outputs.items()}
