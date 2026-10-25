# Annotation snapshot: schema and scope

**English** | [简体中文](README.zh-CN.md)

The 2026-10-25 snapshot has **694 records**: 547 confirmed, 146 draft and 1 held
for adjudication. All 146 drafts are folded duplicates; the active queue contains
535 confirmed records and `fb_0588` awaiting adjudication.

## Files

| Entry | Use |
|---|---|
| [Dataset entry](../README.md) | Start here for labels, formats and downloads |
| [Full source snapshot](../labels/community-corrections-v1.jsonl) | All current geometry and per-item corrections, including unconfirmed records |
| [Confirmed subset](../confirmed/README.md) | 547 complete confirmed records and derived format views |
| [Frozen split](../splits/evaluation-split-v1.json) | 535 usable images and their conservative leakage groups |
| [Curation](CURATION.md) | Queue and priority list; not a quality-filtered truth set |
| [Toolchain](TOOLCHAIN.md) | Import, review, dedupe and export |
| [Review rounds, Chinese](review-rounds.zh-CN.md) | Review history and outstanding adjudication |

## Contract

- Geometry: `box_xyxy` and/or `point_xy` on the frozen 384×256 input. Eye points
  have no invented extent. Accepted native half-pixel edges stay unchanged.
- `kind`: bird, head, eye, auxiliary or uncertain. Auxiliary is not a body label.
- `review_status`: confirmed, draft, needs_adjudication. A draft or missing part
  is never a negative label.
- `decision`: correct, partial_error, error, uncertain or unassessed.
- `items`, `diff`, revision counts and frozen-candidate counts distinguish
  accepted vendor proposals from human additions, removals and edits.
- Private paths, reviewer identities and free-text notes are removed from the
  public snapshot. The production database and full revision log remain local.

## Evaluation limits

375/80/80 images were assigned to train/validation/test before fitting. Groups
stay together, but they are source-directory/visual engineering approximations,
not verified capture identities; 58 test images share one group. The test was
used once and is not a fresh test for continued development.

The labels are Z8-assisted human review, not independent blind annotation,
original-photo visibility or lens autofocus success. Multi-bird part association
is not established. See [training evidence](../../../docs/training/z8-native-head-finetune.md)
and [publication limits](../../../docs/releases/not-published.md).

Check offline with `python scripts/tools/verify_annotations.py`.
