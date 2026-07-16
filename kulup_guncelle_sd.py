# -*- coding: utf-8 -*-
"""SoccerDonna profil sayfasından GÜNCEL KULÜBÜ çekip SD profil JSON'larına yazar.

Her kayda `guncel_kulup` (+ `guncel_kulup_t` tarih damgası) ekler; kulüpsüz
oyuncular "Serbest" olur. fetch_scout_kadro.py bu alanı sheet kulübünün
önüne koyar (SD > sheet), böylece sitede görünen takım SD kadar güncel kalır.

Kullanım:  python kulup_guncelle_sd.py            # iki dosya, bugün damgasızlar
           python kulup_guncelle_sd.py --zorla    # damga bakma, hepsini tazele
Kesilirse yeniden çalıştır — bugün damgalılar atlanır (25'te bir ara kayıt).
"""
import json, re, sys, time
from datetime import date
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
KOK = Path(__file__).parent
DOSYALAR = ["scouting_sd_profiller.json", "soccerdonna_profiller.json"]
BUGUN = date.today().isoformat()

try:
    from scrape_leistungsdaten import ULKE_SLUGLARI
except Exception:
    ULKE_SLUGLARI = set()

def _ulke_mu(href: str) -> bool:
    m = re.search(r"/([a-z-]+)/(?:historische-kader|startseite)/verein_", href)
    if not m:
        return False
    return re.sub(r"-u-?\d+$", "", m.group(1).rstrip("-")) in ULKE_SLUGLARI

def profil_kulup(url: str) -> str | None:
    """Profil sayfası başlığındaki kulüp. '' = hata, 'Serbest' = kulüpsüz."""
    try:
        r = requests.get(url, headers=H, timeout=14)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None
    # başlık bölgesi: ilk tabloda oyuncu adı + kulüp,lig satırı bulunur
    baslik = soup.find("table")
    metin = baslik.get_text(" ", strip=True).lower() if baslik else ""
    if "vereinslos" in metin or "without club" in metin or "clubless" in metin:
        return "Serbest"
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "verein_" not in href:
            continue
        if _ulke_mu(href):
            continue
        ad = a.get_text(strip=True)
        if ad.lower() in ("vereinslos", "without club"):
            return "Serbest"
        if ad.lower() in ("unbekannt", "unknown", "karriereende"):
            return None                      # SD bilmiyor — sheet kulübü kalsın
        if ad and ad not in ("-",) and not ad.isdigit():
            return ad
    if "karriereende" in r.text.lower():
        return "(Kariyer sonu)"
    return None

def isle(dosya: str, zorla: bool) -> None:
    yol = KOK / dosya
    if not yol.exists():
        return
    sd = json.load(open(yol, encoding="utf-8"))
    hedef = [k for k, v in sd.items() if isinstance(v, dict) and v.get("profil_url")
             and not v.get("bulunamadi")
             and (zorla or v.get("guncel_kulup_t") != BUGUN)]
    print(f"\n── {dosya}: {len(hedef)} profil taranacak ──")
    ok = 0
    for i, k in enumerate(hedef, 1):
        klp = profil_kulup(sd[k]["profil_url"])
        if klp is not None:
            sd[k]["guncel_kulup"] = klp
            ok += 1
        sd[k]["guncel_kulup_t"] = BUGUN     # hata da damgalanır (sonsuz döngü olmasın)
        if i % 25 == 0:
            json.dump(sd, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  [{i}/{len(hedef)}] ara kayıt (kulüp bulunan: {ok})")
        time.sleep(0.3)
    json.dump(sd, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  bitti: {ok}/{len(hedef)} kulüp yazıldı")

if __name__ == "__main__":
    zorla = "--zorla" in sys.argv
    for d in DOSYALAR:
        isle(d, zorla)
