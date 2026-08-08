# PPTX Structure Precheck Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`0`
- 警告数：`1`
- 未检查数：`0`

## 摘要

- `warning` / `font_size_outside_theme_scale`: 1

## 问题清单

### `warning`

#### `font_size_outside_theme_scale`

显式字号不属于 active theme_tokens 的语义字号表，可能是局部手填档位。

建议：把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

出现位置：
- slide 1 | shape 2 | font_sizes_pt=54
