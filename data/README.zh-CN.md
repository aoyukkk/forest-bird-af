# 数据：照片、标注与划分

[English](README.md) | **简体中文**

## 先选用途

| 需要什么 | 入口 |
|---|---|
| 全部人工确认标注 | [547 条确认记录](annotations-2026-10-25/README.zh-CN.md) |
| 训练、验证与测试划分 | [535 条可用记录，375/80/80 划分](annotations-2026-10-25/splits/evaluation-split-v1.json) |
| 含草稿的完整复核快照 | [694 条源记录](annotations-2026-10-25/labels/community-corrections-v1.jsonl) |
| 稳定图片编号与哈希 | [registry.csv](registry.csv) |
| 去重与优先浏览清单 | [整理说明](annotations-2026-10-25/docs/CURATION.zh-CN.md) |

## 图片下载

照片及精确 PNG/CHW 输入放在 Release，不放 Git。完整 **694 个不重复资产**
需要下载五批。每批提供 `SHA256SUMS.txt`；
[releases.json](releases.json) 汇总下载文件、大小和哈希。

| 批次 | 编号 | 图数 | 下载 |
|---|---|---:|---|
| [第一批](community-2026-10-24/README.zh-CN.md) | fb_0001–fb_0296 | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| [第二批](community-2026-10-24-batch02/README.zh-CN.md) | fb_0297–fb_0523 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |
| [第三批](community-2026-10-24-batch03/README.zh-CN.md) | fb_0524–fb_0570 | 47 | [v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3) |
| [第四批](community-2026-10-24-batch04/README.zh-CN.md) | fb_0571–fb_0634 | 64 | [v0.4](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v4) |
| [第五批](community-2026-10-25-batch05/README.zh-CN.md) | fb_0635–fb_0694 | 60 | [v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5) |

复现标注和眼点评估时下载 `z8-inputs-384x256-*.zip`，
不要把 384×256 坐标直接套到原分辨率照片。NEF 的审核输入采用各批明确记录的机内 JPEG 表示。

## 复核状态

去重后的活动队列为 **535 条确认 + 1 条待裁决**。
另有 12 条已确认、146 条草稿属于折叠重复图，保留供追溯；
草稿不是负例，也不是新增待标任务。使用 JSONL 可保留眼点和部分标注信息，
COCO/YOLO 视图不能独立充当完整 BHE 真值。

[最初 292 条投稿注册](contributions-2026-10-23/)和
[CUB 校准元数据](calibration-200/)是独立历史资料。后续导入须从累计注册表实际最大编号追加。

## 许可

照片版权归摄影者，遵循[照片使用范围](community-2026-10-24/README.zh-CN.md#使用范围)。
文档及标注元数据采用 CC BY 4.0，不自动授予照片许可；CUB 遵循其来源条款。
