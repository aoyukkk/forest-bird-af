# Public expansion and empty-scene results

**English** | [简体中文](README.zh-CN.md)

**Data expansion and four new runs completed; retain the current primary policy.** The new empty-scene recipe improves internal anchor retention under the same false-selection budget, but produces no useful extra community selections. [Protocol and commands](../../docs/training/data-expansion-2026-10-27.md).

## Data and teacher admission

| Newly admitted source | Fit-side images | Internal calibration images |
|---|---:|---:|
| NABirds | 12,855 | 1,403 |
| COCO bird masks | 1,899 | 245 |
| CCT explicit empty | 678 | 172 |

17,252 newcomers are admitted and 158 isolated, with all originals retained. 16,399 reference input identities are used for conservative contamination signatures only. NABirds eyes are positive-only; no new head boxes are invented. Images without usable eye/mask supervision do not generate fit frames. Source rights remain with their respective datasets; photos are not republished here.

The A12 teacher is **not admitted**. Eleven SDK libraries and seven model files match locks, but the live photo-to-box entry is Z8. The completed genuine local Sony example is a zero-input re-identification embedding, with neither verified detector image preprocessing nor a verified B/H/eye decoder. The Windows wrapper copies raw input file bytes despite a broader docstring. New A12 pseudolabels: **zero**. No new Sony process, system virtualization change or remote job was started.

## Matched classifier results

Two seeds per recipe, 32 epochs, 4,096 cached frame-pair presentations per epoch, same 808,417-parameter verifier and frozen n parent. The empty recipe replaces 30% of negative counterparts with CCT; its first-point/image sequence matches the positive-only recipe. All 32 old baseline checkpoints per seed receive the same expanded calibration selection opportunities. Four new runs total 128 cache epochs in 6.94 minutes including process loading; baseline scoring takes 1.76 minutes. This is not full-backbone training.

Mask columns are foreground / known wrong / unknown / abstain over 2,045 internal CUB/COCO views. Real anchors are from the 41-image internal verifier calibration, previously seen by the parent. NABirds anchors are diagnostic, not inference detection recall. CCT calibration covers 15 camera locations, and the views/frames are correlated. These are not new real-forest test results.

| Recipe and seed | Best epoch | Threshold | Real anchors | Empty false frames | Mask F/W/U/A | NABirds anchors |
|---|---:|---:|---:|---:|---|---:|
| baseline_20261027 | 28 | 0.9995 | 13/23 | 1/172 | 538/0/19/1488 | 377/1458 |
| positive_20261027 | 4 | 0.995 | 5/23 | 1/172 | 493/0/20/1532 | 645/1458 |
| empty_20261027 | 22 | 0.99 | 14/23 | 1/172 | 785/4/64/1192 | 1084/1458 |
| baseline_20261028 | 11 | 0.999 | 12/23 | 1/172 | 639/0/23/1383 | 482/1458 |
| positive_20261028 | 10 | 0.995 | 9/23 | 1/172 | 628/1/31/1385 | 765/1458 |
| empty_20261028 | 29 | 0.995 | 13/23 | 0/172 | 651/2/42/1350 | 984/1458 |

Compared with positive-only expansion, adding explicit empty negatives retains 5→14 and 9→13 real anchors at the same false-frame constraint. Compared with the recalibrated old baseline, the gains are only 13→14 and 12→13. New data alone therefore does not establish a general improvement. Both new recipes add **zero** selections on the reused 80-image community validation for either primary policy. One recalibrated old baseline adds a previously inspected AI-supported point to the weaker native-B/H hybrid; it is not a new human confirmation or a new-model gain.

## The routing problem exposed by complete inference

Actual batch-one replay agrees with cached CCT false-frame counts. However, the independent **two-n experimental primary already selects 60/172 empty frames**: 43 bird, 10 head and 7 eye. These are not native Z8 or A12 measurements. An abstention-only auxiliary branch cannot remove a pre-existing wrong primary choice. Complete pipelines retain 60 or 61 false selections, although the ranker alone selects only 0 or 1. Camera-trap domain behavior must not be generalized to a field AF error rate.

A fixed-threshold shadow rejection of B/H reduces empty selections from 60 to 8 for both new seeds, while keeping all eyes by construction. It also drops community geometric support from 68/80 to 36/80 or 35/80, rejecting 33 or 34 primary B/H choices. Geometry is only a proxy; three rejected points were actually inspected and judged AI-supported coarse bird surfaces, without human confirmation. The old human point export matches none of these exact rejected points. Thus this fixed gate is not enabled. Its threshold was calibrated for maximum pooled proposals, not for the different production B/H-point population; this failure does not rule out a separately trained/calibrated gate.

## Decision and next experiment

Keep the primary and its defaults. The next useful experiment is direct background suppression in the main n detector, with explicit empty-scene negatives and correct-eye replay, plus quality training on the actual B/H candidate sources. Global non-detections or missing eye labels must not become negatives. This next main-detector training was **not executed in this round**. New capture-event testing is still missing; public calibration and synthetic masks cannot substitute for it.

The corrected 40-view supervision audit, separate 200-step pilot and 150 unit/contract tests passed. Evaluation and prediction CLIs reproduce locked calibration, existing-target preservation and abstention. All new epoch checkpoints read back; initial states and matched first-point sampling are verified. 19,396 new input/mask assets and 15 pre-locked cache binaries pass final hash checks; production annotation state and originals remain unchanged. Failed contour-cache and initial NumPy JSON-serialization attempts are retained; neither supplied new formal training results.

[summary.json](summary.json), [training-curves.json](training-curves.json) and [SHA256SUMS.txt](SHA256SUMS.txt) publish statistics and execution identities. Weights, photos, masks, caches and private paths remain outside Git. Inference structure is unchanged; this round adds no new deployment or camera timing claim.
