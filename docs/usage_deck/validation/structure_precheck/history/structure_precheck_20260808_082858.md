# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`1`
- 警告数：`17`
- 未检查数：`1`

## 摘要

- `error` / `text_occluded_by_shape`: 1
- `not_checked` / `flattened_graphic_requires_render_review`: 1
- `warning` / `body_text_below_theme_token`: 1
- `warning` / `font_size_fragmentation`: 1
- `warning` / `font_size_outside_theme_scale`: 15

## 问题清单

### `error`

#### `text_occluded_by_shape`

文本估计边界与更高层对象发生显著重叠，存在相邻对象压字风险。

建议：移动遮挡对象、增加留白，或重排文本框与卡片边界。

出现位置：
- slide 8 | shape 4 | occluder=20 | overlap_ratio=1

### `warning`

#### `body_text_below_theme_token`

较长文本低于 active body_font_pt，疑似通过压小字号解决版面密度。

建议：先减少文案、放宽容器或拆页；确需更小字号时，记录该语义角色和例外原因。

出现位置：
- slide 11 | shape 6 | font_sizes_pt=10.5

#### `font_size_fragmentation`

整份 deck 的显式字号档位过多，字号系统可能已经碎片化。

建议：把相同语义的文字收敛到 hero / section / page title / subtitle / body / label / caption / table token。

出现位置：
- font_sizes_pt=9,10,10.5,12,13,14,16,18,20,24,36,44,56

#### `font_size_outside_theme_scale`

显式字号不属于 active theme_tokens 的语义字号表，可能是局部手填档位。

建议：把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

出现位置：
- slide 1 | shape 2 | font_sizes_pt=44
- slide 1 | shape 3 | font_sizes_pt=20
- slide 1 | shape 6 | font_sizes_pt=10
- slide 2 | shape 6 | font_sizes_pt=56
- slide 2 | shape 10 | font_sizes_pt=56
- slide 2 | shape 14 | font_sizes_pt=56
- slide 2 | shape 17 | font_sizes_pt=13
- slide 5 | shape 5 | font_sizes_pt=13
- slide 5 | shape 9 | font_sizes_pt=13
- slide 5 | shape 13 | font_sizes_pt=13
- slide 5 | shape 17 | font_sizes_pt=13
- slide 5 | shape 21 | font_sizes_pt=13
- 其余 3 个位置见 JSON 报告

### `not_checked`

#### `flattened_graphic_requires_render_review`

该图片对象可能承载内部文字或图表标签，但结构预检无法看到图片内部对象边界，需要交给 render review。

建议：若该图片内部含文字、刻度或标签，请在预览导出后执行 render review，而不是把 `not_checked` 当成通过。

出现位置：
- slide 9 | shape 8
