"""Direct B/H n-detector continuation with paired empty-scene supervision.

The separate eye network is never trained. BN running statistics and unused
pose heads are frozen. Partial labels remain unknown, including public heads.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
from PIL import Image
import torch
from torch import nn
import torch.nn.functional as F
from ultralytics.utils.tal import make_anchors
from bird_surface import read,write,digest,outside_git
from bird_parts_model import (build_model,as_raw,BirdDataset,BirdLoss,
                              classification_validity,regions_mask,decode,numpy_iou)
from bird_guidance_metrics import select_candidate,assess_guidance


def supervision(samples, centers, empty_enabled):
    valid=classification_validity(samples,centers)
    for i,s in enumerate(samples):
        if s['source']=='CCT' and not empty_enabled:valid[i]=False
    return valid


class BoxOnlyLoss:
    def __init__(self, model, empty_enabled):
        self.det=BirdLoss(model).det;self.empty_enabled=empty_enabled

    def __call__(self, raw, samples):
        raw={k:v.float() if torch.is_tensor(v) else v for k,v in raw.items()}
        device=raw['scores'].device
        anchors,strides=make_anchors(raw['feats'],self.det.stride,.5)
        self.det.bce.valid=supervision(samples,anchors*strides,self.empty_enabled)
        idx,cls,boxes=[],[],[]
        for i,s in enumerate(samples):
            for o in s['objects']:
                x1,y1,x2,y2=o['box']
                if x2<=x1 or y2<=y1:continue
                idx.append(i);cls.append(0 if o['kind']=='bird' else 1)
                boxes.append([(x1+x2)/768,(y1+y2)/512,(x2-x1)/384,(y2-y1)/256])
        batch=dict(batch_idx=torch.tensor(idx,device=device),cls=torch.tensor(cls,device=device).reshape(-1,1),bboxes=torch.tensor(boxes,device=device).reshape(-1,4))
        weights=[.1 if s['source']=='CCT' else 1. for s in samples]
        self.det.class_weights=torch.tensor(weights,device=device).reshape(-1,1,1).expand(-1,1,2)
        loss,_=self.det.loss(raw,batch)
        return loss.sum()/len(samples)


def preservation(raw, teacher, samples, stride):
    anchors,scales=make_anchors(raw['feats'],stride,.5);centers=(anchors*scales).float()
    mask=torch.zeros_like(raw['scores'],dtype=torch.bool)
    for b,s in enumerate(samples):
        if s['source']=='CCT':continue
        for kind,c in [('bird',0),('head',1)]:
            roi=regions_mask([o['box'] for o in s['objects'] if o['kind']==kind],centers)
            mask[b,c]=roi&(teacher['scores'][b,c].float().sigmoid()>=.2)
    if not mask.any():return raw['scores'].sum()*0
    score=F.smooth_l1_loss(raw['scores'].float()[mask],teacher['scores'].float()[mask])
    boxmask=mask.any(1)[:,None].expand(-1,raw['boxes'].shape[1],-1)
    box=F.smooth_l1_loss(raw['boxes'].float()[boxmask],teacher['boxes'].float()[boxmask])
    return score+.02*box


def frozen_bn_train(model):
    model.train()
    for module in model.modules():
        if isinstance(module,nn.modules.batchnorm._BatchNorm):module.eval()


def grouped(rows):
    groups={}
    for r in rows:groups.setdefault(r['group'],[]).append(r)
    return list(groups.values())


def choice(values,u):return values[min(len(values)-1,int(u*len(values)))]


def epoch_batches(document, seed, epoch, batches=96):
    rows=document['records']
    community=grouped([r for r in rows if r['split']=='community_train'])
    public=[[r for r in rows if r['source']==source and r['split']=='public_train'] for source in ('CUB-200-2011','NABirds','COCO-2017')]
    empty=grouped([r for r in rows if r['source']=='CCT' and r['split']=='public_train'])
    rng=np.random.default_rng(seed+epoch*1000003)
    for _ in range(batches):
        selected=[]
        for j in range(16):
            u=rng.random(5)
            if j>=12:r=choice(choice(empty,u[1]),u[2])
            elif u[0]<.7:r=choice(choice(community,u[1]),u[2])
            else:r=choice(choice(public,u[1]),u[2])
            selected.append(r)
        yield selected


def measure(model, document, eyes):
    eval_ids=set(document['eval_ids']);rows=[r for r in document['records'] if r['image_id'] in eval_ids]
    predictions={};model.eval()
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
        for r in rows:
            with Image.open(r['path']) as im:v=np.asarray(im.convert('RGB')).transpose(2,0,1).copy()
            raw=as_raw(model(torch.from_numpy(v).cuda().float()[None]/256))
            bh=[q for q in decode(raw,model.model[-1].stride)[0] if q['kind'] in ('bird','head')]
            predictions[r['image_id']]=bh+eyes[r['image_id']]
    community=[r for r in rows if r['split']=='community_val']
    region_rows=document['community_regions'];ids={r['image_id'] for r in community}
    selected={k:select_candidate(predictions[k],.8,'none',.4,.4) for k in ids}
    counts=assess_guidance(region_rows,{k:predictions[k] for k in ids},selected_by_id=selected)['counts']
    empty=[r for r in rows if r['source']=='CCT'];empty_selected={r['image_id']:select_candidate(predictions[r['image_id']],.8,'none',.4,.4) for r in empty}
    kinds=Counter(p['kind'] for p in empty_selected.values() if p is not None)
    coco=[r for r in rows if r['source']=='COCO-2017'];tp=0;labels=0
    for r in coco:
        truth=[o['box'] for o in r['objects'] if o['kind']=='bird'];labels+=len(truth);matched=set()
        for q in sorted((p for p in predictions[r['image_id']] if p['kind']=='bird' and p['score']>=.4),key=lambda q:q['score'],reverse=True):
            available=[(numpy_iou(q['box_xyxy'],b),i) for i,b in enumerate(truth) if i not in matched]
            if available:
                score,i=max(available)
                if score>=.5:matched.add(i);tp+=1
    return dict(community=counts,empty_frames=len(empty),empty_selected=sum(kinds.values()),empty_by_kind=dict(kinds),
        COCO_bird_box_TP=tp,COCO_bird_box_labels=labels,predictions=predictions,community_selected=selected,empty_selected_predictions=empty_selected)


def rank(result, reference):
    c,r=result['community'],reference['community']
    safe=c['geometry_supported']>=r['geometry_supported'] and c['outside_labelled_geometry']<=r['outside_labelled_geometry'] and c['explicit_absent_selection']<=r['explicit_absent_selection']
    for key in ('selected_eye','eye_4px','eye_unmatched_4px','eye_unassessed_selected'):
        if c[key]!=r[key]:raise RuntimeError('Fixed eye branch selection changed')
    return (int(safe),-result['empty_selected'],c['geometry_supported'],-c['outside_labelled_geometry'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','eyes','initial','eye-parent','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--condition',choices=('control','empty'),required=True)
    p.add_argument('--seed',type=int,default=20261027);p.add_argument('--epochs',type=int,default=8)
    p.add_argument('--batches',type=int,default=96);p.add_argument('--pilot-steps',type=int,default=0)
    a=p.parse_args();out=outside_git(a.output)
    if out.is_relative_to(a.dataset.resolve().parent):p.error('Keep runs outside frozen dataset')
    if not torch.cuda.is_available():p.error('CUDA required; no fallback')
    out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir();(out/'executed-code').mkdir()
    for n in ('train_main_background.py','bird_parts_model.py','bird_guidance_metrics.py'):
        shutil.copyfile(Path(__file__).with_name(n),out/'executed-code'/n)
    torch.set_num_threads(4);torch.manual_seed(a.seed)
    document=read(a.dataset);eye_record=read(a.eyes)
    if document['box_parent_sha256']!=digest(a.initial) or document['eye_parent_sha256']!=digest(a.eye_parent) or eye_record['parent_sha256']!=digest(a.eye_parent):raise ValueError('Initial/eye identity differs')
    initial=torch.load(a.initial,map_location='cpu',weights_only=True)
    model=build_model('n').cuda();model.load_state_dict(initial['state_dict'])
    teacher=build_model('n').cuda().eval();teacher.load_state_dict(initial['state_dict']);teacher.requires_grad_(False)
    for name,parameter in model.named_parameters():
        if '.cv4' in name:parameter.requires_grad_(False)
    bn_before={k:v.clone() for k,v in model.state_dict().items() if k.endswith(('running_mean','running_var','num_batches_tracked'))}
    trainable=[q for q in model.parameters() if q.requires_grad]
    optimizer=torch.optim.AdamW(trainable,lr=.00002,weight_decay=.0001)
    scaler=torch.amp.GradScaler('cuda',init_scale=128.,growth_interval=10**9)
    loss_fn=BoxOnlyLoss(model,a.condition=='empty')
    config=dict(condition=a.condition,seed=a.seed,epochs=a.epochs,batches_per_epoch=a.batches,batch=16,replay_frames_per_batch=12,empty_frames_per_batch=4,
        lr=.00002,empty_classification_weight=.1,preservation_weight=.25,BN_statistics_frozen=True,independent_eye_branch_frozen=True,
        parameters=sum(v.numel() for v in model.parameters()),trainable_parameters=sum(v.numel() for v in trainable),
        dataset_sha256=digest(a.dataset),eyes_sha256=digest(a.eyes),initial_sha256=digest(a.initial),eye_parent_sha256=digest(a.eye_parent),new_A12_labels=0)
    write(out/'config.json',config)
    reference=None;best=None
    if not a.pilot_steps:
        reference=measure(model,document,eye_record['predictions'])
        if reference['community']['geometry_supported']!=68 or reference['empty_selected']!=60:raise RuntimeError('Parent replay differs from fixed reference')
        write(out/'validation-parent.json',reference);best=rank(reference,reference)
        shutil.copyfile(a.initial,out/'best.pt');write(out/'validation-best.json',reference)
    history=[];start=time.perf_counter()
    try:
        for epoch in range(1 if a.pilot_steps else a.epochs):
            frozen_bn_train(model);losses=[];classification=[];replay=[];order=hashlib.sha256();sources=Counter()
            for rows in epoch_batches(document,a.seed,epoch,a.pilot_steps or a.batches):
                order.update(('\n'.join(r['image_id'] for r in rows)+'\n').encode());sources.update(r['source'] for r in rows)
                samples=[BirdDataset([r])[0] for r in rows];images=torch.stack([x for x,s in samples]).cuda();samples=[s for x,s in samples]
                # No geometric augmentation or blur; preserve source coordinates.
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.float16):
                    raw=as_raw(model(images))
                    with torch.no_grad():frozen=as_raw(teacher(images))
                detection=loss_fn(raw,samples);guard=preservation(raw,frozen,samples,model.model[-1].stride)
                loss=detection+.25*guard
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
                scaler.scale(loss).backward();scaler.unscale_(optimizer)
                if not torch.isfinite(torch.nn.utils.clip_grad_norm_(trainable,10.)):raise RuntimeError('Nonfinite gradient')
                scaler.step(optimizer);scaler.update();losses.append(float(loss.detach()));classification.append(float(detection.detach()));replay.append(float(guard.detach()))
            if not all(torch.equal(model.state_dict()[k],v) for k,v in bn_before.items()):raise RuntimeError('BN running state changed')
            payload=dict(state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},epoch=epoch+1,size='n',condition=a.condition,seed=a.seed)
            path=out/'checkpoints'/f'epoch-{epoch+1:03d}.pt';torch.save(payload,path)
            saved=torch.load(path,map_location='cpu',weights_only=True);assert all(torch.equal(v,saved['state_dict'][k]) for k,v in payload['state_dict'].items())
            row=dict(epoch=epoch+1,loss=float(np.mean(losses)),detection_loss=float(np.mean(classification)),preservation_loss=float(np.mean(replay)),sample_order_sha256=order.hexdigest(),presentations=dict(sources))
            if not a.pilot_steps and ((epoch+1)%2==0 or epoch+1==a.epochs):
                result=measure(model,document,eye_record['predictions']);key=rank(result,reference)
                write(out/f'validation-{epoch+1:03d}.json',result)
                row.update(community=result['community'],empty_selected=result['empty_selected'],empty_by_kind=result['empty_by_kind'],rank=key,
                           COCO_bird_box_TP=result['COCO_bird_box_TP'],COCO_bird_box_labels=result['COCO_bird_box_labels'])
                if key>best:
                    best=key;shutil.copyfile(path,out/'best.pt');write(out/'validation-best.json',result)
            history.append(row);write(out/'history.json',history);print(json.dumps(row),flush=True)
        if digest(a.eye_parent)!=config['eye_parent_sha256']:raise RuntimeError('Eye model changed')
        write(out/'status.json',dict(status='completed',epochs=len(history),seconds=time.perf_counter()-start,BN_unchanged=True,eye_parent_unchanged=True,checkpoints_readback_equal=True,peak_gpu_bytes=torch.cuda.max_memory_allocated()))
    except Exception as exc:
        write(out/'status.json',dict(status='failed',error=repr(exc),completed_epochs=len(history)));raise


if __name__=='__main__':main()
