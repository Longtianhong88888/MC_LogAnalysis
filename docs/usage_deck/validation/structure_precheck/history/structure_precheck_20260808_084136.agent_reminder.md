# Agent QC Reminder

- decision: `hard_blocked`
- target_milestone: `final`
- hard_groups: `1`
- soft_groups: `0`
- advisory_groups: `2`
- full_report: `/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/validation/structure_precheck/history/structure_precheck_20260808_084136.json`

## Must Fix Before Milestone

### `layout.text_fit.bounds_overflow` × 10

文本估计边界已经越出可用内容区，存在明确的文本框 fit 失败风险。

suggested_fix: 增加文本框高度、减少文案密度，或把内容拆到更多卡片 / 更多页。

actual_values: 24pt×10

sample_locations:
- slide 10 | shape 2 | shape_text
- slide 11 | shape 2 | shape_text
- slide 12 | shape 2 | shape_text
- omitted `7` locations; see full report.

## Advisories

### `typography.font_size.fragmentation` × 1

检测到字号系统问题；当前未解析出 active role token，需先确认模板、语言和语义 role。

suggested_fix: 把相同语义的文字收敛到 hero / section / page title / subtitle / body / label / caption / table token。

sample_locations:
- ppt

### `typography.font_size.outside_scale` × 15

检测到字号系统问题为 11pt×10, 10pt×2, 54pt×1；当前未解析出 active role token，需先确认模板、语言和语义 role。

suggested_fix: 把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

actual_values: 10pt×2, 11pt×10, 18pt×1, 20pt×1, 54pt×1

sample_locations:
- slide 1 | shape 2 | shape_text
- omitted `14` locations; see full report.

rendered_group_count: `3`
