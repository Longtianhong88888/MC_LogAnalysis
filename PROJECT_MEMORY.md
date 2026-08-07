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
- **Pure UPH** = 3600 × 每周期产出 ÷ 理想CT（未填时用正常周期平均）。
- **Derated UPH M2** = 3600 × 每周期产出 ÷ 有效平均周期（剔除离群点）；多模组整机=各模组之和。
- **Derated UPH M1** = EM 投入 ÷ RUN 时长（单模组）；多模组=各模组之和。
- **有效UPH** = 3600 × 每周期产出 ÷（基础周期 + 每颗换盘开销），每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数。
- **CAW 双机台 UPH**（`analyze_bottleneck_machines`，模板 `bottleneck_machines`）：上料机(PLC2) 与 焊接机(PLC1) 各自 单颗CT = 周期中位 ÷ (每周期颗数 × 并行单元数)，取 CT 长者（瓶颈机台）算 UPH = 3600/瓶颈CT。
  - 上料机：放熟料完成 周期中位 10.8s，每周期 4 颗（2生+2熟），并行 2 取料轴 → 单颗CT 1.35s。
  - 焊接机：去交换位 周期中位 23.05s（按 8 工位分单元测，避免并行交换突发），每周期 2 颗，并行 4（左右 2 侧 × 2 焊接头）→ 单颗CT 2.88s → **瓶颈=焊接机，UPH≈1249/hr（整机；单边≈625）**。
  - 机台配置：`module.file` 文件名匹配（CAW PLC 文件平铺）、`unit_pattern` 按子单元测周期（正则捕获组）、`parallel_units` 并行单元数。
- **EFF** = 操作时间(运行+待机) ÷ 计划生产时间；停机按 ReasonID 拆 pDT/uDT。
- **每盘颗数**：按 Tray ID（carrierId/CubeTrayId）动态分段统计，不写死；同一盘号跨小时复用按间隔切段（run_gap=300s）。
- **换盘时间**：SA 式「同工位 卸载→下一次装载」间隔中位数（`measure_tray_change`，O(n log n) 二分）。
- **状态推导**：活动关键词→RUN；停机关键词（AutoRun Stop/ErrOn/生产流程出现异常）按 EReason 清单归类 DOWN/IDLE；纯时间日志按文件名补日期（`_row_date`），防止混排成 100+ 年时长。
- **单颗循环步骤分析**（`analyze_steps`，输出到 UPH_Analysis.xlsx 的「步骤分析」sheet）：
  - 模板 `step_analysis` 配置：`units[{name, module(from_path/pattern), cycle, steps[{name, start?, end?, timeout_seconds?}]}]` + `coefficient`（默认 1.5）。
  - start+end=事件对时长；仅 end=顺序切分（本步完成−上一步完成）。
  - 异常 = 时长 > 中位×系数，或（配 timeout_seconds 时）> 中位+超时秒；**中位时长 < 0.01 秒的动作直接忽略**（信号抖动，如 CCD定位 2ms）；**时长 > 计划性停机阈值（默认 900s，可用模板 max_step_seconds 覆盖）视为超长停机，从步骤统计与异常中剔除**（FR 42 分钟停机不再计入点胶异常）。
  - 指标：循环数/中位/平均/P90/最长时长、异常次数、异常影响时长（超额时长）、异常时间占比、异常频率（次/小时）；时间统一 h:mm:ss（`fmt_hms`）。
  - 已配置制程：LM（GetSN/CCD取像解析/CCD定位/激光打标）、FR（左/右轴点胶）、SA（点胶/贴附/热压/检测）、ACF（上料/主机/下料）、CAW（取料1(工位4)/取料2(工位7)：取料=取熟料完成,双取生料完成 → 扫码完成 → 放料完成）。
  - CAW 按机台结构单独配置：**上料机（PLC2）** 取料1/取料2 左右取料轴（各 2 生料+2 熟料吸嘴），步骤=取生料→扫码→取熟料→放生料→放熟料（循环=放熟料完成）；**焊接机（PLC1）** 支架流程=chassis（滑台1-4，步骤=请求上生料→中转去上料位→装载完成→中转去焊接位，循环=中转去焊接位）+ 焊接流程（滑台1-4×左/右 8 工位，步骤=PR1纠偏→纠偏→贴合→判定PR3→焊接→检查PR6→压合回零→交换，循环=去交换位）。
  - 两个关键实现点：① 并行工位/多吸嘴（CAW X1&X2）事件会交叉，步骤段必须按**时间排序切分**而非配置顺序（否则负时长）；② 关键词匹配用与 UPH 一致的**词边界**（`_match_kws`，MarkEnd1 不误命中 MarkEnd1_0）。
  - ③ 同一步骤 50ms 内连续事件合并为一次（`merge_gap=0.05`）：ACF 下料機 4 吸嘴并行事件间隔仅 1ms，不合并会把中位算成 0.02s 刷出 99% 假异常、或 <0.01s 被忽略。
  - ④ 配置了 `timeout_seconds` 的步骤以 **中位+超时** 为唯一异常判定（不叠加 1.5× 系数）：亚秒步骤（CAW 贴合 30ms、LM CCD定位 2ms）用系数会刷假异常。
  - **SA 走独立逻辑** `analyze_steps_sa`（模板 `step_analysis.mode="sa"`）：复用四工位每排周期（点胶/贴附/热压/检测，检测 k 自动估算），**不重叠分块**（每 k 个事件一排，滑动窗口会把一排算成多个重叠样本）；输出格式与通用一致。
  - UI：UPH 参数页「步骤异常系数」（默认 1.5，可调）。

## 界面（Apple 风格，views/main_window.py）

- QSS 卡片式：背景 #F5F5F7、卡片白、主色 #007AFF；间距常量 GAP_SECTION/ROW/INNER/CARD_PAD 已压缩。
- 窗口尺寸按屏幕可用区域 **80%** 动态计算（`window_target_size`，最小 900×620），启动画面同尺寸；main.py 在 QApplication 前启用 `AA_EnableHighDpiScaling`（Windows 高分屏字体清晰的关键）。
- 布局要点：配置卡 2×2（制程模板+制程名称 / 功能选择+日志文件筛选）；参数卡 min-height 260（UPH 页 6 行表单完整显示）；结果卡撑满剩余空间（`_card` 内容必须 `addLayout(...,1)`）。
- 「使用说明」按钮在右上角（views/user_guide.py 内容），版权在状态栏右下角 `Copyright©️2026 ABU NPD EOL`。
- 启动画面（main.py）：与主窗口同尺寸（cover 裁切填满）、淡出过渡（FADE_MS=300）衔接主窗口；图片 Machine.png。

## 测试

- `venv/bin/python -m unittest discover -s tests`，59 个用例全绿。
- 注意：环境需装 pptx / xlsxwriter / PyQt5，否则相关用例报错（不是代码问题）。

## 已知问题 / 待办

- 主機 UPH 依赖完整主機日志（当前样本仅 ~5 分钟），数据补齐后数字才稳定。
- 上料機/下料機/主機 三者日志覆盖时长不一致时，UPH 对比注意口径。
- PPT 报告的 EFF/状态页依赖 EFF/状态分析结果（ACF 已配活动+停机关键词）。

## 最近的提交

- `5a96a21 assets: 更新启动画面图片`
- `a4e7ab9 ui: 启动画面淡出过渡，与主窗口平滑衔接`
- `03ccafa ui: 启动画面尺寸与主窗口一致`
- `fcf4772 build: 打包改用 onedir 模式`
- `5321ae2 feat: ACF 三機完整支持 + 一键分析质量修复 + Apple 风格 UI 优化`
