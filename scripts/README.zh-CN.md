# 脚本

[English](README.md) | **简体中文**

按任务分组。所有脚本只依赖标准库或已在 `docs/training/README.zh-CN.md` 说明的环境；
涉及原厂模型包与 CUDA 的脚本需要自备，仓库不含厂商资产。

## pipeline/ — 从原片到预标注

| 脚本 | 作用 |
|---|---|
| `prepare_community_release.py` | 稳定编号登记与来源映射 |
| `extract_verified_rar.py` / `extract_verified_zip.py` | 解压并逐文件校验哈希，完成后删除压缩包 |
| `sanitize_jpeg.py` | 去除 JPEG 元数据段，保留压缩采样、色彩与方向 |
| `finalize_community_release.py` | 图片完整性校验、NEF 审核图、公开副本打包 |
| `nef_review.py` | 校验 TIFF 压缩图像数据并提取机内 JPEG |
| `z8_input.py` / `package_z8_inputs.py` | 生成固定 384×256 模拟输入 |
| `prelabel_community.py` | Z8 原厂后处理推理 |
| `validate_e7_backend.py` / `validate_e7_batch.py` | 模型身份、CPU/GPU 一致性、批量配置校验 |
| `package_prelabels.py` / `build_review_page.py` | 打包候选与复核页面 |

## annotator/ — 本地标注服务

| 脚本 | 作用 |
|---|---|
| `annotator.py` | 初始化工作区、导入冻结输入 |
| `launch_annotator.py` | 启动本地服务（默认 127.0.0.1:8765） |
| `remote_annotator.py` / `share_annotator.py` | 远程协作访问 |
| `dedupe_annotator.py` | 去重扫描与队列折叠 |
| `verify_annotator_workspace.py` | 工作区结构与哈希校验 |

## training/ — 原生检测头微调

`prepare_z8_training.py`、`train_z8_heads.py`、`evaluate_z8_training.py`、
`probe_z8_finetune.py`、`probe_z8_multibird.py`、`benchmark_z8_candidate.py`，
配套 `z8_probe_labels.py`、`z8_trainable_heads.py`、`z8_training_targets.py`、`e7_backend.py`。
方法与结果见[训练](../docs/training/README.zh-CN.md)。

## publish/ — 生产库到公开文件

| 脚本 | 输出 |
|---|---|
| `export_confirmed_labels.py` | 全部人工确认标注（JSONL/CSV/COCO/YOLO） |
| `export_z8_labels.py` | 694 条逐图记录 |
| `export_split_manifest.py` | 冻结训练/验证/测试划分 |
| `export_dedupe_queue.py` | 去重队列清单 |
| `export_best_images.py` | 复核优先顺序清单 |
| `export_label_formats.py` | 单条记录的 COCO/YOLO 转换 |

## tools/ — 校验与诊断

| 脚本 | 作用 |
|---|---|
| `verify_repo.py` | 扫描仓库是否误入厂商资产或照片 |
| `verify_annotations.py` | 校验标签、划分、队列、确认导出与敏感字段 |
| `verify_review_page.mjs` | 复核页静态检查 |
| `compare_saved_decoders.py` | 两套解码器输出对比 |
