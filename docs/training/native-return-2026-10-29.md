# Fixed-layout native E7 continuation

**English** | [简体中文](native-return-2026-10-29.zh-CN.md)

[Results and firmware evidence](../../experiments/native-return-2026-10-29/README.md).

The user confirmed that original topology, weight format and deployment interface
must remain fixed, while existing parameters may be fine-tuned in separate copies.
This round returns to native resource744 instead of the independent YOLO model.

## Preserved execution

`TrainableHeads` retains the original FP16 storage and native dot/add forward
arithmetic. The backbone is frozen. Backward uses explicitly approximate STE;
it is not the derivative of the original finite-precision implementation.
The existing `eye-small-anchor` mask admits 2,130 original parameters: eye-class
rows plus channels 0–9 of the first fine anchor. Shared fine-anchor fields may
also affect bird/head proposals; they are evaluated, not assumed unchanged.
Auxiliary rows and all non-admitted parameters remain fixed. Each optimizer
step clips parameter deviation to ±.5 and restores frozen entries exactly.

Exports patch only original head matrix/bias ranges in a body copy. Body length,
command stream, descriptors, backbone and native consumer remain unchanged.
No vendor weights or firmware are published.

## Matched training

Reuse the locked native cache. Exclude the 21 suspected related-scene fit IDs
from the later scene audit: 354 fit and 80 reused validation frames are loaded.
No test feature tensor is opened; original split files remain unchanged.
Both conditions start from original weights with identical image order per seed.

- Two conditions × two order seeds, 16 epochs each, batch 32, AdamW lr .0003.
- Both use existing partial positive losses, explicit recoverable removed proposals
  and original-output preservation weight 10. No missing part becomes background.
- The quality condition additionally supervises the native eye class at an
  assigned, labelled eye anchor with `exp(-distance²/(2*6²))`. Distance is measured
  in 384×256 input pixels and detached from this class-quality loss; existing
  coordinate supervision still supplies coordinate gradients.
- No extra network, crop branch, training image transform or score-table change.

Selection uses the declared E/H/B selector (.6/.5/.4) on final points: preserve
original geometry support and do not increase outside geometry, explicit-absent
selection, known-eye mismatch or unassessed-eye promotion. Among eligible epochs,
maximize supported frames then known 4px eyes, fewer eye errors, and strict macro
F1 as a tie break. An unassessed eye is unknown, not an error; the promotion ceiling
is a conservative acceptance rule. It cannot certify such a point as wrong.

## Reproduction

Supply independently verified local files and keep outputs outside Git and all
source/annotation directories. Use the existing pinned conda environment.

```text
python scripts/training/train_native_guidance.py --dataset ../private-native-cache --upstream ../private-native-package --regions ../work/regions-validation.json --exclude ../work/excluded-fit.json --output ../work/control-20261029 --condition control --seed 20261029 --epochs 16
python scripts/training/train_native_guidance.py --dataset ../private-native-cache --upstream ../private-native-package --regions ../work/regions-validation.json --exclude ../work/excluded-fit.json --output ../work/quality-20261029 --condition quality --seed 20261029 --epochs 16
```

Repeat both with seed 20261030 into new directories. `--pilot --epochs 1` limits
the pilot to two training batches; never use it as formal initialization.
The executed matrix preserves all 64 epoch checkpoints and their actual consumer
outputs. A separately identified post-hoc diagnostic candidate is for point review,
not a selected replacement.

For original-layout candidate empty-scene replay:

```text
python scripts/training/evaluate_native_empty.py --dataset ../work/main-dataset.json --upstream ../private-native-package --body-copy ../work/diagnostic/resource744.finetuned.body.bin --output ../work/native-candidate-empty
```

The loader rejects backbone/instruction or body-length changes. The same prior
172-frame CCT calibration is reused; this is not a fresh independent test.
Review pages use the existing explicit-confirmation point-review tool, with new
input/point identities and no production or automatic training writes.

The firmware verification probes and binary-derived excerpts stay local. Published
aggregates distinguish synthetic control-flow verification from real image quality,
and neither establishes camera detection frequency or optical AF success.
