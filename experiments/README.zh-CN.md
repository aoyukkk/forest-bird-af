# 实验运行记录

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


## 训练对照

[2026-10-26 汇总](next-training-2026-10-26/README.zh-CN.md)记录原生修复、
YOLO26衍生n/s训练、稀疏正点蒸馏及锁定后的公开配对测试。失败运行和厂商资产保留Git外。

[输入/上下文后续轮](input-context-2026-10-26/README.zh-CN.md)保留随后四组训练及有边界说明的眼模块组合结果。

[容量与真实困难负例](residual-2026-10-27/README.zh-CN.md)记录两种容量、两个种子、延长匹配重训及保留主策略的结果。
