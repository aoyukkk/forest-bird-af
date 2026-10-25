# Community bird images: batch 05

**English** | [简体中文](README.zh-CN.md)

**60 new JPEG photographs**, IDs **fb_0635–fb_0694**. The cumulative register now contains **694 assets**. [Download v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5).

## Download and review

- Two `community-images-20261025-batch05-partNN-of02.zip` archives: original-resolution public copies and the batch manifest.
- `z8-inputs-384x256-20261025-batch05.zip`: 60 lossless 384×256 PNGs and exact saved CHW uint8 buffers.
- `z8-prelabels-review-20261025-batch05.zip`: proposals, overlays, previews and an English/Simplified Chinese review page.
- `manifest.csv`, cumulative `registry.csv` and `SHA256SUMS.txt`.

Extract both image archives and the review bundle into the same directory, open review.html, and export your decisions as JSON. This batch has an independent browser storage key.

## Import checks

All 60 RAR members were matched to extracted files by size and SHA-256 before the source archive was deleted. The initial verification included a directory record unsupported by bsdtar stdout extraction; selecting regular members resolved the error without rewriting extracted photos. All 60 assets are new source hashes. Existing IDs and original photos remain unchanged.

Identifying JPEG metadata was removed from separate public copies. Decoded RGB pixels match the source images for all 60 files. No NEF or RAW rendering was required.

## Z8 predictions

**60/60 completed, 0 inference errors**: **22 images with candidates, 38 without, 45 raw boxes**. GPU network time: **39.09 seconds**, excluding image I/O, overlays and CPU postprocessing. Fresh CUDA batch-size 64 fixtures passed bitwise checks; the network and decoder code match batch 04. Both decoders matched all 60 saved results.

Inputs use EXIF-oriented RGB, bilinear stretch to 384×256, CHW uint8 and float32(u8)/256 normalization. Saved-input hashes and PNG round trips all pass. Proposals are not human labels, and no candidates does not mean no bird.

Correct training examples can be accepted after checking the complete visible-part annotation; they need not be redrawn. Retain normal controls, correct errors and missing parts, and annotate independent test candidates without seeing model predictions.

## Records

[Manifest](manifest.csv) · [Register](../registry.csv) · [Predictions](predictions.jsonl) · [Input hashes](input-manifest.jsonl) · [Input checks](input-validation.json) · [Image checks](image-validation.json) · [Metadata checks](metadata-validation.json) · [Extraction checks](extraction-validation.json) · [Execution](../../experiments/community-prelabel-2026-10-25-batch05/summary.json).

Photographs retain contributor copyrights. Splits remain unassigned and training has not started.
