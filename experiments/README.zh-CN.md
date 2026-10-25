# 预标注运行记录

[English](README.md) | **简体中文**

每个子目录对应一次预标注批次，保存该次运行的校验证据：批量一致性、解码器对比、
运行时锁、双语页检查与总结。这些是运行事实记录，不随后续改动重写。

| 目录 | 内容 |
|---|---|
| `community-prelabel-2026-10-24/` | 首批 296 张 |
| `community-prelabel-2026-10-24-batch02/` | 第二批 227 张 |
| `community-prelabel-2026-10-24-batch03/` | 第三批 47 张 NEF（机内 JPEG） |
| `community-prelabel-2026-10-24-batch04/` | 第四批 64 张 |
| `community-prelabel-2026-10-25-batch05/` | 第五批 60 张 |
| `run-001-frozen/` `run-002-parser/` `run-003-runtime/` | 早期协议与解析、运行时准入记录 |

图片与候选在 Releases 分发，清单在 `data/` 下。

历史 runtime lock 保留原始源码路径和哈希。[source-relocations.json](source-relocations.json) 仅记录新位置，不把重构后的代码冒充当时执行的版本。
