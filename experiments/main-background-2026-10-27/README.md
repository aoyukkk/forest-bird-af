# Direct B/H background continuation — 2026-10-27

**English** | [简体中文](README.zh-CN.md)

**Four matched runs completed; retain the parent.** Direct empty-scene
supervision reduces background selections, but every evaluated continuation
fails the locked community-preservation conditions. No inference default is changed.
The models are independent YOLO26 derivatives, not native Z8 or A12 networks.

## Results

Thresholds are fixed at eye .8, head .4 and bird .4. The table uses the same
final epoch for matched comparisons; source curves retain all four evaluated
epochs per run. Community support is a geometric proxy, not camera focus success.

| Model / condition | Seed | Epoch | Community support /80 ↑ | Outside geometry /80 ↓ | Explicit absent selection ↓ | CCT selections /172 ↓ | COCO bird-box TP /381 ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Parent | — | 0 | 68 | 1 | 0 | 60 | 57 |
| Replay control | 20261027 | 8 | 67 | 1 | 1 | 123 | 103 |
| Empty supervision | 20261027 | 8 | 65 | 1 | 0 | 44 | 97 |
| Replay control | 20261028 | 8 | 68 | 4 | 1 | 133 | 100 |
| Empty supervision | 20261028 | 8 | 66 | 2 | 0 | 37 | 96 |

The minimum-empty checkpoints occur at epoch 6: **35/172** with **64/80**
community support for seed 20261027, and **36/172** with **66/80** for seed
20261028. They are diagnostic rejected candidates, not selected replacements.
All four safety-constrained selections retain epoch zero. Selected eyes remain
35, known-eye 4-pixel hits 15, known-eye misses 2 and unassessed selected eyes 18,
because the independent eye model and E→H→B routing are fixed.

The control and empty runs receive exactly the same ordered images for each
seed and epoch. Their CCT loss mask is the intervention; BN running statistics
are frozen. Thus the fixed-epoch comparison supports a background-supervision
effect within this recipe. It does not establish a better complete model or
generalization to a new forest-bird collection.

## What regressed

For the minimum-empty seed-20261027 checkpoint, four previous geometric cues
become abstentions, with no new supported frames: `fb_0175`, `fb_0181`,
`fb_0382`, `fb_0384`. An actual input-scale engineering inspection shows tiny
grass birds in the first pair and dark tree-hole birds in the second. They are
paired scenes, not four established independent events. Twelve changed-output
panels were viewed. This inspection is an AI diagnosis, not new human truth.

These losses are **not eye-distance or box-IoU rejections**: the complete
selector produces no point. Relaxing spatial tolerances cannot recover an
abstention at the existing confidence thresholds. Conversely, increasing COCO
box recall alone is insufficient: both controls improve it while substantially
increasing empty-scene selections.

The observations suggest a confidence/retention tradeoff and source-domain
mismatch. They do not identify model capacity as the bottleneck. A bounded next
comparison should first freeze the backbone and box regression, calibrate the
B/H classification head, and strengthen fit-side tiny/dark-bird retention.
That recipe has **not** been run here. New real-event holdouts remain necessary
before recommending a model replacement.

## Execution and readback

- Existing local conda/CUDA environment, RTX 4080 Laptop GPU; four runs × eight
  epochs, 96 batches per epoch, batch 16. Formal matrix wall time: **583.69 s
  (9.73 min)** including subprocess setup and baseline evaluations. Recorded
  training/periodic-evaluation loops total 527.83 s. The separate 32-batch pilot
  is not part of the formal matrix.
- 33,212 source input hashes read back unchanged. Protected model/test files and
  five production database table snapshots match. No original or review is edited.
- All 32 checkpoint readbacks match; all contain actual parameter changes.
  BN running state and unused pose-head tensors match the parent throughout.
- Actual two-network replay of the rejected shadow covers 380 development
  inputs and exactly reproduces both frozen-eye and recorded combined predictions.
- 157 local tests pass, including actual empty-loss gradients, partial-label
  masks, frozen BN, paired batches and rejection of harmful continuations.

Timing of the rejected shadow is diagnostic: 120 alternating repetitions per
arm over eight fixed inputs give parent P50/P95 **36.79/41.43 ms** and shadow
**37.11/42.26 ms**. This includes host-to-device transfer, two FP16 forwards,
both decoders and selection, excluding disk loading. Both paths contain
4,911,456 parameters; there is no additional verifier. Peak training allocation
reported by PyTorch is 585,787,904 bytes, excluding the desktop and other GPU
allocations. These timings do not establish a speed gain or camera compatibility.

## Evidence and limits

[Method and commands](../../docs/training/main-background-2026-10-27.md) ·
[Aggregate results](summary.json) · [All epoch curves](training-curves.json) ·
[Frozen-plan fields](plan.json) · [Checksums](SHA256SUMS.txt).

The 80 community development frames and 172 CCT calibration frames are reused.
The 128 COCO development frames may overlap public pretraining. No old test is
reopened; no new independent real-event test is available. Geometry does not
prove visible surface, subject identity, depth or actual focus. No A12 labels,
remote jobs, virtualization changes or camera deployment occur. Weights,
photographs, private paths and production databases stay outside Git.
