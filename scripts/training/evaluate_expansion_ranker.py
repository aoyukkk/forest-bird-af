"""Select saved point verifiers on the same expanded internal calibration."""
import argparse
from pathlib import Path
import shutil
import torch
from bird_surface import read,write,digest,outside_git
from bird_residual import PointRanker
from train_expansion_ranker import MappedCache,assessment


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('checkpoints','old-cache','new-cache','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=outside_git(a.output)
    if out.exists() or any(out.is_relative_to(x.resolve()) for x in (a.old_cache,a.new_cache)):
        p.error('Use a new output outside immutable caches')
    if not torch.cuda.is_available():p.error('CUDA required; no automatic fallback')
    checkpoints=sorted(a.checkpoints.glob('epoch-*.pt')) if a.checkpoints.is_dir() else [a.checkpoints]
    if not checkpoints:p.error('No saved epoch checkpoints')
    old,new=read(a.old_cache/'config.json'),read(a.new_cache/'config.json')
    for key in ('parent_sha256','surface_head_sha256'):
        if old[key]!=new[key]:p.error('Frozen proposer identity differs: '+key)
    out.mkdir(parents=True);torch.set_num_threads(4)
    caches=[MappedCache(a.old_cache/'real-calibration'),MappedCache(a.old_cache/'public-calibration'),MappedCache(a.new_cache/'calibration')]
    best=None;history=[]
    for source in checkpoints:
        payload=torch.load(source,map_location='cpu',weights_only=True)
        model=PointRanker(payload['large']).cuda().eval();model.load_state_dict(payload['state_dict'])
        result=assessment(model,*caches)
        history.append(dict(epoch=payload['epoch'],source_sha256=digest(source),selected=result['selected']))
        write(out/f'calibration-{payload["epoch"]:03d}.json',result)
        if best is None or tuple(result['key'])>best:
            best=tuple(result['key']);shutil.copyfile(source,out/'best.pt')
            assert digest(source)==digest(out/'best.pt')
            write(out/'calibration-best.json',result)
        del model
    write(out/'history.json',history)
    write(out/'inference-calibration.json',dict(parent_sha256=old['parent_sha256'],surface_head_sha256=old['surface_head_sha256'],ranker_sha256=digest(out/'best.pt'),
         threshold=read(out/'calibration-best.json')['selected']['threshold'],new_cache_config_sha256=digest(a.new_cache/'config.json'),experimental=True,
         community_validation_used_for_selection=False,new_independent_real_event_test=False,camera_AF_verified=False))
    print(read(out/'calibration-best.json')['selected'])


if __name__=='__main__':main()
