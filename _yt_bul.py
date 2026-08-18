# -*- coding: utf-8 -*-
"""15 portföy oyuncusu için YouTube'da en uygun highlight videosunu bul."""
import re, sys, json, time
import requests
sys.stdout.reconfigure(encoding="utf-8")

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
     "Accept-Language": "en-US,en;q=0.9"}
C = {"CONSENT": "YES+1"}

OYUNCULAR = ["Angelina Portnova", "Miray Ayhan", "Aude Bizet", "Tanja Malesija",
             "Sumaya Komuntale", "Meryem Cal", "Sibel Koksal", "Aude Gbedjissi",
             "Miray Cin", "Ana Barjaktarovic", "Kader Hancar", "Ajsa Kalac",
             "Ceylin Erata", "Fatma Sakar", "Natalia Wrobel"]

def ara(sorgu):
    url = "https://www.youtube.com/results?search_query=" + requests.utils.quote(sorgu)
    r = requests.get(url, headers=H, cookies=C, timeout=20)
    # videoId + başlık çiftleri (ytInitialData içinden)
    adaylar = re.findall(r'"videoRenderer":\{"videoId":"([^"]{11})".+?"title":\{"runs":\[\{"text":"(.*?)"\}\]', r.text)
    return adaylar[:6]

def puanla(baslik, isim):
    b = baslik.lower()
    soyad = isim.split()[-1].lower()
    ad = isim.split()[0].lower()
    p = 0
    if soyad in b: p += 5
    if ad in b: p += 3
    for k in ("highlight", "skills", "goals", "welcome", "best of", "compilation", "saves"):
        if k in b: p += 2
    for k in ("fifa", "efootball", "pes ", "gameplay", "fc 2"):   # oyun videosu eleme
        if k in b: p -= 6
    return p

sonuc = {}
for isim in OYUNCULAR:
    en_iyi = (None, "", -99)
    for sorgu in (f"{isim} football highlights", f"{isim} futbol"):
        try:
            for vid, baslik in ara(sorgu):
                baslik = baslik.encode().decode("unicode_escape", errors="ignore")
                p = puanla(baslik, isim)
                if p > en_iyi[2]:
                    en_iyi = (vid, baslik, p)
        except Exception as e:
            print(f"  ! {isim}: {type(e).__name__}")
        time.sleep(0.8)
        if en_iyi[2] >= 8:   # soyad+highlight bulundu, ikinci sorguya gerek yok
            break
    vid, baslik, p = en_iyi
    if vid and p >= 5:       # en az soyad eşleşmesi şart
        sonuc[isim] = {"url": f"https://www.youtube.com/watch?v={vid}", "baslik": baslik, "puan": p}
        print(f"✓ {isim:22} [{p:2}] {baslik[:60]}")
    else:
        print(f"✗ {isim:22} güvenilir video yok (arama linki kalacak)")

json.dump(sonuc, open("_yt_linkler.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n{len(sonuc)}/15 oyuncuya direkt video bulundu -> _yt_linkler.json")
