# forest-bird-af

**English** | [简体中文](README.zh-CN.md)

Bird detection in foliage for autofocus research: **visible eye → head → bird**.
Community photographs, human-reviewed labels and a native Z8 head-training
pipeline. Whole-camera autofocus has not been verified.

**694 image assets · 547 confirmed records · 535 deduplicated usable records**

Updated: **2026-10-26**.

## Start here

| I want to… | Open |
|---|---|
| Download photographs or exact 384×256 inputs | [Image downloads](data/README.md#image-downloads) |
| Use the complete confirmed labels | [Labels and formats](data/annotations-2026-10-25/README.md) |
| Reproduce or improve the native detector | [Training code and prerequisites](docs/training/README.md) |
| Review or correct annotations | [Local review tool](docs/tools/z8-review.md) |
| Find another document or script | [Documentation](docs/INDEX.md) · [Scripts](scripts/README.md) |

## What is ready

| Artifact | Current state |
|---|---|
| Images | Five published Releases: 568 JPG, 7 PNG, 119 NEF; image files stay outside Git |
| Model inputs | 694 frozen RGB PNGs plus exact CHW buffers and hashes |
| Confirmed labels | 547 records; original points, boxes, IDs and auxiliary items retained |
| Deduplicated queue | 535 confirmed usable images and **1 adjudication item** (`fb_0588`) |
| Archived duplicates | 12 confirmed and 146 draft records retained; these drafts are not a new annotation backlog |
| Evaluation split | 375 train / 80 validation / 80 test, grouped before training |
| Training | Five initial configurations and four refinements; experimental candidate only |

The [694-record snapshot](data/annotations-2026-10-25/labels/community-corrections-v1.jsonl)
also includes drafts and the adjudication item. **Unconfirmed records are not
negatives.** The [120-image ranking](data/annotations-2026-10-25/docs/CURATION.md)
is a browsing aid, not the complete label set or a test set.

## Use the labels correctly

- [confirmed.jsonl](data/annotations-2026-10-25/confirmed/confirmed.jsonl)
  preserves full geometry on the frozen **384×256 input**.
- Eyes remain points unless their boundaries were actually boxed. COCO/YOLO
  views contain **1,041 source boxes** and keep **160 point-only eyes separately**;
  no fixed-size eye boxes are invented. See [formats](data/annotations-2026-10-25/confirmed/README.md).
- COCO/YOLO are **partial box views**, not complete standalone BHE training
  targets. A missing eye box is unknown, not background.
- Review was assisted by visible Z8 proposals, not independently blinded.
  Multi-bird part association is not established.

## Check a checkout

These checks need Python 3.11+ and the standard library, without a GPU, photos
or vendor package:

```bash
git clone https://github.com/aoyukkk/forest-bird-af.git
cd forest-bird-af
python scripts/tools/verify_annotations.py
python scripts/tools/verify_links.py
python scripts/tools/verify_repo.py
```

For the annotation UI, install [requirements-annotator.txt](requirements-annotator.txt).
Training additionally needs NumPy, a compatible CUDA PyTorch installation and
your own verified vendor package; see [training](docs/training/README.md) and
[tests](tests/README.md). Firmware, original/modified vendor weights, feature
caches and the production database are not distributed.

## Results so far

One candidate was selected on validation and tested once on 80 held-out images.
Strict criteria: bird/head IoU ≥0.5; eye-center error ≤4 input pixels.

| Test metric | Original | Candidate |
|---|---:|---:|
| Macro F1 | 43.89% | 46.92% |
| Eye hits / labels | 4/22 | 6/22 |
| Eye unmatched-location false positives | 1 | 3 |
| Eye precision | 80.00% | 66.67% |

**More eyes were found, with more false eye detections. The candidate is not
recommended as a replacement for the vendor model.** Four further refinements
retained the parent weights. The test has only five conservative groups, 58
images share one group, and eye precision is evaluated where that part was
labelled. This is neither camera focus rate nor tracking performance. The used
test split is preserved for reproduction, not as a fresh test for further tuning.

[Full method, results and compute](docs/training/z8-native-head-finetune.md) ·
[Model/parity evidence](docs/reports/05-e7-comparison-and-cuda.md) ·
[Publication boundaries](docs/releases/not-published.md)

## Repository map

| Directory | Purpose |
|---|---|
| [data/](data/README.md) | Downloads, stable IDs, labels, curation and splits |
| [scripts/](scripts/README.md) | Pipeline, annotator, training, publishing and checks |
| [src/forest_bird_annotator/](src/forest_bird_annotator/README.md) | Annotation service and browser UI |
| [docs/](docs/INDEX.md) | Current guides, results and separate historical research |
| [experiments/](experiments/README.md) | Frozen run records and source-relocation notes |
| [tests/](tests/README.md) | Unit tests and published-data contracts |

## Credits and licenses

Code: [Apache-2.0](LICENSE). Original documentation and metadata: CC BY 4.0.
Photographs retain contributor copyrights; see [photo terms](data/community-2026-10-24/README.md#rights).
Thanks to the photographers and upstream projects in [Acknowledgments](ACKNOWLEDGMENTS.md).
