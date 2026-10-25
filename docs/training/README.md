# Training code

The scripts under `scripts/` are the code that produced the local head
fine-tune. This repository does **not** contain the vendor model package, CUDA
weights, the annotation database or the photos, so the scripts are complete and
their arguments are accurate, but they will not run without your own verified
package.

## What each script does

| Script | Purpose | Needs |
|---|---|---|
| [prepare_z8_training.py](../../scripts/prepare_z8_training.py) | Back up the annotation database read-only, freeze train/val/test by leakage group, cache native backbone features and verify them bit-exactly | vendor package, CUDA, Pillow |
| [train_z8_heads.py](../../scripts/train_z8_heads.py) | Freeze the backbone, update only allowed head rows, export the candidate body and read it back | as above plus the frozen dataset directory |
| [evaluate_z8_training.py](../../scripts/evaluate_z8_training.py) | Open the test set once after selection; run both models through the original BA2 post-processing | as above |
| [probe_z8_finetune.py](../../scripts/probe_z8_finetune.py) | Bounded trainability probe to confirm the gradient path | as above |
| [probe_z8_multibird.py](../../scripts/probe_z8_multibird.py) | Observe candidate behaviour on multi-bird frames | as above |
| [benchmark_z8_candidate.py](../../scripts/benchmark_z8_candidate.py) | Batch throughput, original versus candidate | as above |
| [z8_probe_labels.py](../../scripts/z8_probe_labels.py) | Native table lookup and candidate label adaptation | vendor package |
| [z8_trainable_heads.py](../../scripts/z8_trainable_heads.py) | Trainable head tensors, gradient masks and body export | torch |
| [z8_training_targets.py](../../scripts/z8_training_targets.py) | Target assignment, negative construction, metric matching, derived supervision | torch, numpy |
| [export_z8_labels.py](../../scripts/export_z8_labels.py) | Production database to publishable labels, private fields dropped | standard library |
| [export_split_manifest.py](../../scripts/export_split_manifest.py) | Frozen split to a publishable manifest | standard library |
| [verify_annotations.py](../../scripts/verify_annotations.py) | Offline check of published labels and split | standard library |

## Key arguments

```text
--dataset            frozen data directory (split-lock.json, dataset.json, cache-report.json, features/)
--upstream           locally verified vendor model package
--workspace          workspace holding the 384 x 256 input PNGs
--z8-package         vendor executor package containing z8models
--output             training output; must stay outside the vendor package, annotation database and repository
--update-mode        all | eye-class-only | eye-small-anchor
--preservation       weight of the original-output preservation constraint
--background-weight  derived background eye negative supervision
--precision-guard    require validation eye precision at least the vendor level and no extra background eye candidates
--head-local-weight  in-head local eye negative supervision
--min-epochs         minimum epochs for a directed long run; does not relax selection
```

## Gradient and numeric boundary

- The forward pass keeps native dot/add and FP16 storage, so the reproducible
  moving parts stay on the native numeric path.
- The backward pass is an STE approximation: the true derivative of FP16
  quantization and integer arithmetic is not derived, only an approximate
  direction is claimed.
- Every epoch checks that FP16 parameters outside the allowed mask are
  unchanged; any change fails the run.
- The exported body has the same size as the original; only bytes inside the
  allowed head range differ.

## Results and publication boundary

Measured numbers are in [native head fine-tune](z8-native-head-finetune.md);
withheld artifacts are in [what is not published](../releases/not-published.md).

## Minimal path

```bash
python scripts/prepare_z8_training.py --help
python scripts/train_z8_heads.py --help
python scripts/evaluate_z8_training.py --help
```

`--help` works without the vendor package. A real run needs the locally verified
package and CUDA, and the output directory must stay outside the repository.
