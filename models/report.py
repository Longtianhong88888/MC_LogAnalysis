"""PPT 报告生成：读取一键分析产出的 4 个 Excel，基于最终模板 Analysis_Report.pptx 生成报告。

模板封面保留并替换制程字母；内容页原位复用（更新副标题/图表/表格），
页码按 '1 /' + 总页数（封面）与 'n/总页数'（内容页）同步更新。
"""

import copy
import os
from datetime import datetime

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from utils.resource_utils import find_external_resource

HEADER_FILL = RGBColor(0xDD, 0xEB, 0xF7)
GRAY = RGBColor(0x60, 0x60, 0x60)
CHART_LEFT, CHART_TOP, CHART_W, CHART_H = 0.6, 1.6, 6.6, 5.2
TABLE_LEFT, TABLE_W = 7.4, 5.3
_TITLE_PREFIX = {
    "LM 激光打标": "LM",
    "CAW 组装": "CAW",
    "FR 机台": "FR",
    "SA 机台": "SA",
    "ACF 三機": "ACF",
}
_TEMPLATE_CANDIDATES = ["Analysis_Report.pptx", "PPT模板.pptx"]
SECTION_TITLES = ["UPH 分析", "EFF 分析", "停机 Pareto", "报警分析", "机台状态汇总", "机台状态趋势"]


def _read_sheet(path, name):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        # dtype=str：保留原因码等前导零（如 0010000000），图表取值再转数值
        return pd.read_excel(path, sheet_name=name, dtype=str)
    except Exception:
        return pd.DataFrame()


def _to_float(value):
    try:
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None
        f = float(value)
        if f != f or f in (float('inf'), float('-inf')):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _chart_values(values):
    """图表数值清洗：NaN/Inf/空串统一转 0，避免 python-pptx 写入报错。"""
    out = []
    for value in values:
        try:
            f = float(value)
        except (TypeError, ValueError):
            f = None
        if f is None or f != f or f in (float('inf'), float('-inf')):
            out.append(0)
        else:
            out.append(f)
    return out


def _set_text_preserving(tf, text):
    """替换文本框内容并保留首 run 的样式。"""
    if tf.paragraphs and tf.paragraphs[0].runs:
        tf.paragraphs[0].runs[0].text = str(text)
        for extra in list(tf.paragraphs[0].runs[1:]):
            extra._r.getparent().remove(extra._r)
        for para in list(tf.paragraphs[1:]):
            para._p.getparent().remove(para._p)
    else:
        tf.text = str(text)


def _content_layout(prs):
    for layout in prs.slide_layouts:
        if "content" in layout.name.lower():
            return layout
    return prs.slide_layouts[0] if prs.slide_layouts else None


def _clean_placeholders(slide):
    """删除内容页上空白的 body/clipart 占位符（保留标题、页脚、页码）。"""
    for shape in list(slide.shapes):
        if not shape.is_placeholder:
            continue
        idx = shape.placeholder_format.idx
        if idx == 0 or idx in (3, 4):
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
    total_h = min(height, 0.42 + (rows + 1) * 0.30)
    graphic = slide.shapes.add_table(
        rows + 1, cols, Inches(left), Inches(top), Inches(width), Inches(total_h)
    )
    table = graphic.table
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
    chart_data.add_series("数值", _chart_values(values))
    chart = slide.shapes.add_chart(
        chart_type, Inches(left), Inches(top), Inches(width), Inches(height), chart_data
    ).chart
    chart.has_legend = legend
    chart.has_title = True
    chart.chart_title.text_frame.text = title
    chart.chart_title.text_frame.paragraphs[0].font.size = Pt(13)
    return chart


def _metrics_table(df):
    if df is None or df.empty:
        return pd.DataFrame()
    row = df.iloc[0]
    return pd.DataFrame({"指标": row.index, "数值": row.values})


def _report_title(process_name):
    prefix = _TITLE_PREFIX.get(process_name)
    if prefix:
        return f"{prefix}設備一鍵自動分析報告"
    return "MC Log 分析报告"


def _fill_template_cover(prs, process_name):
    """替换封面标题中的制程字母（XX/LM/CAW/FR），其余内容与样式保持不变。"""
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
        if "設備一鍵自動分析報告" not in tf.text:
            continue
        if tf.paragraphs and tf.paragraphs[0].runs:
            first = tf.paragraphs[0].runs[0]
            if first.text.replace(" ", "") in ("XX", "LM", "CAW", "FR"):
                first.text = prefix
        return


def _delete_slide(prs, index):
    sld_id_lst = prs.slides._sldIdLst
    slides = list(sld_id_lst)
    sld_id = slides[index]
    r_id = sld_id.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    prs.part.drop_rel(r_id)
    sld_id_lst.remove(sld_id)


def _delete_slide_by_title(prs, title):
    sld_id_lst = prs.slides._sldIdLst
    for idx in range(len(sld_id_lst) - 1, 0, -1):
        slide = prs.slides[idx]
        t = slide.shapes.title
        if t is not None and t.text.strip() == title:
            _delete_slide(prs, idx)
            return


def _prepare_template_pages(prs):
    """保留封面与分节内容页，删除目录页及不属于分节的多余页面。"""
    sld_id_lst = prs.slides._sldIdLst
    slides = list(sld_id_lst)
    for idx in range(len(slides) - 1, 0, -1):
        slide = prs.slides[idx]
        name = slide.slide_layout.name.lower()
        if 'content' not in name and 'agenda' not in name:
            continue
        t = slide.shapes.title
        title = t.text.strip() if t is not None else ''
        if title in SECTION_TITLES:
            continue
        _delete_slide(prs, idx)


def _section_slide(prs, title):
    for slide in prs.slides:
        t = slide.shapes.title
        if t is not None and t.text.strip() == title:
            return slide
    return None


def _set_subtitle(slide, subtitle):
    for shape in slide.shapes:
        if shape.is_placeholder or shape.has_chart or shape.has_table or not shape.has_text_frame:
            continue
        _set_text_preserving(shape.text_frame, subtitle)
        return


def _replace_chart(slide, chart_type, chart_title, categories, values, legend=False):
    for shape in list(slide.shapes):
        if not shape.has_chart:
            continue
        left, top, width, height = shape.left, shape.top, shape.width, shape.height
        shape._element.getparent().remove(shape._element)
        chart_data = CategoryChartData()
        chart_data.categories = list(categories)
        chart_data.add_series("数值", _chart_values(values))
        chart = slide.shapes.add_chart(chart_type, left, top, width, height, chart_data).chart
        chart.has_legend = legend
        chart.has_title = True
        chart.chart_title.text_frame.text = chart_title
        chart.chart_title.text_frame.paragraphs[0].font.size = Pt(13)
        return chart
    return None


def _remove_table(slide):
    """删除页面上的表格（瓶颈模式 PPT 只放最终结果，不展示工位明细）。"""
    for shape in list(slide.shapes):
        if shape.has_table:
            shape._element.getparent().remove(shape._element)


def _update_table(slide, df, max_rows=12):
    data = df.head(max_rows)
    rows, cols = data.shape
    if rows == 0 or cols == 0:
        return
    for shape in slide.shapes:
        if not shape.has_table:
            continue
        table = shape.table
        t_el = table._tbl
        # 列数不足时扩展（模板表可能只有 2 列，而工位明细有多列）
        need_cols = min(cols, 12)
        grid = t_el.find(qn('a:tblGrid'))
        grid_cols = grid.findall(qn('a:gridCol')) if grid is not None else []
        if len(grid_cols) < need_cols:
            for _ in range(need_cols - len(grid_cols)):
                grid.append(copy.deepcopy(grid_cols[-1]))
            for tr in t_el.findall(qn('a:tr')):
                tcs = tr.findall(qn('a:tc'))
                if tcs:
                    for _ in range(need_cols - len(tcs)):
                        tr.append(copy.deepcopy(tcs[-1]))
        trs = t_el.findall(qn('a:tr'))
        need = rows + 1
        if len(trs) < need:
            last_tr = trs[-1]
            for _ in range(need - len(trs)):
                t_el.append(copy.deepcopy(last_tr))
        elif len(trs) > need:
            for tr in trs[need:]:
                t_el.remove(tr)
        n_cols = min(cols, len(table.columns))
        for j in range(n_cols):
            _set_text_preserving(table.cell(0, j).text_frame, str(data.columns[j]))
        for i, (_, row) in enumerate(data.iterrows(), start=1):
            for j in range(n_cols):
                value = '' if pd.isna(row.iloc[j]) else str(row.iloc[j])
                _set_text_preserving(table.cell(i, j).text_frame, value)
        return


def _build_section(prs, title, subtitle, chart_type, chart_title, cats, vals, table_df,
                   table_left=TABLE_LEFT, table_width=TABLE_W, chart_full=False):
    """优先原位更新模板内容页；模板无此页时新建。"""
    slide = _section_slide(prs, title)
    if slide is None:
        slide = _add_slide(prs, title, subtitle)
        if cats is not None and len(cats) > 0:
            _add_chart(slide, chart_type, chart_title, cats, vals,
                       width=(12.1 if chart_full else CHART_W),
                       legend=(chart_type == XL_CHART_TYPE.PIE))
        if not table_df.empty:
            _add_table(slide, table_df, left=table_left, top=CHART_TOP,
                       width=(12.1 if chart_full else table_width), height=CHART_H)
        return
    _set_subtitle(slide, subtitle)
    if cats is not None and len(cats) > 0:
        _replace_chart(slide, chart_type, chart_title, cats, vals,
                       legend=(chart_type == XL_CHART_TYPE.PIE))
    if not table_df.empty:
        _update_table(slide, table_df)


def _update_page_numbers(prs):
    """封面 '1 /' + 总页数；内容页 'n/总页数'（与模板样式一致）。"""
    total = len(prs.slides)
    for i, slide in enumerate(prs.slides, start=1):
        page_holder = page_x = None
        for shape in slide.shapes:
            if not shape.is_placeholder:
                continue
            idx = shape.placeholder_format.idx
            if idx == 4:
                page_holder = shape
            elif idx == 3:
                page_x = shape
        if page_holder is not None:
            _set_text_preserving(page_holder.text_frame, f"{i} /")
        if page_x is not None:
            if page_holder is not None:
                _set_text_preserving(page_x.text_frame, str(total))
            else:
                _set_text_preserving(page_x.text_frame, f"{i}/{total}")
        if page_holder is None and page_x is None:
            tb = slide.shapes.add_textbox(Inches(11.35), Inches(7.08), Inches(1.75), Inches(0.3))
            tf = tb.text_frame
            tf.text = f"{i}/{total}"
            tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
            tf.paragraphs[0].font.size = Pt(10)
            tf.paragraphs[0].font.color.rgb = GRAY


def build_ppt_report(output_dir, process_name=None, report_name="Analysis_Report.pptx"):
    """读取 output_dir 下 4 个分析 Excel，基于最终模板生成报告，返回报告路径。"""
    out_path = os.path.join(output_dir, report_name)
    template = next(
        (p for p in (find_external_resource(name) for name in _TEMPLATE_CANDIDATES) if p),
        None,
    )
    prs = Presentation(template) if template else Presentation()
    if template:
        _fill_template_cover(prs, process_name)
        _prepare_template_pages(prs)
    else:
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        slide = _add_slide(prs, _report_title(process_name), "UPH / EFF / 报警 / 机台状态")
        box = slide.shapes.add_textbox(Inches(0.4), Inches(3.2), Inches(9.2), Inches(0.5))
        box.text_frame.text = f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        box.text_frame.paragraphs[0].font.size = Pt(14)
        box.text_frame.paragraphs[0].font.color.rgb = GRAY

    to_remove = []

    # ---------- UPH 分析 ----------
    ame = _read_sheet(os.path.join(output_dir, "UPH_Analysis.xlsx"), "AMESummary")
    if ame.empty:
        to_remove.append("UPH 分析")
    else:
        uph_summary = _read_sheet(os.path.join(output_dir, "UPH_Analysis.xlsx"), "Summary")
        machine_mode = not ame.empty and "瓶颈机台" in ame.columns
        if machine_mode:
            # CAW 双机台：瓶颈机台 + 单颗CT + 整机 UPH，各机台 CT 用图展示
            b_name = str(ame.iloc[0].get("瓶颈机台") or "")
            b_ct = str(ame.iloc[0].get("瓶颈CT(秒)") or "")
            uph = str(ame.iloc[0].get("UPH(个/小时)") or "")
            subtitle = f"瓶颈机台：{b_name}（单颗CT {b_ct}s）→ UPH ≈ {uph}/h"
            slide = _section_slide(prs, "UPH 分析")
            if slide is None:
                slide = _add_slide(prs, "UPH 分析", subtitle)
            else:
                _set_subtitle(slide, subtitle)
            machine_table = uph_summary.copy()
            if "单颗CT(秒)" in machine_table.columns:
                machine_table["单颗CT(秒)"] = machine_table["单颗CT(秒)"].fillna("")
            _remove_table(slide)
            _replace_chart(slide, XL_CHART_TYPE.COLUMN_CLUSTERED, "各机台单颗CT（秒）",
                           uph_summary["机台"], uph_summary["单颗CT(秒)"])
        elif not uph_summary.empty and "工位" in uph_summary.columns:
            # 多工位机：PPT 只放最终结果——瓶颈工位与 UPH，各工位周期用图展示
            b_name = str(ame.iloc[0].get("瓶颈工位") or "")
            b_time = str(ame.iloc[0].get("瓶颈周期(秒)") or "")
            pure = str(ame.iloc[0].get("Pure UPH(个/小时)") or "")
            subtitle = f"瓶颈工位：{b_name}（{b_time}s/排）→ UPH ≈ {pure}/h"
            slide = _section_slide(prs, "UPH 分析")
            if slide is None:
                slide = _add_slide(prs, "UPH 分析", subtitle)
            else:
                _set_subtitle(slide, subtitle)
            station_table = uph_summary.copy()
            if "瓶颈" in station_table.columns:
                station_table["瓶颈"] = station_table["瓶颈"].fillna("")
            _remove_table(slide)
            _replace_chart(slide, XL_CHART_TYPE.COLUMN_CLUSTERED, "各工位每排周期（秒）",
                           station_table["工位"], station_table["每排周期(秒)"])
        else:
            labels = ["Pure UPH(个/小时)", "Derated UPH M1(个/小时)", "Derated UPH M2(个/小时)"]
            vals = [_to_float(ame.iloc[0].get(c)) for c in labels]
            _build_section(prs, "UPH 分析", "CoreTech AME：Pure UPH / Derated UPH M1 / M2",
                           XL_CHART_TYPE.COLUMN_CLUSTERED, "UPH 对比", labels, vals, _metrics_table(ame))

    # ---------- EFF 分析 ----------
    eff = _read_sheet(os.path.join(output_dir, "EFF_Analysis.xlsx"), "Summary")
    if eff.empty:
        to_remove += ["EFF 分析", "停机 Pareto"]
    else:
        row = eff.iloc[0]
        cats = ["运行RUN", "待机IDLE", "停机DOWN"]
        vals = [_to_float(row.get(c)) for c in ("运行时间RUN(秒)", "待机时间IDLE(秒)", "停机时间DOWN(秒)")]
        _build_section(prs, "EFF 分析", "EFF = 操作时间(运行+待机) / 计划生产时间",
                       XL_CHART_TYPE.PIE, "时间构成（秒）", cats, vals, _metrics_table(eff))
        pareto = _read_sheet(os.path.join(output_dir, "EFF_Analysis.xlsx"), "DOWN_Pareto")
        if pareto.empty:
            to_remove.append("停机 Pareto")
        else:
            top = pareto.head(10)
            if '原因名称' in top.columns and top['原因名称'].notna().any():
                # 有原因清单：以中文原因名称展示
                labels = top['原因名称'].fillna('')
                table_df = top[['原因名称', '次数', '总时长(秒)', '占比(%)']].copy()
                subtitle = "按停机原因统计时长 Top10"
            else:
                labels = top['ReasonID']
                table_df = top[['ReasonID', '次数', '总时长(秒)', '占比(%)']]
                subtitle = "按 ReasonID 统计停机时长 Top10"
            _build_section(prs, "停机 Pareto", subtitle,
                           XL_CHART_TYPE.BAR_CLUSTERED, "停机时长（秒）",
                           labels, top["总时长(秒)"], table_df)

    # ---------- 报警分析 ----------
    by_kw = _read_sheet(os.path.join(output_dir, "Alarm_Analysis.xlsx"), "ByKeyword")
    alarm_summary = _read_sheet(os.path.join(output_dir, "Alarm_Analysis.xlsx"), "Summary")
    if by_kw.empty and alarm_summary.empty:
        to_remove.append("报警分析")
    else:
        if not by_kw.empty:
            top = by_kw.head(10)
            _build_section(prs, "报警分析", "按关键词与模块统计报警",
                           XL_CHART_TYPE.COLUMN_CLUSTERED, "报警次数 Top10",
                           top["命中关键词"], top["报警次数"], top)
        else:
            _build_section(prs, "报警分析", "按关键词与模块统计报警",
                           XL_CHART_TYPE.COLUMN_CLUSTERED, "报警次数 Top10",
                           [], [], alarm_summary)

    # ---------- 机台状态 ----------
    status = _read_sheet(os.path.join(output_dir, "Status_Analysis.xlsx"), "Summary")
    if status.empty:
        to_remove += ["机台状态汇总", "机台状态趋势"]
    else:
        cats = list(status["状态"])
        vals = [_to_float(v) for v in status["总时长(秒)"]]
        _build_section(prs, "机台状态汇总", "RUN / IDLE / DOWN / WARN 时长与占比",
                       XL_CHART_TYPE.PIE, "状态时长（秒）", cats, vals, status)
        hourly = _read_sheet(os.path.join(output_dir, "Status_Analysis.xlsx"), "Hourly")
        if hourly.empty or "EFF(%)" not in hourly.columns:
            to_remove.append("机台状态趋势")
        else:
            _build_section(prs, "机台状态趋势", "每小时 EFF 趋势",
                           XL_CHART_TYPE.LINE_MARKERS, "每小时 EFF(%)",
                           hourly["小时"], hourly["EFF(%)"], pd.DataFrame(), chart_full=True)

    for title in to_remove:
        _delete_slide_by_title(prs, title)

    _update_page_numbers(prs)
    prs.save(out_path)
    return out_path
