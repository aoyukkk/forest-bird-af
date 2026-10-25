# 标注快照：字段与使用范围

[English](README.md) | **简体中文**

2026-10-25 快照共有 **694 条记录**：547 条确认、146 条草稿、1 条待裁决。
146 条草稿均为已折叠重复图；活动队列只有 535 条确认和待裁决的 `fb_0588`。

## 文件入口

| 入口 | 用途 |
|---|---|
| [数据集首页](../README.zh-CN.md) | 标注、格式和图片下载 |
| [全量源快照](../labels/community-corrections-v1.jsonl) | 所有当前几何与逐项修改，含未确认记录 |
| [已确认子集](../confirmed/README.zh-CN.md) | 完整 547 条确认记录及派生格式 |
| [冻结划分](../splits/evaluation-split-v1.json) | 535 张可用图片及保守关联组 |
| [整理说明](CURATION.zh-CN.md) | 队列与优先浏览清单，不是筛选后的真值集 |
| [工具链](TOOLCHAIN.zh-CN.md) | 导入、复核、去重与导出 |
| [复核轮次](review-rounds.zh-CN.md) | 复核过程与待裁决项 |

## 字段约定

- 几何：冻结 384×256 输入上的 `box_xyxy`、`point_xy`。
  眼点不制造宽高，已接受原厂框的半像素边界保持原样。
- `kind`：bird、head、eye、auxiliary 或 uncertain，辅助区域不是鸟身标签。
- `review_status`：confirmed、draft、needs_adjudication。
  草稿或缺少某部位不能当作负例。
- `decision`：correct、partial_error、error、uncertain、unassessed。
- `items`、`diff`、修订次数和原厂候选计数区分已接受原框与人工增删修改。
- 公开快照移除私人路径、复核者身份和自由备注；生产数据库和完整修订日志保留本地。

## 评估边界

训练前冻结了 375/80/80 划分，关联组不跨划分。但分组只是目录/视觉工程近似，
不是核实后的拍摄事件身份；58 张测试图同组。测试集已使用一次，
不能继续作为新实验的独立测试集。

标签来自 Z8 辅助人工复核，不是独立盲标、原图可见性或镜头合焦证据。
多鸟部位实例关联尚未建立。详见[训练证据](../../../docs/training/z8-native-head-finetune.zh-CN.md)
和[发布边界](../../../docs/releases/not-published.zh-CN.md)。

离线检查：`python scripts/tools/verify_annotations.py`。
