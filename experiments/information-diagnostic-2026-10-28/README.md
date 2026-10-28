# Information, scale and automatic fallback diagnostic — 2026-10-28

**English** | [简体中文](README.zh-CN.md)

**Existing-data experiments completed; both new fallback policies are rejected.** Keep the retained parent and native model. Pause additional fitting with the current recipe; preserve the project and improve supervision/evaluation before further optimization. This is not evidence that every possible training route must fail.

## Scope

Freeze 48 cases before new predictions: 12 previously unsupported frames plus 36 small-part/group-balanced controls. All aggregates use the full 80 reused community development images, six groups. Empty calibration uses 172 CCT frames from 15 locations. No historical test was reopened and no new submission entered training.

Ten view variants cover true 768x512 forwards, low-image upsampling controls, matched low/high-detail crops and actual native replay. The native graph remains fixed at 384x256. Label-derived crops diagnose recognition with location supplied; they are neither automatic discovery nor a mathematical optimal bound.

Actual native replay covers 238 full/crop views plus 172 empty frames. All 80 native full packets equal the frozen baseline; 252 dual-n full predictions equal the retained parent. All 80 reference resizes exactly reproduce frozen RGB; 172 original CCT sources pass hashes and resize equality.

Native E/H/B thresholds remain .6/.5/.4; dual n .8/.4/.4. Neither was tuned this round. E→H→B is a declared selector, not recovered camera target control.

## View results

Geometry support means proximity to a labelled eye or inclusion in an existing part box. Outside geometry is not automatically an optical focusing error. Eye counts concern the finally selected eye with assessable labels; 25 frames have eye labels. Missing eyes remain unknown; these are not complete-object recall or precision.

| View | Supported /80 ↑ | Outside geometry ↓ | Known eye 4px hits ↑ | Known eye unmatched ↓ |
|---|---:|---:|---:|---:|
| Native full | 54 | 10 | 9 | 3 |
| Retained dual n full | 68 | 1 | 15 | 2 |
| Dual n: low input upscaled to 768x512 | 62 | 10 | 15 | 0 |
| Dual n: reference resized to 768x512 | 67 | 10 | 18 | 2 |
| Dual n: automatic high-detail crops alone | 65 | 5 | 16 | 2 |
| Dual n: labelled low-detail crops | 69 | 0 | 6 | 0 |
| Dual n: labelled high-detail crops | 73 | 4 | 16 | 2 |
| Native: labelled low-detail crops | 75 | 3 | 16 | 4 |
| Native: labelled high-detail crops | 69 | 5 | 19 | 2 |

High full gains three supported frames and loses four. Upsampled low input scores 62/80 versus 67/80 for actual high detail: extra information helps some cases, but does not offset the current model/threshold shift. Native low-detail labelled crops reach 75/80, so supplied scale/context can matter without new pixels. This does not solve discovering the correct crop.

There was no 768-scale training or threshold recalibration. Results do not prove that high-resolution training would fail or that parameter capacity is exhausted.

## Complete automatic policies

Only parent abstentions trigger either branch; existing parent choices stay unchanged. Automatic regions use predicted B/H scores ≥ .1, body priority, 1.5x context, minimum 64 input pixels, 3:2 extent, at most two distinct regions. No proposals means no crop fallback. Coordinates return to the original 384x256 plane without loosening metric tolerances.

| Policy | Supported /80 | Outside geometry /80 | Original-detail empty selections /172 |
|---|---:|---:|---:|
| Retained dual n |68|1|60|
| Abstention→high full |70|7|138|
| Abstention→automatic high-detail crops |68|2|103|

High fallback adds support on `fb_0177` and `fb_0380`, but adds six outside-geometry points. Equal-group support improves only 1.53 percentage points. Automatic crops add no supported frame. Abstention-only routing cannot fix an existing wrong parent point such as `fb_0241`.

Upsampling/cropping the frozen low empty inputs yields 120/83 selections versus 138/103 using original detail. The low-image control does not add original information.

## Native comparison and location weighting

| Policy | Empty selections /172 ↓ | Equal-location false-selection rate ↓ |
|---|---:|---:|
| Native packets + declared selector |74|26.18%|
| Retained dual n |60|51.53%|
| High full fallback |138|80.79%|
| Automatic crop fallback |103|78.67%|

The retained parent has fewer frame-weighted empty selections than native, but worse equal-location results. Community geometry 54→68 and group mean 74.81%→90.00% are reused-development results; unassessed eye selections also increase 1→18. No single favorable aggregate establishes replacement quality.

## Visual inspection and annotation limits

AI engineering inspection covered 48 frozen cases plus four supplemental cases, one repeated (51 unique community frames), eight new empty selections and six point zooms. It created no human truth or production edits.

- New high fallbacks on `fb_0180/0182/0377/0378/0379/0388` visibly target foliage/branches.
- `fb_0395` high-full and `fb_0391` labelled high-crop points appear on visible head/beak above the existing bird box. Two pending human-review suggestions are retained separately; scores and labels remain unchanged.
- A zoom of `fb_0389` confirms the labelled-crop point on a foreground twig beside the blurred bird.
- Possible annotation-boundary undercounting does not explain the empty increase 60→138/103.

## Runtime and deployment

The completed diagnostic took 10.75 min; added native-empty replay took 6.55 min. An earlier inefficient serial run was interrupted and retained, not presented as completed. Original-empty inference overlapped native diagnostic work, but latency waited for that diagnostic to finish; added native-empty execution started after latency finished.

Eight fixed reference frames (two trigger fallback), 80 alternating repeats per policy. Includes original RGB resizing in host memory, transfer, actual forwards, decoding and conditional routing; excludes disk reads/model construction. These are not camera times and differ from earlier ~37 ms timing that excluded original resizing.

| Policy | P50 ms | P95 ms | Mean network calls |
|---|---:|---:|---:|
| Retained dual n | 94.86 | 120.82 | 2.00 |
| High-full fallback | 106.87 | 177.23 | 2.50 |
| Automatic high-detail crop fallback | 103.33 | 126.84 | 2.25 |

The two networks retain 4,911,456 parameters. Measured conv/linear arithmetic is 2.609 GFLOPs at 384x256 and 10.435 at 768x512 (~4x), excluding other work/memory traffic. Triggered high fallback also pays the initial parent pass. Camera operators/compiler, working RAM, ISP contract and frame budget remain unverified. A six-slot descriptor ring does not establish detector frequency.

## Decision and verification

Reject both policies; no default change, replacement export, training run or parameter update. Pause this recipe, review boundary labels and collect same-domain visible-surface/foliage supervision and new events. A12 has not passed teacher admission.

New-event blind testing, tracking and optical focusing remain unavailable; old resplits or synthetic data cannot stand in for them. Fixed-threshold inference failure alone does not prove project impossibility.

166 tests passed, covering dynamic coordinate limits, native-center crop mapping, label-independent regions and group-paired differences. Protected inputs/weights/vendor package and five production tables passed equality checks. Images, weights, database, private paths and per-image predictions remain outside Git.

[Summary](summary.json) · [Frozen plan](plan.json) · [Checksums](SHA256SUMS.txt) · [Reproduction](../../docs/training/information-diagnostic-2026-10-28.md).
