# Community bird images: 2026-10-24

**English** | [简体中文](README.zh-CN.md)

296 files: **259 JPG, 7 PNG, and 30 NEF**. IDs `fb_0001` through `fb_0292` retain the earlier register; four new assets extend it to `fb_0296`.

## Download

Open the [release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1). Download all four `community-images-20261024-partXX-of04.zip` files, then extract them into the same directory to merge `images/`. Each ZIP can be opened independently.

| File | Contents |
|---|---|
| [manifest.csv](manifest.csv) | IDs, image dimensions, original/public hashes, and review-image hashes |
| [packages.json](packages.json) | Archive sizes, image counts, and SHA-256 checksums |
| [predictions.jsonl](predictions.jsonl) | Per-image raw-class proposals, pending review |
| [review-bundle.json](review-bundle.json) | Review archive size and checksum |

The release also includes `SHA256SUMS.txt`, the review bundle, and a separate bilingual `review.html`. Replace the bundled page with this newer file for English by default and a Simplified Chinese option. See the [review workflow](../../docs/run-prelabel.md).

## Image preparation

Originals stay local and unchanged. Public copies have the specified GPS, serial-number, owner, host, comment, and XMP fields removed with ExifTool 13.59.

All JPEG/PNG decoded pixels and all 30 NEF sensor arrays match their originals. Cleaning changes file bytes, so the manifest records both original and public SHA-256 hashes.

NEF review JPEGs use rawpy 0.25.1, AHD, camera white balance, sRGB 8-bit, no auto-brightening, and JPEG quality 98 with no chroma subsampling. The review bundle includes these full-resolution renders; image archives retain the NEF files.

## Simulation input dataset

Download `z8-inputs-384x256-20261024.zip` from the same release. It contains:

- `input-png/`: 296 lossless RGB PNGs, each **384 × 256 pixels** (98,304 pixels).
- `input-chw-u8/`: the 296 preserved input buffers, each 294,912 bytes, in CHW order `[3, 256, 384]`.
- `input-manifest.jsonl`: stable IDs, dimensions, and hashes linking inputs to original, public, and review images.
- `input-validation.json`: all saved input hashes and PNG pixel round-trips passed.

The PNGs were reconstructed from the saved buffers, without another inference run or image resize. Rearranging their decoded RGB pixels to CHW reproduces the recorded `input_sha256` for every image. PNG file hashes differ from input-buffer hashes.

The network receives `float32(u8) / 256`. These are the exact inputs used by this simulation run; the complete in-camera sensor-to-network preprocessing has not been established. Keep original-resolution images for detailed eye/head annotation and use these fixed inputs for model comparisons. Labels remain pending human review.

The conversion is implemented in [z8_input.py](../../scripts/z8_input.py): apply EXIF orientation, convert to RGB, stretch to 384 × 256 using Pillow bilinear interpolation, then store R, G, B planes. NEF first uses the fixed review JPEG described above. To reproduce one input from its review image:

```powershell
python scripts/z8_input.py path/to/review-image.jpg --output input-check --expected-sha256 INPUT_SHA256
```

Use the `input_chw_u8_sha256` from [input-manifest.jsonl](input-manifest.jsonl). Exact reproduction depends on the review image and the Pillow version recorded in [input-validation.json](input-validation.json). The publisher is [package_z8_inputs.py](../../scripts/package_z8_inputs.py).

## Prelabel results

All 296 files completed inference: **207 images with candidates, 89 without, 660 candidate boxes**. Proposals retain native class slots 0–5. Human review and data splitting are pending.

The [validation report](../../docs/reports/05-e7-comparison-and-cuda.md) describes the E7 numerical profile, CUDA checks, and retained Z8 postprocessor.

## Rights

Photographs retain their contributors' copyrights. This release does not assign a blanket CC BY, CC0, or commercial-use license to the images. Contact the rights holders for uses beyond the permissions already granted.
