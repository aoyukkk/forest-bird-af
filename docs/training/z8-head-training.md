# Local native-head fine-tuning

**English** | [简体中文](z8-head-training.zh-CN.md)

The user authorized formal local Z8 training on 2026-10-25 and requested reuse
of the existing conda environment. Sony, remote jobs and camera deployment remain
paused. Vendor packages, weight copies, private source maps and annotation
snapshots stay outside this repository.

`prepare_z8_training.py` snapshots the reviewed database and dedupe sidecar,
verifies PNG/CHW identities and freezes group-level train/validation/test splits.
Conservative grouping combines submitted source directories and visual/dedupe
relations. Loose files with unresolved provenance are training-only. These are
engineering leakage groups, not verified photographer or capture identities.

The current snapshot has 535 usable confirmed images: 375 train, 80 validation,
80 test. It excludes 158 queue-hidden duplicates and one unresolved review.
The held-out labels were reviewed with Z8 assistance, not independently blinded.

Exact frozen-backbone features are cached once. Each image must reproduce the
original frozen FP16 heads and the trainable-head replay bit for bit before
training starts. `train_z8_heads.py` uses native dot/add/storage in the forward
pass and explicit STE approximations in backward. Only original detection-head
weight/bias spans may be exported into an independent body copy. It does not
replace the backbone with floating-point convolutions.

Human bird boxes supervise the operational review union of slots 0/4, head
boxes slot 1, and eyes the unresolved union 2/3. This does not establish the
vendor subtype/direction semantics. An eye point supervises location without
inventing a box extent. Auxiliary regions are not body targets. Missing parts
remain unknown. Conservative recovered human-deleted proposals and explicitly
confirmed no-bird frames supply negatives; other outputs are preserved against
the original model. Optional positive-anchor competition excludes auxiliary
and same-part unresolved subclasses. The eye-class-only mode masks gradients
for all other original output rows.

The subsequent eye-small-anchor experiment supervises positive eyes only and
also permits fine anchor 0 geometry/objectness and known-part class rows to
adapt. Other anchors' geometry/objectness and all auxiliary class rows stay
frozen. The run records the exact allowed parameter count and verifies all
other FP16 parameters remain identical after optimization.

Checkpoint selection uses validation macro F1 (bird/head IoU ≥0.5; eye-center
distance ≤4 pixels on 384×256), with an absolute per-part recall drop capped at
0.05 and F1 drop capped at 0.03. The F1 guard was added using validation errors
before trial 4 and before opening the test set; earlier trials remain intact.
Precision is conditional on part-labelled or explicit no-bird images;
unlabelled parts are ignored. Recall, precision, false-positive counts and a
looser IoU/distance view must accompany macro F1. This is an offline detection
metric, not tracking, multi-bird association or lens autofocus success.

`evaluate_z8_training.py` opens the test lock only after model selection. It
allows recovery only for the identical selected checkpoint. Both original and
tuned test buffers are checked against the original BA2 postprocessor. The
exported copy must also pass a full-native-graph replay check. Production data
and original weight hashes are checked again at completion.

```powershell
& <existing-conda-python> scripts/training/prepare_z8_training.py --help
& <existing-conda-python> scripts/training/train_z8_heads.py --help
& <existing-conda-python> scripts/training/evaluate_z8_training.py --help
```

Results are private experiment artifacts. Passing a training loss check does
not establish an improvement. Report the locked test outcome and any component
regression before recommending a candidate.

## Continued fine-tuning after the first test

The next round reuses the existing conda environment, frozen train/validation
split and cached native features. `--initial-head` loads a previous local
checkpoint only after verifying original forward parity. It must preserve all
currently frozen parameter rows. Epoch `-1` explicitly means the unchanged
parent checkpoint was retained; it is not a new training improvement.

`--background-weight` enables a derived eye-background loss with top-k hard
negatives. Only human-confirmed whole-bird-labelled or explicit no-bird frames
qualify. Every retained shape, including auxiliary/uncertain regions, has a
16-pixel protection margin. A cell is negative only if its entire possible
center range lies outside all protected regions. Head/eye-only frames have no
derived background. Both eye slots receive negatives in these regions, while
other classes/objectness do not receive a background-negative gradient. These
regions rely on a coverage assumption and are not newly human-labelled truth.

`--precision-guard` additionally requires validation eye precision at least as
high as the original model and no increase in derived-region eye candidates.
An unchanged macro F1 does not select a new checkpoint. The original output
retention loss is disabled for known-background eye logits, so it does not
explicitly preserve those mistakes.

The first round's 80 test images are quarantined during continued development.
They are not re-evaluated or used for new model selection. The prior test result
does not transfer to a changed checkpoint; a new independent evaluation is
required before making a new held-out-performance claim.

The optional `--head-local-weight` addresses eye-position mistakes inside a
labelled head. It requires exactly one human-confirmed head and one labelled
eye inside it, with no uncertain shapes. Predicted centers inside that head
and farther than the 8-pixel ignore radius can receive derived eye-class
negatives, excluding all positive-assigned cells. Coordinates/objectness are
detached from negative selection, so these negatives affect eye classes only.
The radius is not a fabricated eye bounding box. Completeness of visible-eye
labelling within that head is an explicit derived assumption; multi-eye,
missing-eye and ambiguous cases do not use this rule.

`--min-epochs` can prevent a short, threshold-flat pilot from stopping a longer
targeted run early. It does not relax checkpoint-selection or precision guards.
