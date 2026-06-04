"""
SoccerDonna leistungsdaten scraper - tum scouting oyuncularinin kariyer istatistikleri
Cikti: scouting_leistungsdaten.json

Yapi:
{
  "Teodora Nicoara": {
    "sezonlar": [
      {"sezon":"24/25","kulup":"Fatih Vatan SK","lig":"Kadin Futbol Super Ligi",
       "mac":24,"gol":1,"asist":1,"sari":2,"dakika":1963}
    ],
    "guncelleme": "2026-06-03"
  }
}

Kullanim:
  python scrape_leistungsdaten.py           # tum oyuncular
  python scrape_leistungsdaten.py --eksik   # sadece JSON'da kaydi olmayanlar
  python scrape_leistungsdaten.py Izzy      # isimde 'Izzy' gecen oyuncular
"""

import json
import sys
import time
import re
from collections import Counter
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PROFILLER_YOL = Path(__file__).parent / "scouting_sd_profiller.json"
LEISTUNG_YOL  = Path(__file__).parent / "scouting_leistungsdaten.json"
HEADERS       = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BEKLEME       = 1.2
BUGUN         = date.today().isoformat()


def spieler_id_ve_slug(profil_url: str):
    sid  = re.search(r"spieler_(\d+)", profil_url)
    slug = re.search(r"/(?:en|de)/([^/]+)/profil/", profil_url)
    return (sid.group(1) if sid else None), (slug.group(1) if slug else None)


def leistung_url(sid: str, slug: str, yil: int | None = None) -> str:
    base = f"https://www.soccerdonna.de/en/{slug}/leistungsdaten/spieler_{sid}"
    return f"{base}_{yil}.html" if yil else f"{base}.html"


def sezon_yillarini_cek(soup: BeautifulSoup) -> list[int]:
    """Sayfadaki leistungsdaten linkleri / dropdown'dan mevcut yil listesi."""
    yillar = set()
    # <a href="...spieler_12345_2023.html">
    for a in soup.find_all("a", href=True):
        m = re.search(r"leistungsdaten/spieler_\d+_(\d{4})\.html", a["href"])
        if m:
            y = int(m.group(1))
            if 2010 <= y <= 2030:
                yillar.add(y)
    # <option value="...2023...">
    for opt in soup.select("select option"):
        m = re.search(r"(\d{4})", opt.get("value", ""))
        if m:
            y = int(m.group(1))
            if 2010 <= y <= 2030:
                yillar.add(y)
    return sorted(yillar, reverse=True)


# SoccerDonna ulke (milli takim) URL slug'lari — kulup sanilmasinlar diye elenir
ULKE_SLUGLARI = {
    "rumaenien", "deutschland", "frankreich", "polen", "bosnien-herzegowina",
    "nordirland", "italien", "spanien", "england", "niederlande", "belgien",
    "schweiz", "oesterreich", "tuerkei", "portugal", "schweden", "norwegen",
    "daenemark", "finnland", "island", "ukraine", "russland", "serbien",
    "kroatien", "slowenien", "slowakei", "tschechien", "ungarn", "griechenland",
    "bulgarien", "montenegro", "nordmazedonien", "albanien", "kosovo", "irland",
    "schottland", "wales", "usa", "kanada", "brasilien", "argentinien", "japan",
    "china", "australien", "mexiko", "kolumbien", "chile", "neuseeland",
    "weissrussland", "belarus", "litauen", "lettland", "estland", "georgien",
    "armenien", "aserbaidschan", "kasachstan", "israel", "zypern", "malta",
    "luxemburg", "moldau", "moldawien", "wales", "haiti", "ghana", "nigeria",
    "kamerun", "marokko", "suedafrika", "costa-rica", "kosta-rika",
}


def _ulke_slug_mu(href: str) -> bool:
    m = re.search(r"/([a-z-]+)/historische-kader/verein_", href)
    if not m:
        return False
    slug = m.group(1).rstrip("-")
    # U19/U17 gibi alt takimlar da milli: rumaenien-u19
    base = re.sub(r"-u-?\d+$", "", slug)
    return base in ULKE_SLUGLARI


def kulup_bul(soup: BeautifulSoup) -> str:
    """
    Maç tablosundaki '/verein_' linklerinden oyuncunun kulübünü bul.
    En sık geçen KULÜP (milli takim/ulke degil) = oyuncunun kulübü.
    """
    sayac = Counter()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/verein_" in href and "/historische-kader/" in href:
            if _ulke_slug_mu(href):
                continue  # milli takim — atla
            isim = a.get_text(strip=True)
            if isim and isim not in ("", "-"):
                sayac[isim] += 1
    if not sayac:
        return ""
    # Ek guvenlik: isimde milli takim kelimesi geceni dusur
    milli_kelimeler = {"national", "nationalmannschaft", "verband", "federation"}
    filtreli = {k: v for k, v in sayac.items()
                if not any(w in k.lower() for w in milli_kelimeler)}
    if filtreli:
        return max(filtreli, key=filtreli.get)
    return max(sayac, key=sayac.get)


def int_cevir(metin: str) -> int:
    """'1.963' veya '1,963' -> 1963; '-' -> 0"""
    temiz = metin.strip().replace(".", "").replace(",", "").replace("-", "").replace("'", "")
    return int(temiz) if temiz.isdigit() else 0


def milli_mi(lig: str) -> bool:
    """
    Lig adından milli takim turnuvasi mi kulup turnuvasi mi ayir.
    Champions League = kulup (oncelikli), digerleri heuristik.
    """
    l = lig.lower()
    # Kulup turnuvalari (oncelikli — milli kelimelerini ezer)
    if "champions league" in l:
        return False
    milli_kelimeler = (
        "nations league", "world cup", "euro qual", "em-qual", "em qual",
        "euro qualif", "qualification league", "qualification playoffs",
        "friendl", "freundschaft", "vier-nationen", "turnier", "tournament",
        "algarve", "cyprus women", "pinatar", "she believes", "olympi",
        "wm-qual", "wm qual",
    )
    if any(k in l for k in milli_kelimeler):
        return True
    if re.search(r"\bu-?(17|19|20|23)\b", l):
        return True
    return False


def ozet_tabloyu_parse(soup: BeautifulSoup, sezon: str, kulup: str, ulke: str = "") -> list[dict]:
    """
    'Competition / Matches / ...' baslikli ozet tabloyu parse et.
    Her satir bir lig/kupa = bir kayit.
    Milli takim turnuvalarinda kulup yerine oyuncunun ulkesi yazilir.
    """
    kayitlar = []
    for tablo in soup.select("table"):
        basliklar = [th.get_text(strip=True).lower() for th in tablo.select("th")]
        if "competition" not in basliklar and "wettbewerb" not in basliklar:
            continue
        if "matches" not in basliklar and "spiele" not in basliklar and "oys." not in basliklar:
            continue

        for tr in tablo.select("tr"):
            td_list = tr.select("td")
            if len(td_list) < 8:
                continue

            # td[0] = bos/resim, td[1] = lig adi, td[2] = mac sayisi, ...
            lig_td  = td_list[1]
            lig_adi = lig_td.get_text(strip=True)

            # Toplam/footer/gecersiz satirlari atla
            if not lig_adi:
                continue
            if lig_adi.lower().startswith(("total", "thereof", "gesamt")):
                continue
            # Sadece rakamdan olusan lig adi = toplam satiri
            if re.fullmatch(r"[\d\s]+", lig_adi):
                continue

            # Sayisal degerler: td[2]=mac, td[3]=gol, td[5]=asist, td[6]=sari, td[-1]=dakika
            # Son iki td genellikle formatlı + ham dakika
            # td[12] ham dakika (en sagliklisi)
            def td_val(idx):
                if idx < len(td_list):
                    return int_cevir(td_list[idx].get_text(strip=True))
                return 0

            mac    = td_val(2)
            gol    = td_val(3)
            # td[4] oz gol - atliyoruz
            asist  = td_val(5)
            sari   = td_val(6)
            # td[11] formatli dakika (1.963), td[12] ham (1963) - ham tercih
            dakika = td_val(12) if len(td_list) > 12 else td_val(11)
            if dakika == 0:
                dakika = td_val(11)

            if mac == 0:
                continue

            is_milli   = milli_mi(lig_adi)
            kulup_son  = (ulke or "Milli Takım") if is_milli else kulup

            kayitlar.append({
                "sezon":  sezon,
                "kulup":  kulup_son,
                "lig":    lig_adi,
                "mac":    mac,
                "gol":    gol,
                "asist":  asist,
                "sari":   sari,
                "dakika": dakika,
                "milli":  is_milli,
            })

        break  # Ilk eslesen tablodan cik

    return kayitlar


def oyuncu_cek(isim: str, profil_url: str, ulke: str = "") -> list[dict]:
    sid, slug = spieler_id_ve_slug(profil_url)
    if not sid or not slug:
        return []

    # 1. Varsayilan sayfa - su anki sezon + yil listesi
    url0 = leistung_url(sid, slug)
    try:
        r    = requests.get(url0, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [HATA] {isim}: {e}")
        return []

    # Mevcut sezon etiketini sayfadan bul
    mevcut_sezon = ""
    for eleman in soup.select(".saison, .season, h2, h3, .box-header"):
        m = re.search(r"(\d{2}/\d{2})", eleman.get_text())
        if m:
            mevcut_sezon = m.group(1)
            break

    sezon_yillari = sezon_yillarini_cek(soup)
    kulup0 = kulup_bul(soup)

    tum_kayitlar = []

    if not sezon_yillari:
        # Dropdown yok — sadece varsayilan sayfa
        tum_kayitlar.extend(
            ozet_tabloyu_parse(soup, mevcut_sezon or "?", kulup0, ulke))
        return tum_kayitlar

    # Tum yillari sirayla cek. En guncel yil (idx 0) = varsayilan sayfa,
    # tekrar istek atmadan ondan isle → duplikasyon olmaz.
    for idx, yil in enumerate(sezon_yillari):
        etiket = f"{str(yil)[2:]}/{str(yil+1)[2:]}"
        if idx == 0:
            tum_kayitlar.extend(ozet_tabloyu_parse(soup, etiket, kulup0, ulke))
            continue
        url_y = leistung_url(sid, slug, yil)
        try:
            r2     = requests.get(url_y, headers=HEADERS, timeout=12)
            soup2  = BeautifulSoup(r2.text, "html.parser")
            kulup2 = kulup_bul(soup2)
            tum_kayitlar.extend(ozet_tabloyu_parse(soup2, etiket, kulup2, ulke))
        except Exception as e:
            print(f"  [HATA] {etiket}: {e}")
        time.sleep(BEKLEME)

    return tum_kayitlar


def main():
    args = sys.argv[1:]

    # Kaynak secimi: --analig (Turkiye Super Ligi) veya varsayilan (scouting)
    if "--analig" in args:
        prof_yol  = Path(__file__).parent / "soccerdonna_profiller.json"
        cikti_yol = Path(__file__).parent / "analig_leistungsdaten.json"
    else:
        prof_yol  = PROFILLER_YOL
        cikti_yol = LEISTUNG_YOL

    with open(prof_yol, encoding="utf-8") as f:
        profiller = json.load(f)

    if cikti_yol.exists():
        with open(cikti_yol, encoding="utf-8") as f:
            leistung = json.load(f)
    else:
        leistung = {}

    sadece_eksik = "--eksik" in args
    arama        = next((a for a in args if not a.startswith("--")), None)

    hedefler = []
    for isim, veri in profiller.items():
        if isinstance(veri, str) or veri.get("bulunamadi"):
            continue
        profil_url = veri.get("profil_url", "")
        if not profil_url:
            continue
        if sadece_eksik and isim in leistung:
            continue
        if arama and arama.lower() not in isim.lower():
            continue
        ulke = veri.get("Nationality") or veri.get("vatandaslik") or ""
        hedefler.append((isim, profil_url, ulke))

    print(f"Hedef: {len(hedefler)} oyuncu")

    for i, (isim, profil_url, ulke) in enumerate(hedefler, 1):
        print(f"[{i}/{len(hedefler)}] {isim} ...", end=" ", flush=True)
        try:
            satirlar = oyuncu_cek(isim, profil_url, ulke)
            leistung[isim] = {"sezonlar": satirlar, "guncelleme": BUGUN}
            print(f"OK {len(satirlar)} satir")
        except Exception as e:
            print(f"HATA: {e}")

        if i % 10 == 0:
            with open(cikti_yol, "w", encoding="utf-8") as f:
                json.dump(leistung, f, ensure_ascii=False, indent=2)
            print(f"  [ara kayit: {i} oyuncu]")

    with open(cikti_yol, "w", encoding="utf-8") as f:
        json.dump(leistung, f, ensure_ascii=False, indent=2)
    print(f"\nTamamlandi: {cikti_yol}")


if __name__ == "__main__":
    main()
