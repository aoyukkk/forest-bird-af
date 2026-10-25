# Z8 native head fine-tune: round-two results and what can be published

[简体中文](z8-native-head-finetune.zh-CN.md) | **English**

Date: 2026-10-25. Machine-readable record:
[z8-native-head-finetune.json](z8-native-head-finetune.json). The plan and method
notes are in [native detection-head fine-tuning](../z8-head-training.md).

**Result: the current experiment candidate raised held-out macro F1 from 43.89%
to 46.92% and eye hits from 4/22 to 6/22, while eye precision fell from 80.00% to
66.67%. The 95% group-bootstrap interval for the macro-F1 gain is [0.00, 4.90]
percentage points and touches zero. Treat it as an experiment candidate only; it
is not a recommendation to replace the vendor model and says nothing about
in-camera autofocus.**

A further four refinement configurations did not beat the parent checkpoint
under the precision guard, so `selected_epoch = -1` keeps `trial_005` epoch 59.

## Data

A read-only snapshot of the production review database yields 535 confirmed
images: 694 rows minus 158 deduplicate-hidden queue images and 1 image held for
adjudication.

| Split | Images | Conservative groups | Bird | Head | Eye |
|---|---:|---:|---:|---:|---:|
| Train | 375 | 56 | 385 | 301 | 174 |
| Validation | 80 | 6 | 79 | 50 | 25 |
| Test | 80 | 5 | 83 | 59 | 22 |

Splits were frozen before training and the test set was opened once after
validation-only selection. The published splits and labels live in
`data/annotations-2026-10-25/` and can be checked offline with
`python scripts/verify_annotations.py`.

Two limits belong together with these numbers. 58 of the 80 test images share a
single conservative group, so the test set is not 80 independent scenes. Labels
come from Z8-assisted human review, not independent blind annotation, and are
bound to the frozen 384 x 256 input.

## Method

- The vendor backbone stays frozen; all 535 cached features replay bit-identical
  to the frozen FP16 output before any update.
- The forward pass keeps native dot/add/FP16 storage; the backward pass uses an
  explicitly recorded STE approximation and does not claim the true derivative
  of the integer graph.
- Only 2,130 original head parameters are allowed to move. The selected weights
  changed 1,350 FP16 parameters and nothing outside the allowed mask.
- The original consumer post-processes the output with unchanged thresholds and
  lookup tables.
- Selection maximises validation macro F1 with a per-part guard of at most 0.05
  recall drop and 0.03 F1 drop. The F1 guard was added on validation after trial
  4, before the test set was opened.

## Results

Strict criteria: bird and head IoU of at least 0.5, eye centre within 4 input
pixels, one-to-one matching, and unlabelled parts are never treated as
negatives.

| Metric | Original | Candidate |
|---|---:|---:|
| Bird F1 | 47.33% | 47.33% |
| Head F1 | 54.72% | 54.72% |
| Eye F1 | 29.63% | 38.71% |
| **Macro F1** | **43.89%** | **46.92%** |
| Bird hits / labels | 31 / 83 | 31 / 83 |
| Head hits / labels | 29 / 59 | 29 / 59 |
| Eye hits / labels | 4 / 22 | 6 / 22 |
| Eye unmatched-location false positives | 1 | 3 |
| Eye precision | 80.00% | 66.67% |
| Eye recall | 18.18% | 27.27% |

Under looser criteria (IoU of at least 0.3, eye distance of at most 8 pixels)
macro F1 moves from 45.15% to 48.18%, in the same direction.

Two more eyes are found and two more unmatched eye candidates appear. Bird and
head statistics did not regress on the test set, but that holds on five
conservative groups only and should not be extrapolated.

## Compute and size

| Item | Value |
|---|---|
| First native feature cache | 411.8 s |
| All five training loops | 1,131.6 s |
| Selected trial loop | 290.9 s |
| Final native cross-check | 61.7 s |
| Round-two refinement loops | 643.8 s |
| Candidate body size | 1,543,726 bytes, identical to the original |
| Changed body bytes | 2,248 |

With a batch of 16, one warm-up and three interleaved rounds, the original model
takes 18.968 s and the candidate 19.074 s, about a 0.56% difference. This is
local batch throughput, not single-image latency or camera frame rate.

## Why the weights and photos are not in this repository

- **The candidate weight is not committed.** Almost every byte of
  `resource744.finetuned.body.bin` is still vendor numeric parameters; the 2,248
  changed bytes sit on top of vendor weights, so publishing it publishes the
  vendor model. Only hashes, the changed-byte range and the reproduction path are
  published.
- **Photos stay in release packages.** The repository carries manifests, hashes
  and labels.
- **The database stays local.** Production annotations, deduplicate records and
  execution snapshots stay outside the repository; the published label file drops
  absolute paths, original-asset hashes, reference hashes and reviewer identity.

Weight identity can still be checked. Original body SHA-256 is
`e8d371e77efc3035d0c633c8c90aa4851f1675e5abcf7999edb23adc6439722b`; candidate
body SHA-256 is
`7171a42d8e9148ba9dd534f5096914818715ad414fed74a60964406cba781a0a`.

## Reproduce

```bash
python scripts/prepare_z8_training.py --help   # freeze splits and cache features (needs the local vendor package)
python scripts/train_z8_heads.py --help        # train and export the candidate body
python scripts/evaluate_z8_training.py --help  # single post-selection test run
python scripts/export_z8_labels.py --help      # production database to publishable labels
python scripts/export_split_manifest.py --help # frozen splits to a publishable manifest
python scripts/verify_annotations.py           # offline check of labels and splits
```

The first three scripts require the locally verified vendor package and CUDA,
neither of which is in the repository. The last three use the standard library
only and can validate the published files directly.

## Next steps

- The dominant eye problem is unmatched-location false positives: the five
  validation misses sit 8.09-11.19 px from the labelled eye, all inside the
  current background guard radius, so background-only supervision cannot reach
  them.
- More independently reviewed eye negatives are needed; only four restorable
  deleted eye false positives exist today.
- Grow the number of independent conservative groups before discussing held-out
  gains.
- Phase detection, lens drive and the whole-camera AF loop remain out of scope;
  no lock-on rate may be quoted.
