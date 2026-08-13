#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PIL 视觉稿渲染器：3 版完整拼图 + 逐页高清（规格 JSON 驱动）。

用法：
  python render_mockups.py --spec spec.json --out-dir out --mode collages
  python render_mockups.py --spec spec.json --out-dir out --mode hd --theme C
  python render_mockups.py --spec spec.json --out-dir out --mode all

规格结构见 examples/spec.example.json：
  - pages: cover / bar_table / pie_table / pareto_table / line_full
  - 每页: index, title, subtitle, icon, 以及对应类型的图表/表格字段
  - 全局: tag（页头标签）, copyright（页脚版权）

要点：
  - 文字用 PIL 代码直出，保证中文与数字准确（不要用 AI 生图做这类拼图）。
  - 内置 3 套视觉方向主题（A 企业深蓝 / B 浅色科技 / C 深色驾驶舱），
    每套内部统一字体/色彩/背景/图表/图标/卡片/页脚页码系统。
"""

from __future__ import annotations

import argparse
import json
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HI_GB = "/System/Library/Fonts/Hiragino Sans GB.ttc"
HI_GB_ALT = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]


def _font_path():
    for p in [HI_GB] + HI_GB_ALT:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("未找到可用中文字体")


FP = _font_path()
SCALE = 1.0
SCALE_Y = None


def F(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    idx = 2 if bold and FP.endswith("Hiragino Sans GB.ttc") else 0
    return ImageFont.truetype(FP, max(1, round(size * SCALE)), index=idx)


def _sy() -> float:
    return SCALE_Y if SCALE_Y is not None else SCALE


def hx(c: str) -> tuple:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    a, b = hx(c1), hx(c2)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(size, top: str, bot: str):
    w, h = size
    mask = Image.linear_gradient("L").resize((1, h))
    top_img = Image.new("RGB", (1, h), top)
    bot_img = Image.new("RGB", (1, h), bot)
    return Image.composite(bot_img, top_img, mask).resize((w, h))


class SD:
    """带缩放包装的 ImageDraw：坐标/宽度按 SCALE 放大，textlength 返回基准单位。"""

    def __init__(self, d):
        self.d = d
        self.sx = SCALE
        self.sy = _sy()

    def _box(self, b):
        return (b[0] * self.sx, b[1] * self.sy, b[2] * self.sx, b[3] * self.sy)

    def _xy(self, xy):
        return (xy[0] * self.sx, xy[1] * self.sy)

    def _pts(self, seq):
        out = []
        for it in seq:
            if isinstance(it, (list, tuple)) and len(it) == 2:
                out.append((it[0] * self.sx, it[1] * self.sy))
            else:
                out.append(it)
        return out

    def _w(self, w):
        return max(1, round(w * self.sx)) if w else w

    def text(self, xy, text, font=None, fill=None, anchor=None):
        self.d.text(self._xy(xy), text, font=font, fill=fill, anchor=anchor)

    def textlength(self, text, font=None, **kw):
        return self.d.textlength(text, font=font, **kw) / self.sx

    def line(self, xy, fill=None, width=1, joint=None):
        self.d.line(self._pts(xy), fill=fill, width=self._w(width), joint=joint)

    def rectangle(self, xy, fill=None, outline=None, width=1):
        self.d.rectangle(self._box(xy), fill=fill, outline=outline, width=self._w(width))

    def rounded_rectangle(self, xy, radius=0, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._box(xy), radius=radius * self.sx,
                                 fill=fill, outline=outline, width=self._w(width))

    def pieslice(self, xy, start, end, fill=None, outline=None, width=1):
        self.d.pieslice(self._box(xy), start, end, fill=fill,
                        outline=outline, width=self._w(width))

    def ellipse(self, xy, fill=None, outline=None, width=1):
        self.d.ellipse(self._box(xy), fill=fill, outline=outline, width=self._w(width))

    def polygon(self, xy, fill=None, outline=None, width=1):
        self.d.polygon(self._pts(xy), fill=fill, outline=outline, width=self._w(width))

    def point(self, xy, fill=None):
        self.d.point(self._xy(xy), fill=fill)


def new_page():
    w = int(600 * SCALE + 0.5)
    h = int(338 * _sy() + 0.5)
    img = Image.new("RGB", (w, h))
    return img, SD(ImageDraw.Draw(img))


# ---------------- 三套视觉方向主题 ----------------

THEMES = {
    "A": {
        "name": "方案 A · Apple 浅色报告",
        "collage_bg": "#F2F2F7",
        "page_bg": "#FFFFFF",
        "panel_bg": "#F5F5F7",
        "panel_line": "#E5E5EA",
        "card_radius": 6,
        "shadow": False,
        "title": "#1D1D1F",
        "sub": "#86868B",
        "text": "#3A3A3C",
        "accent": "#007AFF",
        "chip_bg": "#F5F5F7",
        "chip_fg": "#007AFF",
        "tag_bg": "#F5F5F7",
        "tag_fg": "#007AFF",
        "table_header_bg": "#F9F9FB",
        "table_header_fg": "#1D1D1F",
        "table_row_alt": "#FAFAFA",
        "table_line": "#E5E5EA",
        "bar_colors": ["#007AFF", "#34C759", "#FF9F0A"],
        "bar_hl": "#FF3B30",
        "grid": "#EDEDF2",
        "axis": "#86868B",
        "pie_colors": ["#34C759", "#FF9F0A", "#FF3B30"],
        "line": "#007AFF",
        "line_area": "#E9F2FF",
        "line_hl": "#FF3B30",
        "footer_fg": "#86868B",
        "cover_top": "#F2F2F7",
        "cover_bot": "#FFFFFF",
        "cover_title": "#1D1D1F",
        "cover_sub": "#86868B",
        "cover_accent": "#007AFF",
        "icon_color": "#007AFF",
        "swatches": ["#007AFF", "#FF3B30", "#34C759"],
    },
    "B": {
        "name": "方案 B · 浅色科技仪表盘",
        "collage_bg": "#EAF1F1",
        "page_bg": "#F4F8F9",
        "panel_bg": "#FFFFFF",
        "panel_line": "#E3EBF1",
        "card_radius": 11,
        "shadow": True,
        "title": "#0F6E73",
        "sub": "#64748B",
        "text": "#243B40",
        "accent": "#F59E0B",
        "chip_bg": "#DFF1EF",
        "chip_fg": "#0F6E73",
        "tag_bg": "#FFFFFF",
        "tag_fg": "#0F6E73",
        "table_header_bg": "#DFF1EF",
        "table_header_fg": "#0F6E73",
        "table_row_alt": "#F6FAFA",
        "table_line": "#E8F0F0",
        "bar_colors": ["#0E8A8A", "#54B9AE", "#A9DDD6"],
        "bar_hl": "#F59E0B",
        "grid": "#E3ECEE",
        "axis": "#7E9499",
        "pie_colors": ["#0E8A8A", "#54B9AE", "#F2B24C"],
        "line": "#0E8A8A",
        "line_area": "#DDF0ED",
        "line_hl": "#F59E0B",
        "footer_fg": "#93A7AC",
        "cover_top": "#E6F5F2",
        "cover_bot": "#FDFEFE",
        "cover_title": "#0F6E73",
        "cover_sub": "#5F8388",
        "cover_accent": "#F59E0B",
        "icon_color": "#0E8A8A",
        "swatches": ["#0E8A8A", "#F59E0B", "#54B9AE"],
    },
    "C": {
        "name": "方案 C · 深色运营驾驶舱",
        "collage_bg": "#0A0F19",
        "page_bg": "#0D1524",
        "panel_bg": "#131E33",
        "panel_line": "#25344F",
        "card_radius": 2,
        "shadow": False,
        "title": "#E7F1FF",
        "sub": "#8FA3C4",
        "text": "#C6D3E8",
        "accent": "#F5B64C",
        "chip_bg": "#16233C",
        "chip_fg": "#35C6F4",
        "tag_bg": "#16233C",
        "tag_fg": "#35C6F4",
        "table_header_bg": "#1B2B47",
        "table_header_fg": "#8FD8F7",
        "table_row_alt": "#16233C",
        "table_line": "#22314D",
        "bar_colors": ["#35C6F4", "#1E6FA8", "#16324F"],
        "bar_hl": "#F5B64C",
        "grid": "#24334E",
        "axis": "#8FA3C4",
        "pie_colors": ["#35C6F4", "#2E86C1", "#F5B64C"],
        "line": "#35C6F4",
        "line_area": "#12233C",
        "line_hl": "#F5B64C",
        "footer_fg": "#5F7396",
        "cover_top": "#0A1020",
        "cover_bot": "#0E1A30",
        "cover_title": "#FFFFFF",
        "cover_sub": "#8FA3C4",
        "cover_accent": "#F5B64C",
        "icon_color": "#35C6F4",
        "swatches": ["#35C6F4", "#F5B64C", "#2E86C1"],
    },
}


# ---------------- 基础绘制 ----------------

def soft_card(img, d, box, t, radius=None):
    r = radius if radius is not None else t["card_radius"]
    if t["shadow"]:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ds = SD(ImageDraw.Draw(sh))
        x0, y0, x1, y1 = box
        ds.rounded_rectangle((x0, y0 + 5, x1, y1 + 5), radius=r, fill=(21, 48, 60, 26))
        sh = sh.filter(ImageFilter.GaussianBlur(5 * SCALE))
        img.paste(sh, (0, 0), sh)
    d.rounded_rectangle(box, radius=r, fill=t["panel_bg"],
                        outline=t["panel_line"], width=1)


def _frosted_card(img, d, box, t, radius=3):
    """磨砂玻璃半透明卡片：背景裁剪→高斯模糊→半透明白色叠加→描边+顶部高光。"""
    x0, y0, x1, y1 = box
    px0, py0 = round(x0 * SCALE), round(y0 * _sy())
    px1, py1 = round(x1 * SCALE), round(y1 * _sy())
    crop = img.crop((px0, py0, px1, py1))
    blurred = crop.filter(ImageFilter.GaussianBlur(max(3, round(4 * SCALE))))
    glass = blurred.convert("RGBA")
    white = hx("#FFFFFF")
    alpha = 110 if t["name"].startswith("方案 C") else 150
    tint = Image.new("RGBA", glass.size, (*white, alpha))
    glass = Image.alpha_composite(glass, tint)
    img.paste(glass.convert("RGB"), (px0, py0))
    d.rounded_rectangle(box, radius=radius, outline=t["panel_line"], width=1)
    d.line([(x0 + 6, y0 + 1), (x1 - 6, y0 + 1)],
           fill=mix("#FFFFFF", t["panel_bg"], 0.30), width=1)


def brackets(d, box, color="#35C6F4", l=9, w=2):
    x0, y0, x1, y1 = box
    for x, y, dx, dy in (
        (x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1),
    ):
        d.line([(x, y), (x + dx * l, y)], fill=color, width=w)
        d.line([(x, y), (x, y + dy * l)], fill=color, width=w)


def hrule(d, x0, x1, y, color, w=2):
    d.line([(x0, y), (x1, y)], fill=color, width=w)


def pill(d, x, y, w, h, label, t, size=9):
    font = F(size, True)
    d.rounded_rectangle((x, y, x + w, y + h), radius=h / 2, fill=t["chip_bg"])
    d.text((x + w / 2, y + h / 2), label, font=font, fill=t["chip_fg"], anchor="mm")


def tag(d, x0, y, label, t, h=18):
    font = F(9, True)
    w = d.textlength(label, font=font) + 14
    d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=t["tag_bg"])
    d.text((x0 + 7, y + h / 2), label, font=font, fill=t["tag_fg"], anchor="lm")
    return x0 + w


def footer(d, img, idx, t, total, copyright_text):
    d.line([(24, 312), (576, 312)], fill=t["table_line"] if t["shadow"] else t["grid"],
           width=1)
    d.text((24, 321), copyright_text, font=F(8), fill=t["footer_fg"], anchor="lm")
    d.text((576, 321), f"{idx}/{total}", font=F(9, True), fill=t["accent"], anchor="rm")


def page_bg(img, d, t):
    img.paste(hx(t["page_bg"]), (0, 0, img.width, img.height))
    if t["name"].startswith("方案 C"):
        for x in range(24, 600, 74):
            d.line([(x, 0), (x, 338)], fill="#101C31", width=1)
        for y in range(0, 338, 74):
            d.line([(0, y), (600, y)], fill="#101C31", width=1)


def section_header(d, img, idx, title, sub, t, icon, tag_text, total):
    page_bg(img, d, t)
    tx = tag(d, 24, 15, tag_text, t) + 8
    ICONS[icon](d, tx, 17, t["icon_color"])
    d.text((tx + 20, 16), title, font=F(25, True), fill=t["title"], anchor="la")
    pill(d, 576 - 92, 16, 92, 18, f"{idx:02d} / {total:02d}", t)
    d.text((24, 55), sub, font=F(11), fill=t["sub"], anchor="la")
    if not t["shadow"] and not t["name"].startswith("方案 C"):
        hrule(d, 24, 576, 72, t["title"], w=2)
    footer(d, img, idx, t, total, COPYRIGHT)


# ---------------- 图标（统一线性风格，随主题换色） ----------------

def icon_chart(d, x, y, color, s=15):
    d.rectangle([x + 1, y + s - 6, x + 4, y + s - 1], fill=color)
    d.rectangle([x + 6, y + s - 10, x + 9, y + s - 1], fill=color)
    d.rectangle([x + 11, y + s - 4, x + 14, y + s - 1], fill=color)


def icon_clock(d, x, y, color, s=15):
    d.ellipse([x + 1, y + 1, x + s - 1, y + s - 1], outline=color, width=1)
    d.line([(x + s / 2, y + s / 2), (x + s / 2, y + 4)], fill=color, width=1)
    d.line([(x + s / 2, y + s / 2), (x + s - 4, y + s / 2 + 2)], fill=color, width=1)


def icon_alert(d, x, y, color, s=15):
    d.polygon([(x + s / 2, y + 1), (x + s - 1, y + s - 1), (x + 1, y + s - 1)],
              outline=color, width=1)
    d.line([(x + s / 2, y + 6), (x + s / 2, y + 9)], fill=color, width=1)
    d.point((x + s / 2, y + 11), fill=color)


def icon_trend(d, x, y, color, s=15):
    d.line([(x + 1, y + s - 2), (x + 5, y + s - 7), (x + 9, y + s - 4), (x + s - 1, y + 1)],
           fill=color, width=1)
    d.line([(x + 10, y + 1), (x + s - 1, y + 1), (x + s - 1, y + 10)], fill=color, width=1)


def icon_pie(d, x, y, color, s=15):
    d.ellipse([x + 1, y + 1, x + s - 1, y + s - 1], outline=color, width=1)
    d.line([(x + s / 2, y + s / 2), (x + s / 2, y + 1)], fill=color, width=1)
    d.line([(x + s / 2, y + s / 2), (x + s - 1, y + s / 2)], fill=color, width=1)


def icon_pareto(d, x, y, color, s=15):
    for i, hgt in enumerate((4, 8, 12)):
        d.rectangle([x + 1 + i * 4, y + s - hgt - 1, x + 4 + i * 4, y + s - 1],
                    outline=color, width=1)


ICONS = {
    "chart": icon_chart,
    "clock": icon_clock,
    "alert": icon_alert,
    "trend": icon_trend,
    "pie": icon_pie,
    "pareto": icon_pareto,
}


# ---------------- 图表 ----------------

def _wrap_label(d, text, font, max_w):
    """按像素宽度自动换行（中英文混排），返回行列表。"""
    lines = []
    cur = ""
    for ch in str(text):
        trial = cur + ch
        if cur and d.textlength(trial, font=font) > max_w:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


def bar_chart(d, box, title, labels, values, t, hl=None, y_max=None):
    x0, y0, x1, y1 = box
    d.text((x0, y0 + 2), title, font=F(10, True), fill=t["title"], anchor="la")
    py0, py1 = y0 + 20, y1 - 38  # 底部预留 3 行标签空间
    maxv = (max(values) * 1.15) if y_max is None else y_max
    for gy in (py0, py0 + (py1 - py0) * 0.5, py1):
        d.line([(x0, gy), (x1, gy)], fill=t["grid"], width=1)
    n = len(values)
    bw = (x1 - x0) / n
    barw = bw * 0.46
    palette = t["bar_colors"]
    for i, (lab, v) in enumerate(zip(labels, values)):
        cx = x0 + bw * (i + 0.5)
        bh = (v / maxv) * (py1 - py0 - 4)
        bx0 = cx - barw / 2
        by0 = py1 - bh
        col = t["bar_hl"] if (hl is not None and i == hl) else palette[i % len(palette)]
        d.rounded_rectangle([bx0, by0, bx0 + barw, py1], radius=2, fill=col)
        val = f"{v:,.0f}" if v >= 100 else f"{v:.1f}"
        label_fill = col if t["name"].startswith("方案 C") else t["text"]
        d.text((cx, by0 - 9), val, font=F(8, True), fill=label_fill, anchor="ma")
        # 横轴标签过长时自动换行（最多 3 行，超出省略）
        lines = _wrap_label(d, lab, F(8), max(bw * 0.9, 42))
        if len(lines) > 3:
            lines = lines[:3]
            lines[-1] = lines[-1][:-1] + "…"
        for k, ln in enumerate(lines[:3]):
            d.text((cx, py1 + 8 + k * 10), ln, font=F(8), fill=t["axis"],
                   anchor="ma")
    d.line([(x0, py1), (x1, py1)], fill=t["axis"], width=1)


def hbar_chart(d, box, title, rows, t, label_w=150):
    """横向条形图：标签在左侧可自动换行，数值在右侧（用于报警分析等长名称场景）。"""
    x0, y0, x1, y1 = box
    d.text((x0, y0 + 2), title, font=F(10, True), fill=t["title"], anchor="la")
    py0, py1 = y0 + 20, y1 - 4
    maxv = max(v for _, v in rows)
    rh = (py1 - py0) / len(rows)
    bar_x0 = x0 + label_w
    value_font = F(8, True)
    for i, (lab, v) in enumerate(rows):
        cy = py0 + rh * (i + 0.5)
        col = t["bar_hl"] if i == 0 else t["bar_colors"][i % len(t["bar_colors"])]
        bend = bar_x0 + (v / maxv) * (x1 - bar_x0 - 52)
        d.rounded_rectangle([bar_x0, cy - 8, bend, cy + 8], radius=3, fill=col)
        lines = _wrap_label(d, lab, F(8), label_w - 6)
        for k, ln in enumerate(lines[:2]):
            d.text((x0, cy - 5 + k * 11), ln, font=F(8), fill=t["text"],
                   anchor="lm")
        d.text((x1, cy), f"{v:,}", font=value_font, fill=t["text"], anchor="rm")


def pareto_chart(d, box, title, rows, t, top3=False):
    x0, y0, x1, y1 = box
    d.text((x0, y0 + 2), title, font=F(10, True), fill=t["title"], anchor="la")
    py0, py1 = y0 + 22, y1 - 4
    maxv = max(r[1] for r in rows)
    rh = (py1 - py0) / len(rows)
    value_font = F(8, True)
    if top3:
        distinct = sorted({r[1] for r in rows}, reverse=True)
        threshold = distinct[2] if len(distinct) >= 3 else (distinct[-1] if distinct else 0)
    for i, row in enumerate(rows):
        lab, v = row[0], row[1]
        pct = row[2] if len(row) > 2 else None
        cy = py0 + rh * (i + 0.5)
        if top3:
            col = t["bar_hl"] if v >= threshold else "#FFB4AB"
            label_fill = "#FFFFFF" if v >= threshold else t["text"]
        else:
            col = t["bar_hl"] if i == 0 else t["bar_colors"][1 % len(t["bar_colors"])]
            label_fill = "#FFFFFF"
        bend = x0 + (v / maxv) * (x1 - x0)
        d.rounded_rectangle([x0, cy - 8, bend, cy + 8], radius=3, fill=col)
        value_txt = f"{v:,.0f}s · {pct}%" if pct is not None else f"{v:,}"
        value_w = d.textlength(value_txt, font=value_font)
        single = _wrap_label(d, lab, value_font, 999)
        fits_inside = (bend - x0) > 48 and len(single) == 1
        if fits_inside:
            d.text((x0 + 8, cy), lab, font=value_font, fill=label_fill, anchor="lm")
        else:
            max_w = max(60, (x1 - 6) - (bend + 6) - value_w - 8)
            lines = _wrap_label(d, lab, value_font, max_w)
            for k, ln in enumerate(lines[:2]):
                d.text((bend + 6, cy - 5 + k * 11), ln, font=value_font,
                       fill=t["text"], anchor="lm")
        d.text((x1, cy), value_txt, font=value_font, fill=t["text"], anchor="rm")


def pie_chart(d, box, title, slices, t, doughnut=False):
    x0, y0, x1, y1 = box
    d.text((x0, y0 + 2), title, font=F(10, True), fill=t["title"], anchor="la")
    cy = (y0 + 20 + y1) / 2
    r = min(58, (y1 - y0 - 24) / 2.4)
    cx = x0 + 58
    total = sum(v for _, v in slices)
    start = -90.0
    colors = t["pie_colors"]
    for i, (lab, v) in enumerate(slices):
        ang = 360.0 * v / total
        col = colors[i % len(colors)]
        if t["name"].startswith("方案 C"):
            d.pieslice((cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3),
                       start, start + ang, fill=mix(col, "#0D1524", 0.45))
        d.pieslice((cx - r, cy - r, cx + r, cy + r), start, start + ang,
                   fill=col, outline=t["page_bg"], width=2)
        start += ang
    if doughnut:
        d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55),
                  fill=t["panel_bg"])
    lx = cx + r + 14
    for i, (lab, v) in enumerate(slices):
        ly = y0 + 22 + i * 20
        col = colors[i % len(colors)]
        d.rounded_rectangle([lx, ly, lx + 9, ly + 9], radius=2, fill=col)
        d.text((lx + 15, ly + 4), f"{lab}  {v / total * 100:.1f}%", font=F(9),
               fill=t["text"], anchor="lm")


def line_chart(d, box, title, values, t, xlabels):
    x0, y0, x1, y1 = box
    d.text((x0, y0 + 2), title, font=F(10, True), fill=t["title"], anchor="la")
    py0, py1 = y0 + 20, y1 - 22
    vmin, vmax = 96.8, 100.2
    for gy, gv in ((py0, 100), (py0 + (py1 - py0) / 2, 98.5), (py1, 97)):
        d.line([(x0, gy), (x1, gy)], fill=t["grid"], width=1)
        d.text((x0 - 4, gy), f"{gv}", font=F(7), fill=t["axis"], anchor="rm")
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        px = x0 + (x1 - x0) * i / (n - 1)
        py = py1 - (v - vmin) / (vmax - vmin) * (py1 - py0)
        pts.append((px, py))
    d.polygon([(x0, py1)] + pts + [(x1, py1)], fill=t["line_area"])
    d.line(pts, fill=t["line"], width=2, joint="curve")
    for i, (px, py) in enumerate(pts):
        if i % 4 == 0:
            d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=t["line"])
    imin = min(range(n), key=lambda i: values[i])
    imax = max(range(n), key=lambda i: values[i])
    for i in (imin, imax):
        px, py = pts[i]
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=t["line_hl"],
                  outline=t["page_bg"], width=1)
        d.text((px, py - 12), f"{values[i]:.2f}", font=F(8, True),
               fill=t["line_hl"], anchor="ma")
    for xlab, idx in xlabels:
        px = x0 + (x1 - x0) * idx / (n - 1)
        d.text((px, y1 - 12), xlab, font=F(8), fill=t["axis"], anchor="ma")


# ---------------- 表格 ----------------

def table(d, box, t, header, rows, col_weights=None):
    x0, y0, x1, y1 = box
    if col_weights is None:
        col_weights = [1.0] * len(header)
    total_w = sum(col_weights)
    n = len(rows) + 1
    rh = min((y1 - y0) / n, 24)
    total_h = rh * n
    if total_h < (y1 - y0) * 0.72:
        y0 += ((y1 - y0) - total_h) / 2
    y1 = y0 + total_h
    cols = []
    cx = x0
    for w in col_weights:
        cols.append((cx, cx + (x1 - x0) * w / total_w))
        cx += (x1 - x0) * w / total_w
    hf = F(8.5, True)
    bf = F(8.5)
    d.rectangle([x0, y0, x1, y0 + rh], fill=t["table_header_bg"])
    for ci, htxt in enumerate(header):
        align = "lm" if ci == 0 else "rm"
        d.text((cols[ci][0] + 8, y0 + rh / 2), htxt, font=hf,
               fill=t["table_header_fg"], anchor=align)
    for ri, row in enumerate(rows):
        ry = y0 + rh * (ri + 1)
        if ri % 2 == 1:
            d.rectangle([x0, ry, x1, ry + rh], fill=t["table_row_alt"])
        for ci, val in enumerate(row):
            align = "lm" if ci == 0 else "rm"
            d.text((cols[ci][0] + 8, ry + rh / 2), val, font=bf,
                   fill=t["text"], anchor=align)
        d.line([(x0, ry), (x1, ry)], fill=t["table_line"], width=1)
    d.line([(x0, y0 + rh), (x1, y0 + rh)], fill=t["table_line"], width=1)
    d.rounded_rectangle([x0, y0, x1, y0 + rh * n], radius=2,
                        outline=t["panel_line"], width=1)


# ---------------- 页面渲染（规格驱动） ----------------

COPYRIGHT = "© 2026 Hon Hai Precision Industry Co., Ltd. All rights reserved."


def page_cover(t, p):
    img, d = new_page()
    img.paste(vgrad((int(600 * SCALE + 0.5), int(338 * _sy() + 0.5)),
                    t["cover_top"], t["cover_bot"]), (0, 0))
    if t["name"].startswith("方案 C"):
        for x in range(24, 600, 74):
            d.line([(x, 0), (x, 338)], fill="#101C31", width=1)
        for y in range(0, 338, 74):
            d.line([(0, y), (600, y)], fill="#101C31", width=1)
        brackets(d, (18, 18, 582, 320))
    elif t["shadow"]:
        d.ellipse([400, -90, 620, 130], fill=mix(t["cover_top"], "#FFFFFF", 0.10))
        d.ellipse([-80, 250, 120, 450], fill=mix(t["cover_top"], "#FFFFFF", 0.08))
    d.rectangle([24, 148, 60, 154], fill=t["cover_accent"])
    d.text((24, 178), p["title"], font=F(32, True), fill=t["cover_title"], anchor="la")
    d.text((24, 228), p.get("subtitle", ""), font=F(16), fill=t["cover_sub"], anchor="la")
    d.line([(24, 312), (576, 312)], fill=mix(t["cover_sub"], t["cover_bot"], 0.5),
           width=1)
    d.text((24, 321), COPYRIGHT, font=F(8), fill=mix(t["cover_sub"], t["cover_bot"], 0.4),
           anchor="lm")
    d.text((576, 321), f"1/{TOTAL}", font=F(9, True), fill=t["cover_accent"],
           anchor="rm")
    kpis = p.get("kpis")
    if kpis:
        gap = 10
        cw = (576 - 24 - 24 - gap * (len(kpis) - 1)) / len(kpis)
        for i, (lab, val) in enumerate(kpis):
            x0 = 24 + i * (cw + gap)
            _frosted_card(img, d, (x0, 250, x0 + cw, 294), t)
            d.text((x0 + cw / 2, 265), val, font=F(16, True),
                   fill=t["cover_accent"], anchor="mm")
            d.text((x0 + cw / 2, 285), lab, font=F(8),
                   fill=t["cover_sub"], anchor="mm")
    return img


def _module(d, img, t, box):
    soft_card(img, d, box, t)
    if t["name"].startswith("方案 C"):
        brackets(d, box)


def _right_table(d, img, t, header, rows, weights):
    _module(d, img, t, (342, 80, 582, 306))
    table(d, (350, 86, 574, 300), t, header, rows, weights)


def page_bar_table(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "chart"), TAG, TOTAL)
    if p.get("layout") == "tb":
        # 上下分布：上层柱状图（全宽），下层表格（全宽）
        _module(d, img, t, (18, 80, 582, 200))
        bar_chart(d, (30, 92, 570, 196), p["chart_title"], p["labels"],
                  p["values"], t, hl=p.get("highlight"), y_max=p.get("chart_y_max"))
        _module(d, img, t, (18, 210, 582, 306))
        table(d, (26, 216, 574, 300), t, p["table_header"], p["table_rows"],
              p.get("col_weights"))
        return img
    _module(d, img, t, (18, 80, 330, 306))
    bar_chart(d, (30, 110, 318, 298), p["chart_title"], p["labels"], p["values"],
              t, hl=p.get("highlight"), y_max=p.get("chart_y_max"))
    _right_table(d, img, t, p["table_header"], p["table_rows"], p.get("col_weights"))
    return img


def page_pie_table(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "pie"), TAG, TOTAL)
    _module(d, img, t, (18, 80, 330, 306))
    pie_chart(d, (30, 110, 318, 298), p["chart_title"], p["slices"], t,
              doughnut=t["shadow"])
    _right_table(d, img, t, p["table_header"], p["table_rows"], p.get("col_weights"))
    return img


def page_pareto_table(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "pareto"), TAG, TOTAL)
    _module(d, img, t, (18, 80, 330, 306))
    pareto_chart(d, (30, 110, 318, 298), p["chart_title"], p["rows"], t)
    _right_table(d, img, t, p["table_header"], p["table_rows"], p.get("col_weights"))
    return img


def page_hbar_table(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "alert"), TAG, TOTAL)
    _module(d, img, t, (18, 80, 330, 306))
    hbar_chart(d, (30, 110, 318, 298), p["chart_title"], p["rows"], t)
    _right_table(d, img, t, p["table_header"], p["table_rows"], p.get("col_weights"))
    return img


def page_pareto_full(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "pareto"), TAG, TOTAL)
    _module(d, img, t, (18, 80, 582, 306))
    pareto_chart(d, (30, 110, 570, 298), p["chart_title"], p["rows"], t,
                 top3=p.get("top3", False))
    return img


def page_hbar_full(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "alert"), TAG, TOTAL)
    _module(d, img, t, (18, 80, 582, 306))
    hbar_chart(d, (30, 110, 570, 298), p["chart_title"], p["rows"], t, label_w=270)
    return img


def page_line_full(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "trend"), TAG, TOTAL)
    _module(d, img, t, (18, 80, 582, 306))
    line_chart(d, (30, 110, 570, 298), p["chart_title"], p["values"],
               t, p.get("x_labels", []))
    return img


# ---------------- 说明书通用内容页(卡片/流程/表格/列表/问答/命令) ----------------

CONTENT_DEFAULT_H = {
    "cards3": 118, "cards2": 118, "flow": 66, "table": 214,
    "bullets": 200, "qa": 208, "grid6": 216, "cmd": 150,
    "warning3": 118,
}


def _content_block(d, img, t, box, block):
    kind = block.get("kind")
    x0, y0, x1, y1 = box
    if kind in ("cards3", "cards2"):
        cards = block.get("cards", [])
        n = len(cards)
        gap = 10
        w = (x1 - x0 - gap * (n - 1)) / n
        for i, c in enumerate(cards):
            cx0 = x0 + i * (w + gap)
            _module(d, img, t, (cx0, y0, cx0 + w, y1))
            d.text((cx0 + 10, y0 + 12), c.get("title", ""),
                   font=F(12, True), fill=t["title"], anchor="la")
            d.line([(cx0 + 10, y0 + 30), (cx0 + w - 10, y0 + 30)],
                   fill=t["accent"], width=1)
            ly = y0 + 40
            for line in c.get("lines", []):
                d.text((cx0 + 10, ly), line, font=F(8), fill=t["text"],
                       anchor="la")
                ly += 14
    elif kind == "flow":
        steps = block.get("steps", [])
        n = len(steps)
        gap = 28
        w = (x1 - x0 - gap * (n - 1)) / n
        for i, s in enumerate(steps):
            cx = x0 + w * (i + 0.5)
            cy = (y0 + y1) / 2 - 6
            d.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=t["accent"])
            d.text((cx, cy), str(i + 1), font=F(13, True), fill="#FFFFFF",
                   anchor="mm")
            d.text((cx, cy + 24), s.get("title", ""), font=F(10, True),
                   fill=t["title"], anchor="ma")
            d.text((cx, cy + 41), s.get("text", ""), font=F(8),
                   fill=t["sub"], anchor="ma")
            if i < n - 1:
                d.line([(cx + 19, cy), (cx + w + gap - 19, cy)],
                       fill=t["grid"], width=1)
    elif kind == "table":
        _module(d, img, t, (x0, y0, x1, y1))
        table(d, (x0 + 8, y0 + 8, x1 - 8, y1 - 8), t,
              block["header"], block.get("rows", []),
              block.get("col_weights"))
    elif kind == "bullets":
        _module(d, img, t, (x0, y0, x1, y1))
        ly = y0 + 14
        for item in block.get("items", []):
            lead, rest = item
            d.text((x0 + 16, ly), "▪", font=F(10, True),
                   fill=t["accent"], anchor="la")
            if lead:
                d.text((x0 + 30, ly), lead, font=F(10, True),
                       fill=t["title"], anchor="la")
                lw = d.textlength(lead, font=F(10, True))
                d.text((x0 + 32 + lw, ly), rest, font=F(9),
                       fill=t["text"], anchor="la")
            else:
                d.text((x0 + 30, ly), rest, font=F(9), fill=t["text"],
                       anchor="la")
            ly += 17
    elif kind == "qa":
        _module(d, img, t, (x0, y0, x1, y1))
        ly = y0 + 12
        for q, a in block.get("items", []):
            d.text((x0 + 14, ly), "Q", font=F(10, True),
                   fill=t["accent"], anchor="la")
            d.text((x0 + 30, ly), q, font=F(10, True),
                   fill=t["title"], anchor="la")
            ly += 15
            d.text((x0 + 30, ly), "A  " + a, font=F(9), fill=t["text"],
                   anchor="la")
            ly += 15
    elif kind == "grid6":
        cards = block.get("cards", [])
        n = len(cards)
        cols = 3
        rows = math.ceil(n / cols)
        gap = 10
        cw = (x1 - x0 - gap * (cols - 1)) / cols
        ch = (y1 - y0 - gap * (rows - 1)) / rows
        for i, c in enumerate(cards):
            r, col = divmod(i, cols)
            cx0 = x0 + col * (cw + gap)
            cy0 = y0 + r * (ch + gap)
            _module(d, img, t, (cx0, cy0, cx0 + cw, cy0 + ch))
            d.text((cx0 + 8, cy0 + 6), c.get("title", ""), font=F(9, True),
                   fill=t["title"], anchor="la")
            d.text((cx0 + 8, cy0 + 20), c.get("text", ""), font=F(8),
                   fill=t["text"], anchor="la")
    elif kind == "cmd":
        _module(d, img, t, (x0, y0, x1, y1))
        d.rounded_rectangle([x0 + 10, y0 + 8, x1 - 10, y1 - 8], radius=4,
                            fill=t["chip_bg"])
        ly = y0 + 24
        for line in block.get("lines", []):
            d.text((x0 + 24, ly), line, font=F(9), fill=t["chip_fg"],
                   anchor="la")
            ly += 16
    elif kind == "warning3":
        cards = block.get("cards", [])
        n = len(cards)
        gap = 10
        w = (x1 - x0 - gap * (n - 1)) / n
        for i, c in enumerate(cards):
            cx0 = x0 + i * (w + gap)
            _module(d, img, t, (cx0, y0, cx0 + w, y1))
            d.polygon([(cx0 + 16, y0 + 14), (cx0 + 25, y0 + 33),
                       (cx0 + 7, y0 + 33)], fill=t["accent"])
            d.text((cx0 + 14, y0 + 42), c.get("title", ""), font=F(10, True),
                   fill=t["title"], anchor="la")
            d.text((cx0 + 14, y0 + 58), c.get("text", ""), font=F(8),
                   fill=t["text"], anchor="la")


def page_content(t, p):
    img, d = new_page()
    section_header(d, img, p["index"], p["title"], p["subtitle"], t,
                   p.get("icon", "chart"), TAG, TOTAL)
    y = 84
    for block in p.get("blocks", []):
        h = block.get("h") or CONTENT_DEFAULT_H.get(block.get("kind"), 100)
        if y + h > 304:
            h = 304 - y
        _content_block(d, img, t, (18, y, 582, min(y + h, 304)), block)
        y += h + 8
    return img


def page_closing(t, p):
    img, d = new_page()
    img.paste(vgrad((int(600 * SCALE + 0.5), int(338 * _sy() + 0.5)),
                    t["cover_top"], t["cover_bot"]), (0, 0))
    if t["name"].startswith("方案 C"):
        for x in range(24, 600, 74):
            d.line([(x, 0), (x, 338)], fill="#101C31", width=1)
        for y in range(0, 338, 74):
            d.line([(0, y), (600, y)], fill="#101C31", width=1)
        brackets(d, (18, 18, 582, 320))
    d.rectangle([270, 128, 330, 134], fill=t["cover_accent"])
    d.text((300, 158), p.get("title", "感谢使用"), font=F(28, True),
           fill=t["cover_title"], anchor="ma")
    d.text((300, 202), p.get("subtitle", ""), font=F(12),
           fill=t["cover_sub"], anchor="ma")
    d.line([(24, 312), (576, 312)], fill=mix(t["cover_sub"], t["cover_bot"], 0.5),
           width=1)
    d.text((24, 321), COPYRIGHT, font=F(8),
           fill=mix(t["cover_sub"], t["cover_bot"], 0.4), anchor="lm")
    d.text((576, 321), f"{TOTAL}/{TOTAL}", font=F(9, True),
           fill=t["cover_accent"], anchor="rm")
    return img


RENDERERS = {
    "cover": page_cover,
    "bar_table": page_bar_table,
    "pie_table": page_pie_table,
    "pareto_table": page_pareto_table,
    "hbar_table": page_hbar_table,
    "pareto_full": page_pareto_full,
    "hbar_full": page_hbar_full,
    "line_full": page_line_full,
    "content": page_content,
    "closing": page_closing,
}

TAG = ""
TOTAL = 7


def set_globals(spec):
    global TAG, TOTAL, COPYRIGHT
    TAG = spec.get("tag", "自动分析报告")
    TOTAL = len(spec["pages"])
    COPYRIGHT = spec.get("copyright", COPYRIGHT)


# ---------------- 拼图 ----------------

THUMB_W, THUMB_H = 600, 338
COLS = 3
GAP = 46
MARGIN = 64
HEADER_H = 128
CAPTION_H = 30
FOOT_H = 64


def swatch_row(d, x, y, t):
    font = F(9)
    for label, col in (("主色", t["swatches"][0]),
                       ("强调色", t["swatches"][1]),
                       ("图表色", t["swatches"][2])):
        d.rounded_rectangle([x, y, x + 14, y + 14], radius=3, fill=col)
        d.text((x + 20, y + 7), label, font=font, fill="#2C3E50", anchor="lm")
        x += 96


def build_collage(spec, key, out_dir):
    set_globals(spec)
    t = THEMES[key]
    rows = math.ceil(len(spec["pages"]) / COLS)
    W = MARGIN * 2 + COLS * THUMB_W + (COLS - 1) * GAP
    H = HEADER_H + rows * THUMB_H + (rows - 1) * GAP + rows * CAPTION_H + FOOT_H
    img = Image.new("RGB", (W, H), t["collage_bg"])
    d = ImageDraw.Draw(img)
    d.text((MARGIN, 32), t["name"], font=F(34, True), fill="#16324F", anchor="la")
    tag_text = spec.get("collage_tag", "").replace("|", " · ")
    d.text((MARGIN, 82), tag_text, font=F(14), fill="#5A7186", anchor="la")
    tw = d.textlength(tag_text, font=F(14))
    swatch_row(d, max(MARGIN + tw + 44, MARGIN + 430), 66, t)
    d.line([(MARGIN, 118), (W - MARGIN, 118)], fill="#C9D6E2", width=1)
    pages = [RENDERERS[p["type"]](t, p) for p in spec["pages"]]
    for i, page in enumerate(pages):
        col = i % COLS
        row = i // COLS
        x = MARGIN + col * (THUMB_W + GAP)
        y = HEADER_H + row * (THUMB_H + GAP + CAPTION_H)
        img.paste(page, (x, y))
        d.rectangle([x - 1, y - 1, x + THUMB_W, y + THUMB_H],
                    outline="#C9D6E2", width=1)
        d.text((x + THUMB_W / 2, y + THUMB_H + 10), f"{i + 1:02d} / {TOTAL:02d}",
               font=F(10, True), fill="#5A7186", anchor="ma")
    out = os.path.join(out_dir, f"方案{key}.png")
    img.save(out)
    return out


def render_hd(spec, theme, out_dir, width=3840, height=2160):
    global SCALE, SCALE_Y
    set_globals(spec)
    os.makedirs(out_dir, exist_ok=True)
    SCALE = width / 600.0
    SCALE_Y = height / 338.0
    t = THEMES[theme]
    outs = []
    for i, p in enumerate(spec["pages"]):
        img = RENDERERS[p["type"]](t, p)
        out = os.path.join(out_dir, f"{theme}_第{i + 1}页.png")
        img.save(out)
        outs.append(out)
    return outs


def main():
    ap = argparse.ArgumentParser(description="PIL 视觉稿渲染器：3 版拼图 + 逐页高清")
    ap.add_argument("--spec", required=True, help="页面规格 JSON")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--mode", choices=["collages", "hd", "all"], default="collages")
    ap.add_argument("--theme", choices=list(THEMES), default="C")
    ap.add_argument("--size", default="3840x2160")
    args = ap.parse_args()
    spec = json.load(open(args.spec, encoding="utf-8"))
    os.makedirs(args.out_dir, exist_ok=True)
    if args.mode in ("collages", "all"):
        for k in THEMES:
            print(build_collage(spec, k, args.out_dir))
    if args.mode in ("hd", "all"):
        w, h = (int(v) for v in args.size.lower().split("x"))
        for p in render_hd(spec, args.theme, args.out_dir, w, h):
            print(p)


if __name__ == "__main__":
    main()
