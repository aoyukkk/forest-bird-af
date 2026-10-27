"""Select fit-only small/dark replay groups without consulting validation."""
import argparse
import math
from pathlib import Path
import numpy as np
from PIL import Image
from bird_surface import read, write, digest, outside_git


def characterize(row):
    with Image.open(row['path']) as im:
        rgb = np.asarray(im.convert('RGB'), dtype=np.float32) / 255
    bodies = [o for o in row['objects'] if o['kind'] == 'bird']
    reasons, luminance = set(), []
    if not bodies and row['objects']:
        reasons.add('partial-head-only')
    for obj in bodies:
        x1, y1, x2, y2 = obj['box']
        if max(x2-x1, y2-y1) <= 32:
            reasons.add('small-body')
        crop = rgb[max(0, math.floor(y1)):min(256, math.ceil(y2)),
                   max(0, math.floor(x1)):min(384, math.ceil(x2))]
        if crop.size:
            value = float(np.median(crop @ np.array([.2126, .7152, .0722])))
            luminance.append(value)
            if value <= .18:
                reasons.add('dark-body-box')
    return dict(image_id=row['image_id'], group=row['group'], reasons=sorted(reasons),
                median_box_luminance=luminance, input_sha256=digest(row['path']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--quarantine-group', action='append', default=[], help='Explicit suspected related fit groups; never changes old splits')
    a = p.parse_args(); out = outside_git(a.output)
    out.mkdir(parents=True, exist_ok=False)
    rows = [r for r in read(a.dataset)['records'] if r['split'] == 'community_train']
    if len(rows) != 375 or any(r['source'] != 'community' for r in rows):
        raise ValueError('Expected original 375 community fit frames')
    records = [characterize(r) for r in rows]
    quarantine = set(a.quarantine_group)
    if not quarantine <= {r['group'] for r in rows}:
        raise ValueError('Quarantine group is not a community fit group')
    excluded = [r['image_id'] for r in rows if r['group'] in quarantine]
    hard = [r for r in records if r['reasons'] and r['image_id'] not in excluded]
    if not hard:
        raise ValueError('No hard replay groups')
    result = dict(dataset_sha256=digest(a.dataset), records=records,
                  hard_ids=[r['image_id'] for r in hard],
                  excluded_fit_ids=excluded, quarantined_fit_groups=sorted(quarantine),
                  criteria=dict(max_body_side=32, median_luminance=.18, head_only=True),
                  hard_criteria_use_validation=False, new_human_labels=False,
                  quarantine_scope='explicit related-scene audit; parent and reused validation are not independent')
    write(out/'hard-replay.json', result)
    print(dict(fit_frames=len(rows), hard_frames=len(hard), hard_groups=len({r['group'] for r in hard})), flush=True)


if __name__ == '__main__':
    main()
