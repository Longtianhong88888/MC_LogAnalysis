# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`0`
- 警告数：`14`
- 未检查数：`0`

## 摘要

- `warning` / `font_size_outside_theme_scale`: 14

## 问题清单

### `warning`

#### `font_size_outside_theme_scale`

显式字号不属于 active theme_tokens 的语义字号表，可能是局部手填档位。

建议：把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

出现位置：
- slide 1 | shape 2 | font_sizes_pt=54
- slide 1 | shape 7 | font_sizes_pt=10
- slide 2 | shape 4 | font_sizes_pt=10
- slide 3 | shape 11 | font_sizes_pt=10
- slide 4 | shape 11 | font_sizes_pt=10
- slide 5 | shape 24 | font_sizes_pt=10
- slide 6 | shape 19 | font_sizes_pt=10
- slide 7 | shape 7 | font_sizes_pt=10
- slide 8 | shape 21 | font_sizes_pt=10
- slide 9 | shape 9 | font_sizes_pt=10
- slide 10 | shape 8 | font_sizes_pt=10
- slide 11 | shape 7 | font_sizes_pt=10
- 其余 2 个位置见 JSON 报告
