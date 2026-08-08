"""
PIL-based slide renderer for MC Log Analysis usage deck.
Produces exact 1920×1080 PNG slides matching corporate_clear visual spec.
"""
import os, math
from PIL import Image, ImageDraw, ImageFont

# ── Canvas (exact 1920×1080) ────────────────────────
W, H = 1920, 1080
MARGIN = 112  # ~0.78in at 144dpi

# ── Colors ──────────────────────────────────────────
NAVY     = (8, 60, 99)        # #083C63
RED_ACC  = (239, 81, 73)      # #EF5149
LT_BLUE  = (222, 235, 247)    # #DEEBF7
WHITE    = (255, 255, 255)
DARK     = (51, 51, 51)
GRAY     = (128, 128, 128)
MID_GRAY = (100, 100, 100)
ALT_ROW  = (248, 250, 252)    # subtle alt row bg

# ── Fonts (point size → pixels at 144dpi → /72*144=×2) ──
FONT_BASE = '/System/Library/Fonts/Supplemental'
FONT_SYS  = '/System/Library/Fonts'

def _f(path, size_pt):
    return ImageFont.truetype(path, size_pt * 2)  # pt→px at 144dpi

# Chinese serif (宋体) — body text
SONG = lambda pt: _f(f'{FONT_BASE}/Songti.ttc', pt)
# Chinese sans (黑体) — titles
HEI  = lambda pt: _f(f'{FONT_SYS}/STHeiti Medium.ttc', pt)
HEI_L = lambda pt: _f(f'{FONT_SYS}/STHeiti Light.ttc', pt)
# Latin serif — English body & titles
TNR      = lambda pt: _f(f'{FONT_BASE}/Times New Roman.ttf', pt)
TNR_BOLD = lambda pt: _f(f'{FONT_BASE}/Times New Roman Bold.ttf', pt)

# ── Drawing helpers ─────────────────────────────────
def hline(draw, x1, y, x2, color=NAVY, width=2):
    draw.line([(x1, y), (x2, y)], fill=color, width=width)

def center_text(draw, text, font, fill, y, x_center=None):
    """Draw text centered horizontally."""
    if x_center is None:
        x_center = W // 2
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x_center - tw // 2, y), text, fill=fill, font=font, anchor='la')

def draw_pn(draw, n, total=13):
    """Page number bottom-right."""
    text = f"{n} / {total}"
    font = TNR(9)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((W - MARGIN - tw, H - 56), text, fill=GRAY, font=font, anchor='la')

def draw_fn(draw, text):
    """Footnote/source bottom-left."""
    draw.text((MARGIN, H - 56), text, fill=GRAY, font=SONG(9), anchor='la')

def draw_chapter_tag(draw, text, x=MARGIN, y=22):
    """Small red chapter label above title."""
    draw.text((x, y), text, fill=RED_ACC, font=SONG(10), anchor='la')

# ══════════════════════════════════════════════════════
#  SLIDE 01 — COVER
# ══════════════════════════════════════════════════════
def render_slide_01():
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)

    cy = H // 2  # vertical center

    # Red accent line
    lw = 220
    ly = cy - 170
    hline(d, W//2 - lw//2, ly, W//2 + lw//2, color=RED_ACC, width=3)

    # Main title
    center_text(d, "MC Log Analysis", TNR_BOLD(54), NAVY, ly + 42)

    # Subtitle
    center_text(d, "机台日志分析工具 · 使用说明", SONG(18), DARK, ly + 130)

    # Navy separator
    sep_y = ly + 175
    hline(d, W//2 - lw//2, sep_y, W//2 + lw//2, color=NAVY, width=1)

    # Navigation
    center_text(d, "功能与亮点  ·  操作教学  ·  制程与口径  ·  输出与注意", SONG(14), MID_GRAY, sep_y + 36)

    # Version (bottom-left)
    d.text((MARGIN, H - 56), "v1.0  ·  内部使用", fill=GRAY, font=SONG(9), anchor='la')

    draw_pn(d, 1)
    return img


# ══════════════════════════════════════════════════════
#  SLIDE 08 — UPH CALCULATION LOGIC
# ══════════════════════════════════════════════════════
def render_slide_08():
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # ── Header ──
    draw_chapter_tag(d, "第3章  制程与口径")
    d.text((MARGIN, 46), "UPH 口径：实际、Pure、Derated M1/M2 与有效 UPH",
           fill=NAVY, font=HEI(24), anchor='la')
    hline(d, MARGIN, 98, W - MARGIN, color=NAVY, width=1)

    # ── Conclusion ──
    d.text((MARGIN, 116), "实际 UPH 看真实产出，Pure 看理想节拍，Derated 剔离群点，有效 UPH 把换盘时间摊进单颗",
           fill=MID_GRAY, font=SONG(14), anchor='la')

    # ── Five formula rows ──
    formulas = [
        ("实际 UPH",    "= 产出数 ÷ 统计时长 × 3600",                              "按真实产出与统计时长计算。"),
        ("Pure UPH",    "= 3600 × 每周期产出 ÷ 理想周期CT",                        "未填理想 CT 时取正常周期平均。"),
        ("Derated UPH M2", "= 3600 × 每周期产出 ÷ 有效平均周期",                   "剔除离群点（<0.9×理想CT、>1.1×最大理论CT）；多模组整机 = 各模组 M2 之和。"),
        ("Derated UPH M1", "= EM 投入数 ÷ RUN 时长",                               "多模组整机 = 各模组 M1 之和。"),
        ("有效 UPH",    "= 3600 × 每周期产出 ÷（基础周期 + 每颗换盘开销）",         "每颗换盘开销 = 单次换盘时间 ÷ 每盘颗数。"),
    ]

    row_h = 68
    row_start_y = 160
    name_x = MARGIN + 12
    eq_x = MARGIN + 268
    detail_x = MARGIN + 268

    for i, (name, eq, detail) in enumerate(formulas):
        y = row_start_y + i * row_h

        # Alternating row background
        if i % 2 == 0:
            d.rectangle([(MARGIN, y - 2), (W - MARGIN, y + row_h - 4)], fill=ALT_ROW)

        # Formula name — navy bold
        d.text((name_x, y + 6), name, fill=NAVY, font=HEI(15), anchor='la')

        # Equation text
        d.text((eq_x, y + 6), eq, fill=DARK, font=SONG(13), anchor='la')

        # Detail line (smaller, gray)
        d.text((detail_x, y + 36), detail, fill=MID_GRAY, font=SONG(11), anchor='la')

    # ── Period classification ──
    class_y = row_start_y + 5 * row_h + 12
    d.text((name_x, class_y),
           "周期分类：间隔 > 计划性停机阈值 → 计划性停机；> 正常周期阈值 → 异常周期；其余为正常周期。",
           fill=MID_GRAY, font=SONG(11), anchor='la')

    # ── Swap example card ──
    card_x1 = MARGIN + 8
    card_y1 = class_y + 42
    card_x2 = W - MARGIN - 8
    card_y2 = H - MARGIN - 24

    d.rectangle([(card_x1, card_y1), (card_x2, card_y2)], fill=LT_BLUE, outline=(180, 200, 220), width=1)

    # Card title
    d.text((card_x1 + 24, card_y1 + 18), "换盘分摊示例（LM）", fill=NAVY, font=HEI(15), anchor='la')

    # Example data — two columns
    ex_x = card_x1 + 24
    ex_y = card_y1 + 48
    ex_font = SONG(13)
    ex_data = [
        ("单次换盘（下料 → 新盘上料）", "15.46 秒"),
        ("每盘颗数", "24 颗"),
        ("每颗换盘开销", "15.46 ÷ 24 ≈ 0.64 秒"),
        ("有效周期", "1.65 + 0.64 ≈ 2.29 秒"),
        ("Pure UPH", "≈ 1570 / 小时"),
    ]
    for j, (label, val) in enumerate(ex_data):
        ly = ex_y + j * 28
        d.text((ex_x, ly), label, fill=DARK, font=ex_font, anchor='la')
        # Right-align the value
        val_bbox = d.textbbox((0, 0), val, font=ex_font)
        vw = val_bbox[2] - val_bbox[0]
        d.text((card_x2 - 24 - vw, ly), val, fill=NAVY, font=ex_font, anchor='la')
        # Connector dots between label and value
        if j == 0:
            dots_x = ex_x + d.textbbox((0, 0), label, font=ex_font)[2] + 12
            dots_w = card_x2 - 24 - vw - dots_x - 12
            if dots_w > 20:
                dot_str = "· · · · · · · · · · · · · · · · · · ·"
                d.text((dots_x, ly), dot_str, fill=(180, 200, 220), font=SONG(9), anchor='la')

    # ── Footer ──
    draw_fn(d, "UPH 口径按 CoreTech AME 定义；换盘示例数值为说明用途")
    draw_pn(d, 8)

    return img


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
if __name__ == '__main__':
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '页面图片')
    os.makedirs(out_dir, exist_ok=True)

    for fn, render_fn in [("第01页.png", render_slide_01), ("第08页.png", render_slide_08)]:
        print(f"Rendering {fn}...")
        img = render_fn()
        path = os.path.join(out_dir, fn)
        img.save(path, 'PNG')
        print(f"  -> {path} ({img.size[0]}×{img.size[1]})")

    print("Done. Two sample slides ready.")
