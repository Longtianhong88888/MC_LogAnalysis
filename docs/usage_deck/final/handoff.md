# Handoff

## 交付物
- 可编辑 PPTX：`final/机台log分析使用说明.pptx`（16:9，13 页，基于 `PPT模板.pptx` 的 master-first 继承，python-pptx 原生文本/形状/表格/图片）
- 逐页预览（结构近似渲染）：`build/rendered/structure_preview/`
- 验证证据：`validation/package_preflight/`、`validation/structure_precheck/`、`validation/visual/review_log.md`
- 源文档：`brief.md`、`deck_narrative.md`、`build/generated/slide_specs.yaml`、`scripts/build_deck.py`

## 页面结构
1 封面 → 2 工具概览 → 3 核心功能 → 4 功能亮点 → 5 快速上手（5 步）→ 6 界面导览 → 7 制程模板 → 8 UPH 计算逻辑 → 9 步骤甘特图 → 10 EFF/状态/报警 → 11 输出物 → 12 使用注意事项 → 13 结尾

（第3页起标题带章节小字：第1章 功能与亮点 / 第2章 操作教学 / 第3章 制程与口径 / 第4章 输出与注意）

## 验证结论
- package_preflight：通过（0 error）
- structure_precheck：通过（0 error；封面 54pt 为模板字号例外记 warning；甘特 PNG 内部文字 not_checked）
- render_review：未执行（环境无法导出高保真成图，见 review_log）

## 后续可继续
- 在 PowerPoint 中打开复核成图效果
- 逐页措辞微调、补充真实界面截图、调整配色或版式
