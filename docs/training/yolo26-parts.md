# YOLO26 bird-parts experiments

**English** | [简体中文](yolo26-parts.zh-CN.md)

This local route trains B/H boxes and eye points independently of vendor weights.
It reuses the official YOLO26 pose backbone, neck and one-to-many branches, with
two box classes and an unordered cell-local eye output. It is a modified model,
not stock YOLO26 pose/detection or a verified camera replacement.

## Data and environment

[CUB-200-2011](https://www.vision.caltech.edu/datasets/cub_200_2011/) and
[NABirds](https://dl.allaboutbirds.org/nabirds) provide bird boxes and landmarks.
Verify image IDs, dimensions and official splits before using mirrors; mirror
license fields do not override original terms. Third-party images remain local.
Community data keep the frozen 375/80/80 split; historical test data do not select models.

Use a compatible existing CUDA PyTorch environment plus
[requirements-yolo26.txt](../../requirements-yolo26.txt). The tested environment
uses Python 3.12, torch 2.7.0.dev20250117+cu126, NumPy 1.26.4, Pillow 11,
OpenCV 4.11, Ultralytics 8.4.189 and PyArrow 17.

## Entry points

All scripts below live in `scripts/training/`:

| Script | Purpose |
|---|---|
| `prepare_public_community.py` | Public labels/split/input PNGs to a community manifest; no vendor package |
| `prepare_bird_parts.py` | CUB plus community inputs to partial labels at 384×256 |
| `import_nabirds_parts.py` | Match verified parquet images to original landmark metadata and official training IDs |
| `prepare_yolo26_weights.py` | Seeded, hashed initialization from official open pose weights; CPU only |
| `bird_parts_model.py` | Model, partial losses, derived background, augmentation and custom decoding |
| `train_bird_parts.py` | Training, validation selection, parent retention, sparse positive distillation and reload checks |
| `evaluate_bird_parts.py` | Locked public test with native/BA2 cross-checks |
| `predict_bird_parts.py` | Standalone custom-checkpoint inference; validation thresholds, no vendor package |

Use `--help` for exact arguments. With frozen Release inputs in a workspace
outside Git, an example is:

```text
python scripts/training/prepare_public_community.py --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl --split data/annotations-2026-10-25/splits/evaluation-split-v1.json --registry data/registry.csv --inputs ../forest-bird-work/review/images --output ../forest-bird-work/community.json
python scripts/training/prepare_bird_parts.py --cub ../public-data/CUB_200_2011 --community ../forest-bird-work/community.json --workspace ../forest-bird-work/review --output ../forest-bird-work/parts
python scripts/training/prepare_yolo26_weights.py --output ../forest-bird-work/initialization
python scripts/training/train_bird_parts.py --dataset ../forest-bird-work/parts/dataset.json --pretrained ../forest-bird-work/initialization --output ../forest-bird-work/run-n --size n --epochs 40 --batch-size 32
```

Screen cross-split near duplicates and freeze data/initialization hashes before
formal runs. Current paired runs share saved initialization snapshots. Their
original new-layer creation seed was not recorded, so exact replay needs those
snapshots; the training seed alone does not reconstruct them. The new preparation
tool records a creation seed for future runs.

## Supervision and augmentation

- Inputs are frozen RGB 384×256 divided by256. Points never acquire invented eye boxes.
- TAL trains B/H boxes. Two unordered eye hypotheses per stride-8 cell have separate
  coordinate/confidence losses. RLE and one-to-one paths are unused; use this decoder.
- Missing parts are unknown; head/eye-only examples need no invented body box.
- Public head boxes derived from landmarks remain weak. Their classification weight
  is0.35; geometry still assumes the coarse box. A no-public-head ablation tests this choice.
- Only human-reviewed community frames with a body permit derived background outside
  protected boxes, points and uncertain regions. Public focal-bird labels and head/eye-only
  community frames never enable global negatives.
- `--augment` adds flip, reduction, blur and small occluders. `--scale-match` matches
  public birds to community **training** sizes. Median-colour canvas padding looks
  synthetic; it is not real forest context. Unusable eyes become unknown after transforms.
- `--teacher` and `--teacher-threshold` enable sparse s-teacher positives, additionally
  corroborated within4px by existing human eye points. Teacher misses supply no negatives;
  this does not create new human truth or implement large-scale unlabelled self-training.

## Evaluation boundaries

Select thresholds/checkpoints on community validation only. Report box IoU .5/.3,
eye2/4/8px, threshold curves, candidate coverage and the proposed E→H→B selection
diagnostic. Distinguish duplicates from wrong locations. Unknown visibility cannot
prove correct fallback. GPU or native-emulator time does not measure camera NPU or lens AF.

Lock candidates/inputs before public testing. Source landmark visibility plus an input-scale
heuristic is not new blind review. Public images may overlap vendor/general pretraining;
public results do not replace a new real forest-bird test.


## Licenses and exact replay

The YOLO route integrates Ultralytics code and pretrained weights governed by
its [AGPL-3.0 / Enterprise terms](https://www.ultralytics.com/license).
The repository's Apache-2.0 license for original code does not replace those
terms. CUB and NABirds retain their original research-use restrictions;
third-party source images and per-image NABirds annotations are not republished.

`evaluate_bird_parts.py` expects the recorded experiment workspace layout
(selection manifest, pretrained snapshots and native repair directory).
It is not a generic stock-Ultralytics evaluation command. It persists native
forward packets, verifies every packet with original BA2 instructions using
CPU workers, and checks original batch/singleton and repaired full reload
parity on three images. Resuming requires identical locked assets and thresholds.


## Run a candidate

Use the selected `best.pt` and a JSON object containing `thresholds` for
`bird`, `head` and `eye` (the training `validation-best.json` has that field):

```text
python scripts/training/predict_bird_parts.py --weights ../forest-bird-work/run-n/best.pt --calibration ../forest-bird-work/run-n/validation-best.json --image bird.jpg --output ../forest-bird-work/prediction.json
```

It loads the full saved state into this custom architecture, so inference does
not need the initialization snapshot or vendor model. It applies EXIF orientation,
RGB and a bilinear stretch to384×256, and reports input-pixel coordinates.
CUDA is default; CPU requires explicit `--device cpu`. Use the project JPEG
rendering path for RAW. Existing outputs/inputs are never overwritten. This
is not stock `yolo predict`, a camera firmware file or a lens controller.
