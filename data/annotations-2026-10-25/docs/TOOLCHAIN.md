# Annotation toolchain and reviewed data

[简体中文](TOOLCHAIN.zh-CN.md) | **English**

This page documents how one photo becomes one trainable label record, so the
tooling can be reproduced and not only its output.

## Pieces

| Piece | Location | Role |
|---|---|---|
| Annotation service | `src/forest_bird_annotator/` | Local HTTP service; humans and AI share one API |
| Pages | `src/forest_bird_annotator/web/` | Build-free browser editor, Simplified Chinese by default |
| Launchers | `scripts/annotator/annotator.py`, `launch_annotator.py` | Initialise a workspace, start the service |
| Importer | `annotator.py` -> `importer.py` | Import frozen 384 x 256 inputs and verify hashes |
| Dedupe | `dedupe.py` + `scripts/annotator/dedupe_annotator.py` | Reversible queue folding, never writes labels |
| Exporters | `scripts/publish/export_z8_labels.py` and friends | Production database to publishable files |

## Run it

Python 3.11+ and Pillow are enough; no Node, Docker or online service.

```bash
python scripts/annotator/annotator.py init --workspace <workspace> --runs <completed prelabel run dir>
python scripts/annotator/launch_annotator.py --workspace <workspace>
```

Open `http://127.0.0.1:8765`. The workspace gains `annotations.sqlite3`,
`images/`, `backups/` and `dedupe/`. The database stays local; `*.sqlite3` is
gitignored.

## Data flow

```text
original photo + release copy
   -> fixed preprocessing review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1
        -> 384 x 256 RGB PNG + 3 x 384 x 256 CHW bytes, each with SHA-256
             -> frozen vendor candidates (never trained on)
                  -> human review: B bird / H head / E eye point / R eye box / U uncertain
                       -> z8_reviews + z8_review_history, one row per revision
                            -> export_z8_labels.py -> community-corrections-v1.jsonl
                                 -> export_split_manifest.py -> evaluation-split-v1.json
```

## Fields

- `kind`: `bird`, `head`, `eye`, `auxiliary`, `uncertain`. `auxiliary` is a vendor
  auxiliary region and is **not** bird truth.
- Geometry: `xyxy` half-open boxes or eye-centre `point_xy` on the 384 x 256
  input; floats are legal, out-of-range values are rejected.
- `status`: `draft` -> `confirmed`; disagreements become `needs_adjudication`.
- `decision`: `correct`, `partial_error`, `error`; every revision keeps before
  and after values.
- Paging, opening and autosave never count as confirmation.

## Dedupe

The header **Deduplicate** button folds the current image into the previous
numbered image, removes it from the queue and advances; **Undo deduplication**
returns it. Full behaviour is in
[the annotator guide](../../../docs/tools/annotator.md#deduplication-one-click-duplicate-marking).

The resulting queue is published as [dedupe-queue-v1.json](../curation/dedupe-queue-v1.json):
158 of 694 folded, 536 in the queue, 42 groups, all of them similar frames rather
than byte duplicates.

## Export formats

Besides the JSONL and JSON here, `scripts/publish/export_label_formats.py` converts any
record:

```bash
python scripts/publish/export_label_formats.py --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl --image fb_0241 --output <dir>
```

It writes `<id>.coco.json`, `<id>.yolo.txt` and `<id>.json`. Categories are fixed
to `bird`/`head`/`eye`; an eye point without a visible boundary becomes a 12 x 12
box flagged `eye_center_boxed` in COCO `source`. Do not read that box as a
human-measured eye size.

## Licence and scope

Code is Apache-2.0, annotation data CC BY 4.0, photo copyrights stay with the
photographers. Labels describe the 384 x 256 input only; they are neither
original-image truth nor in-camera focus results.
