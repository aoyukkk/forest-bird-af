"""Matched frozen-base surface experiments; select only on fixed CUB validation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import time
import numpy as np
import torch
import cv2
from bird_surface import (FrozenSurface,batch_samples,decode_surface,digest,outside_git,
                          read,surface_loss,training_samples,validation_samples,write)


THRESHOLDS=(.3,.5,.7,.8,.9,.95,.98,.99,1.000001)


def state_digest(model):
    h=hashlib.sha256()
    for k,v in model.state_dict().items():
        h.update(k.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def chunks(iterator,size):
    batch=[]
    for item in iterator:
        batch.append(item)
        if len(batch)==size:yield batch;batch=[]
    if batch:yield batch


def build_cache(args):
    out=outside_git(args.output);out.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(20261027)
    model=FrozenSurface(args.parent).cuda().eval()
    document=read(args.dataset)
    count=sum(r['source']=='CUB-200-2011' and r['split']=='public_val' for r in document['records'])*3
    arrays={name:np.lib.format.open_memmap(out/(name+'.npy'),mode='w+',dtype=dtype,shape=shape)
            for name,dtype,shape in (
                ('p2',np.float16,(count,64,64,96)),('p3',np.float16,(count,64,32,48)),
                ('support',np.bool_,(count,64,96)),('known',np.bool_,(count,64,96)),
                ('occlusion',np.bool_,(count,64,96)))}
    index=0;metas=[];stamp=time.perf_counter()
    for batch in chunks(validation_samples(document),args.batch_size):
        images,_=batch_samples(batch,'cuda')
        with torch.autocast('cuda',dtype=torch.float16):p2,p3,_=model.encode(images)
        n=len(batch)
        arrays['p2'][index:index+n]=p2.cpu().numpy();arrays['p3'][index:index+n]=p3.cpu().numpy()
        for key in ('support','known','occlusion'):
            arrays[key][index:index+n]=np.stack([s[key][2::4,2::4] for s in batch])
        metas.extend(s['meta'] for s in batch);index+=n
        if index%240==0:print('cached',index,'/',count,flush=True)
    assert index==count
    for value in arrays.values():value.flush()
    write(out/'cache.json',dict(count=count,meta=metas,parent_sha256=digest(args.parent),
         dataset_sha256=digest(args.dataset),precision='CUDA autocast float16 frozen features',
         thresholds=THRESHOLDS,seconds=time.perf_counter()-stamp,
         limits=['three variants share each source image','synthetic views reuse training-derived backgrounds',
                 'mask foreground is an engineering spatial proxy, not human AF usability']))


def evaluate_head(model,cache):
    meta=read(cache/'cache.json')
    arrays={k:np.load(cache/(k+'.npy'),mmap_mode='r') for k in ('p2','p3','support','known','occlusion')}
    model.eval();predictions=[]
    with torch.no_grad():
        for start in range(0,meta['count'],64):
            p2=torch.from_numpy(np.array(arrays['p2'][start:start+64],copy=True)).cuda()
            p3=torch.from_numpy(np.array(arrays['p3'][start:start+64],copy=True)).cuda()
            with torch.autocast('cuda',dtype=torch.float16):logits=model.head(p2,p3)
            predictions.extend(decode_surface(logits))
    decisions=[]
    for i,p in enumerate(predictions):
        x,y=p['point_xy'];r,c=int(y/4),int(x/4)
        support=bool(arrays['support'][i,r,c]);occ=bool(arrays['occlusion'][i,r,c])
        known=bool(arrays['known'][i,r,c])
        category='mask_foreground' if support else ('known_occluder' if occ else ('known_background' if known else 'unknown'))
        decisions.append(dict(image_id=meta['meta'][i]['image_id'],variant=meta['meta'][i]['variant'],
                              **p,category=category))
    curve=[]
    for threshold in THRESHOLDS:
        counts=dict(total=len(decisions),selected=0,foreground=0,background=0,occluder=0,unknown=0)
        for d in decisions:
            if d['score']<threshold:continue
            counts['selected']+=1
            key={'mask_foreground':'foreground','known_occluder':'occluder','known_background':'background','unknown':'unknown'}[d['category']]
            counts[key]+=1
        counts['abstain']=len(decisions)-counts['selected']
        counts['known_wrong']=counts['background']+counts['occluder']
        curve.append(dict(threshold=threshold,counts=counts,
                          utilities={str(cost):counts['foreground']-cost*counts['known_wrong'] for cost in (2,5,10)}))
    best=max(curve,key=lambda v:(v['utilities']['5'],v['counts']['foreground'],-v['counts']['known_wrong'],v['threshold']))
    return dict(selected=best,curve=curve,points=decisions,
                selection='CUB development mask foreground minus 5 times known wrong; community labels not read')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('cache','pilot','train'),required=True)
    for key in ('dataset','parent','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cache',type=Path)
    p.add_argument('--condition',choices=('R1','R2'),default='R2')
    p.add_argument('--seed',type=int,default=20261027)
    p.add_argument('--epochs',type=int,default=8)
    p.add_argument('--epoch-samples',type=int,default=4096)
    p.add_argument('--batch-size',type=int,default=16)
    p.add_argument('--pilot-steps',type=int,default=200)
    args=p.parse_args()
    if not torch.cuda.is_available():p.error('CUDA required; no automatic backend fallback')
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    if args.mode=='cache':build_cache(args);return
    if args.mode=='train' and not args.cache:p.error('Frozen CUB validation cache required')
    out=outside_git(args.output)
    if out.is_relative_to(args.dataset.resolve().parent):p.error('Keep run separate from frozen dataset')
    out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir();(out/'executed-code').mkdir()
    for name in ('bird_surface.py','bird_parts_model.py','train_bird_surface.py'):
        shutil.copyfile(Path(__file__).with_name(name),out/'executed-code'/name)
    torch.manual_seed(20261027);np.random.seed(args.seed)
    model=FrozenSurface(args.parent).cuda()
    base_hash=state_digest(model.base);initial_head=state_digest(model.head)
    config={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()}
    config.update(parent_sha256=digest(args.parent),dataset_sha256=digest(args.dataset),
                  base_state_digest=base_hash,initial_head_digest=initial_head,
                  initialization_seed=20261027,lr=.001,thresholds=THRESHOLDS,
                  parameters_base=sum(v.numel() for v in model.base.parameters()),
                  parameters_surface=sum(v.numel() for v in model.head.parameters()),
                  community_used_for_selection=False,camera_AF_verified=False)
    write(out/'config.json',config)
    if args.cache:
        cm=read(args.cache/'cache.json')
        if cm['parent_sha256']!=config['parent_sha256'] or cm['dataset_sha256']!=config['dataset_sha256']:
            raise ValueError('Cache identity mismatch')
    optimizer=torch.optim.AdamW(model.head.parameters(),lr=.001,weight_decay=.0001)
    scaler=torch.amp.GradScaler('cuda',init_scale=128.,growth_interval=10**9)
    document=read(args.dataset)
    # Independent fixed batch-one float32 replay before and after training.
    row=next(r for r in document['records'] if r['split']=='community_train')
    from bird_surface import make_sample
    sample=make_sample(row,document['context_assets'],np.random.default_rng(17))
    probe,_=batch_samples([sample],'cuda')
    model.eval()
    with torch.no_grad():_,before=model(probe,with_base=True)
    before={k:v.detach().clone() for k,v in before.items() if torch.is_tensor(v)}
    history=[];best_key=None;start=time.perf_counter()
    try:
        epochs=1 if args.mode=='pilot' else args.epochs
        count=args.pilot_steps*args.batch_size if args.mode=='pilot' else args.epoch_samples
        for epoch in range(epochs):
            model.train();stamp=time.perf_counter();losses=[];order=hashlib.sha256();step=0
            for group in optimizer.param_groups:
                group['lr']=.001*(.1+.9*(1+math.cos(math.pi*epoch/max(1,epochs)))/2)
            for batch in chunks(training_samples(document,args.seed,epoch,count),args.batch_size):
                order.update(json.dumps([s['meta'] for s in batch],sort_keys=True).encode())
                images,targets=batch_samples(batch,'cuda');optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.float16):logits=model(images)
                loss=surface_loss(logits,targets,args.condition)
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite surface loss')
                scaler.scale(loss).backward();scaler.unscale_(optimizer)
                if any(v.grad is not None for v in model.base.parameters()):raise RuntimeError('Gradient entered frozen base')
                norm=torch.nn.utils.clip_grad_norm_(model.head.parameters(),10.)
                if not torch.isfinite(norm):raise RuntimeError('Nonfinite surface gradient')
                scaler.step(optimizer);scaler.update();losses.append(float(loss.detach()));step+=1
                if step%64==0:print(args.condition,args.seed,'epoch',epoch+1,'step',step,'loss',round(np.mean(losses[-64:]),4),flush=True)
            model.eval()
            if state_digest(model.base)!=base_hash:raise RuntimeError('Frozen parameters or BN state changed')
            with torch.no_grad():_,after=model(probe,with_base=True)
            if any(not torch.equal(v,after[k]) for k,v in before.items()):raise RuntimeError('Frozen float32 batch-one output changed')
            path=out/'checkpoints'/f'epoch-{epoch+1:03d}.pt'
            checkpoint=dict(head_state_dict={k:v.detach().cpu().clone() for k,v in model.head.state_dict().items()},
                            parent_sha256=config['parent_sha256'],epoch=epoch+1,condition=args.condition,seed=args.seed)
            torch.save(checkpoint,path)
            replay=torch.load(path,map_location='cpu',weights_only=True)
            if any(not torch.equal(v,replay['head_state_dict'][k]) for k,v in checkpoint['head_state_dict'].items()):
                raise RuntimeError('Checkpoint readback failed')
            record=dict(epoch=epoch+1,steps=step,loss=float(np.mean(losses)),sampling_sha256=order.hexdigest(),
                        seconds=time.perf_counter()-stamp,base_unchanged=True,base_outputs_equal=True)
            if args.mode=='train':
                assessment=evaluate_head(model,args.cache);write(out/f'validation-{epoch+1:03d}.json',assessment)
                selected=assessment['selected'];record['validation']=selected
                key=(selected['utilities']['5'],selected['counts']['foreground'],-selected['counts']['known_wrong'],selected['threshold'])
                if best_key is None or key>best_key:
                    best_key=key;shutil.copyfile(path,out/'best-head.pt');write(out/'validation-best.json',assessment)
            history.append(record);write(out/'history.json',history)
            write(out/'status.json',dict(status='running',epoch=epoch+1,seconds=time.perf_counter()-start))
            print(json.dumps(record),flush=True)
        if state_digest(model.head)==initial_head:raise RuntimeError('Surface head did not update')
        write(out/'status.json',dict(status='completed',epochs=len(history),seconds=time.perf_counter()-start,
              base_state_equal=True,base_outputs_equal=True,head_changed=True,
              peak_allocated_bytes=torch.cuda.max_memory_allocated()))
    except Exception as exc:
        write(out/'status.json',dict(status='failed',error=repr(exc),epochs=len(history)))
        raise


if __name__=='__main__':main()
