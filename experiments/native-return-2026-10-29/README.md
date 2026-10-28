# Native E7 return: firmware verification and fixed-layout training — 2026-10-29

**English** | [简体中文](README.zh-CN.md)

Four native runs and actual candidate replay completed. Topology, parameter layout and consumer stay fixed. All formal selections retain original initialization; one post-hoc development diagnostic is exported for 11 changed-point reviews. Defaults stay unchanged. This round does not beat the historical native candidate.

## Firmware evidence

The resource744 bytes at the declared Z8 C3.11 MAIN offset match the extracted resource; its 1,543,726-byte body exactly matches the pinned E7 backend. Input descriptors are 384×256, three byte planes, row pitch 384 and plane pitch 98, 304. Actual camera color order, normalization and ISP ROI remain unqualified.

Fresh original-ARM64 verification passes 130 instance-relation and 28 caller-scope cases. Group 6/7 membership and 10/11 eye links/headless cleanup are function-level evidence, not a closed final bird-selection loop. Observed generic-controller dispatch admits only 0/1/2/9.

A further 112 scenarios execute original `0x40fed730`, with explicit stubs only for initialization/provider/state outcomes, and verify global results 0/1/2/3. Missing source yields 0; some state/secondary-source conditions yield 1; flag+5 directly yields 3; otherwise two signed fields around±10 distinguish2/3. Physical field units and downstream inference submission effects remain unresolved. Earlier private H20 estimates of20–30 detections/s are not accepted: capture/display frames, task wakeups and CNN submissions are distinct counts.

An unsigned-immediate-load scan finds 181 offset candidates across the bounded code range. The two prior +680/+681 sites have local base/stride relationships consistent with family 0/2/4/5; they do not prove the final bird 6/7/10/11 consumer. Indirect access and full member association remain open.

## Training

Original initialization, frozen native backbone, exact native forward and explicitly approximate STE backward. Only 2,130 existing head parameters may update. Exclude 21 suspected related-scene fit frames: 354 train, 80 reused validation; no test tensor loaded and no old split modified.

Two order seeds per control/quality condition, 16 epochs each, batch 32, AdamW lr .0003 and preservation 10. Quality adds a detached six-input-pixel Gaussian localization target at assigned labelled eye anchors. Unknown eyes stay unknown. The added term also changes loss strength, so differences cannot be attributed solely to the quality target definition. Same-seed sample order matches exactly.

Adoption preserves original support and disallows increases in outside/explicit-empty selection, known-eye errors or unassessed-eye promotion; eligible models rank support, known 4px eyes, fewer known errors and strict macro F1. Unknown-eye promotion is a conservative adoption ceiling, not an error label.

| Run | Epochs | Final support /80 | Final known 4px eyes | Final known-eye errors | Final unassessed eyes | Selected epoch |
|---|---:|---:|---:|---:|---:|---:|
| control-20261029 | 16 | 54 | 11 | 3 | 4 | 0 |
| control-20261030 | 16 | 54 | 11 | 3 | 4 | 0 |
| quality-20261029 | 16 | 54 | 11 | 3 | 4 | 0 |
| quality-20261030 | 16 | 54 | 11 | 3 | 4 | 0 |

Epoch0 means retained original. All 64 epoch checkpoints have actual FP16 updates within the mask, with no frozen-entry changes. All 434 loaded feature hashes agree. Original counts are 54 supported, 9 known eyes, 3 known-eye errors and 1 unassessed eye. At epoch 14 quality reaches 11/3 known/unassessed eyes versus control 10/3 in both seeds; final metrics converge. No accepted endpoint or generalization gain is established.

## Post-hoc diagnostic and historical baseline

`quality-20261029`, epoch 14 is retained separately for inspection, not as an adopted model.

| Same reused development protocol | Support /80 | Final known 4px eyes | Final known-eye errors | Unassessed eyes |
|---|---:|---:|---:|---:|
| Original |54|9|3|1|
| This diagnostic |54|11|3|3|
| Historical trial_005 native candidate |56|17|3|10|

Historical evaluation uses the same cache/consumer/selector, never its old test. Its candidate-level strict eye TP/FP 17/5 differs from final-selection counts; this diagnostic is 11/3. Do not mix units.

The diagnostic body changes2, 335 bytes, keeps length 1,543,726 and preserves every non-head byte. Eight actual-photo full-native outputs match cached-head words exactly; three also match the original BA2 instruction interpreter. Original package bytes stay untouched.

## Empty scenes and review

On the same 172 CCT calibration frames, both original and diagnostic select 74 frames, equal-location rate 26.18%. No false-selection frame is added or removed. One false head becomes a false eye, increasing eye-kind selections 2→3. Equal totals do not mean identical outputs.

Actual AI engineering inspection covers 11 changed-point/kind panels. `fb_0242/0262` provide the two added known 4px matches. `fb_0171` moves a previously unassessed eye 1px; `fb_0172/0245` promote heads to unassessed eyes. `fb_0172` appears near body/wing, not a proven eye. Human confirmations remain 0; production labels are unchanged. New review identities bind input hash and point; old judgments do not transfer.

## Delivery and boundary

Formal matrix wall time 5.57 min, excluding pilot/firmware/roundtrip. Native empty loop 7.75 min is software replay, not camera latency. No graph/instruction step is added; this does not establish camera FPS.

170 tests passed. Same-format training/export/native decoding works, but a better model is unproven. New-event blind testing, final bird target consumption and optical AF remain open. Prioritize the 11 explicit human point decisions and actual membership/input callers before further fitting. No Sony, remote work or deployment; vendor assets/private records stay outside Git.

[Method](../../docs/training/native-return-2026-10-29.md) · [Summary](summary.json) · [Frozen plan](plan.json) · [Checksums](SHA256SUMS.txt).
