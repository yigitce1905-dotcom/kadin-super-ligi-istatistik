# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")
m = app._rol_merkezleri()
print(f"Öğrenilen rol prototipi: {len(m)}")
for (rol, gk), c in sorted(m.items()):
    print(f"  {'🧤' if gk else '⚽'} {rol} ({len(c)} nitelik)")
for isim in ("Naomi Girma", "Sam Kerr", "Caroline Graham Hansen", "Mackenzie Arnold"):
    print(f"\n{isim}: ", app._rol_uygunluk(isim))
