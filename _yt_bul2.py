# -*- coding: utf-8 -*-
"""2. tur: kulüp bağlamlı sorgular + şüphelilerin elenmesi."""
import re, sys, json, time
import requests
sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "en-US,en;q=0.9"}
C = {"CONSENT": "YES+1"}

# oyuncu: (ek sorgular)
HEDEF = {
 "Angelina Portnova": ["Angelina Portnova goalkeeper", "Portnova Asteras Tripolis"],
 "Miray Ayhan": ["Miray Ayhan Stabæk", "Miray Ayhan futbol highlights"],
 "Aude Bizet": ["Aude Bizet Fleury", "Aude Bizet défenseure"],
 "Sibel Koksal": ["Sibel Köksal Sparta Rotterdam", "Sibel Köksal voetbal"],
 "Miray Cin": ["Miray Cin futbol", "Miray Cin kadın futbol"],
 "Ana Barjaktarovic": ["Ana Barjaktarovic Partizan", "Ana Barjaktarovic fudbal"],
 "Kader Hancar": ["Kader Hançar highlights", "Kader Hançar gol"],
 "Ajsa Kalac": ["Ajsa Kalac goalkeeper", "Ajša Kalač Olimpija"],
 "Ceylin Erata": ["Ceylin Erata Nürnberg", "Ceylin Erata futbol"],
 "Fatma Sakar": ["Fatma Şakar futbol", "Fatma Sakar highlights"],
 "Natalia Wrobel": ["Natalia Wrobel Strasbourg", "Natalia Wróbel piłka nożna"],
}

def ara(sorgu):
    url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(sorgu)
    r = requests.get(url, headers=H, cookies=C, timeout=20)
    return re.findall(r'"videoRenderer":\{"videoId":"([^"]{11})".+?"title":\{"runs":\[\{"text":"(.*?)"\}\]', r.text)[:5]

def puanla(baslik, isim):
    b = baslik.lower(); parcalar = isim.lower().split()
    p = 0
    if all(x in b for x in parcalar): p += 6
    elif parcalar[-1] in b: p += 4
    elif parcalar[0] in b: p += 1
    for k in ("highlight","skills","goals","gol","saves","kurtarış","welcome","best"):
        if k in b: p += 2
    for k in ("fifa","efootball","gameplay","podcast","interview","söyleşi","course","conference"):
        if k in b: p -= 5
    return p

mevcut = json.load(open("_yt_linkler.json", encoding="utf-8"))
# şüphelileri çıkar
for k in ("Sibel Koksal", "Miray Cin", "Natalia Wrobel", "Angelina Portnova"):
    mevcut.pop(k, None)

for isim, sorgular in HEDEF.items():
    if isim in mevcut: continue
    en = (None, "", -99)
    for s in sorgular:
        try:
            for vid, b in ara(s):
                b = b.encode().decode("unicode_escape", errors="ignore")
                p = puanla(b, isim)
                if p > en[2]: en = (vid, b, p)
        except Exception: pass
        time.sleep(0.8)
    vid, b, p = en
    if vid and p >= 6:
        mevcut[isim] = {"url": f"https://www.youtube.com/watch?v={vid}", "baslik": b, "puan": p}
        print(f"✓ {isim:20} [{p:2}] {b[:62]}")
    else:
        print(f"✗ {isim:20} yok (en iyi aday [{p}]: {b[:50]})")

json.dump(mevcut, open("_yt_linkler.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nTOPLAM {len(mevcut)}/15 direkt video")
for i, v in mevcut.items():
    print(f"  {i:20} -> {v['baslik'][:58]}")
