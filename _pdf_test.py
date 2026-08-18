# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException as e:
    print("import kesildi:", type(e).__name__, str(e)[:100])
app = sys.modules.get("app")
d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))

for isim in ("Katriina Talaslahti", "Mackenzie Arnold", "Sam Kerr"):
    r = d[isim]
    b = app._scout_pdf_uret(isim, r)
    yol = rf"C:\Users\MSI\Desktop\_test_{isim.split()[-1]}.pdf"
    open(yol, "wb").write(bytes(b))
    print(f"✓ {isim}: {len(b)} bayt | kaleci={'VAR' if r.get('kaleci') else 'yok'} -> {yol}")
