# Agent QC Reminder

- decision: `proceed_with_advisories`
- target_milestone: `final`
- hard_groups: `0`
- soft_groups: `0`
- advisory_groups: `1`
- full_report: `/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/validation/structure_precheck/history/structure_precheck_20260808_090702.json`

## Advisories

### `typography.font_size.outside_scale` × 1

检测到字号系统问题为 54pt×1；当前未解析出 active role token，需先确认模板、语言和语义 role。

suggested_fix: 把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

actual_values: 54pt×1

sample_locations:
- slide 1 | shape 2 | shape_text

rendered_group_count: `1`
