# Prelabeling and review

**English** | [简体中文](run-prelabel.zh-CN.md)

## Review a batch

Choose a batch in [Releases](https://github.com/aoyukkk/forest-bird-af/releases). Download its image archive(s) and review bundle, then extract them into one directory. Batch 02 already includes the bilingual page. For the first 296-image release, also copy its separate `review.html` there to replace the bundled version. The page defaults to English and includes a Simplified Chinese selector.

Start with images without candidates. Inspect the whole image, mark correct boxes, errors, or uncertain cases, and add notes. Export the decisions JSON before closing the browser. Use full-resolution images for detailed annotation.

Keep correct examples as controls. Corrected training examples may use model proposals; independent test annotations should be made without seeing those proposals. The current slots 0–5 still need semantic labels.

## Environment

This run used conda `machine`, PyTorch `2.7.0.dev20250117+cu126`, NumPy 1.26.4, and an RTX 4080 Laptop with 12 GB VRAM. rawpy 0.25.1 is installed in a project-specific dependency directory for NEF preparation.

Obtain the pinned [E7 checkout](https://github.com/WonderLantern/e7-bird-network/tree/8ced43b19edb845baef39a80c45d40be0b49efba) and a local Z8 extraction separately. [Validation details](reports/05-e7-comparison-and-cuda.md).

## Scripts

| Script | Purpose |
|---|---|
| `prepare_community_release.py` | Import assets with stable IDs and a private source map |
| `extract_verified_zip.py` | Extract a new ZIP directory and verify every file before deleting the source archive |
| `sanitize_jpeg.py` | Remove JPEG metadata segments while preserving compressed samples, color markers, and orientation |
| `finalize_community_release.py` | Check image integrity, render NEF review images, and package public copies |
| `nef_review.py` | Verify compressed TIFF image payloads and extract a camera-embedded JPEG |
| `validate_e7_backend.py` | Check model identity, physical fixtures, and CPU/GPU agreement |
| `validate_e7_batch.py` | Check the chosen CUDA batch size |
| `prelabel_community.py` | Run the network with the original local Z8 postprocessor |
| `package_prelabels.py` | Package images, proposals, and the review page |
| `build_review_page.py` | Update the English/Simplified Chinese page without rerunning inference |

Use [data/registry.csv](../data/registry.csv) for `--legacy`. Add `--new-only` to process only new hashes, and explicitly list non-image extensions to leave local with `--ignore-extension`. Audit metadata cleaning on copies before finalization. `--archive-prefix` / `--archive-name` give each batch distinct download names.

Use `--ignore-appledouble` when the input contains macOS resource forks. The importer
checks both the `._` filename prefix and AppleDouble magic before excluding a file,
records it in the private import ledger, and leaves the received file unchanged.
A `.NEF` or `.JPG` suffix alone does not establish that a file is a photograph.

NEF preparation defaults to the fixed rawpy render. If a batch needs camera-embedded
JPEGs, explicitly select `--nef-review-mode embedded-jpeg --exiftool <exiftool.exe>`
when finalizing a new snapshot. This mode verifies every populated TIFF image
segment against the original, extracts `JpgFromRaw`, and checks decoded JPEG pixel
equality after metadata cleaning. The manifest and validation record the selected
representation. It does not claim decoded RAW sensor-sample validation. Batch 03
uses this mode for all 47 NEFs after the rawpy path failed on 28 files; its failed
validation remains recorded.

```powershell
conda run --no-capture-output -n machine python scripts/prelabel_community.py `
  --upstream <e7-checkout> `
  --z8-package <directory-containing-z8models> `
  --snapshot <prepared-snapshot> `
  --validation <single-image-validation.json> `
  --batch-validation <batch-validation.json> `
  --output <fresh-run-directory>
```

Run `--help` for each script. Outputs use new directories; `--resume` checks image hashes before continuing an interrupted run. Inference stops if required numerical checks fail.
