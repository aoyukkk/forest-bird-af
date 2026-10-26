# Reviewing what a coarse capture point actually hits

**English** | [简体中文](point-review-2026-10-26.zh-CN.md)

The 51 eye-unassessed selections from the previous coarse capture candidate
were inspected individually on the frozen 384×256 inputs. Each view contains
the full image and a 96×96 nearest-neighbour crop. Existing B/H truth boxes were
hidden. Additional marked crops were inspected where boundaries were ambiguous.
No other vision model, generated detail or guessed hidden eye was used.

| AI draft judgement | Images |
|---|---:|
| Point appears on visible bird surface and supports a coarse cue | 36 |
| Clearly on vegetation, not a usable bird point | 5 |
| Uncertain, including mixed boundaries and heavy occlusion | 10 |

These are the original AI diagnostic drafts, **not human truth, a new test or AF accuracy**.
The AI records remain `human_confirmed=false` and `accepted_for_training=false`.
The later human confirmations are stored separately below.
The production annotations and previous scores are preserved. An eye that is
not localizable in this input is not labelled absent or used as a negative.

The five unsupported drafts are `fb_0245`, `fb_0377`, `fb_0378`, `fb_0379` and
`fb_0389`. In `fb_0245`, the point lies inside the bird's annotated box but on a
foreground twig across its chest. Three similar scenes select a distant leaf
bud. Box membership therefore cannot establish a visible bird surface.

## Threshold and fallback checks

On these same 51 already-inspected points, increasing the score cutoff from
.2 to .7 retains 25 supported drafts, zero unsupported drafts and 4 unknown
drafts; it also drops 11 supported drafts. This is a same-subset discard
diagnostic, not a validated false-lock rate or an assessment of replacement
fallback positions.

A secondary cache experiment allowed coarse hints only when the primary E/H/B
strategy abstained. Existing targets were retained exactly and new hints were
explicitly labelled `capture_hint`, never precise eyes. At .2:

| Primary policy | Geometric support before → after /80 | Outside labelled geometry before → after | AI-unsupported additions |
|---|---:|---:|---:|
| Native B/H + parent eyes | 62 → 69 | 6 → 7 | 1 |
| Two-n B/H and eye combination | 68 → 72 | 1 → 6 | 4 |

At the AI-only stage, .7 added one AI-unknown point per policy.
The fallback rule is therefore **not enabled by default**. The helper
`bird_guidance_fallback.py` and the optional externally selected-point evaluator
support reproducing the diagnostic; inference defaults are unchanged. These
rules were examined after viewing the same development images.

## Human amendment

The user exported **51/51 explicit confirmations: 44 usable, 7 unusable and
0 uncertain**. Input hashes, candidate IDs, exact points and complete revision
histories were validated; the original export was preserved outside Git.
Production labels were unchanged and no reviewed record was accepted for training.
Optional eye-localizability and part fields all remain unknown. These are coarse
cue decisions, not newly labelled eyes. The 44/51 usable fraction (86.3%) describes
this selected old-validation subset, not whole-model or camera AF accuracy.

| Original AI draft | Human usable | Human unusable |
|---|---:|---:|
| Supported (36) | 35 | 1 |
| Unsupported (5) | 0 | 5 |
| Unknown (10) | 9 | 1 |

Human-unusable IDs are `fb_0245`, `fb_0377`, `fb_0378`, `fb_0379`, `fb_0387`,
`fb_0388` and `fb_0389`. The human decisions supersede AI suggestions for these
fixed points without overwriting the original drafts.

| Primary policy | Capture cutoff | Human-usable additions | Human-unusable additions |
|---|---:|---:|---:|
| Native B/H + parent eyes | .2 | 7 | 1 |
| Two-n combination | .2 | 3 | 6 |
| Native B/H + parent eyes | .7 | 1 | 0 |
| Two-n combination | .7 | 1 | 0 |

The .7 additions (`fb_0386` and `fb_0180`, respectively) are now human-supported.
This corrects their earlier unknown status. Each policy gains only one reviewed
point on reused development data; the rule remains an experimental candidate,
not a default. Low-cutoff promotion remains rejected. Existing primary targets
were not all surface-reviewed and cannot inherit these judgements.

On the same 51 fixed points, a .7 cutoff keeps 29 usable and zero unusable points
while dropping 15 usable ones. This post-review threshold diagnostic does not
establish a zero false-lock rate or validate replacement targets.

All 5,385 prepared CUB training masks were reread: correct 384×256 dimensions,
no empty masks and no empty foreground after a diagnostic two-pixel erosion.
This is structural validation, not a visual quality assessment. They were already
used for hard-context compositing and eye filtering in the preceding round.
The next hypothesis is to supervise a separate coarse-surface output directly
with foreground minus known synthetic occluders, beyond the previous augmentation.
Before a matched two-seed comparison, verify transformed targets and boundary
unknowns visually. Keep precise-eye supervision separate and these old validation
images out of training. No new training was started in this review step.

## Offline human review page

`scripts/annotator/build_point_review.py` builds a self-contained local HTML
from a review workspace's `manifest.json`, source/view hashes and separate
`drafts/<image_id>.json` files:

```text
python scripts/annotator/build_point_review.py --workspace ../point-review-work --output ../point-review-work/review.html
```

Open the HTML in Chrome or Edge. Keys/buttons 1/2/3 explicitly confirm usable,
unusable or uncertain and advance. Navigation and note saving do not confirm.
AI advice is collapsed and never prepopulates human decisions. Semantic edits
invalidate prior confirmation; JSON export/import preserves revisions and
checks the frozen input/point identity. The page uploads nothing and changes
no production labels. Export a JSON backup rather than relying on browser
storage alone.

Validate and preserve the exported backup with:

```text
python scripts/annotator/import_point_review.py --source ../point-review-export.json --workspace ../point-review-work --output ../point-review-work/human-import-new
```

The importer requires the complete frozen cohort, counts only explicit
confirmations, rejects changed identities and training promotion, verifies
source input bytes and refuses to overwrite an import directory. The original
export and history remain private; public results omit notes and private paths.

Desktop rendering was inspected. A separate synthetic-only browser fixture
exercised navigation, confirmation, editing, undo and the export handler; it
created no real human confirmations. The broader training question remains
whether training-side visible-surface/point-quality supervision improves a
separate coarse capture output. These old development drafts will not be
added to training. Sony, remote work and deployment remain paused.

[Separate AI and human records with checksums](../../experiments/point-review-2026-10-26/README.md).
