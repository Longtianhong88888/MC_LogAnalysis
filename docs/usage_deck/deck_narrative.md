---
deck:
  title: "MC Log Analysis 机台日志分析工具 · 使用说明"
  audience: "机台日志分析工具使用者（现场工程师 / 主管）"
  scenario: "新用户培训与日常使用参考"
  objective: "理解工具功能与亮点，并按 5 步完成机台日志分析与报告输出"
  source_context: "no_template"
  delivery_context: "self-contained_reading_deck"
  communication_profile: "technical_explainer"
  visual_profile: "corporate_clear"
  density_profile: "balanced_brief"
  editability_profile: "fully_editable"
  template_file: null
  theme_tokens:
    typography_profile: "zh_formal"
    domain_profile: null
    visual_theme_preset: null
    page_width_in: 13.333
    page_height_in: 7.5
    hero_title_font_pt: 40
    section_title_font_pt: 30
    page_title_font_pt: 24
    subtitle_font_pt: 16
    minor_title_font_pt: 14
    body_font_pt: 12
    label_font_pt: 10.5
    caption_font_pt: 9
    title_line_spacing_multiple: 1.0
    body_line_spacing_multiple: 1.5
    title_paragraph_space_lines: 0.5
    body_first_line_indent_chars: 2
    body_paragraph_space_lines: 0.5
    latin_font_name: "Times New Roman"
    east_asia_font_name: "宋体"
    table_font_pt: 10.5
    table_line_spacing_multiple: 1.0
    table_paragraph_space_lines: 0
    table_first_line_indent_chars: 0
    table_vertical_anchor: "middle"
    table_header_alignment: "center"
    table_index_alignment: "left"
    table_text_alignment: "left"
    table_numeric_alignment: "right"
    left_margin_in: 0.78
    right_margin_in: 12.55
---

# MC Log Analysis 机台日志分析工具 · 使用说明

## Global Narrative
- 这套 deck 的主判断：机台日志分析工具把“看日志、算 UPH/EFF、查报警、出报告”从手工变成一键完成，使用者只需选文件夹、选制程、点自动报告。
- 这套 deck 的论证主线：先让读者知道工具能解决什么问题（功能与亮点），再教按 5 步完成一次分析（操作），最后给出制程口径、计算逻辑、输出物与注意事项，保证读者能独立使用并读懂结果。
- 主题词：一键分析、制程模板、瓶颈自动判定、换盘分摊、步骤甘特图、异常标红、自动报告。
- 禁区：不出现厂商 logo；不把内部实现细节（函数名、配置字段）当作读者必读内容；不把讲稿话术写进页面。

## Planning Checkpoint
- 全局基调：清晰、稳定、克制的技术说明；浅色背景 + 深蓝主色；中文宋体正文。
- 章节结构：第 1 章 功能与亮点（S01–S03）；第 2 章 操作教学（S04–S05）；第 3 章 制程与口径（S06–S09）；第 4 章 输出与注意（S10–S11）；结尾（S12）。
- 资产需求：原生表格（制程对比、输出物、注意事项）、diagram-visual（操作流程、界面示意）、真实甘特示例图（PIL 生成，来自 LM 示例日志）、无生图。
- layout 与节奏：封面 hero → 概览 big-number → 功能网格（dense）→ 亮点网格 → 流程（transition）→ 界面示意 → 表格（dense）→ 公式卡 → 甘特示例（evidence）→ 表格 → 检查表 → closing。
- anti-AI-slop 约束：卡片仅用于功能/亮点/注意分组；流程用步骤节点+箭头；表格用原生 table；矩形文字直接写入 shape；无阴影/渐变/窄边条。

### S01 | 封面：机台日志分析工具 · 使用说明
```yaml slide_spec
title: "MC Log Analysis 机台日志分析工具 · 使用说明"
reader_question: "这是什么工具、这份文档讲什么"
page_task: "orient"
reading_mode: "scan"
archetype: "hero-statement"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "一份文档，从功能亮点到操作步骤，讲清这个机台日志分析工具怎么用"
layout_recipe: "editorial-cover"
rhythm_role: "opener"
required_assets: []
```

**On-slide Copy.** 大标题“MC Log Analysis”；副标题“机台日志分析工具 · 使用说明”；下方一行：功能与亮点 · 操作教学 · 制程与口径 · 输出与注意；版本/日期行：v1.0 · 内部使用。

**Layout Notes.** 深蓝主色大标题 + 细线分隔 + 四章节导航点；无卡片、无背景图。

**Anti-slop Notes.** 封面只用原生文本框与线条，无整页背景、无阴影渐变。

### S02 | 工具概览：一个工具完成机台日志的六类分析
```yaml slide_spec
title: "一个工具，完成机台日志的六类分析与报告"
reader_question: "这工具到底能干什么"
page_task: "orient"
reading_mode: "scan"
archetype: "hero-statement"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "文档合并与拆分、UPH、EFF、报警、机台状态、一键分析——一个界面全部完成，并自动输出 Excel 与 PPT 报告"
layout_recipe: "editorial-big-number"
rhythm_role: "opener"
required_assets: []
```

**On-slide Copy.** 主句：把机台日志的“读、算、查、报”一次做完。三组大数字：6 类分析功能；5 种制程模板（LM/CAW/FR/SA/ACF）；4+1 类输出（UPH/EFF/报警/状态 Excel + 自动 PPT 报告）。末行：支持一键分析，自动完成全部功能并生成报告。

**Layout Notes.** 三个大数字横向排列 + 短说明；数字用深蓝，说明用灰色正文。

**Anti-slop Notes.** 大数字页不使用卡片，用大字号 + 细线分组。

### S03 | 核心功能总览
```yaml slide_spec
title: "六大功能，覆盖日志分析的完整链路"
reader_question: "每个功能分别解决什么问题"
page_task: "explain"
reading_mode: "guided"
archetype: "board-memo"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "合并拆分负责找日志，UPH/EFF/报警/状态负责算指标，一键分析负责出报告"
layout_recipe: "business-summary-grid"
rhythm_role: "evidence"
required_assets: []
```

**On-slide Copy.** 六格（每格：功能名 + 一句话）：
- 文档合并与内容拆分：按关键词/分隔符提取指定行，支持按 PLC 分组导出，异常行自动标红
- UPH 分析：按 CoreTech AME 口径输出 实际/Pure/Derated M1/M2/有效UPH，自动判定瓶颈
- EFF 分析：操作时间 ÷ 计划生产时间，停机按 EReason 清单区分 pDT / uDT
- 报警分析：按关键词统计报警，EReason 中文名映射
- 机台状态分析：status 行或活动/停机关键词推导 RUN / IDLE / DOWN 时间线
- 一键分析（自动报告）：一次运行完成 UPH/EFF/报警/状态 4 项分析，导出 4 个 Excel 并自动生成 PPT 报告；文档合并与内容拆分单独执行（大日志制程提速）

**Layout Notes.** 六格 3×2 直角卡片，格内文字直接写入卡片 shape。

**Anti-slop Notes.** 卡片承担“功能分组”语义，故使用直角卡片；每格一个小标题 + 一句话，无装饰条。

### S04 | 功能亮点
```yaml slide_spec
title: "亮点：自动模板、瓶颈判定、换盘分摊、步骤甘特、异常标红、自动报告"
reader_question: "为什么用这个工具而不是手工看日志"
page_task: "persuade"
reading_mode: "decision"
archetype: "board-memo"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "六个亮点让分析结果更准、更省事、更直观"
layout_recipe: "business-summary-grid"
rhythm_role: "evidence"
required_assets: []
```

**On-slide Copy.** 六格（亮点名 + 说明）：
- 制程模板一键预填：选 LM/CAW/FR/SA/ACF，自动带入触发词、报警关键词与计算逻辑
- 瓶颈自动判定：SA 四工位、CAW 双机台自动取最慢环节，UPH 口径与客户定义一致
- 换盘时间平摊：整盘打标/装盘结束后的下料-上料时间按每盘颗数摊入单颗 CT
- 步骤深度分析 + 甘特图：按轴/平台运动节拍拆步骤，Excel 甘特图直接看出先后与并行
- 异常日志自动标红：报警/停机/步骤超时行标红，剔除产品码中的 NG 误报
- 自动 PPT 报告：汇总 + 图表 + 瓶颈工序甘特图，时间格式统一、可编辑

**Layout Notes.** 六格 3×2 直角卡片；每格亮点名用深蓝，说明灰色。

**Anti-slop Notes.** 同 S03，卡片承担分组语义；无装饰条、无圆角。

### S05 | 快速上手：5 步完成一次分析
```yaml slide_spec
title: "5 步完成一次机台日志分析"
reader_question: "我怎么开始用这个工具"
page_task: "explain"
reading_mode: "guided"
archetype: "process-flow"
asset_mode: "diagram-visual"
validation_mode: "preview_only"
key_message: "选源文件夹 → 选输出文件夹 → 选制程模板 → 选功能 → 自动报告，5 步出结果"
layout_recipe: "technical-flow-horizontal"
rhythm_role: "transition"
required_assets: ["flow_steps_diagram"]
```

**On-slide Copy.** 五个步骤节点（横向箭头连接）：
1 选择源文件夹（机台日志目录，支持子文件夹）→ 2 选择输出文件夹 → 3 选择制程模板（自动预填参数）→ 4 选择功能（合并/UPH/EFF/报警/状态/一键）→ 5 自动报告（结果在界面显示，并导出 Excel/PPT）

**Layout Notes.** 5 个圆角步骤节点 + 横向箭头；节点内文字直接写入 shape；每节点下方一行补充说明。

**Anti-slop Notes.** 流程节点用统一小圆角并编码“步骤”语义；箭头用原生直线箭头；无卡片化。

### S06 | 界面导览
```yaml slide_spec
title: "界面一看就懂：左边选功能，右边筛日志，下方看结果"
reader_question: "界面上的区域各是做什么的"
page_task: "explain"
reading_mode: "guided"
archetype: "research-note"
asset_mode: "diagram-visual"
validation_mode: "preview_only"
key_message: "功能选择在左、日志文件筛选在右、解析结果在下方大区"
layout_recipe: "technical-layout-map"
rhythm_role: "evidence"
required_assets: ["ui_layout_diagram"]
```

**On-slide Copy.** 一个界面示意（原生形状绘制，标注三区）：
- 左侧“功能选择”：文档合并与内容拆分 / UPH 分析 / EFF 分析 / 报警分析 / 机台状态分析 / 一键分析
- 右侧“日志文件筛选 + 制程模板”：制程下拉、文件筛选框（自动填充与制程匹配的内容，可手改）、解析参数
- 下方“解析结果”：分析结果表格与进度显示
- 顶部“使用说明”按钮：各制程使用说明与计算逻辑；右下角版权行

**Layout Notes.** 用三个矩形分区模拟界面（左窄、右中、下大），每区画内部占位线；文字直接写入分区矩形；标注为“界面示意”。

**Anti-slop Notes.** 分区矩形承载“界面布局”语义；标注“示意”避免被误认为真实截图；无阴影。

### S07 | 制程模板说明
```yaml slide_spec
title: "五种制程模板，参数与算法已按机台配好"
reader_question: "不同机台的日志怎么算才是对的"
page_task: "compare"
reading_mode: "reference"
archetype: "comparison-matrix"
asset_mode: "table-native"
validation_mode: "preview_only"
key_message: "每个制程的周期事件、并行结构与瓶颈口径都不同，模板按机台自动选择"
layout_recipe: "table-comparison"
rhythm_role: "dense"
required_assets: ["process_table"]
```

**On-slide Copy.** 原生表格：制程 | 周期完成事件 | 结构 | UPH 口径要点
- LM 激光打标 | MarkEnd1 | 单机台；每盘 4 批×6 颗 | 换盘时间按 24 颗平摊
- CAW 组装 | 放熟料完成 / 去交换位 | PLC1 焊接机 + PLC2 上料机（左右并行） | 双机台瓶颈，取 CT 长者
- FR 点胶 | 轴点胶完成 | 左轴/右轴并行 | Pure UPH ×0.5（单轴），整机 M1/M2 = 左+右
- SA 四工位 | 各工位完成事件 | 点胶/贴附/热压/检测并行 | 自动判定瓶颈工位
- ACF 三機 | 更新Carrier盘 / Cavity cnt:1 / UnloadDuts Finish | 上料機/主機/下料機 分文件夹 | 每盘颗数按 Tray ID 动态统计
注：另有“通用（手动配置）”与“自定义”模板，不套用固定逻辑。

**Layout Notes.** 原生表格，表头居中、类目列居左、文本列居左；行高充足，单元格上下居中。

**Anti-slop Notes.** 真正的数据比较用原生表格，不用 shape 拼格子。

### S08 | UPH 计算逻辑
```yaml slide_spec
title: "UPH 口径：实际、Pure、Derated M1/M2 与有效 UPH"
reader_question: "Excel 里几个 UPH 分别是什么意思"
page_task: "explain"
reading_mode: "guided"
archetype: "research-note"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "实际 UPH 看真实产出，Pure 看理想节拍，Derated 剔离群点，有效 UPH 把换盘时间摊进单颗"
layout_recipe: "research-formula-cards"
rhythm_role: "evidence"
required_assets: []
```

**On-slide Copy.** 五条口径（公式行 + 一句话）：
- 实际 UPH = 产出数 ÷ 统计时长 × 3600
- Pure UPH = 3600 × 每周期产出 ÷ 理想周期CT（未填时取正常周期平均）
- Derated UPH M2 = 3600 × 每周期产出 ÷ 有效平均周期（剔除 <0.9×理想CT、>1.1×最大理论CT 的离群点）；多模组整机 = 各模组 M2 之和
- Derated UPH M1 = EM 投入数 ÷ RUN 时长（多模组整机 = 各模组 M1 之和）
- 有效 UPH = 3600 × 每周期产出 ÷（基础周期 + 每颗换盘开销），每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数
周期分类：>计划性停机阈值=计划性停机；>正常阈值=异常周期；其余=正常周期。

**Layout Notes.** 五条公式行用统一左对齐排版，公式加粗、说明灰色；下方一行周期分类说明。

**Anti-slop Notes.** 公式行不用卡片，用左对齐文本 + 细线分隔，保持可读。

### S09 | 步骤深度分析与甘特图
```yaml slide_spec
title: "步骤拆到运动节拍，甘特图一眼看出先后与并行"
reader_question: "单颗周期里每一步花多久、哪一步先哪一步后"
page_task: "evidence"
reading_mode: "decision"
archetype: "research-note"
asset_mode: "python-figure-image"
validation_mode: "preview_only"
key_message: "每个区块步骤时间总和≈CT；甘特图用颜色填充直观显示并行与先后"
layout_recipe: "chart-spotlight-with-takeaways"
rhythm_role: "evidence"
required_assets: ["gantt_example_png"]
```

**On-slide Copy.** 主句：步骤按轴/平台运动节拍拆分（如 LM：打标前间隔 → Z轴焦距定位 → 激光打标）。右侧放真实甘特示例图（来自 LM 示例日志）：每行一个步骤、每列一个时间块、填充列数=时长；并行步骤同一时间区间的多行并排。图注：示例来自示例日志，不代表特定批次。下句：异常判定 = 中位 + 超时秒数，超时行在日志 Excel 中自动标红。

**Layout Notes.** 左结论 + 右甘特示例图；图用 PIL 生成 PNG（真实 LM 数据），保留比例不拉伸。

**Anti-slop Notes.** 甘特图是真实输出示例（证据），不是装饰；图注标明来源。

### S10 | EFF / 机台状态 / 报警分析
```yaml slide_spec
title: "EFF、状态与报警：三张表讲清设备效率与异常"
reader_question: "EFF/状态/报警分析分别输出什么"
page_task: "explain"
reading_mode: "guided"
archetype: "board-memo"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "EFF=操作时间/计划生产时间；状态自动推导 RUN/IDLE/DOWN；报警按关键词统计并可映射中文名"
layout_recipe: "business-summary-grid"
rhythm_role: "evidence"
required_assets: []
```

**On-slide Copy.** 三格：
- EFF 分析：EFF = 操作时间(运行+待机) ÷ 计划生产时间；停机按 ReasonID 拆 pDT / uDT（EReason 清单优先）
- 机台状态分析：优先读 status:RUN/IDLE/DOWN 行；无 status 时按“活动关键词 + 停机关键词”推导时间线，输出各状态时长/占比/小时分布
- 报警分析：按关键词命中计数，按机台/模组汇总；EReason 清单映射中文原因名称

**Layout Notes.** 三格直角卡片，与 S03/S04 同语言。

**Anti-slop Notes.** 卡片承担分组语义，保持全 deck 角语言一致。

### S11 | 输出物：Excel 与 PPT 报告
```yaml slide_spec
title: "一次分析，输出可编辑的 Excel 与 PPT 报告"
reader_question: "运行完我能拿到什么文件"
page_task: "archive"
reading_mode: "reference"
archetype: "appendix-dense"
asset_mode: "table-native"
validation_mode: "preview_only"
key_message: "4 个分析 Excel + 合并日志 + 自动 PPT 报告，时间格式统一"
layout_recipe: "table-comparison"
rhythm_role: "dense"
required_assets: ["output_table"]
```

**On-slide Copy.** 原生表格：文件 | 内容
- UPH_Analysis.xlsx | Summary / AMESummary / CycleDetail / EMProduction / 步骤分析 / 步骤甘特图
- EFF_Analysis.xlsx | EFF 汇总与停机 Pareto（含 pDT/uDT）
- Alarm_Analysis.xlsx | 报警汇总、关键词分布、明细（EReason 中文名）
- Status_Analysis.xlsx | 状态汇总与小时分布
- LogAnalysis.xlsx | 合并日志（异常行标红）；大文件按日志逐个导出
- Analysis_Report.pptx | 自动报告：UPH/EFF/停机 Pareto/报警/状态 + 瓶颈工序甘特图
时间格式约定：低于 60 秒按秒显示，超过 60 秒按 h:mm:ss；PPT 汇总时间显示到秒。

**Layout Notes.** 原生表格两列（文件/内容），文本列居左。

**Anti-slop Notes.** 数据列表用原生表格；无卡片。

### S12 | 使用注意事项
```yaml slide_spec
title: "使用前注意这几点，避免踩坑"
reader_question: "有哪些已知边界要提前知道"
page_task: "explain"
reading_mode: "guided"
archetype: "board-memo"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "大文件自动按文件导出；EReasonlist 按文件名匹配；PPT 模板放程序同目录；日志文件筛选可手动覆盖"
layout_recipe: "business-summary-grid"
rhythm_role: "evidence"
required_assets: []
```

**On-slide Copy.** 四条：
- 大日志保护：原始日志超过约 100 万行时，自动放弃合并、按日志文件逐个导出 Excel
- EReasonlist：根目录保留 EReasonlist 文件夹，新制程按文件名放入自己的清单，用于状态推导与报警映射
- PPT 模板：Analysis_Report.pptx 放到程序同目录即可正常生成报告；模板含内部数据，仅限内部传送
- 灵活覆盖：日志文件筛选框自动填充与制程匹配的内容，用户有特殊需求可手动输入

**Layout Notes.** 四格直角卡片，与 S03/S04/S10 同语言。

**Anti-slop Notes.** 卡片承担条目分组语义。

### S13 | 结尾
```yaml slide_spec
title: "现在就可以开始第一次分析"
reader_question: "看完之后第一步做什么"
page_task: "orient"
reading_mode: "scan"
archetype: "hero-statement"
asset_mode: "text-layout-native"
validation_mode: "preview_only"
key_message: "选日志文件夹 → 选制程 → 点一键分析，5 分钟拿到第一份报告"
layout_recipe: "editorial-cover"
rhythm_role: "closing"
required_assets: []
```

**On-slide Copy.** 大标题：现在就可以开始第一次分析。副句：选日志文件夹 → 选制程模板 → 点“自动报告”。末尾行：功能与亮点 · 操作教学 · 制程与口径 · 输出与注意 · 版本 v1.0。

**Layout Notes.** 与封面同语言（深蓝大标题 + 细线），形成首尾呼应。

**Anti-slop Notes.** 结尾页只用文本框与线条。
