# 测试

[English](README.md) | **简体中文**

```bash
python -m unittest discover -s tests -p "test_*.py"
```

| 文件 | 覆盖 |
|---|---|
| `test_annotator.py` | 存储、并发声明、导入与 HTTP 接口 |
| `test_dedupe.py` | 相似分组、折叠、撤销、不写标注 |
| `test_z8_review.py` | 复核文档、基线与差异、AI 只能写草稿 |
| `test_z8_training.py` | 目标构造、指标匹配与推导监督 |
| `test_published_exports.py` | 发布标签与划分的契约 |
| `test_curation_exports.py` | 去重队列与优先清单的契约 |
| `test_confirmed_export.py` | 人工确认标注导出的契约 |
| `test_remote_annotator.py` | 远程访问与口令网关 |
| `test_z8_probe_labels.py` | 原生查表与候选适配 |

发布相关测试只依赖标准库，不需要原厂包或 CUDA。

`test_repository_publication.py` 检查无损眼几何、导出/哈希复现、链接与标签压缩包边界。`test_training_output_guards.py` 检查迁移后训练脚本仍拒绝向仓库写私有产物；它导入 PyTorch，但不启动 GPU 作业。完整测试需 Pillow、NumPy 和 PyTorch。


YOLO 路线另有 `test_competition_preservation.py`（空间掩膜、已知缺失）、
`test_bird_parts.py`（部分监督、推导背景、增强几何、无序稀疏蒸馏）、
`test_bird_parts_preparation.py`（弱头框几何）和
`test_public_community_training.py`（旧测试隔离）。模型测试还需固定的可选
[YOLO 依赖](../requirements-yolo26.txt)，使用 CPU。本地完整执行通过 99 项测试。

`test_bird_regions.py`覆盖裁剪映射、不依赖真值的自动区域、原厂B/H候选完整保留；`test_hard_context.py`覆盖背景保护及眼预算/F1选型取舍。
