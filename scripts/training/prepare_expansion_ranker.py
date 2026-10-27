"""Cache admitted human/public supervision for a frozen-parent point verifier."""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
import torch
from bird_surface import (FrozenSurface, read, write, digest, outside_git,
                          dense_targets, rectangle_mask)
from bird_parts_model import decode
from bird_residual import proposal_pool, patches, context_vectors, mask_label
from prepare_bird_residual import Writer


def targets(row, pixels):
    zero = np.zeros((256, 384), np.uint8)
    sample = dict(pixels=pixels, target=zero.astype(np.float32), known=zero.astype(bool),
                  occlusion=zero.astype(bool), points=[],
                  meta=dict(variant='original', primary_abstained=False))
    if row['source']=='CCT':
        if not row['absent'] or row['label_source']!='CCT_explicit_empty':
            raise ValueError('Explicit upstream empty label required')
        sample['known'][:] = True
    elif row['source']=='COCO-2017':
        if digest(row['foreground_mask']) != row['foreground_mask_sha256']:
            raise ValueError('Mask identity differs')
        with Image.open(row['foreground_mask']) as im:
            alpha = (np.asarray(im.convert('L'))>127).astype(np.float32)
        region = rectangle_mask([o['box'] for o in row['objects']])
        y, known, occ, _ = dense_targets(alpha, zero, region)
        # Polygon contours and blur are not precise visible-surface boundaries
        # at this input scale. Do not punish points within four pixels outside.
        boundary_band=cv2.dilate((alpha>.5).astype(np.uint8),np.ones((9,9),np.uint8)).astype(bool)
        known[(y<=.5)&boundary_band]=False
        uncertain = rectangle_mask(row['uncertain']).astype(bool)
        known[uncertain]=False; y[uncertain]=0
        sample.update(target=y, known=known, occlusion=occ)
    elif row['source']!='NABirds':
        raise ValueError('Unexpected admitted source')
    return sample


def label(row, sample, xy, injected=False):
    if row['source']=='CCT':
        return 0, 'CCT_explicit_empty', 1.
    if row['source']=='NABirds':
        if injected and any(np.linalg.norm(np.asarray(xy)-p)<1e-6 for p in row['eyes']):
            return 1, 'NABirds_visible_human_eye', 1.
        return None, 'unknown', 0.
    y, source, weight = mask_label(sample, xy)
    return y, 'COCO_'+source, weight


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('admitted','parent','surface-head','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=outside_git(a.output);out.mkdir(parents=True,exist_ok=False)
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no fallback')
    torch.set_num_threads(4);cv2.setNumThreads(1)
    document=read(a.admitted);rows=document['records']
    assert all(r['source'] in ('NABirds','COCO-2017','CCT') for r in rows)
    model=FrozenSurface(a.parent).cuda().eval()
    head=torch.load(a.surface_head,map_location='cpu',weights_only=True)
    if head['parent_sha256']!=digest(a.parent):raise ValueError('Proposer parent differs')
    model.head.load_state_dict(head['head_state_dict'])
    writers={k:Writer(out/k) for k in ('fit','calibration')}
    audit=[];asset_hashes={};counts=Counter()
    (out/'audit-images').mkdir()
    for start in range(0,len(rows),16):
        batch=rows[start:start+16];samples=[]
        for row in batch:
            actual=digest(row['path']);assert actual==row['input_sha256']
            asset_hashes[row['path']]=actual
            with Image.open(row['path']) as im:pixels=np.asarray(im.convert('RGB')).copy()
            if row['source']=='COCO-2017':asset_hashes[row['foreground_mask']]=digest(row['foreground_mask'])
            samples.append(targets(row,pixels))
        value=torch.from_numpy(np.stack([s['pixels'].transpose(2,0,1) for s in samples])).cuda().float()/256
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            p2,p3,raw=model.encode(value);surface=model.head(p2,p3)
        decoded=([[] for _ in batch] if all(r['source']=='NABirds' for r in batch)
                 else decode(raw,model.base.model[-1].stride))
        for b,(row,sample,parts) in enumerate(zip(batch,samples,decoded)):
            rng=np.random.default_rng(int(hashlib.sha256(row['image_id'].encode()).hexdigest()[:8],16))
            pool=[] if row['source']=='NABirds' else proposal_pool(parts,surface[b:b+1])
            labels=[label(row,sample,p['point_xy']) for p in pool]
            probability=surface[b,0].float().sigmoid().cpu().numpy()
            anchors=row['eyes'] if row['source']=='NABirds' else []
            if row['source']=='COCO-2017':
                yy,xx=np.where(sample['target']>.5)
                if len(xx):anchors=[[float(xx[i]),float(yy[i])] for i in rng.choice(len(xx),min(2,len(xx)),replace=False)]
            for xy in anchors:
                x,y=xy
                if not(0<=x<384 and 0<=y<256):continue
                pool.append(dict(point_xy=list(xy),proposal_score=float(probability[int(y/4),int(x/4)]),source_kind='surface',injected=True))
                labels.append(label(row,sample,xy,True))
            if row['source']!='NABirds':
                for _ in range(6):
                    for attempt in range(100):
                        xy=[float(rng.uniform(2,382)),float(rng.uniform(2,254))]
                        target=label(row,sample,xy)
                        if target[0]==0:break
                    else:continue
                    x,y=xy;pool.append(dict(point_xy=xy,proposal_score=float(probability[int(y/4),int(x/4)]),source_kind='surface',easy=True));labels.append(target)
            features=context_vectors(p2[b:b+1],p3[b:b+1],pool)
            partition='fit' if row['split']=='public_train' else 'calibration'
            writers[partition].add(sample,pool,labels,features,row,partition)
            counts[row['source']+':'+partition]+=1
            # Ten input/crop examples per new supervision type, at most two per group.
            if partition=='fit':
                for category in ('COCO_positive','COCO_negative','NABirds_positive','CCT_negative'):
                    if sum(x['category']==category for x in audit)>=10:continue
                    if sum(x['category']==category and x['group']==row['group'] for x in audit)>=2:continue
                    options=[i for i,t in enumerate(labels) if t[0] is not None and
                             ((category=='COCO_positive' and row['source']=='COCO-2017' and t[0]==1) or
                              (category=='COCO_negative' and row['source']=='COCO-2017' and t[0]==0) or
                              (category=='NABirds_positive' and row['source']=='NABirds' and t[0]==1) or
                              (category=='CCT_negative' and row['source']=='CCT' and t[0]==0))]
                    if not options:continue
                    i=options[0];x,y=pool[i]['point_xy'];index=len(audit)+1
                    path=out/'audit-images'/f'{index:02d}.png'
                    image=Image.fromarray(sample['pixels']);full=image.resize((768,512),Image.Resampling.NEAREST)
                    left=min(288,max(0,int(x)-48));top=min(160,max(0,int(y)-48))
                    crop=image.crop((left,top,left+96,top+96)).resize((384,384),Image.Resampling.NEAREST)
                    for view,px,py in [(full,x*2,y*2),(crop,(x-left)*4,(y-top)*4)]:
                        d=ImageDraw.Draw(view);d.ellipse((px-7,py-7,px+7,py+7),outline='#50c8ff',width=2)
                        d.line((px-12,py,px+12,py),fill='#50c8ff');d.line((px,py-12,px,py+12),fill='#50c8ff')
                    panel=Image.new('RGB',(1184,560),(18,25,32));panel.paste(full,(8,32));panel.paste(crop,(792,32))
                    ImageDraw.Draw(panel).text((8,8),f'{index:02d} {category} {row["image_id"]}',fill='white');panel.save(path)
                    audit.append(dict(index=index,category=category,group=row['group'],image_id=row['image_id'],point_xy=[x,y],label=labels[i][0],label_source=labels[i][1],path=str(path),sha256=digest(path)))
        if start%256==0:print('cached',start+len(batch),'/',len(rows),flush=True)
    for writer in writers.values():writer.close()
    write(out/'audit.json',audit);write(out/'assets.json',asset_hashes)
    write(out/'config.json',dict(admitted_sha256=digest(a.admitted),parent_sha256=digest(a.parent),surface_head_sha256=digest(a.surface_head),counts=dict(counts),
         source_sha256={n:digest(Path(__file__).with_name(n)) for n in ('prepare_expansion_ranker.py','bird_residual.py','bird_surface.py','prepare_bird_residual.py')},
         new_teacher_predictions=0,positive_only_NABirds=True,camera_AF_verified=False))
    print('complete',dict(counts),'audit',len(audit),flush=True)


if __name__=='__main__':main()
