# AI initial annotation and human review workflow v2

**English** | [简体中文](ai-annotation-workflow-v2.zh-CN.md)

Version 2.0, 2026-10-24. Applies to frozen 384×256 input labels. The schema remains `forest-bird-input-manual-v1`; this revision changes the workflow, not coordinates or training targets.

## Calibration and scale

Default to `STAGE=calibration`, `LIMIT=5`, `CHECKPOINT_EVERY=5`, and `BULK_APPROVED=false`. This grants five new images for workflow verification, not a full rerun. Do not increase the limit, select all_pending, or start another batch automatically.

Preserve existing labels and history. Produce a review list and overlays for the entire previous batch, including annotated items. Do not alter existing labels without explicit image IDs and rework authorization. After the new-image trial, stop for human calibration review.

Calibrate the first 40 images across available clear/small birds, occlusion, unavailable heads, blur, multiple birds, uncertain regions and negatives. Limit redundant burst frames and report missing categories honestly. A human inspects inputs before revealing AI labels. One human plus AI is AI initial annotation with human review, not two independent human annotators.

After human confirmation, the user can explicitly enable `STAGE=bulk`, `BULK_APPROVED=true`. Prefer LIMIT=20 with checkpoints every five images; all_pending requires an explicit full-run request. Routine checkpoints do not require separate approval; missing visual capability or failed calibration stops writes.

## Required per-image sequence

1. GET the current annotation and frozen identity. New images must be pending, revision 0 and unclaimed. Inspect the entire current input PNG for all birds and uncertain regions.
2. Inspect ordinary enlargements/crops when needed. Record view path, source PNG SHA-256, crop_xyxy, scale and output dimensions; verify the transform. Convert every coordinate back to 384×256.
3. Independently propose visible-bird/head boxes, eye centers, visibility, fallback target and a visible anchor. Annotate all locatable parts.
4. Save the proposal, then render a full-image overlay and relevant head close-ups from that exact proposal on that exact input. Ordinary Pillow drawing is sufficient; no additional vision model is required.
5. Actually inspect the overlays for missing birds, visible tails/feet/beaks, misplaced eyes, instance associations and anchors on background/branches. After edits, render and inspect the final proposal again. Creating a PNG alone is not visual checking.
6. POST validate and retain the full response including warnings. Resolve warnings against the image. Structural validity does not establish visual correctness.
7. Re-GET eligibility immediately before PUT with base_revision=0. GET after saving and compare complete content and identity before recording success.

Persist proposals, view records, visual checks and validation before PUT. Without actual visual self-checking, do not submit annotated or claim checking is complete; retain the proposal and explain the unfinished step.

Inspect every frame independently. Identical adjacent geometry triggers reinspection and an explicit confirmation record; it is not automatically an error. A shared burst is not sufficient justification. Do not perturb correct coordinates merely to avoid a duplicate warning.

## Eyes, visibility and status

Eye boxes default to null. Mark reliable centers; add a box only when this input supports its boundary. Never generate boxes with a fixed radius. Unlocalizable eyes get no eye point; anatomical side defaults to unknown when uncertain.

Head boxes include visible beaks; bird boxes include all visible tails/feet. Do not reconstruct hidden outlines. A reliable head/body fallback can be annotated. Use needs_adjudication for concrete uncertainty about identity, geometry or anchors, keeping only reliable parts.

Blur, small size and compression do not prove occlusion. Use unknown visibility and the appropriate reason where obstruction is unproven. Hidden does not mean every case of unclear detail. AI cannot write reviewed. Input clarity/localizability and actual camera autofocus are separate evidence.

## Save, recovery and accounting

Compare every annotation field except server-managed provenance and review; separately require review=null and verify provenance actor.id/kind, revision and parent_revision. Object key order is irrelevant; array contents and numeric values must match. The current validate endpoint returns valid/issues, not a normalized annotation. Compare the actual submitted proposal; do not assume unavailable response fields or ignore geometry/unknown fields.

The comparison includes every instance, eye, anchor, visibility, status, presence, input identity, preprocess_id and split=null. Revision/status/hash/actor.kind checks alone are insufficient.

After a PUT timeout or failed readback, persist save_unknown and query the server. Retry the same proposal only if the old revision and eligibility remain unchanged. An expected new revision with matching actor and complete content counts as saved; other new revisions are conflicts. Never force an overwrite with a newer base revision. If reconciliation is unavailable, preserve the unresolved record and pause writes.

Append ledger events with UTC time, attempt_id, actual views, viewed, overlay_checked, proposal/view/readback paths and hashes, base_revision, outcome and reason. Do not hard-code inspection flags. Reconcile checkpoints by unique image_id with saved, adjudication, skipped, conflict, retryable_failed, save_unknown and remaining IDs. Repair a missing ledger entry from confirmed server evidence before retrying writes.

Write checkpoints through a temporary file and atomic replacement. Preserve the original candidate list, stage, quota and IDs allocated to that quota. Continuations inherit the same quota; a new conversation does not grant another five images. Keep failed/unresolved work explicit. Export this run's exact successful image_id+revision pairs, not all work sharing an actor.

These are execution requirements, not a claim that historical run_helper.py/batch_worker.py has been repaired. New helpers may be written inside the new ai-runs directory. Preserve historical artifacts and application source, and never write SQLite directly. Audit old helper behavior before reusing its save logic.

## Human acceptance and reporting

Review all calibration images and any batch with critical errors, including annotated items. After calibration, review every test candidate, severe occlusion, multi-bird, negative/abstention and uncertain case; randomly inspect at least 20% of other training candidates. Critical errors return the whole batch for correction.

Report actual image viewing, overlay self-checking, structural validation, saving and human review separately. Do not equate saved with accurate or claim every image was enlarged without evidence. Record the model as unknown unless actual session configuration establishes its name.

Keep split=null. No training, distillation, Sony, remote tasks or publication is included.
