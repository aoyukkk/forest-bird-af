# Input, hard-context and hybrid follow-up — 2026-10-26

**English** | [简体中文](input-context-2026-10-26.zh-CN.md)

The four local training trials completed. Hard-context augmentation did not
improve both sampling seeds. None of the saved new single-pass eye checkpoints
beat the previous n parent under the declared unmatched-eye budget. The parent
was retained. Native B/H plus the parent's full-image and four-tile eye outputs
reached 17/25 eye matches with3 unmatched proposals on development validation,
using5 n calls. This is a more expensive offline candidate policy, not an
independently tested camera improvement.

## Input diagnostic

Only the original80 community validation images were used. Historical80 test
images and the opened public200-source test were not scored on these new models.
The parent public results motivated the research direction; they are not fresh
evidence for this round. Source-detail references reproduced all80 frozen input
images exactly with EXIF RGB bilinear384×256 preparation.

Automatic regions use native proposals,1.5× context,3:2 aspect, minimum64px
width and a maximum of two regions. Four fixed240×160 windows cover the input.
Low/high variants crop identical regions from the frozen input or the source
reference. All views use batch1. Oracle regions use labels only for a separate
upper-bound diagnostic. The initial mixed-batch diagnostic is preserved locally;
it was repeated at batch1 to avoid batch-shape rounding confounds.

| View / policy | Eye TP / FP | Eye 2px hits | Bird TP / FP | Head TP / FP |
|---|---:|---:|---:|---:|
| native | 9 / 3 | 9 | 44 / 29 | 35 / 18 |
| full | 15 / 3 | 12 | 40 / 18 | 29 / 14 |
| auto_low | 8 / 1 | 8 | 30 / 12 | 13 / 21 |
| auto_high | 13 / 4 | 12 | 49 / 14 | 16 / 42 |
| tiles_low | 15 / 0 | 10 | 34 / 21 | 23 / 32 |
| tiles_high | 16 / 2 | 10 | 38 / 30 | 28 / 54 |
| oracle_high | 16 / 2 | 14 | 61 / 13 | 14 / 51 |
| hybrid_guarded | 8 / 0 | 8 | 44 / 29 | 35 / 18 |

High-detail crops recovered some eyes, but automatic cropping did not dominate
the full-image model. Low-detail tiles can improve the eye tradeoff without new
source pixels: scale/context sensitivity contributes alongside information loss.
Head candidates often worsened after cropping; do not treat crops as uniformly
better. The strict guarded hybrid requires two-scale agreement inside a native
head, achieving8/25 with0 unmatched, at a recall cost.

## Matched training

The same no-public-head pool, saved n initialization,4096 presentations/epoch,
batch32,40-epoch maximum,12-epoch patience, AdamW.0008 and expected50:50
community/public balance were used in both conditions. Seeds20261026/20261027
change sampling/augmentation, not the shared initial weights. Exact replay needs
the original saved initialization; its creation seed was not recorded previously.

Hard augmentation uses5,385 official CUB training masks with verified source
dimensions, plus200 protected-background crops from community training only.
Those crops inherit reviewed-frame coverage assumptions; they are **derived
supervision, not new human-confirmed absence**. No head/eye-only frame supplies
global background. Masked birds are resized to the community size distribution,
clamped16–128px, and composited with probability.7 on eligible CUB examples.
Texture-ribbon occlusion has probability.25. Covered, mask-excluded or too-small
eyes become unknown. These controlled composites have boundary/resampling
artifacts and do not reproduce real depth-dependent defocus.

A200-step pilot used2,510 composite presentations with finite gradients.
200 augmentation draws produced134 composites with valid geometry;48 were
visually inspected. The baseline's first19 loss values and B/H validation counts
matched its previous trajectory; this is not a complete tensor-parity claim.

Before training, selection prioritized eye hits under≤3 unmatched on the fixed
16-threshold grid, with B/H F1 floors.548947/.649612 (native validation minus.03).
Nonpassing runs retain an explicitly failed fallback. F1 floors do not guarantee
head/bird recall or correct AF fallback. The development target also required
at least16/25 eye hits; no complete replacement reached that target.

| Condition / seed | Epoch best / ran | Eye TP / FP | Bird F1 | Head F1 | F1 floors passed |
|---|---:|---:|---:|---:|---|
| baseline_20261026 | 7 / 19 | 4 / 0 | 55.70% | 66.67% | True |
| baseline_20261027 | 5 / 17 | 13 / 0 | 61.88% | 51.76% | False |
| hard_20261026 | 15 / 27 | 12 / 1 | 56.74% | 65.31% | True |
| hard_20261027 | 6 / 18 | 10 / 1 | 62.50% | 56.86% | False |

The hard recipe helped the first seed under this selection but hurt the second;
it is not a reproducible improvement across these two seeds. This small, reused,
Z8-assisted validation has only25 eyes and6 groups. No significance or real-event
generalization claim is supported.

## Eye-only secondary analysis and inference

After the initial diagnostic/baseline, a separate development amendment evaluated
only the four trials' saved best/last checkpoints and the old n parent. Native
B/H are fixed, so unused student B/H outputs do not gate this eye-only hypothesis.
This is post-diagnostic selection, not preregistration; unsaved epochs were not
recovered or claimed as optima. All9 candidates were assessed at batch1.

| Saved eye checkpoint | Eye TP / FP | Eye 2px hits | Target ≥16 TP / ≤3 FP |
|---|---:|---:|---|
| parent | 15 / 3 | 12 | False |
| baseline_20261026_best | 4 / 0 | 2 | False |
| baseline_20261026_last | 13 / 3 | 8 | False |
| baseline_20261027_best | 13 / 0 | 3 | False |
| baseline_20261027_last | 11 / 2 | 6 | False |
| hard_20261026_best | 12 / 1 | 5 | False |
| hard_20261026_last | 11 / 1 | 7 | False |
| hard_20261027_best | 10 / 1 | 1 | False |
| hard_20261027_last | 13 / 3 | 11 | False |

The parent remains the best saved single-pass eye candidate (15/25,3 unmatched).
Additional region combinations below are also development analyses at the
parent's fixed.8 eye threshold. Native B/H packets are retained without new NMS.
The merger suppresses only duplicate eye proposals.

| Native B/H + eye policy | Eye TP / FP | Eye-module calls |
|---|---:|---:|
| hybrid_full | 15 / 3 | 1 |
| hybrid_tiles_low | 15 / 0 | 4 |
| hybrid_full_tiles_low | 17 / 3 | 5 |
| hybrid_full_tiles_high | 18 / 4 | 5 |

The extra eye-module pipeline (warm PNG read, preprocessing, n model, custom
decode and merge; native forward excluded) measured P50/P95
44.96/65.78ms for1 call and
184.77/231.22ms for5 calls,
18 timings each. System-state variability and small samples limit these figures.
An earlier overlap timing is retained locally rather than used for the final
table. The complete native+n CLI passed a real input smoke check, preserving
native B/H exactly and matching cached eye coordinates within.25px. Its cold
native software replay is not the camera implementation or camera latency.

Four training loops totalled41.24 minutes,
excluding preparation, pilot and final analyses. The custom n still has2.456M
parameters /1.312 profiled conv-matmul GFLOPs per call. Using only its eye output
does not prune the unused branches. Five calls add about6.56 GFLOPs before the
native detector, with different native accounting; no NPU/frame-budget claim.

## Firmware and evidence boundary

Original ARM64 descriptor-ring execution passed2,889 synthetic checks:6 slots,
416-byte records, writer0x40fed500 and readers0x40fed60c/0x40fed6cc returning
descriptor offsets+8/+200. This closes part of a previously stubbed provider
chain. It does not establish the actual bird-744 ISP crop, colour planes,
request timing or pixel producer. Six cached descriptors are not a detection
frequency. The generic preparation API's default/255 differs from the pinned
training backend's/256; the generic default is not used by this training route,
so this is not evidence of a camera normalization defect.

The user confirmed no new submissions. The new real-event blind test and
temporal/lens validation remain pending data. See the
[independent-event protocol](../protocol/AF-EVENT-REVIEW-v1.md).
No additional distillation was run: the hard-data benefit was not stable, and
the region combination has not been calibrated as a stronger labelling teacher.

[Machine-readable aggregates](../../experiments/input-context-2026-10-26/summary.json)
include failed results and amendments, with no vendor binaries or photographs.
Source photographs, production labels and historical evidence are protected;
Sony, A800 and camera deployment remained paused.

Use `predict_bird_hybrid.py` with a local candidate, its calibration and your
verified native package. `full` makes1 eye-network call; `full-tiles` makes5.
Outputs are input-plane proposals plus a declared eye→head→bird selection
hypothesis, not recovered vendor target identity or lens control.

Mask source: [Caltech CUB segmentations](https://data.caltech.edu/records/w9d68-gec53),
Ryan Farrell; published MD5 verified. Original CUB research-use restrictions and
Ultralytics terms continue to apply. Masks and derived photographs stay local.


## Reproduce the declared recipe

Use your own external workspace and verified public data; freeze hashes before runs. Exact paired replay requires the saved initialization.

```text
python scripts/training/prepare_hard_bird_context.py --dataset ../work/parts-no-public-head.json --full-head-dataset ../work/parts-full.json --cub ../public/CUB_200_2011 --segmentations ../public/segmentations --output ../work/context
python scripts/training/train_bird_parts.py --dataset ../work/context/dataset.json --pretrained ../work/initialization --output ../work/baseline-20261026 --size n --epochs 40 --patience 12 --batch-size 32 --seed 20261026 --eye-fp-budget 3 --bird-f1-floor 0.5489473684210525 --head-f1-floor 0.6496116504854369
```

Repeat with `--hard-context` into a separate output and with seed20261027. Use `--help` for region/hybrid evaluators.

```text
python scripts/training/predict_bird_hybrid.py --image input.jpg --eye-weights ../work/candidate/eye.pt --calibration ../work/candidate/calibration.json --upstream ../private-native-package --output ../work/prediction.json
```


All recorded epochs were also inspected: best observed eye TP/FP under the budget were baseline seed1 15/3, baseline seed2 13/0, hard seed1 14/2 and hard seed2 13/3. None exceeded the parent's hit count. Some eye-optimal epochs were not retained as best/last; their metrics are logged, without claiming exported weights. Future component-specific training should retain its eye checkpoint separately.
