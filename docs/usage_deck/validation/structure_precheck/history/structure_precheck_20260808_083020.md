# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`4`
- 警告数：`0`
- 未检查数：`1`

## 摘要

- `error` / `text_occluded_by_shape`: 4
- `not_checked` / `flattened_graphic_requires_render_review`: 1

## 问题清单

### `error`

#### `text_occluded_by_shape`

文本估计边界与更高层对象发生显著重叠，存在相邻对象压字风险。

建议：移动遮挡对象、增加留白，或重排文本框与卡片边界。

出现位置：
- slide 8 | shape 8 | occluder=9 | overlap_ratio=1
- slide 8 | shape 12 | occluder=13 | overlap_ratio=1
- slide 8 | shape 16 | occluder=17 | overlap_ratio=1
- slide 8 | shape 20 | occluder=21 | overlap_ratio=1

### `not_checked`

#### `flattened_graphic_requires_render_review`

该图片对象可能承载内部文字或图表标签，但结构预检无法看到图片内部对象边界，需要交给 render review。

建议：若该图片内部含文字、刻度或标签，请在预览导出后执行 render review，而不是把 `not_checked` 当成通过。

出现位置：
- slide 9 | shape 8
