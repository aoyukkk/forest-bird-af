# 临时外网复核链接

[English](remote-review.md) | **简体中文**

网页和 SQLite 标注数据库继续运行在本机。密码网关通过 Cloudflare 临时隧道开放 Z8 复核页面、图片和复核接口，无需自有域名或另行部署服务器。

## 开启与分享

先启动本地标注服务，再使用 Python 3.11+：

```powershell
python scripts/share_annotator.py start --workspace <标注工作区> --cloudflared <已校验的cloudflared.exe>
python scripts/share_annotator.py status --workspace <标注工作区>
```

启动器按官方发布 SHA-256 核对 Windows AMD64 版 cloudflared 2026.10.3，隐藏启动后台进程，等待密码网关就绪并记录临时 HTTPS 地址。重复开启会复用仍在运行的链接。地址和密码保存在 `<标注工作区>/remote-access/SHARE.txt`；该目录留在本地，密码文件不公开上传。

将地址和密码发给同行。登录后在“帮助”中设置各自的复核者编号。大家编辑同一份数据，过期修订会被拒绝，避免静默覆盖。打开图片和自动保存草稿都不算确认。外网入口不开放历史 `/annotate` 精标工具和批量导入接口。“退出登录”会先保存当前草稿，再结束本次浏览器会话。

## 关闭与重新开启

```powershell
python scripts/share_annotator.py stop --workspace <标注工作区>
```

关闭命令只停止身份匹配的网关和隧道进程，本机标注台继续可用。重新启动会清除登录会话，并生成新的临时地址。同行使用期间，电脑需保持开机、联网且不休眠；关闭浏览器标签页不会关闭共享。

`remote-access/` 保存访问配置、密码、进程编号和隧道日志。停止前会检查已记录进程的命令行。网关不开放模型、固件、私人来源路径或任意文件目录，图片读取仍校验冻结哈希。

参考：[Cloudflare 临时隧道说明](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)。
