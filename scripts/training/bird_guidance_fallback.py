"""Coarse hints fill abstentions; they never replace an existing E/H/B target."""
from bird_guidance_metrics import select_candidate


def choose_capture_hint(predictions, threshold=.2):
    eyes=[p for p in predictions if p['kind']=='eye' and p['score']>=threshold]
    if not eyes:return None
    return dict(max(eyes,key=lambda p:p['score']),kind='capture_hint',source_kind='eye',
                output_role='coarse capture hint; not a precise eye claim')


def route_candidate(primary_predictions,capture_predictions,thresholds,capture_threshold=.2,gate='none'):
    primary=select_candidate(primary_predictions,thresholds['eye'],gate,thresholds['bird'],thresholds['head'])
    if primary is not None:return primary,False
    return choose_capture_hint(capture_predictions,capture_threshold),True
