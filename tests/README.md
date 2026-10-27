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
they run on CPU. The complete local run passed 135 tests.

`test_bird_regions.py` checks crop mapping, label-independent automatic regions and exact native B/H retention. `test_hard_context.py` checks protected background and the eye-budget/F1 selection tradeoff.


`test_bird_guidance.py` checks partial labels, duplicate candidates, abstention, predicted-only gates and auxiliary-region precedence; `test_bird_guidance_loss.py` checks localization-quality gradients and blur-to-unknown labels; `test_guidance_replay.py` checks fixed prediction/reference IDs and CPU-only replay.

`test_point_review.py` checks explicit human confirmation, draft-only edits, input/point-bound backups, safe HTML roundtrips, immutable views and human-export import guards.

`test_bird_surface.py` checks frozen parameters/BN/raw outputs, sparse positives, unknown supervision, explicit occluder gradients and multilevel-mask normalization. The latest local full run passed 135 tests.
