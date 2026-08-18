# -*- coding: utf-8 -*-
"""SD profili olmayan 8 oyuncu için SoccerDonna araması (bağımsız, sheet'siz)."""
import re, sys, time, unicodedata
import requests
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding="utf-8")

import socket
_g = socket.getaddrinfo
def _y(h, p, *a, **k):
    try: return _g(h, p, *a, **k)
    except socket.gaierror:
        if isinstance(h, str) and "google" in h:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.251.127.95", p))]
        raise
socket.getaddrinfo = _y

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def nisim(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z ]"," ", s)).strip()

def satir_kulup(row):
    for a in row.find_all("a", href=True):
        if "verein_" in a["href"]:
            return a.get_text(strip=True)
    t = row.get_text(" ", strip=True)
    for art in ("vereinslos","Karriereende","pausiert","unbekannt"):
        if art.lower() in t.lower(): return art
    return ""

def ara(isim, uen):
    slug = isim.lower().replace(" ","-"); q = isim.replace(" ","+")
    url = f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html?quicksearch={q}"
    soup = BeautifulSoup(requests.get(url, headers=H, timeout=15).text, "html.parser")
    adaylar = []
    for a in soup.find_all("a", href=True):
        if "spieler_" in a["href"] and a.get_text(strip=True):
            row = a.find_parent("tr")
            if not row: continue
            ad = a.get_text(strip=True); nat = ""
            for img in row.find_all("img"):
                ti = img.get("title","")
                if ti and ti != ad and not ti.replace(" ","").isdigit():
                    nat = ti; break
            adaylar.append((ad, nat, satir_kulup(row)))
    hn, hu = nisim(isim), (uen or "").lower()
    def sk(c):
        ad, nat, _ = c; s = 0
        if nisim(ad) == hn: s += 4
        elif hn in nisim(ad) or nisim(ad) in hn: s += 2
        if hu and (hu in nat.lower() or nat.lower() in hu): s += 3
        return s
    if not adaylar: return None
    adaylar.sort(key=sk, reverse=True)
    return adaylar[0] if sk(adaylar[0]) > 0 else None

HEDEF = {"Ange Bawou":"Cameroon","Ifeoma Onumonu":"Nigeria","Vivian Ikechukwu":"Nigeria",
         "Darya Harshkova":"Belarus","Glory Ogbonna":"Nigeria","Sanaa Mssoudy":"Morocco",
         "Shamirah Nalugya":"Uganda","Chaymaa Mourtaji":"Morocco"}
for isim, uyruk in HEDEF.items():
    try:
        c = ara(isim, uyruk)
        print(f"{isim:22} ->", c if c else "BULUNAMADI")
    except Exception as e:
        print(f"{isim:22} -> HATA: {type(e).__name__} {str(e)[:60]}")
    time.sleep(0.7)
