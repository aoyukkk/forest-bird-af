# 训练代码说明

[English](README.md) | **简体中文**

这里包含原生检测头微调，以及独立的 [YOLO26 部位模型](yolo26-parts.zh-CN.md) 训练代码。
**仓库不含厂商模型包、模型权重、特征缓存、生产数据库或照片本体。**

原生路线的 `prepare_z8_training.py` 读取本地 SQLite、预标注运行和来源分组映射；
公开 JSONL 不能直接替代这些私有输入。YOLO 路线现有 `prepare_public_community.py`，
可以从公开标签、冻结划分及已下载的输入 PNG 建立社区数据入口，不需要厂商包。
它不会加载旧测试的标签和像素。两条路线的输出都保存在仓库外。


本轮结果见 [2026-10-26 对照与复盘](next-round-2026-10-26.zh-CN.md)：包含原生修复对照、
公共鸟类部位数据、n/s 模型、增强、稀疏正点蒸馏及锁定后的公开域测试。


## 脚本分工

| 脚本 | 作用 | 依赖 |
|---|---|---|
| [prepare_z8_training.py](../../scripts/training/prepare_z8_training.py) | 只读备份标注库与去重记录，按关联组冻结训练/验证/测试划分，缓存原生骨干特征并逐位校验 | 原厂模型包、CUDA、Pillow |
| [train_z8_heads.py](../../scripts/training/train_z8_heads.py) | 冻结骨干、只更新原检测头允许的参数行，导出候选 body 并读回核对 | 同上 + 冻结后的数据目录 |
| [evaluate_z8_training.py](../../scripts/training/evaluate_z8_training.py) | 选型锁定后一次性打开测试集，原厂与候选都过原 BA2 后处理 | 同上 |
| [probe_z8_finetune.py](../../scripts/training/probe_z8_finetune.py) | 有限步数可训练性试验，确认梯度路径可用 | 同上 |
| [probe_z8_multibird.py](../../scripts/training/probe_z8_multibird.py) | 多鸟图片的候选行为观察 | 同上 |
| [benchmark_z8_candidate.py](../../scripts/training/benchmark_z8_candidate.py) | 原厂与候选的批量吞吐对比 | 同上 |
| [z8_probe_labels.py](../../scripts/training/z8_probe_labels.py) | 原生查表与候选标签适配 | 原厂模型包 |
| [z8_trainable_heads.py](../../scripts/training/z8_trainable_heads.py) | 可训练头张量、梯度掩码与 body 导出 | torch |
| [z8_training_targets.py](../../scripts/training/z8_training_targets.py) | 目标分配、负样本构建、指标匹配与推导监督 | torch、numpy |
| [export_z8_labels.py](../../scripts/publish/export_z8_labels.py) | 生产库 → 可发布标签，剔除私有字段 | 标准库 |
| [export_split_manifest.py](../../scripts/publish/export_split_manifest.py) | 冻结划分 → 可发布清单 | 标准库 |
| [verify_annotations.py](../../scripts/tools/verify_annotations.py) | 离线校验已发布标签与划分 | 标准库 |

## 关键参数

```text
--dataset            冻结数据目录（含 split-lock.json、dataset.json、cache-report.json、features/）
--upstream           本机已校验的原厂模型包
--workspace          384×256 输入 PNG 所在工作区
--z8-package         含 z8models 的原厂执行器包
--output             训练产物目录，必须在原厂包、标注库和公开仓库之外
--update-mode        all | eye-class-only | eye-small-anchor
--preservation       原输出保持约束权重
--background-weight  推导背景眼负监督
--precision-guard    要求验证眼精确率不低于原厂且背景区眼候选不增加
--head-local-weight  头框内局部眼负监督
--min-epochs         定向长训练的最少轮数，不放宽选型
```

## 梯度与数值边界

- 前向保留原生 dot/add 与 FP16 存储，训练可重复的动点仍在原生数值路径上。
- 反向使用 STE 近似：FP16 量化与整数运算的真实导数没有求出，只能声明近似方向可用。
- 梯度掩码限制更新范围；选中的 checkpoint 在导出前检查范围外 FP16 参数变化，非零即失败。
- 导出体量与原始 body 相同，仅检测头允许范围内的字节变化。

## 结果与发布边界

实测数字见[原生检测头微调](z8-native-head-finetune.zh-CN.md)，未发布产物见
[未发布内容](../releases/not-published.zh-CN.md)。

## 最小复跑路径

```bash
python scripts/training/prepare_z8_training.py --help
python scripts/training/train_z8_heads.py --help
python scripts/training/evaluate_z8_training.py --help
```

`--help` 不需要原厂包即可查看完整参数；真正执行需要本机已校验的模型包与 CUDA，
并且输出目录必须留在仓库之外。

最新后续轮：[输入、困难上下文和混合方案结果](input-context-2026-10-26.zh-CN.md)。新训练未超过保留的父模型；五视图眼点融合是更昂贵的开发候选。


[最终引导位置实验](guidance-2026-10-26.zh-CN.md)新增缓存CPU重评、定位质量置信度和从同一父权重开始的匹配对照。

[落点可用性与离线确认](point-review-2026-10-26.zh-CN.md)：51项人工确认（44可用、7不可用），AI草稿独立保存，保留低门槛补位失败规则。

[冻结原模型的鸟面分支实验](surface-2026-10-27.zh-CN.md)：共享特征的轻量头、部分掩膜、明确遮挡监督及两个种子的匹配协议。

[RGB与上下文剩余候选排序](residual-2026-10-27.zh-CN.md)：容量、真实困难负例、内部校准及实际推理计时，仍不推荐替换。

[公开数据扩充与空景训练](data-expansion-2026-10-27.zh-CN.md)：来源准入、明确空景监督、匹配落点抽样及A12教师未准入。

[主检测器背景微调](main-background-2026-10-27.zh-CN.md)：直接训练 B/H 骨干和检测头，对照空景负监督，固定独立眼模型。

[分类头保真微调](classification-guard-2026-10-28.zh-CN.md)：固定特征和框回归，训练侧困难回放、关联场景隔离与匹配空景监督。

[信息与尺度诊断](information-diagnostic-2026-10-28.zh-CN.md)：区分真实高清、低清放大、已知位置与自动局部，包含完整策略时间和停止追加训练的依据。
