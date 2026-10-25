# Human-confirmed labels (547 images)

Every image a human reviewed and confirmed, exported as labels. This is not a
quality-filtered selection.

| File | Content |
|---|---|
| [confirmed.jsonl](confirmed.jsonl) | 547 confirmed records with bird/head/eye geometry, vendor verdict and split |
| [confirmed.csv](confirmed.csv) | Flat index: id, split, queue membership, verdict, part counts |
| [summary.json](summary.json) | Counts, part totals, per-split breakdown, label hash |
| [coco/confirmed.coco.json](coco/confirmed.coco.json) | One COCO file with all 1,201 objects |
| [yolo/\<id\>.txt](yolo/) | One YOLO file per image, `class cx cy w h` normalised |
| [yolo/classes.txt](yolo/classes.txt) | Class order: `bird`, `head`, `eye` |

## Counts

| Item | Count |
|---|---:|
| Confirmed images | 547 |
| With shapes | 545 |
| Explicitly no bird | 2 |
| Bird boxes | 566 |
| Head boxes | 412 |
| Eyes | 223 |
| COCO objects | 1,201 |

Vendor verdicts: `error` 276, `partial_error` 144, `correct` 127. Those 127 are
images you confirmed unchanged, which is still calibration data and is not
filtered out.

Splits: train 375, val 80, test 80, 535 images in total. The other 12 confirmed
images were folded out of the annotation queue by the similarity grouping;
`in_queue` records that instead of dropping them silently.

## Regenerate

```bash
python scripts/export_confirmed_labels.py \
  --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \
  --dedupe data/annotations-2026-10-25/dedupe-queue-v1.json \
  --split  data/annotations-2026-10-25/evaluation-split-v1.json \
  --output data/annotations-2026-10-25/confirmed
```

Rerunning is idempotent: identical inputs produce identical files and the same
`confirmed_sha256`.

## Three boundaries to read together

- **Coordinates are bound to the frozen 384 x 256 input**, not to the original
  photo and not to in-camera focus. Fetch images by `image_id` from the release
  packages listed in [registry.csv](../../registry.csv).
- **This is assisted review, not independent blind annotation.** The frozen
  vendor boxes were visible while confirming, so call these human-calibrated
  training/evaluation labels, not a blind held-out ground truth.
- **Eyes are centres.** An eye without a visible boundary is exported as a 12 x 12
  box flagged `eye_center_boxed`; that is a container size, not a measured eye.

## Versus the "best images" list

| | This file | `best-images-v1.json` |
|---|---|---|
| Scope | all 547 confirmed images | top 120 by score |
| Purpose | complete truth for training and evaluation | suggestion for which to look at first |
| Usable as a metric | yes, these are labels | no, review priority only |

## Licence

Annotation data CC BY 4.0; photo copyrights stay with each photographer and
follow the permission recorded per batch.
