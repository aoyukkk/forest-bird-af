"""Matched positive sampling with an explicit empty-scene negative quota."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from bird_surface import read, write, digest, outside_git
from bird_residual import PointRanker, ranking_loss
from train_bird_residual import THRESHOLDS


class MappedCache:
    def __init__(self, path):
        self.index=read(path/'index.json');n=self.index['count']
        self.rgb=np.memmap(path/'rgb.u8',mode='r',dtype=np.uint8,shape=(n,6,64,64))
        self.context=np.memmap(path/'context.f16',mode='r',dtype=np.float16,shape=(n,133))
        self.labels=np.array([-1 if r['label'] is None else r['label'] for r in self.index['records']])
        self.weights=np.array([r['weight'] for r in self.index['records']],np.float32)

    def batch(self, indices):
        return np.array(self.rgb[indices]),np.array(self.context[indices])


def grouped(frames):
    groups={}
    for f in frames:groups.setdefault(f['group'],[]).append(f)
    return list(groups.values())


def choose(values, u):
    return values[min(len(values)-1,int(u*len(values)))]


def batches(old, new, seed, epoch, empty, presentations=4096):
    original=[f for f in old.index['frames'] if f['easy_negative'] and (f['positive'] or f['hard_negative'])]
    cub=[f for f in original if f['source']=='CUB-200-2011']
    real=grouped([f for f in original if f['source']=='community'])
    nab=[f for f in new.index['frames'] if f['source']=='NABirds' and f['positive']]
    coco=[f for f in new.index['frames'] if f['source']=='COCO-2017' and f['positive']]
    cct=grouped([f for f in new.index['frames'] if f['source']=='CCT' and (f['easy_negative'] or f['hard_negative'])])
    if not all((cub,real,nab,coco,cct)):raise ValueError('Missing explicit source cohort')
    rng=np.random.default_rng(seed+epoch*1000003)
    points=[];positive_tags=[];negative_sources=[]
    for step in range(presentations):
        u=rng.random(12)  # Consume the same random stream in both conditions.
        if u[0]<.5:
            frame=choose(cub,u[2]) if u[1]<.5 else choose(choose(real,u[2]),u[3]);ps=0
            positive=choose(frame['positive'] or frame['easy_negative'],u[4])
            negative=choose(frame['hard_negative'] if frame['hard_negative'] and u[5]<.75 else frame['easy_negative'],u[6]);ns=0
        elif u[0]<.75:
            frame=choose(nab,u[2]);ps=1;positive=choose(frame['positive'],u[4])
            background=choose(cub,u[3]);ns=0
            negative=choose(background['hard_negative'] if background['hard_negative'] and u[5]<.5 else background['easy_negative'],u[6])
        else:
            frame=choose(coco,u[2]);ps=1;positive=choose(frame['positive'],u[4]);ns=1
            if frame['hard_negative'] or frame['easy_negative']:
                negative=choose(frame['hard_negative'] if frame['hard_negative'] and (not frame['easy_negative'] or u[5]<.75) else frame['easy_negative'],u[6])
            else:
                background=choose(cub,u[3]);ns=0
                negative=choose(background['hard_negative'] if background['hard_negative'] and u[5]<.5 else background['easy_negative'],u[6])
        if empty and u[8]<.30:
            background=choose(choose(cct,u[9]),u[10]);ns=1
            negative=choose(background['hard_negative'] or background['easy_negative'],u[11])
        points.extend([(ps,positive),(ns,negative)])
        positive_tags.append((frame['image_id'],positive,ps))
        cache=(old,new)[ns];negative_sources.append(cache.index['records'][negative]['label_source'])
        if (step+1)%64==0:
            yield points,positive_tags,negative_sources
            points=[];positive_tags=[];negative_sources=[]
    if points:yield points,positive_tags,negative_sources


def load_points(caches, points):
    rgb=np.empty((len(points),6,64,64),np.uint8);context=np.empty((len(points),133),np.float16)
    labels=np.empty(len(points),np.float32);weights=np.empty(len(points),np.float32)
    for source,cache in enumerate(caches):
        positions=[i for i,(s,index) in enumerate(points) if s==source]
        if not positions:continue
        indices=[points[i][1] for i in positions]
        rgb[positions],context[positions]=cache.batch(indices)
        labels[positions]=cache.labels[indices];weights[positions]=cache.weights[indices]
    if (labels<0).any():raise ValueError('Unknown must never enter fit loss')
    return tuple(torch.from_numpy(v).cuda() for v in (rgb,context,labels,weights))


def scores(model, cache):
    result=[];model.eval()
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
        for start in range(0,len(cache.labels),512):
            rgb,context=cache.batch(list(range(start,min(start+512,len(cache.labels)))))
            result.extend(model(torch.from_numpy(rgb).cuda(),torch.from_numpy(context).cuda()).float().sigmoid().cpu().tolist())
    return np.array(result)


def assessment(model, real, public, new):
    rs,ps,ns=[scores(model,c) for c in (real,public,new)]
    anchors=np.flatnonzero(real.labels==1)
    real_neg=[np.array([i for i in f['indices'] if real.labels[i]==0],np.int64) for f in real.index['frames']]
    empty=[f for f in new.index['frames'] if f['source']=='CCT']
    mask_frames=[(public,ps,f) for f in public.index['frames']]
    mask_frames.extend((new,ns,f) for f in new.index['frames'] if f['source']=='COCO-2017')
    mask_top=[]
    for cache,values,f in mask_frames:
        indices=f['proposed']
        best=max(indices,key=lambda i:values[i]) if indices else None
        mask_top.append((values[best],cache.labels[best]) if best is not None else (0.,-1))
    empty_max=[max((ns[i] for i in f['proposed']),default=0.) for f in empty]
    nab=[r['index'] for r in new.index['records'] if r['label']==1 and r['label_source']=='NABirds_visible_human_eye']
    curve=[]
    for threshold in THRESHOLDS:
        mask=dict(foreground=0,known_wrong=0,unknown=0,abstain=0,total=len(mask_top))
        for score,label in mask_top:
            key='abstain' if score<threshold else ('foreground' if label==1 else ('known_wrong' if label==0 else 'unknown'))
            mask[key]+=1
        row=dict(threshold=threshold,real_positive_accepted=int((rs[anchors]>=threshold).sum()),real_positive_anchors=len(anchors),
                 real_negative_false_frames=sum(bool(len(ix) and (rs[ix]>=threshold).any()) for ix in real_neg),
                 empty_false_frames=sum(int(v>=threshold) for v in empty_max),empty_frames=len(empty),
                 empty_locations=len({f['group'] for f in empty}),mask=mask,
                 mask_utility=mask['foreground']-5*mask['known_wrong'],
                 NABirds_positive_anchors=len(nab),NABirds_anchors_accepted=int((ns[nab]>=threshold).sum()))
        curve.append(row)
    def key(x):
        valid=x['real_negative_false_frames']<=1 and x['empty_false_frames']<=1
        return (int(valid),x['real_positive_accepted'],x['mask_utility'],-x['empty_false_frames'],-x['real_negative_false_frames'],x['threshold'])
    best=max(curve,key=key)
    return dict(selected=best,key=key(best),curve=curve,
          rule='<=1 real known-negative frame AND <=1 actual CCT-empty selection, then real anchor retention, then combined CUB/COCO proposal mask utility; no community validation')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('old-cache','new-cache','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--condition',choices=('positive','empty'),required=True)
    p.add_argument('--seed',type=int,default=20261027);p.add_argument('--epochs',type=int,default=32)
    p.add_argument('--pilot-steps',type=int,default=0);p.add_argument('--audit',type=Path)
    a=p.parse_args();out=outside_git(a.output)
    if any(out.is_relative_to(path.resolve()) for path in (a.old_cache,a.new_cache)):
        raise ValueError('Keep runs outside immutable caches')
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no fallback')
    if not a.pilot_steps:
        audit=read(a.audit) if a.audit else {}
        if not audit.get('engineering_gate_passed') or audit.get('cache_config_sha256')!=digest(a.new_cache/'config.json'):
            raise ValueError('Actual new-supervision visual audit must pass and bind this cache before fitting')
    out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir();(out/'executed-code').mkdir()
    for name in ('train_expansion_ranker.py','bird_residual.py','train_bird_residual.py'):
        shutil.copyfile(Path(__file__).with_name(name),out/'executed-code'/name)
    torch.set_num_threads(4);torch.manual_seed(20261027)
    model=PointRanker(True).cuda();torch.manual_seed(a.seed)
    fit=[MappedCache(a.old_cache/'fit'),MappedCache(a.new_cache/'fit')]
    cal=[] if a.pilot_steps else [MappedCache(a.old_cache/'real-calibration'),MappedCache(a.old_cache/'public-calibration'),MappedCache(a.new_cache/'calibration')]
    config=dict(condition=a.condition,seed=a.seed,epochs=a.epochs,presentations_per_epoch=4096,
       old_cache_config_sha256=digest(a.old_cache/'config.json'),new_cache_config_sha256=digest(a.new_cache/'config.json'),
       parameters=sum(v.numel() for v in model.parameters()),empty_negative_probability=.30 if a.condition=='empty' else 0.,
       init_state_sha256=hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes() for v in model.state_dict().values())).hexdigest(),
       stream_fit_memmaps=True,original_model_updated=False,new_A12_pseudolabels=0)
    write(out/'config.json',config)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001)
    scaler=torch.amp.GradScaler('cuda',init_scale=128.,growth_interval=10**9)
    history=[];best=None;start=time.perf_counter()
    try:
        for epoch in range(1 if a.pilot_steps else a.epochs):
            model.train();losses=[];positives=hashlib.sha256();all_points=hashlib.sha256();negatives=Counter()
            for points,tags,sources in batches(*fit,a.seed,epoch,a.condition=='empty',a.pilot_steps*64 if a.pilot_steps else 4096):
                positives.update(json.dumps(tags).encode());all_points.update(json.dumps(points).encode());negatives.update(sources)
                rgb,context,y,w=load_points(fit,points);rgb=(rgb.float()*(torch.rand(len(y),1,1,1,device='cuda')*.2+.9)).clamp(0,255)
                pairs=[(i,i+1) for i in range(0,len(points),2)
                       if fit[points[i][0]].labels[points[i][1]]==1
                       and fit[points[i+1][0]].labels[points[i+1][1]]==0]
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.float16):loss=ranking_loss(model(rgb,context),y,w,pairs)
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
                scaler.scale(loss).backward();scaler.unscale_(optimizer)
                if not torch.isfinite(torch.nn.utils.clip_grad_norm_(model.parameters(),10.)):raise RuntimeError('Nonfinite gradient')
                scaler.step(optimizer);scaler.update();losses.append(float(loss.detach()))
            checkpoint=dict(state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},large=True,epoch=epoch+1,condition=a.condition,seed=a.seed,
                   cache_config_sha256=config['new_cache_config_sha256'])
            path=out/'checkpoints'/f'epoch-{epoch+1:03d}.pt';torch.save(checkpoint,path)
            back=torch.load(path,map_location='cpu',weights_only=True)
            assert all(torch.equal(v,back['state_dict'][k]) for k,v in checkpoint['state_dict'].items())
            row=dict(epoch=epoch+1,loss=float(np.mean(losses)),positive_sequence_sha256=positives.hexdigest(),point_sequence_sha256=all_points.hexdigest(),negative_provenance=dict(negatives))
            if not a.pilot_steps:
                result=assessment(model,*cal);write(out/f'calibration-{epoch+1:03d}.json',result);row['selected']=result['selected']
                if best is None or tuple(result['key'])>best:
                    best=tuple(result['key']);shutil.copyfile(path,out/'best.pt');write(out/'calibration-best.json',result)
            history.append(row);write(out/'history.json',history);print(json.dumps(row),flush=True)
        write(out/'status.json',dict(status='completed',epochs=len(history),seconds=time.perf_counter()-start,
               peak_gpu_allocated_bytes=torch.cuda.max_memory_allocated(),checkpoints_readback_equal=True))
    except Exception as exc:
        write(out/'status.json',dict(status='failed',error=repr(exc),completed_epochs=len(history)));raise


if __name__=='__main__':main()
