# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")

b = app.birlesik_scout_yukle()
# 1) TR oyuncu PDF üretimi (havuz=tr etiketi + YURTDIŞI kutusu yolu)
isim = "SELDA AKGÖZ"
r = b[isim]
pdf = app._scout_pdf_uret(isim, r)
print(f"✓ PDF: {isim} -> {len(bytes(pdf))} bayt (kaleci={'VAR' if r.get('kaleci') else 'yok'})")

# 2) render fonksiyonları hatasız mı (headless)
app.render_scout_kadro_raporu(isim)
print("✓ site raporu render hatasız")

# 3) ikizler TR oyuncusu için çalışıyor mu (birleşik vektör uzayı)
ik = app._nitelik_ikizleri(isim)
print(f"✓ ikizler: {[(a, s) for a, s in ik[:3]]}")

# 4) rol uygunluğu
print(f"✓ rol: {app._rol_uygunluk(isim)}")
