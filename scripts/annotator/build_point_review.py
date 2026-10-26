"""Build a self-contained human review page from separate AI point drafts."""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def build(workspace, output):
    repo=Path(__file__).resolve().parents[2]
    if output.resolve().is_relative_to(repo) or output.exists():
        raise ValueError('Use a new HTML file outside public Git')
    document=json.loads((workspace/'manifest.json').read_text(encoding='utf-8'))
    items=[]
    for source in document['records']:
        image_id=source['image_id']
        draft=json.loads((workspace/'drafts'/(image_id+'.json')).read_text(encoding='utf-8'))
        if draft['image_id']!=image_id or draft['input_sha256']!=source['source_sha256'] or draft['point_xy']!=source['point_xy']:
            raise ValueError('Draft identity mismatch: '+image_id)
        if draft['actor_kind']!='ai' or draft['status']!='draft' or draft['human_confirmed'] or draft['accepted_for_training']:
            raise ValueError('AI proposals must remain unconfirmed drafts')
        panel=Path(source['panel_path']).read_bytes()
        if hashlib.sha256(panel).hexdigest()!=source['panel_sha256']:
            raise ValueError('View changed: '+image_id)
        raw=Path(source['source_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['source_sha256']:
            raise ValueError('Input changed: '+image_id)
        identity=json.dumps([image_id,source['source_sha256'],source['point_xy']],separators=(',',':'))
        items.append(dict(image_id=image_id,candidate_id=hashlib.sha256(identity.encode()).hexdigest(),
                          input_sha256=source['source_sha256'],point_xy=source['point_xy'],
                          image='data:image/png;base64,'+base64.b64encode(panel).decode(),ai=draft['judgement']))
    if not items or len({x['image_id'] for x in items})!=len(items):
        raise ValueError('Expected nonempty unique review records')
    dataset_id=hashlib.sha256(json.dumps([x['candidate_id'] for x in items]).encode()).hexdigest()
    seed=json.dumps(dict(dataset_id=dataset_id,items=items),ensure_ascii=False).replace('<','\\u003c')
    directory=Path(__file__).resolve().parent
    html=(directory/'point_review_template.html').read_text(encoding='utf-8')
    html=html.replace('__CORE__',(directory/'point_review_core.js').read_text(encoding='utf-8'),1).replace('__SEED__',seed,1)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding='utf-8')
    return dict(images=len(items),dataset_id=dataset_id,initial_human_confirmed=0,
                output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),bytes=output.stat().st_size)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(build(a.workspace,a.output)))


if __name__=='__main__':main()
