# -*- coding: utf-8 -*-
"""v2'nin SERBEST+DEĞİŞMİŞ oyuncularını C yöntemiyle (isim+uyruk arama) yeniden doğrula."""
import json, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from sd_yeniden_ara import ara, TR_EN, ayni_kulup, d

txt = open("_sd_kulup_v2.txt", encoding="utf-8").read()
def blok_isim(bas, son):
    seg = txt.split(bas)[1].split(son)[0]
    return [m.group(1).strip() for m in re.finditer(r"^\s+(.+?) (?:\| bizde:|\|)", seg, re.M)]
isimler = blok_isim("--- SERBEST kalmış", "--- KULÜP DEĞİŞMİŞ")
isimler += blok_isim("--- KULÜP DEĞİŞMİŞ", "--- BELİRSİZ")
isimler = list(dict.fromkeys(isimler))
print("Yeniden doğrulanacak (v2 değişen):", len(isimler))

serbest, degismis, ayni, emekli, bulunamadi = [], [], [], [], []
for k, isim in enumerate(isimler):
    biz = d.get(isim, {}).get("kulup", "")
    uen = TR_EN.get(d.get(isim, {}).get("vatandaslik", ""), "")
    try:
        c = ara(isim, uen)
    except Exception:
        c = None
    if not c:
        bulunamadi.append((isim, biz)); time.sleep(0.4); continue
    ad, nat, kulup, href = c
    low = kulup.lower()
    if "karriereende" in low: emekli.append((isim, biz, ad))
    elif "vereinslos" in low or low in ("pausiert","unbekannt"): serbest.append((isim, biz, ad))
    elif ayni_kulup(biz, kulup): ayni.append(isim)
    else: degismis.append((isim, biz, kulup, ad))
    if (k+1) % 40 == 0:
        print(f"  ...{k+1}/{len(isimler)} | ayni {len(ayni)} serbest {len(serbest)} degismis {len(degismis)}")
    time.sleep(0.4)

L = [f"=== v2 DEĞİŞENLER YENİDEN DOĞRULAMA — {len(isimler)} ===",
     f"Aynı {len(ayni)} | SERBEST {len(serbest)} | DEĞİŞMİŞ {len(degismis)} | Emekli {len(emekli)} | Bulunamadı {len(bulunamadi)}",
     f"\n--- SERBEST ({len(serbest)}) ---"] + [f"  {i} | {b} -> SERBEST" for i,b,a in serbest]
L += [f"\n--- KULÜP DEĞİŞMİŞ ({len(degismis)}) ---"] + [f"  {i} | {b} -> {k}" for i,b,k,a in degismis]
L += [f"\n--- EMEKLİ ({len(emekli)}) ---"] + [f"  {i} | {b}" for i,b,a in emekli]
L += [f"\n--- AYNI olarak düzeltildi ({len(ayni)}) ---"] + [f"  {i}" for i in ayni]
L += [f"\n--- BULUNAMADI ({len(bulunamadi)}) ---"] + [f"  {i} | {b}" for i,b in bulunamadi]
open("_reverify_v2.txt","w",encoding="utf-8").write("\n".join(L))
print("\n".join(L[:2])); print("-> _reverify_v2.txt")
