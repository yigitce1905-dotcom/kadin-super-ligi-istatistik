# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")
sorgular = [
    "u23 stoper", "u-19 kaleci", "23 yaş altı kanat", "23 yaşından küçük bek",
    "28 yaş üstü forvet", "30 yaşından büyük lider stoper", "en fazla 25 yaş orta saha",
    "20-26 yaş kanat", "20 ile 26 yaş arası stoper", "24 yaşında golcü",
    "25 altı hızlı kanat", "genç stoper", "tecrübeli kaleci",
    "max 50k 22 yas alti forvet",   # ASCII + bütçe karışık
]
for q in sorgular:
    ozet, son = app.akilli_arama(q)
    yaslar = [x for x in (ozet or []) if x.startswith("🎂")]
    print(f"{q:38} -> {' '.join(yaslar) or 'YAŞ YOK ⚠️'}  ({len(son or [])} sonuç)")
