# Community bird images: batch 04

**English** | [简体中文](README.zh-CN.md)

**64 new photos: 42 NEFs and 22 JPGs**, IDs **fb_0571–fb_0634**. The register now contains **634 assets**. [Download v0.4](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v4).

## Download and review

- Two `community-images-20261024-batch04-partNN-of02.zip` archives: original-resolution public copies and the batch manifest.
- `z8-inputs-384x256-20261024-batch04.zip`: 64 lossless 384 × 256 PNGs and exact saved CHW uint8 inputs.
- `z8-prelabels-review-20261024-batch04.zip`: proposals, overlays, previews, full-size NEF review JPEGs, and English/Simplified Chinese `review.html`.
- `manifest.csv`, cumulative `registry.csv`, and `SHA256SUMS.txt`.

Extract the image archives and review bundle into the same directory and open `review.html`. Export decisions as JSON; batch 04 has its own storage key.

## Import and image checks

All **67 received files** passed extraction and SHA-256 checks before the source ZIP was deleted. **64 are photographs**; three macOS auxiliary files remain local. One AppleDouble resource fork has a `.NEF` suffix; its file signature identifies it as metadata, so it is excluded before ID assignment. The earlier private snapshot was not committed. Existing registered IDs remain unchanged.

Public JPEG copies preserve source decoded pixels. The 42 NEFs use **JpgFromRaw camera-embedded JPEGs**, explicitly continuing the representation selected for batch 03. No rawpy attempt is claimed for this batch. Every populated TIFF image payload in the public NEFs matches the original compressed bytes; embedded review JPEGs preserve decoded pixels. Identifying metadata is removed and the Nikon serial field is constant 0. Original photos remain unchanged.

## Z8 predictions

**64/64 completed, 0 execution errors**: **32 with candidates, 32 without, 105 raw boxes**. GPU network time: **42.59 s**, excluding I/O and postprocessing. Both decoders matched all 64 saved records. The CUDA batch-size 64 validation from the same import session is reused with unchanged network and decoder scripts.

EXIF-oriented review images are converted to RGB, bilinearly stretched to 384 × 256, arranged as CHW uint8, and normalized by `/256`. All preserved input hashes and PNG round trips pass.

## Records

[Manifest](manifest.csv) · [Register](../registry.csv) · [Predictions](predictions.jsonl) · [Input hashes](input-manifest.jsonl) · [Input checks](input-validation.json) · [Image checks](image-validation.json) · [Metadata checks](metadata-validation.json) · [Extraction checks](extraction-validation.json) · [Execution](../../experiments/community-prelabel-2026-10-24-batch04/summary.json).

Photographs retain contributor copyrights. Predictions await human review; splits remain unassigned and no training was started.
