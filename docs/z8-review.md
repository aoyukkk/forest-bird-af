# Z8-assisted human correction

**English** | [简体中文](z8-review.zh-CN.md)

This is the default annotation homepage from 2026-10-25. Open `http://127.0.0.1:8765/` and review frozen Z8 proposals image by image. Previous LLM annotations and revisions remain in `/annotate`; they are excluded from this workflow's starting shapes.

## Review

1. Z8 shapes are visible by default. Inspect the entire 384×256 image, including missed birds and parts outside existing boxes. Original slots remain visible; slot 5 is auxiliary.
2. If everything is correct, select **Confirm & next** or press Enter. Viewing, navigation and autosave never confirm correctness.
3. Drag boxes/corners or edit coordinates. Delete false positives. **B** adds a bird box, **H** a head box, **E** a visible eye center, **R** an eye box only when its boundary is clear. Label every identifiable part without inferring hidden eyes or inventing fixed-size eye boxes.
4. Confirm corrections. At least one unchanged original shape plus changes becomes **Z8 partly wrong**. No unchanged original shapes, or adding missed targets to an empty baseline, becomes **Z8 wrong**. This classification describes shape changes, not severity.
5. No proposals does not mean no bird. Add missed targets; use **Confirm no bird** only after inspecting the whole image. Use **U** for uncertain geometry and **Uncertain & next** for unresolved cases, which are excluded from confirmed exports.

Ctrl+Z undoes, Ctrl+Shift+Z redoes, wheel zooms, Space+drag pans, F fits the image. Arrow keys only navigate. Restoring the Z8 baseline creates a draft without deleting history or confirming it.

**Batch deletion:** in **V Select / edit** mode, drag from empty space to fully enclose boxes; eye points only need to lie inside the selection. On release, check the highlighted shapes and the count on **Delete selected**, then press **Delete** or click that button. One **Ctrl+Z** restores the entire batch. **Shift+drag** adds to the selection and can start inside an existing shape; dragging a shape normally still moves or resizes it. **Esc** clears selection. Selection alone neither edits nor confirms annotations; deletion retains the frozen baseline and per-item correction history.

**Clear all shapes:** click the toolbar button without selecting anything to clear every box and eye point in the current image, retain notes and presence, and return to V. If the original-baseline overlay was visible, it is hidden; the frozen baseline remains unchanged. Clearing autosaves a draft without confirming absence or navigating. One Ctrl+Z restores the entire batch; Ctrl+Shift+Z redoes it. The button is disabled on empty images.

**Continuous annotation:** the **Continuous B → H → E** switch below the toolbar defaults on and remembers the preference in this browser. Entering an image without any boxes or points selects B; existing annotations start in V. A newly drawn bird box advances to H, a head box to E, and an eye point returns to V. Press B for another bird. Press V to finish when a part is unclear, or H/E to skip to an identifiable part; completing every part is optional. With the switch off, each drawing returns to V. Deleting all false positives does not activate B, so no-bird confirmation remains available. Tool changes and this preference never confirm images.

**One-click deduplication:** when the current image repeats the previous numbered image, click **Deduplicate** in the header or **Same as previous** at the bottom. The tool resolves the predecessor from all image IDs, including hidden ones, excludes the current image and advances to the next non-excluded image. No ID entry or confirmation dialog is needed. The first image disables the button. Consecutive duplicates resolve to a retained representative. Existing annotations remain unchanged; exclusion does not confirm correctness or absence.

**Duplicate management:** open **Manage duplicates** in the header. **Hide duplicates** defaults on; queue navigation and confirmation skip collapsed images. Disable it to show every record, or use the **Duplicates** filter and ID search to access hidden images. Confirmed images participate, while retaining their individual labels, status and revision histories. **Export confirmed usable records (deduplicated)** excludes duplicates; archival confirmed/all exports retain every record. Queue progress follows the current hiding preference; the dialog also reports the total confirmed count. Scanning never switches the active image unexpectedly.

**Rescan all images** uses the CPU to compare frozen 384×256 inputs after a database backup. It checks hashes, color, global structure, local differences and sharpness, plus human-annotated regions when available. Each collapsed member must match its representative directly; confirmed records take priority. Frames with substantial changes remain visible. Similarity families are engineering suggestions, not human-confirmed capture sequences or final training splits. Expand families for thumbnails. **Keep this image visible** reverses hiding and survives rescans. Alternatively enter a representative ID and use **Mark this image as duplicate**.

`GET /api/z8-review/export?scope=usable` exports confirmed non-duplicate records; `confirmed/all` retain archival semantics.

Grouping is stored in workspace `dedupe/current.json` and immutable run receipts. No photographs or annotation rows are deleted, modified or transferred. Adding or replacing inputs invalidates the old hiding map until rescanning. CLI: `python scripts/dedupe_annotator.py --workspace <workspace>`. `GET /api/z8-review/dedupe` reads the view; `POST` accepts `action=scan`, `action=previous` with `image_id` (one-click previous), or `action=keep/hide` with `image_id` (hide also requires `representative`).

Use **View original reference** to open the read-only reference image, then explicitly tick **Original reference consulted** if appropriate. Opening the dialog does not confirm the review; coordinates still describe the 384×256 input.

Edits autosave. Editing a confirmed image returns it to draft. Unsaved local drafts can be recovered after connection loss or refresh. On conflict, download the draft and load the current revision. Set a reviewer ID, switch languages and export from the header.

**IDs:** `fb_0496` identifies an image asset; `p0/p1…` index its frozen Z8 proposal list; `n1/n2…` identify newly drawn shapes. None is automatically a bird identity. `slot 0…5` identifies the native class. One bird can have multiple proposals, and one slot can occur on several birds. The correction schema does not yet contain bird-instance associations; multi-bird AF evaluation needs a separate part-association step.

## Records

Schema `forest-bird-z8-correction-v1` is separate from historical precision labels (`forest-bird-input-manual-v1`). Frozen input identity and raw Z8 predictions are retained. Each revision records retained shapes, before/after changes, additions, removals, affected parts, actor and time.

- **Confirmed** exports retain accepted, partially wrong and wrong images.
- **All saved** includes drafts and unresolved records. Untouched images are not fabricated as empty annotations.
- **Uncertain** exports isolate unresolved judgments.

Colors follow native slots; manual kinds and original slots remain distinct. Auxiliary shapes are not automatic bird training labels. Bird/part association and training-format conversion need a later adapter; correction exports are not final YOLO training labels. Keep accepted examples for capability retention and regression checks.

These are **Z8-assisted reviews**, not independent blind test labels. Use a separate hidden-proposal precision-labeling workflow for independent evaluation. Coordinates and visibility describe input pixels, not actual camera focus.

## Human and AI API

Humans and AI read the same records. AI may save drafts but cannot confirm correctness; this human-review workflow does not automatically invoke an LLM.

| Endpoint | Purpose |
|---|---|
| `GET /api/z8-review/schema` | Fields, kinds and states |
| `GET /api/z8-review/dataset` | Correction queue |
| `GET /api/z8-review/{id}` | Frozen baseline, review and revision |
| `PUT /api/z8-review/{id}` | Submit `base_revision`, full `review`, `actor`, `action` |
| `GET /api/z8-review/{id}/history` | Immutable correction history |
| `GET /api/z8-review/export?scope=confirmed` | Confirmed JSONL |
| `GET /api/z8-review/export?scope=all` | All saved records |
| `GET /api/z8-review/export?scope=uncertain` | Unresolved records |

Actions are `draft / confirm / uncertain`; the last two require a human actor. GET before PUT, preserve frozen identity/baseline fields and submit the current revision. Conflicts return 409. Original shape IDs are `p0…`; new IDs are `n1…`, advancing `next_id` without reuse. AI must use `actor.kind=ai` rather than impersonating a human.

The existing workspace database gains `z8_reviews` and `z8_review_history` tables. Backups include both workflows. UI acceptance tests use a separate workspace.
