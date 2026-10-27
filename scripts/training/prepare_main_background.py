"""Freeze main-detector replay cohorts and real fixed-eye predictions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from bird_surface import read,write,digest,outside_git
from bird_parts_model import build_model,as_raw,decode


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','admitted','regions','box-parent','eye-parent','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=outside_git(a.output);out.mkdir(parents=True,exist_ok=False)
    base,new=read(a.base),read(a.admitted)
    rows=base['records']+new['records']
    if len({r['image_id'] for r in rows})!=len(rows):raise ValueError('Duplicate IDs')
    for r in rows:
        if r['source']!='community':
            if any(o['kind']=='head' for o in r['objects']):raise ValueError('No derived public head labels')
            r['head_labels_are_weak']=False
    community=[r for r in rows if r['split']=='community_train']
    empty=[r for r in rows if r['source']=='CCT' and r['split']=='public_train']
    cal_empty=[r for r in rows if r['source']=='CCT' and r['split']=='public_val']
    val=[r for r in rows if r['split']=='community_val']
    coco=sorted([r for r in rows if r['source']=='COCO-2017' and r['split']=='public_val'],
                key=lambda r:hashlib.sha256(('main-cal-20261027:'+r['image_id']).encode()).hexdigest())[:128]
    assert (len(community),len(empty),len(cal_empty),len(val),len(coco))==(375,678,172,80,128)
    assert not ({r['group'] for r in empty}&{r['group'] for r in cal_empty})
    regions=read(a.regions)['records'];assert {r['image_id'] for r in regions}=={r['image_id'] for r in val}
    document=dict(schema='main-background-replay-v1',records=rows,community_regions=regions,
           eval_ids=[r['image_id'] for r in val+cal_empty+coco],
           box_parent_sha256=digest(a.box_parent),eye_parent_sha256=digest(a.eye_parent),
           source_manifests={str(q):digest(q) for q in (a.base,a.admitted,a.regions)},
           counts=dict(Counter(r['source']+':'+r['split'] for r in rows)),
           B_H_E_thresholds=[.4,.4,.8],historical_test_included=False,A12_labels=0,camera_AF_verified=False)
    write(out/'dataset.json',document)
    paths=sorted({r['path'] for r in rows})
    with ThreadPoolExecutor(max_workers=8) as pool:hashes=list(pool.map(digest,paths))
    assets=dict(zip(paths,hashes))
    for r in rows:
        if r.get('input_sha256') and assets[r['path']]!=r['input_sha256']:raise ValueError('Input changed')
    write(out/'assets.json',assets)
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no fallback')
    torch.set_num_threads(4);model=build_model('n').cuda().eval()
    model.load_state_dict(torch.load(a.eye_parent,map_location='cpu',weights_only=True)['state_dict'])
    predictions={}
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
        for r in val+cal_empty+coco:
            with Image.open(r['path']) as im:v=np.asarray(im.convert('RGB')).transpose(2,0,1).copy()
            raw=as_raw(model(torch.from_numpy(v).cuda().float()[None]/256))
            predictions[r['image_id']]=[x for x in decode(raw,model.model[-1].stride)[0] if x['kind']=='eye']
    write(out/'fixed-eyes.json',dict(parent_sha256=digest(a.eye_parent),input_hashes={r['image_id']:assets[r['path']] for r in val+cal_empty+coco},
         predictions=predictions,scope='actual batch-one frozen eye branch; no teacher labels'))
    write(out/'status.json',dict(status='prepared',source_assets=len(assets),evaluation_images=len(predictions),originals_changed=False))
    print(read(out/'status.json'),flush=True)


if __name__=='__main__':main()
