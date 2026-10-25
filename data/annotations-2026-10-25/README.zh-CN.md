# 已标注结果（2026-10-25 快照）

[English](README.md) | **简体中文**

本目录发布 **Z8 辅助人工纠错标签** 和 **冻结评估划分**，不含图片、原始资产哈希、
数据库或权重。图片按批次从 Releases 获取，编号对照 [registry.csv](../registry.csv)。

| 文件 | 内容 |
|---|---|
| [labels/community-corrections-v1.jsonl](labels/community-corrections-v1.jsonl) | 694 张图的逐图标签（JSON Lines） |
| [labels/community-corrections-v1.json](labels/community-corrections-v1.json) | 计数、标签文件哈希与字段剔除说明 |
| [labels/summary.md](labels/summary.md) | 一行式摘要 |
| [evaluation-split-v1.json](evaluation-split-v1.json) | 535 张训练/验证/测试划分与关联组 |
| [dedupe-queue-v1.json](dedupe-queue-v1.json) | 去重队列：536 张在队列、158 张折叠、42 组 |
| [best-images-v1.json](best-images-v1.json) | 120 张优先复核清单与评分规则 |

文档：

| 文件 | 内容 |
|---|---|
| [TOOLCHAIN.zh-CN.md](TOOLCHAIN.zh-CN.md) | 标注工具链：从原片到可训练标签的全流程与导出格式 |
| [CURATION.zh-CN.md](CURATION.zh-CN.md) | 较好图片怎么选、去重队列的事实 |
| [review-rounds.zh-CN.md](review-rounds.zh-CN.md) | 复核轮次、纠错统计与剩余问题 |

训练与发布边界见[原生检测头微调](../../docs/training/z8-native-head-finetune.zh-CN.md)与[未发布内容](../../docs/releases/not-published.zh-CN.md)。

## 当前状态

| 复核状态 | 图数 |
|---|---:|
| `confirmed`（人工确认） | 547 |
| `draft`（未确认草稿） | 146 |
| `needs_adjudication`（待裁决） | 1 |

已确认的 547 张图里共有 1,441 个部位项：鸟身 566、鸟头 412、眼 223、辅助区域 240。
其中 2 张是确认无鸟的空图。冻结原厂候选合计 1,495 个，覆盖 469 张图。

`draft` 行保留是为了让外部读者知道哪些图还没复核过，**不要当作负样本**。
Z8 有候选而人工尚未确认的图，既不是“确认无鸟”，也不是“确认有误”。

## 字段

每行至少包含：

```json
{
  "image_id": "fb_0001",
  "annotation_image": {
    "width": 384, "height": 256,
    "png_sha256": "...", "input_chw_u8_sha256": "...",
    "preprocess_id": "review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1",
    "coordinate_space": "z8_input_384x256"
  },
  "review_status": "confirmed",
  "presence": "present",
  "decision": "error",
  "revision": 5,
  "revisions": 5,
  "confirmed": true,
  "parts": {"bird": 1, "head": 0, "eye": 0},
  "items": [{"id": "n1", "kind": "bird", "box_xyxy": [163.0, 104.0, 224.5, 142.0]}],
  "frozen_z8_candidates": {"bird": 0, "head": 0, "eye": 0, "auxiliary": 0},
  "frozen_z8_candidate_total": 0,
  "frozen_baseline_matches_current": false,
  "diff": {"added": [], "removed": [], "changed": [], "unchanged": [], "changed_parts": ["bird"]},
  "review_changes": 1,
  "record_sha256": "..."
}
```

- `kind`：`bird`（整鸟）、`head`（含喙的头框）、`eye`（眼中心点）、`auxiliary`
  （原厂附属区域，**不是**鸟身真值）。眼物品共 226 个：160 个带中心点 `point_xy`，
  66 个只画了边界清楚的眼框 `box_xyxy`。眼框宽高只在边界确实可见时存在，不批量
  编造固定像素框。
- `decision`：`correct` 原厂正确、`partial_error` 部分有误、`error` 有误、
  `uncertain` 不确定、`unassessed` 未判定。
- `diff` 保留逐框增删改；`frozen_z8_candidates` 是复核前的冻结原厂候选计数。
- 坐标语义：人工框为 384×256 输入上的半开区间 `xyxy`；原厂候选沿用原机含端点像素
  坐标，因此会出现 `-0.5` 这类值。两者都在合法范围内。

## 划分

| 划分 | 图片 | 保守关联组 | 鸟 | 头 | 眼 |
|---|---:|---:|---:|---:|---:|
| train | 375 | 56 | 385 | 301 | 174 |
| val | 80 | 6 | 79 | 50 | 25 |
| test | 80 | 5 | 83 | 59 | 22 |

划分在训练前冻结，关联组不跨划分，测试集只在验证集选型后打开一次。分组依据投稿
子目录、视觉相似候选和去重关系，是工程防泄漏近似，不等于已核实的拍摄事件身份。
80 张测试图里有 58 张同属一个保守组。

## 校验

```bash
python scripts/verify_annotations.py
```

检查项：JSON 解析、坐标范围、眼点必须存在、部位计数与条目一致、状态取值、划分不跨组、
划分计数一致，以及路径类敏感字段（原图绝对路径、原资产哈希等）没有泄漏。

## 可做什么、不可做什么

可以：离线评估鸟身/鸟头/眼检测，比较原厂模型与自研改动，复现发布过的划分。

不可以：把这些数字说成机身对焦成功率、眼锁成功率或镜头合焦效果；把
`draft` 当负样本；把辅助区域当鸟身标签；把 Z8 辅助复核说成独立盲标。
