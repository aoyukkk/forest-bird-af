# Confirmed labels: lossless geometry and derived formats

**English** | [简体中文](README.zh-CN.md)

**547 confirmed images**, including 12 folded duplicates and 2 explicit no-bird
frames. The frozen split selects 535 usable images: 375 train / 80 val / 80 test.
Use `in_queue` and the split; do not silently train on the 12 duplicates.

| File | Contract |
|---|---|
| [confirmed.jsonl](confirmed.jsonl) | Canonical confirmed subset: source IDs, points, boxes and auxiliary items unchanged |
| [confirmed.csv](confirmed.csv) | Image index, split, queue membership and B/H/E counts |
| [COCO view](coco/confirmed.coco.json) | 1,041 actual source boxes; 160 point-only eyes in custom `point_annotations` |
| [YOLO archive](yolo-labels.zip) | Partial measured-box TXT files; `eye-points.jsonl` sidecar and format warning |
| [summary.json](summary.json) | Counts, format version and checksums |

## Geometry matters

There are **566 bird boxes, 412 head boxes and 223 eyes**. Of those eyes, 63 have
actual source boxes and **160 are points without a measured extent**. The full
JSONL also retains 240 auxiliary items; auxiliary is not a bird target.

**No fixed-size eye boxes are generated.** The COCO `point_annotations`
extension is not standard detection annotation, and YOLO TXT cannot represent a
point. Plain COCO/YOLO loaders ignore the point sidecars and can wrongly turn
unlabelled eye regions into negatives. Use JSONL and a partial-label adapter for
complete BHE supervision. The native training pipeline does this.

Coordinates belong to the frozen **384×256 input**, not the original photograph.
Accepted native half-pixel edges are preserved in JSONL/COCO; the YOLO box view
clips edges to the input. Images come from [Releases](../../README.md#image-downloads).

## Rebuild and check

```bash
python scripts/publish/export_confirmed_labels.py \
  --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \
  --dedupe data/annotations-2026-10-25/curation/dedupe-queue-v1.json \
  --split data/annotations-2026-10-25/splits/evaluation-split-v1.json \
  --output data/annotations-2026-10-25/confirmed
python scripts/tools/verify_annotations.py
```

Text uses LF; ZIP entries have fixed timestamps and ordering. Identical inputs
produce identical outputs, including the archive and its checksums.

## Export correction on 2026-10-26

Format v2 replaces the earlier derived 12×12 eye containers with original points
and retains original item IDs and auxiliary shapes. **The 694-record source
snapshot, human annotations and frozen split did not change.** See the
[migration note](../../../docs/releases/2026-10-26-repository-update.md).

This is Z8-assisted human review, not independently blinded ground truth or
camera autofocus performance. Annotation metadata: CC BY 4.0; photographs retain
their contributors' copyrights.
