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

## Prelabels

All 296 files completed inference: **207 images with candidates, 89 without, 660 candidate boxes**. Proposals retain native class slots 0–5. Human review and data splitting are pending.

The [validation report](../../docs/reports/05-e7-comparison-and-cuda.md) describes the E7 numerical profile, CUDA checks, and retained Z8 postprocessor.

## Rights

Photographs retain their contributors' copyrights. This release does not assign a blanket CC BY, CC0, or commercial-use license to the images. Contact the rights holders for uses beyond the permissions already granted.
