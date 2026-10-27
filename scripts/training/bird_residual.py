"""Candidate ranking with local RGB evidence, frozen context and partial labels."""
import math
import cv2
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F

from bird_guidance_metrics import point
from bird_surface import rectangle_mask


def proposal_pool(parts, surface_logits, limit=24):
    """Prediction-only pool; injected training truths never enter this function."""
    proposals=[]
    for kind,number in (('eye',8),('head',4),('bird',4)):
        for p in sorted((x for x in parts if x['kind']==kind),key=lambda x:x['score'],reverse=True)[:number]:
            proposals.append(dict(point_xy=point(p),proposal_score=p['score'],source_kind=kind))
    probability=surface_logits.detach().float().sigmoid().reshape(1,1,64,96)
    peaks=probability==F.max_pool2d(probability,5,stride=1,padding=2)
    scores=(probability*peaks).flatten()
    values,indices=scores.topk(16)
    for score,index in zip(values.cpu().tolist(),indices.cpu().tolist()):
        if score<=0:continue
        proposals.append(dict(point_xy=[(index%96)*4+2.,(index//96)*4+2.],
                              proposal_score=score,source_kind='surface'))
    result=[]
    for p in proposals:
        x,y=p['point_xy']
        if not (0<=x<384 and 0<=y<256):continue
        if any(math.dist(p['point_xy'],q['point_xy'])<4 for q in result):continue
        result.append(p)
        if len(result)>=limit:break
    return result


def patches(pixels, points):
    """Point-centred 24px and 96px views, each bilinearly sampled to 64px."""
    result=[]
    for x,y in points:
        views=[]
        for side in (24.,96.):
            axis=(np.arange(64,dtype=np.float32)+.5-32)*side/64
            xx,yy=np.meshgrid(axis+x,axis+y)
            crop=cv2.remap(pixels,xx.astype(np.float32),yy.astype(np.float32),cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
            views.append(crop.transpose(2,0,1))
        result.append(np.concatenate(views))
    return np.stack(result) if result else np.zeros((0,6,64,64),np.uint8)


def context_vectors(p2,p3,proposals):
    if not proposals:return np.zeros((0,133),np.float16)
    grid=p2.new_tensor([[2*p['point_xy'][0]/384-1,2*p['point_xy'][1]/256-1] for p in proposals]).reshape(1,1,-1,2)
    vectors=[F.grid_sample(v.float(),grid.float(),align_corners=False).reshape(64,-1).T for v in (p2,p3)]
    kinds=('eye','head','bird','surface')
    meta=p2.new_tensor([[p['proposal_score']]+[float(p['source_kind']==k) for k in kinds] for p in proposals]).float()
    return torch.cat([*vectors,meta],1).detach().cpu().numpy().astype(np.float16)


def community_label(row,xy,injected=False):
    """Real positives are exact human eye points; exterior negatives are derived."""
    if injected and any(math.dist(xy,p)<1e-6 for p in row['eyes']):return 1,'human_eye',1.
    if row['absent']:return 0,'human_frame_absence',1.
    if not any(o['kind']=='bird' for o in row['objects']):return None,'unknown',0.
    protected=[o['box'] for o in row['objects']]+row['uncertain']+[[x,y,x,y] for x,y in row['eyes']]
    x,y=xy
    if any(a-32<=x<=c+32 and b-32<=y<=d+32 for a,b,c,d in protected):return None,'unknown',0.
    return 0,'derived_review_exterior',.5


def mask_label(sample,xy):
    x,y=xy;r,c=int(np.clip(y,0,255)),int(np.clip(x,0,383))
    if sample['target'][r,c]>.5:return 1,'mask_interior',1.
    if sample['occlusion'][r,c]:return 0,'known_synthetic_occluder',1.
    if sample['known'][r,c]:return 0,'qualified_mask_background',.5
    return None,'unknown',0.


class PointRanker(nn.Module):
    def __init__(self,large=True):
        super().__init__()
        channels=[32,64,128,192,256] if large else [16,32,64,96,128]
        layers=[];last=6
        for width in channels:
            layers.extend([nn.Conv2d(last,width,3,stride=2,padding=1),nn.SiLU()]);last=width
        self.rgb=nn.Sequential(*layers)
        self.context_norm=nn.LayerNorm(128)
        self.classifier=nn.Sequential(nn.Linear(last+133,128),nn.SiLU(),nn.Linear(128,1))
        self.large=large

    def forward(self,rgb,context):
        rgb=rgb.float()/256
        feature=self.rgb(rgb).mean((2,3))
        context=context.float()
        context=torch.cat([self.context_norm(context[:,:128]),context[:,128:]],1)
        return self.classifier(torch.cat([feature,context],1))[:,0]


def ranking_loss(logits,labels,weights,pairs):
    classification=(F.binary_cross_entropy_with_logits(logits.float(),labels.float(),reduction='none')*weights).sum()/weights.sum().clamp(min=1)
    if pairs:
        positive=logits[[a for a,b in pairs]].float();negative=logits[[b for a,b in pairs]].float()
        confidence=torch.minimum(weights[[a for a,b in pairs]],weights[[b for a,b in pairs]])
        ranking=(F.softplus(negative-positive+1)*confidence).mean()
    else:ranking=logits.sum()*0
    return classification+.5*ranking
