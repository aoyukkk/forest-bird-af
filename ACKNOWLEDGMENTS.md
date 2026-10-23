# 致谢

这个项目站在许多人的工作上。以下按作用分类列出。

---

## 一、固件研究

### fwtool.py 与 PR #52

Sony 固件容器的解密与解包能力来自这个项目。没有它，本项目无法开始。

- 仓库：<https://github.com/ma1co/fwtool.py>
- 作者：**ma1co**
- 许可：MIT
- 本项目使用：PR #52 作者分支提交 `3955d7890fc38daf942bb52827599bfe35de4a14`
- PR 链接：<https://github.com/ma1co/fwtool.py/pull/52>

**特别感谢 PR #52 的作者 DavidBuchanan314**，这个 PR 新增了新版机型的容器解密与解包支持，并改进了 ext2 检测。a1 II v4.00 的解包正是依赖这部分工作。

同时感谢 PR #52 讨论区中报告各机型测试结果的社区成员，他们的记录帮助本项目判断哪些机型可行、哪些仍受阻。

该 PR 当前仍为 open 状态、未合并到主分支。使用者务必固定上述提交，不要假设默认分支已包含。

### 早期 Sony 固件研究

fwtool 本身继承了更早的研究：

- **oz_paulb** — 原始 fwtool 与 nex-hack 工作
- **nex-hack** 社区 — Sony 相机固件结构的早期探索

### VeriSilicon TIM-VX

用于交叉验证本项目的格式判断，尤其在量化参数上的纠错。

- 仓库：<https://github.com/VeriSilicon/TIM-VX>
- 许可：MIT
- 本项目使用：提交 `702715d714277376d7ff466b7b72833ff57564c1`

**这份源码直接纠正了本项目的一处错误判断。** 早期报告把张量描述符中的某个字段读作 `zero_point = -127`，用官方 NBG 解析器验证后发现该字段是 `fixed_pos`，在非对称量化下真正的零点是 128。这个纠错过程完整记录在 `docs/reports/03-pilot-run-002.md`。

---

## 二、数据集

### CUB-200-2011

首轮 200 张校准图全部来自这个数据集。

- 项目页：<https://www.vision.caltech.edu/datasets/cub_200_2011/>
- 发布记录：<https://data.caltech.edu/records/65de6-vp158>
- 引用：

> Wah, C.; Branson, S.; Welinder, P.; Perona, P.; Belongie, S.
> *The Caltech-UCSD Birds-200-2011 Dataset*.
> California Institute of Technology, CNS-TR-2011-001, 2011.

**感谢 200 个鸟种照片的原始摄影者。** CUB 图片版权属于拍摄者本人，数据集发布方说明其用于非商业研究与教育用途。本项目不重新分发图片，只提供清单与校验值。

### NABirds

后续扩大训练集时的候选来源。

- 项目：<https://dl.allaboutbirds.org/nabirds>
- 论文：<https://openaccess.thecvf.com/content_cvpr_2015/papers/Horn_Building_a_Bird_2015_CVPR_paper.pdf>
- 引用：

> Van Horn, G.; Branson, S.; Farrell, R.; Haber, S.; Barry, J.; Ipeirotis, P.; Perona, P.; Belongie, S.
> *Building a Bird Recognition App and Large Scale Dataset With Citizen Scientists: The Fine Print in Fine-Grained Dataset Construction*. CVPR 2015.

**感谢参与标注的数千名志愿者。**

### iCub / Elusive Images

后续独立域外验证的候选来源，包含更多小鸟与困难实例。

- 项目：<https://catalys1.github.io/elusive-images-fgvc/>
- 论文：<https://openaccess.thecvf.com/content/WACV2024/papers/Anderson_Elusive_Images_Beyond_Coarse_Analysis_for_Fine-Grained_Recognition_WACV_2024_paper.pdf>
- 引用：

> Anderson, P.; et al.
> *Elusive Images: Beyond Coarse Analysis for Fine-Grained Recognition*. WACV 2024.

### NUBird2022

有遮挡标签，但因场景为室内封闭环境的斑胸草雀全景序列，与本项目林鸟场景差距较大，未采用。记录在此以说明筛选过程。

- 项目：<https://www.cs.is.i.nagoya-u.ac.jp/ja/opensource/nubird/>

---

## 三、软件依赖

| 项目 | 作者 / 维护方 | 许可 | 用途 |
|---|---|---|---|
| [fwtool.py](https://github.com/ma1co/fwtool.py) | ma1co | MIT | 固件容器解密解包 |
| [TIM-VX](https://github.com/VeriSilicon/TIM-VX) | VeriSilicon | MIT | NBG 格式交叉验证 |
| [PyCryptodome](https://www.pycryptodome.org/) | Legrandin | BSD-2-Clause | AES 解密 |
| [PyYAML](https://pyyaml.org/) | Kirill Simonov 及维护者 | MIT | 配置解析 |

---

## 四、工具链与基础设施

| 项目 | 用途 |
|---|---|
| [Python](https://www.python.org/) | 全部解析与实验脚本 |
| [Git](https://git-scm.com/) | 版本控制 |
| [LLVM](https://llvm.org/) | 反汇编与二进制分析 |
| [Ghidra](https://ghidra-sre.org/) | 主机侧代码分析（NSA 开源） |
| [QEMU](https://www.qemu.org/) | 模拟环境研究 |

---

## 五、知识来源

本项目的方案设计参考了大量公开研究，无法尽列。对影响最直接的部分致谢：

### Ultralytics / YOLO 系列

检测头结构（anchors × (4 + 1 + classes)）的判读依据，以及算力预算的公开对照数据。

- 仓库：<https://github.com/ultralytics/ultralytics>
- YOLOv5：<https://github.com/ultralytics/yolov5>（AGPL-3.0）
- 模型文档：[YOLOv8](https://docs.ultralytics.com/models/yolov8/) / [YOLO11](https://docs.ultralytics.com/models/yolo11/) / [YOLO26](https://docs.ultralytics.com/models/yolo26)
- 引用：

> Jocher, G.; Chaurasia, A.; Qiu, J. *Ultralytics YOLO*.

**说明**：本项目只引用了其公开文档中的结构说明与算力数字用于对照，未复制代码。若后续使用其权重或代码，需按其 AGPL-3.0 条款处理。

### 知识蒸馏

方案中 A0/A1/A2 对照组的设计思路。

> Hinton, G.; Vinyals, O.; Dean, J.
> *Distilling the Knowledge in a Neural Network*. NIPS 2014 Workshop.

### CEVA 架构公开资料

用于判断 Z8 图像处理链路的算力边界，以及确认 CEVA-XM6 的专有 ISA 性质。

- [CEVA NeuPro 架构说明](https://www.ceva-ip.com/press/ceva-introduces-new-ai-inference-processor-architecture-for-edge-devices-with-co-processing-support-for-custom-neural-network-engines/)
- [CEVA ONNX 支持说明](https://www.ceva-ip.com/press/ceva-adds-onnx-support-to-cdnn-neural-network-compiler/)

**注意**：这些是产品宣传材料，只证明其产品具备相关能力，不证明本项目已获得对应编译器或本地可复现。

### 传感器与曝光研究

Z8 DGO 可行性评估参考的公开技术资料：

- [Canon DGO 白皮书](https://downloads.canon.com/cinemaeos/DGO-Sensor-White-Paper.pdf)
- [Canon DGO 技术说明](https://www.canon-europe.com/pro/stories/dgo-sensor-explained/)
- [Magic Lantern Dual ISO](https://github.com/reticulatedpines/magiclantern_simplified/blob/dev/modules/dual_iso/dual_iso.c)
- [Photons to Photos 测量数据](https://photonstophotos.net/Charts/RN_e.htm)

### 厂商官方文档

用于确认功能存在性，不作为实现依据：

- [Nikon Z8 官方说明书](https://onlinemanual.nikonimglib.com/z8/en/)
- [Sony a1 II 对焦说明](https://support.d-imaging.sony.co.jp/support/ilc/autofocus/ilce1m2/en/13.php)

### 细粒度视觉识别

部位标注规范参考了该领域的公开工作，包括 CUB 与 NABirds 论文中的部位点定义方式（但本项目明确区分“部位点”与“眼框/头框”，不直接等同）。


---

## 六、器材与数据贡献者

- **Nikon Z8 与 Sony a1 II 的固件研究**建立在大量前人的逆向工作之上，本项目只是接续。
- **参与照片投稿的拍摄者** — 姓名将在获得许可后列入 `CONTRIBUTORS.md`。不愿署名的保持匿名。

---

## 七、如果遗漏了你

### 2026-10-24 补充：E7 原网络数值复现

[WonderLantern/e7-bird-network](https://github.com/WonderLantern/e7-bird-network) 提供同一 resource744 网络主体的细化算术实现和公开实机回归样例。本项目固定提交 `8ced43b19edb845baef39a80c45d40be0b49efba`，验证与本地 Z8 主体相同，并在独立 GPU 适配通过回归后用于社区图片预标注。后处理继续使用本地 Z8 原厂执行路径。来源、数值范围及未确认语义见[对比报告](docs/reports/05-e7-comparison-and-cuda.md)。上游原资产与源码副本不随本仓库重新分发，也不把上游工作计为本项目原创。

这个列表一定不完整。如果你认为自己的工作被使用但未列出，请提 issue，我们会补上。

**致谢不是形式。** 本项目选择公开方法与格式，很大程度是因为上游的工作本身是公开的——如果把这些成果据为己有，这个项目就没有存在的理由。
