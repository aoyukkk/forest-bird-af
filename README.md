# forest-bird-af

**English** | [简体中文](README.zh-CN.md)

Bird autofocus in foliage, with a focus on missed birds and boxes that drift onto branches. The target behavior is to use a visible eye, fall back to the head, then the bird, and release the target when none is usable.

## Progress

Updated: 2026-10-24.

| Work | Status |
|---|---|
| Community images | 523 files: 486 JPG, 7 PNG, 30 NEF |
| Image checks | All 523 registered originals preserved; public-copy pixel and RAW-sample checks passed |
| Simulation input dataset | 523 lossless RGB PNGs at 384 × 256 across two releases, with saved CHW input buffers |
| Z8 prelabeling | 523/523 completed across two batches on a local RTX 4080 Laptop GPU; 0 execution errors |
| Candidates | 1262 boxes across 387 images; 136 images have no candidates |
| Human review | Ready to begin |
| Fine-tuning | Not started |
| Sony experiments | Paused |

The [latest release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) adds **227 JPGs**, IDs fb_0297–fb_0523. GPU prelabeling found 602 raw candidates across 180 images; 47 images have no candidates. The first 296-image release remains unchanged. [Latest batch details](data/community-2026-10-24-batch02/README.md).

## Download and review

| Batch | Images | Download |
|---|---:|---|
| First snapshot | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| Batch 02 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |

Each release includes original-resolution public copies, fixed 384 × 256 simulation inputs, and a review bundle. Download both batches for all 523 images; new downloads contain only the additional 227. Check ZIPs against each release's checksum file.

For batch 02, extract its image and review ZIPs into one directory and open `review.html`. The page defaults to English with a Simplified Chinese selector. For v0.1, also replace the bundled page with that release's separate `review.html`.

Review the whole image, starting with images without candidates. Export decisions as JSON, keep correct examples as controls, and send errors for detailed annotation. Use full-resolution images for eye and head annotation. Native slots 0–5 still need semantic labels.

Use [data/registry.csv](data/registry.csv) for the complete stable-ID register. [Input format and conversion code](data/community-2026-10-24/README.md#simulation-input-dataset).

## Model and validation

The Z8 resource744 model body is byte-identical to [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network). We use its numerical profile with a validated CUDA adapter and retain the local Z8 factory postprocessor.

- Public physical-reference fixtures and a real-image CPU/GPU comparison passed bitwise checks.
- E7 host decoding matched the saved original-Z8 candidate records on all 523 images across both batches.
- GPU network time was 185.95 seconds for the first 296 images and 143.13 seconds for the new 227. This excludes image I/O, postprocessing, and review.

See the [comparison and validation report](docs/reports/05-e7-comparison-and-cuda.md) and [latest execution records](experiments/community-prelabel-2026-10-24-batch02/).

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
