# forest-bird-af

**English** | [简体中文](README.zh-CN.md)

Bird detection in foliage for autofocus research: **visible eye → head → bird**.
Community photographs, human-reviewed labels, native Z8 head training and
independent YOLO26-derived bird-parts experiments. Whole-camera autofocus has not been verified.

**694 image assets · 547 confirmed records · 535 deduplicated usable records**

Updated: **2026-10-27**.

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
| Training | Native, n/s, surface, RGB-verifier and empty-scene trials completed; no replacement recommended |

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
Training needs NumPy and compatible CUDA PyTorch; the native route also needs
your own verified vendor package. The independent YOLO route uses public data. See [training](docs/training/README.md) and
[tests](tests/README.md). Firmware, original/modified vendor weights, feature
caches and the production database are not distributed.

## Public expansion and empty scenes — 2026-10-27

17,252 additional public research images passed conservative admission; 158
were isolated with originals retained. Four verifier runs completed 32 epochs
each. Empty-scene supervision improves internal calibration, but complete
inference exposes existing primary false selections and a harmful rejection
tradeoff. Defaults stay unchanged. The A12 entry audit admits no teacher or
pseudolabels. [Data, results and scope](experiments/expansion-2026-10-27/README.md).

## Capacity and real hard negatives — 2026-10-27

Two RGB/context verifier sizes were compared over six 8-epoch and six 32-epoch
runs, retaining the frozen n parent. Larger capacity did not establish useful
improvement on the stronger primary policy's remaining cases. A fit-side
40-image / 80-point review queue is prepared, with no new confirmed labels.
Default inference and original annotations are retained.
[Results, timing and diagnosis](experiments/residual-2026-10-27/README.md).

## Frozen surface branch — 2026-10-27

Four matched runs completed 32 epochs with a 6,945-parameter shared-feature
head. Synthetic occluder errors decreased on CUB development views, but real
residual cases still selected vegetation and the sole confirmed no-bird frame.
P95 overhead was 3.8% for the single-n path and 6.3% for two n models, measured
over 500 repetitions. Original outputs and annotations were preserved;
**no replacement is recommended**. [Results and limits](experiments/surface-2026-10-27/README.md).

## Point-availability review — 2026-10-26

Human review is complete for 51 previously unassessed capture points:
**44 usable coarse cues and 7 unusable points**. Original AI drafts and the
validated human export are kept separately. Low-threshold empty-target fallback
still adds too many bad points; a .7 cutoff adds only one usable point per
primary policy on reused validation data. No default change or new training.
[Findings and offline review tools](docs/training/point-review-2026-10-26.md).

## Selected focus-cue follow-up — 2026-10-26

Six matched continuations completed 48 epochs in 27.49 minutes. Fine-guidance
selection retained the parent. A two-n B/H-and-eye combination improved
geometric support from 62/80 to 68/80 while retaining 15/25 selected-eye hits.
The old/new coarse acquisition references scored 71/80 and 70/80, with different
fine-eye errors and many unassessed eye selections. These are development
geometry proxies; visible surface, depth and camera focus remain unverified.
[Results, runtime and diagnostics](docs/training/guidance-2026-10-26.md).

## Input/context follow-up — 2026-10-26

Four additional matched trials (baseline/hard context, two sampling seeds)
completed. The new training did not surpass the retained single-pass n eye
parent. The hard recipe improved one seed and regressed on the other.

| Community development validation, 25 eye labels | Eye hits / unmatched | Extra n calls |
|---|---:|---:|
| Native | 9 / 3 | 0 |
| Native B/H + parent n eyes | 15 / 3 | 1 |
| Native B/H + parent n full/four-tile eyes | 17 / 3 | 5 |

This is reused, Z8-assisted validation; the region combination is a development
candidate with extra cost. No new real-event test is available, and no camera
replacement is recommended. [Results, input audit and limitations](docs/training/input-context-2026-10-26.md).

## Latest comparison — 2026-10-26

The selected YOLO26n-derived model improves eye localization on the locked
original-size public images. On matched small-target images its bird-box
recall drops below the native detector. **No camera replacement is recommended.**

| Public view | Model | Bird hits / 200 | Eye hits | Unmatched eye proposals |
|---|---|---:|---:|---:|
| Original | Native | 65 | 150/201 | 23 |
| Original | n candidate | 193 | 160/201 | 19 |
| Small-target paired view | Native | 117 | 40/179 | 16 |
| Small-target paired view | n candidate | 64 | 48/179 | 13 |

Boxes use IoU .5; eyes use 4 input pixels. Thresholds were fixed on community
validation. The two views share 200 CUB sources; they are not new real forest
captures. Native original-view bird hits rise to 183/200 at IoU .3, so strict
unmatched boxes cannot be read as background focus locks. Overall community
validation F1 still favours the native candidate; sparse distillation retained
its n parent. [Full comparison, compute and limitations](docs/training/next-round-2026-10-26.md)
· [Implementation](docs/training/yolo26-parts.md).

## Historical first-round test

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
