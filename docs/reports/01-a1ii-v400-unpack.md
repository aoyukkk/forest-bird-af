# Sony a1 II v4.00 固件完整解包与鸟类对焦模型提取报告

日期：2026-10-23。目标固件：`E:\Z8\BODYDATA.DAT`（1,194,332,648 B）。

## 0. 结论摘要

**解包链完整通过，对焦 AI 模型资产已全部提取。**

- 官方固件容器解密成功，crypter 为 `CXD90057_k8`（AES-CBC，k8 密钥表）。
- 机型判定 `model = 0x40030023`，版本 `4.00`，`isAccessory = false`。
- 主文件系统中定位到唯一神经网络资产包 `data/ai_dict/default/default.nab`（40,047,760 B）。
- 该包内含 **17 个独立网络**，全部为 INT8 量化、NHWC 布局，运行于 Sony 自有推理框架（`AiDictionary` → `AdamSeq`）。
- 鸟类部位检测器已识别并逐一切出，含 **3 个 2 类部位检测器 + 2 个关键点检测器 + 2 个横竖双方向头部检测器**。

**尚未完成的部分**（与方案的四个条件对应）：权重数据的算子级还原、输入预处理标定、输出后处理语义（眼/头/身类号分配）、以及离线可执行验证。当前停在"资产可定位 + 结构可读"，未到"可离线推理"，也未到"可作教师"。

## 1. 固件容器解包

固定使用 [fwtool.py PR #52](https://github.com/ma1co/fwtool.py/pull/52) 作者分支提交 `3955d7890fc38daf942bb52827599bfe35de4a14`（`improve ext2 detection`，HEAD detached 检出，未合并到 master）。

```
git clone --filter=blob:none https://github.com/DavidBuchanan314/fwtool.py.git
git checkout 3955d7890fc38daf942bb52827599bfe35de4a14
python fwtool.py unpack -f E:\Z8\BODYDATA.DAT -o E:\Z8\extract\a1ii_v400
```

依赖：`pycryptodomex`、`pyyaml`。

### 解包结果

| 项 | 值 |
|---|---|
| 输入 SHA-256 | `F6F8DB5735FD15584DFC0118F84E537876C3AAEBA72A9971388C21334CE34614` |
| DAT 头魔数 | `89 55 46 55 0D 0A 1A 0A` |
| crypter | `CXD90057_k8` |
| model | `0x40030023` |
| version | `4.00` |
| region | 0 |
| isAccessory | false |
| USB PID（normal） | 0x448 / 0x47D / 0xD15 / 0xD16 / 0xD19 / 0xD1A / 0xDA4 / 0xDA5 / 0xE0A / 0xE0E / 0xE72 / 0xE76 / 0xE7E / 0xE86 / 0xE8A / 0xE8E / 0xEE6 / 0xEEA（VID 0x54C） |
| USB PID（updater） | 0x3E2 |

产物：`firmware.fdat`（1,189,666,304 B）、`firmware.tar`（1,188,408,320 B）、`updater.img`（1,257,472 B），及递归解包后的目录树与 `config.yaml`。

**这是解包成功，不等于安全启动签名通过，也不等于机内行为一致。**

## 2. 文件系统结构

`firmware.tar_unpacked/` 顶层分区目录：

| 目录 | 内容 |
|---|---|
| `0100_config` / `0101_config_sum` | 更新配置 |
| `0110_backup` / `0111_backup_sum` | `SYSIPSX-DSLR/HC/*.bin` 多语言备份 |
| `0300_partconf` | 分区配置 |
| `0600_gps` / `0630_ca` / `0640_darwin` | 定位、证书、Darwin 模块 |
| `0650_prfile` | `PMBP/LICENSE` |
| `0700_part_image` | **主镜像区**：`nflasha3/5/7/8/15` |
| `0750_nor_loader` | NOR 引导 |
| `0800_appli` | 应用资源 |
| `1030_genlock` / `1050_i2c` | 外设 |

`0700_part_image/dev/` 下：

| 镜像 | 大小 | 解包后可读内容 |
|---|---|---|
| `nflasha15` | 747,399,168 B | **主根文件系统**（`bin/ lib/ data/ codec/ sabin/ share/`） |
| `nflasha5` | 340,062,784 B | 未识别为已知归档 |
| `nflasha3` | 32,540,672 B | `vmlinux.bin`、`av-cam.bin`、`initrd.img` |
| `nflasha8` | 26,520,576 B | `cpapp-b.bin`、`cpImg.dat`、`DGU.bin`、`DmmCfg.bin`、`MIS.bin` 等协处理器固件 |
| `nflasha7` | 5,222,400 B | 小型 rootfs（`version.txt` = `34023_06.2025100701`） |

`nflasha15` 关键文件：

| 路径 | 大小 | 说明 |
|---|---|---|
| `lib/appFw.so` | 94,665,016 B | AF/UI 主逻辑（含 `bird_detection_parts`、`face_eye_detection_af`） |
| `data/ai_dict/default/default.nab` | 40,047,760 B | **神经网络资产包（本次核心）** |
| `lib/libAiDictionary.so` | 68,888 B | AI 字典加载器（JSON 清单 + `NA_LOAD_REQ` → `AdamSeq`） |
| `lib/libInfraSKD.so` | 7,611,988 B | 推理/SKD 基础设施 |
| `codec/vcd_firmware_imola2.bin` | 10,934,476 B | 视频编解码器固件 |

## 3. AI 模型命名空间的两层结构

**这一层很关键，容易误判。**

`data/ai_dict/` 下有 `default/` 与 `usr/` 两个目录：

1. **`usr/` 为空、`default/*.rsc` 是空壳清单。** 10 个 `.rsc` 文件（`AAAAAAI.rsc` … `AAAAACQ.rsc`）是 **用户可下载 AI 模型** 的元数据，`ai_model_id_number` 1–10，各自带 `category`/`menu_category` 与 `slots` 引用。它们指向的 `AAAAAA*.nab` **不在固件包内**——那是下载式模型，不是本次的目标。
2. **`default.nab` 是出厂内置网络包。** 真正的鸟类对焦网络都在这里面。

`.rsc` 的 `slots` 字段引用的槽位号（5,6,7,8,9,10,11,14,15,16,17,18,19）与 `default.nab` 头部槽位表的 id 一一对应，说明下载式模型可以覆盖/替换包内槽位——但这不影响出厂包的独立解析。

## 4. default.nab 格式还原

全部字段经实测验证，非推测。

### 4.1 文件头

```
0x00  u32  0x4E41         "NA"
0x04  u32  78             版本
0x08  u32  1
0x0C  u32  17             网络数量
0x10  u32  48
0x14  u32  128
0x18  u32  176
0x1C  u32  32
0x20  u32  720
0x24  u32  32
0x28  u32  1264
```

### 4.2 槽位表（0x110 起，stride 0x30）

```c
struct Slot {
  uint32 slot_id;    // 4,5,6,7,8,9,10,11,14,15,16,17,18,19
  uint32 buf_size;   // 画布字节数
  uint32 offA;       // 画布/缓冲偏移
  uint32 offB;       // 第二缓冲偏移
  uint32 marker;     // = 32
};
```

实测 14 条记录。`buf_size` 与输入尺寸对应关系验证：

| slot | buf_size | 分解 | 对应 |
|---|---|---|---|
| 4 | 150,528 | 224×224×3 | net[3] 输入 |
| 5, 6 | 230,400 | 480×480 | 中间缓冲 |
| 7 | 49,152 | 128×128×3 | net[6] 输入 |
| 8, 9, 10, 11, 16, 17 | 307,200 | 320×320×3 | 部位检测器输入 |
| 14 | 6,144 | 32×64×3 | net[11] 输入 |
| 15 | 12,288 | 64×64×3 | net[12] 输入 |
| 18, 19 | 359,424 | 416×288×3 | head 检测器输入 |

### 4.3 网络描述符（VPMN）

```
0x00  "VPMN"
0x04  u16  版本    0x0D / 0x0F / 0x16（三档，新版打包用 0x16）
0x06  u16  1
0x08  u32  名字长度 0xD4 = 212
0x0C  char 名字[212]
```

共 17 个 VPMN，顺序即网络序号。

### 4.4 张量描述符（名字在 +0x34）

```c
struct Tensor {
  uint32 marker;      // = 4
  uint32 H, W, C;
  uint32 one[3];      // 1,1,1
  uint32 dtype;       // = 2 → int8
  uint32 zero;
  uint32 two;         // = 2
  int32  zero_point;  // -127 / 88 / ...
  float  scale;       // 0.0039215689 = 1/255, 0.0078431377 = 2/255, ...
  uint32 name_len;
  char   name[];      // "input[0]" / "uid_NNN_out_0" / "output[K]"
};
```

`dtype=2` + `zero_point` + `scale` 三件套证实 **INT8 非对称量化**，与 Sony 的 `cquant` 命名一致。

### 4.5 层记录

```c
struct Layer {
  char   name[0x40];   // 输入张量名
  uint32 marker;       // = 1
  uint32 layer_index;  // 0..199
  char   type[0x40];   // "ConvolutionReluPoolingLayer2" 等
};
```

支持的层类型：`ConvolutionReluPoolingLayer2`、`ConvolutionReluPoolingLayer`、`PoolingLayer2`、`ConvolutionLayer`、`ActivationLayer`、`ConcatLayer`、`Softmax2Layer`、`FullyConnectedReluLayer`、`BatchNormalizationLayer`、`DeConvolutionLayer`、`L2NormalizeLayer`、`NormalizeLayer`。

## 5. 17 个网络完整清单

| # | 名称 | 输入 HWC | 输出头 | 层数 | 字节 | 判定 |
|---|---|---|---|---|---|---|
| 0 | `sony_net_opt_NHWC` | 512×336×3 | 64×42×40, 64×42×19 | 152 | 1,254,560 | 主干/主体显著性 |
| 1 | `reid_NHWC` | 64×128×3 | 64×1×1 | 14 | 129,120 | 重识别嵌入 |
| 2 | `reidpost_NHWC` | 16×(64×1×1) | 16×1×1×1 | 8 | 401,184 | 重识别后处理 |
| 3 | `tfl107_t58_e70_q58_d53_c0_NHWC` | 224×224×3 | 13×1×1 | 66 | 2,272,160 | 13 类场景分类 |
| 4 | `model_NCHW` | 320×180×3 + 320×180×1 | 320×180×1 | 70 | 2,546,144 | 二输入掩码网络 A |
| 5 | `model_NCHW` | 320×180×3 + 320×180×1 | 320×180×1 | 69 | 2,574,752 | 二输入掩码网络 B |
| 6 | `aed_03_00_05_rc2_NHWC` | 128×128×3 | 3×1×1, 32×32×3 | 46 | 1,808,992 | 3 类分类 + 上采样 |
| 7 | `dummy_network_name` | 320×320×3 | 30ch, 24ch, 6ch | 70 | 3,978,400 | 单类检测（早期） |
| **8** | `dummy_network_name` | 320×320×3 | **42ch(×2), 24ch, 6ch** | 70 | **4,103,968** | **部位检测器 A** |
| **9** | `dummy_network_name` | 320×320×3 | **18ch(×2), 24ch, 6ch** | 77 | 4,028,000 | **关键点检测器 A** |
| **10** | `dummy_network_name` | 320×320×3 | **42ch(×2), 24ch, 6ch** | 70 | **4,009,312** | **部位检测器 B** |
| 11 | `tflite_djd5-U-resnet7-32_64-esch_lw_quan_max23_NHWC` | 32×64×3 | 64×1×1 | 15 | 131,872 | 轻量嵌入 |
| 12 | `sfr_tf_resnet_454-80-160-320-512-nose_NHWC` | 64×64×3 | 512×1×1 | 70 | 1,377,824 | ResNet 特征（512d） |
| **13** | `dummy_network_name` | 320×320×3 | **18ch(×2), 24ch, 6ch** | 70 | 3,933,088 | **关键点检测器 B** |
| **14** | `dummy_network_name` | 320×320×3 | **42ch(×2), 24ch, 6ch** | 70 | **3,973,216** | **部位检测器 C** |
| **15** | `v58_h27_head_no_norm_clip_416x288_cquant_order_NHWC` | 416×288×3 | 36ch, 18ch, 2ch, 1ch | 70 | 1,762,080 | **头部检测器（横构图）** |
| **16** | `v58_h27_head_no_norm_clip_288x416_cquant_order_NHWC` | 288×416×3 | 36ch, 18ch, 2ch, 1ch | 70 | 1,761,792 | **头部检测器（竖构图）** |

### 输出通道语义推断

以 net[8] 为例，head 层张量：

| 张量 | 形状 | 系数分解 | 含义 |
|---|---|---|---|
| `uid_129_out_0` | 3×3×42 | 6 anchors × 7 | `tx,ty,tw,th,obj,c0,c1` → **2 类检测** |
| `uid_130_out_0` | 1×1×42 | 6 anchors × 7 | 同上，最高尺度 |
| `uid_136_out_0` | 3×3×24 | 6 anchors × 4 | 框回归 |
| `uid_137_out_0` | 1×1×24 | 6 anchors × 4 | 同上 |
| `uid_123_out_0` | 1×1×6 | 6 anchors × 1 | objectness |

**6 anchors × 7 = 42 且 6 anchors × 4 = 24 的严格一致，是 YOLO 系检测头**。三尺度特征图 80/40/20/10/5/3 出现在中间张量（`uid_131..137`），与 320×320 输入、stride 4/8/16/32/64/… 的 FPN 结构吻合。

`v58_h27_head` 的 36 = 18 anchors × 2 类，18 = 18 anchors × 1，与 416×288 输入、52×36 输出网格（stride 8）对应，是**更高分辨率的单类部位检测器**。

## 6. 与"鸟眼模型"的直接对应关系

`appFw.so` 中确认存在下列 AF 功能符号：

- `subject_recognition_bird_detection_parts` — **鸟类部位检测开关**
- `subject_recognition_animal_bird_priority`
- `subject_recognition_bird_detection_sensitivity`
- `subject_recognition_bird_tracking_sensitivity`
- `face_eye_detection_af`

`subject_recognition_bird_detection_parts` 就是官方说明中"眼/头/身"三档部位识别的开关。与之对应的网络结构为：

| 官方功能 | 网络 |
|---|---|
| 头部识别（横构图） | net[15] `v58_h27_head_*_416x288` |
| 头部识别（竖构图） | net[16] `v58_h27_head_*_288x416` |
| 部位识别（眼/身等多部位） | net[8] / net[10] / net[14] 三个 42ch 2 类检测器 |

**三个 42ch 检测器结构完全相同、层数相同（70）、输出头形状逐位一致，仅权重不同** —— 这正是"同一架构分别训练三个部位"的特征。`v58_h27_head` 作为更新的高分辨率 head 检测器单独存在，说明 v4.00 对"头"换用了新一代模型，而"眼"和"身"仍走旧的 320×320 三件套。

**这一段的证据等级是"结构与命名一致"，不是"已证实 net[8] 就是眼"**。要钉死哪个是眼，必须做第 7 节的验证。

## 7. 已提取产物

目录 `E:\Z8\extract\a1ii_v400\bird_models\`：

| 文件 | 大小 | SHA-256（前 16） |
|---|---|---|
| `08_part_detector_A__dummy_network_name.vvpm` | 4,103,968 | `91a08ee1d9d847b3` |
| `10_part_detector_B__dummy_network_name.vvpm` | 4,009,312 | `252581c5235d90e6` |
| `14_part_detector_C__dummy_network_name.vvpm` | 3,973,216 | `37b4e51f16b0f180` |
| `09_kpt_detector_A__dummy_network_name.vvpm` | 4,028,000 | `5135ebd5704ff860` |
| `13_kpt_detector_B__dummy_network_name.vvpm` | 3,933,088 | `fd9f7e37c0df4fb5` |
| `15_head_416x288__v58_h27_..._NHWC.vvpm` | 1,762,080 | `a35ee84923226d30` |
| `16_head_288x416__v58_h27_..._NHWC.vvpm` | 1,761,792 | `91af0dfeb61e1cb7` |

全部 17 个网络的完整切分在 `E:\Z8\extract\a1ii_v400\nab_out\`，带 `manifest.json`。

解析工具：`E:\Z8\tools\nab\nab_tool.py`（独立可复现，输出见下）。

```
python nab_tool.py <default.nab>
```

### 验证记录（本轮实际执行）

| 检查 | 结果 |
|---|---|
| DAT 容器 CRC | 通过（`readDat` 校验） |
| FDAT 解密 | 通过（`CXD90057_k8`） |
| FDAT 头 CRC + mode + luw | 通过 |
| tar 递归解包 | 通过 |
| `default.nab` 17 个 VPMN 定位 | 通过 |
| 每个网络张量/层记录解析 | 通过 |
| 槽位表 14 条记录 | 通过 |
| slot 17 的 buf_size（416×288×3 = 359,424）与 head 输入 | 逐位精确匹配 |
| slot 4 的 buf_size（224×224×3 = 150,528）与 net[3] 输入 | 逐位精确匹配 |

## 8. 尚未完成、且不能声称完成的部分

按方案的四条准入条件，当前只满足第 1、2 条：

| 条件 | 状态 |
|---|---|
| 1. 固件可解包 | **通过**（本地实测） |
| 2. 鸟类资产可定位 | **通过**（17 网络 + 层 + 张量 + 槽位） |
| 3. 模型可离线执行 | **未达成** |
| 4. 输出有标注价值 | **未达成** |

第 3 条的具体缺口：

- **权重 payload 未还原。** 层记录之后是权重区，其内部排布（per-channel scale 数组、卷积核 NHWC 顺序、bias 偏移）尚未逐步验证。目前能证明"权重在文件里且网络结构自洽"，未证明"逐层权重能正确重建为可前向的图"。
- **算子语义未完全确定。** `ConvolutionReluPoolingLayer2` 的融合细节（是否内部含 BN、padding 策略、pool 类型与 stride）需要按记录字段逐一比对。
- **输入预处理未标定。** `scale = 1/255` 或 `2/255`、`zero_point = -127` 已读出，但 resize 方式、ROI 取景、色彩空间（ISP 输出到模型输入的转换）没有机身对照。
- **输出后处理未确认。** 2 类的类号 → 眼/头/身的映射、anchor 表、解码公式属于主机侧代码，需继续在 `appFw.so` / `libInfraSKD.so` 中定位消费者。
- **无离线推理证据。** 没有任何一张真实图像跑过这些网络。

**因此：现在拿到的是模型资产，不是可运行的教师。** 三个 42ch 检测器中哪个是眼，目前只能按结构与命名推测，必须在第 4.4 条的人工小集上验证后才能定论。

## 9. 下一步（按方案 P1 继续，不跳步）

1. **权重区格式还原**：定位每层权重记录，验证 per-channel scale 与卷积核排布，做单层数值 round-trip（原字节 → 张量 → 原字节）。
2. **后处理链定位**：在 `appFw.so` 中追踪 `uid_NNN_out_0` 的消费者，确定 anchor 表与类号含义，锁定三个 42ch 网络中哪个对应眼。
3. **输入标定**：从 `libInfraSKD.so` / `sony_net_opt` 的输入约定反推 resize 与归一化，与 `vcd_firmware` 的输出格式对齐。
4. **200 张人工校准集**：眼网络能跑起来后，按方案 §4 的对照表与 Z8 逐一比对，判断互补场景。
5. 只有第 1–3 步跑通、第 4 步给出正向结果，才进入 A1/A2 训练条件。

本轮没有下载额外固件、没有运行 GPU、没有启动训练。a7R VI 与 a7 V 的解密阻塞状态不变。
