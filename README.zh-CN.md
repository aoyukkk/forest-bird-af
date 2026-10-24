# forest-bird-af

[English](README.md) | **简体中文**

优化枝叶遮挡下的鸟类自动对焦，重点处理漏鸟和误锁树枝。目标是：有可用眼锁眼，否则退到头，再退到整鸟；都不可用时释放目标。

## 当前进度

更新于 2026-10-24。

| 工作 | 状态 |
|---|---|
| 社区照片 | 523 个文件：486 JPG、7 PNG、30 NEF |
| 图像校验 | 523 份已登记原片保持不变；公开副本的像素及 RAW 采样校验通过 |
| 模拟输入数据集 | 两批合计 523 张 384 × 256 无损 RGB PNG，附留存的 CHW 输入 |
| Z8 预标注 | 本地 RTX 4080 Laptop GPU 两批完成 523/523 张，执行错误 0 |
| 候选结果 | 387 张有框，共 1262 个候选；136 张无候选 |
| 人工复核 | 已准备就绪 |
| 定向微调 | 尚未开始 |
| Sony 实验 | 暂停 |

[最新发布](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2)新增 **227 张 JPG**，编号 fb_0297–fb_0523。GPU 预标注得到 602 个原始候选，180 张有候选、47 张无候选。首批 296 张的发布保持不变。[本批说明](data/community-2026-10-24-batch02/README.zh-CN.md)。

## 下载与复核

| 批次 | 图数 | 下载 |
|---|---:|---|
| 首批快照 | 296 | [v0.1](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) |
| 第二批 | 227 | [v0.2](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v2) |

每批提供全分辨率公开副本、固定 384 × 256 模拟输入和复核包。完整 523 张需要下载两批；新包只含新增 227 张。ZIP 使用各批校验文件核对。

第二批将图片包和复核包解压到同一目录，打开 `review.html` 即可。页面默认英文，可切换简体中文。首批 v0.1 还需用该 Release 独立提供的 `review.html` 替换包内页面。

检查整张图片，优先看无候选图，结束后导出决定 JSON。正确图保留作对照，错误图进入精标。眼、头精标使用全分辨率图片，原始类号 0–5 的语义仍待确认。

累计编号使用 [data/registry.csv](data/registry.csv)。[输入格式与转换代码](data/community-2026-10-24/README.zh-CN.md#模拟输入数据集)。

## 模型与验证

本地 Z8 resource744 的模型主体与 [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network) 逐字节相同。本轮采用其数值配置和通过验证的 CUDA 适配，后处理保留本地 Z8 原厂路径。

- 公开实机参考样例、真实图 CPU/GPU 对照均通过逐位检查。
- 两批共 523 张图片的 E7 主机解码与留存 Z8 原厂候选记录全部一致。
- 首批 296 张的 GPU 网络累计 185.95 秒；新增 227 张为 143.13 秒，均不包含图片读写、后处理和人工复核。

详见[对比验证报告](docs/reports/05-e7-comparison-and-cuda.zh-CN.md)和[最新执行记录](experiments/community-prelabel-2026-10-24-batch02/)。

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
