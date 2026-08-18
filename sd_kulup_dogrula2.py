# -*- coding: utf-8 -*-
"""Güncel kulüp doğrulama v2: cached SD profilini UYRUK+YAŞ ile doğrula, sonra kulübü karşılaştır.
Doğru profil = güvenilir; uyruk/yaş tutmuyorsa 'profil doğrulanamadı' (isim çakışması)."""
import json, re, sys, time, unicodedata
import requests
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
sd = json.load(open("scouting_sd_profiller.json", encoding="utf-8"))

ARTIFACT = ("spielerin löschen", "unbekannt", "pausiert", "löschen", "karriereende", "unknown")
ALIAS = {"internazionale":"inter","inter milano":"inter","inter milan":"inter",
         "bayern munchen":"bayern","bayern munih":"bayern","olympique lyonnais":"lyon",
         "ol lyonnes":"lyon","olympique lyon":"lyon","manchester":"manchester",
         "parma calcio":"parma","juventus":"juventus"}
SUFFIX = r"\b(fc|sc|fk|zfk|znk|cf|sv|vfl|vfb|bk|if|il|ff|q|ii|iii|u23|u21|u20|u19|u17|w|women|" \
         r"frauen|feminin|femenin|femenil|femminile|ladies|kvinner|dff|wfc|calcio|1893|1899|1894)\b"

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(SUFFIX, " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIAS.get(s, s)

def ayni_kulup(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb: return False
    if na == nb: return True
    ta, tb = set(na.split()), set(nb.split())
    return bool(ta & tb) and (na in nb or nb in na or len(ta & tb) >= min(len(ta), len(tb)))

def yas_ok(isim):
    biz = d.get(isim,{}).get("yas")
    sy = sd.get(isim,{}).get("Age","")
    m = re.search(r"\d{1,2}", str(sy))
    if not biz or not m: return None
    return abs(int(biz) - int(m.group())) <= 1

def uyruk_ok(isim):
    biz = norm(d.get(isim,{}).get("vatandaslik"))
    sdp = sd.get(isim,{}); su = norm(sdp.get("vatandaslik") or sdp.get("Nationality"))
    if not biz or not su: return None
    return biz == su or biz in su or su in biz

def sd_kulup(url):
    r = requests.get(url, headers=H, timeout=12)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        if re.search(r"verein_\d+", a["href"]):
            t = a.get_text(strip=True)
            if t: return t
    return ""

hedef = [(i,v) for i,v in d.items()
         if v.get("kulup") and isinstance(sd.get(i),dict) and sd[i].get("profil_url")]
print(f"Doğrulanacak: {len(hedef)}\n")

serbest, degismis, dogrulanamadi, belirsiz, ayni = [], [], [], [], 0
for k,(isim,v) in enumerate(hedef):
    u_ok, y_ok = uyruk_ok(isim), yas_ok(isim)
    # profil doğru mu? uyruk YANLIŞ ise kesin yanlış profil. uyruk None+yaş yanlış da şüpheli.
    if u_ok is False or (u_ok is None and y_ok is False):
        dogrulanamadi.append((isim, v["kulup"])); continue
    try:
        sdk = sd_kulup(sd[isim]["profil_url"])
    except Exception:
        dogrulanamadi.append((isim, v["kulup"])); continue
    low = sdk.lower()
    if not sdk or any(x in low for x in ARTIFACT):
        belirsiz.append((isim, v["kulup"], sdk or "?")); continue
    if low == "vereinslos":
        serbest.append((isim, v["kulup"])); continue
    if ayni_kulup(v["kulup"], sdk):
        ayni += 1
    else:
        degismis.append((isim, v["kulup"], sdk))
    if (k+1) % 60 == 0:
        print(f"  ...{k+1}/{len(hedef)} | ayni {ayni} serbest {len(serbest)} degismis {len(degismis)} dogrulanamadi {len(dogrulanamadi)}")
    time.sleep(0.4)

L = [f"=== GÜNCEL KULÜP DOĞRULAMA v2 (uyruk+yaş teyitli) ===",
     f"Toplam {len(hedef)} | Aynı {ayni} | SERBEST {len(serbest)} | DEĞİŞMİŞ {len(degismis)} | "
     f"Profil doğrulanamadı(isim çakışması) {len(dogrulanamadi)} | Belirsiz {len(belirsiz)}",
     f"\n--- SERBEST kalmış ({len(serbest)}) ---"]
L += [f"  {i} | bizde: {b} -> SERBEST" for i,b in serbest]
L.append(f"\n--- KULÜP DEĞİŞMİŞ ({len(degismis)}) ---")
L += [f"  {i} | {b} -> {s}" for i,b,s in degismis]
L.append(f"\n--- BELİRSİZ (SD'de garip değer, kontrol) ({len(belirsiz)}) ---")
L += [f"  {i} | {b} -> {s}" for i,b,s in belirsiz]
L.append(f"\n--- PROFİL DOĞRULANAMADI (isim çakışması, SD linki yanlış kişi) ({len(dogrulanamadi)}) ---")
L += [f"  {i} | bizde: {b}" for i,b in dogrulanamadi]
open("_sd_kulup_v2.txt","w",encoding="utf-8").write("\n".join(L))
print("\n".join(L[:2]))
print("\n-> _sd_kulup_v2.txt")
