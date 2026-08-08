# MC Log Analysis 机台日志分析工具 · 使用说明 Deck

## 任务定义
- 目标读者：机台日志分析工具的使用者（现场工程师 / 主管），中文环境，无人讲解也能读懂。
- 主使用场景：新用户培训材料 + 日常使用参考（可随时翻阅）。
- 目标动作：读者看完能理解工具能做什么、亮点在哪，并按 5 步完成一次机台日志分析并拿到 Excel / PPT 报告。
- 是否需要无人讲解也能读懂：是（self-contained）。
- 参考模板文件：无（不沿用 Analysis_Report.pptx，那是分析报告模板，不是说明 deck 模板）。
- 模板 / 品牌约束：无品牌素材；不使用任何机构 logo。
- 交付物要求：可编辑 pptx（16:9），正文中文宋体、英文 Times New Roman，正文字号 ≥12pt，表格 10.5pt；同时交付逐页预览图与验证证据。
- 验证要求：package_preflight / structure_precheck / 预览导出 / render_review / 人工 visual review。

## Deck Contract
- source_context：no_template
- delivery_context：self-contained_reading_deck
- communication_profile：technical_explainer
- visual_profile：corporate_clear
- density_profile：balanced_brief
- editability_profile：fully_editable
- typography / table policy：
  - 中文正文 12pt、1.5 倍行距、首行缩进 2 字符（正文段落）；标题 1.0 倍行距、段前段后 0.5 行
  - 页面标题 24pt、副标题 16pt、小标题 14pt、标签 10.5pt、图注 9pt
  - 表格 10.5pt、单倍行距、段前段后 0、单元格上下居中、表头居中、类目/文本列居左、数值列靠右
  - 字体：中文 宋体、英文 Times New Roman（标题可用黑体系，但保持成对切换）

## 模板取证
- 页面系统判断：无模板，空白页直生（build route = 空白页直生 editable deck）。
- 关键母版 / layout 元素：统一自定义页眉（左上标题区 + 右下页码/版本），用 slide 层原生形状实现，不依赖母版。
- 字号系统：按 theme_tokens（hero 40 / section 30 / page title 24 / subtitle 16 / minor 14 / body 12 / label 10.5 / caption 9 / table 10.5）。
- 计划采用的构建路线：空白页直生，python-pptx 原生文本/形状/表格；预览导出走 PowerPoint（本机已装）。
- 最小 PoC 结论：直接用 python-pptx 新建 16:9 页 + 自定义页眉即可稳定渲染。

## 风格与边界
- 风格参考：corporate_clear（清晰、稳定、克制），无花哨装饰。
- typography_profile：zh_formal（宋体正文 / Times 西文）
- domain_profile：无（技术使用说明，不需要研报纪律）
- visual_theme_preset：无（不使用预设配色；主色取深蓝 #1F4E79 + 浅蓝 #DEEBF7 + 中性灰）
- 允许使用的素材：项目自带内容（功能、流程、计算逻辑、制程参数），以及用 PIL 生成的真实甘特示例图（来自工具对 LM 日志的分析结果，作为“输出示例”证据）。
- 禁止使用的品牌元素：不出现具体厂商 logo / 受保护标识；不使用 Analysis_Report.pptx 内部数据页作为说明素材。
- 免责声明 / 风险边界：页面中的 UPH/EFF 数值示例仅用于说明界面与计算口径，不代表特定批次结果；甘特示例来自示例日志。
- 不允许发生的错误：把“本页要说明 / 建议讲者 / 帮助读者理解”等元叙述放进页面可见层；正文低于 12pt；表格文字低于 10.5pt；出现无信息理由的卡片墙。

## Anti-AI-Slop Prompt Intake
- 先读 prompt，再开始设计或写代码：已读 slide_design_system.md 的 anti-AI-slop 章节。
- 卡片使用理由：仅在“功能总览 / 亮点 / 注意事项”这类承担分组与比较语义的页面使用卡片；流程、表格、示意布局页不强行卡片化。
- 背景实现方式：统一浅色背景（slide background 或页面底层原生矩形），不使用整页图片背景。
- 圆角 / 色条 / 阴影 / 渐变使用理由：流程步骤节点用小圆角并带箭头（编码“步骤节点”语义）；不使用窄边强调条、阴影、渐变；角语言统一（功能卡直角，流程节点小圆角且全 deck 一致）。
- 矩形、节点、panel、卡片内部文字是否直接写入对应 shape：是，全部直接写入 shape.text_frame，不额外叠文本框；独立标题、页脚、图注才使用独立文本框。
