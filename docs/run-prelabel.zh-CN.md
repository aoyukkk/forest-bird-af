# 预标注与人工复核

[English](run-prelabel.md) | **简体中文**

## 选择批次并复核

在 [Releases](https://github.com/aoyukkk/forest-bird-af/releases) 选择批次，下载该批图片包与复核包，解压到同一目录。第二批已内置双语页面；首批 296 张的版本还需用独立 `review.html` 替换包内页面。页面默认英文，可切换简体中文。

先查看无候选图，检查整张照片，再标记正确、错误或不确定，并补充备注。结束前导出决定 JSON；细致标注使用完整分辨率图片。

正确图保留作对照。训练候选可以参考模型建议纠错，独立测试标注应不看预测。当前原始类号 0–5 的语义仍待确认。

## 环境

本轮使用 conda `machine`、PyTorch `2.7.0.dev20250117+cu126`、NumPy 1.26.4，以及 12 GB 显存的 RTX 4080 Laptop。NEF 处理所用 rawpy 0.25.1 安装在项目独立依赖目录。

运行前分别取得固定版本的 [E7 仓库](https://github.com/WonderLantern/e7-bird-network/tree/8ced43b19edb845baef39a80c45d40be0b49efba)和本地 Z8 提取包。[验证说明](reports/05-e7-comparison-and-cuda.zh-CN.md)。

## 脚本

| 脚本 | 用途 |
|---|---|
| `prepare_community_release.py` | 稳定编号登记与私人来源映射 |
| `extract_verified_zip.py` | 解压到新目录并逐文件校验，完成后再删除源 ZIP |
| `sanitize_jpeg.py` | 移除 JPEG 元数据段，保留压缩采样、颜色标记和方向 |
| `finalize_community_release.py` | 图片完整性校验、NEF 审核图和公开副本打包 |
| `nef_review.py` | 校验 TIFF 压缩图像数据并提取机内 JPEG |
| `validate_e7_backend.py` | 模型身份、实机样例及 CPU/GPU 一致性检查 |
| `validate_e7_batch.py` | 验证实际采用的 CUDA batch size |
| `prelabel_community.py` | 网络推理与本地 Z8 原厂后处理 |
| `package_prelabels.py` | 打包图片、候选和复核页面 |
| `build_review_page.py` | 更新英中双语页面，无须重新推理 |

`--legacy` 使用累计注册表 [data/registry.csv](../data/registry.csv)。`--new-only` 只处理新哈希，`--ignore-extension` 显式指定保留在本地的非图片类型。公开副本先通过元数据审计，再打包；`--archive-prefix` / `--archive-name` 用于区分批次文件名。

收到 macOS 资源叉时，使用 `--ignore-appledouble`。导入器同时检查 `._`
文件名前缀和 AppleDouble 文件头，确认后记入私人辅助文件清单并保留原文件。
不能仅凭 `.NEF` 或 `.JPG` 扩展名认定为照片。

NEF 默认使用固定 rawpy 渲染。需要使用机内 JPEG 时，在新快照上显式指定
`--nef-review-mode embedded-jpeg --exiftool <exiftool.exe>`。此模式逐段校验
TIFF 中所有非空图像数据与原片一致，提取 `JpgFromRaw`，并核对去除元数据
前后的 JPEG 解码像素。清单和验证记录会写明所用表示，不声称完成 RAW
传感器采样解码校验。第三批在 rawpy 路径失败 28 张后，统一为全部 47 张
NEF 选择此模式；失败记录保留。

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
