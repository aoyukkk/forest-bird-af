# 固件解包流程

从 Sony 官方固件到获得 `.nab` 网络资产包的完整步骤。

**本文只讲方法。固件原文件与解包产物均不在本仓库内。**

---

## 前置条件

| 项 | 要求 |
|---|---|
| 固件来源 | 厂商官方支持页面，自行下载 |
| Python | 3.10+ |
| 依赖 | `pycryptodomex`、`pyyaml` |
| 磁盘 | 解包产物约为固件的 3 倍，建议预留 5 GB |

```bash
pip install pycryptodomex pyyaml
```

---

## 步骤 1：获取解密工具

Sony 的 DAT/FDAT 容器解密**不是本项目的工作**，使用公开项目：

```bash
git clone --filter=blob:none https://github.com/DavidBuchanan314/fwtool.py.git
cd fwtool.py
git checkout 3955d7890fc38daf942bb52827599bfe35de4a14
```

**必须固定这个提交。** 这是 PR #52 的作者分支 HEAD，PR 本身仍 open、未合并到 master。用默认分支会缺少新版机型的容器支持。

该提交对应的 PR：[ma1co/fwtool.py#52](https://github.com/ma1co/fwtool.py/pull/52)

---

## 步骤 2：执行解包

```bash
python fwtool.py unpack -f <固件路径> -o <输出目录>
```

典型输出：

```
Decrypting firmware image
Extracting files
Unpacking .../firmware.tar
Unpacking .../0700_part_image/dev/nflasha15
Unpacking .../updater.img
```

### 如何判断成功

解包**成功**的标志：

1. 进程正常结束
2. 输出目录生成 `config.yaml`
3. `config.yaml` 中含 `crypterName`、`model`、`version`
4. 生成 `firmware.tar` 并已递归解包

解包**失败**的典型表现：

- `Exception: No decrypter found` → 容器密钥不在已知列表中
- `Wrong checksum` → 密钥错误或文件损坏
- `Wrong data version` → DAT 格式版本不匹配

**不要用"能读出一些可打印字符串"当作成功。** 必须满足上述 4 条。

### a1 II v4.00 的实测结果

作为参照（你的文件哈希可能不同，以官方下载为准）：

```yaml
dat:
  crypterName: CXD90057_k8
  isLens: false
fdat:
  model: 0x40030023
  version: '4.00'
  isAccessory: false
```

| 项 | 值 |
|---|---|
| 输入大小 | 1,194,332,648 B |
| 输入 SHA-256 | `F6F8DB5735FD15584DFC0118F84E537876C3AAEBA72A9971388C21334CE34614` |
| `firmware.fdat` | 1,189,666,304 B |
| `firmware.tar` | 1,188,408,320 B |
| `updater.img` | 1,257,472 B |

---

## 步骤 3：定位网络资产

解包后，网络资产包位于主根文件系统内：

```
<输出目录>/firmware.tar_unpacked/
  0700_part_image/dev/nflasha15_unpacked/
    data/ai_dict/default/default.nab
```

### 文件系统路径说明

`firmware.tar` 内按分区组织：

| 目录 | 内容 |
|---|---|
| `0700_part_image/dev/nflasha15` | 主根文件系统（含 AI 模型） |
| `0700_part_image/dev/nflasha8` | 协处理器固件 |
| `0700_part_image/dev/nflasha3` | 内核 + initrd |
| `0700_part_image/dev/nflasha7` | 小型 rootfs |

`nflasha15` 会被自动递归解包为 `nflasha15_unpacked/`。

**模型只在 `nflasha15` 里。** 其他分区没有神经网络权重。

### `data/ai_dict/` 的两层结构（易错点）

```
data/ai_dict/
├── default/
│   ├── default.nab          ← 出厂内置网络，真正目标
│   ├── AAAAAAI.rsc … AAAAACQ.rsc    ← 用户可下载模型的清单
│   └── default.nab 以外的 .nab 不存在于固件中
└── usr/                     ← 空
```

`AAAAAA*.rsc` 是 JSON 清单，描述 10 个**用户可下载**的 AI 模型，指向的 `AAAAAA*.nab` **不在固件包内**。

**不要把它们当成模型。** 它们是空壳元数据。

示例清单内容：

```json
{
  "na_file_name": "AAAAAAY.nab",
  "ai_model_id": "AAAAAAY",
  "ai_model_id_number": 3,
  "ai_model_category": 1,
  "slots": {"slot1": 18, "slot2": 19}
}
```

`slots` 引用的槽位号对应 `default.nab` 头部的槽位表。

---

## 步骤 4：切分网络

用本仓库的解析器：

```bash
python src/nab/nab_tool.py <路径>/default.nab
```

输出 17 个网络的名称、输入形状、输出头、字节大小。

### 切分方法

每个网络的边界由 `VPMN` 魔数确定：

```
net[n].start = 第 n 个 "VPMN" 出现位置
net[n].end   = 第 n+1 个 "VPMN" 出现位置
net[last].end = 文件大小
```

按此范围切出字节即得独立网络文件。

### 切分验证

三项必须全部通过：

1. **首尾相接**：`net[n].end == net[n+1].start`
2. **总长匹配**：所有网络大小之和 + 头部 + 槽位表 == 文件大小
3. **无重复**：每个切片的 SHA-256 互不相同

a1 II v4.00 实测：17 个网络合计 40,046,464 B，文件 40,047,760 B，差 1,296 B 为头部与槽位表，SHA-256 全部唯一。

---

## 步骤 5：后续工作

切出网络后，**还不能运行**。剩余工作见 [NAB-FORMAT.md 第 7 节](NAB-FORMAT.md)：

- 权重 payload 内部排布未解
- 卷积核内存顺序未解
- anchor 表与解码公式在主机侧代码
- 输入预处理未标定

**"切出文件"不等于"模型可用"。** 这两件事之间还有实质工作。

---

## 其他机型

本流程对同一代容器结构的机型通用，但需自行验证：

| 机型 | 状态 |
|---|---|
| a1 II (ILCE-1M2) | 本流程实测通过 |
| a7R VI (ILCE-7RM6) | 容器解密密钥社区记录为未知 |
| a7 V (ILCE-7M5) | 有现有方法失败的反馈 |

后两者**未经本项目验证**，不保证可用。

---

## 注意事项

1. **不要在公开仓库放固件或解包产物。** 用 `scripts/verify_repo.py` 自查。
2. **不要假设解包成功等于安全启动签名通过。** 这是两回事。
3. **不要假设解包成功等于机内行为一致。** 硬件输入映射、图像滤波、浮点舍入仍需机身对照。
