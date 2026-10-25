# 标注格式定义

> 历史格式，保留以解释已有模板。2026-10-24 起，新的人工标注采用[方案 v1](../../docs/protocol/DATASET-SPEC-v1.md)的 `instances + xyxy` 记录。本文的 xywh 框、单眼字段和输入尺度判据不得静默混入新记录；原图可见性与模型输入可用性现已分开。迁移须保留旧文件和明确版本。

每张图一条 JSON 记录，JSONL 一行一条。

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `image_id` | string | 本数据集内的统一编号 |
| `source` | object | 来源信息 |
| `split` | string | `train` / `val` / `test` |
| `group` | string | `A_occluded` / `B_control` / `C_unresolvable` |
| `instances` | array | 每只鸟一条，见下 |
| `notes` | string | 自由备注 |

### `source`

| 字段 | 类型 | 说明 |
|---|---|---|
| `dataset` | string | `cub200-2011` / `user-contribution` / `own-capture` |
| `orig_id` | string | 数据集内原始编号（若适用） |
| `camera` | string | 机型，如 `Z8`、`ILCE-1M2` |
| `lens` | string | 镜头 |
| `iso` | number | 可选 |
| `shutter` | string | 可选 |
| `aperture` | string | 可选 |
| `location` | string | 大致地点，不必精确 |
| `captured_at` | string | ISO 8601 |
| `sha256` | string | 原图哈希，用于校验 |

## `instances[]`

每只可见个体一条。

| 字段 | 类型 | 说明 |
|---|---|---|
| `instance_id` | int | 图内编号，从 1 开始 |
| `bird_box` | box | 整鸟可见框 |
| `head_box` | box \| null | 头部可见框，不可辨则 null |
| `eye` | eye \| null | 可定位眼，不可辨则 null |
| `visibility` | string | `full` / `partial` / `head_only` / `body_only` / `unresolvable` |
| `occlusion` | object | 遮挡原因 |
| `target_level` | string | 该实例应锁定的层级 |

### `box`

```json
{"x": 120, "y": 80, "w": 64, "h": 96}
```

坐标基于原图，整数像素。

### `eye`

```json
{"cx": 152, "cy": 101, "box": {"x": 148, "y": 97, "w": 8, "h": 8}, "side": "left", "visible": true}
```

- `box` 可选。给出眼框时单独核验。
- `visible` 为 `false` 时，`cx`/`cy` **必须为 null**。

### `target_level`

这是本项目的核心字段。决定模型应该锁定什么。

| 值 | 含义 | 判据 |
|---|---|---|
| `eye` | 应锁眼 | 至少一只眼在模型输入尺度下清晰可定位 |
| `head` | 应锁头 | 眼不可辨，但头部轮廓可辨 |
| `body` | 应锁身 | 头不可辨，但身体可辨 |
| `none` | 应丢失 | 三档均不可辨 |

**判据必须在模型实际输入尺度下检验**（Z8 = 384×256，a1 II 部位 = 320×320），不是在原图上看。

### `occlusion`

```json
{
  "cause": "branch" ,
  "covering_eye": false,
  "covering_head": true,
  "covering_body": false,
  "severity": "moderate"
}
```

| `cause` | 含义 |
|---|---|
| `none` | 无遮挡 |
| `branch` | 细枝穿过 |
| `leaf` | 叶片遮挡 |
| `dense_foliage` | 密叶整体遮蔽 |
| `trunk` | 树干阻挡 |
| `backlight` | 逆光致轮廓不可辨 |
| `blur` | 失焦或运动模糊 |
| `other` | 其他，需在 notes 说明 |

`severity`：`light` / `moderate` / `heavy`。

## 完整示例

```json
{
  "image_id": "bird_0042",
  "source": {
    "dataset": "cub200-2011",
    "orig_id": "Northern_Flicker_0012_5823.jpg",
    "camera": null,
    "sha256": "a3f1...c9d2"
  },
  "split": "val",
  "group": "A_occluded",
  "instances": [
    {
      "instance_id": 1,
      "bird_box": {"x": 88, "y": 60, "w": 190, "h": 240},
      "head_box": {"x": 130, "y": 72, "w": 52, "h": 48},
      "eye": null,
      "visibility": "head_only",
      "occlusion": {
        "cause": "branch",
        "covering_eye": true,
        "covering_head": false,
        "covering_body": false,
        "severity": "moderate"
      },
      "target_level": "head"
    }
  ],
  "notes": "细枝横穿眼部，头部轮廓完整"
}
```

## 禁止的做法

1. **不得补画被遮挡的眼睛。** 眼不可辨时 `eye` 必须是 `null`，不能填推断位置。
2. **不得把清晰图的眼坐标搬到遮挡图上**当作可见眼真值。
3. **不得只标模型检出不了的图。** 两边都漏的图要保留并记录为不确定。
4. **不得在多个划分间共享同一序列。**
