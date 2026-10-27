"""Experimental RGB/context candidate ranking, with explicit primary preservation."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
import torch
from bird_surface import FrozenSurface,read,write,digest,outside_git
from bird_parts_model import decode
from bird_residual import PointRanker,proposal_pool,patches,context_vectors


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','surface-head','ranker','calibration','image','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--primary-result',type=Path)
    a=p.parse_args();out=outside_git(a.output)
    if out.exists():p.error('Use a new output')
    primary=read(a.primary_result) if a.primary_result else None
    input_sha=digest(a.image)
    if primary is not None and primary['input_image_sha256']!=input_sha:p.error('Primary input identity differs')
    calibration=read(a.calibration)
    for field,path in [('parent_sha256',a.parent),('surface_head_sha256',a.surface_head),('ranker_sha256',a.ranker)]:
        if calibration[field]!=digest(path):p.error('Calibration identity differs: '+field)
    existing=primary['selected_candidate'] if primary is not None else None
    candidates=[];chosen=existing
    if existing is None:
        if not torch.cuda.is_available():p.error('CUDA required; no automatic backend fallback')
        torch.set_num_threads(4)
        model=FrozenSurface(a.parent).cuda().eval()
        model.head.load_state_dict(torch.load(a.surface_head,map_location='cpu',weights_only=True)['head_state_dict'])
        payload=torch.load(a.ranker,map_location='cpu',weights_only=True)
        ranker=PointRanker(payload['large']).cuda().eval();ranker.load_state_dict(payload['state_dict'])
        with Image.open(a.image) as im:pixels=np.asarray(ImageOps.exif_transpose(im).convert('RGB').resize((384,256),Image.Resampling.BILINEAR)).copy()
        value=torch.from_numpy(pixels.transpose(2,0,1).copy()).cuda().float()[None]/256
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            p2,p3,raw=model.encode(value);surface=model.head(p2,p3)
            pool=proposal_pool(decode(raw,model.base.model[-1].stride)[0],surface)
            rgb=torch.from_numpy(patches(pixels,[q['point_xy'] for q in pool])).cuda()
            context=torch.from_numpy(context_vectors(p2,p3,pool)).cuda()
            scores=ranker(rgb,context).float().sigmoid().cpu().tolist() if pool else []
        candidates=[dict(q,score=s,kind='capture_hint',output_role='coarse candidate quality; not a precise eye') for q,s in zip(pool,scores)]
        if candidates:
            candidate=max(candidates,key=lambda q:q['score'])
            if candidate['score']>=calibration['threshold']:chosen=candidate
    out.parent.mkdir(parents=True,exist_ok=True)
    write(out,dict(selected_candidate=chosen,candidates=candidates,threshold=calibration['threshold'],
                   primary_target_preserved=existing is not None,inference_skipped=existing is not None,
                   input_image_sha256=input_sha,parent_sha256=calibration['parent_sha256'],
                   ranker_sha256=calibration['ranker_sha256'],camera_AF_verified=False,experimental=True,
                   limits=['without a primary record this is a coarse-only diagnostic',
                           'existing E/H/B choices are never replaced','no new independent real-event test']))
    print(chosen)


if __name__=='__main__':main()
