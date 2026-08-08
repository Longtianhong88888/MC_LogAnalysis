# MC Log Analysis 机台日志分析工具 · 使用说明 Deck

## 任务定义
- 目标读者：机台日志分析工具的使用者（现场工程师 / 主管），中文环境，无人讲解也能读懂。
- 主使用场景：新用户培训材料 + 日常使用参考（可随时翻阅）。
- 目标动作：读者看完能理解工具能做什么、亮点在哪，并按 5 步完成一次机台日志分析并拿到 Excel / PPT 报告。
- 是否需要无人讲解也能读懂：是（self-contained）。
- 参考模板文件：`PPT模板.pptx`（项目根目录，鸿海/富士康风格模板）。
- 模板 / 品牌约束：template_locked——必须继承模板 master/layout（版权行、右上 logo、页码/页脚、封面/目录/章节/内容页体系），不重建品牌。
- 交付物要求：可编辑 pptx（16:9），正文中文宋体、英文 Times New Roman，正文字号 ≥12pt，表格 10.5pt；同时交付逐页预览图与验证证据。
- 验证要求：package_preflight / structure_precheck / 预览导出 / render_review / 人工 visual review。

## Deck Contract
- source_context：template_locked
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
- 页面系统判断：layout 族 = 1_cover（封面）/ 1_agenda（目录）/ 1~4_new category（章节页）/ 1~5_content page（内容页）；模板自带 2 张示例页（封面 + 目录）。
- 关键母版 / layout 元素：master 含底部版权 “© 2026 Hon Hai Precision Industry Co., Ltd.”（10pt）与右上 logo 图片（0.58in）；layout 含页码占位（‹#› 右下）、页脚占位、内容页 TITLE + OBJECT（左文本 7.19in）+ BITMAP（右图 4.59in）占位。
- 字号系统：封面标题文本框 54pt（EF5149）；内容页标题继承 layout（构建时显式设 24pt）；正文 12pt；版权 10pt；表格 10.5pt。
- 配色：模板主题 强调色 EF5149（红橙，封面标题/大数字）+ 深蓝 083C63（页码/次级标题）+ 白底；本 deck 沿用该配色（不再用自定义 1F4E79 蓝）。
- 计划采用的构建路线：master-first / layout-first——基于 `PPT模板.pptx` 打开，删除示例页，用模板 layout 逐页创建并继承 master 版权/logo/页码；封面标题按模板样式（54pt EF5149）自加文本框。
- 最小 PoC 结论：新建 layout 页后版权/logo/页码/页脚自动继承（需在构建后抽查确认）。

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
