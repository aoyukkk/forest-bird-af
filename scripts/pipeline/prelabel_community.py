import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'training'))
"""Generate review-only raw-class Z8 proposals using validated E7 CUDA heads.

The original local Z8 BA2 postprocessor is retained. No proposal is promoted to
human ground truth or a named eye/head/bird class by this program.
"""
import argparse
import collections
import hashlib
import html
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageOps

from e7_backend import Backend, PIN, BODY_SHA


def review_page(rows, out):
    data = []
    for row in rows:
        data.append({'id': row['image_id'], 'count': len(row['candidates']),
                     'overlay': 'overlays/' + row['image_id'] + '.jpg',
                     'image': row['review_relative_path']})
    body = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>Z8 预标注复核</title><style>
body{font:16px system-ui;background:#101820;color:#eee;margin:24px}button,select{padding:9px;margin:5px}header{position:sticky;top:0;background:#101820;padding:12px;z-index:2}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}.card{background:#1c2a35;padding:14px;border-radius:12px}img{width:100%;height:260px;object-fit:contain}a{color:#8dd8ff}.small{font-size:13px;color:#bbc}
</style><header><h1>Z8 原始类号预标注 · 待人工复核</h1>
<p>请检查整张图，尤其是没有框的图。slot 0–5 未映射为眼/头/鸟；这些框不是人工真值。未检测到候选不代表无鸟。</p>
<select id="filter"><option value="all">全部</option><option value="zero">无候选，优先查漏检</option><option value="pending">未复核</option><option value="error">已标为错误</option></select>
<button id="toggle">切换：原图/带框</button><button id="export">导出复核决定 JSON</button><span id="summary"></span>
<p class="small">决定仅保存于当前浏览器 localStorage。结束时请导出；清除浏览器数据会丢失未导出的决定。此页不自动生成训练标签。</p></header><main class="grid" id="grid"></main>
<script>const rows=__DATA__;let overlay=true;const key='forest-bird-z8-prelabel-20261024-v1';let decisions={};try{decisions=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){};
function render(){const f=document.getElementById('filter').value;const selected=rows.filter(r=>f==='all'||f==='zero'&&r.count===0||f==='pending'&&!decisions[r.id]||f==='error'&&decisions[r.id]?.decision==='error');document.getElementById('grid').innerHTML=selected.map(r=>`<article class="card"><b>${r.id}</b> · ${r.count} 个原始候选<a href="${overlay?r.overlay:r.image}" target="_blank"><img loading="lazy" src="${overlay?r.overlay:r.image}"></a><div><a href="${r.image}" target="_blank">打开完整审核图</a></div><select data-id="${r.id}"><option value="">未复核</option><option value="correct">框位置正确，保留</option><option value="error">漏检/误框/需修改</option><option value="uncertain">不确定，需裁决</option></select><textarea data-note="${r.id}" placeholder="错误类型、漏掉哪只鸟等" style="width:95%;height:54px"></textarea></article>`).join('');document.querySelectorAll('[data-id]').forEach(s=>{s.value=decisions[s.dataset.id]?.decision||'';s.onchange=()=>{decisions[s.dataset.id]={decision:s.value,note:decisions[s.dataset.id]?.note||'',at:new Date().toISOString()};save()}});document.querySelectorAll('[data-note]').forEach(s=>{s.value=decisions[s.dataset.note]?.note||'';s.onchange=()=>{decisions[s.dataset.note]={decision:decisions[s.dataset.note]?.decision||'',note:s.value,at:new Date().toISOString()};save()}});document.getElementById('summary').textContent=`显示 ${selected.length}/${rows.length}；已有决定 ${Object.values(decisions).filter(x=>x.decision).length}`}
function save(){localStorage.setItem(key,JSON.stringify(decisions));document.getElementById('summary').textContent=`总计 ${rows.length}；已有决定 ${Object.values(decisions).filter(x=>x.decision).length}`}
document.getElementById('filter').onchange=render;document.getElementById('toggle').onclick=()=>{overlay=!overlay;render()};document.getElementById('export').onclick=()=>{const payload={schema:'prediction-assisted-review-v1',created_at:new Date().toISOString(),review_with_predictions:true,class_semantics_confirmed:false,decisions};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));a.download='z8-review-decisions.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)};render();</script>'''
    (out / 'review.html').write_text(body.replace('__DATA__', json.dumps(data).replace('</', '<\\/')), encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream', type=Path, required=True)
    p.add_argument('--z8-package', type=Path, required=True)
    p.add_argument('--snapshot', type=Path, required=True)
    p.add_argument('--validation', type=Path, required=True)
    p.add_argument('--batch-validation', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    valid = json.loads(a.validation.read_text())
    batch_valid = json.loads(a.batch_validation.read_text())
    if not valid['passed'] or not batch_valid['passed'] or not valid['body_byte_identical']:
        raise RuntimeError('Required numerical gates not passed')
    if not json.loads((a.snapshot / 'image-validation.json').read_text())['passed']:
        raise RuntimeError('Image integrity gate not passed')
    metadata = json.loads((a.snapshot / 'manifest.json').read_text())
    out = a.output.resolve()
    if not a.resume:
        out.mkdir(parents=True, exist_ok=False)
    for name in ('predictions', 'heads', 'inputs', 'overlays'):
        (out / name).mkdir(exist_ok=a.resume)
    sys.path.insert(0, str(a.z8_package))
    from z8models.native_post import decode_raw
    model = Backend(a.upstream, 'cuda')
    batch_size = batch_valid['batch_size']
    pending, completed = [], []
    for row in metadata:
        target = out / 'predictions' / (row['image_id'] + '.json')
        if a.resume and target.exists():
            old = json.loads(target.read_text())
            if old['review_sha256'] != row['review_sha256']:
                raise RuntimeError('Resume image changed')
            completed.append(old)
        else:
            pending.append(row)
    report = {'complete': False, 'images_expected': len(metadata), 'images_completed': len(completed),
              'failed': [], 'backend': 'CUDA E7 numerical profile with original local Z8 BA2 postprocessor',
              'upstream_commit': PIN, 'body_sha256': BODY_SHA, 'gpu': torch.cuda.get_device_name(0),
              'torch': torch.__version__, 'batch_size': batch_size,
              'class_semantics_confirmed': False, 'human_review_complete': False,
              'training_started': False, 'batches': []}

    def save():
        (out / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    save()
    try:
        for offset in range(0, len(pending), batch_size):
            batch = pending[offset:offset + batch_size]
            raws = []
            for row in batch:
                path = a.snapshot / row['review_file']
                if hashlib.sha256(path.read_bytes()).hexdigest() != row['review_sha256']:
                    raise RuntimeError('Review image changed: ' + row['image_id'])
                with Image.open(path) as image:
                    rgb = ImageOps.exif_transpose(image).convert('RGB')
                    if rgb.size != (row['width'], row['height']):
                        raise RuntimeError('Review dimensions changed')
                    prepared = rgb.resize((384, 256), Image.Resampling.BILINEAR)
                raws.append(np.asarray(prepared).transpose(2, 0, 1).copy().tobytes())
            start = time.perf_counter()
            got = model.infer_many(raws)
            seconds = time.perf_counter() - start
            for i, row in enumerate(batch):
                image_id = row['image_id']
                heads = {key: value[i] for key, value in got['heads'].items()}
                packed = model.pack_heads(heads['fine'].view('<f2'), heads['coarse'].view('<f2'))
                decoded = decode_raw(packed, 744)
                candidates = []
                sx, sy = row['width'] / 384, row['height'] / 256
                for proposal in decoded['candidates']:
                    box = proposal['box_xyxy']
                    candidates.append({'class_slot': proposal['ipu_class_id'],
                        'native_integer_score': proposal['score_milli'],
                        'box_input_xyxy': box,
                        'box_review_xyxy': [box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy],
                        'semantic_label': None})
                record = {'image_id': image_id, 'review_sha256': row['review_sha256'],
                    'width': row['width'], 'height': row['height'],
                    'review_relative_path': os.path.relpath(a.snapshot / row['review_file'], out).replace('\\', '/'),
                    'preprocess_id': 'review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1',
                    'input_sha256': hashlib.sha256(raws[i]).hexdigest(),
                    'candidates': candidates, 'annotation_status': 'pending',
                    'instances': None, 'presence': None, 'review_decision': None,
                    'class_semantics_confirmed': False, 'human_review_complete': False}
                (out / 'inputs' / (image_id + '.bin')).write_bytes(raws[i])
                np.savez_compressed(out / 'heads' / (image_id + '.npz'), **heads)
                with Image.open(a.snapshot / row['review_file']) as image:
                    display = ImageOps.exif_transpose(image).convert('RGB')
                display.thumbnail((1800, 1400), Image.Resampling.LANCZOS)
                draw = ImageDraw.Draw(display)
                colors = ['#ff5555', '#44ff99', '#44bbff', '#ffcc55', '#dd88ff', '#ffffff']
                for proposal in candidates:
                    x1, y1, x2, y2 = proposal['box_review_xyxy']
                    x1, x2 = np.clip([x1, x2], 0, row['width']) * display.width / row['width']
                    y1, y2 = np.clip([y1, y2], 0, row['height']) * display.height / row['height']
                    if x2 <= x1 or y2 <= y1:
                        continue
                    color = colors[proposal['class_slot']]
                    draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
                    draw.text((x1, max(0, y1 - 14)), f"slot {proposal['class_slot']} / {proposal['native_integer_score']}", fill=color, stroke_width=1, stroke_fill='black')
                if not candidates:
                    draw.text((10, 10), 'NO CANDIDATES - REVIEW FOR MISSED BIRDS', fill='red', stroke_width=1, stroke_fill='white')
                display.save(out / 'overlays' / (image_id + '.jpg'), quality=90)
                (out / 'predictions' / (image_id + '.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
                completed.append(record)
            report['images_completed'] = len(completed)
            report['batches'].append({'images': len(batch), 'network_seconds': seconds})
            save()
            print(json.dumps({'completed': len(completed), 'total': len(metadata), 'network_batch_seconds': seconds}), flush=True)
        completed.sort(key=lambda row: int(row['image_id'].split('_')[1]))
        (out / 'predictions.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in completed), encoding='utf-8')
        counts = [len(row['candidates']) for row in completed]
        report.update(complete=True, total_candidates=sum(counts), images_with_candidates=sum(n > 0 for n in counts),
                      images_without_candidates=sum(n == 0 for n in counts),
                      raw_class_counts=dict(collections.Counter(str(p['class_slot']) for row in completed for p in row['candidates'])))
        review_page(completed, out)
        save()
    except BaseException as error:
        report['failed'].append({'error': repr(error), 'at_completed': len(completed)})
        save()
        raise


if __name__ == '__main__':
    main()
