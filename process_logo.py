# -*- coding: utf-8 -*-
"""Masaüstündeki logo JPG'sini → şeffaf arka planlı, kırpılmış PNG (static/logo.png).
Zemin koyu yeşil-teal, logo mor/pembe → 'morluk' (R+B)/2 - G maskesiyle ayrılır.
"""
import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

KAYNAK = Path(r"C:\Users\MSI\Desktop\25f4c875-afa9-415e-8242-fb348b449e98.jpg")
STATIK = Path(__file__).parent / "static"
STATIK.mkdir(exist_ok=True)

im = Image.open(KAYNAK).convert("RGB")
a = np.asarray(im).astype(np.float32)
R, G, B = a[..., 0], a[..., 1], a[..., 2]

# Morluk skoru: logo (mor/pembe) yüksek pozitif, zemin (yeşil-teal) negatif.
morluk = (R + B) / 2.0 - G
# Parlaklık de yardımcı: çok karanlık = zemin.
parlaklik = (R + G + B) / 3.0

# Alfa: morluk eşiğiyle yumuşak geçiş (feather) + karanlık zemini iyice sil.
lo, hi = 4.0, 38.0
alpha = np.clip((morluk - lo) / (hi - lo), 0, 1)
# Düşük parlaklık + düşük morluk olan yerleri tamamen şeffaf yap (vignette glow temizliği)
alpha[(parlaklik < 22) & (morluk < 12)] = 0.0
alpha = (alpha * 255).astype(np.uint8)

rgba = np.dstack([a.astype(np.uint8), alpha])
out = Image.fromarray(rgba, "RGBA")

# Alfa kanalını hafif blur → pürüzsüz kenar
ablur = out.split()[3].filter(ImageFilter.GaussianBlur(0.6))
out.putalpha(ablur)

# İçeriğe göre kırp (şeffaf kenar boşluklarını at) + küçük pay
bbox = out.split()[3].point(lambda p: 255 if p > 12 else 0).getbbox()
if bbox:
    pad = 18
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(out.width, x1 + pad), min(out.height, y1 + pad)
    out = out.crop((x0, y0, x1, y1))

out.save(STATIK / "logo.png")
print("logo.png:", out.size, "->", STATIK / "logo.png")

# Kare marka (favicon / kompakt) — sadece içerik, kareye ortalı
sq = max(out.size)
kanvas = Image.new("RGBA", (sq, sq), (0, 0, 0, 0))
kanvas.paste(out, ((sq - out.width) // 2, (sq - out.height) // 2), out)
fav = kanvas.resize((256, 256), Image.LANCZOS)
fav.save(STATIK / "logo_kare.png")
print("logo_kare.png:", fav.size)
