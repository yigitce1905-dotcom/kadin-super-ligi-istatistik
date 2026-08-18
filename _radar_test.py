# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")
ham_saha, ham_gk = app._nitelik_ham()
def eksen(v, attrs):
    vals=[v[a] for a in attrs if a in v]
    return sum(vals)/len(vals) if len(vals)>=2 else None
for isim, eks in (("Naomi Girma", app._RADAR_SAHA), ("Phallon Tullis-Joyce", app._RADAR_GK)):
    havuz = ham_gk if isim in ham_gk else ham_saha
    q = havuz.get(isim)
    print(f"\n{isim}:")
    if not q: print("  vektör yok!"); continue
    for tr_ad, en_ad, attrs in eks:
        qd = eksen(q, attrs)
        if qd is None: print(f"  {tr_ad:14}: eksen verisi yok"); continue
        dag=[x for x in (eksen(v,attrs) for v in havuz.values()) if x is not None]
        pct=round(sum(1 for x in dag if x<=qd)/len(dag)*100)
        print(f"  {tr_ad:14}: {pct}. yüzdelik (ham {qd:.1f})")
