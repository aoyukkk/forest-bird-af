# NOTICE

本仓库包含或引用第三方材料。权利归属如下。

## 一、本仓库原创内容

| 内容 | 许可 |
|---|---|
| `src/` 下的解析器与实验代码 | Apache-2.0 |
| `docs/` 下的方案、报告、调研记录 | CC BY 4.0 |
| `data/` 下的清单、标注规范、元数据 | CC BY 4.0 |
| `experiments/` 下的实验记录与配置 | CC BY 4.0 |

## 二、未包含在本仓库中的材料

### 厂商固件

Nikon Z8 与 Sony a1 II 的固件镜像属于各自厂商的受版权保护资产。本仓库**不包含**、也**不提供下载**：

- `BODYDATA.DAT`（Sony a1 II 固件容器）
- `Z_8_*.bin`（Nikon Z8 固件）
- 任何解包所得的 `nflasha*` 分区镜像、`firmware.tar`、`firmware.fdat`

获取途径为厂商官方支持页面，使用条件以厂商条款为准。本项目的用途是研究设备在自有相机上的行为。

### 厂商神经网络权重

从固件中提取的神经网络模型（`default.nab` 及其中的 17 个网络、切分出的 `.vvpm` 文件）属于厂商知识产权。本仓库**不包含**这些权重，只公开：

- 容器格式的结构化描述（字段布局、偏移、类型）
- 各网络的输入输出**形状**与量化参数
- 字节偏移与哈希摘要，用于校验本地提取结果的正确性

即：公开"格式知识"与"验证方式"，不公开"资产本体"。

### 图像

`data/calibration-200/` 的 200 张图片来自 CUB-200-2011，**图片本体不入库**，只提供：

- 编号到数据集原始路径的映射
- 尺寸与 SHA-256 校验值
- 初筛分组

CUB 图片版权属于原始摄影者。CUB 发布方说明其用于非商业研究与教育用途。原图水印保留。详见 `data/calibration-200/README.md`。

### 用户投稿照片

通过公开征集获得的照片**不入库**。仅在本地用于训练与评测。入库的只有统计数字与标注规范。

## 三、引用的第三方软件

| 项目 | 许可 | 用途 |
|---|---|---|
| [fwtool.py](https://github.com/ma1co/fwtool.py) | MIT | Sony 固件容器解包，PR #52 提交 `3955d789` |
| [TIM-VX](https://github.com/VeriSilicon/TIM-VX) | MIT | NBG 格式解析，提交 `702715d7` |
| pycryptodomex | BSD-2-Clause | AES 解密 |
| PyYAML | MIT | 配置解析 |

以上均以依赖形式引用或由使用者自行获取，本仓库不复制其源码（`fwtool.py` 的 PR 分支不在本仓库内）。

## 四、数据集引用

- **CUB-200-2011** — Wah, C.; Branson, S.; Welinder, P.; Perona, P.; Belongie, S. *The Caltech-UCSD Birds-200-2011 Dataset*. California Institute of Technology, CNS-TR-2011-001, 2011. <https://www.vision.caltech.edu/datasets/cub_200_2011/>
- **NABirds** — Van Horn, G. et al. *Building a Bird Recognition App and Large Scale Dataset With Citizen Scientists*. CVPR 2015.
- **iCub (Elusive Images)** — Anderson, P. et al. WACV 2024.

## 五、声明

本项目的所有结论均限于自有设备的软件层面观察，不代表厂商设计意图，也不构成对硬件行为的证明。"可解包"不等于"可运行"，"能运行"不等于"与机身等价"。
