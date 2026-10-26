# 2026-10-26 training aggregates

**English** | [简体中文](README.zh-CN.md)

[summary.json](summary.json) contains measured counts, threshold curves,
checkpoint hashes and qualified diagnostics for the completed local comparison.
[Report](../../docs/training/next-round-2026-10-26.md) ·
[Implementation](../../docs/training/yolo26-parts.md).

One fixed training seed; the community validation labels were Z8-assisted.
Public tests have 200 CUB source images in two paired views, not 400 independent
captures. No new real forest-event test or camera AF verification is claimed.
No training or threshold changes followed test opening. The n candidate
improved original-view eye localization but regressed in small-view bird recall;
continuation/KD retained the same parent. The original whole-teacher failure
remains recorded even though a later sparse-positive development gate passed.

Only aggregate evidence is published. Vendor weights, production database,
initialization/checkpoint binaries, third-party photographs and per-image
NABirds labels remain outside Git. Saved initialization snapshots are required
for exact replay because their original creation seed was not recorded.
