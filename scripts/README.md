# Scripts

**English** | [简体中文](README.zh-CN.md)

Grouped by task. Everything runs on the standard library or the environment
described in `docs/training/README.md`; scripts that need the vendor model
package and CUDA expect you to bring your own, since the repository holds no
vendor assets.

## pipeline/ — photo to prelabel

| Script | Purpose |
|---|---|
| `prepare_community_release.py` | Stable ID registry and source mapping |
| `extract_verified_rar.py` / `extract_verified_zip.py` | Extract, verify every file, then delete the archive |
| `sanitize_jpeg.py` | Strip JPEG metadata, keep sampling, colour and orientation |
| `finalize_community_release.py` | Image integrity, NEF review images, public copy packaging |
| `nef_review.py` | Verify compressed TIFF payload and extract the embedded JPEG |
| `z8_input.py` / `package_z8_inputs.py` | Build the fixed 384 x 256 simulation input |
| `prelabel_community.py` | Vendor post-processing inference |
| `validate_e7_backend.py` / `validate_e7_batch.py` | Model identity, CPU/GPU parity, batch config |
| `package_prelabels.py` / `build_review_page.py` | Package candidates and the review page |

## annotator/ — local annotation service

| Script | Purpose |
|---|---|
| `annotator.py` | Initialise a workspace, import frozen inputs |
| `launch_annotator.py` | Start the local service (default 127.0.0.1:8765) |
| `remote_annotator.py` / `share_annotator.py` | Remote collaborative access |
| `dedupe_annotator.py` | Similarity scan and queue folding |
| `verify_annotator_workspace.py` | Workspace structure and hash checks |

## training/ — native heads and YOLO26 parts

`prepare_z8_training.py`, `train_z8_heads.py`, `evaluate_z8_training.py`,
`probe_z8_finetune.py`, `probe_z8_multibird.py`, `benchmark_z8_candidate.py`,
plus `z8_probe_labels.py`, `z8_trainable_heads.py`, `z8_training_targets.py` and
`e7_backend.py`. Method and results: [training](../docs/training/README.md).

The independent [YOLO26 route](../docs/training/yolo26-parts.md) uses
`prepare_public_community.py`, `prepare_bird_parts.py`, `import_nabirds_parts.py`,
`prepare_yolo26_weights.py`, `bird_parts_model.py`, `train_bird_parts.py` and
`evaluate_bird_parts.py` and `predict_bird_parts.py`. It supports B/H boxes and eye points without vendor
weights; the comparison evaluator additionally needs your local native package.

## publish/ — database to public files

| Script | Output |
|---|---|
| `export_confirmed_labels.py` | Every human-confirmed label (JSONL/CSV/COCO/YOLO) |
| `export_z8_labels.py` | 694 per-image records |
| `export_split_manifest.py` | Frozen train/val/test split |
| `export_dedupe_queue.py` | Deduplicated queue |
| `export_best_images.py` | Review-priority ordering |
| `export_label_formats.py` | COCO/YOLO for one record |

## tools/ — verification and diagnostics

| Script | Purpose |
|---|---|
| `verify_repo.py` | Scan the tree for vendor assets or photos |
| `verify_annotations.py` | Check labels, splits, queue, confirmed export, private fields |
| `verify_links.py` | Check relative Markdown file targets after directory changes |
| `verify_review_page.mjs` | Static check of the review page |
| `compare_saved_decoders.py` | Compare two decoder outputs |

The follow-up adds `evaluate_bird_regions.py`, `bird_parts_regions.py`, `prepare_hard_bird_context.py`, `hard_bird_context.py`, `evaluate_bird_hybrid.py` and `predict_bird_hybrid.py`. See [input/context results](../docs/training/input-context-2026-10-26.md).


Guidance tools: `bird_guidance_metrics.py` (standard-library top-one proxies), `evaluate_guidance_predictions.py` (CPU cache replay), `train_bird_guidance.py` (matched continuations), and `predict_bird_guidance.py` (one/two independent models without vendor code). See [guidance evaluation](../docs/training/guidance-2026-10-26.md).

Point review adds `annotator/build_point_review.py`, `point_review_core.js`, `point_review_template.html` and `annotator/import_point_review.py`. The importer validates exact input/point identity, complete revisions and explicit human confirmation, preserving the original export outside Git. Generated HTML and embedded photos also stay outside Git. `training/bird_guidance_fallback.py` reproduces a rejected abstention-only capture rule; it is not enabled in inference defaults. [Human results and tools](../docs/training/point-review-2026-10-26.md).

Surface experiments add `training/bird_surface.py`, `prepare_bird_surface.py`, `train_bird_surface.py` and `predict_bird_surface.py`. They bind CUB masks, freeze the original model and train a separate coarse head. [Protocol and commands](../docs/training/surface-2026-10-27.md).

RGB/context ranking adds `training/bird_residual.py`, `prepare_bird_residual.py`, `train_bird_residual.py`, `predict_bird_residual.py` and `benchmark_bird_residual.py`. [Partial labels, matched comparisons and commands](../docs/training/residual-2026-10-27.md).

Public expansion adds `training/prepare_coco_cct.py`, `admit_public_expansion.py`, `prepare_expansion_ranker.py`, `train_expansion_ranker.py` and `evaluate_expansion_ranker.py`. [Source rights, partial targets and commands](../docs/training/data-expansion-2026-10-27.md).
