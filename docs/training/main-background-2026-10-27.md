# Main-detector background continuation

**English** | [简体中文](main-background-2026-10-27.zh-CN.md)

This experiment updates the B/H detector itself after the separate verifier
failed to suppress primary background selections without losing real cues.
It uses an independent YOLO26-derived n model, not the native Z8 network.
[Results and decision](../../experiments/main-background-2026-10-27/README.md).

## Models and supervision

The existing two-network parent has a B/H expert and a separate eye expert,
each with 2,455,728 parameters. Only the B/H backbone, neck and detector are
updated. Its unused pose heads and BN running statistics are frozen. The
independent eye expert is unchanged; its preserved eye results are a routing
property, not evidence that the new training improves eyes.

The merged manifest freezes 33,212 inputs. Fit pools contain 375 community,
5,385 CUB, 21,428 NABirds, 1,899 COCO and 678 CCT images. The remaining inputs
belong to public/community development partitions and are not sampled for fit.
No historical test images enter the manifest. Source admission, licenses and
conservative duplicate screening follow the
[previous expansion](data-expansion-2026-10-27.md).

Only upstream exclusive-empty CCT frames supply new whole-frame B/H absence.
Some contain humans; the supervision concerns birds. Public missing heads are
unknown. The eye branch is not trained. Existing partial class masks and the
community exterior-background assumption remain in effect. COCO labels include
dead birds, retained as generic bird examples; they are not all live forest birds.
No A12 pseudolabels or generated images are used.

An actual 24-input engineering inspection overlays B/H targets at 384×256:
12 community, three COCO, three NABirds and six CCT examples. It does not add
human confirmations or prove every source label correct. All input SHA-256
values and actual batch-one eye predictions are frozen before fitting.

## Matched intervention

Both conditions use identical batches, initialization and optimization. Each
batch contains 12 replay frames and four CCT frames. Replay samples community
groups with probability .7; otherwise it samples CUB/NABirds/COCO uniformly by
source. CCT is sampled by camera then frame. In the control, CCT B/H loss is
masked out. In the empty condition it receives .1 classification weight.
Frozen BN statistics prevent the control's CCT images from changing BN state.

There are two seeds, 20261027 and 20261028, eight epochs per run, 96 batches
per epoch and batch 16: 12,288 image presentations per run, not one complete
pass over the manifest. AdamW uses learning rate .00002, decay .0001, float16
autocast, FP32 loss arithmetic and gradient clipping at 10. No geometric or
blur augmentation is applied. The input is fixed RGB CHW 384×256 divided by 256.

Positive replay includes an output-preservation penalty of .25. It matches
parent B/H logits only within corresponding annotated boxes where the parent
score is at least .2, plus .02 times raw box-regression preservation. No parent
prediction is promoted to a new annotation. The separate 32-batch pilot is
discarded before formal training.

## Selection and verification

Parent and epochs 2/4/6/8 are evaluated with actual batch-one B/H inference and
fixed eye predictions on 80 reused community development frames, 172 CCT
calibration frames and 128 COCO development frames selected by a metadata hash.
The thresholds stay E=.8, H=.4, B=.4, with E→H→B precedence.

Selection first requires community geometric support at least 68/80,
outside-labelled-geometry at most 1/80 and no selection on the explicit
community absent frame. Selected-eye counts must exactly match the parent.
Among safe candidates it minimizes CCT selections, then maximizes community
geometric support. Epoch zero is an eligible candidate, so a harmful continuation
cannot force a replacement. COCO body recall at IoU≥.5 and score≥.4 is diagnostic,
not a checkpoint-selection target.

Geometric support means a point near a labelled eye or inside a labelled part
box. It does not establish visible bird surface, target identity, depth or
camera focus. CCT calibration and the old community validation have been used
repeatedly; neither is a new blind test. No new real capture-event holdout is
available. Missing eye labels remain unknown, not failed eye detections.

After selection, both independent networks are reloaded and their predictions
are recomputed. Eye-cache equality and selected-checkpoint equality are checked.
Optional timing alternates parent/candidate arms on eight fixed inputs, including
transfer, both forwards, decoding and final selection, excluding disk loading.
Original models, source inputs, production reviews and old test evidence remain
protected by readback hashes and database logical snapshots.

## Commands

Use the pinned optional YOLO runtime and compatible CUDA PyTorch, with outputs
outside Git and frozen source manifests from the earlier rounds:

```text
python scripts/training/prepare_main_background.py --help
python scripts/training/train_main_background.py --help
python scripts/training/evaluate_main_background.py --help
```

Preparation accepts `--base`, `--admitted`, `--regions`, `--box-parent`,
`--eye-parent` and `--output`. Training accepts the prepared `--dataset` and
`--eyes`, original `--initial` box weights, `--eye-parent`, `--condition`
(`control` or `empty`), `--seed` and a fresh `--output`. Repeat for both seeds
without changing any source or dataset. Evaluation takes the selected `--box`
and its `--expected` validation JSON, the same frozen inputs, and a fresh output.
For timing add `--reference-box` and `--benchmark-repeats 120`.

Weights, input images, private manifests and full per-image predictions stay
outside Git. Public source hashes and aggregate curves identify the experiment;
they do not distribute vendor assets or restricted-source photographs.
