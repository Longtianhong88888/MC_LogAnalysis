# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`0`
- 警告数：`0`
- 未检查数：`1`

## 摘要

- `not_checked` / `flattened_graphic_requires_render_review`: 1

## 问题清单

### `not_checked`

#### `flattened_graphic_requires_render_review`

该图片对象可能承载内部文字或图表标签，但结构预检无法看到图片内部对象边界，需要交给 render review。

建议：若该图片内部含文字、刻度或标签，请在预览导出后执行 render review，而不是把 `not_checked` 当成通过。

出现位置：
- slide 9 | shape 8
