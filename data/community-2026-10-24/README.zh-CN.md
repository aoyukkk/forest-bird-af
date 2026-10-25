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

Release 同时提供 `SHA256SUMS.txt`、复核包和独立的双语 `review.html`。用独立页面替换包内版本即可默认显示英文，并可切换简体中文，详见[复核流程](../../docs/workflow/run-prelabel.zh-CN.md)。

## 图片处理

本地原片保持不变。公开副本用 ExifTool 13.59 移除指定的 GPS、序列号、所有者、主机、评论和 XMP 字段。

全部 JPEG/PNG 解码像素及 30 个 NEF 的传感器采样均与原片一致。元数据处理会改变文件字节，因此清单分别保存原片和公开文件的 SHA-256。

NEF 审核 JPEG 使用 rawpy 0.25.1、AHD、相机白平衡、sRGB 8-bit、关闭自动提亮、JPEG quality 98 和无色度降采样。全尺寸渲染图包含在复核包中，图片包仍保留 NEF。

## 模拟输入数据集

在同一 Release 下载 `z8-inputs-384x256-20261024.zip`，包含：

- `input-png/`：296 张 **384 × 256**（98,304 像素）无损 RGB PNG。
- `input-chw-u8/`：296 份实际留存的输入缓冲区，每份 294,912 字节，CHW 排列 `[3, 256, 384]`。
- `input-manifest.jsonl`：编号、尺寸，以及原资产、公开副本、审核图和输入的哈希关联。
- `input-validation.json`：296 份输入哈希及 PNG 像素往返校验全部通过。

PNG 直接由留存输入还原，没有重新推理或缩放。将解码像素排列为 CHW 后，全部匹配预标注记录的 `input_sha256`；PNG 文件哈希与输入缓冲区哈希不同。

网络实际接收 `float32(u8) / 256`。这批数据固定了本轮模拟的真实输入，但尚未确认完整机内传感器预处理链路。眼、头精标继续使用全分辨率图片，模型对照使用固定输入；人工标签仍待完成。

[转换代码](../../scripts/pipeline/z8_input.py)依次应用 EXIF 方向、转 RGB、Pillow 双线性拉伸至 384 × 256，再按 R/G/B 平面存储。NEF 先使用上文规定的审核 JPEG。单图复现：

```powershell
python scripts/pipeline/z8_input.py path/to/review-image.jpg --output input-check --expected-sha256 INPUT_SHA256
```

预期哈希取自 [input-manifest.jsonl](input-manifest.jsonl) 的 `input_chw_u8_sha256`。复现需使用相同审核图和 [input-validation.json](input-validation.json) 中记录的 Pillow 版本。[打包代码](../../scripts/pipeline/package_z8_inputs.py)负责校验留档并导出 PNG。

## 预标注结果

296 个文件全部完成推理：**207 张有候选、89 张无候选，共 660 个框**。候选保留原始类号 0–5，人工复核和数据划分尚未完成。

E7 数值配置、CUDA 检查和保留的 Z8 后处理见[验证报告](../../docs/reports/05-e7-comparison-and-cuda.zh-CN.md)。

## 使用范围

照片版权归各自摄影者。本次发布不为全部图片统一授予 CC BY、CC0 或商业许可，超出现有授权的使用请联系权利人。
