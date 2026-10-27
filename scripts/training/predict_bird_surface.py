"""Run an experimental surface head and optionally fill a frozen primary abstention."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
import torch
from bird_surface import FrozenSurface,decode_surface,digest,outside_git,read,write


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','head','calibration','image','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--primary-result',type=Path)
    p.add_argument('--device',choices=('cpu','cuda'),default='cuda')
    a=p.parse_args();out=outside_git(a.output)
    if out.exists():p.error('Use a new output; preserve prior evidence')
    if a.device=='cuda' and not torch.cuda.is_available():p.error('CUDA unavailable; CPU must be selected explicitly')
    calibration=read(a.calibration);threshold=calibration['capture_threshold']
    if not isinstance(threshold,(float,int)) or not 0<=threshold<=1.000001:
        p.error('Invalid capture threshold')
    parent_sha,head_sha=digest(a.parent),digest(a.head)
    if calibration['parent_sha256']!=parent_sha or calibration['head_sha256']!=head_sha:
        p.error('Calibration weight identity mismatch')
    primary=read(a.primary_result) if a.primary_result else None
    input_sha=digest(a.image)
    if primary is not None and primary['input_image_sha256']!=input_sha:
        p.error('Primary result belongs to another input')
    checkpoint=torch.load(a.head,map_location='cpu',weights_only=True)
    if checkpoint['parent_sha256']!=parent_sha:p.error('Head belongs to another frozen parent')
    torch.set_num_threads(4)
    model=FrozenSurface(a.parent).to(a.device).eval();model.head.load_state_dict(checkpoint['head_state_dict'])
    with Image.open(a.image) as im:
        pixels=np.asarray(ImageOps.exif_transpose(im).convert('RGB').resize((384,256),Image.Resampling.BILINEAR)).transpose(2,0,1).copy()
    value=torch.from_numpy(pixels).to(a.device).float()[None]/256
    with torch.inference_mode(),torch.autocast(a.device,dtype=torch.float16,enabled=a.device=='cuda'):
        cue=decode_surface(model(value))[0]
    accepted=cue if cue['score']>=threshold else None
    existing=primary['selected_candidate'] if primary is not None else None
    selected=existing if existing is not None else accepted
    out.parent.mkdir(parents=True,exist_ok=True)
    write(out,dict(capture_candidate=cue,accepted_capture=accepted,selected_candidate=selected,
                  primary_record_supplied=primary is not None,primary_target_preserved=existing is not None,
                  capture_threshold=threshold,parent_sha256=parent_sha,head_sha256=head_sha,
                  input_image_sha256=input_sha,device=a.device,
                  input='EXIF RGB bilinear-stretched 384x256 /256',camera_AF_verified=False,
                  experimental=True,output_role='coarse surface cue; never a precise eye',
                  limits=['no primary record means surface-only diagnostic','existing primary is never replaced',
                          'CPU float32 and CUDA float16 may differ near thresholds','deployment and generalization unverified']))
    print(selected)


if __name__=='__main__':main()
