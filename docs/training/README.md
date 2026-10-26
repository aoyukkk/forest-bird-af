# Training code

**English** | [简体中文](README.zh-CN.md)

This directory covers native head fine-tuning and an independent
[YOLO26 parts model](yolo26-parts.md). The repository contains no vendor model
package, weights, feature caches, production database or photo files.

The native preparation route needs local SQLite, prelabel runs and source-group
maps. The YOLO route includes `prepare_public_community.py`, which adapts public
labels, the frozen split and downloaded input PNGs without a vendor package.
Historical test entries import metadata only. Keep all derived workspaces outside Git.


Current next-round results: [2026-10-26 comparison](next-round-2026-10-26.md).
It includes repaired native controls, public bird-parts data, n/s models,
augmentation, sparse positive distillation and the locked public test.


## What each script does

| Script | Purpose | Needs |
|---|---|---|
| [prepare_z8_training.py](../../scripts/training/prepare_z8_training.py) | Back up the annotation database read-only, freeze train/val/test by leakage group, cache native backbone features and verify them bit-exactly | vendor package, CUDA, Pillow |
| [train_z8_heads.py](../../scripts/training/train_z8_heads.py) | Freeze the backbone, update only allowed head rows, export the candidate body and read it back | as above plus the frozen dataset directory |
| [evaluate_z8_training.py](../../scripts/training/evaluate_z8_training.py) | Open the test set once after selection; run both models through the original BA2 post-processing | as above |
| [probe_z8_finetune.py](../../scripts/training/probe_z8_finetune.py) | Bounded trainability probe to confirm the gradient path | as above |
| [probe_z8_multibird.py](../../scripts/training/probe_z8_multibird.py) | Observe candidate behaviour on multi-bird frames | as above |
| [benchmark_z8_candidate.py](../../scripts/training/benchmark_z8_candidate.py) | Batch throughput, original versus candidate | as above |
| [z8_probe_labels.py](../../scripts/training/z8_probe_labels.py) | Native table lookup and candidate label adaptation | vendor package |
| [z8_trainable_heads.py](../../scripts/training/z8_trainable_heads.py) | Trainable head tensors, gradient masks and body export | torch |
| [z8_training_targets.py](../../scripts/training/z8_training_targets.py) | Target assignment, negative construction, metric matching, derived supervision | torch, numpy |
| [export_z8_labels.py](../../scripts/publish/export_z8_labels.py) | Production database to publishable labels, private fields dropped | standard library |
| [export_split_manifest.py](../../scripts/publish/export_split_manifest.py) | Frozen split to a publishable manifest | standard library |
| [verify_annotations.py](../../scripts/tools/verify_annotations.py) | Offline check of published labels and split | standard library |

## Key arguments

The public label JSONL is not a drop-in replacement for the local training
workspace. `prepare_z8_training.py` currently consumes the annotation SQLite
database, saved prelabel runs and private source-group maps; it does not import
`confirmed.jsonl` directly. The public labels/split support inspection and
independent adapters, but a standalone public-data-to-native-workspace importer
is not supplied. Published-data verification needs none of these private inputs.

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
- Gradient masks restrict updates; the selected checkpoint is checked before
  export for FP16 changes outside the allowed mask.
- The exported body has the same size as the original; only bytes inside the
  allowed head range differ.

## Results and publication boundary

Measured numbers are in [native head fine-tune](z8-native-head-finetune.md);
withheld artifacts are in [what is not published](../releases/not-published.md).

## Minimal path

```bash
python scripts/training/prepare_z8_training.py --help
python scripts/training/train_z8_heads.py --help
python scripts/training/evaluate_z8_training.py --help
```

`--help` works without the vendor package. A real run needs the locally verified
package and CUDA, and the output directory must stay outside the repository.

Latest follow-up: [input, hard-context and hybrid results](input-context-2026-10-26.md). New training did not surpass the saved parent; five-view eye fusion is a more expensive development candidate.


[Final selected guidance experiment](guidance-2026-10-26.md) adds cached CPU replay, localization-quality confidence and matched parent continuations.
