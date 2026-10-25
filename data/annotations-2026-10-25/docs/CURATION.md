# Best images and the deduplicated queue

This directory carries three scripts-generated, offline-checkable lists:

| File | Content |
|---|---|
| [best-images-v1.json](../curation/best-images-v1.json) | 120 confirmed stills ranked for first-look review |
| [dedupe-queue-v1.json](../curation/dedupe-queue-v1.json) | The queue after folding: 158 of 694 folded, 536 in queue, 42 groups |
| [labels/community-corrections-v1.jsonl](../labels/community-corrections-v1.jsonl) | All 694 per-image label records |

## How "best images" is ranked

Only human-confirmed images that are still in the deduplicated queue qualify.
The rule is fixed in `scripts/publish/export_best_images.py`:

```text
score = 4*coverage + (3*removed + 2*added + changed) + 2 when the vendor model produced no candidate
coverage = eye +2, head +1, bird +1
```

Result: 533 qualify, the top 120 are listed. Score bands: one image at 50-59,
one at 40-49, 26 at 30-39, 92 at 20-29.

| Split | Listed |
|---|---:|
| train | 92 |
| val | 11 |
| test | 17 |

Excluded: 147 unconfirmed or under adjudication, 12 already folded out of the
queue, 2 without any bird/head/eye shape.

**The score measures review value and correction effort, not detection
accuracy.** High scores usually mean the vendor boxes were wrong in that frame,
so never cite this list as evidence that the vendor model performed well.

## Where the photos are

Photos are not in the repository. Look up the `image_id` in
[registry.csv](../../registry.csv), then download the matching release:
`community-images-2026-10-24-v1` through `community-images-2026-10-25-v5`.

## The deduplicated queue

| Item | Count |
|---|---:|
| Images | 694 |
| Folded out | 158 |
| Queue | 536 |
| Folded groups | 42 |
| Candidate similarity groups (unfolded) | 101 |
| Folded images that were confirmed | 12 |

Key facts:

- **No folded image shares input pixels with its representative** (zero CHW hash
  collisions). They are similar frames of the same scene or burst, not byte
  duplicates.
- Folding requires each member to match its representative directly; there is no
  transitive collapsing that would squash a whole burst into one image.
- Groups never span the published train/val/test split (0 conflicts).
- Folding changes only the queue view; images, labels and revision history are
  untouched.

## Verify

```bash
python scripts/tools/verify_annotations.py
python -m unittest tests.test_published_exports -v
```

The digest of each list is recorded in the generating script output and in the
`digest` field of the dedupe file.
