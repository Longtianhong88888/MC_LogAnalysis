# Agent QC Reminder

- decision: `hard_blocked`
- target_milestone: `final`
- hard_groups: `1`
- soft_groups: `0`
- advisory_groups: `0`
- full_report: `/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/validation/package_preflight/history/package_preflight_20260808_082832.json`

## Must Fix Before Milestone

### `artifact_integrity.package.slide_count_mismatch` × 1

`docProps/app.xml` 中的 `Slides` 统计与实际 slide 数不一致，这对移动端解析器是高风险信号。

suggested_fix: 在最终打包前重写 `docProps/app.xml` 的 slide 统计，保证和真实 deck 一致。

sample_locations:
- ppt

rendered_group_count: `1`
