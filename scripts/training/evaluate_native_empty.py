"""Actual native packet replay on the same reused empty calibration frames."""
import argparse
from pathlib import Path
import time
import numpy as np
from PIL import Image
from bird_surface import read,write,digest,outside_git
from e7_backend import Backend
from z8_training_targets import records_to_predictions
from diagnose_bird_information import select


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dataset','upstream','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--body-copy',type=Path,help='Explicit same-layout native-head candidate; original package remains immutable')
    a=p.parse_args();out=outside_git(a.output);out.mkdir(exist_ok=False,parents=True)
    rows=[r for r in read(a.dataset)['records'] if r['source']=='CCT' and r['split']=='public_val'];assert len(rows)==172
    files=[a.dataset,a.upstream/'manifest.json',a.upstream/'resource744.body.bin']+[Path(r['path']) for r in rows]
    if a.body_copy:files.append(a.body_copy)
    lock={str(p):digest(p) for p in files};write(out/'inputs.json',lock)
    write(out/'plan.json',dict(images=172,batch=8,thresholds=dict(eye=.6,head=.5,bird=.4),
            native_packets=True,selection='declared E/H/B hypothesis, not camera control',new_test=False))
    backend=Backend(a.upstream,'cuda')
    if a.body_copy:
        from z8_trainable_heads import apply_body_copy
        apply_body_copy(backend,a.body_copy)
    predictions={};selections={};start=time.perf_counter()
    for first in range(0,len(rows),8):
        batch=rows[first:first+8];raws=[]
        for r in batch:
            with Image.open(r['path']) as im:raws.append(np.asarray(im.convert('RGB')).transpose(2,0,1).copy().tobytes())
        heads=backend.infer_many(raws)['heads']
        for j,r in enumerate(batch):
            result,_=backend.decode({k:v[j] for k,v in heads.items()})
            pred=[dict(q,score=q['score']/1000.) for q in records_to_predictions(result['records'])]
            predictions[r['image_id']]=pred;selections[r['image_id']]=select(pred,True)
        write(out/'progress.json',dict(completed=len(predictions),total=172))
        print(dict(completed=len(predictions),total=172,seconds=time.perf_counter()-start),flush=True)
    if lock!={str(p):digest(p) for p in files}:raise RuntimeError('Input change')
    write(out/'predictions.json',dict(predictions=predictions,selected=selections))
    groups={r['group'] for r in rows}
    summary=dict(images=len(rows),selected=sum(v is not None for v in selections.values()),
         by_kind={k:sum(v is not None and v['kind']==k for v in selections.values()) for k in ('bird','head','eye')},
         camera_macro_rate=float(np.mean([np.mean([selections[r['image_id']] is not None for r in rows if r['group']==g]) for g in groups])),
         seconds=time.perf_counter()-start,inputs_equal=True,camera_AF_verified=False,
         body_sha256=digest(a.body_copy or a.upstream/'resource744.body.bin'))
    write(out/'summary.json',summary);write(out/'status.json',dict(status='completed'));print(summary,flush=True)


if __name__=='__main__':main()
