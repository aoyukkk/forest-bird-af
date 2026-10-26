# Next-round training and degradation review — 2026-10-26

**English** | [简体中文](next-round-2026-10-26.zh-CN.md)

Local training, augmentation and sparse distillation completed. The selected n
model improved original-view public eye localization, but small-view bird
recall regressed and overall community validation favoured the native
candidate. It is an offline research candidate,
not a recommended Z8 replacement. No camera autofocus was tested.

## What was held fixed

The community split remains 375 train / 80 validation / 80 historical test.
The old test was not evaluated again. Final public tests use 200 official CUB
test sources, one per species, excluding historical calibration IDs and screened
near duplicates. The second view shrinks the same sources to community bird
sizes on a median-colour canvas. These are 200 sources, not 400 independent
captures or new real forest events. All final models and thresholds were locked
before opening either view. No further training or threshold changes followed.

The model pool contained 13,958 public training and 1,547 public internal
validation images, from CUB official training data and 9,572 verified NABirds
official-training IDs. With community training, 14,333 unique images were
available. Each epoch samples 4,096 presentations with expected 50:50
community/public balance; it does not traverse all public images each epoch.

All YOLO trials share saved initialization snapshots, seed 20261026, 384×256
RGB /256 inputs, batch 32, AdamW and the declared partial-label losses. n/s are
pose-derived custom B/H and eye-grid models, not stock YOLO26. Community head
and eye-only labels never require invented body boxes. Public coarse head boxes
are weak labels; original eye points never become artificial eye boxes.

## Validation and controlled comparisons

Validation has 79 bird, 50 head and 25 eye labels. Strict boxes use IoU .5,
eyes use 4 input pixels. Native and YOLO thresholds are calibrated on the same
validation set and the same 16-value grid; native calibration can only filter
already-emitted proposals. Epoch selection uses macro F1 as a development
proxy. A complete matched wrong-target-rate or fallback criterion remains
unavailable because visibility/instance identity is incompletely labelled.

| Model | B TP/FP | H TP/FP | E TP/FP | Macro F1 | Epoch best/ran | Loop min |
|---|---:|---:|---:|---:|---:|---:|
| Native original, val calibrated | 44/29 | 35/18 | 9/3 | 58.17% | — | — |
| Native repaired, val calibrated | 44/29 | 35/18 | 17/5 | 66.07% | — | — |
| n baseline | 45/11 | 25/14 | 17/9 | 63.17% | 9/21 | 11.70 |
| n augmentation | 45/34 | 31/22 | 14/3 | 61.27% | 19/31 | 19.05 |
| s teacher | 55/17 | 27/15 | 13/3 | 64.99% | 7/19 | 12.03 |
| n no public head | 40/18 | 29/14 | 15/3 | 63.51% | 17/29 | 12.81 |
| n continuation control | 40/18 | 29/14 | 15/3 | 63.51% | 0/12 | 5.49 |
| n sparse KD | 40/18 | 29/14 | 15/3 | 63.51% | 0/12 | 5.52 |
| n matched size | 43/37 | 27/13 | 16/4 | 61.73% | 16/28 | 14.24 |

The original native-mask bug reused a class index as a spatial column. Its
gradient regression tests now pass. Matched repair and competition=0 controls
both ran 89 epochs, selected epoch 59, and retained 17 eye hits / 5 unmatched
proposals at native settings, equal to the old candidate. Fixing the bug did
not improve this validation score. The raw native-settings macro F1 was
57.95% →65.85%; the table above separately shows calibrated thresholds.

The earlier n run without reviewed-frame background supervision scored
56.71%; the matched full-head baseline with protected background scored
63.17%. This supports that training-semantic correction in this seed/recipe.
Removing public coarse heads improved some head/eye precision but did not
improve all parts. Standard augmentation and size matching also traded parts
against each other. No claim covers all YOLO26 recipes or multiple seeds. Labels were reviewed with visible Z8 proposals; zero native coordinate error can reflect retained proposal coordinates and is not independent subpixel ground truth.

## Precision/recall tradeoff

These are validation-only descriptive operating points on the existing
threshold grid, not new public-test thresholds. The denominator is 25 eye
labels. FP means conditionally unmatched proposals, not camera misfocus.

| Model | ≤0 eye unmatched | ≤3 | ≤5 |
|---|---:|---:|---:|
| original | 0 TP / 0 FP | 9 TP / 3 FP | 9 TP / 3 FP |
| repaired | 0 TP / 0 FP | 8 TP / 3 FP | 17 TP / 5 FP |
| n baseline | 4 TP / 0 FP | 9 TP / 1 FP | 14 TP / 5 FP |
| n augmentation | 9 TP / 0 FP | 14 TP / 3 FP | 14 TP / 3 FP |
| s teacher | 7 TP / 0 FP | 13 TP / 3 FP | 13 TP / 3 FP |
| n no public head | 2 TP / 0 FP | 15 TP / 3 FP | 15 TP / 3 FP |
| n matched size | 10 TP / 0 FP | 10 TP / 0 FP | 16 TP / 4 FP |

## Teacher and distillation outcome

The s teacher failed the original whole-model admission: at its validation
threshold .9, 200 training-domain calibration images yielded 78 correct / 28
unmatched eyes. That failure is retained. After inspecting validation
duplicates, a new **development-stage amendment** admitted only sparse .95
positive guidance: calibration 40/5, validation 7/0. This criterion was not
preregistered. Teacher points also had to be within 4px of existing human eyes;
misses never became negatives. It did not create new unlabelled-image truth.

The matched continuation and KD trials both selected epoch 0, preserving the
same n parent tensors. Their last weights changed, and KD used 4,908 supported
point presentations; the experiment ran but produced no selected improvement.
Before KD, tests caught and fixed unordered-slot routing and duplicate teacher
assignment. Failed code/test evidence remains local.

## Locked public tests

Thresholds: original/repaired B=.4, H=.5, E=.6; student B=.6, H=.15, E=.8.
No human head-box truth exists in this test, so public macro F1 averages B/E
only and is not comparable to three-part validation macro F1. Eye eligibility
uses source landmark visibility and an input-scale heuristic, not new blind
review. Missing/unknown parts are ignored. Focal-bird labels do not certify
all other birds absent. Every original/repaired output buffer passed the
original BA2 instruction execution; full repaired reload and original
batch/singleton head equality passed on three samples in each view.


**original: 200 images, 201 eligible eye points.**

| Model | Bird hits / 200 at IoU .5 | Bird hits at IoU .3 | Eye hits | Eye unmatched | Eye precision | E 2px/8px hits | B/E macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| original | 65 | 183 | 150/201 | 23 | 86.71% | 108/162 | 56.16% |
| repaired | 65 | 183 | 161/201 | 45 | 78.16% | 106/178 | 55.61% |
| student | 193 | 196 | 160/201 | 19 | 89.39% | 120/171 | 89.88% |

**scale_stress: 200 images, 179 eligible eye points.**

| Model | Bird hits / 200 at IoU .5 | Bird hits at IoU .3 | Eye hits | Eye unmatched | Eye precision | E 2px/8px hits | B/E macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| original | 117 | 174 | 40/179 | 16 | 71.43% | 25/49 | 46.34% |
| repaired | 117 | 174 | 66/179 | 60 | 52.38% | 35/92 | 50.96% |
| student | 64 | 94 | 48/179 | 13 | 78.69% | 29/53 | 38.88% |

## What the public numbers mean

At native IoU .5 the original has 65/200 bird matches; at .3 it has 183/200.
Of 205 native bird proposals, 199 centres lie inside the focal bird box and
118 overlap at .3–.5. Thus 140 strict unmatched boxes do **not** mean 140
background focus locks. The student better fits CUB box geometry; the size
of its strict box advantage must not be read as an equally large AF gain.

At 4px eye precision/recall, the original-view student improves over the
original. The native fine-tune adds recall but loses precision. The proposed
E→H→B selector still sometimes chooses an unmatched eye while a labelled
body/head candidate exists; these diagnostics have unknown/biased coverage,
not verified camera selection or complete fallback. Public-pretraining
overlap is unknown, so these views do not establish real forest generalization.

In the small-target view the student's bird recall is 64/200 versus native
117/200, despite a modest eye improvement (48/179 with 13 unmatched versus
40/179 with 16). Its B/E macro F1 is 38.88% versus 46.34%. The native fine-tune
has more small-view eye hits (66), with 60 unmatched proposals. This is a
recall/precision tradeoff rather than an overall better model.


## Compute and timing

RTX 4080 Laptop 12GB and the existing local conda environment were sufficient.
The seven completed v4 YOLO loops totalled 80.84
minutes; two native recovery loops totalled 13.05
minutes. These totals exclude data downloads/preparation, failed engineering
runs, earlier background ablations and final parity tests.

| Custom model | Parameters | Conv/matmul GFLOPs at 384×256 | FP16 parameter payload | Training allocated peak |
|---|---:|---:|---:|---:|
| n | 2,455,728 | 1.312 | 4.91 MB | 953 MiB |
| s | 9,769,776 | 5.176 | 19.54 MB | 1,895 MiB |

The selected n measured model+decode P50/P95 21.14/23.21ms with GPU input
already resident; it excludes image load. These are local software timings,
not camera latency. The native physical-MAC proxy is 0.699G operations,
including padded lanes and excluding other instructions. Its accounting
differs from the profiler's conv/matmul count. Neither proves camera NPU
throughput, supported operators, working RAM, compiler access or portability.

## Evidence and next decision

Original assets, production labels and old test locks were preserved; no Sony,
A800 or camera deployment ran. [Aggregate evidence](../../experiments/next-training-2026-10-26/summary.json)
contains every completed trial, fixed thresholds, initialization/checkpoint
hashes, curves, test counts and qualified selection diagnostics. It contains no
third-party images or vendor weights. Exact paired-run replay needs the saved
initialization snapshots: their original creation seed was not recorded.
[Implementation and commands](yolo26-parts.md).

Next priority is a new real-event forest holdout with available/unavailable/
unknown eye/head states, a few complete bursts, and audits of input scaling or
ROI selection. Keep strict localization and separate coarse acquisition and
duplicate proposals. Do not lower thresholds after this test to manufacture
a win, or assume simple blur/padding mimics real foreground defocus. Further
large-scale pseudo-labelling should wait for a teacher calibrated on those
actual failure modes. Camera deployment remains a separate engineering task.

Data remain subject to [CUB terms](https://www.vision.caltech.edu/datasets/cub_200_2011/),
[NABirds terms](https://dl.allaboutbirds.org/merlin-computer-vision-terms-of-use),
and the YOLO route to [Ultralytics terms](https://www.ultralytics.com/license).

Batch-one warm-cache pipeline timing includes PNG decode, input transfer and postprocessing: n P50/P95 24.72/28.85ms (n=30); native physical replay 17331.84/17631.67ms (n=6). The latter expands physical arithmetic into many CUDA tensor calls; their speed ratio is not a camera cost ratio. No concurrent training or repository tests ran in this final timing pass.

The aggregate also records nearest-eye distance normalized by the unique containing human head's long side on community validation. It is a best-case proposal diagnostic, with missing proposals separate; it does not establish the selected AF point or bird identity.
