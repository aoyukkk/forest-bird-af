# Repository check and export correction — 2026-10-26

**English** | [简体中文](2026-10-26-repository-update.zh-CN.md)

The existing topic folders are retained. The root README now starts with
photograph downloads, confirmed labels, training code and verification, with
matching English and Simplified Chinese navigation.

## Data is not relabelled

- The original 694-record source snapshot and frozen 375/80/80 split are unchanged.
- All 547 confirmed records are included, with original item IDs, points, boxes
  and auxiliary shapes. Twelve confirmed duplicates remain explicitly archived.
- All 146 draft records are folded duplicates. The active queue has 535
  confirmed records and only `fb_0588` awaiting adjudication.
- Five image releases are already published, covering all 694 assets. The
  machine-readable release index now also includes batch 05.

## Confirmed format v2

The previous derived COCO/YOLO exporter converted a point-only eye into a 12×12
container and the confirmed JSONL discarded the source point/ID. Even with a
warning, those containers are not measured human eye boxes.

The correction preserves source geometry in confirmed JSONL. The derived COCO
box view has **1,041 source boxes**; **160 point-only eyes** remain in its custom
`point_annotations` extension. YOLO contains source boxes and an `eye-points.jsonl`
sidecar. Plain detection loaders do not automatically support the points or
unknown parts; use the canonical JSONL and a partial-label adapter for full BHE
supervision. See [formats](../../data/annotations-2026-10-25/confirmed/README.md).

Exports use LF text and a deterministic ZIP. The original source snapshot did
not acquire fabricated eye boxes, and the training labels were not rewritten.

## Refactor checks

Post-move registry defaults and repository-output guards are repaired. Historical
runtime locks retain their recorded paths/hashes; a separate
[relocation map](../../experiments/source-relocations.json) describes current paths.
Broken research links now name unpublished local artifacts rather than claiming
they are repository downloads. A Markdown file-target checker is included.

Firmware, vendor weights, private database records and photo originals are not
added to Git. This update does not train a model or change the published metrics.
