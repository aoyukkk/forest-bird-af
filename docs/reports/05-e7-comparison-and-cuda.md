# Z8 / E7 comparison and CUDA validation

**English** | [简体中文](05-e7-comparison-and-cuda.zh-CN.md)

Run date: 2026-10-24. The 296-image community batch completed on a local GPU with the Z8 factory postprocessor. Inference produced 660 raw candidates on 207 images; 89 images had no candidates. Human review is next.

## Model identity

Upstream: [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network), commit `8ced43b19edb845baef39a80c45d40be0b49efba`. Its 59-file package integrity check passed.

The local Z8 C3.11 resource744 file is 1,543,904 bytes. Its model body starts at offset 176 and is 1,543,726 bytes long. That body is byte-identical to the upstream body, with SHA-256:

`e8d371e77efc3035d0c633c8c90aa4851f1675e5abcf7999edb23adc6439722b`

## Execution profile

| Component | This run |
|---|---|
| Input | EXIF-oriented RGB, primary image frame, Pillow bilinear stretch to 384 x 256, CHW u8 divided by 256 |
| Network | Original body, weights, and command order with the E7 RTZ/FTZ arithmetic profile |
| GPU adapter | Explicit device placement and CUDA double-to-half conversion; the arithmetic policy stays fixed |
| Postprocessor | Original local Z8 IPU instructions executed through the existing BA2 implementation |
| Classes | Native slots 0-5; semantic names are pending |

The earlier local runner used u/255 and FP16 storage with FP32 matrix accumulation. Its results remain separate from this run.

## Validation

| Check | Result |
|---|---|
| Public stripe/random physical fixtures | 23,232 logical head halves and 245,760 defined workspace halves matched bitwise |
| Real-image CPU/GPU comparison | All 11,616 logical head halves matched |
| Repeated GPU inference | Bitwise identical |
| CUDA batches of 16 and 64 | Every sample matched the fixture heads and defined workspace |
| Two decoders on the same 296 image outputs | All candidate records matched |

The upstream reference captures were made on a Nikon ZR C1.10. They validate the supplied network fixtures; the current experiment measures network outputs and candidates, rather than closed-loop camera AF.

The upstream decoder tables are not entirely identical to the corresponding local IPU ranges. Even though all 296 candidate records matched, this run retains the original Z8 postprocessor.

## Environment and timing

- Existing conda environment `machine`, Python 3.12, PyTorch `2.7.0.dev20250117+cu126`, NumPy 1.26.4.
- NVIDIA RTX 4080 Laptop with 12 GB VRAM.
- rawpy 0.25.1 in a project-specific dependency directory for NEF review rendering.

Batch-64 fixture validation took 39.87 seconds with about 4.65 GB peak tensor allocation. The five image batches (64, 64, 64, 64, 40) took **185.95 seconds** for the network stage, or 0.628 seconds per image when amortized across batches. This excludes image I/O, postprocessing, rendering, and human review.

## Batch results

| Item | Count |
|---|---:|
| Completed images | 296 |
| Execution failures | 0 |
| Images with candidates | 207 |
| Images without candidates | 89 |
| Candidate boxes | 660 |

Candidate counts by slot: 0=196, 1=190, 2=9, 3=33, 4=20, 5=212. These are model outputs, not accuracy measurements.

## Review files

The bundle contains 296 overlays, 296 unmarked previews, 30 full-resolution NEF review JPEGs, per-image proposals, and `review.html`. All proposals retain `annotation_status=pending` and `instances=null`. Inputs and network heads remain local; the public bundle excludes them.

All 296 original image hashes were checked again after processing and remained unchanged. The review page passed JavaScript logic checks for filtering, switching images, decision serialization, export triggering, and image paths. Example overlays were inspected visually. Browser layout and click testing were not performed because the in-app browser blocks local file URLs.

[Execution records](../../experiments/community-prelabel-2026-10-24/) · [Review workflow](../workflow/run-prelabel.md)
