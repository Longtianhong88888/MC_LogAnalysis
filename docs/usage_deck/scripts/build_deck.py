#!/usr/bin/env python3
"""MC Log Analysis 使用说明 deck 构建脚本（python-pptx 原生，editable）。

读取 build/generated/slide_specs.yaml 作为页面合同，按 theme_tokens 排版，
输出 build/pptx/usage_deck.pptx。所有矩形/卡片文字直接写入 shape.text_frame。
"""

import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

import yaml
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "build" / "generated" / "slide_specs.yaml"
OUT_PATH = ROOT / "build" / "pptx" / "usage_deck.pptx"
GANTT_PNG = ROOT / "assets" / "images" / "generated" / "gantt_example_lm.png"

NAVY = RGBColor(0x1F, 0x4E, 0x79)
BLUE_LIGHT = RGBColor(0xDE, 0xEB, 0xF7)
GRAY = RGBColor(0x59, 0x59, 0x59)
GRAY_LIGHT = RGBColor(0xF2, 0xF5, 0xF8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ACCENT = RGBColor(0xED, 0x7D, 0x31)
GREEN = RGBColor(0x70, 0xAD, 0x47)

EA_FONT = "宋体"
LATIN_FONT = "Times New Roman"
TOTAL_SLIDES = 13


def _set_run(run, size, bold=False, color=RGBColor(0x00, 0x00, 0x00), latin=None, ea=None):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = latin or LATIN_FONT
    rPr = run._r.get_or_add_rPr()
    ea_el = rPr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
    from pptx.oxml.ns import qn
    if ea_el is None:
        ea_el = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea_el)
    ea_el.set("typeface", ea or EA_FONT)


def add_text(slide, x, y, w, h, text, size=12, bold=False, color=RGBColor(0, 0, 0),
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.0,
             space_after=0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        if space_after:
            p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = line
        _set_run(r, size, bold, color)
    return box


def add_rect_text(slide, x, y, w, h, text, fill=WHITE, line_color=None, radius=None,
                  size=12, bold=False, color=RGBColor(0, 0, 0), align=PP_ALIGN.LEFT,
                  anchor=MSO_ANCHOR.MIDDLE, line_spacing=1.0, margin=0.12):
    """矩形/卡片：文字直接写入 shape.text_frame（anti-slop：不额外叠文本框）。"""
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line_color is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line_color
        shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    tf = shp.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(0.06)
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        r = p.add_run()
        r.text = line
        _set_run(r, size, bold, color)
    return shp


def add_line(slide, x, y, w, color=NAVY, weight=1.5):
    ln = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb = color
    ln.line.width = Pt(weight)
    return ln


def add_arrow(slide, x, y, w, color=NAVY, weight=2.0):
    """横向箭头（直线 + 三角），用于流程步骤连接。"""
    ln = slide.shapes.add_connector(1, Inches(x), Inches(y), Inches(x + w), Inches(y))
    ln.line.color.rgb = color
    ln.line.width = Pt(weight)
    tri = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE,
                                 Inches(x + w - 0.06), Inches(y - 0.07),
                                 Inches(0.14), Inches(0.14))
    tri.rotation = 90
    tri.fill.solid()
    tri.fill.fore_color.rgb = color
    tri.line.fill.background()
    tri.shadow.inherit = False
    return ln


def header(slide, page_title, page_no):
    """统一页眉：左上标题 + 右下页码/版本。"""
    add_line(slide, 0.78, 1.06, 11.77, color=NAVY, weight=1.25)
    add_text(slide, 0.78, 0.32, 11.0, 0.62, page_title, size=24, bold=True, color=NAVY)
    add_text(slide, 10.2, 7.08, 2.6, 0.3,
             f"{page_no} / {TOTAL_SLIDES}   ·   v1.0 内部使用",
             size=9, color=GRAY, align=PP_ALIGN.RIGHT)


def build_cover(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, 1.1, 2.25, 11.1, 1.0, "MC Log Analysis", size=40, bold=True, color=NAVY)
    add_text(slide, 1.12, 3.35, 11.0, 0.55, "机台日志分析工具 · 使用说明", size=16, color=GRAY)
    add_line(slide, 1.12, 4.15, 3.6, color=NAVY, weight=2.0)
    add_text(slide, 1.12, 4.45, 11.0, 0.4,
             "功能与亮点  ·  操作教学  ·  制程与口径  ·  输出与注意", size=14, color=GRAY)
    add_text(slide, 1.12, 6.7, 11.0, 0.3, "v1.0  ·  内部使用", size=9, color=GRAY)


def build_overview(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, "一个工具，完成机台日志的六类分析与报告", 2)
    add_text(slide, 0.78, 1.35, 11.7, 0.5,
             "把机台日志的“读、算、查、报”一次做完：选择日志文件夹与制程，一键输出 Excel 与 PPT 报告。",
             size=14, color=GRAY)
    nums = [
        ("6", "类分析功能", "合并拆分 · UPH · EFF · 报警 · 状态 · 一键"),
        ("5", "种制程模板", "LM / CAW / FR / SA / ACF，参数自动预填"),
        ("4+1", "类输出", "UPH / EFF / 报警 / 状态 Excel + 自动 PPT 报告"),
    ]
    x0 = 0.78
    for i, (num, label, desc) in enumerate(nums):
        x = x0 + i * 4.05
        add_text(slide, x, 2.35, 3.7, 1.0, num, size=40, bold=True, color=NAVY, align=PP_ALIGN.LEFT)
        add_text(slide, x + 0.05, 3.45, 3.6, 0.4, label, size=16, bold=True)
        add_text(slide, x + 0.05, 3.95, 3.65, 1.0, desc, size=12, color=GRAY, line_spacing=1.3)
        if i < 2:
            add_line(slide, x + 3.7, 2.5, 0.0, color=GRAY)
    add_rect_text(slide, 0.78, 5.55, 11.77, 0.75,
                  "支持“一键分析”：一次运行完成全部功能，结果在界面显示，并自动导出 4 个分析 Excel 与 PPT 报告。",
                  fill=BLUE_LIGHT, size=14, bold=True, color=NAVY, align=PP_ALIGN.LEFT)


def build_grid(prs, spec, cards, page_no, title):
    """3×2 直角卡片网格（卡片文字直接写入 shape）。"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, title, page_no)
    cw, ch = 3.82, 2.28
    for i, (t, body) in enumerate(cards):
        row, col = divmod(i, 3)
        x = 0.78 + col * (cw + 0.16)
        y = 1.5 + row * (ch + 0.22)
        shp = add_rect_text(slide, x, y, cw, ch, t, fill=GRAY_LIGHT, size=14, bold=True,
                            color=NAVY, anchor=MSO_ANCHOR.TOP, margin=0.14)
        tf = shp.text_frame
        p = tf.add_paragraph()
        p.line_spacing = 1.25
        p.space_before = Pt(6)
        r = p.add_run()
        r.text = body
        _set_run(r, 12, False, GRAY)
    return slide


def build_flow(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, "5 步完成一次机台日志分析", 5)
    steps = [
        ("1 选择源文件夹", "机台日志所在目录，支持子文件夹"),
        ("2 选择输出文件夹", "Excel / PPT 报告输出位置"),
        ("3 选择制程模板", "自动预填 UPH 触发词、报警关键词等参数"),
        ("4 选择功能", "合并 / UPH / EFF / 报警 / 状态 / 一键"),
        ("5 自动报告", "界面显示结果，并导出 Excel / PPT"),
    ]
    bw, bh, gap = 2.12, 1.15, 0.42
    x0 = 0.78
    y = 2.0
    for i, (t, desc) in enumerate(steps):
        x = x0 + i * (bw + gap)
        add_rect_text(slide, x, y, bw, bh, t, fill=NAVY, radius=0.08,
                      size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        add_text(slide, x - 0.08, y + bh + 0.18, bw + 0.16, 1.0, desc,
                 size=12, color=GRAY, align=PP_ALIGN.CENTER, line_spacing=1.3)
        if i < 4:
            add_arrow(slide, x + bw - 0.02, y + bh / 2, gap + 0.06)
    add_text(slide, 0.78, 5.6, 11.77, 0.4,
             "提示：日志文件筛选框会自动填充与制程匹配的内容，有特殊需求也可手动输入。",
             size=12, color=GRAY)


def build_ui_map(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, "界面一看就懂：左边选功能，右边筛日志，下方看结果", 6)
    add_text(slide, 0.78, 1.25, 11.7, 0.4, "界面示意（非截图）：三块区域各司其职。",
             size=12, color=GRAY)
    # 左：功能选择
    add_rect_text(slide, 0.78, 1.9, 2.9, 4.35, "功能选择",
                  fill=BLUE_LIGHT, size=14, bold=True, color=NAVY, anchor=MSO_ANCHOR.TOP, margin=0.14)
    left_items = ["文档合并与内容拆分", "UPH 分析", "EFF 分析", "报警分析", "机台状态分析", "一键分析"]
    for j, it in enumerate(left_items):
        add_text(slide, 1.0, 2.42 + j * 0.58, 2.55, 0.4, "· " + it, size=12, color=GRAY)
    # 右：制程模板 + 日志筛选 + 解析参数
    add_rect_text(slide, 3.92, 1.9, 8.63, 2.6, "制程模板 · 日志文件筛选 · 解析参数",
                  fill=GRAY_LIGHT, size=14, bold=True, color=NAVY, anchor=MSO_ANCHOR.TOP, margin=0.14)
    add_text(slide, 4.15, 2.55, 8.2, 0.4, "制程下拉：LM / CAW / FR / SA / ACF / 通用 / 自定义", size=12)
    add_text(slide, 4.15, 3.05, 8.2, 0.4, "日志文件筛选：自动填充与制程匹配的内容，可手动修改", size=12)
    add_text(slide, 4.15, 3.55, 8.2, 0.4, "解析参数：关键词、分隔符（默认左对齐）", size=12)
    # 下：解析结果
    add_rect_text(slide, 3.92, 4.75, 8.63, 1.5, "解析结果",
                  fill=WHITE, line_color=NAVY, size=14, bold=True, color=NAVY, anchor=MSO_ANCHOR.TOP, margin=0.14)
    add_text(slide, 4.15, 5.35, 8.2, 0.7, "分析结果表格与进度显示；顶部“使用说明”按钮可查看各制程说明与计算逻辑，右下角为版权信息。",
             size=12, color=GRAY, line_spacing=1.4)


def build_table_page(prs, spec, headers, rows, page_no, title, note=None, col_widths=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, title, page_no)
    n_rows = len(rows) + 1
    n_cols = len(headers)
    tbl_shape = slide.shapes.add_table(n_rows, n_cols, Inches(0.78), Inches(1.6),
                                       Inches(11.77), Inches(0.42 * n_rows + 0.2))
    tbl = tbl_shape.table
    if col_widths:
        for j, w in enumerate(col_widths):
            tbl.columns[j].width = Inches(w)
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.text = h
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.CENTER
            for r in p.runs:
                _set_run(r, 10.5, True, NAVY)
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = str(val)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.LEFT
                p.line_spacing = 1.0
                for r in p.runs:
                    _set_run(r, 10.5, False, RGBColor(0, 0, 0))
    if note:
        add_text(slide, 0.78, 6.55, 11.77, 0.5, note, size=12, color=GRAY)
    return slide


def build_formulas(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, "UPH 口径：实际、Pure、Derated M1/M2 与有效 UPH", 8)
    items = [
        ("实际 UPH = 产出数 ÷ 统计时长 × 3600", "按真实产出与统计时长计算。"),
        ("Pure UPH = 3600 × 每周期产出 ÷ 理想周期CT", "未填理想 CT 时取正常周期平均。"),
        ("Derated UPH M2 = 3600 × 每周期产出 ÷ 有效平均周期", "剔除 <0.9×理想CT、>1.1×最大理论CT 的离群点；多模组整机 = 各模组 M2 之和。"),
        ("Derated UPH M1 = EM 投入数 ÷ RUN 时长", "多模组整机 = 各模组 M1 之和。"),
        ("有效 UPH = 3600 × 每周期产出 ÷（基础周期 + 每颗换盘开销）", "每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数。"),
    ]
    y = 1.55
    for formula, note in items:
        add_text(slide, 0.78, y, 11.77, 0.42, formula, size=14, bold=True, color=NAVY)
        add_text(slide, 0.78, y + 0.42, 11.77, 0.36, note, size=12, color=GRAY)
        y += 1.05
        add_line(slide, 0.78, y - 0.18, 11.77, color=RGBColor(0xD9, 0xD9, 0xD9), weight=0.75)
    add_text(slide, 0.78, y + 0.05, 9.0, 0.5,
             "周期分类：间隔 > 计划性停机阈值 → 计划性停机；> 正常周期阈值 → 异常周期；其余为正常周期。",
             size=12, color=GRAY)


def build_gantt(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, "步骤拆到运动节拍，甘特图一眼看出先后与并行", 9)
    add_text(slide, 0.78, 1.3, 5.2, 0.5, "每个区块的步骤时间总和 ≈ CT（周期中位）。",
             size=14, bold=True, color=NAVY)
    add_text(slide, 0.78, 1.85, 5.2, 2.4,
             "步骤按轴 / 平台运动节拍拆分，例如 LM 单颗循环：\n\n"
             "打标前间隔 → Z 轴焦距定位 → 激光打标（振镜扫描）\n\n"
             "批次级：读码 GetSN、CCD 轴移动定位（每批 6 颗）\n\n"
             "盘级：平台下料、平台上料（每盘 24 颗）",
             size=12, color=GRAY, line_spacing=1.35)
    add_text(slide, 0.78, 4.6, 5.2, 1.6,
             "异常判定 = 中位时长 + 超时秒数；超时/报警/停机行在日志 Excel 中自动标红。",
             size=12, color=GRAY, line_spacing=1.35)
    if GANTT_PNG.exists():
        slide.shapes.add_picture(str(GANTT_PNG), Inches(6.25), Inches(1.35),
                                 width=Inches(6.5))
        add_text(slide, 6.25, 6.35, 6.5, 0.35,
                 "甘特示例：来自工具对 LM 示例日志的分析输出（示意）", size=9, color=GRAY)


def build_tips(prs, spec, cards, page_no, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    header(slide, title, page_no)
    cw, ch = 5.82, 2.35
    for i, (t, body) in enumerate(cards):
        row, col = divmod(i, 2)
        x = 0.78 + col * (cw + 0.16)
        y = 1.55 + row * (ch + 0.25)
        shp = add_rect_text(slide, x, y, cw, ch, t, fill=GRAY_LIGHT, size=14, bold=True,
                            color=NAVY, anchor=MSO_ANCHOR.TOP, margin=0.16)
        tf = shp.text_frame
        p = tf.add_paragraph()
        p.line_spacing = 1.3
        p.space_before = Pt(6)
        r = p.add_run()
        r.text = body
        _set_run(r, 12, False, GRAY)


def build_closing(prs, spec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, 1.1, 2.6, 11.1, 0.9, "现在就可以开始第一次分析", size=40, bold=True, color=NAVY)
    add_text(slide, 1.12, 3.7, 11.0, 0.5, "选日志文件夹 → 选制程模板 → 点“自动报告”", size=16, color=GRAY)
    add_line(slide, 1.12, 4.5, 3.6, color=NAVY, weight=2.0)
    add_text(slide, 1.12, 4.8, 11.0, 0.4,
             "功能与亮点  ·  操作教学  ·  制程与口径  ·  输出与注意", size=14, color=GRAY)
    add_text(slide, 1.12, 6.7, 11.0, 0.3, "v1.0  ·  内部使用", size=9, color=GRAY)


def fix_docprops_slide_count(path):
    """docProps/app.xml 的 Slides 统计与实际页数不一致会触发 package_preflight 硬阻断；
    保存后用 zip 级修正（只改该 entry，保留其余条目）。"""
    tmp = path.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "docProps/app.xml":
                s = data.decode("utf-8")
                s = re.sub(r"<Slides>\s*\d*\s*</Slides>", "<Slides>%d</Slides>" % TOTAL_SLIDES, s)
                if "<Slides>" not in s:
                    s = s.replace("</Properties>", "<Slides>%d</Slides></Properties>" % TOTAL_SLIDES)
                data = s.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(str(tmp), str(path))


def main():
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    build_cover(prs, spec)
    build_overview(prs, spec)
    build_grid(prs, spec, [
        ("文档合并与内容拆分", "按关键词 / 分隔符提取指定行，支持按 PLC 分组导出，异常行自动标红。"),
        ("UPH 分析", "按 CoreTech AME 口径输出实际 / Pure / Derated M1/M2 / 有效 UPH，自动判定瓶颈。"),
        ("EFF 分析", "操作时间 ÷ 计划生产时间；停机按 EReason 清单区分 pDT / uDT。"),
        ("报警分析", "按关键词统计报警，EReason 中文名映射。"),
        ("机台状态分析", "status 行或活动 / 停机关键词推导 RUN / IDLE / DOWN 时间线。"),
        ("一键分析", "一次运行完成全部功能，导出 4 个 Excel 并自动生成 PPT 报告。"),
    ], 3, "六大功能，覆盖日志分析的完整链路")
    build_grid(prs, spec, [
        ("制程模板一键预填", "选 LM / CAW / FR / SA / ACF，自动带入触发词、报警关键词与计算逻辑。"),
        ("瓶颈自动判定", "SA 四工位、CAW 双机台自动取最慢环节，UPH 口径与客户定义一致。"),
        ("换盘时间平摊", "整盘结束后的下料-上料时间按每盘颗数摊入单颗 CT。"),
        ("步骤深度分析 + 甘特图", "按轴 / 平台运动节拍拆步骤，Excel 甘特图直接看出先后与并行。"),
        ("异常日志自动标红", "报警 / 停机 / 步骤超时行标红，剔除产品码中的 NG 误报。"),
        ("自动 PPT 报告", "汇总 + 图表 + 瓶颈工序甘特图，时间格式统一、可编辑。"),
    ], 4, "亮点：自动模板、瓶颈判定、换盘分摊、步骤甘特、异常标红、自动报告")
    build_flow(prs, spec)
    build_ui_map(prs, spec)
    build_table_page(prs, spec,
                     ["制程", "周期完成事件", "结构", "UPH 口径要点"],
                     [
                         ["LM 激光打标", "MarkEnd1", "单机台；每盘 4 批 × 6 颗", "换盘时间按 24 颗平摊"],
                         ["CAW 组装", "放熟料完成 / 去交换位", "PLC1 焊接机 + PLC2 上料机（左右并行）", "双机台瓶颈，取 CT 长者"],
                         ["FR 点胶", "轴点胶完成", "左轴 / 右轴并行", "Pure UPH ×0.5（单轴）；整机 M1/M2 = 左 + 右"],
                         ["SA 四工位", "各工位完成事件", "点胶 / 贴附 / 热压 / 检测并行", "自动判定瓶颈工位"],
                         ["ACF 三機", "更新Carrier盘 / Cavity cnt:1 / UnloadDuts Finish", "上料機 / 主機 / 下料機 分文件夹", "每盘颗数按 Tray ID 动态统计"],
                     ],
                     7, "五种制程模板，参数与算法已按机台配好",
                     note="另有“通用（手动配置）”与“自定义”模板，不套用固定逻辑。",
                     col_widths=[2.1, 3.3, 3.5, 2.87])
    build_formulas(prs, spec)
    build_gantt(prs, spec)
    build_grid(prs, spec, [
        ("EFF 分析", "EFF = 操作时间（运行 + 待机）÷ 计划生产时间；停机按 ReasonID 拆 pDT / uDT（EReason 清单优先）。"),
        ("机台状态分析", "优先读 status:RUN/IDLE/DOWN 行；无 status 时按“活动 + 停机关键词”推导时间线，输出各状态时长 / 占比 / 小时分布。"),
        ("报警分析", "按关键词命中计数，按机台 / 模组汇总；EReason 清单映射中文原因名称。"),
    ], 10, "EFF、状态与报警：三张表讲清设备效率与异常")
    build_table_page(prs, spec,
                     ["文件", "内容"],
                     [
                         ["UPH_Analysis.xlsx", "Summary / AMESummary / CycleDetail / EMProduction / 步骤分析 / 步骤甘特图"],
                         ["EFF_Analysis.xlsx", "EFF 汇总与停机 Pareto（含 pDT / uDT）"],
                         ["Alarm_Analysis.xlsx", "报警汇总、关键词分布、明细（EReason 中文名）"],
                         ["Status_Analysis.xlsx", "状态汇总与小时分布"],
                         ["LogAnalysis.xlsx", "合并日志（异常行标红）；大文件按日志逐个导出"],
                         ["Analysis_Report.pptx", "自动报告：UPH / EFF / 停机 Pareto / 报警 / 状态 + 瓶颈工序甘特图"],
                     ],
                     11, "一次分析，输出可编辑的 Excel 与 PPT 报告",
                     note="时间格式约定：低于 60 秒按秒显示，超过 60 秒按 h:mm:ss；PPT 汇总时间显示到秒。",
                     col_widths=[3.3, 8.47])
    build_tips(prs, spec, [
        ("大日志保护", "原始日志超过约 100 万行时，自动放弃合并、按日志文件逐个导出 Excel，避免卡死。"),
        ("EReasonlist", "根目录保留 EReasonlist 文件夹，新制程按文件名放入自己的清单，用于状态推导与报警映射。"),
        ("PPT 模板", "Analysis_Report.pptx 放到程序同目录即可正常生成报告；模板含内部数据，仅限内部传送。"),
        ("灵活覆盖", "日志文件筛选框自动填充与制程匹配的内容，用户有特殊需求可手动输入。"),
    ], 12, "使用前注意这几点，避免踩坑")
    build_closing(prs, spec)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT_PATH))
    fix_docprops_slide_count(OUT_PATH)
    print("saved:", OUT_PATH)


if __name__ == "__main__":
    main()
