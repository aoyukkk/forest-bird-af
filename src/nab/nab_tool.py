#!/usr/bin/env python3
"""
nab_tool.py - Sony .nab (NA network asset bundle) container parser.

公开内容：容器结构、网络拓扑、输入输出形状、量化参数、边界与哈希。
不公开：权重 payload 本体与内部排布。

格式说明见 docs/format/NAB-FORMAT.md

用法
    python nab_tool.py list   <default.nab>
    python nab_tool.py split  <default.nab> -o <输出目录>
    python nab_tool.py verify <default.nab>

依赖：仅标准库。
"""
import argparse
import hashlib
import json
import os
import re
import struct
import sys

MAGIC = b'NA'
VPMN = b'VPMN'

LAYER_TYPES = (
    rb'ConvolutionReluPoolingLayer2|ConvolutionReluPoolingLayer|'
    rb'PoolingLayer2|PoolingLayer|ConvolutionLayer|ActivationLayer|'
    rb'ConcatLayer|Softmax2Layer|SoftmaxLayer|FullyConnectedReluLayer|'
    rb'FullyConnectedLayer|BatchNormalizationLayer|DeConvolutionLayer|'
    rb'L2NormalizeLayer|NormalizeLayer|EltwiseLayer|ReshapeLayer'
)

TENSOR_NAMES = rb'(?:uid_\d+_out_0|input\[\d+\]|output\[\d+\])'


def cstr(data, off, maxlen):
    end = off
    limit = min(off + maxlen, len(data))
    while end < limit and data[end] != 0:
        end += 1
    return data[off:end].decode('ascii', 'replace')


class Nab:
    """解析 .nab 容器。只读结构，不触碰权重语义。"""

    def __init__(self, path):
        with open(path, 'rb') as f:
            self.data = f.read()
        self.path = path
        self.n = len(self.data)
        if self.data[:2] != MAGIC:
            raise ValueError('不是 .nab 文件：魔数不匹配')
        self.declared_count = self.u32(0x0C)
        self.networks = self._scan_networks()

    # ---- 基础读取 ----
    def u32(self, o):
        return struct.unpack_from('<I', self.data, o)[0] if o + 4 <= self.n else 0

    def i32(self, o):
        return struct.unpack_from('<i', self.data, o)[0] if o + 4 <= self.n else 0

    def f32(self, o):
        return struct.unpack_from('<f', self.data, o)[0] if o + 4 <= self.n else 0

    # ---- 网络扫描 ----
    def _scan_networks(self):
        starts = []
        pos = 0
        while True:
            pos = self.data.find(VPMN, pos)
            if pos < 0:
                break
            starts.append(pos)
            pos += 4

        nets = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else self.n
            nets.append({
                'index': i,
                'name': cstr(self.data, start + 12, self.u32(start + 8)),
                'version': struct.unpack_from('<H', self.data, start + 4)[0],
                'start': start,
                'end': end,
                'size': end - start,
            })
        return nets

    # ---- 张量 ----
    def tensors(self, net):
        out = []
        s, e = net['start'], net['end']
        for m in re.finditer(TENSOR_NAMES, self.data[s:e]):
            rec = s + m.start() - 0x34
            if rec < s or self.u32(rec) != 4:
                continue
            out.append({
                'name': cstr(self.data, s + m.start(), 0x40),
                'H': self.u32(rec + 0x04),
                'W': self.u32(rec + 0x08),
                'C': self.u32(rec + 0x0C),
                'dtype': self.u32(rec + 0x1C),
                'fixed_pos': self.i32(rec + 0x28),
                'scale': self.f32(rec + 0x2C),
            })
        return out

    # ---- 层 ----
    def layers(self, net):
        out = []
        s, e = net['start'], net['end']
        for m in re.finditer(LAYER_TYPES, self.data[s:e]):
            type_off = s + m.start()
            rec = type_off - 0x48
            if rec < s:
                continue
            out.append({
                'offset': f'0x{rec:X}',
                'input_name': cstr(self.data, rec, 0x40),
                'index': self.u32(rec + 0x44),
                'type': m.group().decode(),
            })
        return out

    # ---- 槽位表 ----
    def slots(self):
        """扫描槽位表。

        实测布局：0x110 起步长 0x30，条目首个 u32 为 slot_id，
        +0x04 buf_size，+0x08/+0x0C 两个缓冲偏移，+0x10 恒为 32。
        条目之间可能夹着全零行，跳过而非中断。
        """
        out = []
        off = 0x110
        limit = min(self.n, 0x400)
        while off + 0x20 <= limit:
            sid = self.u32(off)
            size = self.u32(off + 0x04)
            off_a = self.u32(off + 0x08)
            off_b = self.u32(off + 0x0C)
            marker = self.u32(off + 0x10)
            if marker == 32 and (sid or size):
                out.append({'slot': sid, 'buf_size': size,
                            'offset_a': off_a, 'offset_b': off_b})
            off += 0x30
        return out

    # ---- 汇总 ----
    def summary(self, net):
        ts = self.tensors(net)
        ls = self.layers(net)
        ins = [t for t in ts if t['name'].startswith('input')]
        outs = [t for t in ts if t['name'].startswith('output')]
        heads = [t for t in ts if t['name'].startswith('uid') and t['H'] <= 4]

        type_count = {}
        for l in ls:
            type_count[l['type']] = type_count.get(l['type'], 0) + 1

        return {
            'net': net['index'],
            'name': net['name'],
            'version': f'0x{net["version"]:X}',
            'start': f'0x{net["start"]:X}',
            'end': f'0x{net["end"]:X}',
            'size': net['size'],
            'sha256': hashlib.sha256(
                self.data[net['start']:net['end']]).hexdigest(),
            'inputs': ins,
            'declared_outputs': outs,
            'leaf_heads': heads,
            'layer_type_counts': type_count,
            'layer_count': len(ls),
        }

    def blob(self, net):
        return self.data[net['start']:net['end']]


# ---- 命令实现 ----

def cmd_list(nab, args):
    print(f'文件: {nab.path}')
    print(f'大小: {nab.n} B')
    print(f'头部声明网络数: {nab.declared_count}')
    print(f'实际扫描网络数: {len(nab.networks)}')
    print()

    for net in nab.networks:
        s = nab.summary(net)
        print(f'[{s["net"]:2}] {s["name"]}')
        print(f'     版本 {s["version"]}  偏移 {s["start"]}..{s["end"]}  {s["size"]} B  层数 {s["layer_count"]}')
        for t in s['inputs']:
            print(f'     IN   {t["H"]:>4}x{t["W"]:<4}x{t["C"]:<4}  '
                  f'scale={t["scale"]:.8g}  fixed_pos={t["fixed_pos"]}')
        for t in s['leaf_heads']:
            print(f'     HEAD {t["name"]:<18} {t["H"]}x{t["W"]}x{t["C"]}')
        for t in s['declared_outputs']:
            print(f'     OUT  {t["name"]:<18} {t["H"]}x{t["W"]}x{t["C"]}')
        print()


def cmd_split(nab, args):
    os.makedirs(args.output, exist_ok=True)
    manifest = []
    for net in nab.networks:
        s = nab.summary(net)
        safe = re.sub(r'[^A-Za-z0-9._-]', '_', net['name'])[:60]
        fn = f'{net["index"]:02d}_{safe}.vvpm'
        path = os.path.join(args.output, fn)
        with open(path, 'wb') as f:
            f.write(nab.blob(net))
        s['file'] = fn
        manifest.append(s)
        print(f'[{net["index"]:2}] {fn}  {net["size"]} B')

    meta = {
        'source': os.path.basename(nab.path),
        'source_size': nab.n,
        'source_sha256': hashlib.sha256(nab.data).hexdigest(),
        'network_count': len(nab.networks),
        'networks': manifest,
        'notice': '本清单只含结构信息与哈希，不含权重语义。见 docs/format/NAB-FORMAT.md',
    }
    with open(os.path.join(args.output, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print(f'\n清单已写入 {os.path.join(args.output, "manifest.json")}')
    print(f'注意：切分结果不得提交到公开仓库（scripts/tools/verify_repo.py 会拦截）')


def cmd_verify(nab, args):
    ok = True
    print('=== 校验 1：网络数量 ===')
    if nab.declared_count == len(nab.networks):
        print(f'  通过：头部声明 {nab.declared_count}，实扫 {len(nab.networks)}')
    else:
        print(f'  失败：头部声明 {nab.declared_count}，实扫 {len(nab.networks)}')
        ok = False

    print('\n=== 校验 2：边界首尾相接 ===')
    gaps = 0
    for i in range(len(nab.networks) - 1):
        if nab.networks[i]['end'] != nab.networks[i + 1]['start']:
            print(f'  断裂：net[{i}].end=0x{nab.networks[i]["end"]:X} '
                  f'!= net[{i+1}].start=0x{nab.networks[i+1]["start"]:X}')
            gaps += 1
    print(f'  {"通过：无断裂" if gaps == 0 else f"失败：{gaps} 处断裂"}')
    ok = ok and gaps == 0

    print('\n=== 校验 3：总长匹配 ===')
    total = sum(n['size'] for n in nab.networks)
    diff = nab.n - total
    print(f'  网络总长 {total} B，文件 {nab.n} B，差 {diff} B（头部+槽位表）')
    if 0 < diff < 0x2000:
        print('  通过：差值在合理范围')
    else:
        print('  失败：差值异常')
        ok = False

    print('\n=== 校验 4：切片唯一性 ===')
    hashes = {}
    dup = 0
    for net in nab.networks:
        h = hashlib.sha256(nab.blob(net)).hexdigest()
        if h in hashes:
            print(f'  重复：net[{net["index"]}] 与 net[{hashes[h]}] 相同')
            dup += 1
        else:
            hashes[h] = net['index']
    print(f'  {"通过：全部唯一" if dup == 0 else f"失败：{dup} 处重复"}')
    ok = ok and dup == 0

    print('\n=== 校验 5：槽位 buf_size 可分解 ===')
    checked = 0
    for slot in nab.slots():
        size = slot['buf_size']
        found = []
        for net in nab.networks:
            for t in nab.tensors(net):
                if not t['name'].startswith('input'):
                    continue
                if t['H'] * t['W'] * t['C'] == size:
                    found.append(f'net[{net["index"]}]')
        if found:
            checked += 1
            print(f'  slot {slot["slot"]:<3} {size:>9} -> {", ".join(found)}')
        else:
            print(f'  slot {slot["slot"]:<3} {size:>9} -> 未匹配（可能是中间缓冲）')
    print(f'  已匹配 {checked} 个槽位')

    print()
    print('结论：全部通过' if ok else '结论：存在失败项')
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description='Sony .nab 容器解析器（只读结构，不含权重语义）')
    sub = p.add_subparsers(dest='cmd', required=True)

    for name, help_text in [
        ('list', '列出所有网络及输入输出'),
        ('split', '按网络边界切分'),
        ('verify', '校验解析完整性'),
    ]:
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument('nab', help='default.nab 路径')
        if name == 'split':
            sp.add_argument('-o', '--output', required=True, help='输出目录')

    args = p.parse_args()
    if not os.path.exists(args.nab):
        print(f'文件不存在: {args.nab}', file=sys.stderr)
        return 1

    nab = Nab(args.nab)
    return {
        'list': cmd_list,
        'split': cmd_split,
        'verify': cmd_verify,
    }[args.cmd](nab, args) or 0


if __name__ == '__main__':
    sys.exit(main())
