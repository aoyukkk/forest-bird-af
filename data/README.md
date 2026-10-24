# Datasets

**English** | [简体中文](README.zh-CN.md)

| Dataset | Files | Use |
|---|---:|---|
| [Cumulative register](registry.csv) | 570 | Authoritative IDs and source hashes for future imports |
| [Community batch 03](community-2026-10-24-batch03/README.md) | 47 | New NEFs, embedded-JPEG review images, and Z8 proposals; IDs fb_0524–fb_0570 |
| [Community batch 02](community-2026-10-24-batch02/README.md) | 227 | New images and Z8 prelabels, IDs fb_0297–fb_0523 |
| [First community snapshot](community-2026-10-24/README.md) | 296 | Frozen first release and Z8 prelabels |
| [First contribution register](contributions-2026-10-23/) | 292 | Original IDs retained in the current snapshot |
| [CUB calibration set](calibration-200/) | 200 | Earlier calibration material; obtain images from CUB |

Community images, fixed simulation inputs, and review bundles are distributed through [Releases](https://github.com/aoyukkk/forest-bird-af/releases). Manifests and proposals live in Git. The three community batches contain different assets; download all three for all 570 images.

## Organization

Keep incoming files unchanged. Assign stable IDs and record source, capture sequence, occlusion, image quality, annotation status, and permission separately. One image can have several tags.

The current register contains `fb_0001` through `fb_0570`. Future imports must use [registry.csv](registry.csv), matching `original_sha256` before assigning another ID. Batch manifests are frozen historical subsets.

## Annotation

Annotate every identifiable bird, its visible head, and each locatable eye. Record uncertainty and the eye/head/bird fallback target. Original-image visibility and model-input usability are separate fields.

Current prelabels contain native numeric class slots and await review. A missing detection is not a negative label. The older 292-row blank template also represents unannotated images, despite its empty instance arrays.

Keep bursts, matching RAW/JPEG captures, crops, and re-encoded versions in the same data split. Splits have not been assigned yet.

See the [prelabeling workflow](../docs/run-prelabel.md) and [dataset protocol v1, Chinese](../docs/data/DATASET-SPEC-v1.md).

## Rights

Photographers retain their image copyrights. Dataset documentation and original metadata use CC BY 4.0; this does not grant a blanket license to the photographs. CUB images follow their source terms.
