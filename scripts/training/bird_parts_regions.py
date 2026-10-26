"""Explicit input-plane crop geometry and cross-view proposal merging."""
import math
from PIL import Image


def context_region(box, expansion=1.5, minimum_width=64.):
    x1, y1, x2, y2 = box
    width = min(384., max(minimum_width, (x2-x1)*expansion, (y2-y1)*expansion*1.5))
    height = width / 1.5
    x = max(0., min(384.-width, (x1+x2-width)/2))
    y = max(0., min(256.-height, (y1+y2-height)/2))
    return [x, y, x+width, y+height]


def tiles():
    return [[x, y, x+240., y+160.] for y in (0., 96.) for x in (0., 144.)]


def render_region(image, region):
    w, h = image.size
    extent = tuple(v*(w/384. if i%2 == 0 else h/256.) for i, v in enumerate(region))
    return image.transform((384, 256), Image.Transform.EXTENT, extent, Image.Resampling.BILINEAR)


def map_predictions(predictions, region):
    x, y, right, bottom = region
    sx, sy = (right-x)/384., (bottom-y)/256.
    result = []
    for prediction in predictions:
        p = dict(prediction)
        if p['kind'] == 'eye':
            a, b = p['point_xy']; p['point_xy'] = [x+a*sx, y+b*sy]
        else:
            a, b, c, d = p['box_xyxy']; p['box_xyxy'] = [x+a*sx, y+b*sy, x+c*sx, y+d*sy]
        result.append(p)
    return result


def merge_predictions(predictions):
    from z8_training_targets import iou
    result = []
    for kind in ('bird', 'head', 'eye'):
        kept = []
        for p in sorted((p for p in predictions if p['kind'] == kind), key=lambda p: -p['score']):
            if any(math.dist(p['point_xy'], q['point_xy']) <= 4 if kind == 'eye'
                   else iou(p['box_xyxy'], q['box_xyxy']) > .5 for q in kept):
                continue
            kept.append(p)
            if len(kept) == 20:
                break
        result.extend(kept)
    return result


def combine_native_boxes_and_eyes(native, eyes):
    """Preserve original B/H packets; apply cross-view suppression only to eyes."""
    return [p for p in native if p['kind'] in ('bird','head')]+merge_predictions([p for p in eyes if p['kind']=='eye'])


def automatic_regions(predictions):
    from z8_training_targets import iou
    birds = [p for p in predictions if p['kind'] == 'bird' and p['score'] >= .4]
    choices = birds or [p for p in predictions if p['kind'] == 'head' and p['score'] >= .5]
    regions = []
    for p in sorted(choices, key=lambda p: -p['score']):
        region = context_region(p['box_xyxy'])
        if not any(iou(region, old) > .7 for old in regions):
            regions.append(region)
        if len(regions) == 2:
            break
    return regions
