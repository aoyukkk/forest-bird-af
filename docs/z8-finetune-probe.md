# Native Z8 detection-head fine-tuning probe

**English** | [简体中文](z8-finetune-probe.zh-CN.md)

On 2026-10-25, a local RTX 4080 Laptop GPU completed the following engineering path: frozen native backbone → short native-head update → FP16 body-copy export → full original network reload → original Z8 postprocessing. The probe used three frozen 384 × 256 inputs and 12 optimizer steps.

## Evidence

- The physical detection heads expose 8,784 trainable storage parameters. The run changed 990 float master values and 590 exported bytes. Instructions and non-head bytes remained identical.
- Before updates, replayed heads were bit-identical to the original frozen heads on all three inputs.
- Gradients were finite and nonzero. Positive-only loss decreased from `0.05424943` to `0.05402604`.
- After export, full-network outputs were bit-identical to the updated head replay. Original BA2 decoding returned zero on all three inputs.
- Raw heads changed, but final integer candidate records did not. This validates the engineering path, without a detection-accuracy improvement claim.

Elapsed time was approximately 118 seconds. Peak PyTorch tensor allocation was about 86 MiB, with 120 MiB reserved; these figures exclude CUDA context and other processes. Frozen-backbone memory does not estimate full-backbone training memory.

## Arithmetic and gradients

The inference wrapper uses `inference_mode`; native arithmetic also contains rounding and integer bit operations. The original dot can report `requires_grad=True` while returning entirely zero weight gradients, as observed in a separate diagnostic.

The probe caches actual native head inputs, retains native half-precision forward arithmetic and uses explicit STE backward approximations. It does not substitute an ordinary float backbone. Only detection-head fine-tuning is demonstrated; full-backbone backward is unverified.

The first preflight failed because captured features retained inference-tensor flags. No optimizer update ran. That failure was retained; cloning frozen features outside the inference context fixed the handoff, followed by a fresh repeat of all forward checks.

## Labels

The production correction queue currently has no human confirmations. All 30 historical AI records passed adapter checks, containing 26 head boxes and 26 point-only eyes. They are engineering inputs, not reviewed training ground truth.

| Label | Probe handling |
|---|---|
| Head box | Native slot 1; center/size and positive scores |
| Eye center only | x/y only; no fabricated size or hard slot 2/3 direction |
| Visible eye boundary | Geometry may be retained; direction remains unresolved |
| Whole visible bird box | Not automatically a native slot 0/4 target |
| Auxiliary slot 5 | Original retained; no invented training boundary |
| Unlabelled/unseen/uncertain regions | No background negatives |
| Confirmed absence | Not used by this positive-only probe; a complete negative loss is a separate task |

Both the historical `forest-bird-input-manual-v1` and new `forest-bird-z8-correction-v1` formats are supported. The correction schema lacks bird-instance associations: part detection can be tested, but multi-bird AF association cannot be fully evaluated. Geometry is shared between classes within an anchor; withholding other class targets does not guarantee unchanged predictions for those classes. Formal fine-tuning needs regression evaluation.

## Reproduce locally

Supply separately obtained, validated E7 assets, the extracted Z8 package, the annotation workspace and frozen inference runs. No model, firmware or DLL is included in these scripts. Outputs must be outside these sources, the annotation workspace and the public repository.

```powershell
python scripts/probe_z8_finetune.py `
  --upstream <E7-package> --z8-package <Z8-package> `
  --workspace <annotation-workspace> --frozen-runs <saved-Z8-runs> `
  --output <new-local-experiment-folder> `
  --ids fb_0008 fb_0012 fb_0018 --steps 12 --engineering-labels
```

`--engineering-labels` explicitly allows unreviewed labels for I/O testing. Without it, unreviewed records are rejected. Limits are four images and 20 steps. Any consistency, gradient, export or native-decoder failure exits with a retained report. Model copies remain local and must not be committed to the public repository.

`probe_z8_multibird.py` accepts equivalent path arguments and `--ids fb_0496 fb_0632`, replaying original and horizontally mirrored inputs. Mirrors are diagnostic variants, not independent photos. `pN` indexes a decoded list rather than a bird identity; identify parts by slot and location.
