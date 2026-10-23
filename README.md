# forest-bird-af

**English** | [简体中文](README.zh-CN.md)

Bird autofocus in foliage, with a focus on missed birds and boxes that drift onto branches. The target behavior is to use a visible eye, fall back to the head, then the bird, and release the target when none is usable.

## Progress

Updated: 2026-10-24.

| Work | Status |
|---|---|
| Community images | 296 files: 259 JPG, 7 PNG, 30 NEF |
| Image checks | All 296 originals preserved; public-copy pixel and RAW-sample checks passed |
| Simulation input dataset | 296 lossless RGB PNGs at 384 × 256, with the exact saved CHW input buffers |
| Z8 prelabeling | 296/296 completed on a local RTX 4080 Laptop GPU; 0 execution errors |
| Candidates | 660 boxes across 207 images; 89 images have no candidates |
| Human review | Ready to begin |
| Fine-tuning | Not started |
| Sony experiments | Paused |

The image and review bundles are available in [Releases](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1). [Dataset details](data/community-2026-10-24/README.md).

For reproducible model comparisons, download `z8-inputs-384x256-20261024.zip` from the same release. Its PNG pixels reproduce all 296 saved simulation inputs exactly. Original-resolution images remain in the four community image archives. [Input format and conversion code](data/community-2026-10-24/README.md#simulation-input-dataset).

## Download and review

1. Download the four `community-images-20261024-partXX-of04.zip` files and `SHA256SUMS.txt` from the release. Extract them into one directory to merge `images/`.
2. Extract `z8-prelabels-review-20261024.zip` there, then copy the release's separate `review.html` into that directory, replacing the bundled page. It opens in English and includes a 简体中文 selector.
3. Review the whole image, starting with the 89 images without candidates. Mark boxes as correct, needing correction, or uncertain.
4. Export the review decisions as JSON. Keep correct examples as controls and send errors for detailed annotation.

The review page supports image/overlay switching, filters, notes, and decision export. Decisions are stored in the browser until exported. Use the full-resolution images for eye and head annotation.

Current boxes retain the model's native slots 0-5. Mapping those slots to eye, head, and bird remains part of the annotation work.

## Model and validation

The Z8 resource744 model body is byte-identical to [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network). We use its numerical profile with a validated CUDA adapter and retain the local Z8 factory postprocessor.

- Public physical-reference fixtures and a real-image CPU/GPU comparison passed bitwise checks.
- Both decoders produced identical candidate records on this batch of 296 images.
- The five GPU network batches took 185.95 seconds in total. This excludes image I/O, postprocessing, and review.

See the [comparison and validation report](docs/reports/05-e7-comparison-and-cuda.md) and [execution records](experiments/community-prelabel-2026-10-24/).

## Next steps

- Review missed birds and incorrect boxes, then annotate visible eyes, heads, and birds.
- Group bursts, matching RAW/JPEG captures, and related images before freezing the test set.
- Fine-tune on corrected examples with normal-scene controls, then compare against the frozen original model.

## Documentation

| Topic | Link |
|---|---|
| Images, manifests, and checksums | [Community dataset](data/community-2026-10-24/README.md) |
| Run inference and review results | [Prelabeling workflow](docs/run-prelabel.md) |
| Model identity and GPU checks | [Validation report](docs/reports/05-e7-comparison-and-cuda.md) |
| Dataset organization and annotation protocol | [Protocol v1, Chinese](docs/data/DATASET-SPEC-v1.md) |
| Firmware extraction and model-container format | [Extraction guide, Chinese](docs/format/UNPACK-GUIDE.md) |
| Contribution and publication rules | [AGENTS.md](AGENTS.md), [NOTICE.md](NOTICE.md) |

Earlier plans, the CUB calibration set, and failed runs remain in the repository for reference.

## Credits and licenses

Thanks to the contributing photographers, [WonderLantern](https://github.com/WonderLantern/e7-bird-network), [fwtool.py](https://github.com/ma1co/fwtool.py), and [TIM-VX](https://github.com/VeriSilicon/TIM-VX). See [acknowledgments](ACKNOWLEDGMENTS.md) for the full list.

Code: [Apache-2.0](LICENSE). Original documentation and metadata: CC BY 4.0. Photographs retain their contributors' copyrights; see the [dataset terms](data/community-2026-10-24/README.md#rights).
