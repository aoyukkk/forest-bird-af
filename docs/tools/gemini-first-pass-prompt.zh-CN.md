# Gemini 首次初标提示词

[English](gemini-first-pass-prompt.md) | **简体中文** · [使用说明](gemini-first-pass.zh-CN.md)

复制下方整个代码块给本机 Antigravity 的 Gemini。把配置区替换成你的路径。本机已经配置好的副本由交付说明提供。

```text
你正在本机 Antigravity 中执行林鸟对焦数据集的第一次视觉初标。请直接完成以下工作，不要只返回方案。初标之后由我人工检查。

【配置】
PROJECT = <REPO_ROOT>
PYTHON = <PYTHON_EXE>
WORKSPACE = <ANNOTATION_WORKSPACE>
BASE_URL = http://127.0.0.1:8765
ACTOR = gemini-antigravity-pass1-v2
STAGE = calibration
LIMIT = 5
CHECKPOINT_EVERY = 5
BULK_APPROVED = false
REVIEW_EXISTING_RUN = <上一轮运行目录；没有则留空>

【版本与本轮目标】
执行流程 v2。默认只标 5 张新图并停在人工校准阶段，不自行扩量。已有上一轮标注只读检查、生成全批复核清单和叠框图，不能自动重写。
先读 PROJECT/docs/overview/ai-annotation-workflow-v2.zh-CN.md；旧提示词、旧 run_helper.py / batch_worker.py 和旧检查点不能覆盖本版规则。可以在新运行目录内写符合 v2 的执行辅助脚本，不修改历史运行文件。

【范围】
只处理这个本地标注工具里的 384×256 冻结输入图，不处理其他目录中的素材。
你可以读项目规范、调用本地标注 API、目视读取输入 PNG，并在 WORKSPACE/ai-runs/ 下保存本次图片缓存、逐图记录和报告。通过 API 写入你的 AI 初标。
本任务不修改工具源码、原片、冻结预测或数据库文件，不做训练、蒸馏、Sony 分析、远程服务器任务或 GitHub 发布，也不另行部署视觉服务或申请 API key。
当前所选 Gemini 负责看图；不得用脚本、文件名、模型框或模板代替逐图视觉判断。单个代理顺序处理，不启动其他标注代理。

【准备】
1. 阅读 PROJECT/AGENTS.md、PROJECT/docs/tools/annotator.zh-CN.md、PROJECT/docs/overview/ai-annotation-workflow-v2.zh-CN.md 和本提示词。
   旧的“仅制定规范、不得部署”阶段说明已被本地标注工具授权覆盖。当前授权是通过既有工具完成 AI 初标，不是改写原片或训练。
2. GET BASE_URL/api/health，确认服务正常、schema_version=forest-bird-input-manual-v1。
   如果未启动，仅使用已有 PYTHON 与 PROJECT/scripts/annotator/launch_annotator.py，带 --workspace WORKSPACE --no-open 启动；不重新初始化数据，不安装其他工具。
3. GET /api/schema 和 /api/help，读取实际字段、枚举与模板。GET /api/dataset 读取当前数量，不把文档快照当作实时图片数。
4. POST /api/backup，JSON 为 {}，记录返回的快照文件名。
5. 在 WORKSPACE/ai-runs/ 下创建本次独立目录 gemini-pass1-v2-<UTC时间>。写入 run.json：实际模型名称（无法读取时写 unknown）、actor、输入尺度、开始时间、工作区标识、STAGE、LIMIT、BULK_APPROVED、完整候选 ID、占用本轮额度的 ID、旧运行目录与旧标签复核范围。无法核实实际模型配置就写 unknown，不猜版本。
6. REVIEW_EXISTING_RUN 非空时，读取其配置、流水、检查点并与实时状态对账；为上一轮实际成功的所有图片生成人工复核清单、当前修订号、原始输入与现存标注叠框对照。包含 annotated，不只列 needs_adjudication。新目录保存这些复核材料，既有标签和历史不改；发现人工更新就记录当前版本，不恢复旧版本。

【选图与不覆盖规则】
启动时从 GET /api/dataset 返回的 images 数组，只选 status="pending"、revision=0、claimed_by=null 的条目，按 image_id 顺序形成固定候选列表。注意队列字段叫 status，单图 annotation 对象里的字段才叫 annotation_status。不要用 Z8 有无框或得分选择真值。
calibration 且 BULK_APPROVED=false 时，只从固定列表选最多 LIMIT=5 张作为新图验证，写进 run.json；五张额度包括正在处理和等待重试的图，续跑不得重新选五张。完成或因问题停止后交付人工校准，不自动继续。
只有用户明确确认人工校准并授权扩量，才可配置 STAGE=bulk、BULK_APPROVED=true；建议 LIMIT=20。只有用户明确要求全量才使用 all_pending。不能把普通“继续”解释为解除未完成的校准。
每张写入前重新 GET /api/annotations/{id}。只有它仍为 pending 且 revision=0，才允许写入；其他图片一律跳过并说明原因，包括人工草稿、AI 已有初标、已复核和待裁决记录。
不使用通用 claim 命令替代这个筛选：现有领取接口也可能返回 draft，而本轮不覆盖 draft。
你只有一个工作者，使用逐图修订检查即可。HTTP 409 时保留本次建议，记入冲突清单；不要改成最新 revision 后强行重试。

【必须实际看图】
每张先取得 /api/annotations/{id} 的完整对象与哈希，再通过 /api/images/{id}/png 获取输入 PNG。用你的图像查看能力逐张查看，不能只读取文件或图片元数据就算看过。
如果实际无法查看图像内容，先停止标注写入并报告缺少的能力，不生成批量空标注或猜测框。
第一次初标不请求原图参考，也不打开或读取 Z8 预测框。保持 reference_consulted=false、review_decision=unassessed。
可以普通放大或裁切同一张输入图，优先使用最近邻 4×/8× 显示；不使用超分、生成补全或 AI 锐化。放大只帮助看已有像素，不创造眼睛。
若在裁切/放大视图上判断，必须把坐标换回原 384×256：x=x0+x_view/s，y=y0+y_view/s。所有保存坐标仍是输入图像素，不能把显示坐标或千分制坐标直接写入。

【具体标注规则】
1. 看完整张图，找出所有可确认为鸟的个体，每只鸟独立 instance_id：b1、b2……。标全部可辨鸟，不只标最明显的一只。
2. bird_bbox_xyxy 框住该鸟所有有证据的可见片段，包括可见头、翅、尾、足；不是只框躯干，也不补画被挡住的轮廓。框内可能有枝叶，不代表每个像素都是鸟。
3. 头能可靠定位时画 head_bbox_xyxy，包含可见喙；头不可定位则 null。
4. 每只实际可定位的眼标 center_xy，眼框默认 bbox_xyxy=null。仅当本图输入能辨清眼边界时独立测量后补框；严禁用眼中心 ±2、固定半径或统一 4×4/其他尺寸批量生成眼框。不猜隐藏眼，不可定位则不标眼。每鸟最多两眼；side 按鸟自身左右，拿不准写 unknown。
5. 鸟、头、眼同时可辨时全部标，不是只标眼。target 按 eye→head→body 回退：
   - 眼可定位：af_reference_target_input=eye，af_anchor_input_xy 选一只可见眼的中心。
   - 眼不可定位、头可定位：target=head，anchor 落在实际可见的头部上。
   - 头也不可定位、鸟可定位：target=body，anchor 落在实际可见鸟体上。
   - 确认有鸟但没有可用部位：target=none，anchor=null，说明原因。
   - 目标本身不确定：target=unknown，anchor=null，提交待裁决。
   不把矩形中心机械当对焦点；中心若是树枝或背景，应选择其他可见鸟体位置。
6. part_visibility 分别记录 bird/head/eye。被挡、背向、失焦、运动模糊、太小、压缩和出画分开。没有遮挡证据时不把模糊眼记为被挡：可见性用 unknown，并记录 defocus/too_small 等实际原因；hidden 不能替代所有“没看清”。
7. 仅在实际有遮挡时填写 occluder_types 与 occluded_parts；枝叶背景不自动表示遮挡。原因字段使用 /api/schema 中的枚举。
8. 无法确认是否为鸟的区域放 uncertain_regions，写具体原因；不得为了完成任务把疑似目标变成干净负样本。若确定鸟和疑似区域同图存在，可同时保留。
9. 只有完整检查后确认无可辨鸟且无疑似区域，才写 presence=absent、instances=[]、uncertain_regions=[]。
   确定有鸟用 presence=present；只有疑似目标用 presence=uncertain。没有看过、无法打开或执行失败，不等于 absent。
10. 标注空间只代表输入图。不要基于原图、同一连拍的另一帧或“这类鸟应该有眼”推断本张输入中看不见的部位。无需强制识别鸟种。

【逐图叠框自检：提交前必须完成】
先保存建议 JSON，再用它在当前输入 PNG 上绘制鸟框、头框、眼点、可选眼框和 anchor；保存叠框全图及必要头部局部图。不得复用上一张的底图或裁切。
逐张实际查看最终叠框，检查漏鸟、可见尾足、可见喙、眼点是否在眼部、实例对应及 anchor 是否落到枝叶/背景。修改坐标后重画并重新查看最终版本；只生成图、不目视，不算自检。
记录输入哈希、每份视图路径/哈希、crop_xyxy、scale、输出尺寸及简短自检结果。必须核对裁切坐标和视图尺寸；保存坐标仍为 384×256。
相邻图片几何完全相同时强制重新核对当前图，记录 duplicate_geometry_with 和核对结果。同连拍不是通过理由，也不能为消除重复告警人为改动正确坐标。
没有完成看图和叠框自检，不提交 annotated；保留建议和未完成原因并停止本轮写入，不能降低状态来绕过视觉能力检查。

【字段与提交】
以 GET 返回的 annotation 对象为基础修改，保持 schema_version、image_id、annotation_image、哈希、输入尺寸、preprocess_id 与 split=null 不变。字段模板不是已标注数据，里面的示例坐标不能照抄。
按 /api/schema 构造实例、眼和疑似区域；填好 part_visibility、invisibility_reasons、occluder_types、occluded_parts、target、anchor、needs_review 和简短 notes。
target_mode 可设 auto，但 API 不会替你计算 target/anchor，必须显式填写并自行核对。眼点用作 anchor 时可设 anchor_mode=auto；头/鸟身选择实际点时用 manual。
保持 ID 稳定，更新 id_counters.bird / uncertain 和每个实例的 next_eye_id，不重排或复用已用编号。
不要把 six slots 当六个人工类别，也不要给 slot 5 随意创建躯干框。

清楚且完成全图及最终叠框检查的图片：annotation_status=annotated。没有可定位眼但头/鸟回退可靠，也可 annotated，不因“没眼”自动提交裁决。
有关键语义/定位疑问：只保留可靠部分，在相关实例或疑似区域中标 needs_review=true，整图 annotation_status=needs_adjudication，notes 写明疑问。不靠降低真实性来“凑齐”字段。
无法查看或执行失败：不提交假标签，保持当前状态并记录失败。
永远不写 reviewed；review 保持 null。最终复核由我完成。

每张先 POST /api/validate，body={image_id,annotation}，保存完整响应及 warnings。接口只返回 valid/issues，不返回规范化后的 annotation，不依赖不存在的返回字段。修正结构或坐标问题；部位超出鸟框等警告要回看图片，不要自动扩大框掩盖问题。结构校验通过不等于视觉准确。
PUT 前落盘最终建议、实际看图/叠框自检记录和校验结果，并再次 GET 确认仍为 pending/revision=0；同时复查领取状态，已被他人领取则跳过。
再用 PUT /api/annotations/{id}，body={base_revision:0,annotation,actor:{id:ACTOR,kind:"ai"}}。
成功后重新 GET，逐字段比较完整 annotation，仅排除服务端管理的 provenance、review；另外必须确认 review=null，provenance.actor.id=ACTOR、kind=ai、revision=base_revision+1、parent_revision=base_revision。核对全部输入身份、状态、presence、每只鸟的全部框/眼/anchor/可见性及 split=null，不能只比较计数、状态或哈希。对象键顺序不影响比较，数组及数值内容必须一致。保存请求、响应、读回及比较结果，只有全部一致才能记为保存成功。
若 PUT 超时或读回失败，记录 save_unknown，先 GET 对账：只有预期修订、作者及完整内容相符才补记成功；仍为原修订且资格未变时可有限重试相同建议；任何其他新修订按冲突处理，不改 base_revision 强行覆盖。无法查询就保留未决项并暂停写入。
API 不可用时保留已完成的建议文件，不能绕过 API 直接写 SQLite。

【进度、恢复与报告】
逐张保存建议并向 ledger.jsonl 追加事件，包含 UTC、attempt_id、image_id、输入哈希、实际视图路径/变换/哈希、viewed、overlay_checked、自检结论、建议/校验/读回文件、base_revision、保存 revision、结果及失败/冲突原因。布尔值不能在辅助函数里硬编码或默认 true，未实际查看就不写 true。
每 CHECKPOINT_EVERY 张及退出前保存 checkpoint.json，通过临时文件写完后原子替换；按 image_id 去重并与服务器 revision 对账，列出成功、待裁决、跳过、冲突、可重试失败、save_unknown 及剩余 ID。保留完整候选表和占用本轮额度的 ID，不能逐条累计重试事件而重复计数。数据库已有成功但流水缺失时补对账事件，不重复写入。
每张推断都独立查看当前图，不从上一张坐标直接复制。可以复用执行代码，不能复用未经核对的视觉结论。
若上下文、配额或服务中断，保存已完成工作并报告准确的下一张 ID。没有处理完就不能宣布全量完成。
结束时仅导出本次运行实际成功的 image_id+revision 对应记录；同 actor 的其他运行也不能计入本次。列出本轮全批人工检查项与上一批全批复核清单，不只列 AI 自认为不确定的图片。
用中文分别报告：实际看图、最终叠框自检、结构校验、保存成功、人工复核的数量，以及待裁决、跳过、冲突、失败、未决与剩余数量；注明本轮阶段和额度，给出目录与导出位置。放大次数按实际记录写；用“输入清晰/眼可定位”等描述，不从输入断言机身合焦准确，不报告未经人工测量的准确率。
校准完成后交付并停止。首批校准和已有关键错误批次人工全检，完成首批 40 张校准并得到用户确认后才扩量。本轮不改既有生产标签，不能自行绕过此限制。

现在先检查本地服务与实际图像查看能力，然后按上述流程开始。
```
