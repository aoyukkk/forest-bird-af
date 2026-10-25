# 已确认标注：无损几何与派生格式

[English](README.md) | **简体中文**

**547 张人工确认图片**，其中保留 12 张已折叠重复图及 2 张明确无鸟图。
冻结划分选取 535 张可用图片：训练 375 / 验证 80 / 测试 80。
使用 `in_queue` 和划分，不要把重复图直接混入训练。

| 文件 | 内容 |
|---|---|
| [confirmed.jsonl](confirmed.jsonl) | 无损的已确认子集：原始形状 ID、点、框和辅助区域保持不变 |
| [confirmed.csv](confirmed.csv) | 图片编号、划分、队列状态及 B/H/E 数量 |
| [COCO 视图](coco/confirmed.coco.json) | 1,041 个原有框；160 个纯眼点放在自定义 `point_annotations` 中 |
| [YOLO 包](yolo-labels.zip) | 部分实测框 TXT、`eye-points.jsonl` 眼点附表及格式说明 |
| [summary.json](summary.json) | 数量、格式版本和校验值 |

## 不能混淆点和框

共有 **566 个鸟框、412 个头框、223 个眼标注**。其中 63 个眼有原有框，
**160 个只有眼点，没有实测宽高**。完整 JSONL 还保留 240 个辅助区域，
辅助区域不作为鸟身真值。

**不生成固定尺寸眼框。** COCO 的 `point_annotations` 是自定义扩展，
YOLO TXT 无法表达点。普通 COCO/YOLO 加载器会忽略眼点附表，可能把有眼但
缺眼框的位置误当负例。完整 BHE 监督应使用 JSONL 和支持部分标注的适配器，
原生训练流程采用这种方式。

坐标绑定冻结的 **384×256 输入**，不是原图坐标。
JSONL/COCO 保留已接受原厂框的半像素边界；YOLO 框视图把边缘裁到输入范围。
对应图片从 [Releases](../../README.zh-CN.md#图片下载) 获取。

## 重新生成与检查

```bash
python scripts/publish/export_confirmed_labels.py \
  --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl \
  --dedupe data/annotations-2026-10-25/curation/dedupe-queue-v1.json \
  --split data/annotations-2026-10-25/splits/evaluation-split-v1.json \
  --output data/annotations-2026-10-25/confirmed
python scripts/tools/verify_annotations.py
```

文本使用 LF；ZIP 文件顺序和时间戳固定。相同输入生成完全相同的文件、压缩包和校验值。

## 2026-10-26 导出修订

格式 v2 用原始眼点替代此前派生的 12×12 容器框，并保留原始 ID 与辅助形状。
**694 条源快照、人工标注和冻结划分没有改变。**
详见[迁移说明](../../../docs/releases/2026-10-26-repository-update.zh-CN.md)。

本数据属于 Z8 辅助人工复核，不是独立盲标或机身对焦性能。
标注元数据采用 CC BY 4.0；照片版权仍归各投稿者。
