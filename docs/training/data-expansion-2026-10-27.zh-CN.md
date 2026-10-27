# 扩充公开数据与空场景负监督

[English](data-expansion-2026-10-27.md) | **简体中文**

本轮完成新公开数据准入、A12 本地教师入口检查和落点判别器配方对照。
冻结 YOLO26 衍生检测器，未启用替换。[实测结果](../../experiments/expansion-2026-10-27/README.zh-CN.md)。

## 来源与准入

补齐 NABirds 的六个官方训练划分镜像分片，固定修订和 SHA-256，并关联原始部位元数据。
镜像自称的许可证不覆盖 [Cornell 原始研究条款](https://dl.allaboutbirds.org/nabirds)。
本轮新 NABirds 只提供人工可见眼锚点，删除推导头框，其余位置不当背景。

[COCO](https://cocodataset.org/#termsofuse) 使用 train2017 的鸟实例掩膜和鸟身框，并筛选图片自身许可。
标注许可不等于拥有照片版权。[CCT](https://lila.science/datasets/caltech-camera-traps) 只使用
上游类别集合严格为 `empty` 的图片，不能把模型未检测到当无鸟。白天、每相机每日/每序列最多一帧，
并排除灰度或极端曝光。COCO/CCT 共下载 3,146 张原图，生成 3,053 张输入、排除 93 张。

17,410 张拟增量中准入 17,252 张，隔离 158 张，所有原文件保留。
与 16,399 个冻结输入身份对照，历史留出图仅参与哈希/缩略签名污染排查，不用其预测或标签选型。
初始准入回执把斜线不同的同路径重复计数，修订版规范路径后准入清单完全相同，旧回执保留。

像素相同，或 pHash 距离不超过 4、RGB 缩略 RMSE 不超过 .10 且全局灰度相似代理不低于 .94，
触发保守隔离。这不保证找到全部同拍摄事件或裁剪重复。新近似图直接匹配保留代表。
CCT 按相机划分：15 个地点的 172 张校准，其余 678 张参与训练。
旧社区 ID、标注和冻结划分不改。

## 监督与匹配训练

COCO 负点只在已标鸟框内、掩膜及轮廓不确定区之外，其余全图未知。
40 个输入/局部裁剪工程检查在训练前发现模糊鸟体边缘的歧义负点，失败缓存保留。
修订缓存忽略掩膜外 4 像素带，再次检查通过：22 个相同面板沿用，18 个变化面板实际查看。
推导背景半权重。工程检查不是新增人工确认，也不证明机身景深正确。

新拟合缓存有 58,235 个已知点，校准有 13,677 个含未知点。
实际有可用监督的训练帧为 NABirds 12,561、COCO 1,851、CCT 678。
准入后没有可用眼/掩膜监督的图不产生拟合帧。原 CUB/社区缓存只读保留。

两种新配方从相同初始化训练同一个 808,417 参数 RGB/上下文判别器，检测器及鸟面提议头冻结。
正例扩充配方：50% 原 CUB/社区混合、25% 新 NABirds、25% 新 COCO。
空景配方保持每次第一点及图像顺序完全相同，将 30% 负点替换为按相机、再按帧抽取的 CCT 明确空景点。
RGB 亮度抽样也相同。两种子、各 32 轮，每轮 4,096 次图像对呈现，批次 64 帧。
试跑独立，不作正式初始化。

只读内存映射训练，AdamW 学习率 .0003、衰减 .0001，加权 BCE 加 .5 倍成对 softplus，
CUDA float16 autocast、梯度裁剪 10。未知点不进拟合损失，父特征缓存，这不是全骨干训练。
正式训练前锁定缓存二进制哈希。

两组旧基线也用全部 32 个已保存轮次，在相同扩充校准集选型。
要求真实已知负例误接受不超过 1 帧、CCT 实际候选误选不超过 1 帧，再优先保留真实眼锚点，
再最大化 CUB/COCO 实际候选的“前景−5×已知错误”。NABirds 锚点接受量只作诊断。
CUB/COCO 共 2,045 个关联/内部开发视图；父模型可能在 COCO 预训练中见过图，不是新盲测。

锁定后用实际批次 1 推理重放校准空景，包含双 n 完整路由。
另做固定规则影子试验：用已选门槛只审核已有 B/H，眼保留，不选替代点。
它仅诊断规则，不是新默认策略，也不是在旧社区验证图上搜索门槛。

## A12 入口检查

11 个 SDK 库和 7 个 Sony 模型与既有锁一致，只证明文件身份。
当前照片出框查看器明确调用 Nikon Z8；真实本地 Sony 完整执行例子是量化零输入的
重识别网络，输出 64 字节 embedding。Windows NBG 包装器把输入文件字节直接复制，
没有实现其注释声称的图像预处理。检测预处理及 B/H/眼解码仍未核验，
因此 **不准入任何 A12 伪标签**。未启动新 Sony 进程、系统虚拟化改动或远程任务。

## 复现

使用已有可选 YOLO/PyTorch 环境，按许可获取源元数据/照片；输出必须为 Git 外新目录。

```text
python scripts/training/prepare_coco_cct.py --help
python scripts/training/admit_public_expansion.py --base ../old/dataset.json --nabirds ../completed/dataset.json --coco-cct ../coco-cct/dataset.json --reference ../identity-reference.json --output ../admitted
python scripts/training/prepare_expansion_ranker.py --admitted ../admitted/newcomers.json --parent ../parent.pt --surface-head ../surface.pt --output ../new-cache
python scripts/training/train_expansion_ranker.py --old-cache ../old-cache --new-cache ../new-cache --output ../pilot --condition empty --pilot-steps 200
python scripts/training/train_expansion_ranker.py --old-cache ../old-cache --new-cache ../new-cache --output ../empty-seed1 --condition empty --seed 20261027 --epochs 32 --audit ../new-cache/visual-audit.json
python scripts/training/evaluate_expansion_ranker.py --old-cache ../old-cache --new-cache ../new-cache --checkpoints ../old-baseline/checkpoints --output ../recalibrated-baseline
```

视觉回执必须来自实际检查并绑定当前缓存配置哈希。两条件、两种子重复正式训练。
评估器也可重放单个权重，输出供 `predict_bird_residual.py` 使用的哈希绑定推理校准。
照片、缓存张量、权重、人工原始导出及私人路径留在 Git 外。
没有新的真实拍摄事件测试或机身合焦验证。
