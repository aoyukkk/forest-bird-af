# forest-bird-af

[English](README.md) | **简体中文**

优化枝叶遮挡下的鸟类自动对焦，重点处理漏鸟和误锁树枝。目标是：有可用眼锁眼，否则退到头，再退到整鸟；都不可用时释放目标。

## 当前进度

更新于 2026-10-24。

| 工作 | 状态 |
|---|---|
| 社区照片 | 296 个文件：259 JPG、7 PNG、30 NEF |
| 图像校验 | 296 份原片保持不变；公开副本的像素及 RAW 采样校验通过 |
| 模拟输入数据集 | 296 张 384 × 256 无损 RGB PNG，附实际留存的 CHW 输入字节 |
| Z8 预标注 | 本地 RTX 4080 Laptop GPU 完成 296/296 张，执行错误 0 |
| 候选结果 | 207 张有框，共 660 个候选；89 张无候选 |
| 人工复核 | 已准备就绪 |
| 定向微调 | 尚未开始 |
| Sony 实验 | 暂停 |

图片包与复核包已在 [Releases](https://github.com/aoyukkk/forest-bird-af/releases/tag/community-images-2026-10-24-v1) 提供下载。[数据集说明](data/community-2026-10-24/README.zh-CN.md)。

复现实验可下载同一 Release 中的 `z8-inputs-384x256-20261024.zip`。296 张 PNG 的像素均与留存的模拟输入逐字节一致；全分辨率图片继续由四个社区图片包提供。[输入格式与转换代码](data/community-2026-10-24/README.zh-CN.md#模拟输入数据集)。

## 下载与复核

1. 在 Release 下载四个 `community-images-20261024-partXX-of04.zip` 和 `SHA256SUMS.txt`，解压到同一目录，合并 `images/`。
2. 将 `z8-prelabels-review-20261024.zip` 解压到同一目录，再把 Release 单独提供的 `review.html` 复制进去，替换包内页面。页面默认英文，可切换简体中文。
3. 检查整张照片，优先查看 89 张无候选图。将结果记为正确、需要修改或不确定。
4. 导出复核决定 JSON。正确图保留作对照，错误图进入精标队列。

复核页支持原图与带框图切换、筛选、备注和决定导出。决定先保存在浏览器中，结束前请导出。眼和头的精标使用完整分辨率图片。

当前框保留模型原始类号 0–5，眼、头、整鸟的语义对应仍待确认。

## 模型与验证

本地 Z8 resource744 的模型主体与 [WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network) 逐字节相同。本轮采用其数值配置和通过验证的 CUDA 适配，后处理保留本地 Z8 原厂路径。

- 公开实机参考样例、真实图 CPU/GPU 对照均通过逐位检查。
- 两种解码器在本批 296 张图上的候选记录全部一致。
- 五个 GPU 网络批次累计 185.95 秒，不包含图片读写、后处理和人工复核。

详见[对比验证报告](docs/reports/05-e7-comparison-and-cuda.zh-CN.md)和[执行记录](experiments/community-prelabel-2026-10-24/)。

## 下一步

- 复核漏鸟和误框，补标可见眼、头和整鸟。
- 将连拍、同曝光 RAW/JPEG 和关联图片分组，再冻结测试集。
- 用纠正样本和正常场景对照进行定向微调，与冻结的原模型比较。

## 文档

| 内容 | 入口 |
|---|---|
| 图片、清单和校验值 | [社区数据集](data/community-2026-10-24/README.zh-CN.md) |
| 推理与人工复核 | [预标注流程](docs/run-prelabel.zh-CN.md) |
| 模型身份与 GPU 检查 | [验证报告](docs/reports/05-e7-comparison-and-cuda.zh-CN.md) |
| 数据归类与标注规则 | [规范 v1](docs/data/DATASET-SPEC-v1.md) |
| 固件解包与模型容器格式 | [解包说明](docs/format/UNPACK-GUIDE.md) |
| 项目执行与发布规则 | [AGENTS.md](AGENTS.md)、[NOTICE.md](NOTICE.md) |

历史方案、CUB 校准集和失败运行记录保留在仓库中供查阅。

## 致谢与许可

感谢提供照片的摄影者，以及 [WonderLantern](https://github.com/WonderLantern/e7-bird-network)、[fwtool.py](https://github.com/ma1co/fwtool.py) 和 [TIM-VX](https://github.com/VeriSilicon/TIM-VX)。完整名单见[致谢](ACKNOWLEDGMENTS.md)。

代码采用 [Apache-2.0](LICENSE)，原创文档与元数据采用 CC BY 4.0。照片版权归各自摄影者，使用范围见[数据集许可说明](data/community-2026-10-24/README.zh-CN.md#使用范围)。
