# Frozen-base surface results — 2026-10-27

**English** | [简体中文](README.zh-CN.md)

[Protocol and commands](../../docs/training/surface-2026-10-27.md) · [summary.json](summary.json) · [SHA256SUMS](SHA256SUMS)

All four eight-epoch runs completed. The 6,945-parameter surface head preserves
the 2,455,728-parameter base, its BN statistics and fixed-input float32 raw
outputs. Paired conditions have identical sampling orders. No replacement is
recommended: synthetic validation improved, but residual community cases still
show conspicuous vegetation selections and the sole confirmed no-bird image
was selected by all four candidates.

The following checkpoints and thresholds were selected only on 600 CUB
development images with three fixed variants each. These 1,800 correlated
views are engineering mask diagnostics and reuse training-derived backgrounds.

| Condition/seed | Epoch | Cutoff | Mask foreground | Known background | Known occluder | Unknown | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| R1 / 20261027 | 1 | .95 | 1696 | 15 | 13 | 61 | 15 |
| R2 / 20261027 | 3 | .70 | 1716 | 14 | 1 | 57 | 12 |
| R1 / 20261028 | 8 | .99 | 1687 | 10 | 15 | 75 | 13 |
| R2 / 20261028 | 4 | .80 | 1724 | 14 | 1 | 48 | 13 |

Full threshold curves at common cutoffs and error costs 2/5/10 are retained in
the summary. The selected-cutoff table reflects the combined training/selection
procedure; it does not isolate calibration changes or prove real-world gain.

On old community validation, all existing primary targets and selected-eye
counts remain unchanged. Across four candidates and two routing references,
48 unique new points were viewed. **AI drafts:** 13 supported, 29 unsupported,
6 unknown; **new human confirmations: 0**. The old 51 reviewed points are not
reused for changed coordinates and never enter training. AI judgements are not
human accuracy measurements. The single confirmed no-bird image `fb_0176`
provides an existing human-supported frame-level error for every candidate.

| Added points, AI supported / unsupported / unknown | Native B/H + parent eyes | Two-n primary |
|---|---:|---:|
| R1 / 20261027 | 6 / 4 / 0 | 1 / 10 / 0 |
| R2 / 20261027 | 4 / 4 / 4 | 0 / 10 / 1 |
| R1 / 20261028 | 4 / 4 / 2 | 1 / 8 / 0 |
| R2 / 20261028 | 3 / 4 / 5 | 0 / 10 / 1 |

The stronger primary already covers many usable birds; its remaining abstentions
are a harder distribution than arbitrary bird images. Residual-case calibration
and synthetic-to-real mismatch are hypotheses for follow-up, not proven sole
causes. A subsequent proposal should use training-side primary failures for
sampling, reliable surface supervision and real reviewed foliage negatives;
a model miss alone must never create a negative label.

| Hot PNG/read/preprocess/decode/select, 500 measurements | P50 ms | P95 ms |
|---|---:|---:|
| Single n reference | 22.97 | 35.47 |
| Single n + surface | 23.71 | 36.81 |
| Two-n reference | 42.50 | 63.64 |
| Two n + surface | 43.25 | 67.66 |

P95 overhead is 3.8% and 6.3%, respectively, within the proposed 20% budget.
Models are resident and CUDA float16; the single-n reference reuses cached
native B/H, excluding native computation. Forward-only CUDA event measurements
are separate in the summary. These are not camera or lens timings.

The first 48-view engineering audit caught multilevel mask normalization that
would turn some birds negative. It was fixed before GPU training; failed views,
the second inspected set, regression test and 200-step pilot were retained.
All 18,610 referenced input/mask/background assets and protected parent state
were verified unchanged. Production labels were not written. Local code tests
passed 135 cases, and an exported-head CLI smoke test preserved the supplied
primary target. Photos, views, original exports, cached features and weights
remain outside Git. Sony, remote/A800 and deployment remain paused.
