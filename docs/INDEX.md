# Documentation index

[简体中文](INDEX.zh-CN.md) | **English**

Documentation is grouped by purpose. Each folder has its own index; this page is
the entry point.

## Find by intent

| I want to… | Entry |
|---|---|
| know what the project is and where it stands | [Root README](../README.md) |
| train on the human-confirmed labels | [Confirmed labels](../data/annotations-2026-10-25/confirmed/README.md) |
| install and use the annotation tool | [Toolchain](../data/annotations-2026-10-25/docs/TOOLCHAIN.md) · [Tools](tools/README.md) |
| know the rules for data, IDs and fields | [Protocol](protocol/README.md) |
| reproduce native / YOLO26 training | [Training](training/README.md) · [Next-round results](training/next-round-2026-10-26.md) |
| check model identity, GPU parity, past runs | [Reports](reports/README.md) |
| see what is deliberately withheld | [Publication boundary](releases/not-published.md) |
| read the research plan and firmware analysis | [Research](research/README.md) |
| read the unpacking and container formats | [Reference](reference/README.md) |

## Folders

| Folder | Content | Index |
|---|---|---|
| `docs/overview/` | Project overview and the archived AI first-pass workflow | [overview](overview/README.md) |
| `docs/protocol/` | Data spec, annotation fields, examples | [protocol](protocol/README.md) |
| `docs/tools/` | Annotator, Z8 review, remote access, AI first-pass prompts | [tools](tools/README.md) |
| `docs/workflow/` | Prelabelling, human review, photo call | [workflow](workflow/README.md) |
| `docs/training/` | Native / YOLO26 methods and results | [training](training/README.md) |
| `docs/reports/` | Dated run reports | [reports](reports/README.md) |
| `docs/releases/` | Publication boundary | [releases](releases/README.md) |
| `docs/research/` | Plans and firmware analysis (including Sony) | [research](research/README.md) |
| `docs/reference/` | Unpack guide and NAB container format | [reference](reference/README.md) |

The former `docs/findings/` and `docs/plan/` content now lives under
`docs/research/`.

## Code and data

| Folder | Content | Index |
|---|---|---|
| `src/forest_bird_annotator/` | Annotation service and front end | [src](../src/forest_bird_annotator/README.md) |
| `scripts/pipeline/` | Registry, import, conversion, prelabelling, release packaging | [scripts](../scripts/README.md) |
| `scripts/annotator/` | Annotation service launchers and remote access | same |
| `scripts/training/` | Native heads and YOLO26 parts | same |
| `scripts/publish/` | Read-only exports from the database to public files | same |
| `scripts/tools/` | Verification and diagnostics | same |
| `data/` | Register, batch manifests, published labels | [data](../data/README.md) |
| `tests/` | Unit and contract tests | [tests](../tests/README.md) |
| `experiments/` | Validation records for prelabel runs | [experiments](../experiments/README.md) |

## House rules

- Put new documents in the matching topic folder and update that folder's
  `README.md` and `README.zh-CN.md`.
- Ship Chinese and English together as `.md` and `.zh-CN.md`.
- Run `python scripts/tools/verify_repo.py` and the link check before committing.
- The eight links inside `docs/findings/` point at files that were never
  committed; they stay as historical record and are not to be extended.
