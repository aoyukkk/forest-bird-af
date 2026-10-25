# forest-bird-af

[English](README.md) | **简体中文**

优化枝叶遮挡下的鸟类自动对焦，重点处理漏鸟和误锁树枝。目标是：有可用眼锁眼，否则退到头，再退到整鸟；都不可用时释放目标。

## 当前进度

更新于 2026-10-25。

| 工作 | 状态 |
|---|---|
| 社区照片 | 694 个文件：568 JPG、7 PNG、119 NEF |
| 图像校验 | 原资产哈希保持不变；公开副本校验通过，各批写明所用图像表示 |
| 模拟输入 | 694 张 384 × 256 无损 RGB PNG，附实际留存的 CHW 输入 |
| Z8 预标注 | 本地 RTX 4080 Laptop GPU 完成 694/694 张，执行错误 0 |
| 候选结果 | 469 张有框，共 1495 个候选；225 张无候选 |
| 人工复核 | 待进行 |
| 定向微调 | 尚未开始 |
| Sony 实验 | 暂停 |

最新发布 [v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5) 新增 **60 张 JPEG**，编号 **fb_0635–fb_0694**：22 张有候选，38 张无候选，共 45 个原始框。[第五批详情](data/community-2026-10-25-batch05/README.zh-CN.md)。

## 下载与复核

| 批次 | 图数 | 下载 |
|---|---:|---|
| 首批快照 | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| 第二批 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |
| 第三批 | 47 | [v0.3](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v3) |
| 第四批 | 64 | [v0.4](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v4) |
| 第五批 | 60 | [v0.5](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-25-v5) |

完整 694 个资产需要下载五批。每批提供原分辨率公开副本、固定模拟输入和复核包，下载后用 `SHA256SUMS.txt` 核对。

图片包与复核包解压到同一目录，打开 `review.html`；默认英文，可切换简体中文。首批发布需用其独立 `review.html` 替换包内页面。

第三批使用 NEF **内嵌的机内 JPEG** 做审核图和预测。rawpy 路径失败 28 张后，全部 47 张统一采用此明确表示。公开 NEF 的压缩图像数据与原片一致；内嵌 JPEG 与 RAW 传感器渲染分开记录。

检查整张照片，优先复核无候选图，导出决定 JSON。正确图保留作对照，错误图进入精标。原始类号 0–5 的语义仍待确认。

编号以 [data/registry.csv](data/registry.csv) 为准。[输入转换代码](scripts/z8_input.py)、[预标注流程](docs/run-prelabel.zh-CN.md)。

## 模型与验证

本地 Z8 resource744 模型主体与 [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network) 逐字节一致，使用已验证的 CUDA 适配与本地 Z8 原厂后处理。

- 实机参考样例、真实图 CPU/GPU 对照通过逐位检查。
- 五批共 694 张图的 E7 主机解码与留存 Z8 候选记录全部一致。
- 第三批重新通过 CUDA 批量验证，GPU 网络耗时 30.40 秒，不含图片读写、后处理及复核。

第四批 GPU 网络耗时 42.59 秒，采用同一已验证批量配置；42 张 NEF 使用内嵌 JPEG，22 张 JPG 保持原始解码像素。

第五批重新通过 CUDA 批量验证：60 张 JPEG 的 GPU 网络耗时 39.09 秒，两套解码全部一致。

详见[验证报告](docs/reports/05-e7-comparison-and-cuda.zh-CN.md)和[最新执行记录](experiments/community-prelabel-2026-10-25-batch05/)。

## 下一步

- 复核漏鸟和误框，补标可见眼、头和整鸟。
- 将连拍、同曝光 RAW/JPEG 和关联图片分组，再冻结测试集。
- 用纠正样本和正常场景对照进行定向微调，与冻结的原模型比较。

## 文档

| 内容 | 入口 |
|---|---|
| 图片、清单和校验值 | [社区数据集](data/README.zh-CN.md) |
| 推理与人工复核 | [预标注流程](docs/run-prelabel.zh-CN.md) |
| 模型身份与 GPU 检查 | [验证报告](docs/reports/05-e7-comparison-and-cuda.zh-CN.md) |
| 数据归类与标注规则 | [规范 v1](docs/data/DATASET-SPEC-v1.md) |
| 固件解包与模型容器格式 | [解包说明](docs/format/UNPACK-GUIDE.md) |
| 项目执行与发布规则 | [AGENTS.md](AGENTS.md)、[NOTICE.md](NOTICE.md) |

历史方案、CUB 校准集和失败运行记录保留在仓库中供查阅。

## 致谢与许可

感谢提供照片的摄影者，以及 [WonderLantern](https://github.com/WonderLantern/e7-bird-network)、[fwtool.py](https://github.com/ma1co/fwtool.py) 和 [TIM-VX](https://github.com/VeriSilicon/TIM-VX)。完整名单见[致谢](ACKNOWLEDGMENTS.md)。

代码采用 [Apache-2.0](LICENSE)，原创文档与元数据采用 CC BY 4.0。照片版权归各自摄影者，使用范围见[数据集许可说明](data/community-2026-10-24/README.zh-CN.md#使用范围)。
