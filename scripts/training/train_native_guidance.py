"""Matched native-head continuation; structure, file layout and consumer fixed.

Quality targets use labelled eye-anchor localization only. Missing eyes never
become negatives. Exact native forward, explicitly approximate STE backward.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import shutil
import time
import numpy as np
import torch
import torch.nn.functional as F
from e7_backend import Backend, BODY_SHA
from z8_trainable_heads import TrainableHeads
from z8_probe_labels import native_tables
from z8_training_targets import target_builder, negative_builder, partial_loss
from train_z8_heads import predict, batch_features, gradient_masks
from bird_guidance_metrics import assess_guidance
from bird_surface import read, write, digest, outside_git


def quality_loss(outputs, samples, sigma=6.):
    """Soft eye-class target from detached input-plane distance at known anchors."""
    values=[]
    for n,sample in enumerate(samples):
        for t in sample['targets']:
            if t['kind']!='eye':continue
            raw=outputs[t['head']];h,w=raw.shape[-2:]
            v=raw[n,t['anchor']*11:t['anchor']*11+11,t['row'],t['col']]
            delta=(v[:2].sigmoid()-v.new_tensor(t['xy']))*v.new_tensor([384/w,256/h])
            q=torch.exp(-delta.detach().square().sum()/(2*sigma*sigma))
            values.append(F.binary_cross_entropy_with_logits(v[5+t['class_slot']],q))
    return torch.stack(values).mean() if values else next(iter(outputs.values())).sum()*0


def guidance(result,regions):
    from z8_training_targets import records_to_predictions
    predictions={k:[dict(p,score=p['score']/1000.) for p in records_to_predictions(v)] for k,v in result['records'].items()}
    return assess_guidance(regions,predictions,threshold=.6,head_threshold=.5,bird_threshold=.4)


def selection_key(g,reference,metrics):
    c,r=g['counts'],reference['counts']
    safe=(c['geometry_supported']>=r['geometry_supported'] and c['outside_labelled_geometry']<=r['outside_labelled_geometry']
          and c['explicit_absent_selection']<=r['explicit_absent_selection'] and c['eye_unmatched_4px']<=r['eye_unmatched_4px']
          and c['eye_unassessed_selected']<=r['eye_unassessed_selected'])
    return (int(safe),c['geometry_supported'],c['eye_4px'],-c['eye_unmatched_4px'],metrics['macro_f1'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dataset','upstream','regions','exclude','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--condition',choices=('control','quality'),required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--epochs',type=int,default=16)
    p.add_argument('--lr',type=float,default=.0003);p.add_argument('--pilot',action='store_true')
    a=p.parse_args();out=outside_git(a.output);out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir();(out/'executed-code').mkdir()
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no backend substitution')
    torch.set_num_threads(4);torch.manual_seed(a.seed);random.seed(a.seed)
    doc=read(a.dataset/'dataset.json');lock=read(a.dataset/'split-lock.json');excluded=set(read(a.exclude));regions=read(a.regions)['records']
    assert digest(a.dataset/'dataset.json')==lock['dataset_sha256'] and read(a.dataset/'cache-report.json')['passed']
    backend=Backend(a.upstream,'cuda');model=TrainableHeads(backend);initial=copy.deepcopy(model.state_dict())
    masks=gradient_masks(model,'eye-small-anchor');tables=native_tables(a.upstream)
    fit=[];val=[];features_lock={}
    for row in doc['images']:
        if row['split']=='test' or (row['split']=='train' and row['image_id'] in excluded):continue
        assert row['split'] in ('train','val')
        path=a.dataset/'features'/(row['image_id']+'.pt');features_lock[row['image_id']]=digest(path)
        cached=torch.load(path,map_location='cpu',weights_only=True);targets=target_builder(row,cached['heads'],tables)
        sample=dict(row,**cached,targets=targets,negative_targets=negative_builder(row,cached['heads'],tables,targets))
        sample['features']={k:v.cuda() for k,v in cached['features'].items()};sample['heads']={k:v.cuda() for k,v in cached['heads'].items()}
        (fit if row['split']=='train' else val).append(sample)
    assert len(fit)==354 and len(val)==80 and {r['image_id'] for r in val}=={r['image_id'] for r in regions}
    config=dict(condition=a.condition,seed=a.seed,epochs=a.epochs,batch=32,lr=a.lr,preservation=10.,quality_weight=1. if a.condition=='quality' else 0.,
                quality_sigma_input_pixels=6.,initial='original native body',body_sha256=BODY_SHA,train_frames=len(fit),validation_frames=len(val),excluded_fit=sorted(excluded),
                update_mask='existing eye-small-anchor: native eye logits and first fine-anchor channels 0..9; auxiliary excluded',
                trainable_capacity=sum(int(masks[k].sum()) for k in masks),max_absolute_parameter_delta=.5,approximate_backward='STE only',native_forward=True,
                old_test_loaded=False,new_human_labels=False,A12=False,camera_deployment=False,
                selection='fixed final E/H/B geometry first, then known eye hits, then fewer known eye errors, strict macro F1 tie; no increase outside, absent, unknown-eye selections or known-eye errors')
    write(out/'config.json',config);write(out/'feature-hashes.json',features_lock)
    for name in ('train_native_guidance.py','train_z8_heads.py','z8_trainable_heads.py','z8_training_targets.py','e7_backend.py','bird_guidance_metrics.py'):
        shutil.copyfile(Path(__file__).with_name(name),out/'executed-code'/name)
    baseline,_=predict(model,backend,val,32,baseline=True);replay,_=predict(model,backend,val,32)
    if replay['records']!=baseline['records']:raise RuntimeError('Native cache parity failed')
    reference=guidance(baseline,regions);assert reference['counts']['geometry_supported']==54
    write(out/'validation-original.json',baseline);write(out/'guidance-original.json',reference)
    best=copy.deepcopy(initial);best_epoch=0;best_key=selection_key(reference,reference,baseline['metrics']);best_result=baseline;best_guidance=reference
    optimizer=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=0.);history=[];start=time.perf_counter()
    for epoch in range(1,a.epochs+1):
        order=list(range(len(fit)));random.Random(a.seed+epoch*100003).shuffle(order);losses=[];quality=[]
        sample_order=hashlib.sha256('\n'.join(fit[j]['image_id'] for j in order).encode()).hexdigest()
        for batch_index,first in enumerate(range(0,len(order),32)):
            batch=[fit[j] for j in order[first:first+32]];optimizer.zero_grad(set_to_none=True)
            outputs=model(batch_features(batch));base,parts=partial_loss(outputs,batch,preservation=10.)
            q=quality_loss(outputs,batch);loss=base+(q if a.condition=='quality' else q*0)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
            loss.backward()
            for k,v in model.named_parameters():
                if v.grad is not None:v.grad.mul_(masks[k])
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
            if not torch.isfinite(norm):raise RuntimeError('Nonfinite gradient')
            optimizer.step()
            with torch.no_grad():
                for k,v in model.named_parameters():
                    v.copy_(torch.maximum(torch.minimum(v,initial[k]+.5),initial[k]-.5));v[~masks[k]]=initial[k][~masks[k]]
            losses.append(float(loss.detach()));quality.append(float(q.detach()))
            if a.pilot and batch_index==1:break
        result,_=predict(model,backend,val,32);g=guidance(result,regions);key=selection_key(g,reference,result['metrics'])
        if key>best_key:best=copy.deepcopy(model.state_dict());best_epoch=epoch;best_key=key;best_result=result;best_guidance=g
        torch.save({k:v.detach().cpu() for k,v in model.state_dict().items()},out/'checkpoints'/f'epoch-{epoch:03d}.pt')
        write(out/f'validation-{epoch:03d}.json',result);write(out/f'guidance-{epoch:03d}.json',g)
        record=dict(epoch=epoch,loss=float(np.mean(losses)),quality_loss=float(np.mean(quality)),guidance=g['counts'],metrics=result['metrics'],key=key,sample_order_sha256=sample_order,best_epoch=best_epoch)
        history.append(record);write(out/'history.json',history);print(json.dumps(dict(epoch=epoch,condition=a.condition,seed=a.seed,geometry=g['counts']['geometry_supported'],eye=g['counts']['eye_4px'],known_eye_error=g['counts']['eye_unmatched_4px'],best_epoch=best_epoch)),flush=True)
        if a.pilot:break
    model.load_state_dict(best);torch.save({k:v.cpu() for k,v in best.items()},out/'best-head.pt')
    for k,v in model.named_parameters():
        if not torch.equal(v[~masks[k]],initial[k][~masks[k]]):raise RuntimeError('Frozen parameters changed')
    export=model.export_body(a.upstream,out/'resource744.finetuned.body.bin')
    after,_=predict(model,backend,val,32)
    if after['records']!=best_result['records']:raise RuntimeError('Best checkpoint reload differs')
    write(out/'validation-best.json',best_result);write(out/'guidance-best.json',best_guidance)
    report=dict(completed=True,condition=a.condition,seed=a.seed,selected_epoch=best_epoch,key=best_key,geometry=best_guidance['counts'],
                strict=best_result['metrics'],export=export,seconds=time.perf_counter()-start,native_cache_parity=True,frozen_parameters_equal=True,old_test_used=False)
    write(out/'report.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':main()
