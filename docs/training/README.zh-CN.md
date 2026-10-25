# 训练代码说明

本目录的脚本是本地检测头微调所用的实际代码。**仓库不含厂商模型包、CUDA 权重、
标注数据库和照片**，因此这些脚本在这里只保证结构完整、参数说明准确，不保证在
缺依赖的环境下能直接跑通。

## 脚本分工

| 脚本 | 作用 | 依赖 |
|---|---|---|
| [prepare_z8_training.py](../../scripts/prepare_z8_training.py) | 只读备份标注库与去重记录，按关联组冻结训练/验证/测试划分，缓存原生骨干特征并逐位校验 | 原厂模型包、CUDA、Pillow |
| [train_z8_heads.py](../../scripts/train_z8_heads.py) | 冻结骨干、只更新原检测头允许的参数行，导出候选 body 并读回核对 | 同上 + 冻结后的数据目录 |
| [evaluate_z8_training.py](../../scripts/evaluate_z8_training.py) | 选型锁定后一次性打开测试集，原厂与候选都过原 BA2 后处理 | 同上 |
| [probe_z8_finetune.py](../../scripts/probe_z8_finetune.py) | 有限步数可训练性试验，确认梯度路径可用 | 同上 |
| [probe_z8_multibird.py](../../scripts/probe_z8_multibird.py) | 多鸟图片的候选行为观察 | 同上 |
| [benchmark_z8_candidate.py](../../scripts/benchmark_z8_candidate.py) | 原厂与候选的批量吞吐对比 | 同上 |
| [z8_probe_labels.py](../../scripts/z8_probe_labels.py) | 原生查表与候选标签适配 | 原厂模型包 |
| [z8_trainable_heads.py](../../scripts/z8_trainable_heads.py) | 可训练头张量、梯度掩码与 body 导出 | torch |
| [z8_training_targets.py](../../scripts/z8_training_targets.py) | 目标分配、负样本构建、指标匹配与推导监督 | torch、numpy |
| [export_z8_labels.py](../../scripts/export_z8_labels.py) | 生产库 → 可发布标签，剔除私有字段 | 标准库 |
| [export_split_manifest.py](../../scripts/export_split_manifest.py) | 冻结划分 → 可发布清单 | 标准库 |
| [verify_annotations.py](../../scripts/verify_annotations.py) | 离线校验已发布标签与划分 | 标准库 |

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
- 每轮结束检查允许范围外的 FP16 参数是否被改动，出现非零即判失败。
- 导出体量与原始 body 相同，仅检测头允许范围内的字节变化。

## 结果与发布边界

实测数字见[原生检测头微调](z8-native-head-finetune.zh-CN.md)，未发布产物见
[未发布内容](../releases/not-published.zh-CN.md)。

## 最小复跑路径

```bash
python scripts/prepare_z8_training.py --help
python scripts/train_z8_heads.py --help
python scripts/evaluate_z8_training.py --help
```

`--help` 不需要原厂包即可查看完整参数；真正执行需要本机已校验的模型包与 CUDA，
并且输出目录必须留在仓库之外。
