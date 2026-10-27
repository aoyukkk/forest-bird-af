# B/H classification-only continuation

**English** | [简体中文](classification-guard-2026-10-28.zh-CN.md)

This round follows the [failed backbone continuation](main-background-2026-10-27.md).
It trains only the existing B/H classification towers, **49,158 parameters in
42 tensors**, while retaining the complete independent two-n architecture.
Backbone, neck, box regression, unused pose heads, BN running statistics and
the separate eye expert remain fixed. This is not native Z8 or A12 training.

## Fit-side replay and scene audit

The frozen 33,212-input manifest and 380-image development view are reused.
Hardness is computed only from the 375 community fit records: body maximum
side at most 32 input pixels, median body-box luminance at most .18, or a
head-only partial annotation. Luminance is the median of RGB weighted by
(.2126, .7152, .0722) after division by 255; it describes the box, not a
pixel-accurate bird mask. Missing body/head/eye labels remain unknown.

An actual 12-panel input-scale engineering inspection found a suspected
tree-hole scene relationship between fit `fb_0499` (group `fb_0496`) and
validation `fb_0382`/`fb_0384` (group `fb_0377`). This is a visual suspicion,
not verified capture-event identity. Before formal training, **all 21 fit
frames in group `fb_0496` are quarantined from this round's sampling**.
The original split and production annotations are unchanged. The first pilot,
its executed source and the pre-quarantine replay receipt are retained.

The revised fit pool contains 354 community frames; 60 hard frames belong to
21 groups. Their categories overlap. The parent was already trained on the
old split, so exclusion cannot turn the old validation into an independent
test. The suspected relationship is recorded in the results, rather than
silently claiming decontamination of the parent's history. The 12-panel audit
is an AI engineering inspection, not new human annotation.

A newly received local photograph is copied byte-for-byte into its own intake
batch and held pending annotation and capture-relation checks. It is neither
fit nor development data in this experiment and is not published or assigned
a public registry ID. Old source inputs and the published 694-record snapshot
remain unchanged.

## Matched experiment

Each batch has eight ordinary replay images, four hard community images and
four CCT images. Ordinary replay samples community groups with probability .7;
otherwise it chooses CUB/NABirds/COCO uniformly by source. Hard community and
CCT sampling chooses group then frame. Both conditions receive identical image
orders for each seed. CCT B/H classification loss is masked in `control` and
enabled at .1 weight in `empty`; labels follow the
[source admission protocol](data-expansion-2026-10-27.md).

Two seeds (20261028, 20261029), eight epochs, 96 batches per epoch and batch 16
give 12,288 image presentations per run. AdamW uses learning rate .000005 and
decay .0001, CUDA FP16 autocast, FP32 loss arithmetic and clip norm 10.
The model stays in evaluation mode during autograd so frozen behavior and BN
statistics match the parent. No geometric or blur augmentation is applied.
Inputs are exact 384×256 RGB CHW divided by 256.

The existing partial-label detection criterion is retained. Its frozen
regression terms still contribute to the reported numerical loss, while only
classification parameters receive updates. A new positive guard decodes parent
box centers, finds corresponding labelled B/H regions, and takes up to three
anchors per part with parent score at least .1. It penalizes only decreasing
their logits, using squared hinge loss averaged by object then image. Hard
images receive factor two and the whole guard has weight two. No teacher
prediction becomes a new annotation. No CCT frame receives a positive guard.
The revised 32-batch pilot is discarded before formal training.

## Selection and readback

Parent and epochs 2/4/6/8 are evaluated with fixed E=.8, H=.4, B=.4 and E→H→B
routing on the same 80 community, 172 CCT and metadata-fixed 128 COCO images.
Original aggregate floors remain: geometry support at least 68, outside
geometry at most one and no selection on the explicit community absent frame.
The guard additionally rejects a candidate that loses **any previously
supported community frame**, even if another new frame offsets the total.
All eye counts must remain equal. This is a stronger frame-preservation rule
than the preceding round, so cross-round differences are not a single-factor
ablation. Within this round, both conditions use the same rule and opportunities.

Among safe candidates, fewer CCT selections ranks first, then more community
geometric support. Epoch zero remains eligible. COCO IoU≥.5 / score≥.4 recall
is diagnostic only. Geometric support does not prove visible surface, identity,
depth or focus, and missing eyes are not treated as errors. The reused development
views are not a new blind test. Historical tests are not reopened.

Every fit batch checks raw box-regression equality with the frozen parent.
Each checkpoint is read back; every tensor outside the classification allowlist
must match the original. Regenerated sampling orders must match logged hashes,
and exclude quarantined and development IDs. Final validation reloads the two
actual networks using `evaluate_main_background.py`, recomputes eye predictions,
and checks exact combined-prediction equality. All source and production-state
readbacks are kept outside Git.

## Commands

Use the pinned optional YOLO runtime and existing compatible CUDA PyTorch.
Keep all generated outputs outside Git:

```text
python scripts/training/prepare_classification_guard.py --dataset FROZEN_DATASET --quarantine-group fb_0496 --output FRESH_REPLAY_DIR
python scripts/training/train_classification_guard.py --help
python scripts/training/evaluate_main_background.py --help
```

Training needs `--dataset`, frozen `--eyes`, revised `--hard`, original B/H
`--initial`, unchanged `--eye-parent`, `--condition control|empty`, `--seed`
and fresh `--output`. Run both conditions for both seeds without changing
source, data or parent weights. The evaluator takes a selected box checkpoint
and its corresponding expected validation JSON. The public
[results](../../experiments/classification-guard-2026-10-28/README.md) contain
aggregates and hashes, not weights, photographs, private source paths or databases.
