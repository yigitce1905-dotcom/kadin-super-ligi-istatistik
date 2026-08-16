# -*- coding: utf-8 -*-
"""SoccerDonna künye bilgilerini TAZELER (sözleşme, kulüp, yaş, değer).

NEDEN: profiller bir kez çekilip dosyada bekliyordu; sözleşme yenilendiğinde
kimse fark etmiyordu. Örnek (2026-08-17): Busem Şeker'in sözleşmesi SD'de
30.06.2027 olmuş, bizim önbellek 13 gün eski 31.05.2026'da kalmıştı — üstelik
o tarih ÇOKTAN GEÇMİŞTİ ve kimse görmedi.

Mevcut `soccerdonna_scraper.py` her oyuncuyu SD'de ARAYARAK bulur (yavaş,
1.5 sn/oyuncu + arama). Bu script arama yapmaz: elimizdeki `profil_url`u
doğrudan çeker, yalnızca künye alanlarını günceller. Nitelik/rapor verisine
DOKUNMAZ.

Kullanım:
    python sd_profil_tazele.py                 # kuru çalışma (rapor)
    python sd_profil_tazele.py --yaz           # dosyaları güncelle
    python sd_profil_tazele.py --yaz --gun=14  # 14 günden eski olanlar (varsayılan 7)
    python sd_profil_tazele.py --dosya=scouting_sd_profiller.json
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

KOK = Path(__file__).parent
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
# Yalnızca bu alanlar güncellenir — scout/nitelik verisine dokunulmaz
KUNYE = ("Date of birth", "Age", "Height", "Foot", "Nationality",
         "Current club", "Contract until", "Place of birth")
VARSAYILAN = ["soccerdonna_profiller.json", "scouting_sd_profiller.json"]


def profil_cek(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    s = BeautifulSoup(r.text, "html.parser")
    d = {}
    for row in s.select("table tr"):
        c = [x.get_text(strip=True) for x in row.select("td")]
        if len(c) >= 2 and c[0]:
            k = c[0].rstrip(":")
            if k in KUNYE:
                d[k] = c[1]
    return d


def tazele(yol: Path, yaz: bool, gun: int, limit: int) -> tuple:
    veri = json.load(open(yol, encoding="utf-8"))
    esik = (date.today() - timedelta(days=gun)).isoformat()

    hedef = []
    for isim, v in veri.items():
        if not isinstance(v, dict) or not v.get("profil_url"):
            continue
        if (v.get("kunye_guncelleme") or "") >= esik:
            continue           # yeterince taze
        hedef.append(isim)
    hedef = hedef[:limit] if limit else hedef

    print(f"\n=== {yol.name} — {len(veri)} kayıt, tazelenecek {len(hedef)} "
          f"({gun} günden eski) ===")
    degisim = []
    hata = 0
    for i, isim in enumerate(hedef, 1):
        v = veri[isim]
        try:
            yeni = profil_cek(v["profil_url"])
        except Exception as e:
            hata += 1
            print(f"[{i}/{len(hedef)}] {isim[:30]:30} HATA {type(e).__name__}")
            time.sleep(1.0)
            continue
        fark = {k: (v.get(k), yeni[k]) for k in yeni
                if str(v.get(k) or "").strip() != str(yeni[k]).strip()}
        if fark:
            degisim.append((isim, fark))
            ozet = " · ".join(f"{k}: {a or '—'} → {b}" for k, (a, b) in fark.items())
            print(f"[{i}/{len(hedef)}] {isim[:30]:30} {ozet[:110]}")
        if yaz:
            v.update(yeni)
            v["kunye_guncelleme"] = date.today().isoformat()
        time.sleep(0.8)

    if yaz:
        json.dump(veri, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return len(hedef), degisim, hata


def main():
    yaz = "--yaz" in sys.argv
    gun = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--gun=")), 7)
    limit = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), 0)
    dosyalar = [a.split("=")[1] for a in sys.argv if a.startswith("--dosya=")] or VARSAYILAN

    top_h = top_d = top_e = 0
    for ad in dosyalar:
        yol = KOK / ad
        if not yol.exists():
            print(f"{ad}: yok, atlandı")
            continue
        h, d, e = tazele(yol, yaz, gun, limit)
        top_h += h
        top_d += len(d)
        top_e += e
        # Sözleşmesi geçmişte kalanları ayrıca uyar — pazarlık fırsatı
        gecmis = []
        for isim, v in json.load(open(yol, encoding="utf-8")).items():
            if not isinstance(v, dict):
                continue
            s = (v.get("Contract until") or "").strip()
            try:
                if s and datetime.strptime(s, "%d.%m.%Y").date() < date.today():
                    gecmis.append((isim, s))
            except ValueError:
                pass
        if gecmis:
            # DİKKAT: "SD'de sözleşme bitti" ≠ "oyuncu serbest". SD yenilemeleri
            # geç işliyor — Yiğit doğruladı: Ebru Topçu ve Cansu Nur Kaya
            # yenilemişti ama SD hâlâ eski tarihi gösteriyordu. Nevcan Keleş ise
            # sakattı. Bu liste bir SONUÇ değil, TEYİT KUYRUĞUDUR.
            print(f"  ! SD'de sözleşme tarihi geçmiş {len(gecmis)} kayıt — "
                  f"TEYİT GEREKLİ (SD yenilemeyi geç işleyebilir, serbest demek değil): "
                  + ", ".join(f"{a} ({b})" for a, b in gecmis[:5])
                  + (" ..." if len(gecmis) > 5 else ""))

    print(f"\nTOPLAM: {top_h} kontrol · {top_d} değişiklik · {top_e} hata"
          + ("" if yaz else "   [KURU MOD — yazılmadı, --yaz ekle]"))


if __name__ == "__main__":
    main()
