"""Original-resolution empty controls and complete two-stage host latency."""
import argparse
from pathlib import Path
import time
from urllib.parse import urlparse
import numpy as np
from PIL import Image, ImageOps
import torch
from bird_parts_model import build_model, as_raw, decode
from bird_parts_regions import render_region, merge_predictions
from bird_surface import read, write, digest, outside_git
from diagnose_bird_information import transform, proposal_regions, select


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','regions','box','eye','diagnostic','downloads','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--wait-for-diagnostic',action='store_true',help='Wait for native replay to finish before isolated timing')
    a=p.parse_args();out=outside_git(a.output);out.mkdir(parents=True,exist_ok=False)
    doc=read(a.dataset);rows=read(a.regions)['records'];expected=read(a.diagnostic/'dual-community-checkpoint.json')
    empty=[r for r in doc['records'] if r['source']=='CCT' and r['split']=='public_val']
    sources={r['image_id']:a.downloads/Path(urlparse(r['source_url']).path).name for r in empty}
    for r in empty:
        if digest(sources[r['image_id']])!=r['source_sha256']:raise ValueError('Original empty source missing or changed')
    write(out/'source-lock.json',{str(v):digest(v) for v in sources.values()})
    write(out/'plan.json',dict(status='frozen-before-original-empty-inference',rows=len(empty),
         policies=['parent','fallback_high','fallback_auto_high'],thresholds=dict(eye=.8,head=.4,bird=.4),
         repeated_development_only=True,host_latency='RGB in host RAM -> preprocessing, transfer, two full forwards, decode, routing and triggered extra forwards',
         latency_ids=[r['image_id'] for r in sorted(rows,key=lambda r:r['image_id'])[::10]],
         latency_repetitions_per_policy=80,warmup=5,old_test_used=False))
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    torch.set_num_threads(4);models=[]
    for path in (a.box,a.eye):
        data=torch.load(path,map_location='cpu',weights_only=True);m=build_model(data['size']).cuda().eval();m.load_state_dict(data['state_dict']);models.append(m)
    def dual(image,region=(0,0,384,256)):
        x=torch.from_numpy(np.asarray(image).transpose(2,0,1).copy()).cuda().float()[None]/256
        pred=[]
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            for index,m in enumerate(models):
                pred.extend(q for q in decode(as_raw(m(x)),m.model[-1].stride,input_size=image.size,eye_nms_radius=4*image.width/384)[0]
                            if (q['kind']=='eye')==bool(index))
        return transform(pred,region,image.size)
    records={};start=time.perf_counter()
    for i,r in enumerate(empty):
        key=r['image_id']
        with Image.open(sources[key]) as im:high=im.convert('RGB')
        low=high.resize((384,256),Image.Resampling.BILINEAR)
        with Image.open(r['path']) as im:
            if not np.array_equal(np.asarray(low),np.asarray(im.convert('RGB'))):raise ValueError('Original resize does not reproduce frozen input')
        base=dual(low);parent=select(base);up=dual(high.resize((768,512),Image.Resampling.BILINEAR))
        crops=[]
        for region in proposal_regions(base):crops.extend(dual(render_region(high,region),region))
        records[key]=dict(group=r['group'],parent=parent,fallback_high=parent or select(up),
                          fallback_auto_high=parent or select(merge_predictions(crops)),source_size=list(high.size))
        if (i+1)%40==0:print(dict(stage='original-empty',done=i+1,total=len(empty)),flush=True)
    write(out/'empty-predictions.json',records)
    print(dict(stage='original-empty-completed',counts={m:sum(v[m] is not None for v in records.values()) for m in ('parent','fallback_high','fallback_auto_high')}),flush=True)
    if a.wait_for_diagnostic:
        deadline=time.monotonic()+3600
        while not (a.diagnostic/'status.json').exists():
            if time.monotonic()>deadline:raise RuntimeError('Diagnostic did not complete; timing not measured')
            time.sleep(2)
        if read(a.diagnostic/'status.json')['status']!='completed':raise RuntimeError('Diagnostic failed; stop')
    # Timing uses the actual conditional pipeline, not cached full-frame output.
    selected_rows=sorted(rows,key=lambda r:r['image_id'])[::10];images=[]
    for r in selected_rows:
        with Image.open(r['reference_path']) as im:images.append(ImageOps.exif_transpose(im).convert('RGB').copy())
    def policy(image,mode):
        low=image.resize((384,256),Image.Resampling.BILINEAR);base=dual(low);chosen=select(base);calls=2
        if chosen is None and mode=='fallback_high':chosen=select(dual(image.resize((768,512),Image.Resampling.BILINEAR)));calls+=2
        if chosen is None and mode=='fallback_auto_high':
            crops=[]
            for region in proposal_regions(base):crops.extend(dual(render_region(image,region),region));calls+=2
            chosen=select(merge_predictions(crops))
        return chosen,calls
    modes=['parent','fallback_high','fallback_auto_high']
    for _ in range(5):
        for mode in modes:policy(images[0],mode)
    timing={m:[] for m in modes};count={m:[] for m in modes}
    expected_by_mode={'parent':'dual_full','fallback_high':'dual_high','fallback_auto_high':'dual_auto_high'}
    for i in range(80):
        j=i%len(images);key=selected_rows[j]['image_id']
        for m in modes[i%3:]+modes[:i%3]:
            torch.cuda.synchronize();t=time.perf_counter();chosen,calls=policy(images[j],m);torch.cuda.synchronize()
            timing[m].append((time.perf_counter()-t)*1000);count[m].append(calls)
            correct=select(expected['dual_full'][key]) or (select(expected[expected_by_mode[m]][key]) if m!='parent' else None)
            if chosen!=correct:raise RuntimeError('Actual policy differs from diagnostic cache')
    write(out/'latency-raw.json',dict(ms=timing,calls=count))
    # Conv/linear arithmetic and peak allocated CUDA storage, not NPU cost.
    profiles={}
    for width,height in ((384,256),(768,512)):
        ops=[0];handles=[]
        def hook(module,inputs,output):
            if isinstance(module,torch.nn.Conv2d):ops[0]+=2*output.numel()*(module.in_channels//module.groups)*module.kernel_size[0]*module.kernel_size[1]
            elif isinstance(module,torch.nn.Linear):ops[0]+=2*output.numel()*module.in_features
        for m in models:
            for module in m.modules():
                if isinstance(module,(torch.nn.Conv2d,torch.nn.Linear)):handles.append(module.register_forward_hook(hook))
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();resident=torch.cuda.memory_allocated()
        dual(Image.new('RGB',(width,height)))
        torch.cuda.synchronize()
        profiles[f'{width}x{height}']=dict(conv_linear_GFLOPs=ops[0]/1e9,peak_allocated=torch.cuda.max_memory_allocated(),resident_before=resident,
                                               incremental_peak=torch.cuda.max_memory_allocated()-resident)
        for h in handles:h.remove()
    for r in empty:
        if digest(sources[r['image_id']])!=r['source_sha256']:raise RuntimeError('Original source changed')
    empty_counts={m:sum(v[m] is not None for v in records.values()) for m in modes}
    macro={m:float(np.mean([np.mean([v[m] is not None for v in records.values() if v['group']==g]) for g in {v['group'] for v in records.values()}])) for m in modes}
    summary=dict(empty_original_counts=empty_counts,empty_camera_macro=macro,empty_originals_verified=len(empty),
                 latency={m:dict(P50_ms=float(np.percentile(timing[m],50)),P95_ms=float(np.percentile(timing[m],95)),mean_network_calls=float(np.mean(count[m]))) for m in modes},
                 compute=profiles,total_parameters=sum(p.numel() for m in models for p in m.parameters()),
                 actual_policy_replay_equal=True,seconds=time.perf_counter()-start,not_camera_latency=True,
                 deployment=dict(operator_compiler_verified=False,camera_working_memory_verified=False,camera_frame_budget_verified=False,ISP_contract_verified=False))
    write(out/'summary.json',summary);write(out/'status.json',dict(status='completed'));print(summary,flush=True)


if __name__=='__main__':main()
