# Reviewed labels (2026-10-25 snapshot)

[简体中文](README.zh-CN.md) | **English**

This directory publishes the **Z8-assisted human correction labels** and the
**frozen evaluation split**. It contains no images, no original-asset hashes, no
database and no weights. Images come from the release packages; use
[registry.csv](../registry.csv) for the id mapping.

| File | Content |
|---|---|
| [labels/community-corrections-v1.jsonl](labels/community-corrections-v1.jsonl) | One record per image, 694 lines |
| [labels/community-corrections-v1.json](labels/community-corrections-v1.json) | Counts, label hash, dropped fields |
| [labels/summary.md](labels/summary.md) | One-screen summary |
| [evaluation-split-v1.json](evaluation-split-v1.json) | Train/val/test split of 535 images with leakage groups |
| [dedupe-queue-v1.json](dedupe-queue-v1.json) | Folded queue: 536 in queue, 158 folded, 42 groups |
| [best-images-v1.json](best-images-v1.json) | 120-image first-look ranking and its scoring rule |

Guides:

| File | Content |
|---|---|
| [TOOLCHAIN.md](TOOLCHAIN.md) | Annotation toolchain: photo to trainable label, plus export formats |
| [CURATION.md](CURATION.md) | How "best images" is ranked and the queue facts |
| [review-rounds.zh-CN.md](review-rounds.zh-CN.md) | Review rounds and open issues (Chinese) |

Training and publication boundaries: [native head fine-tune](../../docs/training/z8-native-head-finetune.md)
and [what is not published](../../docs/releases/not-published.md).

## Current state

| Review status | Images |
|---|---:|
| `confirmed` | 547 |
| `draft` | 146 |
| `needs_adjudication` | 1 |

The 547 confirmed images hold 1,441 part items: 566 bird, 412 head, 223 eye and
240 auxiliary. Two confirmed images are genuinely bird-free. The frozen vendor
candidates total 1,495 over 469 images.

`draft` rows are published so readers can see which images are still unreviewed.
**They are not negatives.** An image with vendor candidates but no human
confirmation is neither "confirmed no bird" nor "confirmed wrong".

## Fields

```json
{
  "image_id": "fb_0001",
  "annotation_image": {
    "width": 384, "height": 256,
    "png_sha256": "...", "input_chw_u8_sha256": "...",
    "preprocess_id": "review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1",
    "coordinate_space": "z8_input_384x256"
  },
  "review_status": "confirmed",
  "presence": "present",
  "decision": "error",
  "revision": 5,
  "revisions": 5,
  "confirmed": true,
  "parts": {"bird": 1, "head": 0, "eye": 0},
  "items": [{"id": "n1", "kind": "bird", "box_xyxy": [163.0, 104.0, 224.5, 142.0]}],
  "frozen_z8_candidates": {"bird": 0, "head": 0, "eye": 0, "auxiliary": 0},
  "frozen_z8_candidate_total": 0,
  "frozen_baseline_matches_current": false,
  "diff": {"added": [], "removed": [], "changed": [], "unchanged": [], "changed_parts": ["bird"]},
  "review_changes": 1,
  "record_sha256": "..."
}
```

- `kind`: `bird` (whole bird), `head` (head box including the bill), `eye` (eye
  centre), `auxiliary` (vendor auxiliary region, **not** bird truth). Of 226 eye
  items, 160 carry a centre point `point_xy` and 66 carry only a visible-boundary
  box `box_xyxy`. Eye boxes exist only where the boundary is actually visible; no
  fixed pixel box is generated in bulk.
- `decision`: `correct`, `partial_error`, `error`, `uncertain` or
  `unassessed`.
- `diff` keeps per-box add/remove/change; `frozen_z8_candidates` counts the
  vendor candidates from before review.
- Coordinate conventions: manual boxes are half-open `xyxy` on the 384 x 256
  input; vendor candidates keep the machine's inclusive pixel coordinates, so
  values such as `-0.5` appear. Both are legal.

## Split

| Split | Images | Conservative groups | Bird | Head | Eye |
|---|---:|---:|---:|---:|---:|
| train | 375 | 56 | 385 | 301 | 174 |
| val | 80 | 6 | 79 | 50 | 25 |
| test | 80 | 5 | 83 | 59 | 22 |

Splits were frozen before training, groups never cross splits, and the test set
was opened once after validation-only selection. Grouping uses submission
subdirectories, visual candidate relations and deduplicate relations: an
engineering anti-leakage approximation, not verified capture-event identity. 58
of the 80 test images belong to one conservative group.

## Verify

```bash
python scripts/verify_annotations.py
```

It checks JSON parsing, coordinate ranges, mandatory eye points, part-count
agreement, status values, group splitting, split counts, and that no path-like
or private field leaked.

## Allowed and disallowed uses

Allowed: offline bird/head/eye detection evaluation, comparing the vendor model
with research variants, reproducing the published split.

Not allowed: quoting these numbers as in-camera autofocus, eye lock-on or lens
focus performance; treating `draft` rows as negatives; treating auxiliary regions
as bird labels; presenting Z8-assisted review as independent blind annotation.
