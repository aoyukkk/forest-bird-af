"""Reversible queue deduplication. Never writes image or annotation tables.

Similarity groups are engineering suggestions, not confirmed capture/sequence IDs.
Every hidden member must match its representative directly (no transitive hiding).
"""
from pathlib import Path
import hashlib
import json
import math
import os
import threading
import uuid
from datetime import datetime, timezone
from PIL import Image
from .store import Problem

LOCK = threading.Lock()
SCHEMA = 'forest-bird-queue-dedupe-v1'


def fingerprint(rows):
    return hashlib.sha256(json.dumps([(r['id'],json.loads(r['metadata'])['png_sha256']) for r in rows]).encode()).hexdigest()


def read(store):
    path=store.root/'dedupe'/'current.json'
    if not path.exists():return {'schema':SCHEMA,'groups':[],'hidden':{},'keep_ids':[],'summary':{},'available':False}
    data=json.loads(path.read_text(encoding='utf-8'))
    with store.connect() as c:rows=list(c.execute('SELECT id,metadata FROM images ORDER BY id'))
    data['available']=True;data['stale']=data['fingerprint']!=fingerprint(rows)
    if data['stale']:data['hidden']={}
    return data


def publish(store,data):
    folder=store.root/'dedupe';folder.mkdir(exist_ok=True)
    data['run_id']=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    data['created_at']=datetime.now(timezone.utc).isoformat()
    raw=json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8')
    # A full immutable receipt precedes atomic activation of the queue view.
    (folder/(data['run_id']+'.json')).write_bytes(raw)
    temp=folder/(data['run_id']+'.tmp');temp.write_bytes(raw);os.replace(temp,folder/'current.json')
    return data


def view(store):
    data=read(store)
    return {k:data[k] for k in ('schema','available','stale','run_id','created_at','groups','hidden',
            'keep_ids','candidate_groups','summary','last_decision') if k in data}


def structure(a,b):
    """Global luminance/contrast/covariance score; not windowed SSIM."""
    ma,mb=float(a.mean()),float(b.mean())
    return float((2*ma*mb+6.5025)*(2*float(((a-ma)*(b-mb)).mean())+58.5225)/
                 ((ma*ma+mb*mb+6.5025)*(float(a.var())+float(b.var())+58.5225)))


def regions(row,doc):
    result=[]
    if doc and doc.get('provenance',{}).get('actor',{}).get('kind')=='human':
        for item in doc.get('items',[]):
            if item.get('point_xy'):
                x,y=item['point_xy'];result.append([x-5,y-5,x+5,y+5])
            elif item['kind'] in ('bird','head','eye'):result.append(item['box_xyxy'])
    if not result:
        result=[p['box_input_xyxy'] for p in json.loads(row['predictions']) if p['class_slot'] in (0,1,2)]
    return [[max(0,math.floor(a)),max(0,math.floor(b)),min(384,math.ceil(c)),min(256,math.ceil(d))]
            for a,b,c,d in result if c>a and d>b]


def scan(store):
    if not LOCK.acquire(blocking=False):raise Problem('Deduplication is already running',409)
    try:
        import numpy as np
        old=read(store);keep=set(old.get('keep_ids',[]));manual=old.get('manual_hidden',{})
        with store.connect() as c:
            rows=list(c.execute('SELECT * FROM images ORDER BY id'))
            saved={r['id']:json.loads(r['document']) for r in c.execute('SELECT id,document FROM z8_reviews')}
        backup=store.backup().name
        ids=[r['id'] for r in rows];meta=[json.loads(r['metadata']) for r in rows]
        ph=[];dh=[];rgb=[];gray=[];full=[];quality=[];rois=[]
        matrix=np.cos(np.pi/32*(np.arange(32)[None,:]+.5)*np.arange(8)[:,None])
        for row,m in zip(rows,meta):
            raw=(store.root/'images'/(row['id']+'.png')).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=m['png_sha256']:raise Problem('Image integrity check failed: '+row['id'],409)
            from io import BytesIO
            with Image.open(BytesIO(raw)) as source:im=source.convert('RGB')
            if im.size!=(384,256):raise Problem('Unexpected input size: '+row['id'])
            a=np.asarray(im.resize((32,32)).convert('L'),dtype=np.float32);v=(matrix@a@matrix.T).flatten()[1:];ph.append(v>np.median(v))
            a=np.asarray(im.resize((9,8)).convert('L'),dtype=np.float32);dh.append((a[:,1:]>a[:,:-1]).flatten())
            rgb.append(np.asarray(im.resize((32,24)),dtype=np.float32))
            a=np.asarray(im.resize((96,64)).convert('L'),dtype=np.float32);gray.append(a)
            quality.append(float(np.var(a[1:-1,2:]+a[1:-1,:-2]+a[2:,1:-1]+a[:-2,1:-1]-4*a[1:-1,1:-1])))
            full.append(np.asarray(im.convert('L'),dtype=np.float32));rois.append(regions(row,saved.get(row['id'])))
        ph=np.array(ph);dh=np.array(dh);rgb=np.array(rgb);pairs=[];edges={i:set() for i in ids};parent={i:i for i in ids}
        def find(x):
            while parent[x]!=x:x=parent[x]
            return x
        for i in range(len(ids)):
            pp=(ph[i+1:]!=ph[i]).sum(axis=1);dd=(dh[i+1:]!=dh[i]).sum(axis=1)
            for rel in range(len(ids)-i-1):
                j=i+1+rel
                exact_original=bool(meta[i].get('original_sha256')) and meta[i].get('original_sha256')==meta[j].get('original_sha256')
                exact_input=meta[i]['png_sha256']==meta[j]['png_sha256']
                if not (exact_original or exact_input) and (pp[rel]>12 or dd[rel]>12):continue
                mae=float(np.abs(rgb[i]-rgb[j]).mean())
                if mae>15 and not (exact_original or exact_input):continue
                score=structure(gray[i],gray[j]);ratio=max(quality[i],quality[j])/max(1,min(quality[i],quality[j]))
                tile=float(np.abs(gray[i]-gray[j]).reshape(8,8,12,8).transpose(0,2,1,3).mean(axis=(2,3)).max())
                local=0.
                for x1,y1,x2,y2 in rois[i]+rois[j]:
                    a,b=full[i][y1:y2,x1:x2],full[j][y1:y2,x1:x2]
                    if a.size:local=max(local,float(np.abs(a-b).mean()))
                strict=exact_original or exact_input or (mae<=7 and score>=.96 and tile<=22 and ratio<=1.8 and local<=12)
                # Conflicting confirmed visibility/presence should stay separately visible.
                a,b=saved.get(ids[i],{}),saved.get(ids[j],{})
                if a.get('status')==b.get('status')=='confirmed':
                    signature=lambda d:(d['presence'],sorted(x['kind'] for x in d['items']))
                    if signature(a)!=signature(b) and not exact_original:strict=False
                pair={'a':ids[i],'b':ids[j],'ph':int(pp[rel]),'dh':int(dd[rel]),'mae':round(mae,4),
                      'structure':round(score,6),'max_tile_mae':round(tile,4),'roi_mae':round(local,4),
                      'sharpness_ratio':round(ratio,4),'collapse':bool(strict),
                      'evidence':'original_sha256' if exact_original else 'input_pixels' if exact_input else 'visual_similarity'}
                pairs.append(pair);parent[find(ids[j])]=find(ids[i])
                if strict:edges[ids[i]].add(ids[j]);edges[ids[j]].add(ids[i])
        scene={}
        for ident in ids:scene.setdefault(find(ident),[]).append(ident)
        def priority(ident):
            doc=saved.get(ident,{})
            return (0 if doc.get('status')=='confirmed' else 1 if doc.get('provenance',{}).get('actor',{}).get('kind')=='human' else 2,ident)
        remaining=set(ids);groups=[];hidden={}
        for representative in sorted(ids,key=priority):
            if representative not in remaining:continue
            members=sorted((edges[representative]&remaining)-keep-{representative})
            remaining.discard(representative)
            if members:
                groups.append({'representative':representative,'members':[representative]+members})
                for member in members:hidden[member]=representative;remaining.discard(member)
        # Manual decisions survive scans. Roots must always remain visible.
        for ident,target in manual.items():
            if ident in ids and target in ids and ident not in keep and ident!=target:
                root=target;seen={ident}
                while root in hidden and root not in seen:seen.add(root);root=hidden[root]
                if root not in seen:hidden[ident]=root
        for ident in list(hidden):
            seen={ident};target=hidden[ident]
            while target in hidden and target not in seen:seen.add(target);target=hidden[target]
            if target in seen:raise Problem('Invalid duplicate cycle')
            hidden[ident]=target
        data={'schema':SCHEMA,'fingerprint':fingerprint(rows),'available':True,'stale':False,
              'annotation_backup':backup,'groups':groups,'hidden':hidden,'keep_ids':sorted(keep&set(ids)),
              'manual_hidden':manual,'candidate_groups':[v for v in scene.values() if len(v)>1],'pairs':pairs,
              'thresholds':{'candidate_ph':12,'candidate_dh':12,'candidate_mae':15,'mae':7,'structure':.96,'tile_mae':22,'roi_mae':12,'sharpness_ratio':1.8},
              'summary':{'images':len(ids),'visible':len(ids)-len(hidden),'hidden':len(hidden),'duplicate_groups':len(groups),
                         'candidate_groups':sum(len(v)>1 for v in scene.values()),'confirmed_total':sum(d.get('status')=='confirmed' for d in saved.values()),
                         'confirmed_hidden':sum(saved.get(i,{}).get('status')=='confirmed' for i in hidden)},
              'semantics':'Reversible queue view only; no annotation transfer, deletion, training split or confirmed sequence identity.'}
        return publish(store,data)
    finally:LOCK.release()


def decide(store,body):
    """Explicit human queue decisions, stored separately from labels."""
    with LOCK:
        data=read(store)
        with store.connect() as c:rows=list(c.execute('SELECT id,metadata FROM images ORDER BY id'))
        ids={r['id'] for r in rows}
        if not data['available'] or data.get('stale'):
            if body.get('action')!='previous':raise Problem('Scan the current dataset first',409)
            # One-click manual exclusion does not depend on a similarity scan.
            data={'schema':SCHEMA,'fingerprint':fingerprint(rows),'available':True,'stale':False,
                  'groups':[],'hidden':{},'keep_ids':[],'manual_hidden':{},'candidate_groups':[],
                  'summary':{'images':len(ids),'visible':len(ids),'hidden':0,'duplicate_groups':0,'candidate_groups':0}}
        ident=body.get('image_id');target=body.get('representative');action=body.get('action');previous=None
        if ident not in ids:raise Problem('Unknown image')
        keep=set(data.get('keep_ids',[]));manual=data.setdefault('manual_hidden',{})
        if action=='previous':
            ordered=sorted(ids,key=lambda value:int(value.split('_')[1]));position=ordered.index(ident)
            if position==0:raise Problem('This is the first image; there is no previous image')
            previous=ordered[position-1];target=previous;seen=set()
            while target in data['hidden'] and target not in seen:
                seen.add(target);target=data['hidden'][target]
            if target==ident or target in seen:
                # Automatic grouping can have chosen the current image as the
                # previous image's representative. Explicit human intent wins.
                target=previous;data['hidden'].pop(target,None)
            keep.add(target);manual.pop(target,None);data['hidden'].pop(target,None)
            keep.discard(ident);manual[ident]=target;data['hidden'][ident]=target
            for other,rep in list(data['hidden'].items()):
                if rep==ident:data['hidden'][other]=target
        elif action=='keep':keep.add(ident);manual.pop(ident,None);data['hidden'].pop(ident,None)
        elif action=='restore':
            # Undo one manual decision: the image returns to the visible queue and
            # any automatic collapse that leaned on it is recomputed on next scan.
            manual.pop(ident,None);keep.discard(ident);data['hidden'].pop(ident,None)
            for other,rep in list(data['hidden'].items()):
                if rep==ident and other in manual:manual[other]=data['hidden'].get(other,rep)
        elif action=='hide':
            if target not in ids or ident==target:raise Problem('Choose a different existing representative')
            seen={ident}
            while target in data['hidden'] and target not in seen:seen.add(target);target=data['hidden'][target]
            if target in seen:raise Problem('Duplicate cycle rejected')
            keep.discard(ident);manual[ident]=target;data['hidden'][ident]=target
            for other,rep in list(data['hidden'].items()):
                if rep==ident:data['hidden'][other]=target
        else:raise Problem('Unknown dedupe action')
        data['keep_ids']=sorted(keep);data['summary']['hidden']=len(data['hidden']);data['summary']['visible']=len(ids)-len(data['hidden'])
        with store.connect() as c:
            confirmed={r[0] for r in c.execute('SELECT id FROM z8_reviews WHERE json_extract(document,\'$.status\')=\'confirmed\'')}
        data['summary']['confirmed_hidden']=len(confirmed&set(data['hidden']))
        data['summary']['manual_hidden']=len(manual)
        data['last_decision']={'image_id':ident,'action':action,'representative':target if action in ('hide','previous') else None,
                               'previous_image_id':previous}
        return publish(store,data)
