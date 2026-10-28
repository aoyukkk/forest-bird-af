# Information and scale diagnostic

**English** | [简体中文](information-diagnostic-2026-10-28.zh-CN.md)

[Results and decision](../../experiments/information-diagnostic-2026-10-28/README.md).
This round updates no weights. It separates input information, scale/context,
automatic region discovery, and annotation-boundary effects before more fitting.

## Inputs and isolation

Use the existing pinned Python/PyTorch/Ultralytics environment, a separately
obtained verified native package, the frozen 80-frame community region manifest,
the expanded development manifest, retained B/H and eye checkpoints, the previous
parent evaluation, and frozen native validation packets. The production database
is opened read-only to compare logical table snapshots. All output directories
must be new and outside this repository. Do not point outputs at original images.

The community manifest must contain only `community_val`; the empty cohort is
the existing 172 CCT `public_val` records. No historical test is read. The one
new pending submission does not have confirmed labels and is not used.

## Run

Replace the example paths with locally verified assets. These commands consume
local files; they do not download a model or change the environment.

```text
python scripts/training/diagnose_bird_information.py --regions ../work/regions-validation.json --dataset ../work/main-dataset.json --box ../work/parent-box.pt --eye ../work/parent-eye.pt --parent-evaluation ../work/parent-evaluation.json --native-validation ../work/native-validation.json --upstream ../private-native-package --database ../private-annotation/annotations.sqlite3 --output ../work/information-diagnostic
python scripts/training/evaluate_information_routes.py --dataset ../work/main-dataset.json --regions ../work/regions-validation.json --box ../work/parent-box.pt --eye ../work/parent-eye.pt --diagnostic ../work/information-diagnostic --downloads ../public-downloads/CCT --output ../work/information-routes
python scripts/training/evaluate_native_empty.py --dataset ../work/main-dataset.json --upstream ../private-native-package --output ../work/native-empty
python scripts/training/render_information_review.py --regions ../work/regions-validation.json --diagnostic ../work/information-diagnostic --output ../work/information-review
```

Run sequentially for isolated timing. The executed round overlapped original-CCT
inference with native diagnostic replay using `--wait-for-diagnostic`, which waits
for completed diagnostic status before measuring latency. Native-empty replay then
started after route timing. Preserve any interrupted output instead of overwriting it.

## Geometry and metrics

The independent decoder now accepts explicit input dimensions and eye suppression
radius; default 384×256/4px behavior is unchanged. A 768×512 forward uses 8px eye
suppression and maps all outputs back to 384×256 before assessment. Native explicit
centers and extents are transformed together. Known-eye distances do not double.

Label-derived crops use all labelled bodies, or heads when no body was annotated.
They answer recognition with supplied location, not autonomous localization.
Automatic regions use only B/H proposals at ≥.1, body priority, 1.5× context,
minimum width 64, 3:2 shape, region IoU rejection >.7, and at most two regions.
Both proposed deployment hypotheses preserve any existing parent selection and
use extra inference only for abstentions. Neither policy uses labels at inference.

Report fixed-denominator geometry, known-eye errors, unassessed eyes, paired gains
and losses, and group means. Compare CCT both by frame and by camera location.
Do not convert unknown eyes, outside-box points, or AI review suggestions into
confirmed background labels. The two pending boundary issues are not scored as
corrections and are not written to production.

## Decision boundary

Both automatic routes were rejected on the existing development evidence. There
was no additional training, threshold search, replacement export or deployment.
The 768-scale model was not retrained or recalibrated; this limits causal claims
about its failure. New-event testing, camera operators/compiler, ISP input,
working RAM, frame frequency and optical feedback remain unverified.

The exact executed source hashes are published with the experiment. In the
executed round, original native replay and parent predictions were verified
against frozen outputs, references and CCT originals passed reconstruction checks,
five production tables were preserved, and 166 tests passed.
