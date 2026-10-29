# Experiment records

**English** | [简体中文](README.zh-CN.md)

Each subdirectory is one prelabel batch and keeps that run's validation evidence:
batch consistency, decoder comparison, runtime lock, bilingual page checks and a
summary. These record what happened and are not rewritten later.

| Directory | Content |
|---|---|
| `community-prelabel-2026-10-24/` | First batch, 296 images |
| `community-prelabel-2026-10-24-batch02/` | Batch 02, 227 images |
| `community-prelabel-2026-10-24-batch03/` | Batch 03, 47 NEFs (camera-embedded JPEG) |
| `community-prelabel-2026-10-24-batch04/` | Batch 04, 64 images |
| `community-prelabel-2026-10-25-batch05/` | Batch 05, 60 images |
| `run-001-frozen/` `run-002-parser/` `run-003-runtime/` | Early protocol, parser and runtime admission |

Images ship through releases; manifests live under `data/`.

Historical runtime locks retain their original source paths and hashes. [source-relocations.json](source-relocations.json) maps them to the current layout without asserting that refactored code produced the frozen run.


## Training comparisons

[2026-10-26 aggregates](next-training-2026-10-26/README.md) record native repair,
YOLO26-derived n/s training, sparse positive distillation and locked paired public tests.
Original failed runs and vendor assets stay outside Git.

[Input/context follow-up](input-context-2026-10-26/README.md) records the subsequent four-trial experiment and explicitly qualified eye-module combinations.

[Capacity and real hard negatives](residual-2026-10-27/README.md) records the two-capacity, two-seed experiment, longer matched reruns and unchanged primary policy.

[Public expansion / empty-scene results](expansion-2026-10-27/README.md): 17,252 admitted images, four new verifier runs, full-routing empty-scene replay and a rejected B/H filter.

[Information and scale diagnostic](information-diagnostic-2026-10-28/README.md): 80 development frames, 172 empty scenes, actual native replay and two rejected automatic fallback policies.

[Native E7 return](native-return-2026-10-29/README.md): fixed-layout training and firmware verification.

[Native B/H/E continuation and 11 human point reviews](native-bhe-2026-10-29/README.md): existing head parameters, equal auxiliary-loss weights and separate point/box/empty-scene tradeoffs.
