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
