"""Capacity/real-hard-negative ablations with fit-only paired sampling."""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
import shutil,time
import numpy as np
import torch
from bird_residual import PointRanker,ranking_loss
from bird_surface import read,write,digest,outside_git

THRESHOLDS=(.3,.5,.7,.8,.9,.95,.98,.99,.995,.999,.9995,.9999,.99995,.99999,.999999,1.000001)


class Cache:
    def __init__(self,path,device='cuda'):
        self.index=read(path/'index.json');n=self.index['count']
        rgb=np.memmap(path/'rgb.u8',mode='r',dtype=np.uint8,shape=(n,6,64,64))
        context=np.memmap(path/'context.f16',mode='r',dtype=np.float16,shape=(n,133))
        self.rgb=torch.from_numpy(np.array(rgb)).to(device)
        self.context=torch.from_numpy(np.array(context)).to(device)
        self.labels=np.array([-1 if x['label'] is None else x['label'] for x in self.index['records']])
        self.weights=np.array([x['weight'] for x in self.index['records']],np.float32)
        for frame in self.index['frames']:
            frame['occluder_negative']=[i for i in frame['hard_negative']
                if self.index['records'][i]['label_source']=='known_synthetic_occluder']


def sample_batches(cache,seed,epoch,hard,presentations=4096,batch_frames=64):
    frames=[f for f in cache.index['frames'] if f['easy_negative'] and (f['positive'] or f['hard_negative'])]
    public=[f for f in frames if f['source']=='CUB-200-2011']
    groups={}
    for f in frames:
        if f['source']=='community':groups.setdefault(f['group'],[]).append(f)
    groups=list(groups.values())
    if not public or not groups:raise ValueError('Insufficient paired fit supervision')
    rng=np.random.default_rng(seed+epoch*1000003)
    indices=[];pairs=[];tags=[];hard_count=0
    for step in range(presentations):
        u=rng.random(7)
        if u[0]<.5:frame=public[min(len(public)-1,int(u[1]*len(public)))]
        else:
            group=groups[min(len(groups)-1,int(u[1]*len(groups)))]
            frame=group[min(len(group)-1,int(u[2]*len(group)))]
        positives=frame['positive'];easy=frame['easy_negative'];mined=frame['hard_negative']
        positive=positives[min(len(positives)-1,int(u[3]*len(positives)))] if positives else easy[min(len(easy)-1,int(u[3]*len(easy)))]
        use_hard=hard and frame['source']=='community' and bool(mined) and u[4]<.75
        if frame['source']=='CUB-200-2011' and frame['occluder_negative'] and u[4]<.5:
            negative_pool=frame['occluder_negative']
        elif frame['source']=='CUB-200-2011' and mined and u[4]<.5:
            negative_pool=mined
        else:negative_pool=mined if use_hard else easy
        negative=negative_pool[min(len(negative_pool)-1,int(u[5]*len(negative_pool)))]
        start=len(indices);indices.extend([positive,negative])
        if positives:pairs.append((start,start+1))
        tags.append(frame['image_id']+':'+frame['variant']);hard_count+=int(use_hard)
        if (step+1)%batch_frames==0:
            yield indices,pairs,tags,hard_count
            indices=[];pairs=[];tags=[];hard_count=0
    if indices:yield indices,pairs,tags,hard_count


def scores(model,cache):
    result=[];model.eval()
    with torch.no_grad(),torch.autocast('cuda',dtype=torch.float16):
        for start in range(0,len(cache.labels),256):
            result.extend(model(cache.rgb[start:start+256],cache.context[start:start+256]).float().sigmoid().cpu().tolist())
    return np.array(result)


def assess(model,real,public):
    real_scores=scores(model,real);public_scores=scores(model,public)
    anchors=np.array([r['index'] for r in real.index['records'] if r['label']==1],np.int64)
    negative_by_frame=[np.array([i for i in f['indices'] if real.labels[i]==0],np.int64) for f in real.index['frames']]
    chosen=[]
    for f in public.index['frames']:
        indices=f['proposed']
        if not indices:chosen.append((0.,-1));continue
        index=max(indices,key=lambda i:public_scores[i]);chosen.append((public_scores[index],public.labels[index]))
    curve=[]
    for threshold in THRESHOLDS:
        false_frames=sum(bool(len(ix) and (real_scores[ix]>=threshold).any()) for ix in negative_by_frame)
        positive_accepted=int((real_scores[anchors]>=threshold).sum())
        c=dict(total=len(chosen),foreground=0,known_wrong=0,unknown=0,abstain=0)
        for score,label in chosen:
            if score<threshold:c['abstain']+=1
            elif label==1:c['foreground']+=1
            elif label==0:c['known_wrong']+=1
            else:c['unknown']+=1
        entry=dict(threshold=threshold,real_calibration=dict(frames=len(negative_by_frame),
                   positive_anchors=len(anchors),positive_accepted=positive_accepted,known_negative_false_frames=false_frames),
                   public_calibration=c,public_utility=c['foreground']-5*c['known_wrong'])
        curve.append(entry)
    def key(x):
        r=x['real_calibration']
        return (int(r['known_negative_false_frames']<=1),r['positive_accepted'],
                x['public_utility'],-r['known_negative_false_frames'],x['threshold'])
    best=max(curve,key=key)
    return dict(selected=best,key=key(best),curve=curve,
         selection='<=1 known-negative calibration frame, then accepted real positive anchors, then CUB top-one utility; old community validation not read')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--condition',choices=('small-hard','large-easy','large-hard'),required=True)
    p.add_argument('--seed',type=int,default=20261027);p.add_argument('--epochs',type=int,default=8)
    p.add_argument('--presentations',type=int,default=4096);p.add_argument('--pilot-steps',type=int,default=0)
    a=p.parse_args();out=outside_git(a.output)
    if out.is_relative_to(a.cache.resolve()):p.error('Keep runs outside immutable cache')
    if not torch.cuda.is_available():p.error('CUDA required, no automatic fallback')
    out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir();(out/'executed-code').mkdir()
    for name in ('bird_residual.py','train_bird_residual.py'):
        shutil.copyfile(Path(__file__).with_name(name),out/'executed-code'/name)
    torch.set_num_threads(4);torch.manual_seed(20261027)
    large=a.condition!='small-hard';hard=a.condition!='large-easy'
    model=PointRanker(large).cuda()
    torch.manual_seed(a.seed)
    cache_paths=['fit'] if a.pilot_steps else ['fit','real-calibration','public-calibration']
    required=sum((a.cache/k/'rgb.u8').stat().st_size+(a.cache/k/'context.f16').stat().st_size for k in cache_paths)
    free,total=torch.cuda.mem_get_info()
    if required+1200*1024**2>free:raise RuntimeError('Insufficient GPU space for explicit cache budget')
    caches={k:Cache(a.cache/k) for k in cache_paths}
    config=dict(condition=a.condition,seed=a.seed,large=large,hard_negatives=hard,epochs=a.epochs,
       presentations=a.presentations,lr=.0003,parameters=sum(v.numel() for v in model.parameters()),
       total_with_parent=2455728+6945+sum(v.numel() for v in model.parameters()),
       cache_config_sha256=digest(a.cache/'config.json'),thresholds=THRESHOLDS,
       calibration_false_frame_budget=1,ranker_initialization_seed=20261027,
       gpu_cache_bytes=required,old_community_validation_used_for_selection=False,
       init_state_sha256=hashlib.sha256(b''.join(v.detach().cpu().numpy().tobytes() for v in model.state_dict().values())).hexdigest())
    write(out/'config.json',config)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001)
    scaler=torch.amp.GradScaler('cuda',init_scale=128.,growth_interval=10**9)
    start=time.perf_counter();history=[];best=None
    try:
        for epoch in range(1 if a.pilot_steps else a.epochs):
            model.train();losses=[];image_hash=hashlib.sha256();point_hash=hashlib.sha256();hard_count=0;provenance=Counter()
            count=a.pilot_steps*64 if a.pilot_steps else a.presentations
            for indices,pairs,tags,mined in sample_batches(caches['fit'],a.seed,epoch,hard,count):
                image_hash.update(json.dumps(tags).encode());point_hash.update(json.dumps(indices).encode());hard_count+=mined
                provenance.update(caches['fit'].index['records'][i]['label_source'] for i in indices)
                index=torch.tensor(indices,device='cuda');rgb=caches['fit'].rgb[index].float()
                gain=torch.rand(len(index),1,1,1,device='cuda')*.2+.9
                rgb=(rgb*gain).clamp(0,255)
                labels=torch.as_tensor(caches['fit'].labels[indices],device='cuda',dtype=torch.float32)
                weights=torch.as_tensor(caches['fit'].weights[indices],device='cuda')
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.float16):
                    logits=model(rgb,caches['fit'].context[index]);loss=ranking_loss(logits,labels,weights,pairs)
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite ranker loss')
                scaler.scale(loss).backward();scaler.unscale_(optimizer)
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),10.)
                if not torch.isfinite(norm):raise RuntimeError('Nonfinite ranker gradient')
                scaler.step(optimizer);scaler.update();losses.append(float(loss.detach()))
            checkpoint=dict(state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                         large=large,epoch=epoch+1,condition=a.condition,seed=a.seed,
                         cache_config_sha256=config['cache_config_sha256'])
            path=out/'checkpoints'/f'epoch-{epoch+1:03d}.pt';torch.save(checkpoint,path)
            back=torch.load(path,map_location='cpu',weights_only=True)
            if any(not torch.equal(v,back['state_dict'][k]) for k,v in checkpoint['state_dict'].items()):
                raise RuntimeError('Ranker checkpoint readback mismatch')
            row=dict(epoch=epoch+1,loss=float(np.mean(losses)),frame_order_sha256=image_hash.hexdigest(),
                     point_selection_sha256=point_hash.hexdigest(),hard_real_negatives=hard_count,
                     supervision_provenance=dict(provenance))
            if not a.pilot_steps:
                evaluation=assess(model,caches['real-calibration'],caches['public-calibration'])
                write(out/f'calibration-{epoch+1:03d}.json',evaluation);row['selected']=evaluation['selected']
                if best is None or tuple(evaluation['key'])>best:
                    best=tuple(evaluation['key']);shutil.copyfile(path,out/'best.pt');write(out/'calibration-best.json',evaluation)
            history.append(row);write(out/'history.json',history)
            print(json.dumps(row),flush=True)
        write(out/'status.json',dict(status='completed',epochs=len(history),seconds=time.perf_counter()-start,
             peak_allocated_bytes=torch.cuda.max_memory_allocated(),checkpoints_readback_equal=True,
             original_models_updated=False,camera_AF_verified=False))
    except Exception as exc:
        write(out/'status.json',dict(status='failed',error=repr(exc),completed_epochs=len(history)));raise


if __name__=='__main__':main()
