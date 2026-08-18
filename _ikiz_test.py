# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException as e:
    print("import kesildi:", type(e).__name__)
app = sys.modules.get("app")
d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))

saha, gk = app._nitelik_vektorleri()
print(f"Saha vektörü: {len(saha)} oyuncu | GK vektörü: {len(gk)} oyuncu")

for isim in ("Sam Kerr", "Naomi Girma", "Mackenzie Arnold", "Katriina Talaslahti"):
    ik = app._nitelik_ikizleri(isim)
    r = d.get(isim, {})
    print(f"\n{isim} ({'/'.join(r.get('mevki',[]))}, {r.get('kulup','')}):")
    for aday, s in ik:
        ra = d.get(aday, {})
        print(f"   %{s:3} {aday:28} {'/'.join(ra.get('mevki',[])):12} {ra.get('kulup','')[:20]:20} nihai={ra.get('nihai','')}")
