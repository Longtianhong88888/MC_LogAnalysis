"""PPT 报告生成：读取一键分析产出的 4 个 Excel，生成包含各分析汇总与图表的报告。"""

import os
from datetime import datetime

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from utils.resource_utils import resource_path

HEADER_FILL = RGBColor(0xDD, 0xEB, 0xF7)
GRAY = RGBColor(0x60, 0x60, 0x60)
TABLE_BORDER = RGBColor(0xBF, 0xBF, 0xBF)
CHART_LEFT, CHART_TOP, CHART_W, CHART_H = 0.6, 1.6, 6.6, 5.2
TABLE_LEFT, TABLE_W = 7.4, 5.3
_TITLE_PREFIX = {
    "LM 激光打标": "LM",
    "CAW 组装": "CAW",
    "FR 机台": "FR",
}


def _read_sheet(path, name):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        xl = pd.ExcelFile(path)
        if name in xl.sheet_names:
            return xl.parse(name)
    except Exception:
        pass
    return pd.DataFrame()


def _to_float(value):
    try:
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _content_layout(prs):
    for layout in prs.slide_layouts:
        if "content" in layout.name.lower():
            return layout
    return prs.slide_layouts[0] if prs.slide_layouts else None


def _clean_placeholders(slide):
    """删除内容页上空白的 body/clipart 占位符（保留标题、页脚、页码），避免与图表/表格重叠。"""
    for shape in list(slide.shapes):
        if not shape.is_placeholder:
            continue
        idx = shape.placeholder_format.idx
        if idx == 0 or idx in (3, 4):  # 标题、页脚、页码
            continue
        sp = shape._element
        sp.getparent().remove(sp)


def _add_slide(prs, title, subtitle=""):
    slide = prs.slides.add_slide(_content_layout(prs))
    _clean_placeholders(slide)
    if slide.shapes.title is not None:
        slide.shapes.title.text = title
    else:
        box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.8))
        box.text_frame.text = title
        box.text_frame.paragraphs[0].font.size = Pt(26)
        box.text_frame.paragraphs[0].font.bold = True
    if subtitle:
        box2 = slide.shapes.add_textbox(Inches(0.5), Inches(1.18), Inches(12.3), Inches(0.32))
        tf2 = box2.text_frame
        tf2.text = subtitle
        tf2.paragraphs[0].font.size = Pt(13)
        tf2.paragraphs[0].font.color.rgb = GRAY
    return slide


def _add_table(slide, df, left, top, width, height, max_rows=12):
    data = df.head(max_rows)
    rows, cols = data.shape
    if rows == 0 or cols == 0:
        return
    # 高度按行数自适应，避免行数少时出现超大空行
    total_h = min(height, 0.42 + (rows + 1) * 0.30)
    graphic = slide.shapes.add_table(
        rows + 1, cols, Inches(left), Inches(top), Inches(width), Inches(total_h)
    )
    table = graphic.table
    # 列宽按内容长度比例分配（中文按 2 字符宽计），并归一化到总宽
    lens = []
    for j, col in enumerate(data.columns):
        m = sum(2 if ord(ch) > 127 else 1 for ch in str(col))
        for value in data[col]:
            s = "" if pd.isna(value) else str(value)
            m = max(m, sum(2 if ord(ch) > 127 else 1 for ch in s))
        lens.append(max(m, 5))
    total_len = sum(lens)
    raw_widths = [max(width * ln / total_len, 0.6) for ln in lens]
    scale = width / sum(raw_widths)
    for j in range(cols):
        table.columns[j].width = Inches(raw_widths[j] * scale)
    table.rows[0].height = Inches(0.38)
    for i in range(1, rows + 1):
        table.rows[i].height = Inches(0.30)
    for j, col in enumerate(data.columns):
        cell = table.cell(0, j)
        cell.text = str(col)
        cell.fill.solid()
        cell.fill.fore_color.rgb = HEADER_FILL
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.size = Pt(10)
        cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, (_, row) in enumerate(data.iterrows(), start=1):
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.text = "" if pd.isna(value) else str(value)
            cell.text_frame.paragraphs[0].font.size = Pt(10)
            cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    return table


def _add_chart(slide, chart_type, title, categories, values,
               left=CHART_LEFT, top=CHART_TOP, width=CHART_W, height=CHART_H, legend=False):
    chart_data = CategoryChartData()
    chart_data.categories = list(categories)
    chart_data.add_series("数值", [0 if v is None else v for v in values])
    chart = slide.shapes.add_chart(
        chart_type, Inches(left), Inches(top), Inches(width), Inches(height), chart_data
    ).chart
    chart.has_legend = legend
    chart.has_title = True
    chart.chart_title.text_frame.text = title
    chart.chart_title.text_frame.paragraphs[0].font.size = Pt(13)
    return chart


def _metrics_table(df):
    """单行指标表转置为 指标/数值 两列。"""
    if df is None or df.empty:
        return pd.DataFrame()
    row = df.iloc[0]
    return pd.DataFrame({"指标": row.index, "数值": row.values})


def _report_title(process_name):
    """按制程生成报告标题，如 'LM設備一鍵自動分析報告'；未知制程用通用标题。"""
    prefix = _TITLE_PREFIX.get(process_name)
    if prefix:
        return f"{prefix}設備一鍵自動分析報告"
    return "MC Log 分析报告"


def _fill_template_cover(prs, process_name):
    """把模板封面标题中的制程占位 'XX' 替换为制程字母（LM/CAW/FR），其余内容与样式保持不变。"""
    if not prs.slides:
        return
    prefix = _TITLE_PREFIX.get(process_name)
    if prefix is None:
        return
    cover = prs.slides[0]
    for shape in cover.shapes:
        if not shape.has_text_frame:
            continue
        tf = shape.text_frame
        if "XX" not in tf.text:
            continue
        for paragraph in tf.paragraphs:
            for run in paragraph.runs:
                if "XX" in run.text:
                    run.text = run.text.replace("XX", prefix)
        return


def build_ppt_report(output_dir, process_name=None, report_name="Analysis_Report.pptx"):
    """读取 output_dir 下 4 个分析 Excel，基于根目录 PPT模板.pptx 生成报告，返回报告路径。"""
    out_path = os.path.join(output_dir, report_name)
    template = resource_path("PPT模板.pptx")
    template = template if os.path.exists(template) else None
    prs = Presentation(template) if template else Presentation()
    if template:
        _fill_template_cover(prs, process_name)
    else:
        title = _report_title(process_name)
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        # ---------- 标题页（无模板时） ----------
        slide = _add_slide(prs, title, "UPH / EFF / 报警 / 机台状态")
        box = slide.shapes.add_textbox(Inches(0.4), Inches(3.2), Inches(9.2), Inches(0.5))
        box.text_frame.text = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        box.text_frame.paragraphs[0].font.size = Pt(14)
        box.text_frame.paragraphs[0].font.color.rgb = GRAY

    # ---------- UPH 分析 ----------
    ame = _read_sheet(os.path.join(output_dir, "UPH_Analysis.xlsx"), "AMESummary")
    if not ame.empty:
        slide = _add_slide(prs, "UPH 分析", "CoreTech AME：Pure UPH / Derated UPH M1 / M2")
        labels = ["Pure UPH(个/小时)", "Derated UPH M1(个/小时)", "Derated UPH M2(个/小时)"]
        vals = [_to_float(ame.iloc[0].get(c)) for c in labels]
        _add_chart(slide, XL_CHART_TYPE.COLUMN_CLUSTERED, "UPH 对比", labels, vals)
        _add_table(slide, _metrics_table(ame), left=TABLE_LEFT, top=CHART_TOP, width=TABLE_W, height=CHART_H)

    # ---------- EFF 分析 ----------
    eff = _read_sheet(os.path.join(output_dir, "EFF_Analysis.xlsx"), "Summary")
    if not eff.empty:
        slide = _add_slide(prs, "EFF 分析", "EFF = 操作时间(运行+待机) / 计划生产时间")
        row = eff.iloc[0]
        cats = ["运行RUN", "待机IDLE", "停机DOWN"]
        vals = [_to_float(row.get(c)) for c in ("运行时间RUN(秒)", "待机时间IDLE(秒)", "停机时间DOWN(秒)")]
        _add_chart(slide, XL_CHART_TYPE.PIE, "时间构成（秒）", cats, vals, legend=True)
        _add_table(slide, _metrics_table(eff), left=TABLE_LEFT, top=CHART_TOP, width=TABLE_W, height=CHART_H)

        pareto = _read_sheet(os.path.join(output_dir, "EFF_Analysis.xlsx"), "DOWN_Pareto")
        if not pareto.empty:
            slide = _add_slide(prs, "停机 Pareto", "按 ReasonID 统计停机时长 Top10")
            top = pareto.head(10)
            _add_chart(slide, XL_CHART_TYPE.BAR_CLUSTERED, "停机时长（秒）", top["ReasonID"], top["总时长(秒)"])
            _add_table(slide, top, left=TABLE_LEFT, top=CHART_TOP, width=TABLE_W, height=CHART_H)

    # ---------- 报警分析 ----------
    by_kw = _read_sheet(os.path.join(output_dir, "Alarm_Analysis.xlsx"), "ByKeyword")
    alarm_summary = _read_sheet(os.path.join(output_dir, "Alarm_Analysis.xlsx"), "Summary")
    if not by_kw.empty or not alarm_summary.empty:
        slide = _add_slide(prs, "报警分析", "按关键词与模块统计报警")
        if not by_kw.empty:
            top = by_kw.head(10)
            _add_chart(slide, XL_CHART_TYPE.COLUMN_CLUSTERED, "报警次数 Top10", top["命中关键词"], top["报警次数"])
            _add_table(slide, top, left=TABLE_LEFT, top=CHART_TOP, width=TABLE_W, height=CHART_H)
        elif not alarm_summary.empty:
            _add_table(slide, alarm_summary, left=CHART_LEFT, top=CHART_TOP, width=12.1, height=CHART_H)

    # ---------- 机台状态 ----------
    status = _read_sheet(os.path.join(output_dir, "Status_Analysis.xlsx"), "Summary")
    if not status.empty:
        slide = _add_slide(prs, "机台状态汇总", "RUN / IDLE / DOWN / WARN 时长与占比")
        cats = list(status["状态"])
        vals = [_to_float(v) for v in status["总时长(秒)"]]
        _add_chart(slide, XL_CHART_TYPE.PIE, "状态时长（秒）", cats, vals, legend=True)
        _add_table(slide, status, left=TABLE_LEFT, top=CHART_TOP, width=TABLE_W, height=CHART_H)

        hourly = _read_sheet(os.path.join(output_dir, "Status_Analysis.xlsx"), "Hourly")
        if not hourly.empty and "EFF(%)" in hourly.columns:
            slide = _add_slide(prs, "机台状态趋势", "每小时 EFF 趋势")
            _add_chart(slide, XL_CHART_TYPE.LINE_MARKERS, "每小时 EFF(%)",
                       hourly["小时"], hourly["EFF(%)"],
                       left=CHART_LEFT, top=CHART_TOP, width=12.1, height=CHART_H)

    prs.save(out_path)
    return out_path
