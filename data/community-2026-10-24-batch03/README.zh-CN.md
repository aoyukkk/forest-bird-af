# 社区林鸟图片：第三批

[English](README.md) | **简体中文**

新增 **47 张 NEF**，编号 **fb_0524–fb_0570**，累计 **570 个资产**。[下载 v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3)，前两批保持冻结。

## 文件与复核

- `community-images-20261024-batch03-part01-of01.zip`：47 张原分辨率 NEF 公开副本。
- `z8-inputs-384x256-20261024-batch03.zip`：47 张无损 RGB PNG 和实际留存的 CHW uint8 输入。
- `z8-prelabels-review-20261024-batch03.zip`：带框图、预览、47 张固定全尺寸内嵌 JPEG 审核图、预测及英中双语 `review.html`。
- `manifest.csv`、累计 `registry.csv` 和 `SHA256SUMS.txt`。

打开复核包中的 `review.html`，全尺寸审核 JPEG 位于 `raw-review/`。页面默认英文，可切换简体中文，第三批使用独立浏览器存储键；结束后导出决定 JSON。

## 图像表示与校验

47 个接收文件全部通过解压与 SHA-256 校验后，源 ZIP 已删除。原片保持不变。公开 NEF 去除指定身份元数据，Nikon 序列号字段统一写为常量 0。TIFF 中所有非空 strip、tile 和 JPEG 图像数据与原片逐字节一致。

原片含 27 张 `High Efficiency*`、20 张无损压缩。默认 rawpy 路径失败 28 张后，新快照明确为全部 47 张选用 **JpgFromRaw 机内 JPEG**。清理 JPEG 元数据前后，解码像素保持一致。[失败记录](../../experiments/community-prelabel-2026-10-24-batch03/parent-rawpy-validation.json)和[变更说明](../../experiments/community-prelabel-2026-10-24-batch03/review-mode-amendment.json)保留。本批不声称通过 RAW 传感器采样解码校验。

## Z8 预测

**47/47 张完成，执行错误 0**：**28 张有候选、19 张无候选，共 83 个原始框**。GPU 网络耗时 **30.40 秒**，不含读写和后处理。重新通过 CUDA 批量验证，两种解码器在全部 47 张上的候选一致。类号 0–5 的语义及人工复核待完成。

输入转换为：EXIF 方向校正 JPEG → RGB → Pillow 双线性拉伸至 384 × 256 → CHW uint8 → `float32(u8) / 256`。PNG 往返及留存输入哈希全部通过。[转换代码](../../scripts/z8_input.py)。

## 记录

[本批清单](manifest.csv) · [累计注册表](../registry.csv) · [预测](predictions.jsonl) · [输入清单](input-manifest.jsonl) · [输入校验](input-validation.json) · [图像校验](image-validation.json) · [元数据校验](metadata-validation.json) · [解压校验](extraction-validation.json) · [执行记录](../../experiments/community-prelabel-2026-10-24-batch03/summary.json)。

版权归摄影者。预测待复核，尚未划分数据集，未开始训练。
