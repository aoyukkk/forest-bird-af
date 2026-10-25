# Annotation service source

**English** | [简体中文](README.zh-CN.md)

| Module | Role |
|---|---|
| `server.py` | HTTP service and routing |
| `store.py` | SQLite storage, revisions, concurrent claims |
| `z8_review.py` | Z8-assisted review documents, baseline and per-box diff |
| `dedupe.py` | Similarity groups, queue folding and undo; writes only `dedupe/` |
| `importer.py` | Import frozen 384 x 256 inputs and verify hashes |
| `schema.py` | Legacy precision-label validation |
| `remote.py` | Remote access password gateway |
| `web/` | Build-free front end: `z8-review.*` is the default, `index.html`/`app.js` the legacy editor |

See [annotator](../../docs/tools/annotator.md) to run it.
