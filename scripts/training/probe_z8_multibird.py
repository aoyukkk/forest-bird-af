"""Read-only native multi-bird/ID probe using exact saved model inputs."""
import argparse
import hashlib
import html
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from e7_backend import Backend

COLORS = ['#ff7970', '#77dba5', '#70bfff', '#ffd974', '#cda4fa', '#edf1f5']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('upstream', 'z8-package', 'workspace', 'frozen-runs', 'output'):
        p.add_argument('--' + key, required=True, type=Path)
    p.add_argument('--ids', nargs='+', required=True)
    a = p.parse_args(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(a.z8_package.resolve()))
    from z8models.native_post import decode_raw
    backend = Backend(a.upstream, 'cuda')
    uri = (a.workspace / 'annotations.sqlite3').resolve().as_uri() + '?mode=ro'
    report = {'passed': False, 'source': 'unchanged original resource744', 'cases': [],
              'proposal_id_meaning': 'pN is the current decoded-list index, not a bird identity or track',
              'production_annotation_writes': 0}

    def save():
        (out / 'probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    save()
    with sqlite3.connect(uri, uri=True) as c:
        for ident in a.ids:
            meta, saved_pred = c.execute('SELECT metadata,predictions FROM images WHERE id=?', (ident,)).fetchone()
            meta, saved_pred = json.loads(meta), json.loads(saved_pred)
            for flip in (False, True):
                im = Image.open(a.workspace / 'images' / (ident + '.png')).convert('RGB')
                if flip:
                    im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                raw = np.asarray(im).transpose(2, 0, 1).copy().tobytes()
                if not flip and hashlib.sha256(raw).hexdigest() != meta['input_sha256']:
                    raise RuntimeError('Input identity changed')
                got = backend.infer(raw)['heads']
                frozen_diff = None
                if not flip:
                    sources = list(a.frozen_runs.glob('run_*/heads/' + ident + '.npz'))
                    if len(sources) != 1:
                        raise RuntimeError('Frozen head source ambiguous')
                    with np.load(sources[0]) as wanted:
                        frozen_diff = {k: int(np.count_nonzero(got[k] != wanted[k])) for k in got}
                    if any(frozen_diff.values()):
                        raise RuntimeError('Original native heads changed')
                packed = backend.pack_heads(got['fine'].view('<f2'), got['coarse'].view('<f2'))
                native = decode_raw(packed, 744)
                host, _ = backend.decode(got)
                expected = [[*x['center_xy'], *x['size_wh'], x['score_milli'], x['ipu_class_id']] for x in native['candidates']]
                if host['records'] != expected:
                    raise RuntimeError('Decoder mismatch')
                rows = [{'proposal_id': f'p{i}', 'slot': v['ipu_class_id'], 'box_xyxy': v['box_xyxy'], 'score': v['score_milli']}
                        for i, v in enumerate(native['candidates'])]
                if not flip:
                    expected_saved = [(x['class_slot'], x['box_input_xyxy'], x['native_integer_score']) for x in saved_pred]
                    if [(x['slot'], x['box_xyxy'], x['score']) for x in rows] != expected_saved:
                        raise RuntimeError('Registered candidate order changed')
                key = ident + ('-mirror' if flip else '-original')
                im.save(out / (key + '-input.png'))
                font_path = Path('C:/Windows/Fonts/consola.ttf')
                font = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()
                overlay = Image.new('RGB', (1100, 560), '#14202c')
                overlay.paste(im.resize((768, 512), Image.Resampling.NEAREST), (0, 40))
                d = ImageDraw.Draw(overlay); d.text((10, 7), key + ' | proposal ID / native slot', fill='white', font=font)
                for row in rows:
                    box = row['box_xyxy']; b = [box[0] * 2, box[1] * 2 + 40, box[2] * 2, box[3] * 2 + 40]
                    color = COLORS[row['slot']]
                    d.rectangle(b, outline=color, width=2)
                    d.rectangle((b[0], b[1], b[0] + 30, b[1] + 20), fill='#14202c')
                    d.text((b[0], b[1]), row['proposal_id'], fill=color, font=font)
                    d.text((780, 48 + int(row['proposal_id'][1:]) * 42), f'{row["proposal_id"]}  slot {row["slot"]}  score {row["score"]}', fill=color, font=font)
                overlay.save(out / (key + '-ids.png'))
                row = {'image_id': ident, 'horizontal_flip': flip, 'input_sha256': hashlib.sha256(raw).hexdigest(),
                       'frozen_head_bit_differences': frozen_diff, 'native_decoders_agree': True,
                       'proposals': rows, 'overlay': key + '-ids.png'}
                report['cases'].append(row); save(); print(json.dumps(row), flush=True)
    pairs = []
    for ident in a.ids:
        original, mirror = [r for r in report['cases'] if r['image_id'] == ident]
        for old in original['proposals']:
            old_center = [(old['box_xyxy'][0] + old['box_xyxy'][2]) / 2, (old['box_xyxy'][1] + old['box_xyxy'][3]) / 2]
            # CHW image pixel centers reflect at x -> 383-x. Native decoded
            # integer coordinates and clipping can add another pixel of error.
            wanted = [383 - old_center[0], old_center[1]]
            allowed = (2, 3) if old['slot'] in (2, 3) else (old['slot'],)
            candidates = []
            for new in mirror['proposals']:
                if new['slot'] not in allowed:
                    continue
                b = new['box_xyxy']; center = [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
                distance = sum((x - y)**2 for x, y in zip(center, wanted))**.5
                if distance <= 8:
                    candidates.append((distance, new))
            if candidates:
                distance, new = min(candidates, key=lambda x: x[0])
                pairs.append({'image_id': ident, 'original_id': old['proposal_id'], 'original_slot': old['slot'],
                              'mirror_id': new['proposal_id'], 'mirror_slot': new['slot'], 'center_error_pixels': distance})
    report.update(passed=True, spatial_mirror_matches=pairs,
                  mirror_matching_scope='nearest same-slot (eye pair 2/3 allowed), center error <=8 input pixels; analysis only, not object tracking')
    save()
    body = ['<!doctype html><meta charset="utf-8"><title>Z8 proposal IDs</title><style>body{background:#14202c;color:#e5edf4;font:16px system-ui;margin:24px}img{max-width:100%}a{color:#8fd5c5}</style>',
            '<h1>Z8 多鸟候选编号 / Multi-bird proposal IDs</h1><p>pN 是本张输出列表编号，不是鸟实例或跟踪 ID。slot 是模型类别槽。镜像图仅作受控诊断，不是新独立样本。</p>']
    for case in report['cases']:
        body.append('<h2>' + html.escape(case['image_id'] + (' mirror' if case['horizontal_flip'] else ' original')) + '</h2><img src="' + case['overlay'] + '">')
    body.append('<p><a href="probe.json">Exact proposals, scores and mirror matches</a></p>')
    (out / 'index.html').write_text('\n'.join(body), encoding='utf-8')


if __name__ == '__main__':
    main()
