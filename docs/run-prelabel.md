# Prelabeling and review

**English** | [简体中文](run-prelabel.zh-CN.md)

## Review this batch

Download the image archives, review bundle, and separate `review.html` from the [release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1). Extract the archives into one directory, then copy the separate page there to replace the bundled version. The page defaults to English and includes a Simplified Chinese selector.

Start with images without candidates. Inspect the whole image, mark correct boxes, errors, or uncertain cases, and add notes. Export the decisions JSON before closing the browser. Use full-resolution images for detailed annotation.

Keep correct examples as controls. Corrected training examples may use model proposals; independent test annotations should be made without seeing those proposals. The current slots 0–5 still need semantic labels.

## Environment

This run used conda `machine`, PyTorch `2.7.0.dev20250117+cu126`, NumPy 1.26.4, and an RTX 4080 Laptop with 12 GB VRAM. rawpy 0.25.1 is installed in a project-specific dependency directory for NEF preparation.

Obtain the pinned [E7 checkout](https://github.com/WonderLantern/e7-bird-network/tree/8ced43b19edb845baef39a80c45d40be0b49efba) and a local Z8 extraction separately. [Validation details](reports/05-e7-comparison-and-cuda.md).

## Scripts

| Script | Purpose |
|---|---|
| `prepare_community_release.py` | Import assets with stable IDs and a private source map |
| `finalize_community_release.py` | Check image integrity, render NEF review images, and package public copies |
| `validate_e7_backend.py` | Check model identity, physical fixtures, and CPU/GPU agreement |
| `validate_e7_batch.py` | Check the chosen CUDA batch size |
| `prelabel_community.py` | Run the network with the original local Z8 postprocessor |
| `package_prelabels.py` | Package images, proposals, and the review page |
| `build_review_page.py` | Update the English/Simplified Chinese page without rerunning inference |

Use the latest complete manifest for `--legacy`. Future imports should use the 296-row register, not the earlier 292-row snapshot. Apply metadata cleaning to copies before finalization.

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
