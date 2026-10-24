# forest-bird-af

**English** | [简体中文](README.zh-CN.md)

Bird autofocus in foliage, focused on missed birds and boxes that drift onto branches. The target is a visible eye, then the head, then the bird; release the target when none is usable.

## Progress

Updated: 2026-10-24.

| Work | Status |
|---|---|
| Community images | 570 files: 486 JPG, 7 PNG, 77 NEF |
| Image checks | Source hashes preserved; public-copy image checks passed with the representation recorded per batch |
| Simulation inputs | 570 lossless 384 × 256 RGB PNGs and exact saved CHW buffers |
| Z8 prelabeling | 570/570 completed on a local RTX 4080 Laptop GPU; 0 execution errors |
| Candidates | 1345 boxes across 415 images; 155 images have no candidates |
| Human review | Pending |
| Fine-tuning | Not started |
| Sony experiments | Paused |

The [latest release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3) adds **47 NEFs**, IDs **fb_0524–fb_0570**: 28 images with candidates, 19 without, 83 raw boxes. [Batch 03 details](data/community-2026-10-24-batch03/README.md).

## Download and review

| Batch | Images | Download |
|---|---:|---|
| First snapshot | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| Batch 02 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |
| Batch 03 | 47 | [v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3) |

Download all three batches for all 570 assets. Each release provides original-resolution public copies, fixed simulation inputs, and a review bundle. Verify downloads with `SHA256SUMS.txt`.

Extract a batch's image and review ZIPs into one directory and open `review.html`. The page defaults to English with a Simplified Chinese selector. For the first release, replace the bundled page with its separate `review.html`.

Batch 03 uses the NEFs' **camera-embedded JPEGs** for review and prediction. The rawpy path failed on 28 files; all 47 instead use the same explicit JPEG representation. Compressed image payloads in the public NEFs match their originals. These JPEGs are distinct from RAW sensor renders.

Review the whole image, starting with images without candidates. Export decisions as JSON; keep correct examples as controls and annotate errors in detail. Native slots 0–5 await semantic labels.

Use [data/registry.csv](data/registry.csv) for stable IDs. [Input conversion code](scripts/z8_input.py) and [workflow](docs/run-prelabel.md).

## Model and validation

The local Z8 resource744 body is byte-identical to [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network). The validated CUDA adapter retains the original local Z8 postprocessor.

- Physical-reference fixtures and real-image CPU/GPU comparisons passed bitwise checks.
- E7 host decoding matched all 570 saved Z8 candidate records across three batches.
- Batch 03 passed fresh CUDA batch validation. Its GPU network time was 30.40 seconds, excluding image I/O, postprocessing, and review.

See the [validation report](docs/reports/05-e7-comparison-and-cuda.md) and [latest execution records](experiments/community-prelabel-2026-10-24-batch03/).

## Next steps

- Review missed birds and incorrect boxes, then annotate visible eyes, heads, and birds.
- Group bursts, matching RAW/JPEG captures, and related images before freezing the test set.
- Fine-tune on corrected examples with normal-scene controls, then compare against the frozen original model.

## Documentation

| Topic | Link |
|---|---|
| Images, manifests, and checksums | [Community datasets](data/README.md) |
| Run inference and review results | [Prelabeling workflow](docs/run-prelabel.md) |
| Model identity and GPU checks | [Validation report](docs/reports/05-e7-comparison-and-cuda.md) |
| Dataset organization and annotation protocol | [Protocol v1, Chinese](docs/data/DATASET-SPEC-v1.md) |
| Firmware extraction and model-container format | [Extraction guide, Chinese](docs/format/UNPACK-GUIDE.md) |
| Contribution and publication rules | [AGENTS.md](AGENTS.md), [NOTICE.md](NOTICE.md) |

Earlier plans, the CUB calibration set, and failed runs remain in the repository for reference.

## Credits and licenses

Thanks to the contributing photographers, [WonderLantern](https://github.com/WonderLantern/e7-bird-network), [fwtool.py](https://github.com/ma1co/fwtool.py), and [TIM-VX](https://github.com/VeriSilicon/TIM-VX). See [acknowledgments](ACKNOWLEDGMENTS.md) for the full list.

Code: [Apache-2.0](LICENSE). Original documentation and metadata: CC BY 4.0. Photographs retain their contributors' copyrights; see the [dataset terms](data/community-2026-10-24/README.md#rights).
