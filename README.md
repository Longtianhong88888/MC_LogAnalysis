# MC Log Analysis Tool

机台日志批量解析工具（PyQt5 界面）：选择源文件夹后，读取其中的 `.log` / `.txt` 文件（自动识别编码），按关键词筛选，可选按分隔符把每一行拆成多列，最后导出为 Excel。

## 功能

- 制程模板：选择制程（LM 激光打标 / CAW 组装）自动配置参数与日志文件范围；内置"自定义"模板可保存/加载自己的配置
- 自动检测文件编码（chardet，UTF-8 / GBK / Latin-1 等回退）
- 五种分析模式（顶部“功能选择”切换）：
  1. **文档合并与内容拆分**：关键词筛选 + 按分隔符拆分为多列，导出 `LogAnalysis.xlsx`
  2. **UPH 分析**：按 CoreTech AME 定义输出 Pure UPH（3600×产出/理想周期CT）、Derated UPH M1（投入/运行时间）与 M2（剔除离群周期），导出 `UPH_Analysis.xlsx`
  3. **EFF 分析**：按 CoreTech AME 定义 EFF = 操作时间(运行+待机) / 计划生产时间，基于 RUN/IDLE/DOWN 状态计算，可拆分为 pDT/uDT，导出 `EFF_Analysis.xlsx`
  4. **报警分析**：统计报警关键词命中记录（按模块、按关键词汇总），导出 `Alarm_Analysis.xlsx`
  5. **机台状态分析**：识别 `status:RUN / IDLE / DOWN` 状态行，统计各状态时长与占比，导出 `Status_Analysis.xlsx`
  6. **一键分析（全部）**：按当前制程模板依次运行 UPH/EFF/报警/机台状态四项，分别导出 4 个 Excel
- 解析在后台线程执行，界面不卡顿，带进度条
- 启动画面（`Machine.png`）与应用图标（`log.ico`）

## 环境与运行

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 使用步骤

1. 选择源文件夹（递归扫描其中的 `.log` / `.txt` 文件）
2. 选择输出文件夹
3. 选择制程模板（通用/自定义/LM 激光打标/CAW 组装），参数自动预填
4. 选择分析功能（或"一键分析（全部）"）
5. 点击“开始解析”，完成后结果写入输出文件夹

## 打包 Windows exe

```bash
pyinstaller --onefile --windowed --icon log.ico --add-data "Machine.png;." --add-data "log.ico;." --name MC_LogAnalysis main.py
```

也可以推送 `main` / `master` 分支，由 GitHub Actions 自动构建（见 `.github/workflows/build.yml`）。

## 项目结构

```
app.py                          # 应用组装（控制器 + 主窗口）
main.py                         # 启动入口
controllers/log_controller.py   # 界面事件、后台线程调度
models/log_model.py             # 核心解析逻辑（筛选、拆分、导出）
models/analysis.py              # UPH/EFF/报警/机台状态分析
utils/file_utils.py             # 文件读取、编码检测、Excel 字符清理
utils/resource_utils.py         # 资源路径解析（兼容 PyInstaller 打包）
views/main_window.py            # PyQt5 主界面
tests/                          # 单元测试
```

## 说明与限制

- 关键词为空且填写了分隔符时，`Filtered` 表会对全部日志做拆分
- 多次解析会覆盖同名输出文件，如需保留历史请自行改名
