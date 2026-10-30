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
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}
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
        if ad.lower() == "delete player":        # SD sayfa bağlantısı, kulüp değil
            continue
        if ad.lower() in ("vereinslos", "without club"):
            return "Serbest"
        if ad.lower() in ("unbekannt", "unknown", "karriereende"):
            return None                      # SD bilmiyor — sheet kulübü kalsın
        if ad and ad not in ("-",) and not ad.isdigit():
            return ad
    if "karriereende" in r.text.lower():
        return "(Kariyer sonu)"
    return None

# Süper Lig kulüplerinin SD adlarında geçen parçalar (ASCII'ye indirgenmiş, küçük harf)
_LIG_PARCA = ("fenerbah", "galatasaray", "besiktas", "trabzon", "fomget", "ankara", "amed",
              "hakkari", "unye", "giresun", "1207", "antalya", "yuksekova", "sile", "bilgi doga",
              "bilgidoga", "cekmekoy", "haymana", "bakirkoy", "kayseri", "sultanbeyli")


def _ascii(s: str) -> str:
    import unicodedata
    s = (s or "").replace("ı", "i").replace("İ", "I")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def aktif_serbest_temizle(sd: dict) -> int:
    """SD oyuncuyu 'Serbest' ya da lig DIŞI bir kulüpte gösteriyor ama oyuncu SON 2 lig
    haftasında maça çıkmış → SD gecikmiş (yeni tescil). guncel_kulup silinir ki site TFF
    takımını göstersin. Örnekler: 2026-10-19 Sibel Duman/Bakırköy ve Yağmur Özkumru/Haymana
    (SD'de kulüpsüz); 2026-10-30 María Sánchez (SD: Águila Roja) ve Raheemot Adebayo
    (SD: Yelimay Semey) — ikisi de son haftalarda Bakırköy/Haymana'da oynadı.
    Lig İÇİ kulüp farkına dokunulmaz: o gerçek transfer olabilir (Yetunde Ünye→Bakırköy)."""
    yol = KOK / "oyuncular.json"
    if not yol.exists():
        return 0
    oy = json.load(open(yol, encoding="utf-8"))
    son = max((m["hafta"] for o in oy for m in o.get("mac_gecmisi", [])), default=0)
    n = 0
    for o in oy:
        v = sd.get(o["oyuncu"])
        if not isinstance(v, dict) or not v.get("guncel_kulup"):
            continue
        gk = v["guncel_kulup"]
        lig_disi = gk == "Serbest" or not any(p in _ascii(gk) for p in _LIG_PARCA)
        if lig_disi and any(m["hafta"] >= son - 1 and m.get("dakika", 0) > 0
                            for m in o.get("mac_gecmisi", [])):
            v.pop("guncel_kulup", None)
            n += 1
    return n


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
    if dosya == "soccerdonna_profiller.json":
        print(f"  aktif oynayıp SD'de Serbest/lig dışı görünen (düzeltildi): {aktif_serbest_temizle(sd)}")
    json.dump(sd, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  bitti: {ok}/{len(hedef)} kulüp yazıldı")

if __name__ == "__main__":
    zorla = "--zorla" in sys.argv
    for d in DOSYALAR:
        isle(d, zorla)
