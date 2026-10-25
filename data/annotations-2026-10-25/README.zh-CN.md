# 人工复核鸟类标注

[English](README.md) | **简体中文**

**547 条已确认 · 535 条去重后可用 · 坐标绑定 384×256 输入**

| 需要什么 | 入口 |
|---|---|
| 含眼点的完整人工确认几何 | [confirmed.jsonl](confirmed/confirmed.jsonl) |
| CSV、实测框视图及眼点附表 | [格式说明](confirmed/README.zh-CN.md) |
| 含未确认历史的全部 694 条记录 | [全量源快照](labels/community-corrections-v1.jsonl) |
| 冻结的 375/80/80 划分 | [评估划分](splits/evaluation-split-v1.json) |
| 去重和优先浏览清单 | [整理说明](docs/CURATION.zh-CN.md) |
| 字段、状态和标注工具链 | [详细文档](docs/README.zh-CN.md) |
| 对应照片和输入 PNG | [图片下载](../README.zh-CN.md#图片下载) |

JSONL 保留原始点、框及形状 ID，纯眼点不扩成固定眼框。COCO/YOLO 是部分框视图，
不能直接当作完整 BHE 真值；草稿和未标部位不当负例。12 条已确认重复记录保留在
全量导出中，使用冻结划分可取到 535 条可用记录。本数据是 Z8 辅助人工复核，
不是独立盲标或机身实际对焦真值。
