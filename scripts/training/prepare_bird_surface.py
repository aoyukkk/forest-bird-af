"""Bind existing CUB training/validation masks to an immutable surface dataset."""
import argparse
from pathlib import Path
from PIL import Image
from bird_surface import digest, outside_git, read, sampling_rows, write


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('dataset','cub','segmentations','output'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();out=outside_git(a.output)
    if out.is_relative_to(a.dataset.resolve().parent) or out.is_relative_to(a.cub.resolve()):
        p.error('Output must not be inside source data')
    out.mkdir(parents=True,exist_ok=False);(out/'masks').mkdir()
    doc=read(a.dataset)
    names={int(v[0]):v[1] for line in (a.cub/'images.txt').read_text().splitlines() if (v:=line.split())}
    doc['records']=[r for r in doc['records'] if r['source']=='community' or r['source']=='CUB-200-2011']
    ledger={};counts={}
    for row in doc['records']:
        path=Path(row['path']);ledger[str(path)]=digest(path)
        row['input_sha256']=ledger[str(path)]
        if row['source']=='CUB-200-2011':
            source=a.segmentations/Path(names[int(row['image_id'].split('_')[1])]).with_suffix('.png')
            original=a.cub/'images'/names[int(row['image_id'].split('_')[1])]
            with Image.open(original) as im: size=im.size
            with Image.open(source) as im:
                if im.size!=size:raise ValueError('Official mask/image dimensions differ')
                target=out/'masks'/(row['image_id']+'.png')
                im.convert('L').resize((384,256),Image.Resampling.NEAREST).save(target)
            row['foreground_mask']=str(target)
            ledger[str(source)]=digest(source);ledger[str(target)]=digest(target)
        counts[row['split']]=counts.get(row['split'],0)+1
    for bg in doc['context_assets']['backgrounds']:
        if digest(bg['path'])!=bg['sha256']:raise ValueError('Background changed')
        ledger[bg['path']]=bg['sha256']
    public,groups=sampling_rows(doc)
    doc.update(schema='bird-surface-partial-v1',parent_dataset_sha256=digest(a.dataset),
               counts=counts,surface_sampling=dict(cub_probability=.7,community_probability=.3,
                community_eligible=sum(map(len,groups)),community_groups=len(groups),
                cub_training_images=len(public),group_balanced=True),
               surface_limits=['focal-bird masks are not exhaustive scene labels',
                               'synthetic backgrounds inherit a reviewed-coverage assumption',
                               'community eye points are sparse positives; missing eyes remain unknown'])
    write(out/'dataset.json',doc);write(out/'asset-hashes.json',ledger)
    print(doc['surface_sampling'],counts)


if __name__=='__main__':main()
