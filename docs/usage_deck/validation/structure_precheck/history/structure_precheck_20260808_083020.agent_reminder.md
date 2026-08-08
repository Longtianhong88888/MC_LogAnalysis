# Agent QC Reminder

- decision: `hard_blocked`
- target_milestone: `final`
- hard_groups: `1`
- soft_groups: `1`
- advisory_groups: `0`
- full_report: `/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/validation/structure_precheck/history/structure_precheck_20260808_083020.json`

## Must Fix Before Milestone

### `layout.overlap.object_overlap` × 4

文本估计边界与更高层对象发生显著重叠，存在相邻对象压字风险。

suggested_fix: 移动遮挡对象、增加留白，或重排文本框与卡片边界。

sample_locations:
- slide 8 | shape 12 | shape_text
- slide 8 | shape 16 | shape_text
- slide 8 | shape 20 | shape_text
- omitted `1` locations; see full report.

## Needs Evidence Or Exception

### `validation_coverage.detector.flattened_graphic_internal_text` × 1

该图片对象可能承载内部文字或图表标签，但结构预检无法看到图片内部对象边界，需要交给 render review。

suggested_fix: 若该图片内部含文字、刻度或标签，请在预览导出后执行 render review，而不是把 `not_checked` 当成通过。

sample_locations:
- slide 9 | shape 8 | picture

rendered_group_count: `2`
