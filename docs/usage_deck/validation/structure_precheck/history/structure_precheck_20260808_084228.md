# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`10`
- 警告数：`1`
- 未检查数：`0`

## 摘要

- `error` / `textbox_fit_failure`: 10
- `warning` / `font_size_outside_theme_scale`: 1

## 问题清单

### `error`

#### `textbox_fit_failure`

文本估计边界已经越出可用内容区，存在明确的文本框 fit 失败风险。

建议：增加文本框高度、减少文案密度，或把内容拆到更多卡片 / 更多页。

出现位置：
- slide 3 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-554.4 | right_gap_pt=0
- slide 4 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-891.36 | right_gap_pt=0
- slide 5 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-424.8 | right_gap_pt=0
- slide 6 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-709.92 | right_gap_pt=0
- slide 7 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-606.24 | right_gap_pt=0
- slide 8 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-735.84 | right_gap_pt=0
- slide 9 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-684 | right_gap_pt=0
- slide 10 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-658.08 | right_gap_pt=0
- slide 11 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-658.08 | right_gap_pt=0
- slide 12 | shape 2 | font_sizes_pt=24 | overflow_ratio=0 | bottom_gap_pt=-476.64 | right_gap_pt=0

### `warning`

#### `font_size_outside_theme_scale`

显式字号不属于 active theme_tokens 的语义字号表，可能是局部手填档位。

建议：把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

出现位置：
- slide 1 | shape 2 | font_sizes_pt=54
