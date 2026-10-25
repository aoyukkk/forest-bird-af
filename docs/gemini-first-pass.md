# First-pass annotation with Gemini in Antigravity (workflow v2)

**English** | [简体中文](gemini-first-pass.zh-CN.md) · [Full prompt](gemini-first-pass-prompt.md)

Gemini inspects each input and its final overlay before submitting AI initial labels. A human then edits and reviews them. Follow [workflow v2](ai-annotation-workflow-v2.md). Default: preserve existing labels, prepare the entire previous batch for review and verify five new images.

## Prepare

Open the repository in a **local** Antigravity conversation, select your Gemini model, and provide access to the repository and annotation workspace. The session must support terminal execution and actual image viewing. A remote session's localhost is not this computer.

The repository contains `scripts/annotator_client.py`; the separate annotation workspace contains `images/`, `annotations.sqlite3` and `import-validation.json`. The firmware directory is not required. If access to the annotation folder is blocked, grant that folder access rather than disabling global protections. Google documents project-folder restrictions and platform differences in its [agent settings](https://antigravity.google/docs/agent-settings).

Google provides image attachment/preview features, but actual tools vary by installed surface/session. The prompt checks visual capability before writing; a terminal file read alone is insufficient. See the official [changelog](https://antigravity.google/docs/changelog).

## Start the existing workspace

Use your configured launcher or:

```powershell
& "<PYTHON_EXE>" "<REPO_ROOT>/scripts/launch_annotator.py" --workspace "<ANNOTATION_WORKSPACE>" --no-open
Invoke-RestMethod http://127.0.0.1:8765/api/health
```

Expect `ok=true`, the actual image count and schema `forest-bird-input-manual-v1`. Do not run initialization again to replace the workspace. Port 8766 was used for separate UI tests; production uses 8765.

## Send the prompt

Replace the paths in the [full prompt](gemini-first-pass-prompt.md), set REVIEW_EXISTING_RUN to the prior run directory or leave it empty, and paste the complete block. Defaults are STAGE=calibration, LIMIT=5, CHECKPOINT_EVERY=5 and BULK_APPROVED=false. Preserve existing labels and generate review materials for the entire previous batch, including annotated items.

After the five-image trial, stop for human review. Complete first-40 rule calibration and receive explicit human confirmation before setting STAGE=bulk and BULK_APPROVED=true. Prefer LIMIT=20; all_pending requires an explicit full-run request. A continuation retains the original quota and allocated IDs rather than granting five more. This is not a train/test split. Routine checkpoints require no additional approval. Use the API for writes and the UI for review.

```powershell
Set-Location "<REPO_ROOT>"
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 schema
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 list --status pending --limit 20
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 get fb_0008 --output "<RUN_DIR>/fb_0008-edit.json"
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 image fb_0008 --output "<RUN_DIR>/fb_0008.png"
# Inspect actual pixels and edit annotation first; never submit an unchanged template.
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 save "<RUN_DIR>/fb_0008-edit.json"
```

CLI `list --limit 20` displays only 20 entries. Read `GET /api/dataset` for the whole queue. The generic `claim` endpoint may return a draft; the prompt deliberately uses explicit pending/revision-0 filtering instead.

## Outputs and human review

The agent creates a fresh `WORKSPACE/ai-runs/gemini-pass1-v2-<UTC timestamp>/` with `run.json`, `ledger.jsonl`, `checkpoint.json`, cached inputs, proposals, readbacks and its run export. Labels themselves stay in the existing database, attributed to `gemini-antigravity-pass1-v2` with actor kind AI.

Persist final proposals before PUT, together with exact input/view hashes and transforms, inspected overlays, full validation responses and warnings. Re-render and actually inspect overlays after coordinate edits. Eye boxes default to null; no uniform 4x4 boxes. Identical adjacent geometry requires explicit current-image reinspection. Compare complete saved business content and actor identity, not just revision/status/hash. Historical helpers must satisfy v2 before reuse.

Clear completed images become annotated. Important uncertainty becomes needs_adjudication. Neither automatically becomes human-reviewed. The first pass leaves original-reference consultation false and Z8 review unassessed because it is independent of those references.

In the [local UI](http://127.0.0.1:8765):

1. Set your own human actor ID under Help.
2. Review every image in calibration and any previous batch with critical errors, including annotated. Independently inspect the input before revealing AI labels.
3. Inspect missing birds, genuine eye visibility, visible beaks/tails/feet, instance association and anchors on branches. Initially keep Z8 proposals hidden; turn them on when comparison is useful.
4. Edit as needed. Edits return the record to draft; resubmit, return by image ID if auto-advance moved away, then mark reviewed.

The focus priority eye → head → bird does not replace full visible-part annotation. A reliable head/body fallback can be annotated without eyes. One human reviewing AI labels is not independent double-human annotation. Saving and geometric validation do not establish visual correctness.

## Interruption and continuation

| Situation | Action |
|---|---|
| No actual image viewer | Stop label writes and fix visual access |
| Local service unavailable | Restart the existing workspace, not a replacement dataset |
| HTTP 409 | Preserve proposal, log conflict and skip; do not overwrite |
| Save timed out or readback failed | Record save_unknown and reconcile complete content before retrying |
| Coordinate error | Reinspect that image; do not invent geometry |
| Context/quota exhausted | Save checkpoint and remaining IDs, then continue in a new session |
| Existing draft or label | Skip by default; authorize specific rework separately |

Continuation message:

```text
Continue the same workflow-v2 calibration run without granting a new quota. Read the full revised prompt and the run.json, ledger.jsonl and checkpoint.json in the directory I specify.
Retain STAGE=calibration, BULK_APPROVED=false and the original IDs allocated to the five-image quota. Process only unfinished allocated IDs still pending at revision 0 and unclaimed; do not select five more.
Reconcile save_unknown, failures and server saves missing from the ledger first. Preserve all drafts, saved/adjudication labels and human changes. Never submit a duplicate save.
Inspect each current image and its final overlays; compare complete saved content. Use actor=gemini-antigravity-pass1-v2. Stop after the allocated trial for human review, without scaling automatically.
If the specified run is historical v1, use it only to prepare whole-batch review materials, then create a separate v2 five-image trial. Do not modify historical artifacts or reuse noncompliant save logic.
```

This continuation deliberately does not overwrite interrupted drafts. List them for separate follow-up.

## Export

Use Export/backup in the UI, or:

```powershell
& "<PYTHON_EXE>" "<REPO_ROOT>/scripts/annotator_client.py" export --scope all --output "<ANNOTATION_WORKSPACE>/exports/after-gemini-all.jsonl"
& "<PYTHON_EXE>" "<REPO_ROOT>/scripts/annotator_client.py" export --scope reviewed --output "<ANNOTATION_WORKSPACE>/exports/human-reviewed.jsonl"
```

Native JSONL preserves instances, eye points, visibility, provenance and revisions. It is not automatically converted into the original six-slot training targets; that adapter follows human review and resolution of the original target conventions.
