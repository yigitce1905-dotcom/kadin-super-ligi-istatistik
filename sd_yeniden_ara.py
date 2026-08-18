# -*- coding: utf-8 -*-
"""C: 137 doğrulanamayanı SD'de isim+uyruk ile yeniden ara, doğru profili seç, güncel kulübü oku."""
import json, re, sys, time, unicodedata
import requests
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))

TR_EN = {"ABD":"United States","Türkiye":"Turkey","İsveç":"Sweden","Bosna Hersek":"Bosnia",
 "Hırvatistan":"Croatia","Cezayir":"Algeria","Brezilya":"Brazil","Kanada":"Canada",
 "Avustralya":"Australia","Danimarka":"Denmark","Almanya":"Germany","Macaristan":"Hungary",
 "Gana":"Ghana","Karadağ":"Montenegro","Vietnam":"Vietnam","Rusya Federasyonu":"Russia",
 "Meksika":"Mexico","Portekiz":"Portugal","İspanya":"Spain","Irak":"Iraq","Porto Riko":"Puerto Rico",
 "Arnavutluk":"Albania","Dominik Cumhuriyeti":"Dominican","Gabon":"Gabon","Bermuda":"Bermuda",
 "Panama":"Panama","İrlanda":"Ireland","Nijerya":"Nigeria","Haiti":"Haiti","İngiltere":"England",
 "Venezuela":"Venezuela","Trinidad ve Tobago":"Trinidad","Gürcistan":"Georgia"}

ALIAS = {"internazionale":"inter","inter milano":"inter","ol lyonnes":"lyon","olympique lyon":"lyon"}
SUFFIX = r"\b(fc|sc|fk|zfk|znk|cf|sv|vfl|vfb|bk|if|il|ff|q|ii|iii|u23|u21|u20|u19|u17|w|women|frauen|feminin|femenin|femenil|femminile|ladies|kvinner|dff|wfc|calcio)\b"
def nk(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    s = re.sub(SUFFIX," ", re.sub(r"[^a-z0-9 ]"," ", s)); s = re.sub(r"\s+"," ", s).strip()
    return ALIAS.get(s, s)
def nisim(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z ]"," ", s)).strip()
def ayni_kulup(a,b):
    na,nb=nk(a),nk(b)
    if not na or not nb: return False
    ta,tb=set(na.split()),set(nb.split())
    return na==nb or na in nb or nb in na or bool(ta&tb)

def satir_kulup(row):
    for a in row.find_all("a", href=True):
        if "verein_" in a["href"]: return a.get_text(strip=True)
    t = row.get_text(" ", strip=True)
    for art in ("vereinslos","Karriereende","pausiert","unbekannt"):
        if art.lower() in t.lower(): return art
    return ""

def ara(isim, uyruk_en):
    slug = isim.lower().replace(" ", "-"); q = isim.replace(" ", "+")
    url = f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html?quicksearch={q}"
    r = requests.get(url, headers=H, timeout=12)
    soup = BeautifulSoup(r.text, "html.parser")
    adaylar = []
    for a in soup.find_all("a", href=True):
        if "spieler_" in a["href"] and a.get_text(strip=True):
            row = a.find_parent("tr")
            if not row: continue
            ad = a.get_text(strip=True)
            nat = ""
            for img in row.find_all("img"):
                ti = img.get("title","")
                if ti and ti != ad and not ti.replace(" ","").isdigit():
                    nat = ti; break
            adaylar.append((ad, nat, satir_kulup(row), a["href"]))
    hn, hu = nisim(isim), (uyruk_en or "").lower()
    def skor(c):
        ad,nat,_,_ = c
        s=0
        if nisim(ad)==hn: s+=4
        elif hn in nisim(ad) or nisim(ad) in hn: s+=2
        if hu and (hu in nat.lower() or nat.lower() in hu): s+=3
        return s
    if not adaylar: return None
    adaylar.sort(key=skor, reverse=True)
    return adaylar[0] if skor(adaylar[0])>0 else None

# 137 isimleri
txt = open("_sd_kulup_v2.txt", encoding="utf-8").read()
blok = txt.split("PROFİL DOĞRULANAMADI")[1]
isimler = [m.group(1).strip() for m in re.finditer(r"^\s+(.+?) \| bizde:", blok, re.M)]

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
    if (k+1) % 30 == 0:
        print(f"  ...{k+1}/{len(isimler)} | ayni {len(ayni)} serbest {len(serbest)} degismis {len(degismis)} bulunamadi {len(bulunamadi)}")
    time.sleep(0.4)

L = [f"=== C: YENİDEN ARAMA (isim+uyruk) — {len(isimler)} oyuncu ===",
     f"Aynı {len(ayni)} | SERBEST {len(serbest)} | DEĞİŞMİŞ {len(degismis)} | Emekli {len(emekli)} | Bulunamadı {len(bulunamadi)}",
     f"\n--- SERBEST ({len(serbest)}) ---"] + [f"  {i} | {b} -> SERBEST  (SD: {a})" for i,b,a in serbest]
L += [f"\n--- KULÜP DEĞİŞMİŞ ({len(degismis)}) ---"] + [f"  {i} | {b} -> {k}  (SD: {a})" for i,b,k,a in degismis]
L += [f"\n--- EMEKLİ ({len(emekli)}) ---"] + [f"  {i} | {b}  (SD: {a})" for i,b,a in emekli]
L += [f"\n--- SD'DE BULUNAMADI ({len(bulunamadi)}) ---"] + [f"  {i} | {b}" for i,b in bulunamadi]
open("_sd_yeniden_ara.txt","w",encoding="utf-8").write("\n".join(L))
print("\n".join(L[:2]))
print("-> _sd_yeniden_ara.txt")
