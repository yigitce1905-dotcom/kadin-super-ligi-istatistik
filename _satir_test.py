# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")

b = app.birlesik_scout_yukle()
sd_data = app.birlesik_sd_yukle()
leistung_data = app.birlesik_leistung_yukle()
adlar = list(b.keys())
i = adlar.index("Shelby Hogan")
hedefler = adlar[max(0,i-2):i+4]
print("İncelenen:", hedefler)

def _esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

for tam_isim in hedefler:
    _kd = b.get(tam_isim, {})
    sd = sd_data.get(tam_isim, {})
    _yas = _kd.get("yas") or sd.get("Age","") or ""
    _sezk = [s for s in (leistung_data.get(tam_isim, {}) or {}).get("sezonlar", []) if not s.get("milli")]
    _kl = _kd.get("kulup","") or ""
    _sz = _kd.get("sozlesme","") or sd.get("Contract until","") or ""
    _dg = _kd.get("deger","") or ""
    _nh = _kd.get("nihai","")
    # şüpheli ham değerlerin repr'ı
    for ad, v in (("yas",_yas),("kulup",_kl),("sozlesme",_sz),("deger",_dg),("nihai",_nh)):
        s = str(v)
        if any(ord(c) < 32 or ord(c) == 0xFFFD or 0xD800 <= ord(c) <= 0xDFFF for c in s):
            print(f"  ⚠️ {tam_isim} | {ad} = {s!r}")
    # kontrat renk fonksiyonu patlıyor mu / ne döndürüyor
    try:
        renk = app._kontrat_renk(_sz)
    except Exception as e:
        renk = f"HATA:{type(e).__name__}"
    print(f"  {tam_isim:18} yas={_yas!r} sz={_sz!r} renk={renk!r} dg={_dg!r} nh={_nh!r}")
