# Data: photographs, labels and splits

**English** | [简体中文](README.zh-CN.md)

## Choose a dataset view

| Need | Entry |
|---|---|
| All human-confirmed labels | [547 confirmed records](annotations-2026-10-25/README.md) |
| Training/validation/test assignment | [535 usable records, 375/80/80 split](annotations-2026-10-25/splits/evaluation-split-v1.json) |
| Complete review snapshot, including drafts | [694 source records](annotations-2026-10-25/labels/community-corrections-v1.jsonl) |
| Stable image IDs and hashes | [registry.csv](registry.csv) |
| Duplicate handling and priority list | [Curation guide](annotations-2026-10-25/docs/CURATION.md) |

## Image downloads

Photographs and exact input PNG/CHW buffers are release assets, not Git files.
Download all five batches for **694 unique assets**. Each release has
`SHA256SUMS.txt`; [releases.json](releases.json) lists asset sizes and hashes.

| Batch | IDs | Images | Download |
|---|---|---:|---|
| [01](community-2026-10-24/README.md) | fb_0001–fb_0296 | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| [02](community-2026-10-24-batch02/README.md) | fb_0297–fb_0523 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |
| [03](community-2026-10-24-batch03/README.md) | fb_0524–fb_0570 | 47 | [v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3) |
| [04](community-2026-10-24-batch04/README.md) | fb_0571–fb_0634 | 64 | [v0.4](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v4) |
| [05](community-2026-10-25-batch05/README.md) | fb_0635–fb_0694 | 60 | [v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5) |

For label/point evaluation, use the `z8-inputs-384x256-*.zip` assets. Do not apply
384×256 label coordinates directly to original-resolution photographs. NEF
review inputs use the explicitly documented camera-embedded JPEG representation.

## Review status

The active deduplicated queue is **535 confirmed + 1 adjudication item**.
Another 12 confirmed and 146 draft records are folded duplicates, retained for
history; drafts are not negatives or a new annotation backlog. Use JSONL to
preserve eye points and partial labels. COCO/YOLO views are not complete BHE truth.

The [292-row first contribution register](contributions-2026-10-23/) and
[CUB calibration metadata](calibration-200/) are historical, separate datasets.
New imports must append after the actual maximum ID in the cumulative register.

## Rights

Photographers retain copyrights; see the [photo terms](community-2026-10-24/README.md#rights).
Documentation/annotation metadata use CC BY 4.0, not a blanket image license.
CUB follows its own source terms.
