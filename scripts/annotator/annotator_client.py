"""AI CLI for the same local annotation API used by the browser."""
import argparse
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError


def call(url,path,method='GET',payload=None):
    req=Request(url.rstrip('/')+path,data=json.dumps(payload,allow_nan=False).encode() if payload is not None else None,
                headers={'Content-Type':'application/json'},method=method)
    try:
        with urlopen(req,timeout=30) as r:
            raw=r.read()
            return json.loads(raw) if 'application/json' in r.headers.get('Content-Type','') else raw
    except HTTPError as e:
        raise SystemExit(f'HTTP {e.code}: '+e.read().decode('utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',default='http://127.0.0.1:8765')
    p.add_argument('--actor',default='ai-local')
    s=p.add_subparsers(dest='command',required=True)
    ls=s.add_parser('list');ls.add_argument('--limit',type=int,default=20);ls.add_argument('--status');ls.add_argument('--zero-only',action='store_true')
    s.add_parser('help');s.add_parser('schema')
    get=s.add_parser('get');get.add_argument('image_id');get.add_argument('--output',type=Path)
    image=s.add_parser('image');image.add_argument('image_id');image.add_argument('--output',required=True,type=Path)
    save=s.add_parser('save');save.add_argument('file',type=Path)
    imp=s.add_parser('import');imp.add_argument('file',type=Path)
    claim=s.add_parser('claim');claim.add_argument('--zero-only',action='store_true')
    release=s.add_parser('release');release.add_argument('image_id')
    exp=s.add_parser('export');exp.add_argument('--scope',choices=['all','complete','reviewed'],default='all');exp.add_argument('--output',required=True,type=Path)
    a=p.parse_args();who={'id':a.actor,'kind':'ai'}
    if a.command in ('list','help','schema'):
        result=call(a.url,{'list':'/api/dataset','help':'/api/help','schema':'/api/schema'}[a.command])
        if a.command=='list':
            rows=[r for r in result['images'] if (not a.status or r['status']==a.status) and (not a.zero_only or r['candidate_count']==0)]
            result={'total':len(result['images']),'matching':len(rows),'images':rows[:max(0,a.limit)]}
    elif a.command=='get':result=call(a.url,'/api/annotations/'+a.image_id)
    elif a.command=='image':result=call(a.url,f'/api/images/{a.image_id}/png')
    elif a.command=='save':
        row=json.loads(a.file.read_text(encoding='utf-8'))
        result=call(a.url,'/api/annotations/'+row['image_id'],'PUT',{'actor':who,
                    'base_revision':row.get('base_revision',row.get('revision')),'annotation':row['annotation']})
    elif a.command=='import':
        rows=[json.loads(line) for line in a.file.read_text(encoding='utf-8').splitlines() if line.strip()]
        result=call(a.url,'/api/import','POST',{'actor':who,'records':[{'image_id':r['image_id'],
            'base_revision':r.get('base_revision',r.get('revision')),'annotation':r['annotation']} for r in rows]})
    elif a.command=='claim':result=call(a.url,'/api/claim','POST',{'actor':who,'zero_only':a.zero_only})
    elif a.command=='release':result=call(a.url,'/api/release-claim','POST',{'actor':who,'image_id':a.image_id})
    else:result=call(a.url,'/api/export?scope='+a.scope)
    output=getattr(a,'output',None)
    if output:
        output.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(result,bytes):output.write_bytes(result)
        else:output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'written':str(output)},ensure_ascii=True))
    elif isinstance(result,bytes):print(result.decode('utf-8'))
    else:print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
