"""Build a small bilingual review page independently of the image archives."""
import argparse
import json
from pathlib import Path


TEMPLATE = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>forest-bird-af review</title>
<style>body{font:16px system-ui;background:#101820;color:#eee;margin:24px}button,select{padding:9px;margin:5px}header{position:sticky;top:0;background:#101820;padding:12px 0;z-index:2}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}.card{background:#1c2a35;padding:14px;border-radius:12px}img{width:100%;height:260px;object-fit:contain}a{color:#8dd8ff}.small{font-size:13px;color:#bbc}textarea{width:95%;height:54px}</style>
<header><select id="language" aria-label="Language"><option value="en">English</option><option value="zh-CN">简体中文</option></select>
<h1 id="title"></h1><p id="intro"></p><select id="filter"></select><button id="toggle"></button><button id="export"></button><span id="summary"></span><p id="save-note" class="small"></p></header>
<main class="grid" id="grid"></main><script>
const rows=__DATA__;let overlay=true;const key='forest-bird-z8-prelabel-20261024-v1';
const words={en:{title:'Z8 candidate review',intro:'Review the whole image, including birds with no boxes. Native slots 0-5 still need eye/head/bird labels.',all:'All images',zero:'No candidates',pending:'Not reviewed',error:'Marked for correction',toggle:'Switch image / overlay',export:'Export decisions JSON',save:'Decisions are stored in this browser. Export them to keep a copy. Use full-resolution images for detailed annotation.',open:'Open full-resolution image',unreviewed:'Not reviewed',correct:'Boxes correct; keep as a control',needs:'Missed bird / wrong box / needs correction',uncertain:'Uncertain; review again',note:'Describe missed birds or incorrect boxes',count:'candidates',shown:'Shown',reviewed:'with decisions'},'zh-CN':{title:'Z8 候选框复核',intro:'检查整张图，包括没有框的鸟。原始类号 0-5 的眼、头、整鸟语义仍待确认。',all:'全部图片',zero:'无候选',pending:'未复核',error:'需要修改',toggle:'切换原图 / 带框图',export:'导出复核决定 JSON',save:'决定保存在当前浏览器中，请导出留存。细致标注使用完整分辨率图片。',open:'打开完整分辨率图片',unreviewed:'未复核',correct:'框位置正确，保留作对照',needs:'漏鸟 / 误框 / 需要修改',uncertain:'不确定，需再复核',note:'记录漏掉的鸟或错误框',count:'个候选',shown:'显示',reviewed:'已记录决定'}};
let language=localStorage.getItem(key+'-language')||'en';if(!words[language])language='en';let decisions={};try{decisions=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){};
function stats(){const w=words[language];document.getElementById('summary').textContent=`${w.shown} ${visible().length}/${rows.length}; ${Object.values(decisions).filter(x=>x.decision).length} ${w.reviewed}`}
function visible(){const f=document.getElementById('filter').value;return rows.filter(r=>f==='all'||f==='zero'&&r.count===0||f==='pending'&&!decisions[r.id]?.decision||f==='error'&&decisions[r.id]?.decision==='error')}
function save(){localStorage.setItem(key,JSON.stringify(decisions));stats()}
function render(){const w=words[language];const old=document.getElementById('filter').value||'all';document.documentElement.lang=language;document.getElementById('language').value=language;document.getElementById('title').textContent=w.title;document.getElementById('intro').textContent=w.intro;document.getElementById('save-note').textContent=w.save;document.getElementById('toggle').textContent=w.toggle;document.getElementById('export').textContent=w.export;document.getElementById('filter').innerHTML=['all','zero','pending','error'].map(x=>`<option value="${x}">${w[x]}</option>`).join('');document.getElementById('filter').value=old;
document.getElementById('grid').innerHTML=visible().map(r=>`<article class="card"><b>${r.id}</b> · ${r.count} ${w.count}<a href="${overlay?r.overlay:r.image}" target="_blank"><img loading="lazy" src="${overlay?r.overlay:r.image}"></a><div><a href="${r.full}" target="_blank">${w.open}</a></div><select data-id="${r.id}"><option value="">${w.unreviewed}</option><option value="correct">${w.correct}</option><option value="error">${w.needs}</option><option value="uncertain">${w.uncertain}</option></select><textarea data-note="${r.id}" placeholder="${w.note}"></textarea></article>`).join('');document.querySelectorAll('[data-id]').forEach(s=>{s.value=decisions[s.dataset.id]?.decision||'';s.onchange=()=>{decisions[s.dataset.id]={decision:s.value,note:decisions[s.dataset.id]?.note||'',at:new Date().toISOString()};save()}});document.querySelectorAll('[data-note]').forEach(s=>{s.value=decisions[s.dataset.note]?.note||'';s.onchange=()=>{decisions[s.dataset.note]={decision:decisions[s.dataset.note]?.decision||'',note:s.value,at:new Date().toISOString()};save()}});stats()}
document.getElementById('filter').onchange=render;document.getElementById('toggle').onclick=()=>{overlay=!overlay;render()};document.getElementById('language').onchange=()=>{language=document.getElementById('language').value;localStorage.setItem(key+'-language',language);render()};document.getElementById('export').onclick=()=>{const payload={schema:'prediction-assisted-review-v1',created_at:new Date().toISOString(),review_with_predictions:true,class_semantics_confirmed:false,decisions};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));a.download='z8-review-decisions.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000)};render();</script>'''


def build_html(records, review_id=None):
    rows = [{'id': r['image_id'], 'count': len(r['candidates']),
             'overlay': 'overlays/' + r['image_id'] + '.jpg',
             'image': r['review_relative_path'],
             'full': r.get('full_review_relative_path', r['review_relative_path'])} for r in records]
    page = TEMPLATE.replace('__DATA__', json.dumps(rows).replace('</', '<\\/'))
    if review_id is not None:
        import re
        if not re.fullmatch(r'[A-Za-z0-9_-]+', review_id):
            raise ValueError('Review ID must contain only letters, digits, underscore or hyphen')
        page = page.replace('forest-bird-z8-prelabel-20261024-v1', 'forest-bird-z8-prelabel-' + review_id)
    return page


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predictions', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--review-id', help='Separate browser storage namespace for a new batch')
    a = p.parse_args()
    if a.output.exists():
        raise RuntimeError('Choose a new output file')
    records = [json.loads(line) for line in a.predictions.read_text(encoding='utf-8').splitlines()]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(build_html(records, a.review_id), encoding='utf-8')
    print(json.dumps({'images': len(records), 'default_language': 'en', 'languages': ['en', 'zh-CN']}))


if __name__ == '__main__':
    main()
