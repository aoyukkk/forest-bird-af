# What is deliberately not published

This page lists artifacts that exist locally but do **not** ship in the public
repository, with the concrete reason. The goal is that a reader can tell which
claims can be checked from the repository alone and which can only be reproduced.

## 1. Vendor-side assets

| Artifact | Local location | Why it is withheld |
|---|---|---|
| Original `resource744.body.bin` and the other model packages | local Z8 model package | vendor numeric weights from the same source as the firmware asset |
| Firmware binaries and unpacked output | local firmware workspace | vendor firmware |
| Consumer lookup tables and thresholds | local model package | vendor implementation |
| `z8models` executor sources | local model package | vendor structural description bound to the weight package |

What the repository does publish is the analysis and the hashes, for example
[model and validation](../../README.md#model-and-validation),
[unpack guide](../reference/UNPACK-GUIDE.md) and
[native head fine-tune](../training/z8-native-head-finetune.md).

## 2. Candidate fine-tuned weights

| Item | Value |
|---|---|
| File | `resource744.finetuned.body.bin` |
| Size | 1,543,726 bytes |
| Changed bytes | 2,248 across 1,350 allowed FP16 parameters |
| SHA-256 | `7171a42d8e9148ba9dd534f5096914818715ad414fed74a60964406cba781a0a` |

Almost every byte of the candidate is still vendor weight, so shipping the file
would ship the vendor model. Instead the repository publishes the hash, the
changed-byte range, the allowed-parameter mask and the scripts, so anyone with
their own lawful copy can reproduce the result.

## 3. Photos and public copies

| Artifact | Note |
|---|---|
| Original receiving-area assets (694) | original path, filename, bytes and EXIF untouched |
| Frozen 384 x 256 input PNGs | rebuildable from the release copies with the fixed preprocessing |
| Public copies | distributed in five release batches, verified with `SHA256SUMS.txt` |

The repository carries manifests, hashes and labels only. Photo copyright stays
with each photographer and permission is recorded per batch.

## 4. Database and private mappings

| Artifact | Why it is withheld |
|---|---|
| `annotations.sqlite3` production database | absolute photo paths, original-asset hashes, reference hashes, reviewer identity |
| Deduplicate records | internal source relations and visual candidate relations |
| Task lists and per-run snapshots | original photo paths |
| Photographer and permission records | privacy and permission scope |

The public substitute is the slimmed label file described in
[reviewed labels](../../data/annotations-2026-10-25/docs/README.md); its `removed_fields` list
states exactly what was dropped.

## 5. Conclusions that are not made

These paths have code or partial evidence but no publishable conclusion, so they
appear in no performance claim:

- Whole-camera AF loop, phase detection and lens drive.
- In-camera focus rate, eye lock-on rate, tracking behaviour.
- Independent blind ground truth and two-annotator adjudication.
- Any gain from enlarging the model, retraining the full network or distillation.

## How to check this yourself

- Labels and splits: `python scripts/tools/verify_annotations.py` and
  `python -m unittest tests.test_published_exports -v`.
- Training method: follow [reproduce](../training/z8-native-head-finetune.md#reproduce) with
  your own verified vendor package and CUDA.
- Repository assets: `python scripts/tools/verify_repo.py`.
