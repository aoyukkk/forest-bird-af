# 本地林鸟标注工具

[English](annotator.md) | **简体中文**

外网同行协作见[临时访问链接](remote-review.zh-CN.md)：服务和数据库继续留在本机，通过密码网关与临时 HTTPS 链接访问，无需自有域名。

人和 AI 共用的本地浏览器工具，标注冻结的 **384×256 Z8 模拟输入图**。界面默认简体中文，可切换英文；不依赖在线服务，不自动调用外部模型。

**当前默认流程（2026-10-25）**：首页改为 [Z8 辅助人工纠错](z8-review.zh-CN.md)，默认显示 Z8 框，人工明确确认后才判定正确。旧 LLM 标签保留在 `/annotate`。下方精标界面和接口仍在历史入口使用。

## 打开工具

使用 Python 3.11+ 和 Pillow，本机现有 `machine` conda 环境已满足要求。界面和 AI 接口共用本地服务，无需安装 Node 包或部署 Docker。

```powershell
python scripts/annotator.py init --workspace <本地标注目录> --runs <已有预标注运行目录>
python scripts/launch_annotator.py --workspace <本地标注目录>
```

第一次导入逐张核对注册表、冻结参考图和 CHW 输入哈希，生成可逐字节还原原推理输入的 PNG。重复导入保留已有人工标注与修订。以后完成新素材登记和 Z8 预测后，用同一命令增量导入。

启动器后台运行服务并打开 `http://127.0.0.1:8765`。同一工作区重复启动会复用服务；其他端口可加 `--port`。关掉网页不影响服务，电脑重启后重新运行启动器即可。服务只接受本机连接。

## 去重（一键标记重复图）

标注页的「去重」是一键操作：把**当前图**记为与**编号相邻的上一张**重复，从队列里折叠，
然后自动跳到下一张可见图。已有标注、修订历史和原片都不受影响，只是不再重复检查。

| 按钮 | 位置 | 作用 |
|---|---|---|
| 去重 | 右上角、底栏「与上一张重复」 | 当前图 → 上一编号图，折叠并前进 |
| 撤销去重 | 右上角、底栏 | 把当前图放回队列，只有被折叠的图可点 |
| 去重管理 | 右上角 | 重新扫描、展开相似组、保留本图、手填代表图编号 |

- 第一张图没有上一编号，按钮自动禁用。
- 上一编号本身已被折叠时，会自动追到它的根图，不会出现互相指向。
- 「去重管理」里的自动扫描是保守分组，只折叠证据充分的帧；明显姿态、虚焦、遮挡变化仍保留，
  因此不要把相似分组当成已确认的连拍身份。
- 「导出已确认可用记录（去重）」只排除折叠图，完整导出仍包含全部记录。
- 想回到全部图片：取消「隐藏重复图」，或在左侧筛选里选「重复」。

## 历史精标流程（`/annotate`）

1. 左侧按编号、批次、状态或“Z8 无候选”筛选图片。**默认隐藏 Z8 候选框**，需要时打开上方开关。
2. **B 画鸟框、H 画头框、E 点可见眼中心**。每只鸟用独立实例编号；给头、眼加标注前选中所属鸟。标全能辨认的部位，不只标最优先部位。
3. 眼边界清楚时，选中眼点后补眼框；不造固定像素眼框，不推测隐藏眼。左右指鸟自身左右，不能确定就选方向未知。
4. 在右侧记录可见性、遮挡物、被遮挡部位和不可定位原因。优先目标自动按眼→头→鸟身生成，也可手动指定；头或鸟身回退时，用 **P** 在实际可见部位标参考对焦点，不机械取框中心。
5. 不确定目标用 **U** 框疑似区域。只有检查完整张图并确认无鸟时，点“已检查：无鸟”。没标、疑似和确定无鸟分别保存。
6. 点“完成初标并下一张”，再由人工单独复核。自己复核自己的结果会明确记录为非独立自复核。AI 初标不能直接标记为人工已复核。

选中框可拖动、拖四角调整大小，右侧可以精确输入坐标。**V** 选择，**F** 适应窗口，滚轮缩放，空格＋拖动平移，Ctrl+Z 撤销，Ctrl+Shift+Z 重做，Delete 删除选中形状，左右箭头切图，Enter 完成初标。输入文字时保持正常编辑快捷键。

每次修改稍停后自动保存到 SQLite；成功保存会新增修订，不覆盖历史。“修订历史”可把旧内容恢复成新草稿。本机还有未保存草稿缓存。遇到多人或 AI 同时写入，工具提示冲突并保留本机内容，不能静默覆盖。

**当前标签和可见性只描述 384×256 输入。** 原图通过只读窗口查看，并记录“已查看参考图”；如果眼只有原图放大才可见，不应当把它标成输入上也能定位。原图标注规范与此输入标注分开，不直接混作同一真值。

Z8 框是独立参考层：0／4 是鸟身区域变体，1 是头，2／3 是方向相关的眼候选，5 是鸟身关联的附属区域。可逐个采用为鸟框、头框或眼点，再人工修正；没有批量提升为人工真值的按钮。原厂各槽的训练边界尚未完全明确。

## AI 如何操作

在本机 Antigravity 使用 Gemini 时，见[首次初标提示词与使用说明](gemini-first-pass.zh-CN.md)，并执行 [AI 初标流程 v2](ai-annotation-workflow-v2.zh-CN.md)：默认 5 张校准，每张实际查看最终叠框，眼框默认 null，完整读回核对；已有标签保留，首批人工全检后再扩量。

浏览器和 AI 使用同一个 REST API。标注者编号用于本地溯源，不是登录认证；此服务面向可信任的本机用户与 AI 进程。

```powershell
python scripts/annotator_client.py help
python scripts/annotator_client.py schema
python scripts/annotator_client.py list
python scripts/annotator_client.py claim --zero-only
python scripts/annotator_client.py get fb_0008 --output edit.json
python scripts/annotator_client.py image fb_0008 --output input.png
# 检查图片，修改 edit.json 中的 annotation，保留图像身份和 revision。
python scripts/annotator_client.py --actor vision-local save edit.json
python scripts/annotator_client.py export --scope all --output labels.jsonl
```

CLI 写入者始终记为 `kind=ai`。工具提供图片读取、任务领取与标注写入，不会自动接入收费视觉模型。AI 读取图片后自行生成初标；人可以在界面里继续修改、复核。

AI 操作浏览器时，在“使用帮助 → 操作者类型”选择 AI 并设置编号；人工也可在这里设置自己的标注者编号，窄窗口下同样可用。

- `GET /api/dataset`：队列与状态。
- `GET /api/images/{id}/png`：输入图片；`GET /api/images/{id}` 读取图像身份和原始候选。
- `GET /api/annotations/{id}`：当前标注与修订号。
- `PUT /api/annotations/{id}`：提交 `base_revision`、完整 `annotation` 与 `actor`。
- `POST /api/claim`、`POST /api/release-claim`：领取和释放任务，默认十分钟到期。领取只是协作提示，写入仍以修订校验为准。
- `POST /api/import`：整批校验、整批提交；任一修订冲突则整批不写入。
- `GET /api/history/{id}`：全部修订。
- `GET /api/export?scope=all|complete|reviewed`：全部工程记录、已初标／已复核、仅人工已复核的原生 JSONL。
- `POST /api/backup`：创建一致的本地数据库快照。
- `GET /api/help`：接口发现与说明。
- `GET /api/schema`：机器可读的字段枚举及鸟、眼和疑似区域模板。

AI 应先读修订再提交；过期修订返回 409。不要把 actor 写成人工以绕过复核状态。

## 保存在哪里

```text
<工作区>/
  images/                     冻结的 384×256 输入 PNG
  annotations.sqlite3         当前标签及不可覆盖的修订历史
  import-validation.json      导入校验
  backups/                    数据库快照
  server-process.json         服务进程与本地地址
  server.stdout.log
  server.stderr.log
```

格式为 `forest-bird-input-manual-v1`，每条绑定 PNG 哈希、CHW 输入哈希和固定预处理 ID。坐标采用输入像素 xyxy，右下边界不包含；点满足 `0≤x<384, 0≤y<256`。`af_reference_target_input` 和 `af_anchor_input_xy` 与原图字段明确区分。数据划分保持空。

原生 JSONL 保留实例、眼点、可见性、不确定状态和修订号，支持修改后重新导入。训练格式转换留到后续适配，不把所有可见鸟外接框直接当成原厂每个 slot 的训练目标。

完整复制工作区即可保留输入图片、数据库和历史。恢复快照前先停止对应服务，把当前数据库连同 WAL／SHM 文件保留为恢复副本，再在独立工作区中验证快照；不要在服务运行时直接替换数据库。原图参考使用本地路径，迁移机器后可重新导入以更新参考路径。

## 验证

```powershell
python -m unittest discover -s tests -p test_annotator.py -v
node --check src/forest_bird_annotator/web/app.js
python scripts/verify_repo.py
git diff --check
```

测试覆盖人／AI 并发写入、批量冲突回滚、像素和哈希一致、人工复核限制、漏标对焦点、未标与无鸟区分、任务领取及数据库备份。界面验收使用独立测试工作区，避免把测试框混入正式标注。
