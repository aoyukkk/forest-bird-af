"""
nab_tool.py - Sony .nab (NA net asset bundle) parser for a1 II v4.00 firmware.

Recovered format notes
----------------------
File layout
   0x00  u32  magic-ish   "NA\\0\\0" (0x4E41)
   0x04  u32  version     78
   0x08  u32  =1
   0x0C  u32  network_count  17
   ...
   0x110 slot table, stride 0x30:
           u32 slot_id, u32 buf_size, u32 offA, u32 offB, u32 marker(32)
   0x510 first VPMN network descriptor

Network descriptor ("VPMN")
   0x00  "VPMN"
   0x04  u16 version   (0x0D / 0x0F / 0x16)
   0x06  u16 flag      (1)
   0x08  u32 name_len  (0xD4)
   0x0C  char name[name_len]

Tensor descriptor (name at +0x34)
   0x00  u32 marker      = 4
   0x04  u32 H
   0x08  u32 W
   0x0C  u32 C
   0x10  u32 1
   0x14  u32 1
   0x18  u32 1
   0x1C  u32 dtype       = 2 (int8)
   0x20  u32 0
   0x24  u32 2
   0x28  i32 zero_point
   0x2C  f32 scale
   0x30  u32 name_len
   0x34  char name[]

Layer record
   0x00  char name[0x40]
   0x40  u32 marker      = 1
   0x44  u32 layer_index
   0x48  char type[0x40]
"""
import struct, re, sys, os, json, hashlib

MAGIC = b'NA'

def cstr(data, off, maxlen=0x40):
    e = off
    lim = min(off + maxlen, len(data))
    while e < lim and data[e] != 0:
        e += 1
    return data[off:e].decode('ascii', 'replace')

class Nab:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        self.n = len(self.data)
        self.networks = self._parse_networks()

    def u32(self, o):
        return struct.unpack_from('<I', self.data, o)[0] if o+4 <= self.n else 0
    def i32(self, o):
        return struct.unpack_from('<i', self.data, o)[0] if o+4 <= self.n else 0
    def f32(self, o):
        return struct.unpack_from('<f', self.data, o)[0] if o+4 <= self.n else 0

    def _parse_networks(self):
        d = self.data
        pos, starts = 0, []
        while True:
            pos = d.find(b'VPMN', pos)
            if pos < 0: break
            starts.append(pos); pos += 4
        nets = []
        for k, vo in enumerate(starts):
            end = starts[k+1] if k+1 < len(starts) else self.n
            nets.append(dict(index=k, name=cstr(d, vo+12, self.u32(vo+8)),
                             version=struct.unpack_from('<H', d, vo+4)[0],
                             start=vo, end=end, size=end-vo))
        return nets

    def tensors(self, net):
        d = self.data
        out = []
        pat = rb'(?:uid_\d+_out_0|input\[\d+\]|output\[\d+\])'
        for m in re.finditer(pat, d[net['start']:net['end']]):
            rec = net['start'] + m.start() - 0x34
            if rec < net['start'] or self.u32(rec) != 4:
                continue
            out.append(dict(name=cstr(d, net['start']+m.start()),
                            H=self.u32(rec+4), W=self.u32(rec+8), C=self.u32(rec+0x0C),
                            dtype=self.u32(rec+0x1C),
                            zero_point=self.i32(rec+0x28), scale=self.f32(rec+0x2C)))
        return out

    def layers(self, net):
        d = self.data
        types = (rb'ConvolutionReluPoolingLayer2|ConvolutionReluPoolingLayer|'
                 rb'PoolingLayer2|ConvolutionLayer|ActivationLayer|ConcatLayer|'
                 rb'Softmax2Layer|FullyConnectedReluLayer|BatchNormalizationLayer|'
                 rb'DeConvolutionLayer|L2NormalizeLayer|NormalizeLayer')
        out = []
        for m in re.finditer(types, d[net['start']:net['end']]):
            typ_off = net['start'] + m.start()
            rec = typ_off - 0x48
            if rec < net['start']:
                continue
            out.append(dict(offset=rec, name=cstr(d, rec, 0x40),
                            index=self.u32(rec+0x44), type=m.group().decode()))
        return out

    def blob(self, net):
        return self.data[net['start']:net['end']]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    nab = Nab(sys.argv[1])
    print(f"{len(nab.networks)} networks in {sys.argv[1]}")
    for net in nab.networks:
        ts = nab.tensors(net)
        ins = [t for t in ts if t['name'].startswith('input')]
        heads = [t for t in ts if t['name'].startswith(('output', 'uid')) and t['H'] <= 4]
        print(f"\n[{net['index']:2}] {net['name']}  ver=0x{net['version']:X}  {net['size']} B")
        for t in ins:
            print(f"      IN   {t['H']:>4}x{t['W']:<4}x{t['C']:<4} zp={t['zero_point']:<5} scale={t['scale']:.8g}")
        for t in heads:
            print(f"      HEAD {t['name']:<18} {t['H']}x{t['W']}x{t['C']}")
