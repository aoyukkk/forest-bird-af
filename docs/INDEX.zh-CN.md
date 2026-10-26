# 文档索引

[English](INDEX.md) | **简体中文**

全部文档按用途分目录。每个目录有一个索引页，这里只给入口。

## 按用途找

| 我想… | 入口 |
|---|---|
| 先知道这个项目在做什么、进展到哪 | [根 README](../README.zh-CN.md) |
| 拿人工校准好的标注去训练 | [人工校准标注](../data/annotations-2026-10-25/confirmed/README.zh-CN.md) |
| 看标注工具怎么装、怎么用 | [标注工具工具链](../data/annotations-2026-10-25/docs/TOOLCHAIN.zh-CN.md) · [工具说明](tools/README.zh-CN.md) |
| 知道数据、编号、标注字段的规矩 | [协议与规范](protocol/README.zh-CN.md) |
| 复现原生 / YOLO26 训练 | [训练](training/README.zh-CN.md) · [本轮结果](training/next-round-2026-10-26.zh-CN.md) |
| 看模型身份、GPU 校验、历史运行 | [报告](reports/README.zh-CN.md) |
| 知道哪些东西刻意没公开 | [发布边界](releases/not-published.zh-CN.md) |
| 看研究方案与固件分析 | [研究](research/README.zh-CN.md) |
| 看固件解包与模型容器格式 | [参考资料](reference/README.zh-CN.md) |

## 目录列表

| 目录 | 内容 | 索引 |
|---|---|---|
| `docs/overview/` | 项目概览、AI 初标流程历史版本 | [overview](overview/README.zh-CN.md) |
| `docs/protocol/` | 数据规范、标注字段、示例 | [protocol](protocol/README.zh-CN.md) |
| `docs/tools/` | 标注工具、Z8 复核、远程协作、AI 初标提示词 | [tools](tools/README.zh-CN.md) |
| `docs/workflow/` | 预标注、人工复核、照片征集文案 | [workflow](workflow/README.zh-CN.md) |
| `docs/training/` | 原生 / YOLO26 方法与结果 | [training](training/README.zh-CN.md) |
| `docs/reports/` | 按日期记录的运行报告 | [reports](reports/README.zh-CN.md) |
| `docs/releases/` | 公开边界与未发布清单 | [releases](releases/README.zh-CN.md) |
| `docs/research/` | 方案与固件分析（含 Sony） | [research](research/README.zh-CN.md) |
| `docs/reference/` | 解包指南、NAB 容器格式 | [reference](reference/README.zh-CN.md) |

`docs/findings/` 与 `docs/plan/` 的内容已并入 `docs/research/`。

## 代码与数据

| 目录 | 内容 | 索引 |
|---|---|---|
| `src/forest_bird_annotator/` | 标注服务与前端 | [src](../src/forest_bird_annotator/README.md) |
| `scripts/pipeline/` | 编号、导入、转换、预标注、发布打包 | [scripts](../scripts/README.md) |
| `scripts/annotator/` | 标注服务启动与远程协作 | 同上 |
| `scripts/training/` | 原生检测头与 YOLO26 部位模型 | 同上 |
| `scripts/publish/` | 生产库 → 公开文件的只读导出 | 同上 |
| `scripts/tools/` | 校验与诊断 | 同上 |
| `data/` | 注册表、各批清单、已标注结果 | [data](../data/README.zh-CN.md) |
| `tests/` | 单元与契约测试 | [tests](../tests/README.md) |
| `experiments/` | 预标注运行的校验记录 | [experiments](../experiments/README.md) |

## 维护规则

- 新增文档放进对应主题目录，并更新该目录的 `README.md` 与 `README.zh-CN.md`。
- 中文与英文成对出现，文件名用 `.md` 与 `.zh-CN.md`。
- 提交前跑 `python scripts/tools/verify_repo.py` 与链接检查。
- `docs/findings/` 里 8 处指向从未提交文件的链接保留为历史记录，不再新增同类断链。
