"""Prepare CUB masks and protected community training backgrounds, outside Git."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from PIL import Image


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('dataset','full-head-dataset','cub','segmentations','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):p.error('Keep derived images outside Git')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'masks').mkdir();(a.output/'backgrounds').mkdir()
    document=json.loads(a.dataset.read_text(encoding='utf-8'))
    heads={r['image_id']:r for r in json.loads(a.full_head_dataset.read_text(encoding='utf-8'))['records']}
    relative={int(line.split()[0]):line.split()[1] for line in (a.cub/'images.txt').read_text().splitlines()}
    count=0
    for row in document['records']:
        if row['split']!='public_train' or row['source']!='CUB-200-2011':continue
        mask=a.segmentations/Path(relative[int(row['image_id'].split('_')[1])]).with_suffix('.png')
        with Image.open(a.cub/'images'/relative[int(row['image_id'].split('_')[1])]) as original:source_size=original.size
        with Image.open(mask) as im:
            if im.size!=source_size:raise ValueError('Mask/image dimension mismatch: '+row['image_id'])
            im.convert('L').resize((384,256),Image.Resampling.NEAREST).save(a.output/'masks'/(row['image_id']+'.png'))
        row['foreground_mask']=str(a.output/'masks'/(row['image_id']+'.png'))
        h=[o['box'] for o in heads[row['image_id']]['objects'] if o['kind']=='head']
        row['context_head_min_side']=min(h[0][2]-h[0][0],h[0][3]-h[0][1]) if h else 0.
        count+=1
    rng=random.Random(20261026)
    community=[r for r in document['records'] if r['split']=='community_train']
    rng.shuffle(community);backgrounds=[]
    for row in community:
        if not row['absent'] and not any(o['kind']=='bird' for o in row['objects']):continue
        protected=[o['box'] for o in row['objects']]+row['uncertain']+[[x,y,x,y] for x,y in row['eyes']]
        protected=[[a-32,b-32,c+32,d+32] for a,b,c,d in protected]
        choices=[(x,y,x+96,y+64) for x in range(0,289,48) for y in range(0,193,32)]
        rng.shuffle(choices);taken=0
        for box in choices:
            x,y,r,b=box
            if any(min(r,c)>max(x,a) and min(b,d)>max(y,z) for a,z,c,d in protected):continue
            ident=f"background_{len(backgrounds):04d}";out=a.output/'backgrounds'/(ident+'.png')
            with Image.open(row['path']) as im:im.convert('RGB').crop(box).resize((384,256),Image.Resampling.BILINEAR).save(out)
            backgrounds.append(dict(id=ident,path=str(out),parent_image_id=row['image_id'],parent_split=row['split'],crop_input_box=list(box),
                                    sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                                    status='derived protected-background assumption; not new human-confirmed absence'))
            taken+=1
            if taken==2 or len(backgrounds)==200:break
        if len(backgrounds)==200:break
    if len(backgrounds)<100:raise RuntimeError('Insufficient protected training background crops')
    sizes=[max(o['box'][2]-o['box'][0],o['box'][3]-o['box'][1]) for r in community for o in r['objects'] if o['kind']=='bird']
    document['context_assets']=dict(backgrounds=backgrounds,sizes=sizes,cub_training_masks=count,
        source_dataset_sha256=hashlib.sha256(a.dataset.read_bytes()).hexdigest(),
        limits=['background crops inherit exhaustive reviewed-body coverage assumption, not new human truth',
                'synthetic compositing and texture ribbons do not recreate real defocus/depth'])
    (a.output/'dataset.json').write_text(json.dumps(document,indent=2),encoding='utf-8')
    print(json.dumps(dict(cub_training_masks=count,backgrounds=len(backgrounds))))


if __name__=='__main__':main()
