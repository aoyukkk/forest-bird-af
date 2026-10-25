"""Human correction of frozen Z8 proposals, separate from semantic labels."""
import copy
import hashlib
import json
import math
import re
from .store import Problem, actor, dumps, initial, now

SCHEMA='forest-bird-z8-correction-v1'
KINDS=('bird','head','eye','auxiliary','uncertain')
SLOTS={0:'bird',1:'head',2:'eye',3:'eye',4:'bird',5:'auxiliary'}


def describe():
    return {'schema_version':SCHEMA,'coordinate_space':'z8_input_384x256',
        'kinds':list(KINDS),'slot_display_mapping':SLOTS,'slot_training_semantics_verified':False,
        'shape':{'id':'p<original index> or n<monotonic next_id>','kind':'bird|head|eye|auxiliary|uncertain',
                 'box_xyxy':'[x1,y1,x2,y2] or null','point_xy':'[x,y] or null (eye/uncertain only)'},
        'actions':{'draft':'save without confirmation','confirm':'human confirmation; server derives decision',
                   'uncertain':'human unresolved judgment; excluded from confirmed export'},
        'decisions':{'correct':'no geometry/kind changes','partial_error':'changes with at least one unchanged original shape',
                     'error':'changes and no unchanged original shape','uncertain':'unresolved','unassessed':'pending/draft'},
        'instructions':['GET the full review and revision before PUT; keep all frozen identity fields.',
            'Use actor.kind=ai for AI drafts. Human confirmation cannot be automated.',
            'Only genuinely visible eye boundaries get boxes. Otherwise use an eye point; never invent a fixed-size box.',
            'Keep raw slots and auxiliary shapes separate from final semantic training labels.',
            'Retain unchanged native out-of-frame proposals exactly. Edited/new geometry must lie within 384x256.',
            'No proposals does not mean no bird. Empty confirmation requires explicit presence=absent.',
            'This workflow records Z8-assisted corrections, not independent blind ground truth.']}


def baseline(store,ident,c):
    meta=store.metadata(ident,c)
    pred=json.loads(c.execute('SELECT predictions FROM images WHERE id=?',(ident,)).fetchone()[0])
    items=[{'id':f'p{i}','kind':SLOTS.get(p['class_slot'],'uncertain'),'box_xyxy':p['box_input_xyxy'],'point_xy':None} for i,p in enumerate(pred)]
    identity=initial(meta)['annotation_image']
    sha=hashlib.sha256(dumps({'input':identity,'predictions':pred}).encode()).hexdigest()
    return meta,pred,items,identity,sha


def get(store,ident,c=None):
    if c is None:
        with store.connect() as conn:return get(store,ident,conn)
    meta,pred,items,identity,sha=baseline(store,ident,c)
    row=c.execute('SELECT * FROM z8_reviews WHERE id=?',(ident,)).fetchone()
    doc=json.loads(row['document']) if row else {
        'schema_version':SCHEMA,'image_id':ident,'annotation_image':identity,'baseline_sha256':sha,
        'items':items,'presence':None,'next_id':1,'notes':'','reference_consulted':False,
        'status':'pending','decision':'unassessed','diff':None,'confirmed_by':None,'confirmed_at':None,'provenance':None}
    return {'image_id':ident,'revision':row['revision'] if row else 0,'review':doc,
            'baseline':{'sha256':sha,'items':items,'predictions':pred},'batch':meta['batch'],'updated':row['updated'] if row else None}


def differences(original,items):
    old={x['id']:x for x in original};new={x['id']:x for x in items}
    changed=[{'id':i,'before':old[i],'after':new[i],'fields':[k for k in ('kind','box_xyxy','point_xy') if old[i][k]!=new[i][k]]} for i in old if i in new and old[i]!=new[i]]
    removed=[old[i] for i in old if i not in new];added=[new[i] for i in new if i not in old]
    unchanged=[i for i in old if i in new and old[i]==new[i]]
    kinds={x['kind'] for x in removed+added}
    for x in changed:kinds.update((x['before']['kind'],x['after']['kind']))
    return {'changed':changed,'removed':removed,'added':added,'unchanged_ids':unchanged,
            'changed_parts':sorted(kinds),'modified_count':len(changed)+len(removed)+len(added)}


def validate_items(items,original):
    if not isinstance(items,list) or len(items)>500:raise Problem('items must be an array of at most 500 shapes')
    old={x['id']:x for x in original};seen=set();result=[]
    for item in items:
        if not isinstance(item,dict) or set(item)!={'id','kind','box_xyxy','point_xy'}:raise Problem('Shape needs exactly id, kind, box_xyxy and point_xy')
        ident=item['id']
        if not isinstance(ident,str) or not re.fullmatch(r'(p\d+|n[1-9]\d*)',ident) or ident in seen:raise Problem('Invalid or duplicate shape ID')
        if ident.startswith('p') and ident not in old:raise Problem('Unknown original candidate ID')
        seen.add(ident)
        if item['kind'] not in KINDS:raise Problem('Invalid shape kind')
        box,point=item['box_xyxy'],item['point_xy']
        def numbers(v,n):return isinstance(v,list) and len(v)==n and all(type(x) in (int,float) and math.isfinite(x) for x in v)
        # Preserve native out-of-frame proposals exactly when unchanged.
        unchanged=ident in old and item==old[ident]
        if box is not None:
            if point is not None or not numbers(box,4) or not box[0]<box[2] or not box[1]<box[3]:raise Problem('Invalid box geometry')
            if not unchanged and not (0<=box[0]<box[2]<=384 and 0<=box[1]<box[3]<=256):raise Problem('Corrected boxes must stay inside 384x256')
        elif not numbers(point,2) or not (0<=point[0]<384 and 0<=point[1]<256) or item['kind'] not in ('eye','uncertain'):raise Problem('A point must be an eye/uncertain point inside the input')
        result.append(copy.deepcopy(item))
    return result


def save(store,ident,payload):
    if not isinstance(payload,dict):raise Problem('Request must be an object')
    who=actor(payload.get('actor'));mode=payload.get('action','draft')
    if mode not in ('draft','confirm','uncertain'):raise Problem('Unknown correction action')
    if mode!='draft' and who['kind']!='human':raise Problem('Only a human can confirm Z8 correctness')
    with store.connect() as c:
        c.execute('BEGIN IMMEDIATE');current=get(store,ident,c);old=current['review'];b=current['baseline'];rev=payload.get('base_revision')
        if type(rev) is not int or rev!=current['revision']:raise Problem('Z8 review revision conflict',409,{'current_revision':current['revision']})
        doc=payload.get('review')
        if not isinstance(doc,dict):raise Problem('review must be an object')
        for key in ('schema_version','image_id','annotation_image','baseline_sha256'):
            if doc.get(key)!=old[key]:raise Problem('Frozen Z8 review identity changed: '+key)
        if doc['baseline_sha256']!=b['sha256']:raise Problem('Original Z8 predictions changed',409)
        items=validate_items(doc.get('items'),b['items']);presence=doc.get('presence')
        if presence not in (None,'present','absent','uncertain'):raise Problem('Invalid presence')
        if presence=='absent' and items:raise Problem('No-bird confirmation cannot contain shapes')
        if mode=='confirm' and presence is None:raise Problem('Confirm bird presence before completing review')
        if mode=='confirm' and presence=='uncertain':raise Problem('Use uncertain action for uncertain presence')
        if mode=='confirm' and not items and presence!='absent':raise Problem('Empty results require explicit no-bird confirmation')
        if mode=='confirm' and any(x['kind']=='uncertain' for x in items):raise Problem('Resolve uncertain shapes or submit as uncertain')
        notes=doc.get('notes','')
        if not isinstance(notes,str) or len(notes)>10000:raise Problem('notes must be text, at most 10000 characters')
        if type(doc.get('reference_consulted')) is not bool:raise Problem('reference_consulted must be boolean')
        next_id=doc.get('next_id')
        if type(next_id) is not int or next_id<old['next_id'] or any(x['id'].startswith('n') and int(x['id'][1:])>=next_id for x in items):raise Problem('next_id must advance without recycling IDs')
        diff=differences(b['items'],items)
        decision=('correct' if not diff['modified_count'] else 'partial_error' if diff['unchanged_ids'] else 'error') if mode=='confirm' else 'uncertain' if mode=='uncertain' else 'unassessed'
        stamp=now();revision=rev+1;clean={k:old[k] for k in ('schema_version','image_id','annotation_image','baseline_sha256')}
        clean.update(items=items,presence=presence,next_id=next_id,notes=notes,reference_consulted=doc['reference_consulted'],
            status={'draft':'draft','confirm':'confirmed','uncertain':'needs_adjudication'}[mode],decision=decision,diff=diff,
            confirmed_by=who if mode!='draft' else None,confirmed_at=stamp if mode!='draft' else None,
            provenance={'actor':who,'at':stamp,'revision':revision,'parent_revision':rev})
        c.execute('INSERT INTO z8_reviews VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,document=excluded.document,updated=excluded.updated',(ident,revision,dumps(clean),stamp))
        c.execute('INSERT INTO z8_review_history VALUES(?,?,?,?,?)',(ident,revision,dumps(clean),dumps(who),stamp))
        return get(store,ident,c)


def dataset(store):
    with store.connect() as c:
        saved={r['id']:r for r in c.execute('SELECT * FROM z8_reviews')};rows=[]
        for row in c.execute('SELECT * FROM images ORDER BY id'):
            meta=json.loads(row['metadata']);record=saved.get(row['id']);doc=json.loads(record['document']) if record else {}
            rows.append({'image_id':row['id'],'batch':meta['batch'],'candidate_count':len(json.loads(row['predictions'])),
                         'status':doc.get('status','pending'),'decision':doc.get('decision','unassessed'),
                         'revision':record['revision'] if record else 0,'modified_count':(doc.get('diff') or {}).get('modified_count',0)})
        return rows


def history(store,ident):
    store.metadata(ident)
    with store.connect() as c:
        return [{'image_id':ident,'revision':r['revision'],'review':json.loads(r['document']),'actor':json.loads(r['actor']),'created':r['created']} for r in c.execute('SELECT * FROM z8_review_history WHERE id=? ORDER BY revision DESC',(ident,))]


def export(store,scope):
    if scope not in ('all','confirmed','uncertain'):raise Problem('Unknown Z8 review export scope')
    with store.connect() as c:
        result=[]
        for row in c.execute('SELECT id FROM z8_reviews ORDER BY id'):
            record=get(store,row['id'],c);status=record['review']['status']
            if scope=='confirmed' and status!='confirmed' or scope=='uncertain' and status!='needs_adjudication':continue
            result.append(record)
        return result
