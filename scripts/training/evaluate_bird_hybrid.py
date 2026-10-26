"""Secondary validation-only eye-module selection with native B/H fixed."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from bird_parts_model import build_model
from train_bird_parts import evaluate,metric_rows,selection_diagnostic
from z8_training_targets import records_to_predictions,match_metrics


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--trials-root',type=Path,required=True)
    p.add_argument('--parent-weights',type=Path,required=True)
    p.add_argument('--native-validation',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):p.error('Keep evaluation outside Git')
    a.output.mkdir(parents=True,exist_ok=False)
    rows=read(a.dataset)['records']
    if any(r['split']!='community_val' for r in rows):raise ValueError('Validation only')
    native={k:[dict(p,score=p['score']/1000.) for p in records_to_predictions(v)] for k,v in read(a.native_validation)['records'].items()}
    native={k:[p for p in v if p['score']>={'bird':.4,'head':.5,'eye':.6}[p['kind']]] for k,v in native.items()}
    truth=metric_rows(rows);reference,_=match_metrics(truth,native)
    paths=[('parent',a.parent_weights)]
    for folder in sorted(a.trials_root.iterdir()):
        if not (folder/'report.json').exists():raise RuntimeError('Trial incomplete: '+folder.name)
        paths.extend((folder.name+'_'+name,folder/(name+'.pt')) for name in ('best','last'))
    torch.set_num_threads(4);model=build_model('n').cuda().eval()
    reports={}
    for name,path in paths:
        payload=torch.load(path,map_location='cpu',weights_only=True)
        model.load_state_dict(payload['state_dict'])
        assessment=evaluate(model,rows,1,eye_fp_budget=3)
        eye_threshold=assessment['thresholds']['eye']
        combined={key:[p for p in native[key] if p['kind'] in ('bird','head')]+
                  [p for p in predictions if p['kind']=='eye' and p['score']>=eye_threshold]
                  for key,predictions in assessment['predictions'].items()}
        metrics,detail=match_metrics(truth,combined)
        for part in ('bird','head'):assert metrics[part]==reference[part]
        tight,_=match_metrics(truth,combined,eye_pixels=2)
        loose,_=match_metrics(truth,combined,box_iou=.3,eye_pixels=8)
        report=dict(weights_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),epoch=payload['epoch'],
                    metrics=metrics,eye_2px=tight['eye'],loose_metrics=loose,
                    thresholds=dict(bird=.4,head=.5,eye=eye_threshold),
                    selection_diagnostic=selection_diagnostic(truth,combined),
                    candidate_coverage=dict(matched_images=sum(any(v['tp'] for v in d['parts'].values()) for d in detail),images=len(rows)),
                    target_met=metrics['eye']['tp']>=16 and metrics['eye']['fp']<=3,
                    body_head_identical_to_native=True,eye_views='full',eye_network_calls=1)
        reports[name]=report
        (a.output/(name+'.predictions.json')).write_text(json.dumps(combined),encoding='utf-8')
        (a.output/(name+'.assessment.json')).write_text(json.dumps(assessment),encoding='utf-8')
        print(json.dumps(dict(candidate=name,eye=metrics['eye'],target_met=report['target_met'])),flush=True)
    valid=[name for name,r in reports.items() if r['metrics']['eye']['fp']<=3]
    selected=max(valid,key=lambda name:(reports[name]['metrics']['eye']['tp'],-reports[name]['metrics']['eye']['fp'],reports[name]['eye_2px']['tp']))
    output=dict(candidates=reports,selected=selected,selected_weights=str(dict(paths)[selected]),
                scope='secondary development selection among saved best/last and parent; no unsaved-epoch optimum claimed',
                batch_size=1,validation_only=True,test_used=False,new_independent_test_available=False,
                original_native=reference,camera_AF_verified=False)
    (a.output/'report.json').write_text(json.dumps(output,indent=2),encoding='utf-8')


if __name__=='__main__':main()
