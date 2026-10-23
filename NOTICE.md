# NOTICE

本仓库公开**方法、格式知识与验证方式**，不公开**资产本体**。

---

## 一、本仓库原创内容与许可

| 内容 | 许可 |
|---|---|
| `src/` 下的解析器与实验代码 | Apache-2.0 |
| `docs/` 下的方案、报告、格式文档 | CC BY 4.0 |
| `data/` 下的清单、标注规范、元数据 | CC BY 4.0 |
| `experiments/` 下的实验记录与配置 | CC BY 4.0 |

---

## 二、明确不包含的资产

### 2.1 厂商固件

Nikon Z8 与 Sony a1 II 的固件镜像属于各自厂商的受版权保护资产。本仓库**不包含、不提供下载**：

- `BODYDATA.DAT`（Sony a1 II 固件）
- `Z_8_*.bin`（Nikon Z8 固件）
- 任何解包产物：`firmware.tar`、`firmware.fdat`、`nflasha*` 分区镜像

获取途径为厂商官方支持页面。

### 2.2 厂商神经网络权重

从固件中提取的神经网络模型（`default.nab` 及其包含的 17 个网络、切分所得的所有网络文件）属于厂商知识产权。

**本仓库公开什么：**

| 公开内容 | 具体形式 |
|---|---|
| 容器格式 | 字段布局、偏移、数据类型、结构关系 |
| 网络拓扑 | 网络数量、每个网络的输入输出**形状**、层数与算子类型统计 |
| 量化参数 | `scale` 值、`fixed_pos` 字段值 |
| 校验依据 | 字节偏移、文件大小、SHA-256 摘要 |
| 提取方法 | 从官方固件到切出网络文件的完整可复现步骤 |

**本仓库不公开什么：**

- 权重 payload 的任何字节
- 权重数值、任何可重建模型的文件
- 解密的固件镜像

**核心边界：公开"格式知识"与"验证方式"，不公开"资产本体"。**

任何人都可以按 [UNPACK-GUIDE.md](docs/format/UNPACK-GUIDE.md) 从官方固件自行提取，并用 [NAB-FORMAT.md](docs/format/NAB-FORMAT.md) 第 8 节的四项校验确认自己提取正确。本仓库提供的是这条路，不是目的地。

### 2.3 图像

`data/calibration-200/` 的 200 张图片来自 CUB-200-2011，**图片本体不入库**，只提供：

- 编号到数据集原始路径的映射
- 尺寸与 SHA-256 校验值
- 初筛分组

CUB 图片版权属于原始摄影者，发布方说明用于非商业研究与教育。详见 `data/calibration-200/README.md`。

### 2.4 用户投稿照片

通过公开征集获得的照片**不入库**。仅在本地用于训练与评测，入库的只有统计数字与标注规范。

### 2.5 第三方代码副本

`fwtool.py`、`z8-qemu`、`NikonFirmwarePatch` 等均以**引用方式**使用，本仓库不复制其源码。

---

## 三、引用的第三方软件

| 项目 | 许可 | 用途 | 固定版本 |
|---|---|---|---|
| [fwtool.py](https://github.com/ma1co/fwtool.py) | MIT | Sony 固件容器解密解包 | PR #52 提交 `3955d7890fc38daf942bb52827599bfe35de4a14` |
| [TIM-VX](https://github.com/VeriSilicon/TIM-VX) | MIT | NBG 格式交叉验证 | 提交 `702715d714277376d7ff466b7b72833ff57564c1` |
| pycryptodomex | BSD-2-Clause | AES 解密（fwtool 依赖） | — |
| PyYAML | MIT | 配置解析（fwtool 依赖） | — |

**固件容器解密不是本项目的工作。** 我们使用公开项目提供的解密能力，本项目的工作是核实其对本机型的适用性，并独立完成 `.nab` 容器格式的逆向与文档化。

---

## 四、数据集引用

- **CUB-200-2011** — Wah, C.; Branson, S.; Welinder, P.; Perona, P.; Belongie, S. *The Caltech-UCSD Birds-200-2011 Dataset*. California Institute of Technology, CNS-TR-2011-001, 2011. <https://www.vision.caltech.edu/datasets/cub_200_2011/>
- **NABirds** — Van Horn, G. et al. *Building a Bird Recognition App and Large Scale Dataset With Citizen Scientists*. CVPR 2015.
- **iCub (Elusive Images)** — Anderson, P. et al. WACV 2024.

---

## 五、声明

本项目的所有结论均限于自有设备的软件层面观察，不代表厂商设计意图，也不构成对硬件行为的证明。

- "可解包"不等于"安全启动签名通过"
- "可解析容器"不等于"模型可执行"
- "能离线运行"不等于"与机身行为等价"

已撤回的早期判断记录在 `docs/reports/03-pilot-run-002.md`，保留原始错误供追溯。
