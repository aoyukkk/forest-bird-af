# forest-bird-af

**English** | [简体中文](README.zh-CN.md)

Bird autofocus in foliage, focused on missed birds and boxes that drift onto branches. The target is a visible eye, then the head, then the bird; release the target when none is usable.

## Progress

Updated: 2026-10-25.

| Work | Status |
|---|---|
| Community images | 694 files: 568 JPG, 7 PNG, 119 NEF |
| Image checks | Source hashes preserved; public-copy image checks passed with the representation recorded per batch |
| Simulation inputs | 694 lossless 384 × 256 RGB PNGs and exact saved CHW buffers |
| Z8 prelabeling | 694/694 completed on a local RTX 4080 Laptop GPU; 0 execution errors |
| Candidates | 1495 boxes across 469 images; 225 images have no candidates |
| Human review | 547 confirmed, 146 draft, 1 held for adjudication |
| Annotation tool | Local browser editor and shared human/AI API; [guide](docs/annotator.md) |
| Reviewed labels | 694 records published with the frozen eval split; [dataset](data/annotations-2026-10-25/README.md) |
| Head fine-tuning | Experiment candidate only: held-out macro F1 43.89% → 46.92%, eye precision fell; [results](docs/training/z8-native-head-finetune.md) |
| Sony experiments | Paused |

The [latest release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5) adds **60 JPEG photos**, IDs **fb_0635–fb_0694**: 22 with candidates, 38 without, 45 raw boxes. [Batch 05 details](data/community-2026-10-25-batch05/README.md).

## Download and review

Use the [Z8-assisted human review workspace](docs/z8-review.md) to inspect all frozen 384 × 256 inputs. Z8 boxes are visible by default. Explicit confirmation records accepted proposals or corrections, preserving every change and revision. Previous LLM labels remain in the historical precision editor.

| Batch | Images | Download |
|---|---:|---|
| First snapshot | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| Batch 02 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |
| Batch 03 | 47 | [v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3) |
| Batch 04 | 64 | [v0.4](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v4) |
| Batch 05 | 60 | [v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5) |

Download all five batches for all 694 assets. Each release provides original-resolution public copies, fixed simulation inputs, and a review bundle. Verify downloads with `SHA256SUMS.txt`.

Extract a batch's image and review ZIPs into one directory and open `review.html`. The page defaults to English with a Simplified Chinese selector. For the first release, replace the bundled page with its separate `review.html`.

Batch 03 uses the NEFs' **camera-embedded JPEGs** for review and prediction. The rawpy path failed on 28 files; all 47 instead use the same explicit JPEG representation. Compressed image payloads in the public NEFs match their originals. These JPEGs are distinct from RAW sensor renders.

Review the whole image, starting with images without candidates. Export decisions as JSON; keep correct examples as controls and annotate errors in detail. Native slots 0–5 await semantic labels.

Use [data/registry.csv](data/registry.csv) for stable IDs. [Input conversion code](scripts/z8_input.py) and [workflow](docs/run-prelabel.md).

## Published results

Everything in the repository can be checked offline:

| Artifact | What it is |
|---|---|
| [Human-confirmed labels](data/annotations-2026-10-25/confirmed/README.md) | **All 547 confirmed images** in JSONL, CSV, COCO and YOLO |
| [Reviewed labels](data/annotations-2026-10-25/labels/community-corrections-v1.jsonl) | 694 per-image records, including drafts, with frozen vendor candidate counts |
| [Evaluation split](data/annotations-2026-10-25/evaluation-split-v1.json) | 375 / 80 / 80 train-val-test assignment with leakage groups, frozen before training |
| [Dedupe queue](data/annotations-2026-10-25/dedupe-queue-v1.json) | 536 in queue, 158 folded, 42 similarity groups |
| [Best images](data/annotations-2026-10-25/best-images-v1.json) | 120-image first-look ordering; a review aid, not the label set |
| [Toolchain](data/annotations-2026-10-25/TOOLCHAIN.md) | Annotation service, importer, dedupe, COCO/YOLO export |
| [Training results](docs/training/z8-native-head-finetune.md) | Native head fine-tune: method, held-out metrics, compute, publication boundary |

```bash
python scripts/verify_annotations.py                 # labels, confirmed export, coordinates, splits, queue
python -m unittest tests.test_published_exports tests.test_curation_exports tests.test_confirmed_export -v
python scripts/verify_repo.py                        # no vendor assets or photos in the tree
```

The candidate weight itself is **not** distributed: nearly every byte of it is
vendor weight. What ships is its SHA-256, the changed-byte range and the scripts
to rebuild it from your own verified package. See [what is not
published](docs/releases/not-published.md).

## Model and validation

The local Z8 resource744 body is byte-identical to [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network). The validated CUDA adapter retains the original local Z8 postprocessor.

- Physical-reference fixtures and real-image CPU/GPU comparisons passed bitwise checks.
- E7 host decoding matched all 694 saved Z8 candidate records across five batches.
- Batch 03 passed fresh CUDA batch validation. Its GPU network time was 30.40 seconds, excluding image I/O, postprocessing, and review.

Batch 04 used the same validated batch configuration: 42.59 seconds of GPU network time. Its 42 NEFs use embedded JPEGs; its 22 JPGs retain the source decoded pixels.

Batch 05 passed fresh CUDA batch validation: 60 JPEGs, 39.09 seconds of GPU network time, and matching host/native decoder results.

See the [validation report](docs/reports/05-e7-comparison-and-cuda.md) and [latest execution records](experiments/community-prelabel-2026-10-25-batch05/).

## Next steps

- Cut eye false positives at unmatched locations; the validation misses sit 8.1–11.2 px from the labelled eye and inside the current background guard.
- Confirm the remaining draft images and adjudicate `fb_0588`, then refresh the published label snapshot.
- Grow the number of independent leakage groups before treating held-out gains as stable.
- Keep phase detection, lens drive and the whole-camera AF loop out of any accuracy claim.

## Documentation

| Topic | Link |
|---|---|
| Images, manifests, and checksums | [Community datasets](data/README.md) |
| Reviewed labels and evaluation split | [Annotations 2026-10-25](data/annotations-2026-10-25/README.md) |
| Annotation toolchain and export formats | [Toolchain](data/annotations-2026-10-25/TOOLCHAIN.md) |
| Best images and the deduplicated queue | [Curation](data/annotations-2026-10-25/CURATION.md) |
| Head fine-tuning results | [Native head fine-tune](docs/training/z8-native-head-finetune.md) |
| Publication boundary | [Not published](docs/releases/not-published.md) |
| Run inference and review results | [Prelabeling workflow](docs/run-prelabel.md) |
| Model identity and GPU checks | [Validation report](docs/reports/05-e7-comparison-and-cuda.md) |
| Dataset organization and annotation protocol | [Protocol v1, Chinese](docs/data/DATASET-SPEC-v1.md) |
| Firmware extraction and model-container format | [Extraction guide, Chinese](docs/format/UNPACK-GUIDE.md) |
| Contribution and publication rules | [AGENTS.md](AGENTS.md), [NOTICE.md](NOTICE.md) |

Earlier plans, the CUB calibration set, and failed runs remain in the repository for reference.

## Credits and licenses

Thanks to the contributing photographers, [WonderLantern](https://github.com/WonderLantern/e7-bird-network), [fwtool.py](https://github.com/ma1co/fwtool.py), and [TIM-VX](https://github.com/VeriSilicon/TIM-VX). See [acknowledgments](ACKNOWLEDGMENTS.md) for the full list.

Code: [Apache-2.0](LICENSE). Original documentation and metadata: CC BY 4.0. Photographs retain their contributors' copyrights; see the [dataset terms](data/community-2026-10-24/README.md#rights).
