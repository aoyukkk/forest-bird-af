# 用 Antigravity 中的 Gemini 做首次初标（流程 v2）

[English](gemini-first-pass.md) | **简体中文** · [完整提示词](gemini-first-pass-prompt.zh-CN.md)

目标：Gemini 逐张看输入图并目视检查最终叠框，再提交 AI 初标；你在标注台里修改并复核。执行细则见 [流程 v2](ai-annotation-workflow-v2.zh-CN.md)。

新版默认先验证 5 张新图。上一轮既有结果只读生成全批人工复核清单和叠框，不自动返工，不直接继续全量。

## 1. 准备工作区

在本机 Antigravity 中打开项目仓库，选择你准备使用的 Gemini 模型。使用可以执行终端并查看图片的会话；只输出文字建议的会话不能完成此任务。

把项目仓库和本地标注工作区加入同一项目可访问的文件夹：

- 仓库：包含 `scripts/annotator_client.py` 和 `docs/annotator.zh-CN.md`。
- 标注工作区：包含 `images/`、`annotations.sqlite3` 和 `import-validation.json`。

使用本机环境，`127.0.0.1:8765` 指的是这台电脑；在远端执行的会话不能直接访问它。初标只需输入 PNG，不需要开放整个固件目录。

如果 Antigravity 提示目录越界，授权所需的标注目录即可。Google 官方说明项目目录和外部文件访问受权限设置控制，且 Windows 设置与其他平台可能不同；不必为标注任务切换到无限制权限。[官方 Agent settings](https://antigravity.google/docs/agent-settings)

图片需要被当前所选 Gemini 实际看见。Google 文档提供图片附件和图片预览功能，但具体可用工具取决于你的安装和会话；提示词会要求先验证，无法看图就停止写标签。[官方更新说明](https://antigravity.google/docs/changelog)

## 2. 启动已有标注工具

运行本机的一键启动入口，或在 PowerShell 中执行：

```powershell
& "<PYTHON_EXE>" "<REPO_ROOT>/scripts/launch_annotator.py" --workspace "<ANNOTATION_WORKSPACE>" --no-open
Invoke-RestMethod http://127.0.0.1:8765/api/health
```

健康检查应返回 `ok=true`、实际图片数和 `schema_version=forest-bird-input-manual-v1`。不要再次执行 `init` 来覆盖工作区，也不要使用历史测试端口 8766。

## 3. 给 Gemini 发什么

打开[完整提示词](gemini-first-pass-prompt.zh-CN.md)，替换配置区的三处路径，再把代码块全文粘贴到 Gemini 会话。

默认 `STAGE=calibration`、`LIMIT=5`、`CHECKPOINT_EVERY=5`、`BULK_APPROVED=false`。只验证 5 张待标、零修订、未被他人领取的新图；原有标注保留。`REVIEW_EXISTING_RUN` 填上一轮运行目录，没有则留空。模型会为上一整批生成复核材料，包含 annotated。

校准试跑完成后交付你检查。首批 40 张规则校准并经你明确确认后，才设置 `STAGE=bulk`、`BULK_APPROVED=true`，建议 `LIMIT=20`；明确要求全量时才设 all_pending。LIMIT 是本轮额度，续跑继承已分配的 ID，不重新获得 5 张，也不改变训练／测试划分。普通断点无需重复确认。

初标优先用接口提交，界面供你检查；无需让 Gemini 对着浏览器逐个拖框。Gemini 可以用已有客户端，也可直接调用同一 API：

```powershell
Set-Location "<REPO_ROOT>"
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 schema
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 list --status pending --limit 20
# 单图示意；实际目录由 Gemini 在本次 ai-runs 目录中创建。
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 get fb_0008 --output "<RUN_DIR>/fb_0008-edit.json"
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 image fb_0008 --output "<RUN_DIR>/fb_0008.png"
# 实际看图并填写 annotation 后再执行 save；不是下载完就直接提交模板。
& "<PYTHON_EXE>" scripts/annotator_client.py --actor gemini-antigravity-pass1-v2 save "<RUN_DIR>/fb_0008-edit.json"
```

`list --limit 20` 只限制终端显示条数，不是完整队列；完整队列从 `GET /api/dataset` 读取。通用 `claim` 也可能领取 draft，本轮按提示词只处理 pending/revision=0，不用它盲选任务。

## 4. 正常运行时会得到什么

Gemini 应先备份数据库，然后在以下位置建立独立运行目录：

```text
<ANNOTATION_WORKSPACE>/ai-runs/gemini-pass1-v2-<UTC时间>/
  run.json            本轮配置、模型名称和候选 ID
  ledger.jsonl        逐图查看、提交与失败记录
  checkpoint.json    已完成和剩余 ID
  proposals/          提交前保存的最终建议
  overlays/           当前输入全图和头部局部叠框
  validation/         包含警告的校验响应
  readbacks/          服务器读回与完整比较结果
  review-existing/    上一整批只读复核材料
  ...                 实际目录可不同，但每份材料必须可追溯
```

每张必须把建议画回当前输入，实际查看最终叠框；修改后重新渲染并查看。眼框默认 null，不能统一生成 4×4 方框；相邻图片坐标完全相同触发独立复查。提交前保存建议及证据，提交后完整比较业务内容，而不只核对状态和哈希。

标注本体仍由 API 保存到既有数据库，标注者为 `gemini-antigravity-pass1-v2`、类型为 AI。清楚且完成全图检查的图片进入“已初标”；关键不确定项进入“需裁决”。不会直接成为“已复核”。

提示词要求独立看输入图，第一次不看 Z8 框、不看原图，因此 `review_decision=unassessed`、`reference_consulted=false` 是正常结果。输入看不清的眼不因为原图有细节就补上。

## 5. 你怎样检查

打开 [本地标注台](http://127.0.0.1:8765)。AI 新提交后，队列会定期刷新；如果当前图片有新版提示，点“载入最新”。需要时刷新网页，先确保自己的草稿已保存。

1. 在“使用帮助”里设置你自己的标注者编号，操作者类型选“人工”，与 Gemini 区分。
2. 首批校准及存在关键错误的上一整批全部检查，不能只检查“需裁决”。先独立看输入判断鸟、头和眼，再显示 AI 标注比较。
3. “已初标”也可能错位；重点检查整批眼点和重复几何组。隐藏 Z8 框检查，完成独立判断后需要比较时再打开。
4. 重点检查：有没有漏鸟，眼是否真的可见，头框是否包含可见喙，整鸟框是否遗漏可见尾足，鸟和部位是否属于同一个体，对焦点是否落在树枝上。
5. 修改后状态回到草稿，重新完成初标，再点“通过复核”；如果完成初标后自动切走，按编号返回这张图再复核。不要把“几何合法、保存成功”当作“识别准确”。

“有眼锁眼、没眼锁头、没头锁身”是目标优先级；能看见的鸟、头、眼仍全部标注。可靠头／鸟回退不因没眼自动变成待裁决。只有一名人工时如实记录“AI 初标加人工复核”，不声称独立双人。

## 6. 中断、冲突与续跑

| 情况 | 处理 |
|---|---|
| 无法真正查看 PNG | 停止写标注；修复图片查看能力后再跑，不以空标签代替 |
| 本地服务连不上 | 用已有启动器恢复；不要新建空数据集 |
| HTTP 409 | 保留建议、记冲突，跳过；不强行覆盖人工修改 |
| 提交超时或读回失败 | 记录 save_unknown，完整对账后决定是否重试；不查询就不能判失败或再次提交 |
| 坐标校验失败 | 返回该张图修正，不自动扩大框或制造眼框 |
| 上下文或模型配额用完 | 让 Gemini 保存 checkpoint 和剩余 ID，新会话继续 |
| 已有草稿或标注 | 默认跳过；确需返工时另给明确的图片 ID，不整批覆盖 |

新会话可发送：

```text
继续流程 v2 的同一轮校准，不新增额度。读取完整新版提示词和我指定运行目录的 run.json、ledger.jsonl、checkpoint.json。
保留 STAGE=calibration、BULK_APPROVED=false，沿用原来分配给五张额度的 ID；只处理其中未完成且仍 pending/revision=0/无人领取的图片，不另选五张。
先对账 save_unknown、失败和服务器已保存但流水缺失的记录，再决定下一步；已有草稿、初标、裁决和人工改动全部保留，不重复写入。
每张都执行当前图片的最终叠框目视自检，完整读回比较，沿用 actor=gemini-antigravity-pass1-v2。完成本轮额度后停止并交付人工校准，不自动扩量。
若指定的是旧版运行目录，只读生成整批复核材料，按新版另建五张校准目录，不能复用旧版提交逻辑或修改历史运行。
```

这段续跑指令不会自动返工上次的未保存 draft。相关 draft 保留，明确列入跳过清单，之后单独处理。

## 7. 导出

你可以在界面“导出／备份”中导出全部工程记录、已初标／已复核记录或仅已复核记录。命令行等价入口：

```powershell
& "<PYTHON_EXE>" "<REPO_ROOT>/scripts/annotator_client.py" export --scope all --output "<ANNOTATION_WORKSPACE>/exports/after-gemini-all.jsonl"
& "<PYTHON_EXE>" "<REPO_ROOT>/scripts/annotator_client.py" export --scope reviewed --output "<ANNOTATION_WORKSPACE>/exports/human-reviewed.jsonl"
```

导出为 JSONL，保留实例关联、眼点、可见性、来源和修订；当前不自动变成原厂六槽训练目标。具体训练适配在人工检查和原模型目标边界明确后再做。
