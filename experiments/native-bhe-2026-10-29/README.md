# Native B/H/E head continuation — 2026-10-29

**English** | [简体中文](README.zh-CN.md)

The user completed all 11 previous point reviews: all support a usable bird-surface hint, while eye-localizability and part remain unknown. Exact inputs, points and complete revision histories pass validation. These are evaluation decisions on old development data, with zero production annotation writes or training-label promotions.

Four new matched runs finish in 5.24 minutes. The selected development candidate reaches **57/80 geometric support and 11/25 known-eye hits**, with 3 known final-eye errors. **It fails empty-scene acceptance and is rejected for replacement; defaults remain unchanged.**

## Matched comparison

| Model / run | Geometric support | Known-eye hits ≤4px | Known final-eye errors | Eye selections without eye truth |
|---|---:|---:|---:|---:|
| Original | 54/80 | 9/25 | 3 | 1 |
| Previous diagnostic | 54/80 | 11/25 | 3 | 3 |
| equal-control-20261029 / epoch 13 | 56/80 | 11/25 | 3 | 3 |
| equal-control-20261030 / epoch 16 | 57/80 | 11/25 | 3 | 4 |
| quality-20261029 / epoch 14 | 56/80 | 11/25 | 3 | 3 |
| quality-20261030 / epoch 16 | 57/80 | 11/25 | 3 | 4 |

All runs start from original weights, use 354 fit / 80 reused validation images, and quarantine the same 21 suspected related-scene fit IDs. Historical test tensors remain unopened. The six validation groups are reused development evidence, not a new event test.

The existing topology, body format, consumer, backbone, auxiliary rows and padding stay fixed. The permitted original-head parameter range expands from 2,130 to **5,490**; model size and inference operation structure do not increase. Native FP16/dot/add forward is retained; STE backward is approximate. Both conditions use AdamW, batch32, lr.0003, preservation10, 16 epochs and seeds20261029/20261030. Both add weight1 BCE at the same labelled-eye anchors: target1 in `equal-control`, detached `exp(-distance²/(2×6²))` in `quality`. This removes the previous extra-loss-weight confound. No missing eyes become negatives.

The declared E/H/B=.6/.5/.4 selector is a hypothesis, not recovered camera control. Selection requires no loss of geometry or increase in outside/absent selections, known final-eye errors or unreviewed eye choices. Human surface decisions exempt only exact same coordinates from the unreviewed counter, never from strict eye errors. New or moved points cannot inherit a decision. Do not infer a causal capacity gain by comparing with earlier rounds that differ in loss and review rules.

The two conditions have equal selected metrics for each seed: 56 supported/11 known-eye hits for20261029 and57/11 for20261030. Localization-quality supervision shows no additional benefit here; equality of aggregate metrics does not prove identical predictions.

## Tradeoffs and actual replay

- Compared with the original, paired geometry gains are fb_0264, fb_0378, fb_0386; losses are none. Group contributions are in [summary.json](summary.json).
- Candidate-level strict bird TP/FP: 44/29 → 45/33; head TP/FP: 35/19 → 34/24; eye TP/FP: 9/3 → 11/4. Head F1 falls .6731→0.6296. Candidate-level false positives and the final selected-eye error count are different quantities.
- Body size remains **1,543,726 bytes**, with 6,813 changed bytes, all in permitted existing head ranges. All 64 checkpoints preserve unauthorized FP16 parameters; 434 loaded feature-cache hashes match. Eight actual full-backbone/body/C-consumer replays match cached head words and packets; three additionally match the original BA2 interpreter. This is eight full-network checks, not 80.
- Same 172 CCT empty frames: **74→82 selections**; equal-location macro rate 26.18%→29.44%. Added false-selection frames 8, removed 0, retained-frame kind switches 6. Counts alone do not establish identical predictions. Empty replay takes 7.38 minutes on the shared software backend, not camera latency.
- All four follow-up points now have explicit human surface support: fb_0264, fb_0365, fb_0378 and fb_0386. Fourteen current candidate positions exactly match supported decisions across both batches, including the three newly captured frames. Eye truth remains unknown; no eye-accuracy promotion follows. See [follow-up evidence](human-surface-followup.json). No new independent events or optical AF tests exist.

The fit set contains **353 present frames and only one explicit empty frame**. Extra head false positives occur on fb_0241 (+3), fb_0364 (+1) and fb_0377 (+1); fb_0379 loses one strict head match. Inadequate negative exposure is a supported motivation for the next experiment, not a proven cause. Next prioritize independent fit-side explicit-empty CCT replay with box-retention guards and matched positive sampling. Never train on these 172 calibration frames or the point-review decisions.

176 tests pass; 6 protected source/cache files and 5 production tables remain equal. A further 16 original ARM64 caller cases confirm cleanup precedes eye linking, with linking gated by a post-cleanup field equal to 2 in two observed callers. These routing probes explicitly stub both callees; the field's meaning, final bird target control and detection Hz remain unresolved. See the [previous independent callee audit](../native-return-2026-10-29/README.md).

## Reproduction and artifacts

```text
python scripts/training/train_native_guidance.py --dataset ../private-native-cache --upstream ../private-native-package --regions ../work/regions-validation.json --exclude ../work/excluded-fit.json --output ../work/equal-control-20261029 --condition equal-control --update-mode bhe-head --review-manifest ../work/point-manifest.json --review ../work/human-export.json --seed 20261029 --epochs 16
```

Repeat for seed20261030 and `--condition quality`, always with new output directories. The full human export and input manifest stay private; [human-surface-review.json](human-surface-review.json) publishes minimal decisions and the full-export hash. Review decisions are never training targets. Replay a separately exported body with `evaluate_native_empty.py --body-copy`; supply the same frozen 172-frame public-validation manifest. [Plan](plan.json), [source hashes](source-sha256.json), [checksums](SHA256SUMS.txt).

Vendor weights, firmware, photos, feature caches and production databases stay outside Git. The candidate is exported locally and is not installed on a camera. The four-point review is complete; the original run summary retains its frozen state. Next evaluate independent fit-side empty replay and retain separate point/box/background metrics; do not simply fit more epochs to the same validation set.
