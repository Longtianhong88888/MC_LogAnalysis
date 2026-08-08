# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`10`
- 警告数：`16`
- 未检查数：`0`

## 摘要

- `error` / `textbox_fit_failure`: 10
- `warning` / `font_size_fragmentation`: 1
- `warning` / `font_size_outside_theme_scale`: 15

## 问题清单

### `error`

#### `textbox_fit_failure`

文本估计边界已经越出可用内容区，存在明确的文本框 fit 失败风险。

建议：增加文本框高度、减少文案密度，或把内容拆到更多卡片 / 更多页。

出现位置：
- slide 3 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=622.59
- slide 4 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=427.66
- slide 5 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=674.82
- slide 6 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=520.81
- slide 7 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=592.83
- slide 8 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=512.18
- slide 9 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=548.19
- slide 10 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=557.12
- slide 11 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=558.9
- slide 12 | shape 2 | font_sizes_pt=24 | overflow_ratio=0.0483 | bottom_gap_pt=-2.71 | right_gap_pt=667.23

### `warning`

#### `font_size_fragmentation`

整份 deck 的显式字号档位过多，字号系统可能已经碎片化。

建议：把相同语义的文字收敛到 hero / section / page title / subtitle / body / label / caption / table token。

出现位置：
- font_sizes_pt=9,10,10.5,11,12,14,18,20,24,40,54

#### `font_size_outside_theme_scale`

显式字号不属于 active theme_tokens 的语义字号表，可能是局部手填档位。

建议：把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

出现位置：
- slide 1 | shape 2 | font_sizes_pt=54
- slide 1 | shape 3 | font_sizes_pt=20
- slide 1 | shape 6 | font_sizes_pt=10
- slide 3 | shape 2 | font_sizes_pt=11
- slide 4 | shape 2 | font_sizes_pt=11
- slide 5 | shape 2 | font_sizes_pt=11
- slide 6 | shape 2 | font_sizes_pt=11
- slide 7 | shape 2 | font_sizes_pt=11
- slide 8 | shape 2 | font_sizes_pt=11
- slide 9 | shape 2 | font_sizes_pt=11
- slide 10 | shape 2 | font_sizes_pt=11
- slide 11 | shape 2 | font_sizes_pt=11
- 其余 3 个位置见 JSON 报告
