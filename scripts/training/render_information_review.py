"""Local engineering review sheets; no human annotation writes."""
import argparse
import html
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
from bird_surface import read,write,outside_git
from bird_parts_regions import render_region,context_region
from bird_guidance_metrics import point
from diagnose_bird_information import select


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('regions','diagnostic','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out=outside_git(a.output);out.mkdir(exist_ok=False,parents=True)
    rows={r['image_id']:r for r in read(a.regions)['records']}
    plan=read(a.diagnostic/'plan.json');pred=read(a.diagnostic/'community-predictions.json');report=read(a.diagnostic/'community-reports.json')
    views=['native_full','dual_full','dual_high','dual_auto_high','dual_oracle_high']
    details={k:{d['image_id']:d for d in v['detail']} for k,v in report['views'].items()}
    sheets=[];items=[]
    for i,key in enumerate(plan['cases']):
        r=rows[key]
        with Image.open(r['path']) as im:low=im.convert('RGB')
        with Image.open(r['reference_path']) as im:high=ImageOps.exif_transpose(im).convert('RGB')
        canvas=Image.new('RGB',(1152,576),'#101820');d=ImageDraw.Draw(canvas)
        for j,name in enumerate(views):
            im=low.copy();draw=ImageDraw.Draw(im)
            for obj in r['objects']:draw.rectangle(obj['box'],outline='#ffaa44',width=1)
            for x,y in r['eyes']:draw.ellipse((x-2,y-2,x+2,y+2),outline='yellow')
            chosen=select(pred[name][key],name.startswith('native'))
            if chosen:
                x,y=point(chosen);draw.ellipse((x-5,y-5,x+5,y+5),outline='#00ffff',width=2)
                draw.line((x-8,y,x+8,y),fill='#00ffff');draw.line((x,y-8,x,y+8),fill='#00ffff')
            x0=(j%3)*384;y0=(j//3)*288;canvas.paste(im,(x0,y0+30))
            d.text((x0+4,y0+2),key+' '+name,fill='white')
            d.text((x0+4,y0+15),details[name][key]['category'],fill='#aaccdd')
        objects=[o for o in r['objects'] if o['kind']=='bird'] or r['objects']
        region=context_region(objects[0]['box']) if objects else [0,0,384,256]
        canvas.paste(render_region(high,region),(768,318));d.text((772,290),'Reference crop (first labelled region)',fill='white')
        file=out/(key+'.png');canvas.save(file);items.append(dict(image_id=key,group=r['group'],file=file.name,reference_crop=region,review_status='unreviewed_engineering_panel'))
        sheets.append(canvas)
    for i in range(0,len(sheets),4):
        sheet=Image.new('RGB',(2304,1152),'black')
        for j,im in enumerate(sheets[i:i+4]):sheet.paste(im,((j%2)*1152,(j//2)*576))
        sheet.save(out/f'sheet-{i//4+1:02d}.jpg',quality=92)
    body=''.join('<section><h2>'+html.escape(x['image_id'])+'</h2><img loading="lazy" src="'+x['file']+'"></section>' for x in items)
    (out/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Information diagnostic</title><style>body{background:#101820;color:#ddd;font-family:sans-serif}img{width:100%;max-width:1536px}section{margin:24px}h1,p{margin:24px}</style><h1>'+str(len(items))+'-case engineering review</h1><p>Cyan: selected point. Orange: existing labels. Oracle uses labels; geometry is not visible surface or camera focus. This page does not confirm or modify labels.</p>'+body,encoding='utf-8')
    write(out/'manifest.json',dict(items=items,new_human_labels=False))


if __name__=='__main__':main()
