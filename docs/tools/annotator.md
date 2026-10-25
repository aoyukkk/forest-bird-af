# Local annotation workspace

**English** | [简体中文](annotator.zh-CN.md)

For collaborators outside this computer, see [temporary remote review access](remote-review.md). The service and database stay local; a password gateway exposes a temporary HTTPS link without a custom domain.

A local browser tool for humans and AI to annotate the same frozen **384 × 256 Z8 simulation inputs**. It works without an external service, model API, training process or internet connection.

**Current default (2026-10-25):** the homepage now uses [Z8-assisted human correction](z8-review.md), with Z8 shapes visible and explicit confirmation. Old LLM records remain archived in `/annotate`. The precision-label editor and APIs below remain available at that historical entry.

## Run

Use Python 3.11+ with Pillow (already present in the local `machine` conda environment). The web server and AI client otherwise use the Python standard library; the interface has no CDN dependencies.

```powershell
python scripts/annotator/annotator.py init --workspace <local-label-folder> --runs <saved-prelabel-runs-folder>
python scripts/annotator/launch_annotator.py --workspace <local-label-folder>
```

Initialization compares the complete registry against saved runs, verifies each CHW buffer and frozen reference hash, and produces PNGs that round-trip to the exact inference input bytes. It preserves IDs, predictions and existing annotation revisions. New inputs can be imported with the same initialization command after updating the registry and saved runs.

The launcher starts a background service at `http://127.0.0.1:8765`, reuses a service belonging to the same workspace, and opens the browser. Use `--port` for another local port or `--no-open` to leave the browser unchanged. The service listens on loopback only. It remains running until the process stops or the computer restarts; rerun the launcher afterward.

## Deduplication (one-click duplicate marking)

The **Deduplicate** button is a single action: it marks the **current image** as a duplicate of
the **previous numbered image**, folds it out of the queue, and advances to the next visible
image. Labels, revision history and originals are untouched; the image is simply no longer
inspected twice.

| Button | Where | Effect |
|---|---|---|
| Deduplicate | header and the bottom bar ("Same as previous") | current image -> previous numbered image, fold and advance |
| Undo deduplication | header and the bottom bar | return the current image to the queue; enabled only for a folded image |
| Manage duplicates | header | rescan, expand similarity groups, keep an image, type a representative id |

- The first image has no predecessor, so the button is disabled there.
- If the previous image is itself folded, the action follows to its root, so no cycle appears.
- The scan in "Manage duplicates" is a conservative grouping: it only folds frames with strong
  evidence. Pose, defocus and occlusion changes stay visible, so a similarity group is still not
  a confirmed capture sequence.
- "Export confirmed usable records (deduplicated)" excludes folded images; the full export keeps
  every record.
- To see everything again, clear "Hide duplicates" or pick the "Duplicates" filter.

## Historical precision-label workflow (`/annotate`)

1. Pick an image in the queue. Filter by ID, batch, status, or images with no Z8 candidates. Predictions are hidden by default.
2. Use **B** to draw a visible-bird box, **H** for its head and **E** to click a visible eye center. Select the parent bird before adding its parts; create separate instances for additional birds.
3. Add an optional eye box only when the boundary is visible. Set anatomical eye side to unknown if uncertain. Never infer an occluded eye.
4. Set visibility, occluders and unavailable reasons. The automatic preferred target is eye → head → bird. An eye point can supply its focus anchor; use **P** to place an actually visible head/body anchor. Do not mechanically use the center of a box that contains branches.
5. Draw **U** uncertain regions, or explicitly choose **Checked: no bird** after inspecting the whole image. Uninspected and uncertain images are not negative examples.
6. Submit the initial annotation. Human review is a separate step; self-review is recorded as non-independent. AI initial annotations cannot directly become human-reviewed.

Selected shapes can be moved and resized; exact coordinates are editable. **V** selects, **F** fits, the mouse wheel zooms, Space+drag pans, Ctrl+Z undoes, Ctrl+Shift+Z redoes, Delete removes selected geometry, arrow keys navigate, Enter submits and advances. Text fields retain normal keyboard editing.

Drafts autosave to SQLite after a short pause. Every successful save adds an immutable revision. Revisions can be restored as a new draft. A local unsaved-draft cache helps recover a refresh or connection failure. Concurrent writes return a conflict; the tool preserves local edits instead of overwriting a newer record.

The original image opens as a read-only reference. Consulting it is recorded. **Labels in this workspace describe the 384×256 image, not full-resolution ground truth.** Seeing an eye only in the reference does not make it visible in the input. Existing full-resolution annotation protocols remain separate.

Z8 proposals are a separate read-only layer. Slots 0/4 are bird-region variants, 1 is head, 2/3 are directional eye candidates, 5 is an auxiliary body-associated region. Their original training boundaries are not fully recovered. A user may adopt a candidate individually as a bird/head box or eye point and correct it; there is no bulk promotion to ground truth.

## AI API and CLI

For Gemini in local Antigravity, use the [first-pass prompt and operator guide](gemini-first-pass.md) and [workflow v2](../overview/ai-annotation-workflow-v2.md) (five-image calibration, actual final-overlay inspection, nullable eye boxes, full readback comparison, preserved existing labels and human calibration before scaling).

The browser and AI use the same REST API and validation. Actor IDs are local provenance labels, not authenticated identities. The loopback service is intended for trusted local users and AI processes.

```powershell
python scripts/annotator/annotator_client.py help
python scripts/annotator/annotator_client.py schema
python scripts/annotator/annotator_client.py list
python scripts/annotator/annotator_client.py claim --zero-only
python scripts/annotator/annotator_client.py get fb_0008 --output edit.json
python scripts/annotator/annotator_client.py image fb_0008 --output input.png
# Edit the annotation object in edit.json, retaining revision and image identity.
python scripts/annotator/annotator_client.py --actor vision-local save edit.json
python scripts/annotator/annotator_client.py export --scope all --output labels.jsonl
```

An AI client must use `actor.kind="ai"`; the CLI enforces this default. The tool provides images and annotation I/O; it does not call an external vision model automatically. AI agents inspect the PNG and write their own initial labels.

An AI operating the browser can select **AI** under **Help → Operator type** and set an actor ID. Human users can set their own ID there too, including in narrow browser panels.

| Endpoint | Purpose |
|---|---|
| `GET /api/help` | Discover the local API |
| `GET /api/schema` | Machine-readable part vocabulary and instance/eye/uncertain templates |
| `GET /api/dataset` | Queue, status and advisory task claims |
| `GET /api/images/{id}` | Frozen image identity and raw proposals |
| `GET /api/images/{id}/png` | Exact input PNG |
| `GET /api/images/{id}/reference` | Read-only fixed reference |
| `GET /api/annotations/{id}` | Current annotation and revision |
| `PUT /api/annotations/{id}` | Save with `base_revision`, `annotation` and `actor` |
| `POST /api/validate` | Check an annotation without saving |
| `POST /api/import` | Atomically save a batch of revision-checked records |
| `POST /api/claim` | Claim the next pending/draft task for 30–3600 seconds |
| `POST /api/release-claim` | Release the caller's advisory claim |
| `GET /api/history/{id}` | Immutable revision history |
| `GET /api/export?scope=all` | Native JSONL project records |
| `GET /api/export?scope=complete` | Initial annotations and reviewed records only |
| `GET /api/export?scope=reviewed` | Human-reviewed records only |
| `POST /api/backup` | Create a consistent local SQLite snapshot |

Claims help AI workers pick different images; they are advisory, not locks. The revision check protects saves. AI clients should release a claim when finished or rely on its expiry.

```json
{
  "base_revision": 0,
  "actor": {"id": "vision-local", "kind": "ai"},
  "annotation": "Use the full annotation object returned by GET, then edit it"
}
```

The illustrative `annotation` string above is not a valid annotation payload. Start with the real object from GET. A stale base revision returns HTTP 409. Batch import validates every record before writing any.

## Data model and storage

Schema: `forest-bird-input-manual-v1`. Coordinates are finite input pixels, xyxy boxes with an exclusive bottom-right boundary. Points satisfy `0≤x<384`, `0≤y<256`. Identity includes PNG SHA-256, saved CHW SHA-256 and the exact preprocessing ID.

Each bird has a stable instance ID, visible-bird/head boxes, up to two visible eye centers with optional boxes, visibility/occlusion attributes, `af_reference_target_input`, and `af_anchor_input_xy`. Uncertain regions are separate. `split` stays null. Statuses are pending → draft → annotated → reviewed, with needs_adjudication for unresolved cases. Any interface edit returns a submitted record to draft; review cannot silently include unsaved content changes.

The original-review schema uses `af_reference_target_original` and `af_anchor_original_xy`; this input schema deliberately uses different names and does not convert input visibility into original-image visibility.

```text
<workspace>/
  images/fb_0001.png ...       frozen 384×256 input copies
  annotations.sqlite3        current labels + every saved revision
  import-validation.json     full input import check
  backups/*.sqlite3          consistent database snapshots
  server-process.json        process and local URL
  server.stdout.log
  server.stderr.log
```

Export/import preserves native JSONL, including points, associations, unknowns and revisions. Training-format conversion is intentionally a later adapter; original slot boundaries are not sufficiently established for automatic training-label generation. Empty templates, raw Z8 proposals and tool tests are not manual ground truth.

To restore a database snapshot, first stop this workspace's service, retain the current database and any WAL/SHM files together as a recovery copy, and restore the snapshot into a separate workspace before replacing anything. Copy the frozen `images` directory alongside it. A whole-workspace copy is the simplest portable backup; original references remain optional local paths.

## Verification

```powershell
python -m unittest discover -s tests -p test_annotator.py -v
node --check src/forest_bird_annotator/web/app.js
python scripts/tools/verify_repo.py
git diff --check
```

Tests cover conflicting human/AI writes, atomic batch rollback, input hash/pixel identity, reviewed-state guards, missing focus geometry, draft/negative separation, task claims and database snapshots. UI smoke checks should use a separate workspace so test marks never enter the user's dataset.
