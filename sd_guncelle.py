# -*- coding: utf-8 -*-
"""SoccerDonna BİRLEŞİK tazeleme — scouting oyuncuları için tek profil çekişinde
GÜNCEL KULÜP + SÖZLEŞME + BOY hepsini alır → scouting_sd_profiller.json.

Alanlar: guncel_kulup (+ guncel_kulup_t), Contract until, Height.
Resumable: bugün tazelenenleri atlar (_sd_ts). Hız-limitli (0.4 sn).
(kontrat_guncelle_sd.py'nin yerine geçer — o yalnız kontrat çekiyordu.)

Kullanım:  PYTHONIOENCODING=utf-8 python sd_guncelle.py
"""
import json, time, sys, datetime, re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
YOL = Path(__file__).parent / "scouting_sd_profiller.json"
BUGUN = datetime.date.today().isoformat()
try:
    from scrape_leistungsdaten import ULKE_SLUGLARI
except Exception:
    ULKE_SLUGLARI = set()

def _ulke_mu(href):
    m = re.search(r"/([a-z-]+)/(?:historische-kader|startseite)/verein_", href)
    return bool(m) and re.sub(r"-u-?\d+$", "", m.group(1).rstrip("-")) in ULKE_SLUGLARI

def profil_bilgi(url):
    """Tek çekişte {kontrat, boy, kulup}. None = ağ hatası."""
    try:
        r = requests.get(url, headers=H, timeout=14)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None
    out = {"kontrat": None, "boy": None, "kulup": None}
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 2 and cells[0]:
            key = cells[0].rstrip(":")
            if key == "Contract until": out["kontrat"] = cells[1]
            elif key == "Height":       out["boy"] = cells[1]
    # güncel kulüp (profil_kulup mantığı)
    baslik = soup.find("table")
    metin = baslik.get_text(" ", strip=True).lower() if baslik else ""
    if "vereinslos" in metin or "without club" in metin or "clubless" in metin:
        out["kulup"] = "Serbest"
    else:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "verein_" not in href or _ulke_mu(href):
                continue
            ad = a.get_text(strip=True)
            if ad.lower() in ("vereinslos", "without club"): out["kulup"] = "Serbest"; break
            if ad.lower() in ("unbekannt", "unknown", "karriereende"): break   # SD bilmiyor → koru
            if ad and ad != "-" and not ad.isdigit(): out["kulup"] = ad; break
    return out

def gecerli(x):
    return bool(x) and str(x).strip().lower() not in ("", "?", "-", "—", "unbekannt", "unknown")

with open(YOL, encoding="utf-8") as f:
    sd = json.load(f)
hedef = [(k, v) for k, v in sd.items()
         if isinstance(v, dict) and v.get("profil_url") and v.get("_sd_ts") != BUGUN]
print(f"Tazelenecek profil: {len(hedef)} / {len(sd)}")

islenen = k_deg = s_deg = b_deg = hata = 0
for i, (k, v) in enumerate(hedef, 1):
    b = profil_bilgi(v["profil_url"])
    if b is None:
        hata += 1; print(f"[{i}/{len(hedef)}] AĞ HATASI {k}"); time.sleep(0.6); continue
    if gecerli(b["kontrat"]) and b["kontrat"].strip() != (v.get("Contract until") or "").strip():
        v["Contract until"] = b["kontrat"].strip(); s_deg += 1
    elif gecerli(b["kontrat"]):
        v["Contract until"] = b["kontrat"].strip()
    if gecerli(b["boy"]):
        if b["boy"].strip() != (v.get("Height") or "").strip(): b_deg += 1
        v["Height"] = b["boy"].strip()
    if b["kulup"]:
        if b["kulup"] != (v.get("guncel_kulup") or ""): k_deg += 1
        v["guncel_kulup"] = b["kulup"]; v["guncel_kulup_t"] = BUGUN
    v["_sd_ts"] = BUGUN
    islenen += 1
    if islenen % 25 == 0:
        with open(YOL, "w", encoding="utf-8") as f:
            json.dump(sd, f, ensure_ascii=False, indent=2)
        print(f"  >> ara kayıt ({islenen}/{len(hedef)}) | kulüp {k_deg} · söz {s_deg} · boy {b_deg}")
    time.sleep(0.4)

with open(YOL, "w", encoding="utf-8") as f:
    json.dump(sd, f, ensure_ascii=False, indent=2)
print(f"BİTTİ. İşlenen {islenen} | değişen: kulüp {k_deg} · sözleşme {s_deg} · boy {b_deg} | ağ hatası {hata}")
