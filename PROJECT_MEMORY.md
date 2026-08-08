# 项目记忆（MC_LogAnalysis）

> 本文档用于跨会话延续工作。更新代码后请同步维护本文件。

## 项目概况

- 机台日志分析工具（PyQt5 桌面应用），支持 文档合并与内容拆分 / UPH 分析 / EFF 分析 / 报警分析 / 机台状态分析 / 一键分析（全部）。
- 仓库：`https://github.com/Longtianhong88888/MC_LogAnalysis`（分支 main）
- 本地路径：`/Users/user/Desktop/PY/MC_LogAnalysis`，venv 在 `venv/`
- 开发环境依赖：PyQt5、pandas、openpyxl、chardet、python-pptx、xlsxwriter（均已装入 venv）

## 重要约定（务必遵守）

1. **推送规则**：用户明确命令「推送」前，不得 push；提交可在本地保留。
2. **PPT 模板**：`Analysis_Report.pptx` 含内部数据，**不随打包**；用户将模板放到 exe 同目录即可，未放则用内置简洁版式。
3. **EReasonList**：根目录 `EReasonList/` 按文件名匹配（如 ACF_EReasonList.xlsx），新用户放入自己制程的清单即可。
4. **打包**：使用 `--onedir`（免解压秒开），不要用 `--onefile`。macOS：`pyinstaller -y --onedir --windowed --icon log.ico --add-data "Machine.png:." --add-data "log.ico:." --name MC_LogAnalysis main.py`。GitHub Actions（`.github/workflows/build.yml`）在 push 到 main 时自动构建 Windows 版。

## 制程模板（models/process_templates.py）

- **通用（手动配置）**：不套模板，按界面当前参数分析全部日志。
- **自定义**：读 `custom_template.json`（gitignore），保存/复用用户自己的参数。
- **LM 激光打标**：触发 `MarkEnd1`，1颗/周期。
- **CAW 组装**：触发 `放熟料完成,放生料完成`；文件筛选 记录PLC/RAYPRUS/Debug/设备状态。
- **FR 点胶**：左轴/右轴并行，触发 `轴点胶完成,有漏点产品`；Pure UPH ×0.5（单轴），整机 AME M1/M2=左轴+右轴。
- **SA 四工位**：点胶/贴附/热压/检测，自动判定瓶颈工位；每排 2 颗；换盘 = JigUnloading→JigLoading 间隔平摊。
- **ACF 三機**（分文件夹 上料機/主機/下料機）：
  - 上料機：触发 `更新Carrier盘` × 8颗/批；每盘颗数按 carrierId 动态统计（8颗/盘）；换盘 = 请求出托盘→等待Carrier Ready（3.64s）。
  - 主機：触发 `Cavity cnt:1` × 8颗/批（一批=一个 carrier）；carrier 走 CMS 输送线，周期已含换盘。
  - 下料機：触发 `UnloadDuts Finish` × 3颗；每盘颗数按 CubeTrayId 动态统计（24颗/盘）；换盘 = 清除2号托盘→轨道2进板成功（12.76s）。
  - **新批次Check 是切 Lot（690颗/批），不是换盘**，不得用于换盘时间。

## 计算逻辑

- **UPH(实际)** = 产出数 ÷ 统计时长 × 3600。
- **Pure UPH** = 3600 × 每周期产出 ÷ 有效周期（有效周期 = 理想CT/正常周期平均 + 每颗换盘开销；LM 换盘时间平摊到整盘产品）。
- **Derated UPH M2** = 3600 × 每周期产出 ÷ 有效平均周期（剔除离群点）；多模组整机=各模组之和。
- **Derated UPH M1** = EM 投入 ÷ RUN 时长（单模组）；多模组=各模组之和。
- **有效UPH** = 3600 × 每周期产出 ÷（基础周期 + 每颗换盘开销），每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数。
- **CAW 双机台 UPH**（`analyze_bottleneck_machines`，模板 `bottleneck_machines`）：上料机(PLC2) 与 焊接机(PLC1) 各自 单颗CT = 周期中位 ÷ (每周期颗数 × 并行单元数)，取 CT 长者（瓶颈机台）算 UPH = 3600/瓶颈CT。
  - 上料机：放熟料完成 周期中位 10.8s，每周期 2 颗（**每次给 1 个滑台换料**，与焊接机每滑台周期需求对齐），并行 2 取料轴 → 单颗CT 2.71s，UPH≈1330/hr。
  - 焊接机：去交换位 周期中位 23.05s（按 8 工位分单元测，避免并行交换突发），每周期 2 颗（每滑台左右 2 工位各 1 颗），并行 4（**左右 2 侧 × 每侧 2 滑台**）→ 单颗CT 2.88s → **瓶颈=焊接机，UPH≈1249/hr（整机；单边≈625）**。
  - 机台配置：`module.file` 文件名匹配（CAW PLC 文件平铺）、`unit_pattern` 按子单元测周期（正则捕获组）、`parallel_units` 并行单元数。
  - 一键分析修复：CAW UPH Excel 带 Summary/AMESummary/CycleDetail(两机台周期明细+正常/异常/计划分类)/步骤分析/EMProduction 五张表；合并分析按 `merge_groups` 分组导出 LogAnalysis_PLC1焊接机/PLC2上料机/其他.xlsx（模板级 `merge_groups` 配置）。
- **EFF** = 操作时间(运行+待机) ÷ 计划生产时间；停机按 ReasonID 拆 pDT/uDT。
- **每盘颗数**：按 Tray ID（carrierId/CubeTrayId）动态分段统计，不写死；同一盘号跨小时复用按间隔切段（run_gap=300s）。
- **换盘时间**：SA 式「同工位 卸载→下一次装载」间隔中位数（`measure_tray_change`，O(n log n) 二分）。
- **状态推导**：活动关键词→RUN；停机关键词（AutoRun Stop/ErrOn/生产流程出现异常）按 EReason 清单归类 DOWN/IDLE；纯时间日志按文件名补日期（`_row_date`），防止混排成 100+ 年时长。
- **单颗循环步骤分析**（`analyze_steps`，输出到 UPH_Analysis.xlsx 的「步骤分析」sheet）：
  - 模板 `step_analysis` 配置：`units[{name, module(from_path/pattern), cycle, steps[{name, start?, end?, timeout_seconds?}]}]` + `coefficient`（默认 1.5）。
  - start+end=事件对时长；仅 end=顺序切分（本步完成−上一步完成）。
  - `standalone: true`：事件对模式下独立计时，但完成事件**不参与链式切分**——用于每盘一次的 Tray 级动作（LM 读码/CCD），避免把 Tray 事件混进单颗循环段边界（曾导致 LM CCD取像解析被抓成 1.8s 伪段）。
  - 异常 = 时长 > 中位×系数，或（配 timeout_seconds 时）> 中位+超时秒；**中位时长 < 0.01 秒的动作直接忽略**（信号抖动，如 CCD定位 2ms）；**时长 > 计划性停机阈值（默认 900s，可用模板 max_step_seconds 覆盖）视为超长停机，从步骤统计与异常中剔除**（FR 42 分钟停机不再计入点胶异常）。
  - 指标：循环数/中位/平均/P90/最长时长、异常次数、异常影响时长（超额时长）、异常时间占比、异常频率（次/小时）。
  - **时间输出统一约定**（Excel/PPT 全部生效，`fmt_duration`，旧名 `fmt_hms` 兼容）：**低于 60 秒按秒显示**（整数秒显示整数，小数最多 3 位去尾零，如 0.05 / 1.3 / 45），**超过 60 秒按 h:mm:ss(.mmm) 显示**（如 12:02:32）；PPT 表格对列名含 秒/时长 的列格式化展示，图表仍用原始数值；Excel 带 (秒) 单位的数据列（CycleSeconds/总时长(秒)/单颗CT(秒) 等）保持数值供计算与图表。
  - 已配置制程：LM（单颗循环按运动节拍拆分：打标前间隔+Z轴焦距定位+激光打标(振镜扫描)，段和≈CT；批次级 读码GetSN/CCD轴移动定位 每批6颗 standalone；盘级 平台下料/上料 每盘24颗 standalone）、FR（左/右轴点胶=整循环，日志秒级精度无法细分）、SA（4工位行周期 + 左右点胶头内部动作 视觉对位/探针对位/点胶轮廓）、ACF（上料/主机/下料）、CAW（取料1(工位4)/取料2(工位7)：取料=取熟料完成,双取生料完成 → 扫码完成 → 放料完成）。
  - CAW 按机台结构单独配置：**上料机（PLC2）** 取料1/取料2 左右取料轴（各 2 生料+2 熟料吸嘴），步骤=取生料→扫码→取熟料→放生料→放熟料（循环=放熟料完成）；**焊接机（PLC1）** 支架流程=chassis（滑台1-4，步骤=请求上生料→中转去上料位→装载完成→中转去焊接位，循环=中转去焊接位）+ 焊接流程（滑台1-4×左/右 8 工位，步骤=PR1纠偏→纠偏→贴合→判定PR3→焊接→检查PR6→压合回零→交换，循环=去交换位）。
  - 两个关键实现点：① 并行工位/多吸嘴（CAW X1&X2）事件会交叉，步骤段必须按**时间排序切分**而非配置顺序（否则负时长）；② 关键词匹配用与 UPH 一致的**词边界**（`_match_kws`，MarkEnd1 不误命中 MarkEnd1_0）。
- ③ 同一步骤 50ms 内连续事件合并为一次（`merge_gap=0.05`）：ACF 下料機 4 吸嘴并行事件间隔仅 1ms，不合并会把中位算成 0.02s 刷出 99% 假异常、或 <0.01s 被忽略。
  - ④ 配置了 `timeout_seconds` 的步骤以 **中位+超时** 为唯一异常判定（不叠加 1.5× 系数）：亚秒步骤（CAW 贴合 30ms、LM CCD定位 2ms）用系数会刷假异常。
  - ⑤ LM CCD/读码为**批次级动作**（每批 6 颗、每盘 4 批），`standalone` 独立计时；每盘颗数由日志自动统计（`detect_units_per_tray`：CCD 间 MarkEnd1 众数 × 换盘间 CCD 批次数众数），换盘时间（`Move to unload`→`收到上料完成信号`，中位 15.46s）平摊到 24 颗 → 每颗开销 0.644s，Pure UPH 2183→1570。
  - **SA 走独立逻辑** `analyze_steps_sa`（模板 `step_analysis.mode="sa"`）：复用四工位每排周期（点胶/贴附/热压/检测，检测 k 自动估算），**不重叠分块**（每 k 个事件一排，滑动窗口会把一排算成多个重叠样本）；输出格式与通用一致。另按 Sequence 名（SeqCycle003_Left/SeqCycle005_Right）拆左右点胶头内部动作：视觉对位(DispOneChipAlignVisionCycle)→探针对位(DispOneChipProbeAlignCycle)→点胶轮廓(DispOneChipProfileWorkCycle)，B 模式段和≈该头行周期（左头≈13.4s、右头≈19.3s，右头是点胶工位潜在瓶颈；整机点胶 9.96s/排为双头交替吞吐口径）。
  - UI：UPH 参数页「步骤异常系数」（默认 1.5，可调）。

## 步骤时间 vs CT 一致性校验（2026-08-07）

- 校验口径：每个单元用**自己的周期事件**测 CT（周期中位），与步骤中位时长之和对比；B 模式链式切分下逐周期「段和=周期长」恒成立。
- **LM**：旧 B 模式把每盘一次的读码/CCD 混进单颗循环，CCD取像解析伪段 1.8s、步骤和 3.36s vs CT 1.39s。已改为按轴/平台运动节拍拆分：单颗循环 = 打标前间隔(B:MarkEnd1→MarkStart1, 50ms)+Z轴焦距定位(A:MarkStart1→MarkStart1_0, 16ms)+激光打标(A:MarkStart1_0→MarkEnd1_0, 1.321s)，段和 1.387s vs CT 1.393s ✓；批次级 standalone：读码GetSN(每批6颗, 0.128s)/CCD轴移动定位(每批6颗, 0.972s)；盘级 standalone：平台下料(每盘24颗, 5.71s)/平台上料(每盘24颗, 4.59s)。
- **FR**：左/右轴点胶 3.00s = CT ✓；日志仅秒级精度，循环内子动作同秒无法细分，步骤=整循环（修正前 开始点胶 为批次事件仅 1522 次/天，现按每颗 1.3 万+ 次）。
- **SA**：四工位并行，步骤和本身无意义；各工位每排周期 ≈ 排 CT（热压 11.06s=行 CT）。
- **CAW 上料机**：取料1 11.29 vs CT 10.72（+5.3%）、取料2 10.53 vs CT 12.10（-13%）；差异主因 ① 扫码完成为可选事件（约一半周期不扫码）、② 停机周期拉偏 CT。
- **CAW 焊接机**：逐周期段和=周期长（滑台1 181/181、支架 189/189 验证通过），但步骤和中位 19~20s vs CT 21.4~25.3s（-8%~-26%）；原因 ① 停机/异常周期（p75 达 51s）拉偏 CT 中位，② 滑台3/4 约 35% 周期为“短循环”（下熟料/上生料/PR1 后回安全位，无贴合/焊接/压合事件，疑似空料或 NG 循环），这些短循环也计入去交换位 CT 但无完整步骤。步骤抓取本身结构完整，如需步骤和严格=CT 需先统一“有效周期”口径（如仅统计含全部步骤事件的周期）。

## 界面（Apple 风格，views/main_window.py）

- QSS 卡片式：背景 #F5F5F7、卡片白、主色 #007AFF；间距常量 GAP_SECTION/ROW/INNER/CARD_PAD 已压缩。
- 窗口尺寸按屏幕可用区域 **80%** 动态计算（`window_target_size`，最小 900×620），启动画面同尺寸；main.py 在 QApplication 前启用 `AA_EnableHighDpiScaling`（Windows 高分屏字体清晰的关键）。
- 布局要点：配置卡 2×2（制程模板+制程名称 / 功能选择+日志文件筛选）；参数卡 min-height 260（UPH 页 6 行表单完整显示）；结果卡撑满剩余空间（`_card` 内容必须 `addLayout(...,1)`）。
- 「使用说明」按钮在右上角（views/user_guide.py 内容），版权在状态栏右下角 `Copyright©️2026 ABU NPD EOL`。
- 启动画面（main.py）：与主窗口同尺寸（cover 裁切填满）、淡出过渡（FADE_MS=300）衔接主窗口；图片 Machine.png。

## 测试

- `venv/bin/python -m unittest discover -s tests`，73 个用例全绿。

## 合并分析异常标红

- `process(abnormal_keywords=...)` 写入后把命中行整行标浅红（`_highlight_abnormal_rows`，FFC7CE）。
- 控制器从模板报警关键词 + 停机标记（AutoRun Stop / ErrOn / 生产流程出现异常 / status:DOWN / 机械手不安全 / 换盘提示 / 超时等）构建，并**剔除 NG**（产品码常含 NG，如 RDA620700NG55423C 会误标）。
- 标红对**所有制程、所有输出路径生效**：普通合并 LogAnalysis.xlsx、按分组（merge_groups）、大日志 per-file（LogAnalysis_Files，含流式写入路径）。
- UPH 步骤超时标红：`analyze_steps`/`analyze_steps_sa` 把异常步骤的触发行内容存入 `df.attrs['anomaly_lines']`（注意：该集合须在单元循环外初始化，否则只剩最后一个单元）；合并 feature 先跑一次步骤分析，写入后按行内容精确标红（`_highlight_step_lines`）。CAW 实测：焊接机 1851 行 + 上料机 411 行步骤超时标红。

## 步骤甘特图（Excel「步骤甘特图」sheet，2026-08-08）

- 方案：每行一个步骤、每列一个时间块（默认 0.1s/列，数据超 120 列自动放大到 0.2/0.5/1/2/5/10…），颜色填充列数 = 步骤时长，直观看出步骤先后与并行（同一时间区间的多行并排）。
- 数据：`build_gantt_rows`（通用 units，逐周期计算每步相对周期起点的中位起止偏移；B 模式=链式段、A 模式=start/end、standalone 独立绘制）与 `build_gantt_rows_sa`（四工位行周期轨道 0→中位 + 左右点胶头三段 视觉对位→探针对位→点胶轮廓）。
- 绘制：`LogModel._format_gantt_sheet`（openpyxl 块填充），层级颜色 循环=浅蓝 DDEBF7 / 批次=浅橙 FCE4D6 / 盘=浅绿 E2EFDA，时间块列宽 2.5、冻结 F2；UPH_Analysis.xlsx 新增 sheet，各制程（LM/FR/CAW/ACF 通用、SA 专用）自动生成。
- PPT 报告新增「瓶颈工序甘特图」页：`_gantt_page_rows` 从 UPH Excel 筛选瓶颈工序（CAW 瓶颈机台=焊接机时按滑台周期排序取表现居中的滑台左右工位；SA 瓶颈工位截四工位并行全图；其余制程截整机），`_gantt_png` 用 PIL 渲染 PNG 后插入（中文字体自动查找苹方/微软雅黑；临时 PNG 用完即删）。甘特 sheet 时间块刻度从 G 列起（F 列保留“层级”表头）。
- 已验证：SA（analyze_steps_sa 模式）530 行步骤超时标红；ACF（4.8M 行 per-file 路径）上料機每时文件约 320 行标红。ACF 全量合并+标红约 6-7 分钟（480 万行 openpyxl 逐行检查），属正常开销。
- 注意：环境需装 pptx / xlsxwriter / PyQt5，否则相关用例报错（不是代码问题）。

## 已知问题 / 待办

- 主機 UPH 依赖完整主機日志（当前样本仅 ~5 分钟），数据补齐后数字才稳定。
- 上料機/下料機/主機 三者日志覆盖时长不一致时，UPH 对比注意口径。
- PPT 报告的 EFF/状态页依赖 EFF/状态分析结果（ACF 已配活动+停机关键词）。
- PPT 的 UPH 页支持机台瓶颈模式（AMESummary 含「瓶颈机台」列时）：副标题=瓶颈机台+单颗CT+整机UPH，柱状图=各机台单颗CT（CAW 用；SA 工位模式、通用模式照旧）。

## 性能优化（2026-08-08，LM UPH 600s+ → 38s）

- 根因：① `_iter_monotonic` 对 42 万行日志逐行调用 `datetime.timestamp()`（本地时区转换，77s/次扫描），且一键分析里被多次调用；② `analyze_steps`/`build_gantt_rows` 周期循环对每周期线性扫描全部步骤事件（O(周期×事件)，LM 2.8 万×2.8 万）；③ `_match_kws` 每次调用重复编译正则。
- 修复：① `calendar.timegm(t.utctimetuple())` 替代 timestamp()（统一 UTC，差值不变，微秒级）；② 周期循环改用 bisect 二分定位区间事件；③ `parse_ts`/关键词正则 lru_cache；周期循环每 500 次检查 cancel_event。
- 效果：analyze_steps 84.5→13.6s、build_gantt_rows 84→11s、换盘测量 153→2.5s；LM 全量 UPH 339→38s；FR 28s/CAW 2.4s/SA 0.2s/ACF 2.7s 冒烟通过。

## 最近的提交

- `5a96a21 assets: 更新启动画面图片`
- `a4e7ab9 ui: 启动画面淡出过渡，与主窗口平滑衔接`
- `03ccafa ui: 启动画面尺寸与主窗口一致`
- `fcf4772 build: 打包改用 onedir 模式`
- `5321ae2 feat: ACF 三機完整支持 + 一键分析质量修复 + Apple 风格 UI 优化`
