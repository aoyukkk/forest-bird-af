# Human-reviewed bird labels

**English** | [简体中文](README.zh-CN.md)

**547 confirmed · 535 deduplicated usable · 384×256 coordinates**

| Need | File |
|---|---|
| Complete confirmed geometry, including eye points | [confirmed.jsonl](confirmed/confirmed.jsonl) |
| CSV, measured-box views and point sidecars | [Format guide](confirmed/README.md) |
| All 694 records, including unconfirmed history | [Source snapshot](labels/community-corrections-v1.jsonl) |
| Frozen 375/80/80 split | [Evaluation split](splits/evaluation-split-v1.json) |
| Duplicate decisions and browsing priority | [Curation guide](docs/CURATION.md) |
| Schema, status and annotation toolchain | [Detailed documentation](docs/README.md) |
| Corresponding photographs and input PNGs | [Images](../README.md#image-downloads) |

JSONL preserves original points, boxes and IDs. Point-only eyes never acquire
fixed-size boxes. COCO/YOLO are partial box views, not complete standalone BHE
targets; drafts and unknown parts are not negatives. The 12 folded confirmed
records remain in the full export. Use the frozen split for 535 usable records.
These are Z8-assisted human labels, not blinded camera autofocus truth.
