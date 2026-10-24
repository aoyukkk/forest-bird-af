# Community bird images: batch 03

**English** | [简体中文](README.zh-CN.md)

**47 new NEFs**, IDs **fb_0524–fb_0570**; **570 assets** in the cumulative register. [Download v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3). Earlier releases remain frozen.

## Files and review

- `community-images-20261024-batch03-part01-of01.zip`: 47 original-resolution public NEF copies.
- `z8-inputs-384x256-20261024-batch03.zip`: 47 lossless RGB PNGs and exact saved CHW uint8 buffers.
- `z8-prelabels-review-20261024-batch03.zip`: overlays, previews, the 47 fixed full-size embedded JPEG review images, predictions, and bilingual `review.html`.
- `manifest.csv`, cumulative `registry.csv`, and `SHA256SUMS.txt`.

Open `review.html` from the review bundle. Its full-size JPEGs are in `raw-review/`; the English/Simplified Chinese page has a separate storage key for batch 03. Export decisions as JSON.

## Image representation and checks

All 47 received files passed extraction and SHA-256 checks before the source ZIP was deleted. No original photo was changed. Public NEFs remove requested identifying metadata; their Nikon serial field uses constant 0. Every populated TIFF strip, tile, and JPEG image payload matches its original byte for byte.

The RAW files include 27 `High Efficiency*` and 20 lossless-compressed files. The default rawpy path failed on 28 files. The new snapshot explicitly uses **JpgFromRaw camera-embedded JPEGs for all 47**, with decoded pixels unchanged after JPEG metadata cleaning. The failed gate remains in [parent-rawpy-validation.json](../../experiments/community-prelabel-2026-10-24-batch03/parent-rawpy-validation.json). This batch does not claim decoded RAW sensor-sample checks. The [review-mode amendment](../../experiments/community-prelabel-2026-10-24-batch03/review-mode-amendment.json) records the change.

## Z8 prediction

**47/47 completed**, 0 execution errors: **28 with candidates, 19 without, 83 raw boxes**. GPU network time: **30.40 s**, excluding I/O and postprocessing. Fresh CUDA batch validation passed and both decoders matched all 47 saved records. Native slots 0–5 await human review and semantic mapping.

Input: EXIF-oriented review JPEG → RGB → Pillow bilinear stretch to 384 × 256 → CHW uint8 → `float32(u8) / 256`. PNG round trips and all saved input hashes passed. [Conversion](../../scripts/z8_input.py).

## Records

[Manifest](manifest.csv) · [Cumulative register](../registry.csv) · [Predictions](predictions.jsonl) · [Input manifest](input-manifest.jsonl) · [Input checks](input-validation.json) · [Image checks](image-validation.json) · [Metadata checks](metadata-validation.json) · [Extraction checks](extraction-validation.json) · [Execution](../../experiments/community-prelabel-2026-10-24-batch03/summary.json).

Photographers retain their copyrights. Predictions are pending review; splits are unassigned. No training was started.
