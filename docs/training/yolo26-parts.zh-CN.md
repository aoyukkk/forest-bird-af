# YOLO26 鸟类部位实验

[English](yolo26-parts.md) | **简体中文**

这是一条独立于原厂权重的本地训练路线，输出鸟/头框和眼点。它使用官方 YOLO26
pose 的骨干、颈部及 one-to-many 分支，修改为两个框类别和无左右语义的眼点网格。
**它不是原封不动的 YOLO26 检测/pose 模型，也不是已验证的 Z8 机身替换文件。**

## 数据与依赖

- [CUB-200-2011](https://www.vision.caltech.edu/datasets/cub_200_2011/) 提供鸟框和部位点。
- [NABirds](https://dl.allaboutbirds.org/nabirds) 的原始鸟框和部位点可扩充训练。
  必须核对镜像图片 ID、尺寸和官方划分；镜像许可证不能覆盖 Cornell 的原使用条件。
- 社区数据沿用 375 训练、80 验证、80 历史测试。旧测试不参与本轮选型。
- 第三方图片只在本地研究使用；仓库提供代码和来源，不重新分发它们。

复用已有 CUDA PyTorch 环境，另需 [requirements-yolo26.txt](../../requirements-yolo26.txt)。
本地实测为 Python 3.12、PyTorch 2.7.0.dev20250117+cu126、NumPy 1.26.4、Pillow 11、
OpenCV 4.11、Ultralytics 8.4.189、PyArrow 17。安装依赖前检查现有环境，避免改掉已验证的 torch/CUDA。

## 脚本

| 脚本，均在 `scripts/training/` | 用途 |
|---|---|
| `prepare_public_community.py` | 公开标签/划分/PNG → 社区输入清单，无需厂商包 |
| `prepare_bird_parts.py` | CUB 与社区输入 → 384×256 部分标注数据 |
| `import_nabirds_parts.py` | 已校验 parquet 原图与原始部位元数据按 ID 匹配导入 |
| `prepare_yolo26_weights.py` | 官方预训练权重 → 有种子、哈希的初始化快照，CPU 执行 |
| `bird_parts_model.py` | 部分标注损失、推导背景、增强、模型和解码 |
| `train_bird_parts.py` | 本地训练、验证选型、父权重保留、稀疏正点蒸馏及读回 |
| `evaluate_bird_parts.py` | 锁定后公开域测试，原生输出与 BA2 交叉检查 |
| `predict_bird_parts.py` | 独立候选推理，使用验证阈值，无需厂商包 |

`--help` 给出实际参数。假设仓库外工作区为 `../forest-bird-work`，先把 Release 的
冻结输入放到该工作区的 `review/images/`，再执行：

```text
python scripts/training/prepare_public_community.py --labels data/annotations-2026-10-25/labels/community-corrections-v1.jsonl --split data/annotations-2026-10-25/splits/evaluation-split-v1.json --registry data/registry.csv --inputs ../forest-bird-work/review/images --output ../forest-bird-work/community.json
python scripts/training/prepare_bird_parts.py --cub ../public-data/CUB_200_2011 --community ../forest-bird-work/community.json --workspace ../forest-bird-work/review --output ../forest-bird-work/parts
python scripts/training/prepare_yolo26_weights.py --output ../forest-bird-work/initialization
python scripts/training/train_bird_parts.py --dataset ../forest-bird-work/parts/dataset.json --pretrained ../forest-bird-work/initialization --output ../forest-bird-work/run-n --size n --epochs 40 --batch-size 32
```

正式实验还应先筛查跨划分近重复，并保存数据哈希、初始化哈希和实际执行源码。
本轮历史初始化快照已保存并共用于各对照；其最初生成新层时的种子没有记录，精确重放
需要同一快照，不能只凭训练 seed 重建。新初始化工具会记录生成 seed。

## 监督与增强规则

- 输入为冻结 RGB 384×256、除以256，眼点不变成固定像素眼框。
- 鸟/头使用 TAL 框监督。眼在 stride-8 网格上每格提供两个无序假设，单独监督坐标和置信度。
  只用细网格眼输出，未使用官方 RLE 和 one-to-one 路径；必须使用本项目解码器。
- 未标部位是未知。头或眼单独可见时，不要求虚构鸟身框。
- 公共推导头框是弱标签；分类降权为0.35，几何仍依赖粗框假设。去掉公共粗头框的对照用于检验它的影响。
- 仅人工复核且有鸟框的社区图可推导保护区域外背景。全部框、眼点、疑似区域都受保护；
  头/眼单独可见而无鸟框的图不提供全图背景，公共主鸟标注也不启用此假设。
- `--augment` 加翻转、缩小、模糊和小遮挡；`--scale-match` 使用社区**训练**目标尺寸分布缩小公共鸟图。
  中位色填充画布有合成外观，不能当作真实林间背景。缩小或模糊后不再可用的眼置未知。
- `--teacher` 使用 s 模型的高置信正点指导；`--teacher-threshold` 控制门槛。
  教师点还必须在现有人工眼点4px以内，漏报不生成负例，不创建未知图片的“人工真值”。

## 评价与边界

阈值和轮次只按社区验证选。报告鸟/头 IoU .5 与 .3、眼2/4/8px、阈值曲线、候选覆盖及
假设的 E→H→B 选择诊断。重复候选与错误位置分别解释；未知可用性不能当作正确回退。
单张 GPU 时间和原生算术模拟器时间均不代表机身 NPU 或镜头合焦速度。

公开域测试的输入与候选在打开前锁定。CUB 原始眼可见性和输入尺度启发式不是新的人类盲审；
公开图像也可能与厂商或通用预训练资料重叠。公开域结果不能替代新的真实林鸟测试。


## 许可与精确重放

YOLO 路线实际集成 Ultralytics 代码及预训练权重，遵循其
[AGPL-3.0 / Enterprise 条件](https://www.ultralytics.com/license)。
仓库原创代码的 Apache-2.0 不替代上游条款。CUB/NABirds 仍受原研究用途条件约束；
不重新发布其原图及 NABirds 逐图标注。

`evaluate_bird_parts.py` 要求本次记录的实验工作区布局，包括选型清单、初始化快照和原生修复目录，
不是通用的标准 Ultralytics 评估命令。它持久化原生输出，使用 CPU 多进程对每个缓冲区执行原始 BA2
指令核对；另在三张图上检查原生批量/单图一致，以及修复权重完整读回一致。
只有锁定资产和阈值完全相同时才允许恢复。


## 使用候选

准备选中的 `best.pt`，以及包含 `thresholds`（bird/head/eye）的JSON；
训练输出 `validation-best.json` 已有该字段：

```text
python scripts/training/predict_bird_parts.py --weights ../forest-bird-work/run-n/best.pt --calibration ../forest-bird-work/run-n/validation-best.json --image bird.jpg --output ../forest-bird-work/prediction.json
```

直接创建自定义结构并严格加载全部状态，推理不需要初始化快照或厂商模型。
按EXIF方向转RGB、双线性拉伸至384×256，返回输入像素坐标。默认CUDA，CPU须显式
`--device cpu`；RAW先按项目JPEG路径渲染。不会覆盖已有输出或输入。
不能用标准 `yolo predict` 直接代替，也不是相机固件或镜头控制器。
