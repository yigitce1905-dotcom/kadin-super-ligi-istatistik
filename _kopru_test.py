# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")

sd = app.birlesik_sd_yukle()
le = app.birlesik_leistung_yukle()
b  = app.birlesik_scout_yukle()
print(f"Birleşik SD: {len(sd)} profil | Birleşik kariyer: {len(le)}")

isim = "SELDA AKGÖZ"
p = sd.get(isim, {})
sez = (le.get(isim) or {}).get("sezonlar", [])
print(f"\n{isim}:")
print(f"  SD profil: {'VAR' if p else 'YOK'} — boy={p.get('Height','?')} uyruk={p.get('Nationality','?')} sözleşme={p.get('Contract until','?')}")
print(f"  kariyer sezonu: {len(sez)} satır")
for s in sez[:4]:
    print(f"    {s.get('sezon','?'):10} {str(s.get('kulup','?'))[:24]:24} maç={s.get('mac',0)} {'(MİLLİ)' if s.get('milli') else ''}")
milli = [s for s in sez if s.get("milli")]
print(f"  milli takım satırı: {len(milli)}")
# TR havuzundan kaç kişinin SD/kariyer köprüsü doldu
tr = app.scotr_kadro_yukle()
sd_var = sum(1 for i in tr if i in sd)
le_var = sum(1 for i in tr if i in le)
print(f"\nTR havuzu {len(tr)} oyuncudan: SD profili {sd_var}, kariyer verisi {le_var}")
