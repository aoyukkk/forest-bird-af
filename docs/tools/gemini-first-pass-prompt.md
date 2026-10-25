# Gemini first-pass annotation prompt v2

**English** | [简体中文](gemini-first-pass-prompt.zh-CN.md) · [Operator guide](gemini-first-pass.md)

Replace the path placeholders and paste the complete block into a local Antigravity conversation using Gemini. Default: preserve existing labels, prepare their human-review materials and verify five new images.

```text
Execute an AI initial annotation pass for the local forest-bird autofocus dataset. I will review the results afterward. Follow workflow v2 rather than historical prompts or helper behavior.

CONFIGURATION
PROJECT = <REPO_ROOT>
PYTHON = <PYTHON_EXE>
WORKSPACE = <ANNOTATION_WORKSPACE>
BASE_URL = http://127.0.0.1:8765
ACTOR = gemini-antigravity-pass1-v2
STAGE = calibration
LIMIT = 5
CHECKPOINT_EVERY = 5
BULK_APPROVED = false
REVIEW_EXISTING_RUN = <PREVIOUS_RUN_OR_EMPTY>

SCOPE AND STAGE
Use only frozen 384x256 inputs in the existing annotation tool. Read PROJECT/AGENTS.md, docs/tools/annotator.md, docs/overview/ai-annotation-workflow-v2.md and this prompt. The later annotation-tool authorization supersedes historical documentation-only restrictions.
Default to five new calibration images. Do not increase the quota, select all_pending or automatically start another batch. After this trial, hand off for human review and stop. A continuation inherits the same quota and allocated image IDs; it does not grant five more images.
Only an explicit human confirmation of calibration and authorization to scale enables STAGE=bulk, BULK_APPROVED=true. Prefer LIMIT=20; use all_pending only for an explicit full-run request. Routine checkpoint saves do not require approval. A generic continue does not bypass pending calibration.
Use one sequential agent with actual image-viewing capability. No other annotating agents, training, distillation, Sony, remote servers, publication, additional vision services or API keys.
You may create run helpers under a new WORKSPACE/ai-runs directory. Do not change application source, historical run artifacts, originals, frozen predictions or SQLite directly. Historical run_helper.py/batch_worker.py is not automatically repaired by these instructions; audit every requirement before reusing save logic.

PREPARATION AND EXISTING WORK
GET /api/health, /api/schema, /api/help and /api/dataset. Confirm forest-bird-input-manual-v1 and actual queue counts. If down, use the existing PYTHON and scripts/annotator/launch_annotator.py --workspace WORKSPACE --no-open; do not initialize a replacement dataset or install tools.
POST /api/backup with {} and record the snapshot. Create ai-runs/gemini-pass1-v2-<UTC timestamp>/.
Write run.json with actual model name (unknown unless established by session configuration), actor, input scale, time, workspace ID, stage, quota, bulk approval, complete eligible list, allocated new-image IDs and prior-run review scope.
If REVIEW_EXISTING_RUN is supplied, read its run, ledger and checkpoint and reconcile them against current server records. Generate a human-review list and raw/overlay comparisons for every image actually saved in that prior run, including annotated items. Record current revisions and human changes. Preserve all existing labels/history and never restore old content. Store review materials in the new directory.

ELIGIBILITY
Freeze image_id-ordered candidates from /api/dataset.images where status=pending, revision=0 and claimed_by=null. Queue status is not annotation_status. Do not select truth by Z8 detections or scores. Allocate at most five new images in calibration; retain those IDs for recovery.
Never alter existing drafts, initial labels, adjudication items or reviewed records, regardless of actor. Rework requires separately specified IDs and authorization. Do not blindly use claim, which may return drafts. Recheck current annotation and unclaimed status immediately before PUT. On 409, preserve the proposal and skip; do not force an overwrite with a newer base revision.

VISUAL EVIDENCE AND GEOMETRY
Get /api/annotations/{id} and the input PNG at /api/images/{id}/png. Actually inspect each current image with visual capability. File reads, metadata and image generation alone are not inspection. If visual access fails, retain work and stop writes rather than submitting guesses or empty labels.
Do not request original references or Z8 predictions. Keep reference_consulted=false and review_decision=unassessed. Do not infer invisible parts from burst neighbors, species expectations or originals.
Ordinary nearest-neighbor 4x/8x crops/enlargements are allowed; no super-resolution, generative completion or AI sharpening. Record view path/hash, source PNG SHA-256, crop_xyxy, scale and output dimensions. Verify the transform and convert x=x0+x_view/scale, y=y0+y_view/scale. Save only 384x256 input coordinates, not screenshot or normalized coordinates.
Inspect the entire image for every identifiable bird and uncertain region. Give each bird stable b1/b2/... IDs and associate its head and eyes correctly. Bird boxes contain all evidenced visible head, wings, tail and feet; do not reconstruct occluded outlines or create a torso-only class. Head boxes include visible beaks when reliably localizable, otherwise null.
For each genuinely localizable eye, mark its center, at most two per bird. Eye bbox defaults to null. Add a box only when this input supports its actual boundary. Never generate fixed-radius/4x4 eye boxes. If the eye cannot be localized, do not mark it. Use anatomical side=unknown unless reliable.
Annotate all locatable parts regardless of the preferred target. Select eye -> head -> body, with an anchor on the actual visible selected part. Eye target uses a visible eye center. Never mechanically use a rectangle center on branches/background. A confirmed bird with no usable part uses none/null anchor; an uncertain target uses unknown/null and adjudication.
Record bird/head/eye visibility and separate occlusion, pose, defocus, motion blur, small size, compression and out-of-frame. Without obstruction evidence, use unknown visibility with the observed reason rather than calling blur hidden/occluded. A leafy background alone is not occlusion. Use live schema enumerations.
Uncertain bird-like regions go into uncertain_regions with reasons; they are not clean negatives. Confirmed birds and uncertain regions may coexist. Only after whole-image inspection confirms no bird or uncertain region may presence=absent with both arrays empty. Failures/unopened files are not negatives.

MANDATORY OVERLAY CHECK BEFORE SAVING
Save the proposal JSON, then draw that exact proposal on that exact current input: bird/head boxes, eye points/optional boxes and anchors. Save a full-image overlay and relevant head close-ups; ordinary Pillow drawing is enough.
Actually inspect the final overlays for missing birds, tails/feet/beaks, eye placement, instance associations and anchors on background/branches. After changing coordinates, render and inspect the final version again. Never reuse a previous image's base/crop. Creating an overlay without viewing it is not a check.
Record the actual view paths/hashes/transforms and a short check result. Identical adjacent geometry requires reinspection of the current frame and a duplicate_geometry_with record explaining confirmation. A shared burst is not sufficient. Do not perturb correct geometry merely to avoid duplicate warnings.
Without image viewing and overlay checking, do not submit annotated; preserve the proposal and stop writes. Do not bypass visual access by lowering status.

PAYLOAD, VALIDATION AND COMPLETE READBACK
Edit the real GET annotation, preserving schema_version, image_id, annotation_image, hashes, dimensions, preprocess_id and split=null. Templates are not labels. Keep IDs stable: id_counters.bird/uncertain and each instance.next_eye_id advance without recycling.
Fill the live schema fields, visibility, reasons, occluders, target, anchor, needs_review and short notes. The API does not compute target/anchor even in auto mode. Eye-center anchors may use auto, visible head/body anchors use manual. Raw six slots are not six manual classes; slot 5 is not an invented torso class.
Use annotated for a completed whole-image/final-overlay check with reliable localization, including reliable head/body fallback without eyes. Important uncertainty about identity, geometry or anchors requires needs_adjudication, reliable parts only, needs_review=true and a concrete explanation. Do not invent geometry. AI never writes reviewed; review remains null.
POST /api/validate with {image_id,annotation}. Persist the complete valid/issues response, including warnings. This endpoint does not return a normalized annotation. Reinspect warnings rather than inflating boxes or manufacturing eye boundaries. Structural validity is not visual accuracy.
Before PUT, persist the final proposal, real visual-check evidence and validation response. Re-GET pending/revision=0 and check the image remains unclaimed.
PUT /api/annotations/{id} with {base_revision:0,annotation,actor:{id:ACTOR,kind:"ai"}}.
GET again and compare every annotation field except server-managed provenance and review. Separately require review=null and provenance.actor.id=ACTOR, kind=ai, revision=base_revision+1, parent_revision=base_revision. Compare full input identity, status, presence, all instances/boxes/eyes/anchors/visibility and split=null. Object key order is irrelevant; array/numeric contents must match. Persist request/response/readback/comparison; count saved only after complete agreement.
For PUT timeouts or failed readback, record save_unknown and query first. Matching expected revision, actor and complete content establishes saved. Retry the same proposal only if the original revision and eligibility remain. Any other new revision is a conflict. If reconciliation fails, preserve unresolved work and pause writes. Never write SQLite directly.

LEDGER, RECOVERY AND REPORT
Append per-attempt ledger events with UTC, attempt_id, image_id, input hash, actual view paths/hashes/transforms, viewed, overlay_checked, check results, proposal/validation/readback paths, base/saved revisions, outcome and reasons. Do not hard-code inspection booleans true.
Every five images and before exit, atomically replace checkpoint.json via a temporary file. Reconcile unique image IDs and server revisions rather than counting every retry event. List saved, adjudication, skipped, conflicts, retryable failures, save_unknown and remaining IDs. Preserve complete candidates, stage, quota and allocated IDs. A confirmed save missing from the ledger needs a reconciliation event, not a duplicate PUT.
Export exact successful image_id+revision pairs from this run only, excluding other runs even when the actor matches. Include every new image in the human-review checklist plus the entire prior batch, not just AI-flagged uncertainty.
Report in Chinese: actual image viewing, final-overlay checks, structural validation, saving and human review separately; include adjudication, skipped/conflict/failure/unresolved/remaining counts, stage/quota and artifact paths. Report enlargement views honestly. Describe input clarity/localizability, not actual camera AF correctness. Do not invent accuracy.
Stop after calibration. All calibration images and any batch with critical errors require human inspection. Complete first-40 calibration and receive human confirmation before scaling. Preserve existing production labels in this run.

Start with health and visual capability checks, prepare previous-batch review materials, then execute the five-image calibration trial.
```
