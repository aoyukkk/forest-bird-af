# 林鸟标注初始集：200 张专业数据集原图

2026-10-23。用途：比较已恢复的 Nikon/Sony 鸟类模型，校准部位标注与遮挡回退逻辑。仅完成图片选择和打包，没有运行模型、生成模型标签或训练。

## 直接使用

- `annotation_package_200.zip`：可交给标注模型的包，含 images/ 下 200 张 JPG、标注要求和 200 行空模板。没有附带 CUB 答案或场景分组。
- `images/`：bird_0001.jpg～bird_0200.jpg，统一编号、确定性打乱顺序；像素和文件字节与官方原图一致，无裁剪、超分、生成遮挡或压缩重编码。
- `contact_sheets/`：每页 20 张，共 10 页，供浏览和核对编号。缩略图不可代替原图标注。
- `metadata/manifest.csv` / `manifest.json`：编号到数据集原始路径、ID、划分、尺寸、SHA-256 和初筛分组的映射。
- `metadata/source_annotations.json`：原数据集的鸟体框、15 个部位点及可见性，仅供独立复核。部位点不是眼框/头框，且 visible=0 不等于树叶遮挡；不直接转换为训练真值。
- `metadata/qa.json`：图片解码、数量、文件一致性及重复筛查结果。

## 本批来源和构成

来源全部为 Caltech 官方 CUB-200-2011 原始包中的 **官方 train 划分**。从 3,507 张林栖/灌丛相关类别的训练照片中，按部位缺失、小目标和每类数量上限建立 840 张候选；查看了前 630 张候选的联系表，并复核选中图和替换图，最终选 200 张、92 个物种类别。筛选仅使用原始标注和目视检查，没有让检测模型决定哪些图片进入本批。

| 初筛用途 | 数量 | 含义 |
|---|---:|---|
| 枝叶遮挡候选 | 100 | 覆盖细枝、叶片、密枝、树干、树洞等，包含轻微/局部遮挡；不是 100 张重度遮挡，也不是最终遮挡真值 |
| 自然场景对照 | 60 | 自然植被、复杂背景、较小鸟、背光及树干伪装等；是否存在局部遮挡仍由标注确认 |
| 清晰/姿态对照 | 40 | 侧面、正面、背面、低头、展翅等；眼不可见可能由朝向造成 |

分组是选图提示，不是人工专家真值。**遮挡原因、实际部位可见性和眼→头→身的参考目标，均需新标注并复核。** 本批全为有鸟图，没有额外加入无鸟负样本，不足以评估纯背景误报。

## 质量与用途边界

保留官方图像原尺寸，最终选中图长边范围以 qa.json 为准，多数约 500 像素。适合首轮静态模型输入和标注校准，不能代替 Z8 原始高分辨率照片、连续遮挡恢复视频、失焦/运动及真实镜头驱动测试。CUB 主要为北美鸟种，亚洲林鸟、拍摄器材和场景分布仍需后续实拍补充。

本批是校准/候选标注集，不能同时用来挑选教师、调阈值、微调后再宣称是独立最终测试集。官方 train/test 划分已保存，未选用官方 test；但官方仍提醒 CUB 与 ImageNet/Flickr 的预训练数据可能重叠，因此不声称这些图对所有教师都是未见样本。

重复筛查包括文件 SHA-256 和 64 位 dHash 两两比较（阈值 ≤7）；未命中不等于证明拍摄序列、个体或预训练来源绝无重复。未获取拍摄序列的完整身份信息。

## 为什么先用这个数据集

| 数据集 | 已核实的信息 | 本轮采用情况 |
|---|---|---|
| CUB-200-2011 | 11,788 图，200 类，每图鸟体框与 15 部位点；官方可下载并有校验值 | 已下载官方原包并选出本批 200 张 |
| NABirds | 48,562 图、555 类；论文说明每图鸟体框与 11 部位可见性/位置 | 作为后续扩展来源；本批未使用来源和尺寸不明确的第三方缩小包 |
| iCub（WACV 2024） | 16,876 张 iNaturalist 来源图片，与 CUB 同类，包含更多小鸟/困难实例；作者定位为 evaluation-only | 适合后续独立域外验证；本批未下载、未混入微调候选 |
| NUBird2022 | 有遮挡标签，但为约 8 分钟室内/封闭环境五只斑胸草雀的全景序列 | 与本轮林鸟场景差距大，未选 |

已停止 Commons 关键词采集。先前下载的关键词候选只保留在 work/ 中作为工作记录，**没有进入本批 200 张图或标注包**。

## 官方来源与使用说明

- CUB 项目与使用条件：https://www.vision.caltech.edu/datasets/cub_200_2011/
- CUB 官方发布记录：https://data.caltech.edu/records/65de6-vp158
- 原包 1,150,585,339 字节，官方 MD5 `97eceeb196236b17998738112f37df78`，已核对一致。发布元数据和验证记录在 sources/CUB-200-2011/。
- CUB 图片按发布方说明用于非商业研究及教育；原摄影者版权和图片原水印保留。本地标注包没有改写为 CC0/MIT，也没有上传公共平台。
- NABirds 原论文：https://openaccess.thecvf.com/content_cvpr_2015/papers/Horn_Building_a_Bird_2015_CVPR_paper.pdf
- NABirds 项目：https://dl.allaboutbirds.org/nabirds
- NABirds 使用条件：https://dl.allaboutbirds.org/merlin-computer-vision-terms-of-use
- iCub 作者项目：https://catalys1.github.io/elusive-images-fgvc/
- iCub 论文：https://openaccess.thecvf.com/content/WACV2024/papers/Anderson_Elusive_Images_Beyond_Coarse_Analysis_for_Fine-Grained_Recognition_WACV_2024_paper.pdf
- NUBird2022：https://www.cs.is.i.nagoya-u.ac.jp/ja/opensource/nubird/

CUB 引用：Wah, C.; Branson, S.; Welinder, P.; Perona, P.; Belongie, S. *The Caltech-UCSD Birds-200-2011 Dataset*. California Institute of Technology, CNS-TR-2011-001, 2011.
