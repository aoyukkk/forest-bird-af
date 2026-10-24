# 社区林鸟图片：第四批

[English](README.md) | **简体中文**

新增 **64 张照片：42 NEF、22 JPG**，编号 **fb_0571–fb_0634**，累计 **634 个资产**。[下载 v0.4](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v4)。

## 下载与复核

- 两个 `community-images-20261024-batch04-partNN-of02.zip`：原分辨率公开副本及本批清单。
- `z8-inputs-384x256-20261024-batch04.zip`：64 张无损 384 × 256 PNG 与实际留存的 CHW uint8 输入。
- `z8-prelabels-review-20261024-batch04.zip`：预测、带框图、预览、NEF 全尺寸审核 JPEG 及英中双语 `review.html`。
- `manifest.csv`、累计 `registry.csv` 和 `SHA256SUMS.txt`。

图片包与复核包解压到同一目录，打开 `review.html`，结束时导出决定 JSON。第四批使用独立浏览器存储键。

## 导入与图像检查

接收的 **67 个文件**全部通过解压和 SHA-256 校验后，源 ZIP 已删除。其中 **64 张是真实照片**，3 个 macOS 辅助文件留在本地。一个 AppleDouble 资源叉带有 `.NEF` 后缀，按文件头确认后在编号前排除；此前私人工作快照没有提交，已登记编号不变。

公开 JPG 的解码像素与原图一致。42 张 NEF 明确沿用第三批的 **JpgFromRaw 内嵌机内 JPEG** 表示，本批未尝试 rawpy 渲染。公开 NEF 中所有非空 TIFF 图像数据与原片压缩字节一致；审核 JPEG 保持解码像素。指定身份元数据已清理，Nikon 序列号字段统一为常量 0。原片未改。

## Z8 预测

**64/64 张完成，执行错误 0**：**32 张有候选、32 张无候选，共 105 个原始框**。GPU 网络耗时 **42.59 秒**，不含读写和后处理。两种解码器在全部 64 张上的记录一致。网络和解码脚本不变，复用本次导入会话已通过的 CUDA batch-size 64 验证。

输入为方向校正后的 RGB 审核图，双线性拉伸至 384 × 256，再转 CHW uint8 并除以 256。实际留存输入哈希及 PNG 往返校验全部通过。

## 记录

[本批清单](manifest.csv) · [累计注册表](../registry.csv) · [预测](predictions.jsonl) · [输入哈希](input-manifest.jsonl) · [输入校验](input-validation.json) · [图像校验](image-validation.json) · [元数据校验](metadata-validation.json) · [解压校验](extraction-validation.json) · [执行记录](../../experiments/community-prelabel-2026-10-24-batch04/summary.json)。

版权归投稿摄影者。预测待人工复核，数据尚未划分，未开始训练。
