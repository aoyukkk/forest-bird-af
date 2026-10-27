# Classification-only retention — 2026-10-28

**English** | [简体中文](README.zh-CN.md)

**Four matched runs completed.** The best development candidate retains all
68 previously supported community frames and reduces CCT selections from
60/172 to 58/172. The improvement is small and includes a new error, so the
candidate is exported separately and **inference defaults stay unchanged**.
These are independent YOLO26-derived n networks, not native Z8 or A12 models.

## Measured results

The table compares the same final epoch. Thresholds remain E=.8, H=.4, B=.4.
Geometric support means a cue near a labelled eye or inside a part box; it
does not establish visible surface, depth, subject identity or actual focus.

| Model / condition | Seed | Epoch | Community support /80 ↑ | Lost parent-supported frames ↓ | Outside geometry /80 ↓ | CCT selections /172 ↓ | COCO bird-box TP /381 ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Parent | — | 0 | 68 | 0 | 1 | 60 | 57 |
| Replay control | 20261028 | 8 | 68 | 0 | 2 | 69 | 60 |
| Empty supervision | 20261028 | 8 | 68 | 0 | 1 | 59 | 58 |
| Replay control | 20261029 | 8 | 68 | 0 | 1 | 66 | 59 |
| Empty supervision | 20261029 | 8 | 68 | 0 | 1 | **58** | 58 |

The two control selections retain the parent. Seed 20261028's empty condition
selects epoch 2, while seed 20261029 selects epoch 8, the overall development
candidate. All 16 evaluated new checkpoints preserve the parent-supported
frame set. One control checkpoint fails the outside-geometry ceiling. No run
selects the explicitly absent community frame. Actual eye outputs remain
identical: 35 selected eyes, 15 known-eye 4-pixel hits, two known-eye misses and
18 unassessed selected eyes. This is a consequence of freezing the independent
eye network, not evidence of improved eye learning.

Within each seed, image orders and settings are matched; the CCT loss mask is
the intervention. Empty supervision improves the fixed-epoch background result
relative to the control in both runs. Across rounds, backbone freezing, learning
rate, positive guard, sampling and selection rules all changed; retention
cannot be attributed to freezing alone from that comparison.

## What changed in actual inference

The selected candidate removes **three** previous empty-scene selections but
adds **one head selection on a human**, for a net reduction of two. The removed
bird scores change .443→.390, .401→.358 and .417→.388 at the fixed .4 threshold.
This is a small confidence change, not broad evidence of stronger bird semantics.

Six community outputs change coordinate or part kind; all remain geometrically
supported. One switches from a bird box to a head box. Ten panels covering all six
changes and all four empty transitions were actually viewed. Their visible
surface/depth quality is an AI diagnostic, not newly human-confirmed truth;
prior point-review decisions do not transfer to a different point. The four
frames lost in the previous backbone continuation retain the parent's exact
point and kind in this candidate.

## Data and integrity finding

Hard replay initially selected 62 of 375 community fit frames. A 12-panel
engineering inspection found suspected shared tree-hole scenery between fit
`fb_0499` (group `fb_0496`) and validation `fb_0382`/`fb_0384` (group `fb_0377`).
Capture identity is unconfirmed. Before formal fitting, all 21 fit frames in
group `fb_0496` were quarantined from this round. The original split and reviews
remain unchanged; revised replay uses 354 community frames, including 60 hard
frames in 21 groups. Both pilot records are retained and discarded for formal
initialization.

The parent has historical exposure to the old fit pool. Quarantine does not
make its old validation independent, nor prove that all remaining scenes are
independent. This limits both this round and interpretation of earlier scores.
No historical test is reopened. The reused 80 community / 172 CCT development
views are not a fresh test, and the COCO view may overlap public pretraining.

One new local submission was copied into a separate collection batch, with
source/copy SHA-256 equality and full JPEG decode verification. It remains
pending annotation and relationship checks, with no public ID, publication,
training use or development use. The published 694-record snapshot is unchanged.

## Execution and delivery

- Four runs × eight epochs, 96 batches per epoch, batch 16. Existing local conda
  and RTX 4080 Laptop GPU; formal matrix wall time **700.50 s / 11.68 min**,
  including setup and baseline evaluation. Training/periodic-evaluation loops
  total 629.31 s. Two independent 32-batch pilots precede the formal matrix.
- Only 49,158 B/H classification parameters in 42 tensors are eligible for
  updates. All other checkpoint state and every batch's raw box regression match
  the parent. Both independent networks together still contain 4,911,456 parameters.
- All 32 checkpoints read back correctly and contain real classification
  updates. Regenerated sample orders match; neither quarantined nor development
  IDs are sampled. All 33,212 source hashes and five production-table snapshots
  match. The new source photo and copied bytes also match.
- Actual two-network reload on 380 inputs exactly reproduces eye and combined
  predictions. The separate candidate export is hash verified. **162 tests pass.**
- Alternating batch-one timing, 120 repeats per arm over eight inputs, gives
  parent P50/P95 **37.28/41.89 ms**, candidate **36.98/41.65 ms**. It includes
  transfer, both FP16 forwards, decoding and selection, excluding disk loading.
  The difference does not establish acceleration. PyTorch peak fit allocation
  is 170,692,096 bytes, excluding desktop/other GPU allocations.

Next evidence should prioritize new-point human review, same-domain foliage
negatives and a new capture-event holdout. The local pending photo is a possible
future case after annotation and relationship checks, not a completed test set.
No claim of a generally better model or camera deployment follows from this round.

[Method and commands](../../docs/training/classification-guard-2026-10-28.md) ·
[Summary](summary.json) · [All epoch curves](training-curves.json) ·
[Frozen-plan fields](plan.json) · [Checksums](SHA256SUMS.txt).

No A12 labels, remote jobs or virtualization changes occur. Weights, photographs,
private source paths and production databases remain outside Git.
