# Capacity and real-hard-negative ranking results

**English** | [简体中文](README.zh-CN.md)

**Completed; retain the primary policy.** Six 8-epoch runs, then six fresh matched 32-epoch runs: 240 configured cache epochs, not whole-backbone epochs. The longer matrix took 2.46 minutes including process/cache loading, excluding cache preparation. [Method and commands](../../docs/training/residual-2026-10-27.md).

## Selected 32-epoch candidates

Real column: accepted exact eye anchors /23; known-negative false frames. CUB column: foreground / known wrong / unknown / abstain out of 1,800 correlated development views. Added points: **AI-supported / AI-unsupported / AI-unknown** after primary abstentions on reused community validation. These are drafts, not human truth.

| Run | Best epoch | Threshold | Real calibration | CUB F/W/U/A | Native B/H + parent eye additions | Two-n additions |
|---|---:|---:|---|---|---|---|
| small-hard_20261027 | 20 | 0.95 | 23/23; 0 | 1606/15/58/121 | 3/2/2 | 0/4/1 |
| large-easy_20261027 | 27 | 0.99 | 22/23; 1 | 1508/10/44/238 | 2/2/2 | 0/5/1 |
| large-hard_20261027 | 27 | 0.95 | 23/23; 1 | 1645/17/78/60 | 3/1/2 | 0/4/2 |
| small-hard_20261028 | 30 | 0.9 | 23/23; 1 | 1645/20/76/59 | 4/2/2 | 0/5/2 |
| large-easy_20261028 | 27 | 0.99 | 23/23; 1 | 1495/13/51/241 | 1/2/2 | 0/4/1 |
| large-hard_20261028 | 21 | 0.9 | 23/23; 1 | 1645/22/68/65 | 3/2/2 | 0/5/2 |

The internal rule ranks `large-hard_20261027` first. On the weaker native-B/H hybrid it adds 3 supported, 1 unsupported and 2 uncertain points; on the stronger two-n primary it adds **0 clearly supported, 4 unsupported and 2 uncertain** points. Existing primary choices and fine-eye counts stay unchanged. No replacement is enabled.

The six selected models produce 14 distinct new points: 4 AI-supported, 6 unsupported, 4 unknown. Nine exact input/point AI drafts were retained from the first inspection; five new points were actually inspected, including marker-free crops for ambiguous tiny heads. No old human point matches exactly and no new point has human confirmation. The historical tests remain quarantined; this is development diagnosis, not independent improvement evidence.

## What the comparisons show

The verifiers have 224,049 / 808,417 parameters. One n parent plus surface head and verifier totals 2,686,722 / 3,271,090; retaining a second independent n box model totals 5,142,450 / 5,726,818. Single-n totals exclude native B/H. These are not whole-camera resource or deployment claims.

Hard-negative training retains more calibration anchors than easy controls, but more capacity does not reliably improve real residual points. Longer fitting improves internal metrics without establishing useful two-n residual gains.

Real positives are sparse eye anchors; foliage inside a bird box remains unknown. Only one fit frame is explicitly absent, and internal calibration has none. It contributed just 40 or 52 point presentations per 32-epoch run, out of 262,144. The numerical negative budget therefore constrains mostly distant derived background, with poor coverage of in-box foliage and varied empty scenes. This supports a coverage/sampling diagnosis, not proof that capacity can never help or that one loss term alone caused failure.

A separate queue contains 40 existing fit images, 80 points, 24 groups, all initially unknown and unconfirmed. It changes no production labels and is not a list of 80 known errors. Every selected source frame already has a non-abstaining parent. Self-mining with a model that saw these images gives an optimistic failure pool. Next residual mining should use group-wise out-of-fold predictions initialized from weights that never saw that fold, explicit absence sampling, and fit-side local point judgements. Starting each fold from the current all-data parent would leak the fold. New capture events are still needed for final assessment.

## Matched local timing

500 repetitions per policy, rotated order, RTX 4080 Laptop, CUDA autocast float16, batch one, internally selected seed-20261027 32-epoch checkpoints.

| Pipeline | P50 ms | P95 ms |
|---|---:|---:|
| single_base | 21.38 | 25.65 |
| single_small | 21.78 | 26.74 |
| single_large | 21.83 | 26.26 |
| two_n_base | 38.46 | 44.93 |
| two_n_small | 38.89 | 45.92 |
| two_n_large | 39.29 | 45.40 |

Hot PNG read, preprocessing, decode and conditional ranking are included. Single-n caches native B/H outputs; two-n includes both networks. Large-verifier overall P95 overhead is 2.4% / 1.0% for single/two-n, but on abstaining frames alone two-n P95 rises from 42.17 to 47.28 ms. Overall percentiles conceal per-trigger costs. All models are resident; this is neither deployment-memory nor camera NPU/lens timing. Tail noise does not establish that a larger verifier is faster.

## Verification

140 unit/contract tests passed. Actual CLI checks preserve an existing target, reject input identity mismatch and reproduce an exported ranked point. Timed choices match independently exported inference. All epoch checkpoints read back, paired frame order matches, hard small/large point order matches, and executed source hashes match. 12,545 source assets, protected files and production annotation state passed readback. Binary cache checksums were first recorded after the initial matrix, so they are post-run identities rather than pre/post binary-equality proof.

[summary.json](summary.json) contains both stages, provenance, hashes and timing. [training-curves.json](training-curves.json) retains all epoch diagnostics. [SHA256SUMS.txt](SHA256SUMS.txt) covers the LF-normalized public aggregate files. Photos, weights, masks, caches, private paths and human exports remain outside Git. Sony, remote/A800 jobs and camera deployment remain paused.
