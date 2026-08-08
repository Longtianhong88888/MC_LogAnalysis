# Agent QC Reminder

- decision: `hard_blocked`
- target_milestone: `final`
- hard_groups: `1`
- soft_groups: `1`
- advisory_groups: `4`
- full_report: `/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/validation/structure_precheck/history/structure_precheck_20260808_082858.json`

## Must Fix Before Milestone

### `layout.overlap.object_overlap` × 1

文本估计边界与更高层对象发生显著重叠，存在相邻对象压字风险。

suggested_fix: 移动遮挡对象、增加留白，或重排文本框与卡片边界。

sample_locations:
- slide 8 | shape 4 | shape_text

## Needs Evidence Or Exception

### `validation_coverage.detector.flattened_graphic_internal_text` × 1

该图片对象可能承载内部文字或图表标签，但结构预检无法看到图片内部对象边界，需要交给 render review。

suggested_fix: 若该图片内部含文字、刻度或标签，请在预览导出后执行 render review，而不是把 `not_checked` 当成通过。

sample_locations:
- slide 9 | shape 8 | picture

## Advisories

### `typography.font_size.fragmentation` × 1

检测到字号系统问题；当前未解析出 active role token，需先确认模板、语言和语义 role。

suggested_fix: 把相同语义的文字收敛到 hero / section / page title / subtitle / body / label / caption / table token。

sample_locations:
- ppt

### `typography.font_size.outside_scale` × 14

检测到字号系统问题为 13pt×5, 56pt×3, 10pt×2；当前未解析出 active role token，需先确认模板、语言和语义 role。

suggested_fix: 把该文本绑定到已有 typography token；确需新档位时先更新 theme_tokens 并记录语义用途。

actual_values: 10pt×2, 13pt×5, 18pt×1, 20pt×1, 36pt×1, 44pt×1, 56pt×3

sample_locations:
- slide 2 | shape 10 | shape_text
- omitted `13` locations; see full report.

### `typography.font_size.outside_scale` × 1

当前中文正文字号为 13pt×1；active `theme_tokens.body_font_pt` 推荐 12pt。

suggested_fix: 如无模板、品牌或已登记的 profile 例外，直接改为 12pt。

actual_values: 13pt×1

sample_locations:
- slide 2 | shape 17 | shape_text

### `typography.font_size.role_drift` × 1

当前中文正文字号为 10.5pt×1；active `theme_tokens.body_font_pt` 推荐 12pt。

suggested_fix: 如无模板、品牌或已登记的 profile 例外，直接改为 12pt。

actual_values: 10.5pt×1

sample_locations:
- slide 11 | shape 6 | shape_text

rendered_group_count: `6`
