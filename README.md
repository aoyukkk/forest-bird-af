# 林鸟遮挡条件下的自动对焦优化

> **2026-10-24 数据工作入口**：[执行规范 AGENTS.md](AGENTS.md) · [归类、编号和人工标注方案 v1](docs/data/DATASET-SPEC-v1.md)。保留 DS 已登记的 292 个编号，新增只追加；原片不动，使用多维标签归类。当前只完成规范，未执行照片整理、增量登记、划分或标注。Sony 暂停，训练未开始。

针对树林环境中鸟类自动对焦的**遮挡场景**做定向优化：眼看得清就锁眼，眼被挡住退到头，头也被挡住退到身体，都辩不清就不锁。

本仓库公开全部研究过程——方案、数据规范、实验记录、算法改动、对照组结果，**包括失败的实验**。

## 项目要解决什么

现有自动对焦在鸟眼清晰时表现良好，但存在三类失败：

1. 枝叶穿过后**完全漏检**
2. 对焦点**锁到树叶或背景**上
3. 眼睛已被遮住，算法仍在**猜眼睛的位置**

要改善的不是"识别得更准"，而是"遮挡条件下识别与正确回退"。

## 当前进展

| 项目 | 状态 |
|---|---|
| 优化方案 | 已定稿，见 [v2 方案](docs/plan/01-forest-bird-plan-v2.md) |
| Z8 原生模型本地执行 | 通过（20/20 图，FP16 输出可重复） |
| Sony a1 II 固件解包 | 通过（v4.00，17 个网络已逐一切分） |
| Sony 模型格式解析 | 历史解析器通过 5/7；后续通过原生元数据接口读取其余两个模型 |
| Sony 模型数值运行 | 历史 CPU 工程执行通过七个模型，语义与准确率尚未验证；当前暂停，服务器项目文件已迁回本地并清理 |
| 200 张标注集 | 图片已备，人工标注待完成 |
| 成对比较、准确率 | 未开始 |
| 定向微调、训练 | 未开始 |

**关键未完成项**：Sony 数值执行成功尚不证明原生预处理、眼/头/鸟解码正确或与机身等价。目前没有经过准确率验证的跨机型教师；当前先做社区实拍人工标注准备，不恢复 Sony 或启动训练。

## 目录

```
docs/format/        固件解包流程 + .nab 容器格式规范
docs/plan/          方案（当前版本与已归档版本）
docs/findings/      调研与可行性评估
docs/reports/       解包报告、各轮试跑报告
docs/collect/       公开征集文案
data/calibration-200/  200 张标注集的元数据与规范
data/schema/        标注格式定义
experiments/        冻结的实验记录，逐轮可追溯
src/nab/            .nab 容器解析器
src/z8/             Z8 侧模型执行
src/eval/           对照与统计
```

## 开源边界

**本仓库公开方法与格式，不公开资产本体。**

| 公开 | 不公开 |
|---|---|
| 固件解包流程与版本锁定 | 厂商固件 `.DAT` / `.bin` |
| `.nab` 容器的字段级格式规范 | 厂商模型权重 `.nab` / `.vvpm` |
| 网络拓扑：形状、层数、算子统计 | 权重数值与任何可重建模型的文件 |
| 量化参数 `scale` / `fixed_pos` | 原始照片、用户投稿 |
| 解析器代码与校验方法 | 第三方仓库副本 |
| 字节偏移与 SHA-256（供比对） | |

即：任何人可以**按本仓库的文档从官方固件自行提取并校验**，本仓库提供的是这条路，不是提取结果。

详见 [NOTICE.md](NOTICE.md)。

## 复现

```bash
# 解包流程见 docs/format/UNPACK-GUIDE.md
python src/nab/nab_tool.py verify <default.nab>
```

环境：Python 3.10+，解析器仅用标准库。固件解包依赖 [fwtool.py PR #52](https://github.com/ma1co/fwtool.py/pull/52) 的作者分支提交 `3955d7890fc38daf942bb52827599bfe35de4a14`，请自行克隆。

## 不做的事

- 不发布厂商固件、厂商模型权重
- 不把"容器可解包"说成"模型可运行"
- 不把模型漏检当成负样本真值
- 不隐瞒失败的实验轮次

## 数据从哪里来

首轮 200 张来自 [CUB-200-2011](https://www.vision.caltech.edu/datasets/cub_200_2011/) 官方 train 划分，按遮挡类型分层抽样。CUB 是北美鸟种，后续需补亚洲林鸟实拍。

**本仓库不托管图片本体**，只放清单、编号映射与 SHA-256。

正在征集真实用户投稿的失败样本，见 [征集文案](docs/collect/call-for-photos.txt)。投稿原图同样不入库。

## 许可

- 代码：Apache-2.0，见 [LICENSE](LICENSE)
- 文档与标注规范：CC BY 4.0
- 数据集元数据：CC BY 4.0；图片本体各自沿用原数据集许可
- 第三方材料见 [NOTICE.md](NOTICE.md)

## 致谢

本项目的固件解包能力来自 [fwtool.py](https://github.com/ma1co/fwtool.py) 及其 [PR #52](https://github.com/ma1co/fwtool.py/pull/52)（ma1co、DavidBuchanan314，MIT）；格式交叉验证参考了 [VeriSilicon TIM-VX](https://github.com/VeriSilicon/TIM-VX)（MIT）；首轮数据来自 [CUB-200-2011](https://www.vision.caltech.edu/datasets/cub_200_2011/)。

完整的上游项目、数据集原始摄影者与工具链致谢见 [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)。

## 引用

Wah, C.; Branson, S.; Welinder, P.; Perona, P.; Belongie, S. *The Caltech-UCSD Birds-200-2011 Dataset*. California Institute of Technology, CNS-TR-2011-001, 2011.
