# 社区林鸟图片：第五批

[English](README.md) | **简体中文**

新增 **60 张 JPEG**，编号 **fb_0635–fb_0694**。累计注册 **694 张**。[下载 v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5)。

## 下载与复核

- 两个 `community-images-20261025-batch05-partNN-of02.zip`：保留原始分辨率的公开副本及批次清单。
- `z8-inputs-384x256-20261025-batch05.zip`：60 张无损 384×256 PNG 与原推理保存的 CHW uint8 输入。
- `z8-prelabels-review-20261025-batch05.zip`：候选、叠框、预览及英中双语复核页面。
- `manifest.csv`、累计 `registry.csv` 与 `SHA256SUMS.txt`。

把图片包和复核包解压到同一目录，打开 review.html，结束后导出决定 JSON。本批浏览器存储独立。

## 导入检查

RAR 内 60 张文件均按大小与 SHA-256 核对后才删除源包。首次校验把目录条目送入 bsdtar 标准输出解压而报错；改为明确选择常规文件后通过，已解出的照片未重写。60 张均为新哈希，既有 ID 和原片保持不变。

公开副本单独移除识别性元数据，60 张解码 RGB 像素与原片完全一致；本批没有 NEF，无需 RAW 渲染。

## Z8 预测

**60/60 完成，推理错误 0**：**22 张有候选、38 张无候选，共 45 个原始框**。GPU 网络计算 **39.09 秒**，不含图片读写、叠框及 CPU 后处理。重新执行的 CUDA batch-size 64 样例逐位校验通过；网络及解码代码与第四批相同，两套解码对 60 张结果全部一致。

输入采用 EXIF 正向 RGB、双线性拉伸至 384×256、CHW uint8，网络输入 float32(u8)/256。保存输入哈希与 PNG 还原检查全部通过。候选不是人工真值，无候选也不等于无鸟。

训练候选若全部可见部位已正确，可复核后采用，不必从零重画；正常对照仍要保留，错误与缺少部位再修补。独立测试候选不看模型预测标注。

## 记录

[清单](manifest.csv) · [注册表](../registry.csv) · [预测](predictions.jsonl) · [输入哈希](input-manifest.jsonl) · [输入校验](input-validation.json) · [图片校验](image-validation.json) · [元数据校验](metadata-validation.json) · [解压校验](extraction-validation.json) · [执行记录](../../experiments/community-prelabel-2026-10-25-batch05/summary.json)。

照片版权仍归投稿者，数据尚未划分，未启动训练。
