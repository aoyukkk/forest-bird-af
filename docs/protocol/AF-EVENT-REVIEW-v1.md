# Independent forest-event review v1

**English** | [简体中文](AF-EVENT-REVIEW-v1.zh-CN.md)

Status on 2026-10-26: a collection/review protocol, **no new event dataset has
been received or reviewed**. The user confirmed no new submissions are available.

The initial collection target is 100–150 frames from at least 20 new capture
events. This is a practical target, not a statistical power calculation. Keep
each burst/event intact. The community historical 80-image test and the opened
200-source public comparison cannot become fresh tests by renaming or splitting.

## Collection and grouping

Record image SHA-256, stable event ID, photographer/source consent, frame order
and rendering recipe. Frames of the same bird in one continuous shooting session
belong together even if filenames differ. Select first/middle/last frames or
another declared systematic sampling rule before seeing model scores. Include
clear controls, foliage obstruction and defocus; retain whole short bursts.
Do not collect only one model's failures or deduplicate away the transitions.

Original assets remain unchanged. For RAW, distinguish embedded JPEG from an
independent RAW rendering. The frozen 384×256 input, a source-detail view and
camera/lens focus behavior are three different evidence levels.

## Two review passes

1. Hide all model proposals. The human reviewer records bird presence
   (`present/absent/unknown`) and, separately for the source-detail view and
   frozen input, the availability of eye/head/bird (`available/unavailable/unknown`).
   An invisible or unresolvable eye receives no guessed point. Record a target
   identity for multi-bird frames; otherwise target-identity scoring is unknown.
2. After this pass is frozen, show anonymous locked-model candidates. The reviewer
   judges whether each selected candidate belongs to the intended bird and is
   useful for the available part. An optional visible-eye click supports numeric
   point localization; box IoU requires actual box annotation. Human candidate
   usefulness judgments must not be presented as IoU or pixel-error ground truth.

Opening, paging and autosaving remain drafts. Confirmation requires an explicit
human action. Record reviewer, revision and before/after values. A model miss
does not prove absence. AI proposals and machine-derived visibility remain
separate from human confirmation. Use a separate review workspace; never write
this experiment into the existing production annotation database.

## Evaluation

Freeze model, thresholds, source/input hashes, region policy and total invocation
budget before scoring. Report at least target acquisition, false eye preference
over a valid fallback, and correct head/bird fallback where availability is
known. Keep unknown cases and unassessed cases visible. Report per-event results
as well as frame totals; paired crops do not add independent events.

Use actual ordered bursts for candidate persistence, target jumps and the
number of frames until a useful candidate reappears. These are offline temporal
diagnostics. Lens recovery time and camera AF success still require camera data.

No trained-model improvement on this new population may be claimed until new
events and human review actually exist. Photo redistribution consent is separate
from research use or label confirmation.
