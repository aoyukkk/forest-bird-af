"""Frozen YOLO26-derived features and partial bird-surface supervision.

Synthetic occluders and derived backgrounds are engineering supervision, not
new human visibility labels. Missing community eyes remain unknown.
"""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import torch
from torch import nn
import torch.nn.functional as F



WIDTH, HEIGHT, STRIDE = 384, 256, 4


@lru_cache(maxsize=6144)
def load_rgb(path):
    with Image.open(path) as im:
        value=np.asarray(im.convert('RGB')).copy()
    value.setflags(write=False)
    return value


@lru_cache(maxsize=6144)
def load_mask(path):
    with Image.open(path) as im:
        value=np.asarray(im.convert('L')).copy()
    value.setflags(write=False)
    return value


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def outside_git(path):
    path = Path(path).resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError('Keep private training artifacts outside Git')
    return path


class SurfaceHead(nn.Module):
    def __init__(self, channels=32):
        super().__init__()
        self.p2 = nn.Conv2d(64, channels, 1)
        self.p3 = nn.Conv2d(64, channels, 1)
        self.refine = nn.Sequential(
            nn.SiLU(), nn.Conv2d(channels, channels, 3, padding=1, groups=channels),
            nn.Conv2d(channels, channels, 1), nn.SiLU(),
            nn.Conv2d(channels, channels, 3, padding=1, groups=channels),
            nn.Conv2d(channels, channels, 1), nn.SiLU(), nn.Conv2d(channels, 1, 1))
        nn.init.constant_(self.refine[-1].bias, -2.)

    def forward(self, p2, p3):
        return self.refine(self.p2(p2) + F.interpolate(self.p3(p3), size=p2.shape[-2:], mode='nearest'))


class FrozenSurface(nn.Module):
    def __init__(self, parent):
        super().__init__()
        from bird_parts_model import as_raw, build_model
        self.raw_decoder = as_raw
        self.base = build_model('n')
        payload = torch.load(parent, map_location='cpu', weights_only=True)
        self.base.load_state_dict(payload['state_dict'])
        self.base.requires_grad_(False)
        self.base.eval()
        self.head = SurfaceHead()
        self.features = {}
        self.handles = [self.base.model[index].register_forward_hook(self._hook(name))
                        for name, index in (('p2', 2), ('p3', 16))]

    def _hook(self, name):
        def capture(module, inputs, output):
            self.features[name] = output.detach()
        return capture

    def train(self, mode=True):
        super().train(mode)
        self.base.eval()  # Freeze running statistics as well as parameters.
        return self

    def encode(self, images):
        self.features.clear()
        with torch.no_grad():
            raw = self.raw_decoder(self.base(images))
        p2, p3 = self.features.pop('p2'), self.features.pop('p3')
        if p2.shape[1:] != (64, 64, 96) or p3.shape[1:] != (64, 32, 48):
            raise ValueError('Frozen feature contract changed')
        return p2, p3, raw

    def forward(self, images, with_base=False):
        p2, p3, raw = self.encode(images)
        logits = self.head(p2, p3)
        return (logits, raw) if with_base else logits


def rectangle_mask(boxes, margin=0):
    result = np.zeros((HEIGHT, WIDTH), np.uint8)
    for a, b, c, d in boxes:
        x1, y1 = max(0, math.floor(a-margin)), max(0, math.floor(b-margin))
        x2, y2 = min(WIDTH, math.ceil(c+margin)), min(HEIGHT, math.ceil(d+margin))
        if x2 > x1 and y2 > y1:
            result[y1:y2, x1:x2] = 1
    return result


def dense_targets(alpha, occlusion, region, synthetic=False, blur_sigma=0.):
    """Independent base supervision and explicit occluder-only ablation mask."""
    bird = alpha >= .98
    visible = bird & ~occlusion.astype(bool)
    # Adaptive input-pixel interior; tiny birds may have no reliable positive.
    ys, xs = np.where(bird)
    short_side = min(np.ptp(xs)+1, np.ptp(ys)+1) if len(xs) else 0
    radius = min(2., max(.5, short_side / 64.)) + min(1., blur_sigma)
    positive = cv2.distanceTransform(visible.astype(np.uint8), cv2.DIST_L2, 3) > radius
    expanded = cv2.dilate(bird.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    negative = (~expanded) & region.astype(bool)
    # Controlled occluder interior on original bird, not a guessed hidden eye.
    occ_core = cv2.erode(occlusion.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & bird
    positive &= ~occlusion.astype(bool)
    negative &= ~occlusion.astype(bool)
    known = positive | negative
    return positive.astype(np.float32), known, occ_core, visible


def make_sample(row, config, rng, variant=None, target_size=None):
    pixels = load_rgb(row['path']).copy()
    if pixels.shape != (HEIGHT, WIDTH, 3):
        raise ValueError('Unexpected input size')
    zeros = np.zeros((HEIGHT, WIDTH), np.uint8)
    meta = dict(image_id=row['image_id'], source=row['source'], split=row['split'],
                variant='community' if row['source']=='community' else 'original',
                source_sha256=row['source_sha256'], target_size=None, blur_sigma=0.)
    if row['source'] == 'community':
        protected = [o['box'] for o in row['objects']] + row['uncertain'] + [[x,y,x,y] for x,y in row['eyes']]
        has_body = any(o['kind']=='bird' for o in row['objects'])
        known = np.ones_like(zeros, bool) if row['absent'] else (
            ~rectangle_mask(protected,32).astype(bool) if has_body else zeros.astype(bool))
        return dict(pixels=pixels, target=zeros.astype(np.float32), known=known,
                    occlusion=zeros.astype(bool), support=zeros.astype(bool),
                    points=[list(p) for p in row['eyes']], meta=meta)
    # Official masks have multiple grey levels; some have maximum 204.
    # Match the earlier >127 foreground convention before resampling alpha.
    # Dividing by 255 then requiring .98 would turn those whole birds negative.
    alpha = (load_mask(row['foreground_mask'])>127).astype(np.float32)
    if alpha.shape != (HEIGHT, WIDTH):
        raise ValueError('Mask/input shape mismatch')
    body = next(o['box'] for o in row['objects'] if o['kind']=='bird')
    synthetic = variant in ('small','occluded','blur') or (variant is None and rng.random()<.5)
    occlusion = zeros.copy()
    sigma = 0.
    if synthetic:
        left, top = max(0,int(body[0])-2), max(0,int(body[1])-2)
        right, bottom = min(WIDTH,int(np.ceil(body[2]))+2), min(HEIGHT,int(np.ceil(body[3]))+2)
        size = float(target_size or rng.choice(config['sizes']))
        size = float(np.clip(size,16,128))
        scale = size / max(body[2]-body[0],body[3]-body[1])
        w,h = max(2,round((right-left)*scale)),max(2,round((bottom-top)*scale))
        w,h=min(WIDTH-4,w),min(HEIGHT-4,h)
        dx,dy=int(rng.integers(WIDTH-w+1)),int(rng.integers(HEIGHT-h+1))
        background = config['backgrounds'][int(rng.integers(len(config['backgrounds']))) ]
        bg=load_rgb(background['path']).copy()
        fg=cv2.resize(pixels[top:bottom,left:right],(w,h),interpolation=cv2.INTER_AREA)
        patch_alpha=cv2.resize(alpha[top:bottom,left:right],(w,h),interpolation=cv2.INTER_AREA)
        if variant=='blur' or (variant is None and rng.random()<.25):
            sigma=float(rng.uniform(.45,1.1))
            fg=cv2.GaussianBlur(fg,(0,0),sigma)
        pixels=bg.copy();patch=pixels[dy:dy+h,dx:dx+w]
        patch[:]=np.clip(fg*patch_alpha[...,None]+patch*(1-patch_alpha[...,None]),0,255).astype(np.uint8)
        alpha=np.zeros((HEIGHT,WIDTH),np.float32);alpha[dy:dy+h,dx:dx+w]=patch_alpha
        use_occ=variant in ('occluded','blur') or (variant is None and rng.random()<.5)
        if use_occ:
            cx,cy=dx+w//2,dy+h//2
            angle=float(rng.uniform(0,np.pi));length=max(w,h)
            vx,vy=int(np.cos(angle)*length),int(np.sin(angle)*length)
            cv2.line(occlusion,(cx-vx,cy-vy),(cx+vx,cy+vy),1,int(rng.integers(3,7)))
            if rng.random()<.5:
                cv2.ellipse(occlusion,(cx,cy),(max(2,w//5),max(2,h//8)),float(rng.uniform(0,180)),0,360,1,-1)
            pixels[occlusion>0]=bg[occlusion>0]
        region=np.ones_like(zeros)  # Derived protected-background assumption.
        meta.update(variant='blur' if sigma else ('occluded' if use_occ else 'small'),
                    target_size=size, background_id=background['id'], blur_sigma=sigma)
    else:
        # CUB labels focal bird, not all birds in the whole scene.
        region=rectangle_mask([body])
    target,known,occ,support=dense_targets(alpha,occlusion,region,synthetic,sigma)
    return dict(pixels=pixels,target=target,known=known,occlusion=occ,support=support,points=[],meta=meta)


def batch_samples(samples, device):
    images=torch.from_numpy(np.stack([s['pixels'].transpose(2,0,1) for s in samples])).to(device).float()/256
    targets={k:torch.from_numpy(np.stack([s[k][2::4,2::4] for s in samples])).to(device)
             for k in ('target','known','occlusion')}
    targets['points']=[s['points'] for s in samples]
    return images,targets


def surface_loss(logits, targets, condition):
    if condition not in ('R1','R2'):
        raise ValueError('Unknown surface condition')
    value=logits[:,0].float()
    y=targets['target'].float();known=targets['known'].bool()
    bce=F.binary_cross_entropy_with_logits(value,y,reduction='none')
    terms=[]
    for b in range(len(value)):
        positive=known[b] & (y[b]>.5);negative=known[b] & (y[b]<=.5)
        term=value[b].sum()*0
        if positive.any():term=term+bce[b][positive].mean()
        if negative.any():term=term+bce[b][negative].mean()
        if condition=='R2' and targets['occlusion'][b].any():
            term=term+F.softplus(value[b][targets['occlusion'][b].bool()]).mean()
        points=targets['points'][b]
        if points:
            grid=value.new_tensor([[2*x/WIDTH-1,2*y/HEIGHT-1] for x,y in points]).reshape(1,1,-1,2)
            at=F.grid_sample(value[b:b+1,None],grid,mode='bilinear',align_corners=False)
            term=term+F.softplus(-at).mean()
        terms.append(term)
    return torch.stack(terms).mean()


def decode_surface(logits):
    probability=logits.detach().float().sigmoid()[:,0]
    score,flat=probability.flatten(1).max(1)
    return [dict(kind='capture_hint',score=float(s),
                 point_xy=[float((int(i)%96)*4+2),float((int(i)//96)*4+2)],
                 source_kind='surface',output_role='coarse bird-surface cue; not a precise eye')
            for s,i in zip(score.cpu(),flat.cpu())]


def sampling_rows(document):
    public=[r for r in document['records'] if r['source']=='CUB-200-2011' and r['split']=='public_train']
    community=[r for r in document['records'] if r['split']=='community_train' and
               (r['eyes'] or r['absent'] or any(o['kind']=='bird' for o in r['objects']))]
    groups={}
    for r in community:groups.setdefault(r['group'],[]).append(r)
    if not public or not groups:raise ValueError('Missing training supervision')
    return public,list(groups.values())


def training_samples(document,seed,epoch,count):
    public,groups=sampling_rows(document)
    rng=np.random.default_rng(seed+epoch*1000003)
    for _ in range(count):
        row=public[int(rng.integers(len(public)))] if rng.random()<.7 else (
            lambda g:g[int(rng.integers(len(g)))])(groups[int(rng.integers(len(groups)))])
        yield make_sample(row,document['context_assets'],rng)


def validation_samples(document):
    rows=[r for r in document['records'] if r['source']=='CUB-200-2011' and r['split']=='public_val']
    for row in rows:
        for index,variant in enumerate(('original','small','occluded')):
            seed=int(row['image_id'].split('_')[1])*31+index+20261027
            yield make_sample(row,document['context_assets'],np.random.default_rng(seed),variant)
