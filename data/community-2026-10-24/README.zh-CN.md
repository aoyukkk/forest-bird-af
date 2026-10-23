# 社区林鸟图片：2026-10-24

[English](README.md) | **简体中文**

共 296 个文件：**259 JPG、7 PNG、30 NEF**。原有 `fb_0001` 至 `fb_0292` 保持不变，新增四个资产追加到 `fb_0296`。

## 下载

打开 [Release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1)，下载四个 `community-images-20261024-partXX-of04.zip`，解压到同一目录，合并 `images/`。每个 ZIP 都可以独立解压。

| 文件 | 内容 |
|---|---|
| [manifest.csv](manifest.csv) | 编号、尺寸、原片与公开文件哈希、审核图哈希 |
| [packages.json](packages.json) | 图片包大小、图数与 SHA-256 |
| [predictions.jsonl](predictions.jsonl) | 每图原始类号候选，待人工复核 |
| [review-bundle.json](review-bundle.json) | 复核包大小与校验值 |

Release 同时提供 `SHA256SUMS.txt`、复核包和独立的双语 `review.html`。用独立页面替换包内版本即可默认显示英文，并可切换简体中文，详见[复核流程](../../docs/run-prelabel.zh-CN.md)。

## 图片处理

本地原片保持不变。公开副本用 ExifTool 13.59 移除指定的 GPS、序列号、所有者、主机、评论和 XMP 字段。

全部 JPEG/PNG 解码像素及 30 个 NEF 的传感器采样均与原片一致。元数据处理会改变文件字节，因此清单分别保存原片和公开文件的 SHA-256。

NEF 审核 JPEG 使用 rawpy 0.25.1、AHD、相机白平衡、sRGB 8-bit、关闭自动提亮、JPEG quality 98 和无色度降采样。全尺寸渲染图包含在复核包中，图片包仍保留 NEF。

## 预标注

296 个文件全部完成推理：**207 张有候选、89 张无候选，共 660 个框**。候选保留原始类号 0–5，人工复核和数据划分尚未完成。

E7 数值配置、CUDA 检查和保留的 Z8 后处理见[验证报告](../../docs/reports/05-e7-comparison-and-cuda.zh-CN.md)。

## 使用范围

照片版权归各自摄影者。本次发布不为全部图片统一授予 CC BY、CC0 或商业许可，超出现有授权的使用请联系权利人。
