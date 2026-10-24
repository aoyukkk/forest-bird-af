# Community bird images: batch 02

**English** | [简体中文](README.zh-CN.md)

227 new JPGs, IDs **fb_0297–fb_0523**. Together with the first 296 images, the cumulative register contains **523 assets**. Download this batch from [release v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2); the [first release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) remains unchanged.

## Downloads

| Archive | Contents |
|---|---|
| `community-images-20261024-batch02-part01-of01.zip` | 227 original-resolution public JPG copies, manifest, and image validation |
| `z8-inputs-384x256-20261024-batch02.zip` | 227 lossless 384 × 256 RGB PNGs and exact saved CHW uint8 input buffers |
| `z8-prelabels-review-20261024-batch02.zip` | Overlays, previews, raw-slot predictions, and an English/Simplified Chinese review page |
| `SHA256SUMS.txt` | Checksums for all three ZIPs |

Extract the image and review archives into the same directory, then open `review.html`. This batch already includes the bilingual page and has a separate browser-storage key from the first batch. Export decisions as JSON after review.

## Import and image checks

The incoming ZIP was extracted to a dedicated collection subfolder. All 228 files passed extraction checks: 227 JPGs and a handoff note retained locally. The ZIP was deleted after verification. Each image was new by SHA-256, and existing IDs were preserved.

Public copies remove JPEG metadata segments while retaining compressed image samples, color markers, and EXIF orientation. The metadata audit found no remaining requested identifying fields, and all 227 EXIF-oriented decoded RGB images match the extracted originals. Local source images remain unchanged.

## Source grouping hints

The incoming folder organization describes 118 burst-scene images, 41 AF-mode-switch comparison images, and 68 foliage-scene images. [submission-groups.jsonl](submission-groups.jsonl) preserves 14 anonymous parent-folder group hints. These are provenance hints rather than verified burst membership, obstruction labels, or focus-failure ground truth. Splits remain unassigned.

## Inputs and prelabels

The validated local CUDA pipeline uses the same Z8 resource744 body and original Z8 postprocessor as the first batch. Native class slots 0–5 remain unnamed. Predictions await human review; see [summary.json](../../experiments/community-prelabel-2026-10-24-batch02/summary.json) for counts and network times.

All **227/227** images completed with no execution errors: **180 with candidates, 47 without, 602 raw boxes**. GPU network time was **143.13 seconds**, excluding image I/O and postprocessing. E7 host decoding matched every saved Z8 candidate record in this batch.

The 384 × 256 PNGs are reconstructed from saved input buffers and pass byte-for-byte round-trip checks. Network input is `float32(u8) / 256`, CHW `[3, 256, 384]`. The [conversion code](../../scripts/z8_input.py) reproduces the EXIF-oriented RGB → bilinear resize → CHW conversion. The full camera sensor preprocessing is not established.

| Record | Purpose |
|---|---|
| [manifest.csv](manifest.csv) | This batch's original, public, and review hashes |
| [../registry.csv](../registry.csv) | Cumulative stable-ID register for future imports |
| [predictions.jsonl](predictions.jsonl) | Frozen model proposals, pending human review |
| [input-manifest.jsonl](input-manifest.jsonl) | Per-image saved input and PNG hashes |
| [input-validation.json](input-validation.json) | Saved-buffer and PNG checks |
| [metadata-validation.json](metadata-validation.json) | Public-copy metadata audit |
| [extraction-validation.json](extraction-validation.json) | Verified extraction and archive deletion |

## Rights

Photographs retain contributor copyrights. This release does not assign a blanket image license. No training or reviewed human labels are included.
