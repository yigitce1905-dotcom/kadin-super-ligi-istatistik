# -*- coding: utf-8 -*-
"""SoccerDonna güncel KONTRAT tarihi (Contract until) tazeleme — scouting oyuncuları.

Kayıtlı profil_url'den her profili yeniden çeker, 'Contract until' alanını günceller.
scouting_sd_profiller.json'u yerinde günceller. Resumable: bugün tazelenenleri atlar
(ara verilirse tekrar çalıştır, kaldığı yerden devam eder). Hız-limitli (0.4 sn).

Kullanım:  PYTHONIOENCODING=utf-8 python kontrat_guncelle_sd.py
"""
import json, time, sys, datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
YOL   = Path(__file__).parent / "scouting_sd_profiller.json"
BUGUN = datetime.date.today().isoformat()

with open(YOL, encoding="utf-8") as f:
    d = json.load(f)

def contract_cek(url: str):
    """Profil sayfasından yalnız 'Contract until' değerini döndürür (yoksa None)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return False   # ağ hatası (None ile 'alanı yok'u ayır)
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 2 and cells[0].rstrip(":") == "Contract until":
            return cells[1]
    return None

hedef = [(k, v) for k, v in d.items()
         if isinstance(v, dict) and v.get("profil_url") and v.get("_kontrat_ts") != BUGUN]
print(f"Tazelenecek profil: {len(hedef)} / {len(d)}")

islenen = degisen = hata = 0
for i, (k, v) in enumerate(hedef, 1):
    yeni = contract_cek(v["profil_url"])
    if yeni is False:
        hata += 1
        print(f"[{i}/{len(hedef)}] AĞ HATASI  {k}")
        time.sleep(0.6)
        continue
    eski = v.get("Contract until", "")
    if yeni:
        v["Contract until"] = yeni
        if yeni != eski:
            degisen += 1
            print(f"[{i}/{len(hedef)}] {k}: {eski or '—'} → {yeni}")
    v["_kontrat_ts"] = BUGUN
    islenen += 1
    if islenen % 25 == 0:
        with open(YOL, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"  >> ara kayıt ({islenen}/{len(hedef)})")
    time.sleep(0.4)

with open(YOL, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print(f"BİTTİ. İşlenen: {islenen} | Değişen kontrat: {degisen} | Ağ hatası: {hata}")
