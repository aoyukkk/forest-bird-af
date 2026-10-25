# 社区林鸟图片：第二批

[English](README.md) | **简体中文**

新增 227 张 JPG，编号 **fb_0297–fb_0523**，与首批 296 张合计 **523 个资产**。本批从 [v0.2 Release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) 下载，[首批发布](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1)保持不变。

## 下载

| 压缩包 | 内容 |
|---|---|
| `community-images-20261024-batch02-part01-of01.zip` | 227 张全分辨率公开 JPG 副本、清单及图像校验 |
| `z8-inputs-384x256-20261024-batch02.zip` | 227 张 384 × 256 无损 RGB PNG 及实际留存的 CHW uint8 输入 |
| `z8-prelabels-review-20261024-batch02.zip` | 带框图、预览图、原始类号候选和英中双语复核页 |
| `SHA256SUMS.txt` | 三个 ZIP 的校验值 |

图片包与复核包解压到同一目录，打开 `review.html` 即可。本批已内置默认英文、可切换简体中文的页面，浏览器保存键与首批独立。复核后导出决定 JSON。

## 导入与图片校验

接收 ZIP 已解压到独立子目录，228 个文件逐项通过校验：227 张 JPG 和一份仅保留本地的交接说明。确认完整后已删除 ZIP。全部图片均为新 SHA-256，既有编号未改变。

公开副本移除 JPEG 元数据段，保留压缩图像采样、颜色标记及 EXIF 方向。审计未发现指定身份字段残留，227 张按 EXIF 方向解码的 RGB 像素全部与解压原片一致。本地原片未改动。

## 来源分组提示

投稿目录描述了 118 张连拍场景、41 张 AF 区域模式切换对照及 68 张枝叶场景。[submission-groups.jsonl](submission-groups.jsonl) 保留 14 个匿名父目录分组提示；这些不是已确认的连拍关系、遮挡标签或失焦成因真值。尚未划分训练与测试集。

## 输入与预标注

本批采用与首批一致、已通过验证的本地 CUDA 路径、Z8 resource744 模型主体和原厂后处理。原始类号 0–5 的语义仍待确认，候选等待人工复核。数量与网络耗时见 [summary.json](../../experiments/community-prelabel-2026-10-24-batch02/summary.json)。

**227/227** 张全部完成，执行错误 0：**180 张有候选、47 张无候选，共 602 个原始框**。GPU 网络累计 **143.13 秒**，不含图片读写及后处理。E7 主机解码与本批全部留存 Z8 候选记录一致。

384 × 256 PNG 直接从留存输入缓冲区还原，逐字节往返校验通过。网络输入为 `float32(u8) / 256`，CHW `[3, 256, 384]`。[转换代码](../../scripts/pipeline/z8_input.py)固定 EXIF 方向、RGB、双线性拉伸及 CHW 排列；完整机内传感器预处理链路仍未确认。

| 记录 | 用途 |
|---|---|
| [manifest.csv](manifest.csv) | 本批原片、公开副本及审核图哈希 |
| [../registry.csv](../registry.csv) | 后续增量导入使用的累计注册表 |
| [predictions.jsonl](predictions.jsonl) | 冻结的模型候选，等待复核 |
| [input-manifest.jsonl](input-manifest.jsonl) | 每张输入缓冲区及 PNG 哈希 |
| [input-validation.json](input-validation.json) | 留存输入及 PNG 校验 |
| [metadata-validation.json](metadata-validation.json) | 公开副本元数据审计 |
| [extraction-validation.json](extraction-validation.json) | 解压完整性及压缩包删除记录 |

## 使用范围

照片版权归各自摄影者，本次发布不统一授予图片许可。未进行训练，尚无复核完成的人工标签。
