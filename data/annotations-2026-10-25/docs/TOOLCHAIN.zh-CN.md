# 标注工具与已标注数据

[English](README.md) | **简体中文**

本页把「怎么从一张原片走到一条可训练标签」写完整，方便别人复现这套工具链，而不只是拿到结果文件。

## 组成部分

| 部分 | 位置 | 作用 |
|---|---|---|
| 标注服务 | `src/forest_bird_annotator/` | 本地 HTTP 服务，人和 AI 共用同一套接口 |
| 页面 | `src/forest_bird_annotator/web/` | 零构建依赖的浏览器编辑器，默认简体中文 |
| 启动脚本 | `scripts/annotator/annotator.py`、`launch_annotator.py` | 初始化工作区、启动服务 |
| 导入器 | `scripts/annotator/annotator.py` → `importer.py` | 导入冻结 384×256 输入、校验哈希 |
| 去重 | `dedupe.py` + `scripts/annotator/dedupe_annotator.py` | 可逆的队列折叠，不写标注 |
| 导出 | `scripts/publish/export_z8_labels.py` 等 | 生产库 → 可发布文件 |

## 打开工具

需要 Python 3.11+ 与 Pillow；不需要 Node、Docker 或在线服务。

```bash
python scripts/annotator/annotator.py init --workspace <工作区> --runs <已完成的预标注运行目录>
python scripts/annotator/launch_annotator.py --workspace <工作区>
```

浏览器打开 `http://127.0.0.1:8765`。工作区里会生成 `annotations.sqlite3`、`images/`、`backups/`
和 `dedupe/`。数据库始终留在本机，`*.sqlite3` 已在 `.gitignore` 中。

## 数据流

```text
原片 + 发布副本
   └─ 固定预处理 review-EXIF-RGB-bilinear-stretch-384x256-u8-div256-v1
        └─ 384×256 RGB PNG + 3×384×256 CHW 字节流（各自带 SHA-256）
             └─ Z8 原厂候选（冻结，不参与训练）
                  └─ 人工复核：B 鸟框 / H 头框 / E 眼点 / R 眼框 / U 疑似
                       └─ z8_reviews + z8_review_history（逐修订留痕）
                            └─ export_z8_labels.py → community-corrections-v1.jsonl
                                 └─ export_split_manifest.py → evaluation-split-v1.json
```

## 标注字段

- `kind`：`bird`、`head`、`eye`、`auxiliary`、`uncertain`。`auxiliary` 是原厂附属区域，**不是**鸟身真值。
- 坐标：384×256 输入上的 `xyxy`（半开区间）或眼中心 `point_xy`；浮点合法，越界拒绝。
- `status`：`draft` → `confirmed`；有分歧进 `needs_adjudication`。
- `decision`：`correct`、`partial_error`、`error`；每条修订都保存前后值。
- 翻页、打开、自动保存都不等于确认。

## 去重

页面右上角「去重」是一键操作：把当前图记为与编号相邻的上一张重复、折叠出队列并自动前进；
「撤销去重」把当前图放回队列。完整说明见[标注工具去重一节](../../../docs/tools/annotator.zh-CN.md#去重一键标记重复图)。

队列结果已发布为 [dedupe-queue-v1.json](../curation/dedupe-queue-v1.json)：694 张里折叠 158 张，队列 536 张，
42 组，全部属于相似帧而非字节重复。

## 导出格式

除了本目录的 JSONL 与 JSON，`scripts/publish/export_label_formats.py` 可以把任意一条记录转成：

```bash
python scripts/publish/export_label_formats.py --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl --image fb_0241 --output <目录>
```

输出 `<id>.coco.json`、`<id>.yolo.txt`、`<id>.json`。类别固定为 `bird`/`head`/`eye`；
眼点在没有可见边界时按 12×12 像素补框，并在 COCO 的 `source` 字段标注为 `eye_center_boxed`，
不要把这个框当成人工眼框尺寸。

## 许可与边界

代码 Apache-2.0，标注数据 CC BY 4.0，照片版权归摄影者。标签只描述 384×256 输入，
不是原图真值，也不是机身合焦结果。
