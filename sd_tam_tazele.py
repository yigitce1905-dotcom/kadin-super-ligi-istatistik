"""SoccerDonna TAM künye tazeleme — tek profil çekişinde tablodaki tüm SD metrikleri.

Alanlar: Market value, Position, Contract until, Age, Date of birth, Height, Foot,
güncel kulüp (guncel_kulup). Maç/gol/asist ayrı: scrape_leistungsdaten.py.

NEDEN (2026-11-10): sd_profil_tazele.py 'Market value' ve 'Position'ı hiç
güncellemiyordu; sd_guncelle.py yalnız kulüp+sözleşme+boy alıyordu. Piyasa
değerleri ilk çekildikleri günde kalmıştı.

Kurallar:
  • SD bir alanı '?', 'unknown' ya da boş verirse eldeki değer KORUNUR.
  • Kulüp mantığı sd_guncelle.py ile aynı (milli takım bağlantıları atlanır).
  • Resumable: bugün işlenenler (_tam_ts) atlanır; her 25 oyuncuda ara kayıt.
  • Üst üste 8 ağ/403 hatasında durur (SD'yi zorlamamak için).

Kullanım:
    python sd_tam_tazele.py                 # iki dosya, hepsi (yazar)
    python sd_tam_tazele.py --kuru          # yazmadan rapor
    python sd_tam_tazele.py --limit=20      # deneme
    python sd_tam_tazele.py --dosya=scouting_sd_profiller.json
"""
import datetime
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

KOK = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}
ALANLAR = ("Market value", "Position", "Contract until", "Age", "Date of birth", "Height", "Foot")
VARSAYILAN = ["scouting_sd_profiller.json", "soccerdonna_profiller.json"]
BUGUN = datetime.date.today().isoformat()
BEKLE = 0.6
try:
    from scrape_leistungsdaten import ULKE_SLUGLARI
except Exception:
    ULKE_SLUGLARI = set()


def _ulke_mu(href):
    m = re.search(r"/([a-z-]+)/(?:historische-kader|startseite)/verein_", href)
    return bool(m) and re.sub(r"-u-?\d+$", "", m.group(1).rstrip("-")) in ULKE_SLUGLARI


def gecerli(x):
    return bool(x) and str(x).strip().lower() not in ("", "?", "-", "—", "unbekannt", "unknown")


def profil_cek(url):
    """{alan: değer, '_kulup': ...}. Ağ hatasında istisna fırlatır."""
    r = requests.get(url, headers=H, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = {}
    for row in soup.select("table tr"):
        c = [x.get_text(strip=True) for x in row.select("td")]
        if len(c) >= 2 and c[0]:
            k = c[0].rstrip(":")
            if k in ALANLAR and k not in out:
                out[k] = c[1]
    baslik = soup.find("table")
    metin = baslik.get_text(" ", strip=True).lower() if baslik else ""
    kulup = None
    if "vereinslos" in metin or "without club" in metin or "clubless" in metin:
        kulup = "Serbest"
    else:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "verein_" not in href or _ulke_mu(href):
                continue
            ad = a.get_text(strip=True)
            if ad.lower() == "delete player":
                continue
            if ad.lower() in ("vereinslos", "without club"):
                kulup = "Serbest"; break
            if ad.lower() in ("unbekannt", "unknown", "karriereende"):
                break
            if ad and ad != "-" and not ad.isdigit():
                kulup = ad; break
    out["_kulup"] = kulup
    return out


def tazele(yol, yaz, limit):
    veri = json.load(open(yol, encoding="utf-8"))
    hedef = [k for k, v in veri.items()
             if isinstance(v, dict) and v.get("profil_url") and not v.get("bulunamadi")
             and v.get("_tam_ts") != BUGUN]
    if limit:
        hedef = hedef[:limit]
    print(f"\n=== {yol.name}: {len(veri)} kayıt, tazelenecek {len(hedef)} ===", flush=True)
    say = {k: 0 for k in ALANLAR + ("kulüp",)}
    hata = ardisik = islenen = 0
    for i, isim in enumerate(hedef, 1):
        v = veri[isim]
        try:
            y = profil_cek(v["profil_url"])
            ardisik = 0
        except Exception as e:
            hata += 1; ardisik += 1
            print(f"[{i}/{len(hedef)}] {isim[:32]:32} HATA {type(e).__name__}: {str(e)[:60]}", flush=True)
            if ardisik >= 8:
                print("!! Üst üste 8 hata — durduruldu. Daha sonra tekrar çalıştır (kaldığı yerden devam eder).")
                break
            time.sleep(5 * ardisik)
            continue
        degis = []
        for k in ALANLAR:
            yeni = (y.get(k) or "").strip()
            if not gecerli(yeni):
                continue
            eski = str(v.get(k) or "").strip()
            if yeni != eski:
                say[k] += 1
                degis.append(f"{k}: {eski or '—'} → {yeni}")
                if yaz:
                    v[k] = yeni
        if y.get("_kulup"):
            if y["_kulup"] != (v.get("guncel_kulup") or ""):
                say["kulüp"] += 1
                degis.append(f"kulüp: {v.get('guncel_kulup') or '—'} → {y['_kulup']}")
            if yaz:
                v["guncel_kulup"] = y["_kulup"]; v["guncel_kulup_t"] = BUGUN
        if yaz:
            v["_tam_ts"] = BUGUN
            v["kunye_guncelleme"] = BUGUN
            v["_sd_ts"] = BUGUN
        islenen += 1
        if degis:
            print(f"[{i}/{len(hedef)}] {isim[:32]:32} " + " · ".join(degis)[:160], flush=True)
        if yaz and islenen % 25 == 0:
            json.dump(veri, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  >> ara kayıt {islenen}/{len(hedef)}", flush=True)
        time.sleep(BEKLE)
    if yaz:
        json.dump(veri, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"--- {yol.name}: işlenen {islenen} · hata {hata} · değişen: "
          + ", ".join(f"{k} {n}" for k, n in say.items()), flush=True)
    return say


def deger_gecmisi_yaz(dosyalar):
    """Piyasa değeri geçmişi: deger_gecmisi.json = {isim: [[tarih, euro], ...]}.
    Değer ilk kez görüldüğünde ya da son kayıttan farklıysa yeni satır eklenir
    (aynı değer tekrar yazılmaz). İleride 'değeri yükselenler/düşenler' listesi
    ve profilde değer grafiği için — veri ancak biriktikçe anlam kazanır."""
    yol = KOK / "deger_gecmisi.json"
    gecmis = json.load(open(yol, encoding="utf-8")) if yol.exists() else {}
    eklenen = 0
    for ad in dosyalar:
        f = KOK / ad
        if not f.exists():
            continue
        for isim, v in json.load(open(f, encoding="utf-8")).items():
            if not isinstance(v, dict) or v.get("bulunamadi"):
                continue
            mv = str(v.get("Market value") or "")
            if not gecerli(mv):
                continue
            rakam = re.sub(r"[^0-9]", "", mv)
            if not rakam:
                continue
            deger = int(rakam)
            tarih = v.get("_tam_ts") or BUGUN
            liste = gecmis.setdefault(isim, [])
            if not liste or liste[-1][1] != deger:
                if liste and liste[-1][0] == tarih:
                    liste[-1][1] = deger          # aynı gün ikinci çekim: üzerine yaz
                else:
                    liste.append([tarih, deger])
                eklenen += 1
    json.dump(gecmis, open(yol, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"deger_gecmisi.json: {len(gecmis)} oyuncu, bu çalışmada {eklenen} yeni kayıt", flush=True)


def main():
    yaz = "--kuru" not in sys.argv
    limit = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), 0)
    dosyalar = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--dosya=")] or VARSAYILAN
    if "--sadece-gecmis" not in sys.argv:      # yalnız değer geçmişini yaz, SD'ye gitme
        for ad in dosyalar:
            tazele(KOK / ad, yaz, limit)
    if yaz:
        deger_gecmisi_yaz(dosyalar)
    print("\nBİTTİ" + ("" if yaz else "  [KURU — yazılmadı]"))


if __name__ == "__main__":
    main()
