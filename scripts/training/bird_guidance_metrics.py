"""Top-one geometric guidance proxies on partial labels, not camera success.

No model or torch dependency. A point inside a box may still lie on an occluder;
these metrics never label it as a visible surface, correct depth, or identity.
"""
import math
from collections import Counter

EYE_THRESHOLDS = (.05, .1, .15, .2, .25, .3, .4, .5, .6, .7, .8, .9, .95, .975, .99, .995, 1.01)
GATES = ('none', 'head-or-high')


def point(candidate):
    if candidate.get('point_xy') is not None:
        return candidate['point_xy']
    a, b, c, d = candidate['box_xyxy']
    return [(a + c) / 2, (b + d) / 2]


def inside(p, box):
    return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]


def select_candidate(predictions, threshold=.8, gate='none', bird_threshold=.4, head_threshold=.5):
    """Declared E/H/B hypothesis. Gates use predictions only, never labels."""
    if gate not in GATES:
        raise ValueError('Unknown eye gate')
    boxes = [p for p in predictions if p['kind'] in ('bird', 'head') and
             p['score'] >= (bird_threshold if p['kind'] == 'bird' else head_threshold)]
    heads = [p['box_xyxy'] for p in boxes if p['kind'] == 'head']
    eyes = [p for p in predictions if p['kind'] == 'eye' and p['score'] >= threshold]
    if gate == 'head-or-high':
        eyes = [p for p in eyes if p['score'] >= .95 or any(inside(point(p), b) for b in heads)]
    for kind in ('eye', 'head', 'bird'):
        items = eyes if kind == 'eye' else [p for p in boxes if p['kind'] == kind]
        if items:
            return max(items, key=lambda p: p['score'])
    return None


def assess_guidance(rows, predictions, threshold=.8, gate='none', bird_threshold=.4, head_threshold=.5,
                    selected_by_id=None):
    """Fixed denominators, conditional eye errors, and explicit unknowns.

    nearest-eye matches cannot establish designated-bird identity. Out-of-box
    points are unmatched geometry, not proven background/branch false locks.
    """
    if selected_by_id is not None and set(selected_by_id) != {r['image_id'] for r in rows}:
        raise ValueError('External selection IDs must exactly match the fixed denominator')
    counts = Counter({k: 0 for k in (
        'images', 'selected', 'selected_eye', 'abstain', 'eye_known_images',
        'eye_labelled_images', 'eye_known_selected', 'eye_unassessed_selected',
        'eye_2px', 'eye_4px', 'eye_8px', 'eye_unmatched_4px',
        'geometry_supported', 'outside_labelled_geometry', 'unknown_geometry',
        'explicit_absent_selection', 'head_region', 'bird_region',
        'wrong_eye_over_geometric_fallback', 'strict_eye_geometry', 'near_eye_geometry')})
    detail = []
    for row in rows:
        key = row['image_id']
        if key not in predictions:
            raise ValueError('Missing prediction row: ' + key)
        eyes = row['eyes']
        objects = row['objects']
        absent = row['absent']
        eye_known = bool(eyes) or absent or (row['eye_complete'] and not eyes)
        counts['images'] += 1
        counts['eye_known_images'] += int(eye_known)
        counts['eye_labelled_images'] += int(bool(eyes))
        chosen = (select_candidate(predictions[key], threshold, gate, bird_threshold, head_threshold)
                  if selected_by_id is None else selected_by_id[key])
        record = dict(image_id=key, group=row['group'], selected=chosen, eye_known=eye_known,
                      nearest_eye_pixels=None, category='abstain')
        if chosen is None:
            counts['abstain'] += 1
            detail.append(record)
            continue
        counts['selected'] += 1
        p = point(chosen)
        record['inside_protected_region'] = any(inside(p, b) for b in row.get('uncertain', []))
        distance = min((math.dist(p, e) for e in eyes), default=math.inf)
        record['nearest_eye_pixels'] = distance if math.isfinite(distance) else None
        if chosen['kind'] == 'eye':
            counts['selected_eye'] += 1
            counts['eye_known_selected' if eye_known else 'eye_unassessed_selected'] += 1
            if eye_known:
                for radius in (2, 4, 8):
                    counts[f'eye_{radius}px'] += int(distance <= radius)
                counts['eye_unmatched_4px'] += int(distance > 4)
        if absent:
            category = 'explicit_absent_selection'
        elif distance <= 4:
            category = 'strict_eye_geometry'
        elif distance <= 8:
            # A near-eye cue is only coarse; never a precise eye hit.
            category = 'near_eye_geometry'
        elif any(o['kind'] == 'head' and inside(p, o['box']) for o in objects):
            category = 'head_region'
        elif any(o['kind'] == 'bird' and inside(p, o['box']) for o in objects):
            category = 'bird_region'
        elif record['inside_protected_region']:
            category = 'unknown_geometry'
        elif objects:
            category = 'outside_labelled_geometry'
        else:
            category = 'unknown_geometry'
        record['category'] = category
        counts[category] += 1
        counts['geometry_supported'] += int(category in (
            'strict_eye_geometry', 'near_eye_geometry', 'head_region', 'bird_region'))
        if chosen['kind'] == 'eye' and eye_known and distance > 4:
            fallback = select_candidate([q for q in predictions[key] if q['kind'] != 'eye'],
                                        threshold, gate, bird_threshold, head_threshold)
            if fallback is not None:
                q = point(fallback)
                counts['wrong_eye_over_geometric_fallback'] += int(
                    any(inside(q, o['box']) for o in objects))
        detail.append(record)
    return dict(counts=dict(counts), threshold=threshold, gate=gate, detail=detail,
                limits=['geometric proxies only; visible surface and depth are unassessed',
                        'unlabelled eyes remain unknown; eye precision uses fixed known-eye subset',
                        'no designated-subject identity or temporal/lens proof'],
                validation_only=True, camera_AF_verified=False)


def guidance_rank(report, reference):
    """Protect parent coarse support and conditional top-eye error count.

    Avoid satisfying a precision ratio merely by rejecting everything; preserve
    the same fixed denominators and explicitly constrain unknown eye promotion.
    This is a development selection rule, not a statistically certified gate.
    """
    c, r = report['counts'], reference['counts']
    valid = (c['geometry_supported'] >= r['geometry_supported'] and
             c['eye_unmatched_4px'] <= r['eye_unmatched_4px'] and
             c['eye_unassessed_selected'] <= r['eye_unassessed_selected'] and
             c['explicit_absent_selection'] <= r['explicit_absent_selection'])
    return (int(valid), c['eye_4px'], c['geometry_supported'], -c['eye_unmatched_4px'],
            -c['eye_unassessed_selected'], c['eye_2px'], -c['outside_labelled_geometry'])


def policy_curve(rows, predictions, reference, gates=GATES):
    reports = [assess_guidance(rows, predictions, t, gate)
               for gate in gates for t in EYE_THRESHOLDS]
    selected = max(reports, key=lambda r: (guidance_rank(r, reference), r['threshold'], r['gate'] == 'none'))
    return selected, [dict(counts=r['counts'], threshold=r['threshold'], gate=r['gate'],
                           rank=guidance_rank(r, reference)) for r in reports]
