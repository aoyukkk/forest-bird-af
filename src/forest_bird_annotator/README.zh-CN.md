# 标注服务源码

[English](README.md) | **简体中文**

| 模块 | 作用 |
|---|---|
| `server.py` | HTTP 服务与路由 |
| `store.py` | SQLite 存储、修订与并发声明 |
| `z8_review.py` | Z8 辅助复核文档、基线与逐框差异 |
| `dedupe.py` | 相似分组、队列折叠与撤销，只写 `dedupe/` |
| `importer.py` | 导入冻结 384×256 输入并校验哈希 |
| `schema.py` | 旧版精标字段校验 |
| `remote.py` | 远程访问口令网关 |
| `web/` | 零构建前端：`z8-review.*` 为默认界面，`index.html`/`app.js` 为历史精标 |

启动方式见[标注工具](../../docs/tools/annotator.zh-CN.md)。
