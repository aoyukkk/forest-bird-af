# 预标注与人工复核

[English](run-prelabel.md) | **简体中文**

## 复核本批结果

在 [Release](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) 下载图片包、复核包和单独的 `review.html`。先解压，再用单独的页面替换包内版本。页面默认英文，可切换简体中文。

先查看无候选图，检查整张照片，再标记正确、错误或不确定，并补充备注。结束前导出决定 JSON；细致标注使用完整分辨率图片。

正确图保留作对照。训练候选可以参考模型建议纠错，独立测试标注应不看预测。当前原始类号 0–5 的语义仍待确认。

## 环境

本轮使用 conda `machine`、PyTorch `2.7.0.dev20250117+cu126`、NumPy 1.26.4，以及 12 GB 显存的 RTX 4080 Laptop。NEF 处理所用 rawpy 0.25.1 安装在项目独立依赖目录。

运行前分别取得固定版本的 [E7 仓库](https://github.com/WonderLantern/e7-bird-network/tree/8ced43b19edb845baef39a80c45d40be0b49efba)和本地 Z8 提取包。[验证说明](reports/05-e7-comparison-and-cuda.zh-CN.md)。

## 脚本

| 脚本 | 用途 |
|---|---|
| `prepare_community_release.py` | 稳定编号登记与私人来源映射 |
| `finalize_community_release.py` | 图片完整性校验、NEF 审核图和公开副本打包 |
| `validate_e7_backend.py` | 模型身份、实机样例及 CPU/GPU 一致性检查 |
| `validate_e7_batch.py` | 验证实际采用的 CUDA batch size |
| `prelabel_community.py` | 网络推理与本地 Z8 原厂后处理 |
| `package_prelabels.py` | 打包图片、候选和复核页面 |
| `build_review_page.py` | 更新英中双语页面，无须重新推理 |

`--legacy` 使用最新完整清单。后续导入以 296 条注册记录为准，不退回旧 292 条；元数据处理先在副本上完成，再运行打包校验。

```powershell
conda run --no-capture-output -n machine python scripts/prelabel_community.py `
  --upstream <e7-checkout> `
  --z8-package <directory-containing-z8models> `
  --snapshot <prepared-snapshot> `
  --validation <single-image-validation.json> `
  --batch-validation <batch-validation.json> `
  --output <fresh-run-directory>
```

各脚本支持 `--help`，默认写入新目录。中断后用 `--resume` 时会检查图像哈希；必要的数值校验不通过则停止推理。
