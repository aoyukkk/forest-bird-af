# Datasets

**English** | [简体中文](README.zh-CN.md)

| Dataset | Files | Use |
|---|---:|---|
| [Community snapshot, 2026-10-24](community-2026-10-24/README.md) | 296 | Current photo collection and Z8 prelabels |
| [First contribution register](contributions-2026-10-23/) | 292 | Original IDs retained in the current snapshot |
| [CUB calibration set](calibration-200/) | 200 | Earlier calibration material; obtain images from CUB |

Community images and the review bundle are distributed through [Releases](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1). Manifests and proposals live in Git.

## Organization

Keep incoming files unchanged. Assign stable IDs and record source, capture sequence, occlusion, image quality, annotation status, and permission separately. One image can have several tags.

The current register contains `fb_0001` through `fb_0296`. Future imports must use the latest [manifest](community-2026-10-24/manifest.csv), matching `original_sha256` before assigning another ID.

## Annotation

Annotate every identifiable bird, its visible head, and each locatable eye. Record uncertainty and the eye/head/bird fallback target. Original-image visibility and model-input usability are separate fields.

Current prelabels contain native numeric class slots and await review. A missing detection is not a negative label. The older 292-row blank template also represents unannotated images, despite its empty instance arrays.

Keep bursts, matching RAW/JPEG captures, crops, and re-encoded versions in the same data split. Splits have not been assigned yet.

See the [prelabeling workflow](../docs/run-prelabel.md) and [dataset protocol v1, Chinese](../docs/data/DATASET-SPEC-v1.md).

## Rights

Photographers retain their image copyrights. Dataset documentation and original metadata use CC BY 4.0; this does not grant a blanket license to the photographs. CUB images follow their source terms.
