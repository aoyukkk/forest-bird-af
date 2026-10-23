# 林鸟对焦标注要求

请只读取 `images/` 中的原图。图片编号 bird_0001～bird_0200，编号已打乱。每张图独立输出一条 JSON，不需要识别物种。标注所有可辨认鸟个体，包括部分出画、较小或被遮挡的个体；无法确认是鸟的区域放进 `uncertain_regions`，不要当作确定目标。

任务是记录可见证据，供“有可用眼锁眼，否则锁头，再否则锁身体”的逻辑使用。不要为了满足这个逻辑而补出隐藏的眼睛或头。

## 坐标与框

- 使用原图像素坐标，左上为原点。矩形为 `[xmin, ymin, xmax, ymax]`，0 起算，右下边界不包含，范围不超出 `[0,width] × [0,height]`。保持原图方向和尺寸。
- `visible_bird_bbox_xyxy`：包住该鸟全部可见片段，包括头、身体、翅膀、尾羽和足；不要把前景枝叶算进鸟的可见区域。
- `visible_head_bbox_xyxy`：包住有证据的可见头部，包括喙，不为完全隐藏的头推测框。无法可靠确定边界时用 null，并说明原因。
- `amodal_bird_bbox_xyxy`：可选的完整鸟体推断框。第一版默认 null；若确实给出，必须同时标明它是推断，不与可见框混用。不要用它作为隐藏眼坐标的依据。
- `eyes`：只记录图上能够定位的眼；每只眼给中心点，能可靠画框时再给眼框。不可见眼不添加虚构坐标。眼的轮廓太小、模糊或被遮挡而无法判断时记录 unknown。

## 可见性和遮挡

- 对眼、头、鸟体分别记录 `visible / partially_occluded / occluded / out_of_frame / unknown`。背向镜头导致眼不可见和枝叶遮挡是不同原因，须分别记录。
- 遮挡物类型可多选：branch、leaf、trunk、grass、other_bird、other、none、unknown。普通栖枝和背景有树叶，不自动等于鸟被遮挡。
- 分别说明遮挡头/眼、身体、尾部还是足部。不要把只有尾部遮挡的样本写成头部遮挡。
- `af_reference_target` 取 eye / head / body / lost / unknown，依据原图可辨识证据给出参考。该值不是机身 AF 真值，也不代表缩到 384×256 后仍能辨认。
- 原图可见性与模型实际输入上的可用性分开；本批未指定 Nikon/Sony 的准确预处理，不自行拉伸到 384×256 后回写原图真值。
- `confidence` 为标注器自己的 0～1 置信度，不能用相机模型或其他模型的置信度代替。困难图保留 unknown 和人工审核标记，不强制每张图都有眼框。

## 输出结构

每张图使用以下结构。空模板的 `birds:null` 表示尚未标注；只有完成检查并确认没有鸟时才能写 `birds:[]`。将图片名和实际尺寸填入，`annotation_status` 完成后改为 annotated，仍需人工复核。

```json
{
  "image_id": "bird_0001",
  "file_name": "bird_0001.jpg",
  "width": 500,
  "height": 333,
  "annotation_status": "annotated",
  "birds": [
    {
      "instance_id": "b1",
      "visible_bird_bbox_xyxy": null,
      "visible_head_bbox_xyxy": null,
      "amodal_bird_bbox_xyxy": null,
      "body_visibility": "unknown",
      "head_visibility": "unknown",
      "eye_visibility": "unknown",
      "eyes": [],
      "occluder_types": ["unknown"],
      "occluded_parts": [],
      "invisibility_reason": "unknown",
      "af_reference_target": "unknown",
      "confidence": null,
      "needs_human_review": true,
      "notes": ""
    }
  ],
  "uncertain_regions": [],
  "annotator_model": "填写实际模型和版本",
  "notes": ""
}
```

示例仅展示字段，不提供任何一张图的答案。先标原图；原生模型输出类别尚需单独对齐，暂不直接转换成训练标签，也不开始训练。
