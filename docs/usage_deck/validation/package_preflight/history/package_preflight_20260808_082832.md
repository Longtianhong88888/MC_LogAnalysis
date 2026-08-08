# PPTX Package Preflight Report

- 输入文件：`/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/build/pptx/usage_deck.pptx`
- 错误数：`1`
- 警告数：`0`
- 未检查数：`0`

## 摘要

- `error` / `docprops_slide_count_mismatch`: 1

## 问题清单

### `error`

#### `docprops_slide_count_mismatch`

`docProps/app.xml` 中的 `Slides` 统计与实际 slide 数不一致，这对移动端解析器是高风险信号。

建议：在最终打包前重写 `docProps/app.xml` 的 slide 统计，保证和真实 deck 一致。

出现位置：
- 
