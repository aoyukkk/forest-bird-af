# Public-data expansion and empty-scene supervision

**English** | [简体中文](data-expansion-2026-10-27.zh-CN.md)

This round admits additional public data, checks the local A12 teacher entry,
and compares point-verifier training recipes. It does not retrain the frozen
YOLO26-derived detector or enable a replacement. [Measured results](../../experiments/expansion-2026-10-27/README.md).

## Sources and admission

NABirds completion uses six additional official-training mirror shards pinned
by revision and SHA-256, joined to the original part metadata. The mirror's
license declaration does not override [Cornell's research terms](https://dl.allaboutbirds.org/nabirds).
New NABirds supervision is limited to visible human eye anchors; derived head
boxes are removed. Other pixels do not become background.

[COCO](https://cocodataset.org/#termsofuse) contributes bird instance masks and
body boxes from train2017, restricted to the selected per-image licenses.
Its annotation license does not confer ownership of the photographs.
[CCT](https://lila.science/datasets/caltech-camera-traps) contributes only frames
whose upstream category set is exclusively `empty`: no detector abstention is
converted to truth. Selection uses daytime images, one frame per camera-day
and sequence, then removes grayscale/extreme-exposure inputs. The original
3,146 COCO/CCT downloads produced 3,053 prepared inputs and 93 exclusions.

Of 17,410 proposed newcomers, 17,252 are admitted and 158 quarantined, with
every original retained. Reference contamination screening uses 16,399 frozen
input identities, including historical holdouts, solely for hashes/thumbnails.
No holdout prediction or label selects training, thresholds or checkpoints.
The first admission receipt counted slash-variant paths twice; the retained
corrected receipt normalizes paths and admits exactly the same newcomer list.

Exact pixels or pHash distance at most 4 plus RGB thumbnail RMSE at most .10
and a global gray similarity proxy at least .94 trigger conservative isolation.
This is not a complete capture-event or crop-duplicate detector. New similar
images match their retained representative directly. CCT splits by camera,
reserving 15 locations / 172 frames; the 678 fit frames come from other locations.
Old community IDs, annotations and frozen splits are preserved.

## Cached supervision and matched fitting

COCO negatives are restricted to annotated bird rectangles, outside mask and
contour uncertainty; the rest of the scene is unknown. An actual 40-example
input/crop audit found ambiguous negatives near blurred bird contours before
training. The failed cache is retained. The corrected cache ignores a four-pixel
outside-mask band, then passes another inspection (22 identical panels retained,
18 changed panels actually viewed). Background proxies retain half weight.
These engineering inspections are not new human confirmations or AF depth proof.

The new fit cache has 58,235 known points; calibration has 13,677 points including
unknowns. Fit frames with usable supervision: 12,561 NABirds, 1,851 COCO and
678 CCT. Admitted images with no usable eye/mask supervision generate no fit
frame. The old CUB/community verifier caches remain immutable.

Both new recipes train the same 808,417-parameter RGB/context verifier from
the same initialization, keeping the detector and surface proposer frozen.
The positive recipe draws 50% from the old CUB/community mixture, 25% new
NABirds and 25% new COCO. For the empty recipe, the first point and its image
sequence are exactly matched; 30% of negative counterparts are replaced with
explicit CCT negatives, sampled by camera then frame. RGB brightness draws
match as well. There are two seeds, 32 epochs, 4,096 frame-pair presentations
per epoch and batch 64 frames. The pilot is separate and not reused.

Training uses read-only memory maps, AdamW .0003 / weight decay .0001,
weighted BCE plus .5 pairwise softplus, CUDA float16 autocast and clip norm 10.
Unknowns never enter the fit loss. Parent context is cached; this is not full
backbone training. Binary cache identities are locked before formal fitting.

Both retained old baselines receive all 32 saved epoch checkpoints as selection
opportunities under the same expanded calibration. Selection requires at most
one real known-negative frame and at most one actual CCT-empty selection, then
maximizes retained real eye anchors and combined CUB/COCO mask proposal utility
`foreground - 5*known_wrong`. NABirds anchor acceptance is diagnostic only.
The CUB/COCO pool contains 2,045 correlated/internal development views. A parent
pretrained on COCO may have seen COCO imagery; this is not a new blind test.

Cached calibration is followed by actual batch-one inference at locked
thresholds, including the complete two-n routing on CCT. A separate rejection
shadow filters only B/H at those already selected thresholds, keeps eyes, and
does not select alternatives. It is a diagnostic of a fixed rule, not a new
policy or a threshold search on community validation.

## A12 entry check

Eleven SDK libraries and seven Sony model files match their existing locks.
That proves asset identity, not detection semantics. The current photo-to-box
viewer explicitly invokes Nikon Z8. The genuine completed local Sony example
is a quantized-zero re-identification network with a 64-byte embedding.
The Windows NBG wrapper copies raw input bytes and does not implement the
image preprocessing claimed by its docstring. Detector preprocessing and the
B/H/eye decoder are not verified, so **zero A12 pseudolabels are admitted**.
No new Sony process, system virtualization change or remote job is started.

## Reproduction

Use the existing optional YOLO/PyTorch runtime and fresh outputs outside Git.
Download original source metadata/images under their applicable terms. Then:

```text
python scripts/training/prepare_coco_cct.py --help
python scripts/training/admit_public_expansion.py --base ../old/dataset.json --nabirds ../completed/dataset.json --coco-cct ../coco-cct/dataset.json --reference ../identity-reference.json --output ../admitted
python scripts/training/prepare_expansion_ranker.py --admitted ../admitted/newcomers.json --parent ../parent.pt --surface-head ../surface.pt --output ../new-cache
python scripts/training/train_expansion_ranker.py --old-cache ../old-cache --new-cache ../new-cache --output ../pilot --condition empty --pilot-steps 200
python scripts/training/train_expansion_ranker.py --old-cache ../old-cache --new-cache ../new-cache --output ../empty-seed1 --condition empty --seed 20261027 --epochs 32 --audit ../new-cache/visual-audit.json
python scripts/training/evaluate_expansion_ranker.py --old-cache ../old-cache --new-cache ../new-cache --checkpoints ../old-baseline/checkpoints --output ../recalibrated-baseline
```

The visual-audit receipt must represent actual inspection and bind this cache's
configuration hash. Repeat both conditions for both seeds. The evaluator can
also replay one saved checkpoint, emitting a hash-bound inference calibration
for `predict_bird_residual.py`. Photos, cached tensors, model weights, original
review exports and private paths stay outside Git. No new real capture-event
test or camera AF verification is available.
