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

## training/ — 原生检测头与 YOLO26 部位模型

`prepare_z8_training.py`、`train_z8_heads.py`、`evaluate_z8_training.py`、
`probe_z8_finetune.py`、`probe_z8_multibird.py`、`benchmark_z8_candidate.py`，
配套 `z8_probe_labels.py`、`z8_trainable_heads.py`、`z8_training_targets.py`、`e7_backend.py`。
方法与结果见[训练](../docs/training/README.zh-CN.md)。

独立的 [YOLO26 路线](../docs/training/yolo26-parts.zh-CN.md)使用
`prepare_public_community.py`、`prepare_bird_parts.py`、`import_nabirds_parts.py`、
`prepare_yolo26_weights.py`、`bird_parts_model.py`、`train_bird_parts.py`、
`evaluate_bird_parts.py`、`predict_bird_parts.py`。它输出鸟/头框和眼点，训练无需厂商权重；
原生对比评价器另需本地已验证厂商包。

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
| `verify_links.py` | 检查 Markdown 相对文件目标和移动后的文档链接 |
| `verify_review_page.mjs` | 复核页静态检查 |
| `compare_saved_decoders.py` | 两套解码器输出对比 |

后续轮新增 `evaluate_bird_regions.py`、`bird_parts_regions.py`、`prepare_hard_bird_context.py`、`hard_bird_context.py`、`evaluate_bird_hybrid.py`、`predict_bird_hybrid.py`，见[输入/上下文结果](../docs/training/input-context-2026-10-26.zh-CN.md)。


引导位置工具：`bird_guidance_metrics.py`（标准库最终位置代理）、`evaluate_guidance_predictions.py`（CPU缓存重评）、`train_bird_guidance.py`（匹配继续训练）、`predict_bird_guidance.py`（无需厂商包的一/两个独立模型推理）。见[引导位置评测](../docs/training/guidance-2026-10-26.zh-CN.md)。

落点复核新增`annotator/build_point_review.py`、`point_review_core.js`、`point_review_template.html`和`annotator/import_point_review.py`。导入器核对输入/落点身份、完整修订与明确人工确认，原始导出保存在Git外；生成HTML及内嵌照片也不入Git。`training/bird_guidance_fallback.py`仅复现未通过的空候选补位规则，不改已有推理默认行为。[人工结果与工具](../docs/training/point-review-2026-10-26.zh-CN.md)。

鸟面分支新增`training/bird_surface.py`、`prepare_bird_surface.py`、`train_bird_surface.py`、`predict_bird_surface.py`，接入CUB掩膜、冻结原模型、单独训练粗捕获头。[协议与命令](../docs/training/surface-2026-10-27.zh-CN.md)。

RGB/上下文排序新增 `training/bird_residual.py`、`prepare_bird_residual.py`、`train_bird_residual.py`、`predict_bird_residual.py`、`benchmark_bird_residual.py`。[部分监督、匹配对照与命令](../docs/training/residual-2026-10-27.zh-CN.md)。

公开扩充新增 `training/prepare_coco_cct.py`、`admit_public_expansion.py`、`prepare_expansion_ranker.py`、`train_expansion_ranker.py`、`evaluate_expansion_ranker.py`。[来源许可、部分监督与命令](../docs/training/data-expansion-2026-10-27.zh-CN.md)。

主检测器微调新增 `training/prepare_main_background.py`、`train_main_background.py`、`evaluate_main_background.py`，评估会重载两个真实网络，并可计时完整单图推理。[方法与命令](../docs/training/main-background-2026-10-27.zh-CN.md)。

分类头微调新增 `training/prepare_classification_guard.py`、`train_classification_guard.py`。[训练侧困难定义、明确场景隔离与复现](../docs/training/classification-guard-2026-10-28.zh-CN.md)。
