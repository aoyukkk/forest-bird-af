# 固定结构与格式的原生 E7 继续微调

[English](native-return-2026-10-29.md) | **简体中文**

[结果与固件证据](../../experiments/native-return-2026-10-29/README.zh-CN.md)。
用户已确认：结构、权重格式与部署接口不变，允许独立副本微调原有参数。
本轮回到原生resource744，不使用独立YOLO替代网络。

## 原生执行与修改范围

骨干冻结；前向保持原生FP16存储及dot/add算术，反向用明确声明的STE近似。
沿用`eye-small-anchor`掩码，只允许原有2,130个参数更新：眼类别行，以及第一个
细尺度锚的0–9通道。共享锚参数可能影响鸟/头输出，因此实际评估，不预先宣称不变。
辅助类及未允许参数保持原值，每步限制相对原权重偏移±.5并恢复冻结项。

导出只改副本中原检测头矩阵/偏置的既有字节范围。模型体长度、命令流、描述符、
骨干和原生消费者保持不变；厂商权重与固件不公开。

## 匹配对照

复用冻结原生缓存，隔离后续场景审计中疑似关联的21张训练图；本轮加载354张训练、
80张旧验证，不加载测试张量，不改旧划分。两个条件均从原厂权重开始，同种子图片顺序一致。

- 普通微调／定位质量感知，各两个种子，各16轮，batch32、AdamW学习率.0003。
- 两组均使用既有部分正例监督、可恢复的明确删除候选，以及强度10的原输出保持。
  缺少部位标签不生成背景负例。
- 质量条件额外在已标眼的分配锚点上，以`exp(-距离平方/(2×6平方))`监督眼类别。
  距离按384×256输入像素计算，在质量类别损失中停止距离梯度；坐标仍由既有坐标损失学习。
- 不加网络、不加裁剪分支、不作图片变换、不改消费者分数表。

选型评价最终落点，固定E/H/B=.6/.5/.4。几何支持不低于原厂，框外落点、明确无鸟选点、
已知眼错误与未知眼晋升数不增加；合格项再依次比较支持帧、4px眼命中、眼错误与严格宏F1。
未知眼仍是未知，晋升上限是保守采用条件，不能证明新点错误。

## 复现

提供本地独立核验资产，输出使用仓库及原片/生产标注目录之外的新目录，复用固定conda环境。

```text
python scripts/training/train_native_guidance.py --dataset ../private-native-cache --upstream ../private-native-package --regions ../work/regions-validation.json --exclude ../work/excluded-fit.json --output ../work/control-20261029 --condition control --seed 20261029 --epochs 16
python scripts/training/train_native_guidance.py --dataset ../private-native-cache --upstream ../private-native-package --regions ../work/regions-validation.json --exclude ../work/excluded-fit.json --output ../work/quality-20261029 --condition quality --seed 20261029 --epochs 16
```

另以20261030种子分别运行，输出新目录。`--pilot --epochs 1`只跑两批，不作为正式初始化。
本次保存64个轮次权重及其原消费者输出。另选的事后诊断候选仅供落点复核，不是正式替换模型。

同格式候选的空景回放：

```text
python scripts/training/evaluate_native_empty.py --dataset ../work/main-dataset.json --upstream ../private-native-package --body-copy ../work/diagnostic/resource744.finetuned.body.bin --output ../work/native-candidate-empty
```

加载器拒绝骨干/指令或体积变化。沿用172张CCT旧校准，不称新独立测试。
复核页复用既有明确人工确认工具，绑定新的输入哈希和落点，不自动写生产库或接受为训练真值。

固件探针和原始反汇编留本地。公开汇总区分合成控制流核验与真实图片表现；
这些结果均不能作为机身检测频率或光学合焦率。
