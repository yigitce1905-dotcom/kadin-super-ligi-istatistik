# -*- coding: utf-8 -*-
"""Göknur promosyon görselini 1080x1080 PNG olarak Desktop'a çizer (Instagram için)."""
import os
from PIL import Image, ImageDraw, ImageFont

W = H = 1080
BG = (13, 19, 34)
GREEN = (29, 185, 84)
GREEN2 = (52, 211, 153)
WHITE = (255, 255, 255)
MUTE = (138, 160, 189)
MUTE2 = (159, 176, 198)
MUTE3 = (170, 184, 204)
GRAY = (124, 138, 165)
BARMUTE = (61, 74, 99)

FD = r"C:\Windows\Fonts"
def f(name, size):
    return ImageFont.truetype(os.path.join(FD, name), size)
reg = lambda s: f("arial.ttf", s)
bold = lambda s: f("arialbd.ttf", s)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# üst/alt yeşil şerit
d.rectangle([0, 0, W, 9], fill=GREEN)
d.rectangle([0, H - 10, W, H], fill=GREEN)

d.text((540, 96), "TURKISH WOMEN'S SUPER LEAGUE · KADIN SÜPER LİGİ · 2025-26",
       font=bold(20), fill=GRAY, anchor="mm")
d.text((540, 162), "Fewest goals conceded per match", font=bold(46), fill=(232, 238, 247), anchor="mm")
d.text((540, 208), "En az gol yiyen kaleci", font=reg(26), fill=MUTE, anchor="mm")

d.text((540, 388), "0.10", font=bold(228), fill=GREEN, anchor="mm")
d.text((540, 538), "GOALS CONCEDED PER MATCH · MAÇ BAŞINA YENİLEN GOL",
       font=bold(22), fill=MUTE, anchor="mm")

d.text((540, 632), "GÖKNUR GÜLERYÜZ", font=bold(64), fill=WHITE, anchor="mm")

d.text((95, 735), "GOALS CONCEDED PER MATCH · LOWER IS BETTER", font=bold(22), fill=MUTE2, anchor="lm")
d.text((95, 763), "Maç başına yenilen gol · az = iyi", font=reg(20), fill=GRAY, anchor="lm")

# barlar: (isim, deger, renk_isim, renk_deger, bar_renk)
rows = [
    ("Göknur Güleryüz", 0.10, WHITE, GREEN2, GREEN),
    ("Natalia Munteanu", 0.46, MUTE3, GRAY, BARMUTE),
    ("Gamze Nur Yaman", 0.52, MUTE3, GRAY, BARMUTE),
    ("Roberta Aprile", 0.62, MUTE3, GRAY, BARMUTE),
    ("Aytaj Sharifova", 0.64, MUTE3, GRAY, BARMUTE),
]
x_label = 400      # isim sağ kenarı
x_bar = 420        # bar başlangıcı
scale = 820        # 0.64 -> ~525px
y0, dy, bh = 808, 44, 24
for i, (isim, val, rc, vc, bc) in enumerate(rows):
    y = y0 + i * dy
    yc = y + bh // 2
    d.text((x_label, yc), isim, font=(bold(23) if i == 0 else reg(23)), fill=rc, anchor="rm")
    bw = max(14, int(val * scale))
    d.rounded_rectangle([x_bar, y, x_bar + bw, y + bh], radius=5, fill=bc)
    d.text((x_bar + bw + 14, yc), f"{val:.2f}", font=bold(21), fill=vc, anchor="lm")

d.text((540, 1042), "@idealsportsmanagement", font=bold(23), fill=(95, 111, 136), anchor="mm")

out = os.path.join(os.path.expanduser("~"), "Desktop", "goknur_kaleci.png")
img.save(out, "PNG")
print("KAYDEDILDI:", out, "| boyut:", img.size)
