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
from native_point_review import load_review, annotate_surface
from z8_trainable_heads import HEAD_BATCHES


def quality_loss(outputs, samples, sigma=6., constant_target=False):
    """Soft eye-class target from detached input-plane distance at known anchors."""
    values=[]
    for n,sample in enumerate(samples):
        for t in sample['targets']:
            if t['kind']!='eye':continue
            raw=outputs[t['head']];h,w=raw.shape[-2:]
            v=raw[n,t['anchor']*11:t['anchor']*11+11,t['row'],t['col']]
            delta=(v[:2].sigmoid()-v.new_tensor(t['xy']))*v.new_tensor([384/w,256/h])
            q=v.new_tensor(1.) if constant_target else torch.exp(-delta.detach().square().sum()/(2*sigma*sigma))
            values.append(F.binary_cross_entropy_with_logits(v[5+t['class_slot']],q))
    return torch.stack(values).mean() if values else next(iter(outputs.values())).sum()*0


def guidance(result,regions):
    from z8_training_targets import records_to_predictions
    predictions={k:[dict(p,score=p['score']/1000.) for p in records_to_predictions(v)] for k,v in result['records'].items()}
    return assess_guidance(regions,predictions,threshold=.6,head_threshold=.5,bird_threshold=.4)


def selection_key(g,reference,metrics):
    c,r=g['counts'],reference['counts']
    unknown=g.get('human_surface',{}).get('unreviewed_eye_selections',c['eye_unassessed_selected'])
    reference_unknown=reference.get('human_surface',{}).get('unreviewed_eye_selections',r['eye_unassessed_selected'])
    safe=(c['geometry_supported']>=r['geometry_supported'] and c['outside_labelled_geometry']<=r['outside_labelled_geometry']
          and c['explicit_absent_selection']<=r['explicit_absent_selection'] and c['eye_unmatched_4px']<=r['eye_unmatched_4px']
          and unknown<=reference_unknown and g.get('human_surface',{}).get('unsupported',0)<=reference.get('human_surface',{}).get('unsupported',0))
    return (int(safe),c['geometry_supported'],c['eye_4px'],-c['eye_unmatched_4px'],metrics['macro_f1'])


def update_masks(model, mode):
    if mode == 'eye-small-anchor':
        return gradient_masks(model, mode)
    if mode != 'bhe-head':
        raise ValueError('Unsupported update mode')
    masks = {}
    for i, event in enumerate(model.events):
        head = next(k for k, batches in HEAD_BATCHES.items() if event['batch'] in batches)
        offset = HEAD_BATCHES[head].index(event['batch']) * 16
        channels = 33 if head == 'coarse' else 22
        # Existing geometry/objectness and B/H/E rows only; freeze auxiliary
        # slot 5 and unused padding in both gradients and exported storage.
        allowed = torch.tensor([offset + row < channels and (offset + row) % 11 < 10
                                for row in range(16)], device=model.weights[i].device)
        masks['weights.' + str(i)] = allowed[:, None].expand_as(model.weights[i])
        if str(i) in model.biases:
            masks['biases.' + str(i)] = allowed
    return masks


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dataset','upstream','regions','exclude','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--condition',choices=('control','equal-control','quality'),required=True)
    p.add_argument('--update-mode',choices=('eye-small-anchor','bhe-head'),default='eye-small-anchor')
    p.add_argument('--review-manifest',type=Path);p.add_argument('--review',type=Path)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--epochs',type=int,default=16)
    p.add_argument('--lr',type=float,default=.0003);p.add_argument('--pilot',action='store_true')
    a=p.parse_args();out=outside_git(a.output);out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir();(out/'executed-code').mkdir()
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no backend substitution')
    torch.set_num_threads(4);torch.manual_seed(a.seed);random.seed(a.seed)
    doc=read(a.dataset/'dataset.json');lock=read(a.dataset/'split-lock.json');excluded=set(read(a.exclude));regions=read(a.regions)['records']
    assert digest(a.dataset/'dataset.json')==lock['dataset_sha256'] and read(a.dataset/'cache-report.json')['passed']
    backend=Backend(a.upstream,'cuda');model=TrainableHeads(backend);initial=copy.deepcopy(model.state_dict())
    masks=update_masks(model,a.update_mode);tables=native_tables(a.upstream)
    if bool(a.review_manifest)!=bool(a.review):raise ValueError('Review and manifest must be supplied together')
    reviewed={}
    if a.review:
        _,reviewed=load_review(a.review_manifest,a.review)
        write(out/'review-lock.json',dict(review_sha256=digest(a.review),manifest_sha256=digest(a.review_manifest),
                                        points=len(reviewed),role='validation surface only; never targets or eye labels'))
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
    config=dict(condition=a.condition,seed=a.seed,epochs=a.epochs,batch=32,lr=a.lr,preservation=10.,quality_weight=0. if a.condition=='control' else 1.,
                quality_sigma_input_pixels=6.,initial='original native body',body_sha256=BODY_SHA,train_frames=len(fit),validation_frames=len(val),excluded_fit=sorted(excluded),
                update_mask=a.update_mode,auxiliary_and_padding_frozen=True,
                trainable_capacity=sum(int(masks[k].sum()) for k in masks),max_absolute_parameter_delta=.5,approximate_backward='STE only',native_forward=True,
                old_test_loaded=False,new_human_labels=False,A12=False,camera_deployment=False,
                selection='fixed E/H/B geometry first, known eye hits, fewer known eye errors, strict macro F1 tie; no increase outside, absent, unreviewed eye selections or known eye errors; exact human-supported surface points exempt only from unreviewed counter')
    write(out/'config.json',config);write(out/'feature-hashes.json',features_lock)
    for name in ('train_native_guidance.py','native_point_review.py','train_z8_heads.py','z8_trainable_heads.py','z8_training_targets.py','e7_backend.py','bird_guidance_metrics.py'):
        shutil.copyfile(Path(__file__).with_name(name),out/'executed-code'/name)
    baseline,_=predict(model,backend,val,32,baseline=True);replay,_=predict(model,backend,val,32)
    if replay['records']!=baseline['records']:raise RuntimeError('Native cache parity failed')
    reference=annotate_surface(guidance(baseline,regions),reviewed);assert reference['counts']['geometry_supported']==54
    write(out/'validation-original.json',baseline);write(out/'guidance-original.json',reference)
    best=copy.deepcopy(initial);best_epoch=0;best_key=selection_key(reference,reference,baseline['metrics']);best_result=baseline;best_guidance=reference
    optimizer=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=0.);history=[];start=time.perf_counter()
    for epoch in range(1,a.epochs+1):
        order=list(range(len(fit)));random.Random(a.seed+epoch*100003).shuffle(order);losses=[];quality=[]
        sample_order=hashlib.sha256('\n'.join(fit[j]['image_id'] for j in order).encode()).hexdigest()
        for batch_index,first in enumerate(range(0,len(order),32)):
            batch=[fit[j] for j in order[first:first+32]];optimizer.zero_grad(set_to_none=True)
            outputs=model(batch_features(batch));base,parts=partial_loss(outputs,batch,preservation=10.)
            q=quality_loss(outputs,batch,constant_target=a.condition=='equal-control');loss=base+(q if a.condition!='control' else q*0)
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
        result,_=predict(model,backend,val,32);g=annotate_surface(guidance(result,regions),reviewed);key=selection_key(g,reference,result['metrics'])
        if key>best_key:best=copy.deepcopy(model.state_dict());best_epoch=epoch;best_key=key;best_result=result;best_guidance=g
        torch.save({k:v.detach().cpu() for k,v in model.state_dict().items()},out/'checkpoints'/f'epoch-{epoch:03d}.pt')
        write(out/f'validation-{epoch:03d}.json',result);write(out/f'guidance-{epoch:03d}.json',g)
        record=dict(epoch=epoch,loss=float(np.mean(losses)),quality_loss=float(np.mean(quality)),guidance=g['counts'],human_surface=g['human_surface'],metrics=result['metrics'],key=key,sample_order_sha256=sample_order,best_epoch=best_epoch)
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
