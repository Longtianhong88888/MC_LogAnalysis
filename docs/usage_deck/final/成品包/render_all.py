"""
PIL slide renderer — uses Hon Hai template backgrounds and logo.
Produces 1920×1080 PNGs with full template branding.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "页面图片"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Template assets ─────────────────────────────────
TEMPLATE_IMAGES = Path("/tmp/template_images/ppt/media")
BG_CONTENT = Image.open(TEMPLATE_IMAGES / "image1.png")   # content page bg
BG_COVER   = Image.open(TEMPLATE_IMAGES / "image3.png")   # cover page bg
LOGO       = Image.open(TEMPLATE_IMAGES / "image2.png")   # Foxconn logo

# ── Canvas ──────────────────────────────────────────
W, H = 1920, 1080
MARGIN = 112  # ~0.78in at 144dpi

# Scale backgrounds to canvas
BG_CONTENT = BG_CONTENT.resize((W, H), Image.LANCZOS)
BG_COVER   = BG_COVER.resize((W, H), Image.LANCZOS)

# Scale logo — original is 1000x1142, target ≈ 84px wide at 144dpi (0.58in)
LOGO_W = 84
LOGO_H = int(LOGO.height * (LOGO_W / LOGO.width))
LOGO_IMG = LOGO.resize((LOGO_W, LOGO_H), Image.LANCZOS)

# ── Colors ──────────────────────────────────────────
NAVY     = (8, 60, 99)        # #083C63
RED_ACC  = (239, 81, 73)      # #EF5149
WHITE    = (255, 255, 255)
DARK     = (38, 38, 38)       # near-black
GRAY     = (89, 89, 89)       # #595959
MID_GRAY = (100, 100, 100)
LT_BLUE  = (222, 235, 247)    # #DEEBF7
LT_PINK  = (253, 239, 238)    # #FDEFEE
ALT_ROW  = (242, 245, 248)    # alternating row

PASTEL = [
    (231, 241, 250), (224, 242, 241), (231, 243, 230),
    (251, 242, 218), (250, 231, 218), (239, 232, 247),
]
CARD_TITLE_CLR = (46, 59, 78)
CARD_BODY_CLR  = (82, 95, 111)

# ── Fonts ───────────────────────────────────────────
FONT_BASE = '/System/Library/Fonts/Supplemental'
FONT_SYS  = '/System/Library/Fonts'

def _f(path, pt):
    return ImageFont.truetype(path, pt * 2)  # pt→px at 144dpi

SONG    = lambda pt: _f(f'{FONT_BASE}/Songti.ttc', pt)
HEI     = lambda pt: _f(f'{FONT_SYS}/STHeiti Medium.ttc', pt)
HEI_L   = lambda pt: _f(f'{FONT_SYS}/STHeiti Light.ttc', pt)
TNR     = lambda pt: _f(f'{FONT_BASE}/Times New Roman.ttf', pt)
TNR_B   = lambda pt: _f(f'{FONT_BASE}/Times New Roman Bold.ttf', pt)

# ── Helpers ─────────────────────────────────────────
def hline(draw, x1, y, x2, color=NAVY, width=2):
    draw.line([(x1, y), (x2, y)], fill=color, width=width)

def center_text(draw, text, font, fill, y, cx=None):
    if cx is None: cx = W // 2
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw//2, y), text, fill=fill, font=font, anchor='la')

def draw_pn(draw, n, total=13):
    text = f"{n} / {total}"
    font = SONG(9)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((W - MARGIN - tw, H - 52), text, fill=GRAY, font=font, anchor='la')

def draw_copyright(draw):
    """© 2026 Hon Hai Precision Industry Co., Ltd. All rights reserved."""
    text = "© 2026  Hon Hai Precision Industry Co., Ltd. All rights reserved."
    font = SONG(8)
    draw.text((20, H - 52), text, fill=NAVY, font=font, anchor='la')

def draw_logo(draw):
    """Place Foxconn logo at top-right."""
    logo_x = W - MARGIN + 28
    logo_y = 8
    draw._image.paste(LOGO_IMG, (logo_x, logo_y), LOGO_IMG if LOGO_IMG.mode == 'RGBA' else None)

def draw_chapter_tag(draw, text, x=MARGIN, y=18):
    draw.text((x, y), text, fill=RED_ACC, font=SONG(10), anchor='la')

def draw_title(draw, text, y=42):
    draw.text((MARGIN, y), text, fill=NAVY, font=HEI(24), anchor='la')

def draw_conclusion(draw, text, y=105):
    draw.text((MARGIN, y), text, fill=MID_GRAY, font=SONG(14), anchor='la')

def draw_source_note(draw, text, y=None):
    if y is None: y = H - 52
    draw.text((MARGIN, y), text, fill=GRAY, font=SONG(9), anchor='la')

def make_slide(bg_type="content"):
    """Create a new slide canvas with template background and branding."""
    bg = BG_COVER if bg_type == "cover" else BG_CONTENT
    img = bg.copy()
    draw = ImageDraw.Draw(img)
    draw_logo(draw)
    draw_copyright(draw)
    return img, draw

# ══════════════════════════════════════════════════════
#  SLIDE RENDERERS
# ══════════════════════════════════════════════════════

def s01_cover():
    img, d = make_slide("cover")
    cy = H // 2 - 20
    hline(d, W//2 - 140, cy - 170, W//2 + 140, color=RED_ACC, width=3)
    center_text(d, "MC Log Analysis", TNR_B(54), NAVY, cy - 128)
    center_text(d, "机台日志分析工具 · 使用说明", SONG(18), DARK, cy - 40)
    hline(d, W//2 - 140, cy + 10, W//2 + 140, color=NAVY, width=1)
    center_text(d, "功能与亮点  ·  操作教学  ·  制程与口径  ·  输出与注意", SONG(14), MID_GRAY, cy + 46)
    d.text((MARGIN, H - 52), "v1.0  ·  内部使用", fill=GRAY, font=SONG(9), anchor='la')
    draw_pn(d, 1)
    return img

def s02_overview():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第1章  功能与亮点")
    draw_title(d, "一个工具，完成机台日志的六类分析与报告")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)
    draw_conclusion(d, "把机台日志的「读、算、查、报」一次做完：选择日志文件夹与制程，一键输出 Excel 与 PPT 报告。", 112)

    nums = [
        ("6", "类分析功能", "合并拆分 · UPH · EFF\n报警 · 状态 · 一键"),
        ("5", "种制程模板", "LM / CAW / FR / SA / ACF\n参数自动预填"),
        ("4+1", "类输出", "UPH / EFF / 报警 / 状态\nExcel + 自动 PPT 报告"),
    ]
    for i, (num, label, desc) in enumerate(nums):
        x = MARGIN + i * 420
        center_text(d, num, TNR_B(40), RED_ACC, 220, cx=x + 150)
        center_text(d, label, HEI(16), NAVY, 310, cx=x + 150)
        for j, line in enumerate(desc.split("\n")):
            center_text(d, line, SONG(14), GRAY, 345 + j * 26, cx=x + 150)

    # Bottom highlight bar
    bar_y = 530
    d.rectangle([(MARGIN, bar_y), (W - MARGIN, bar_y + 100)], fill=LT_PINK, outline=(230, 210, 210))
    center_text(d, "支持「一键分析」：一次运行完成全部功能，自动导出 4 个分析 Excel 与 PPT 报告",
                SONG(15), RED_ACC, bar_y + 36)

    draw_pn(d, 2)
    return img

def s03_functions():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第1章  功能与亮点")
    draw_title(d, "六大功能，覆盖日志分析的完整链路")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    cards = [
        ("文档合并与内容拆分", "按关键词 / 分隔符提取指定行，支持\n按 PLC 分组导出，异常行自动标红。"),
        ("UPH 分析", "按 CoreTech AME 口径输出实际 /\nPure / Derated M1/M2 / 有效 UPH，\n自动判定瓶颈。"),
        ("EFF 分析", "操作时间 ÷ 计划生产时间；停机\n按 EReason 清单区分 pDT / uDT。"),
        ("报警分析", "按关键词统计报警，EReason\n中文名映射。"),
        ("机台状态分析", "status 行或活动 / 停机关键词\n推导 RUN / IDLE / DOWN 时间线。"),
        ("一键分析", "一次运行完成全部功能，导出\n4 个 Excel 并自动生成 PPT 报告。"),
    ]
    cw, ch_val, gap = 360, 190, 12
    for i, (title, body) in enumerate(cards):
        row, col = divmod(i, 3)
        x = MARGIN + col * (cw + gap)
        y = 120 + row * (ch_val + gap)
        # Card
        fill = PASTEL[i % len(PASTEL)]
        d.rectangle([(x, y), (x + cw, y + ch_val)], fill=fill, outline=(210, 215, 225), width=1)
        d.text((x + 14, y + 12), title, fill=NAVY, font=HEI(14), anchor='la')
        for j, line in enumerate(body.split("\n")):
            d.text((x + 14, y + 48 + j * 24), line, fill=CARD_BODY_CLR, font=SONG(12), anchor='la')

    draw_pn(d, 3)
    return img

def s04_highlights():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第1章  功能与亮点")
    draw_title(d, "亮点：自动模板、瓶颈判定、换盘分摊、步骤甘特、异常标红、自动报告")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    cards = [
        ("制程模板一键预填", "选 LM / CAW / FR / SA / ACF，\n自动带入触发词、报警关键词\n与计算逻辑。"),
        ("瓶颈自动判定", "SA 四工位、CAW 双机台自动取\n最慢环节，UPH 口径与客户\n定义一致。"),
        ("换盘时间平摊", "整盘结束后的下料-上料时间\n按每盘颗数摊入单颗 CT。"),
        ("步骤深度分析 + 甘特图", "按轴 / 平台运动节拍拆步骤，\nExcel 甘特图直接看出\n先后与并行。"),
        ("异常日志自动标红", "报警 / 停机 / 步骤超时行\n标红，剔除产品码中的 NG 误报。"),
        ("自动 PPT 报告", "汇总 + 图表 + 瓶颈工序甘特图，\n时间格式统一、可编辑。"),
    ]
    cw, ch_val, gap = 360, 190, 12
    for i, (title, body) in enumerate(cards):
        row, col = divmod(i, 3)
        x = MARGIN + col * (cw + gap)
        y = 120 + row * (ch_val + gap)
        fill = PASTEL[(i + 2) % len(PASTEL)]
        d.rectangle([(x, y), (x + cw, y + ch_val)], fill=fill, outline=(210, 215, 225), width=1)
        d.text((x + 14, y + 12), title, fill=NAVY, font=HEI(14), anchor='la')
        for j, line in enumerate(body.split("\n")):
            d.text((x + 14, y + 48 + j * 24), line, fill=CARD_BODY_CLR, font=SONG(12), anchor='la')

    draw_pn(d, 4)
    return img

def s05_flow():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第2章  操作教学")
    draw_title(d, "5 步完成一次机台日志分析")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    steps = [
        ("1 选择源文件夹", "机台日志所在目录\n支持子文件夹"),
        ("2 选择输出文件夹", "Excel / PPT 报告\n输出位置"),
        ("3 选择制程模板", "自动预填 UPH 触发词\n报警关键词等"),
        ("4 选择功能", "合并 / UPH / EFF\n报警 / 状态 / 一键"),
        ("5 自动报告", "界面显示结果\n并导出 Excel / PPT"),
    ]
    bw, bh_val, gap = 280, 100, 32
    y0 = 150
    for i, (title, desc) in enumerate(steps):
        x = MARGIN + i * (bw + gap)
        # Step node
        d.rounded_rectangle([(x, y0), (x + bw, y0 + bh_val)], radius=10,
                            fill=NAVY, outline=NAVY, width=1)
        center_text(d, title, HEI(15), WHITE, y0 + 22, cx=x + bw // 2)
        # Arrow between steps
        if i < 4:
            arrow_x = x + bw + 4
            d.polygon([(arrow_x + gap - 4, y0 + bh_val // 2),
                       (arrow_x + gap - 16, y0 + bh_val // 2 - 8),
                       (arrow_x + gap - 16, y0 + bh_val // 2 + 8)],
                      fill=NAVY)
            d.line([(arrow_x, y0 + bh_val // 2), (arrow_x + gap - 6, y0 + bh_val // 2)],
                   fill=NAVY, width=2)
        # Description below
        for j, line in enumerate(desc.split("\n")):
            center_text(d, line, SONG(12), GRAY, y0 + bh_val + 18 + j * 22, cx=x + bw // 2)

    # Tips box
    tip_y = 450
    d.rectangle([(MARGIN, tip_y), (W - MARGIN, tip_y + 140)], fill=PASTEL[0], outline=(210, 215, 225))
    d.text((MARGIN + 18, tip_y + 14), "操作小贴士", fill=NAVY, font=HEI(15), anchor='la')
    tips = [
        "· 日志文件筛选框会自动填充与制程匹配的内容，有特殊需求可手动输入",
        "· 制程模板会自动预填 UPH 触发词、报警关键词、制程名称（原因清单）",
        "· 一键分析 = 合并拆分 + UPH + EFF + 报警 + 机台状态，一次全部完成",
    ]
    for j, tip in enumerate(tips):
        d.text((MARGIN + 24, tip_y + 48 + j * 28), tip, fill=CARD_BODY_CLR, font=SONG(12), anchor='la')

    draw_pn(d, 5)
    return img

def s06_ui_map():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第2章  操作教学")
    draw_title(d, "界面一看就懂：左边选功能，右边筛日志，下方看结果")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)
    d.text((MARGIN, 112), "界面示意（非截图）：三块区域各司其职。", fill=GRAY, font=SONG(14), anchor='la')

    # Left panel — Function Selection
    d.rectangle([(MARGIN, 150), (MARGIN + 280, 680)], fill=LT_PINK, outline=(230, 210, 210))
    d.text((MARGIN + 16, 166), "功能选择", fill=RED_ACC, font=HEI(15), anchor='la')
    funcs = ["文档合并与内容拆分", "UPH 分析", "EFF 分析", "报警分析", "机台状态分析", "一键分析"]
    for j, f in enumerate(funcs):
        d.text((MARGIN + 24, 206 + j * 48), "· " + f, fill=GRAY, font=SONG(13), anchor='la')

    # Middle panel — Log Filter
    mx = MARGIN + 292
    d.rectangle([(mx, 150), (mx + 260, 680)], fill=LT_BLUE, outline=(190, 205, 225))
    d.text((mx + 16, 166), "日志文件筛选\n+ 制程模板", fill=NAVY, font=HEI(14), anchor='la')
    mids = ["制程下拉", "文件筛选框", "解析参数"]
    for j, m in enumerate(mids):
        d.text((mx + 16, 250 + j * 48), "· " + m, fill=GRAY, font=SONG(13), anchor='la')

    # Right panel — Results
    rx = mx + 272
    rw = W - MARGIN - rx
    d.rectangle([(rx, 150), (rx + rw, 680)], fill=PASTEL[2], outline=(210, 215, 225))
    d.text((rx + 16, 166), "解析结果", fill=CARD_TITLE_CLR, font=HEI(15), anchor='la')
    results = ["分析结果表格", "进度显示与状态信息", "右键导出 Excel / PPT"]
    for j, r in enumerate(results):
        d.text((rx + 16, 220 + j * 48), "· " + r, fill=CARD_BODY_CLR, font=SONG(13), anchor='la')

    draw_pn(d, 6)
    return img

def s07_process_table():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第3章  制程与口径")
    draw_title(d, "五种制程模板，参数与算法已按机台配好")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    headers = ["制程", "周期完成事件", "结构", "UPH 口径要点"]
    col_widths = [200, 280, 340, 488]
    data = [
        ["LM 激光打标", "MarkEnd1", "单机台；每盘 4 批×6 颗", "换盘时间按 24 颗平摊"],
        ["CAW 组装", "放熟料完成 / 去交换位", "PLC1 焊接机 + PLC2 上料机（并行）", "双机台瓶颈，取 CT 长者"],
        ["FR 点胶", "轴点胶完成", "左轴/右轴并行", "Pure UPH ×0.5（单轴），M1/M2=左+右"],
        ["SA 四工位", "各工位完成事件", "点胶/贴附/热压/检测并行", "自动判定瓶颈工位"],
        ["ACF 三機", "更新Carrier盘等", "上料機/主機/下料機 分文件夹", "每盘颗数按 Tray ID 动态统计"],
    ]
    tx, ty = MARGIN, 120
    row_h = 76
    # Header
    cx = tx
    for j, (hdr, cw) in enumerate(zip(headers, col_widths)):
        d.rectangle([(cx, ty), (cx + cw, ty + 38)], fill=NAVY)
        center_text(d, hdr, HEI(11), WHITE, ty + 10, cx=cx + cw // 2)
        cx += cw
    # Data rows
    for i, row in enumerate(data):
        cx = tx
        ry = ty + 38 + i * row_h
        bg_fill = WHITE if i % 2 == 0 else ALT_ROW
        for j, (val, cw) in enumerate(zip(row, col_widths)):
            d.rectangle([(cx, ry), (cx + cw, ry + row_h)], fill=bg_fill,
                        outline=(210, 215, 225) if i > 0 or True else None, width=1)
            font = HEI(12) if j == 0 else SONG(12)
            color = NAVY if j == 0 else DARK
            # Handle multi-line
            for k, line in enumerate(val.split("\n")):
                d.text((cx + 10, ry + 8 + k * 22), line, fill=color, font=font, anchor='la')
            cx += cw

    d.text((MARGIN, ty + 38 + 5 * row_h + 12), "另有「通用（手动配置）」与「自定义」模板，不套用固定逻辑。",
           fill=GRAY, font=SONG(11), anchor='la')
    draw_pn(d, 7)
    return img

def s08_formulas():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第3章  制程与口径")
    draw_title(d, "UPH 口径：实际、Pure、Derated M1/M2 与有效 UPH")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)
    draw_conclusion(d, "实际 UPH 看真实产出，Pure 看理想节拍，Derated 剔离群点，有效 UPH 把换盘时间摊进单颗", 112)

    formulas = [
        ("实际 UPH", "= 产出数 ÷ 统计时长 × 3600", "按真实产出与统计时长计算。"),
        ("Pure UPH", "= 3600 × 每周期产出 ÷ 理想周期CT", "未填理想 CT 时取正常周期平均。"),
        ("Derated UPH M2", "= 3600 × 每周期产出 ÷ 有效平均周期",
         "剔除 <0.9×理想CT、>1.1×最大理论CT 的离群点；多模组整机 = 各模组 M2 之和。"),
        ("Derated UPH M1", "= EM 投入数 ÷ RUN 时长", "多模组整机 = 各模组 M1 之和。"),
        ("有效 UPH", "= 3600 × 每周期产出 ÷（基础周期 + 每颗换盘开销）", "每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数。"),
    ]
    y0, row_h = 150, 72
    for i, (name, eq, detail) in enumerate(formulas):
        y = y0 + i * row_h
        if i % 2 == 0:
            d.rectangle([(MARGIN, y), (W - MARGIN, y + row_h)], fill=ALT_ROW)
        d.text((MARGIN + 12, y + 6), name, fill=NAVY, font=HEI(15), anchor='la')
        d.text((MARGIN + 268, y + 6), eq, fill=DARK, font=SONG(13), anchor='la')
        d.text((MARGIN + 268, y + 36), detail, fill=MID_GRAY, font=SONG(11), anchor='la')
        if i < 4:
            hline(d, MARGIN + 12, y + row_h, W - MARGIN - 12, color=(210, 215, 225), width=1)

    # Period classification
    cy = y0 + 5 * row_h + 14
    d.text((MARGIN + 12, cy), "周期分类：间隔 > 计划性停机阈值 → 计划性停机；> 正常周期阈值 → 异常周期；其余为正常周期。",
           fill=MID_GRAY, font=SONG(11), anchor='la')

    # Swap example card
    card_y = cy + 38
    card_h = 150
    d.rectangle([(MARGIN + 8, card_y), (W - MARGIN - 8, card_y + card_h)],
                fill=LT_BLUE, outline=(180, 200, 220), width=1)
    d.text((MARGIN + 30, card_y + 16), "换盘分摊示例（LM）", fill=NAVY, font=HEI(15), anchor='la')

    ex_lines = [
        "单次换盘（下料 → 新盘上料）：15.46 秒          每盘颗数：24 颗",
        "每颗换盘开销：15.46 ÷ 24 ≈ 0.64 秒",
        "有效周期 = 1.65 + 0.64 ≈ 2.29 秒          Pure UPH ≈ 1570 / 小时",
    ]
    for j, line in enumerate(ex_lines):
        d.text((MARGIN + 30, card_y + 50 + j * 28), line, fill=DARK, font=SONG(13), anchor='la')

    draw_source_note(d, "UPH 口径按 CoreTech AME 定义；换盘示例数值为说明用途。")
    draw_pn(d, 8)
    return img

def s09_gantt():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第3章  制程与口径")
    draw_title(d, "步骤拆到运动节拍，甘特图一眼看出先后与并行")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    # Left explanation
    d.text((MARGIN, 125), "步骤按轴 / 平台运动节拍拆分（以 LM 单颗循环为例）：",
           fill=NAVY, font=HEI(14), anchor='la')
    steps_text = [
        "打标前间隔 → Z 轴焦距定位 → 激光打标（振镜扫描）",
        "",
        "批次级：读码 GetSN、CCD 轴移动定位（每批 6 颗）",
        "",
        "盘级：平台下料、平台上料（每盘 24 颗）",
    ]
    for j, line in enumerate(steps_text):
        d.text((MARGIN + 8, 168 + j * 28), line, fill=DARK if line else DARK, font=SONG(14), anchor='la')

    d.text((MARGIN + 8, 340), "异常判定 = 中位时长 + 超时秒数", fill=GRAY, font=SONG(13), anchor='la')
    d.text((MARGIN + 8, 370), "超时 / 报警 / 停机行在 Excel 中自动标红。", fill=GRAY, font=SONG(13), anchor='la')

    # Right: Gantt placeholder
    gantt_png = Path("/Users/user/Desktop/PY/MC_LogAnalysis/docs/usage_deck/assets/images/generated/gantt_example_lm.png")
    if gantt_png.exists():
        gantt_img = Image.open(gantt_png)
        gw, gh = 540, 410
        gantt_img = gantt_img.resize((gw, gh), Image.LANCZOS)
        img.paste(gantt_img, (W - MARGIN - gw, 140), gantt_img if gantt_img.mode == 'RGBA' else None)
        d = ImageDraw.Draw(img)  # refresh draw after paste

    # Gantt caption
    center_text(d, "甘特示例：来自工具对 LM 示例日志的分析输出（示意）",
                SONG(9), GRAY, 610, cx=W - MARGIN - 270)

    draw_pn(d, 9)
    return img

def s10_eff():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第3章  制程与口径")
    draw_title(d, "EFF、状态与报警：三张表讲清设备效率与异常")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    cards = [
        ("EFF 分析", "EFF = 操作时间（运行 + 待机）÷ 计划\n生产时间；停机按 ReasonID 拆 pDT / uDT\n（EReason 清单优先）。"),
        ("机台状态分析", "优先读 status:RUN/IDLE/DOWN 行；无\nstatus 时按活动+停机关键词推导时间线，\n输出各状态时长/占比/小时分布。"),
        ("报警分析", "按关键词命中计数，按机台/模组汇总；\nEReason 清单映射中文原因名称。"),
    ]
    for i, (title, body) in enumerate(cards):
        x = MARGIN + i * 400
        d.rectangle([(x, 130), (x + 384, 270)], fill=PASTEL[(4 + i) % len(PASTEL)], outline=(210, 215, 225))
        d.text((x + 14, 146), title, fill=NAVY, font=HEI(15), anchor='la')
        for j, line in enumerate(body.split("\n")):
            d.text((x + 14, 190 + j * 28), line, fill=CARD_BODY_CLR, font=SONG(12), anchor='la')

    # Bottom explanation
    d.text((MARGIN, 430), "停机分类：EReason 清单中的计划停机（Planned / Routine）计入 pDT，其余计入 uDT；", fill=GRAY, font=SONG(12), anchor='la')
    d.text((MARGIN, 460), "未填计划停机 ReasonID 时，全部停机计入可用性损失。", fill=GRAY, font=SONG(12), anchor='la')
    d.text((MARGIN, 500), "状态推导：优先识别日志中的 status:RUN / IDLE / DOWN 行；无 status 行时按活动与停机关键词推导时间线。", fill=GRAY, font=SONG(12), anchor='la')

    draw_pn(d, 10)
    return img

def s11_outputs():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第4章  输出与注意")
    draw_title(d, "一次分析，输出可编辑的 Excel 与 PPT 报告")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    headers = ["文件", "内容"]
    col_widths = [380, 928]
    data = [
        ("UPH_Analysis.xlsx", "Summary / AMESummary / CycleDetail / EMProduction / 步骤分析 / 步骤甘特图"),
        ("EFF_Analysis.xlsx", "EFF 汇总与停机 Pareto（含 pDT/uDT）"),
        ("Alarm_Analysis.xlsx", "报警汇总、关键词分布、明细（EReason 中文名）"),
        ("Status_Analysis.xlsx", "状态汇总与小时分布"),
        ("LogAnalysis.xlsx", "合并日志（异常行标红）；大文件按日志逐个导出"),
        ("Analysis_Report.pptx", "自动报告：UPH/EFF/停机Pareto/报警/状态 + 瓶颈工序甘特图"),
    ]
    tx, ty = MARGIN, 120
    row_h = 68
    cx = tx
    for hdr, cw in zip(headers, col_widths):
        d.rectangle([(cx, ty), (cx + cw, ty + 40)], fill=NAVY)
        center_text(d, hdr, HEI(11), WHITE, ty + 12, cx=cx + cw // 2)
        cx += cw
    for i, (name, content) in enumerate(data):
        cx = tx
        ry = ty + 40 + i * row_h
        bg_fill = WHITE if i % 2 == 0 else ALT_ROW
        for val, cw in zip([name, content], col_widths):
            d.rectangle([(cx, ry), (cx + cw, ry + row_h)], fill=bg_fill, outline=(210, 215, 225), width=1)
            color = NAVY if cx == tx else DARK
            font = HEI(12) if cx == tx else SONG(12)
            d.text((cx + 10, ry + 18), val, fill=color, font=font, anchor='la')
            cx += cw

    d.text((MARGIN, ty + 40 + 6 * row_h + 16),
           "时间格式约定：低于 60 秒按秒显示，超过 60 秒按 h:mm:ss；PPT 汇总时间显示到秒。",
           fill=GRAY, font=SONG(11), anchor='la')
    draw_pn(d, 11)
    return img

def s12_tips():
    img, d = make_slide("content")
    draw_chapter_tag(d, "第4章  输出与注意")
    draw_title(d, "使用前注意这几点，避免踩坑")
    hline(d, MARGIN, 92, W - MARGIN, color=NAVY, width=1)

    cards = [
        ("大日志保护", "原始日志超过约 100 万行时，自动\n放弃合并、按日志文件逐个导出\nExcel，避免卡死。"),
        ("EReasonlist", "根目录保留 EReasonlist 文件夹，\n新制程按文件名放入自己的清单，\n用于状态推导与报警映射。"),
        ("PPT 模板", "Analysis_Report.pptx 放到程序\n同目录即可正常生成报告；模板含\n内部数据，仅限内部传送。"),
        ("灵活覆盖", "日志文件筛选框自动填充与制程\n匹配的内容，用户有特殊需求可\n手动输入。"),
    ]
    for i, (title, body) in enumerate(cards):
        row, col = divmod(i, 2)
        x = MARGIN + col * 610
        y = 130 + row * 300
        d.rectangle([(x, y), (x + 590, y + 270)], fill=PASTEL[(i + 2) % len(PASTEL)], outline=(210, 215, 225))
        d.text((x + 18, y + 16), title, fill=NAVY, font=HEI(15), anchor='la')
        for j, line in enumerate(body.split("\n")):
            d.text((x + 18, y + 60 + j * 28), line, fill=CARD_BODY_CLR, font=SONG(13), anchor='la')

    draw_pn(d, 12)
    return img

def s13_closing():
    img, d = make_slide("cover")
    cy = H // 2 - 20
    center_text(d, "现在就可以开始第一次分析", TNR_B(40), RED_ACC, cy - 128)
    center_text(d, "选日志文件夹 → 选制程模板 → 点「自动报告」", SONG(18), NAVY, cy - 40)
    hline(d, W//2 - 100, cy + 10, W//2 + 100, color=NAVY, width=1)
    center_text(d, "功能与亮点  ·  操作教学  ·  制程与口径  ·  输出与注意", SONG(14), GRAY, cy + 46)
    d.text((MARGIN, H - 52), "v1.0  ·  内部使用", fill=GRAY, font=SONG(9), anchor='la')
    draw_pn(d, 13)
    return img


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
SLIDES = [
    ("第01页.png", s01_cover),
    ("第02页.png", s02_overview),
    ("第03页.png", s03_functions),
    ("第04页.png", s04_highlights),
    ("第05页.png", s05_flow),
    ("第06页.png", s06_ui_map),
    ("第07页.png", s07_process_table),
    ("第08页.png", s08_formulas),
    ("第09页.png", s09_gantt),
    ("第10页.png", s10_eff),
    ("第11页.png", s11_outputs),
    ("第12页.png", s12_tips),
    ("第13页.png", s13_closing),
]

if __name__ == "__main__":
    for filename, render_fn in SLIDES:
        print(f"Rendering {filename}...")
        img = render_fn()
        path = OUT_DIR / filename
        img.save(path, 'PNG')
        print(f"  -> {path} ({img.size[0]}×{img.size[1]})")
    print(f"\nDone. {len(SLIDES)} slides rendered to {OUT_DIR}/")
