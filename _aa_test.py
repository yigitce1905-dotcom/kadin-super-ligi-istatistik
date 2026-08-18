# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")
sorgular = [
    "sol ayaklı u23 stoper hava topu güçlü",
    "serbest kelepir kanat",
    "refleksleri iyi genç kaleci",
    "golcü santrafor max 100k istekli",
    "vizyonu iyi orta saha 20-26 yaş",
    "asdfgh",   # anlamsız
]
import time
for q in sorgular:
    t0=time.perf_counter()
    ozet, son = app.akilli_arama(q)
    ms=(time.perf_counter()-t0)*1000
    print(f"\n### {q!r}  ({ms:.1f} ms)")
    if ozet is None:
        print("   -> kriter çözülemedi (beklenen davranış)"); continue
    print("   kriterler:", " · ".join(ozet))
    for r in (son or [])[:4]:
        c=" ".join(f"{a}:{n}" for a,n in r["cipler"])
        print(f"   {r['isim']:26} {r['yas']} {r['mevki']:12} {str(r['kulup'])[:18]:18} {r['deger']:10} nihai={r['nihai']:3} {c}")
    print(f"   toplam: {len(son)}")
