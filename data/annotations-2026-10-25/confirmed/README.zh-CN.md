# 人工校准好的标注（547 张）

这里是**你人工逐张确认过的全部标注**，不是按质量挑出来的图。

| 文件 | 内容 |
|---|---|
| [confirmed.jsonl](confirmed.jsonl) | 547 条确认记录，含鸟/头/眼几何、原厂判定、划分归属 |
| [confirmed.csv](confirmed.csv) | 扁平索引：编号、划分、是否在去重队列、原厂判定、部位数量 |
| [summary.json](summary.json) | 计数、部位合计、逐划分分布与标签哈希 |
| [coco/confirmed.coco.json](coco/confirmed.coco.json) | 一个 COCO 文件装下全部 1,201 个目标 |
| [yolo-labels.zip](yolo-labels.zip) | 每图一个 YOLO 文本，`class cx cy w h` 归一化 |

## 数量

| 项 | 数量 |
|---|---:|
| 确认图片 | 547 |
| 有框的图 | 545 |
| 明确确认无鸟 | 2 |
| 鸟框 | 566 |
| 头框 | 412 |
| 眼 | 223 |
| COCO 目标总数 | 1,201 |

原厂判定分布：`error` 276、`partial_error` 144、`correct` 127。也就是说其中有 127 张是你原样确认“原厂正确”的，
它们同样是校准好的真值，不该被过滤掉。

划分：train 375、val 80、test 80，合计 535 张；另外 12 张确认图在去重时被判为相似帧折叠出队列，
`in_queue` 字段如实记录，没有静默丢弃。

## 怎么用

```bash
python scripts/publish/export_confirmed_labels.py \
  --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \
  --dedupe data/annotations-2026-10-25/curation/dedupe-queue-v1.json \
  --split  data/annotations-2026-10-25/splits/evaluation-split-v1.json \
  --output data/annotations-2026-10-25/confirmed
```

重跑是幂等的：同样的输入生成同样的文件，`confirmed_sha256` 不变。

## 三个必须一起读的边界

- **坐标绑定 384×256 冻结输入**，不是原图真值，也不是机身合焦结果。图片按 `image_id` 从
  [Releases](../docs/README.zh-CN.md) 或 [registry.csv](../../registry.csv) 对应批次获取。
- **这是辅助复核，不是独立盲标**：确认时能看到原厂框，所以这批标签不能当“独立测试真值”的口号卖，
  只能说是人工校准后的训练/评估标签。
- **眼只有中心点**。没有可见边界的眼在 COCO/YOLO 里补成 12×12 框并标 `eye_center_boxed`，
  那是容器尺寸，不是人工量出来的眼睛大小。

## 与“较好图片清单”的区别

| | 本文件 | `best-images-v1.json` |
|---|---|---|
| 范围 | 全部 547 张确认图 | 按分数取前 120 张 |
| 用途 | 训练与评估的完整真值 | 人工先看哪几张的排序建议 |
| 是否可当指标 | 是标签 | 否，只是复核优先级 |

## 许可

标注数据 CC BY 4.0；照片版权归各摄影者，按批次授权范围使用。
