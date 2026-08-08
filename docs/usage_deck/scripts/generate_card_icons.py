#!/usr/bin/env python3
"""生成卡片点缀图标（PIL 线性图标，统一 96px，透明背景，深灰蓝 #2E3B4E）。

图标列表与卡片对应：功能6 + 亮点6 + EFF3(复用) + 注意4。
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "assets" / "icons" / "cards"
COLOR = (46, 59, 78, 255)   # CARD_TITLE
S = 96
W = 5


def new_canvas():
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{name}.png")


def icon_file():
    d = ImageDraw.Draw(new_canvas())
    # 圆角矩形 + 两条横线
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([22, 14, 74, 82], radius=6, outline=COLOR, width=W)
    d.line([(32, 34), (64, 34)], fill=COLOR, width=W)
    d.line([(32, 48), (64, 48)], fill=COLOR, width=W)
    d.line([(32, 62), (52, 62)], fill=COLOR, width=W)
    save(img, "file")


def icon_chart():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.line([(18, 82), (78, 82)], fill=COLOR, width=W)
    d.rectangle([26, 50, 38, 80], outline=COLOR, width=W)
    d.rectangle([43, 34, 55, 80], outline=COLOR, width=W)
    d.rectangle([60, 20, 72, 80], outline=COLOR, width=W)
    save(img, "chart")


def icon_percent():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.ellipse([22, 22, 46, 46], outline=COLOR, width=W)
    d.ellipse([50, 50, 74, 74], outline=COLOR, width=W)
    d.line([(48, 24), (72, 48)], fill=COLOR, width=W)
    d.line([(24, 48), (48, 72)], fill=COLOR, width=W)
    save(img, "percent")


def icon_alert():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.polygon([(48, 14), (82, 78), (14, 78)], outline=COLOR, width=W)
    d.line([(48, 38), (48, 58)], fill=COLOR, width=W)
    d.ellipse([44, 64, 52, 72], outline=COLOR, width=W)
    save(img, "alert")


def icon_pulse():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.line([(10, 48), (36, 48), (46, 26), (58, 66), (68, 42), (86, 42)],
           fill=COLOR, width=W, joint="curve")
    save(img, "pulse")


def icon_rocket():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.polygon([(48, 12), (72, 40), (60, 58), (36, 58), (24, 40)], outline=COLOR, width=W)
    d.line([(36, 58), (30, 82)], fill=COLOR, width=W)
    d.line([(60, 58), (66, 82)], fill=COLOR, width=W)
    d.ellipse([42, 34, 54, 46], outline=COLOR, width=W)
    save(img, "rocket")


def icon_template():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([14, 18, 82, 78], radius=4, outline=COLOR, width=W)
    d.line([(14, 36), (82, 36)], fill=COLOR, width=W)
    d.line([(30, 18), (30, 78)], fill=COLOR, width=W)
    d.rectangle([38, 44, 52, 58], outline=COLOR, width=3)
    d.rectangle([56, 44, 74, 58], outline=COLOR, width=3)
    save(img, "template")


def icon_bottleneck():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.line([(16, 80), (80, 80)], fill=COLOR, width=W)
    d.rectangle([20, 60, 34, 78], outline=COLOR, width=W)
    d.rectangle([38, 44, 52, 78], outline=COLOR, width=W)
    d.rectangle([56, 28, 70, 78], outline=COLOR, width=W)
    d.line([(56, 18), (56, 28)], fill=COLOR, width=W)
    d.line([(56, 18), (48, 18)], fill=COLOR, width=W)
    save(img, "bottleneck")


def icon_swap():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.line([(14, 34), (66, 34)], fill=COLOR, width=W)
    d.line([(56, 24), (66, 34), (56, 44)], fill=COLOR, width=W)
    d.line([(82, 62), (30, 62)], fill=COLOR, width=W)
    d.line([(40, 52), (30, 62), (40, 72)], fill=COLOR, width=W)
    save(img, "swap")


def icon_gantt():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.line([(14, 20), (82, 20)], fill=COLOR, width=3)
    d.line([(14, 48), (82, 48)], fill=COLOR, width=3)
    d.line([(14, 76), (82, 76)], fill=COLOR, width=3)
    d.rectangle([24, 14, 66, 26], fill=COLOR)
    d.rectangle([38, 42, 74, 54], fill=COLOR)
    d.rectangle([18, 70, 56, 82], fill=COLOR)
    save(img, "gantt")


def icon_mark():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.ellipse([16, 16, 80, 80], outline=COLOR, width=W)
    d.line([(48, 34), (48, 54)], fill=COLOR, width=W)
    d.ellipse([44, 62, 52, 70], outline=COLOR, width=W)
    save(img, "mark")


def icon_report():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18, 12, 78, 84], radius=5, outline=COLOR, width=W)
    d.polygon([(30, 70), (46, 50), (56, 60), (70, 42)], outline=COLOR, width=W)
    d.line([(30, 70), (46, 50)], fill=COLOR, width=W)
    d.line([(56, 60), (70, 42)], fill=COLOR, width=W)
    save(img, "report")


def icon_shield():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.polygon([(48, 12), (78, 26), (78, 52), (48, 84), (18, 52), (18, 26)], outline=COLOR, width=W)
    d.line([(36, 48), (44, 56), (62, 38)], fill=COLOR, width=W)
    save(img, "shield")


def icon_folder():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.line([(16, 30), (16, 72), (80, 72), (80, 34)], fill=COLOR, width=W, joint="curve")
    d.line([(16, 34), (40, 34), (46, 44), (80, 44)], fill=COLOR, width=W, joint="curve")
    save(img, "folder")


def icon_ppt():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18, 18, 78, 70], radius=4, outline=COLOR, width=W)
    d.line([(26, 78), (70, 78)], fill=COLOR, width=W)
    d.line([(30, 78), (30, 86)], fill=COLOR, width=W)
    d.line([(66, 78), (66, 86)], fill=COLOR, width=W)
    d.polygon([(34, 56), (34, 32), (62, 44)], outline=COLOR, width=W)
    save(img, "ppt")


def icon_settings():
    img = new_canvas()
    d = ImageDraw.Draw(img)
    d.ellipse([34, 34, 62, 62], outline=COLOR, width=W)
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x0 = 48 + 30 * math.cos(a)
        y0 = 48 + 30 * math.sin(a)
        x1 = 48 + 38 * math.cos(a)
        y1 = 48 + 38 * math.sin(a)
        d.line([(x0, y0), (x1, y1)], fill=COLOR, width=W)
    d.ellipse([43, 43, 53, 53], fill=COLOR)
    save(img, "settings")


def main():
    for fn in (icon_file, icon_chart, icon_percent, icon_alert, icon_pulse, icon_rocket,
               icon_template, icon_bottleneck, icon_swap, icon_gantt, icon_mark, icon_report,
               icon_shield, icon_folder, icon_ppt, icon_settings):
        fn()
    print("icons saved to", OUT)


if __name__ == "__main__":
    main()
