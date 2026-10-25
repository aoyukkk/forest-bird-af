"""Verify frozen annotation PNG pixels, identity and every current label."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from PIL import Image
from forest_bird_annotator.store import Store,validate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args();store=Store(a.workspace);rows=store.dataset();errors=[];statuses=collections.Counter()
    for row in rows:
        ident=row['image_id']
        try:
            meta=store.metadata(ident);path=store.root/'images'/(ident+'.png')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['png_sha256']:raise ValueError('PNG hash mismatch')
            with Image.open(path) as im:
                if im.size!=(384,256) or im.mode!='RGB':raise ValueError('Image mode/size mismatch')
                raw=b''.join(c.tobytes() for c in im.split())
            if hashlib.sha256(raw).hexdigest()!=meta['input_sha256']:raise ValueError('CHW pixel hash mismatch')
            saved=store.get(ident);validate(saved['annotation'],meta)
            statuses[saved['annotation']['annotation_status']]+=1
        except Exception as e:errors.append({'image_id':ident,'error':str(e)})
    known={r['image_id']+'.png' for r in rows}
    extra=sorted(p.name for p in (store.root/'images').glob('*') if p.name not in known)
    report={'passed':not errors and not extra,'images':len(rows),'statuses':dict(statuses),
            'errors':errors,'unexpected_images':extra,'coordinate_space':'z8_input_384x256'}
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
