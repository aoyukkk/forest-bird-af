"""CPU-only replay of cached development predictions and top-one guidance curves."""
import argparse
import hashlib
import json
from pathlib import Path
from bird_guidance_metrics import EYE_THRESHOLDS, GATES, assess_guidance, guidance_rank


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--predictions', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bird-threshold', type=float, default=.4)
    p.add_argument('--head-threshold', type=float, default=.5)
    a = p.parse_args()
    if a.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]) or a.output.exists():
        p.error('Use a new output outside public Git')
    rows = json.loads(a.dataset.read_text(encoding='utf-8'))['records']
    predictions = json.loads(a.predictions.read_text(encoding='utf-8'))
    reference = json.loads(a.reference.read_text(encoding='utf-8'))
    ids = [r['image_id'] for r in rows]
    if not ids or len(ids) != len(set(ids)) or any(r['split'] != 'community_val' for r in rows):
        p.error('Unique community validation records required; no implicit test evaluation')
    if set(predictions) != set(ids) or {d['image_id'] for d in reference['detail']} != set(ids):
        p.error('Prediction and reference IDs must exactly match the fixed denominator')
    reports = [assess_guidance(rows, predictions, threshold, gate, a.bird_threshold, a.head_threshold)
               for gate in GATES for threshold in EYE_THRESHOLDS]
    selected = max(reports, key=lambda r: (guidance_rank(r, reference), r['threshold'], r['gate'] == 'none'))
    result = dict(selected=selected, selected_rank=guidance_rank(selected, reference),
                  policy_curve=[dict(counts=r['counts'], threshold=r['threshold'], gate=r['gate'],
                                     rank=guidance_rank(r, reference)) for r in reports],
                  sources_sha256={k: hashlib.sha256(getattr(a, k).read_bytes()).hexdigest()
                                  for k in ('dataset', 'predictions', 'reference')},
                  thresholds=dict(bird=a.bird_threshold, head=a.head_threshold),
                  validation_only=True, test_used=False, camera_AF_verified=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(dict(selected_rank=result['selected_rank'], selected=selected['counts'])))


if __name__ == '__main__':
    main()
