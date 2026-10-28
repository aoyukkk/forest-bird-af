# 信息与尺度诊断

[English](information-diagnostic-2026-10-28.md) | **简体中文**

[实测结果与决策](../../experiments/information-diagnostic-2026-10-28/README.zh-CN.md)。
本轮不更新权重，先区分输入信息、尺度/上下文、自动区域发现和标注边界问题。

## 输入与保护

复用已有固定 Python/PyTorch/Ultralytics 环境，提供独立核验的原厂包、80张社区区域清单、
扩充开发清单、保留的B/H与眼权重、父轮评价和冻结原厂验证输出。生产数据库只读打开，
比较五张表的逻辑快照。输出必须是仓库外新目录，不能放进原片目录。

社区只允许`community_val`；空景固定为已有172张CCT `public_val`。不读取历史测试。
新接收单图没有确认标签，不用于本轮。

## 复现命令

将示例路径替换为本地已验证资产。命令读取本地文件，不下载模型、不改环境。

```text
python scripts/training/diagnose_bird_information.py --regions ../work/regions-validation.json --dataset ../work/main-dataset.json --box ../work/parent-box.pt --eye ../work/parent-eye.pt --parent-evaluation ../work/parent-evaluation.json --native-validation ../work/native-validation.json --upstream ../private-native-package --database ../private-annotation/annotations.sqlite3 --output ../work/information-diagnostic
python scripts/training/evaluate_information_routes.py --dataset ../work/main-dataset.json --regions ../work/regions-validation.json --box ../work/parent-box.pt --eye ../work/parent-eye.pt --diagnostic ../work/information-diagnostic --downloads ../public-downloads/CCT --output ../work/information-routes
python scripts/training/evaluate_native_empty.py --dataset ../work/main-dataset.json --upstream ../private-native-package --output ../work/native-empty
python scripts/training/render_information_review.py --regions ../work/regions-validation.json --diagnostic ../work/information-diagnostic --output ../work/information-review
```

顺序运行以隔离计时。本次原图CCT推理与原厂诊断曾并行，使用`--wait-for-diagnostic`
等待诊断完成后才开始完整策略测速；原厂空景回放又在测速完成后开始。
被中止的串行尝试保留，不覆盖、不冒充成功结果。

## 坐标与指标

独立模型解码新增显式输入大小和眼点抑制半径，默认384×256、4像素行为不变。
768×512前向采用8像素抑制，全部输出先映射回384×256再评分，已知眼误差容忍不翻倍。
原厂显式中心与框边界同时映射，防止裁剪后仍使用旧局部中心。

已知位置裁剪使用所有鸟框；无鸟框时取头框，只回答“已给位置后能否识别”。自动区域仅用
B/H预测，分数≥.1、鸟优先、扩1.5倍、最小宽64、3:2、区域IoU>.7去重、最多两个。
两条自动策略都保留原父模型已有输出，只在其完全无输出时额外推理，推理不读取标签。

固定分母报告几何支持、已知眼错误、未知眼、逐帧增益/损失和组均值。CCT同时按帧与机位
统计，不能只取有利指标。未标眼、框外点和AI诊断均不自动变成背景真值。
两处标注边界建议保持待人工复核，不修正分数、不写生产库。

## 本轮退出条件与限制

两条自动补位策略在旧开发证据上均被拒绝，未继续训练、搜索阈值、导出替换模型或部署。
没有进行768尺度重训或重新校准，不能将失败归因于容量上限或声称高分训练必然无效。
新事件测试、机身编译器与算子、ISP、工作内存、检测频率及镜头反馈仍未验证。

实验目录发布执行源码哈希。实际核对原厂与父轮输出、原图重建、生产表和受保护资产；
166项测试通过。图片、预测、权重、数据库与私有路径留在Git外。
