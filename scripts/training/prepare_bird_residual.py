"""Mine fit-side candidates and preserve disjoint ranker calibration groups."""
import argparse
from collections import Counter,defaultdict
import hashlib,json
from pathlib import Path
import cv2
import numpy as np
import torch
from bird_surface import (FrozenSurface,read,write,digest,outside_git,make_sample,
                          batch_samples,load_rgb)
from bird_parts_model import decode
from bird_guidance_metrics import select_candidate
from bird_residual import (proposal_pool,patches,context_vectors,community_label,mask_label)


class Writer:
    def __init__(self,path):
        path.mkdir();self.path=path
        self.rgb=(path/'rgb.u8').open('wb');self.context=(path/'context.f16').open('wb')
        self.records=[];self.frames=[]

    def add(self,sample,proposals,labels,features,row,partition):
        # Fit caches exclude unknowns. Calibration retains prediction unknowns.
        keep=[i for i,(label,source,weight) in enumerate(labels) if label is not None or partition!='fit']
        if not keep:return
        chosen=[proposals[i] for i in keep]
        rgb=patches(sample['pixels'],[p['point_xy'] for p in chosen])
        self.rgb.write(rgb.tobytes());self.context.write(features[keep].astype(np.float16).tobytes())
        frame=dict(image_id=row['image_id'],group=row['group'],source=row['source'],
                   variant=sample['meta']['variant'],partition=partition,indices=[],
                   positive=[],easy_negative=[],hard_negative=[],proposed=[],
                   primary_abstained=sample['meta']['primary_abstained'])
        for i,p in zip(keep,chosen):
            index=len(self.records);label,source,weight=labels[i]
            record=dict(index=index,image_id=row['image_id'],variant=sample['meta']['variant'],
                        point_xy=p['point_xy'],label=label,label_source=source,weight=weight,
                        injected=p.get('injected',False),easy=p.get('easy',False),
                        proposal_score=p['proposal_score'],source_kind=p['source_kind'])
            self.records.append(record);frame['indices'].append(index)
            if label==1:frame['positive'].append(index)
            elif label==0:
                frame['easy_negative' if p.get('easy') else 'hard_negative'].append(index)
            if not p.get('injected') and not p.get('easy'):frame['proposed'].append(index)
        self.frames.append(frame)

    def close(self):
        self.rgb.close();self.context.close()
        write(self.path/'index.json',dict(count=len(self.records),records=self.records,frames=self.frames,
              rgb_shape=[len(self.records),6,64,64],context_shape=[len(self.records),133],
              label_counts=dict(Counter(str(x['label']) for x in self.records)),
              provenance=dict(Counter(x['label_source'] for x in self.records))))


def calibration_groups(rows):
    groups=defaultdict(list)
    for row in rows:groups[row['group']].append(row)
    eligible=sorted(k for k,v in groups.items() if 2<=len(v)<=25)
    rng=np.random.default_rng(20261027);rng.shuffle(eligible)
    chosen=[];count=0;eyes=0
    for key in eligible:
        chosen.append(key);count+=len(groups[key]);eyes+=sum(bool(r['eyes']) for r in groups[key])
        if count>=40 and len(chosen)>=3 and eyes>=12:break
    if count<40 or eyes<12:raise ValueError('Insufficient disjoint calibration supervision')
    return chosen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','parent','surface-head','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=outside_git(a.output)
    if out.is_relative_to(a.dataset.resolve().parent):p.error('Keep cache outside frozen dataset')
    out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);cv2.setNumThreads(1)
    if not torch.cuda.is_available():p.error('CUDA required; no automatic fallback')
    document=read(a.dataset);community=[r for r in document['records'] if r['split']=='community_train']
    groups=calibration_groups(community)
    split=dict(calibration_groups=groups,selection='metadata-only seed 20261027; groups size 2..25 until >=40 frames and >=12 eye frames',
               fit_images=[r['image_id'] for r in community if r['group'] not in groups],
               calibration_images=[r['image_id'] for r in community if r['group'] in groups],
               parent_saw_calibration_images=True,independent_test=False)
    write(out/'community-ranker-split.json',split)
    model=FrozenSurface(a.parent).cuda().eval()
    head=torch.load(a.surface_head,map_location='cpu',weights_only=True)
    if head['parent_sha256']!=digest(a.parent):raise ValueError('Frozen surface parent mismatch')
    model.head.load_state_dict(head['head_state_dict'])
    writers={k:Writer(out/k) for k in ('fit','real-calibration','public-calibration')}
    rows=[r for r in document['records'] if r['split']=='community_train' or r['source']=='CUB-200-2011']
    audit=[];asset_hashes={};processed=0
    (out/'audit-images').mkdir()
    for row in rows:
        asset_hashes[row['path']]=digest(row['path'])
        if row['source']=='CUB-200-2011':asset_hashes[row['foreground_mask']]=digest(row['foreground_mask'])
        if row['source']=='community':
            partition='real-calibration' if row['group'] in groups else 'fit';variants=['original']
        elif row['split']=='public_val':partition='public-calibration';variants=['original','small','occluded']
        else:partition='fit';variants=[None]
        for variant_index,variant in enumerate(variants):
            rng=np.random.default_rng(20261027+processed*37+variant_index)
            sample=make_sample(row,document['context_assets'],rng,variant)
            images,_=batch_samples([sample],'cuda')
            with torch.no_grad(),torch.autocast('cuda',dtype=torch.float16):
                p2,p3,raw=model.encode(images);surface=model.head(p2,p3)
            parts=decode(raw,model.base.model[-1].stride)[0]
            proposals=proposal_pool(parts,surface)
            sample['meta']['primary_abstained']=select_candidate(parts,.8,'none',.4,.5) is None
            label_fn=(lambda xy,inj=False:community_label(row,xy,inj)) if row['source']=='community' else (lambda xy,inj=False:mask_label(sample,xy))
            labels=[label_fn(x['point_xy']) for x in proposals]
            # Exact human eyes/mask interiors supply fit supervision, never proposals at inference.
            positives=row['eyes'] if row['source']=='community' else []
            if row['source']!='community':
                yy,xx=np.where(sample['target']>.5)
                if len(xx):
                    take=rng.choice(len(xx),min(2,len(xx)),replace=False)
                    positives=[[float(xx[i]),float(yy[i])] for i in take]
            probability=surface.float().sigmoid()[0,0].detach().cpu().numpy()
            for xy in positives:
                x,y=xy
                if not (0<=x<384 and 0<=y<256):continue
                proposals.append(dict(point_xy=list(xy),proposal_score=float(probability[min(63,int(y/4)),min(95,int(x/4))]),
                                      source_kind='surface',injected=True))
                labels.append(label_fn(xy,True))
            for _ in range(6):
                for attempt in range(100):
                    xy=[float(rng.uniform(2,382)),float(rng.uniform(2,254))]
                    label=label_fn(xy)
                    if label[0]==0:break
                else:continue
                x,y=xy
                proposals.append(dict(point_xy=xy,proposal_score=float(probability[int(y/4),int(x/4)]),
                                      source_kind='surface',easy=True))
                labels.append(label)
            features=context_vectors(p2,p3,proposals)
            writers[partition].add(sample,proposals,labels,features,row,partition)
            # Actual pixels used for a fixed stratified engineering audit are preserved.
            categories=[('real' if row['source']=='community' else 'public',
                          'positive' if l[0]==1 else 'negative') for l in labels]
            for category in [('real','positive'),('real','negative'),('public','positive'),('public','negative')]:
                if partition!='fit' or sum(x['category']==list(category) for x in audit)>=12:continue
                if sum(x['category']==list(category) and x['group']==row['group'] for x in audit)>=3:continue
                options=[i for i,c in enumerate(categories) if c==category and labels[i][0] is not None
                         and (category[1]=='positive' or not proposals[i].get('easy'))]
                if not options:continue
                i=options[0];ident=f'audit_{len(audit)+1:03d}'
                image_path=out/'audit-images'/(ident+'.png')
                from PIL import Image
                Image.fromarray(sample['pixels']).save(image_path)
                audit.append(dict(id=ident,category=list(category),group=row['group'],image_id=row['image_id'],point_xy=proposals[i]['point_xy'],
                                  label=labels[i][0],label_source=labels[i][1],path=str(image_path),sha256=digest(image_path)))
            if row['source']=='community' and row['absent'] and partition=='fit':
                options=[i for i,l in enumerate(labels) if l[1]=='human_frame_absence' and not proposals[i].get('easy')]
                slots=[j for j,x in enumerate(audit) if x['category']==['real','negative']]
                if options and slots:
                    i=options[0];image_path=out/'audit-images'/'audit-absence.png'
                    from PIL import Image
                    Image.fromarray(sample['pixels']).save(image_path)
                    audit[slots[-1]]=dict(id='audit_absence',category=['real','negative'],group=row['group'],
                         image_id=row['image_id'],point_xy=proposals[i]['point_xy'],label=0,
                         label_source='human_frame_absence',path=str(image_path),sha256=digest(image_path))
            processed+=1
            if processed%250==0:print('prepared views',processed,flush=True)
    for writer in writers.values():writer.close()
    for bg in document['context_assets']['backgrounds']:asset_hashes[bg['path']]=digest(bg['path'])
    write(out/'assets.json',asset_hashes);write(out/'audit.json',audit)
    for k in writers:
        index=read(out/k/'index.json')
        print(k,index['count'],index['label_counts'],index['provenance'],flush=True)
    write(out/'config.json',dict(parent_sha256=digest(a.parent),surface_head_sha256=digest(a.surface_head),
          dataset_sha256=digest(a.dataset),proposal_limit=24,community_split=split,
          audit_images=len(audit),old_validation_read_for_fitting=False,old_human_points_used_for_training=False,
          limits=['derived exterior negatives assume reviewed coverage','parent previously trained on calibration images',
                  'injected fit/calibration anchors never enter inference proposals']))


if __name__=='__main__':main()
