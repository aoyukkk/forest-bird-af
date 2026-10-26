"""Masked public birds on derived training-only community background crops."""
import random
import cv2
import numpy as np
from PIL import Image
import torch
from bird_parts_model import BirdDataset


def outside_regions(box, margin=8.):
    a,b,c,d=box;a=max(0.,a-margin);b=max(0.,b-margin);c=min(384.,c+margin);d=min(256.,d+margin)
    return [r for r in ([0,0,a,256],[c,0,384,256],[a,0,c,b],[a,d,c,256]) if r[2]>r[0] and r[3]>r[1]]


class HardContextDataset(BirdDataset):
    def __init__(self, rows, backgrounds, sizes):
        super().__init__(rows,False)
        self.backgrounds=backgrounds;self.sizes=sizes

    def __getitem__(self,index):
        value,s=super().__getitem__(index)
        s['augmentation']['context_composite']=False
        if not s.get('foreground_mask') or np.random.random()>=.7:
            return value,s
        pixels=(value.numpy().transpose(1,2,0)*256).astype(np.uint8)
        with Image.open(s['foreground_mask']) as im:mask=np.asarray(im.convert('L'))>127
        body=next(o['box'] for o in s['objects'] if o['kind']=='bird')
        x1,y1,x2,y2=body
        left,top=max(0,int(x1)-2),max(0,int(y1)-2)
        right,bottom=min(384,int(np.ceil(x2))+2),min(256,int(np.ceil(y2))+2)
        target=float(np.clip(np.random.choice(self.sizes),16,128))
        scale=target/max(x2-x1,y2-y1)
        w=max(2,round((right-left)*scale));h=max(2,round((bottom-top)*scale))
        if w>380 or h>252: return value,s
        bg_entry=random.choice(self.backgrounds)
        with Image.open(bg_entry['path']) as im:background=np.asarray(im.convert('RGB')).copy()
        dx,dy=np.random.randint(385-w),np.random.randint(257-h)
        fg=cv2.resize(pixels[top:bottom,left:right],(w,h),interpolation=cv2.INTER_AREA)
        alpha=cv2.resize(mask[top:bottom,left:right].astype(np.float32),(w,h),interpolation=cv2.INTER_AREA)
        output=background.copy();patch=output[dy:dy+h,dx:dx+w]
        patch[:]=np.clip(fg*alpha[...,None]+patch*(1-alpha[...,None]),0,255).astype(np.uint8)
        sx,sy=w/(right-left),h/(bottom-top)
        def point(p):return [(p[0]-left)*sx+dx,(p[1]-top)*sy+dy]
        objects=[]
        for o in s['objects']:
            a,b,c,d=o['box'];objects.append(dict(o,box=point([a,b])+point([c,d])))
        eyes=[point(p) for p in s['eyes']]
        complete=s['eye_complete']
        if s.get('context_head_min_side',0)*min(sx,sy)<8:
            eyes=[];complete=False
        else:
            kept=[]
            for p in eyes:
                a,b=p
                if dx<=a<dx+w and dy<=b<dy+h and alpha[min(h-1,max(0,int(b-dy))),min(w-1,max(0,int(a-dx)))]>.5:kept.append(p)
                else:complete=False
            eyes=kept
        occlusion=np.zeros((256,384),np.uint8)
        if np.random.random()<.25:
            # A controlled texture ribbon, not a verified real branch silhouette.
            cx,cy=dx+w//2,dy+h//2;angle=np.random.uniform(0,np.pi)
            vx,vy=int(np.cos(angle)*max(w,h)),int(np.sin(angle)*max(w,h))
            cv2.line(occlusion,(cx-vx,cy-vy),(cx+vx,cy+vy),1,int(np.random.randint(2,6)))
            output[occlusion>0]=background[occlusion>0]
            kept=[p for p in eyes if not occlusion[min(255,max(0,int(p[1]))),min(383,max(0,int(p[0])))]]
            if len(kept)!=len(eyes):complete=False
            eyes=kept
        box=next(o['box'] for o in objects if o['kind']=='bird')
        s=dict(s,objects=objects,eyes=eyes,eye_complete=complete,negative_regions=[box],uncertain=[],
               derived_background_regions=outside_regions(box),
               augmentation=dict(context_composite=True,target_size=target,background_id=bg_entry['id'],
                                 background_supervision='derived from reviewed-body coverage, not new human absence',
                                 texture_occlusion=bool(occlusion.any())))
        return torch.from_numpy(output.transpose(2,0,1).copy()).float()/256,s
