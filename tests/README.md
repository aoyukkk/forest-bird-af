# Tests

**English** | [简体中文](README.zh-CN.md)

```bash
python -m unittest discover -s tests -p "test_*.py"
```

| File | Covers |
|---|---|
| `test_annotator.py` | Store, concurrent claims, import, HTTP API |
| `test_dedupe.py` | Similarity groups, folding, undo, no label writes |
| `test_z8_review.py` | Review documents, baseline and diff, AI draft-only |
| `test_z8_training.py` | Target building, metric matching, derived supervision |
| `test_published_exports.py` | Contracts for published labels and split |
| `test_curation_exports.py` | Contracts for the queue and priority list |
| `test_confirmed_export.py` | Contracts for the confirmed label export |
| `test_remote_annotator.py` | Remote access and password gateway |
| `test_z8_probe_labels.py` | Native table lookup and candidate adaptation |

Publication tests use the standard library only; they need neither the vendor
package nor CUDA.

`test_repository_publication.py` checks lossless eye geometry, reproducible exports/checksums, links and the label-archive boundary. `test_training_output_guards.py` checks that moved training scripts still reject repository-local private outputs; it imports PyTorch but launches no GPU job. Full tests need Pillow, NumPy and PyTorch.


The YOLO route adds `test_competition_preservation.py` (spatial masks and known
absence), `test_bird_parts.py` (partial supervision, derived background,
augmentation geometry and unordered sparse distillation),
`test_bird_parts_preparation.py` (weak-head geometry) and
`test_public_community_training.py` (historical-test quarantine). Model tests
also need the pinned optional [YOLO dependencies](../requirements-yolo26.txt);
they run on CPU. The complete local run passed 176 tests.

`test_bird_regions.py` checks crop mapping, label-independent automatic regions and exact native B/H retention. `test_hard_context.py` checks protected background and the eye-budget/F1 selection tradeoff.


`test_bird_guidance.py` checks partial labels, duplicate candidates, abstention, predicted-only gates and auxiliary-region precedence; `test_bird_guidance_loss.py` checks localization-quality gradients and blur-to-unknown labels; `test_guidance_replay.py` checks fixed prediction/reference IDs and CPU-only replay.

`test_point_review.py` checks explicit human confirmation, draft-only edits, input/point-bound backups, safe HTML roundtrips, immutable views and human-export import guards.

`test_bird_surface.py` checks frozen parameters/BN/raw outputs, sparse positives, unknown supervision, explicit occluder gradients and multilevel-mask normalization. The latest local full run passed 176 tests.


`test_bird_residual.py` checks partial real labels, prediction-only pools, immutable RGB crops, capacity bounds and pairwise gradient direction. The latest complete local suite passed 176 tests.


`test_public_expansion.py` adds ten checks for contamination signatures, exclusive upstream emptiness, source-license filtering, partial targets, contour uncertainty, camera splits, matched positive sampling and JSON-safe calibration counts. Full local suite: 176 passed.

`test_main_background.py` adds seven checks for actual empty-loss gradients, missing-head masks, positive-region preservation, frozen BN, paired batch identity and rejecting harmful continuations. Full local suite: 176 passed.

`test_classification_guard.py` adds five checks for classification-only updates and raw-box identity, one-sided positive gradients, paired hard replay, per-frame preservation and non-mutating fit quarantine. Full local suite: 176 passed.

`test_information_diagnostic.py` covers dynamic input coordinates, consistent native center/box mapping, label-independent crops and group-paired gains.

`test_native_guidance.py` checks quality-class gradient direction, detached coordinate targets, unknown-eye masking and conservative promotion limits.

`test_native_point_review.py` adds six checks for image/point identity, draft rejection, exact-point surface versus eye truth, auxiliary/padding freeze, equal-weight control and known-eye error guards.
