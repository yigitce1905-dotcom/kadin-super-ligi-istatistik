# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")

dunya = app.scout_kadro_yukle()
tr = app.scotr_kadro_yukle()
b = app.birlesik_scout_yukle()
cakisan = set(tr) & set(dunya)
print(f"Dünya: {len(dunya)} | TR (değerlendirilmiş): {len(tr)} | Birleşik: {len(b)}")
print(f"Çakışan isim: {len(cakisan)} -> {sorted(cakisan)[:5]}")
dv = sum(1 for r in b.values() if r.get("degerlendirildi"))
print(f"Birleşik değerlendirilmiş: {dv}")

# TR kaydı örneği
ornek = next(i for i in tr if tr[i].get("kaleci"))
r = tr[ornek]
print(f"\nTR kaleci örneği: {ornek}")
print(f"  kulup={r['kulup']} lig={r['lig']} boy={r['boy']} yurtdışı={r['yurtdisi_gorusu']!r} nihai={r['nihai']}")
print(f"  beceri={len(r['beceri'])} kaleci={len(r['kaleci'])} havuz={r['havuz']}")

# akıllı arama TR oyuncu buluyor mu
ozet, son = app.akilli_arama("türkiye liginden golcü santrafor")  # 'türkiye' kelimesi mevki değil — sadece santrafor+golcü
trli = [x for x in (son or []) if b.get(x["isim"], {}).get("havuz") == "tr"]
print(f"\nAkıllı arama 'golcü santrafor': {len(son or [])} sonuç, TR ligi: {len(trli)}")
for x in trli[:4]:
    print(f"  🇹🇷 {x['isim']} ({x['kulup']}) nihai={x['nihai']}")

# nitelik ham havuzu büyüdü mü
s, g = app._nitelik_ham()
print(f"\nVektör havuzu: saha {len(s)} + gk {len(g)} = {len(s)+len(g)}")
