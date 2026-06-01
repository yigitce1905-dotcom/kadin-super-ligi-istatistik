"""
SoccerDonna Zenginleştirme Scraper'ı
oyuncular.json'daki her oyuncuyu SoccerDonna'da arar,
profil bilgilerini çekip soccerdonna_profiller.json'a kaydeder.
"""

import json, re, time, unicodedata
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

CIKTI     = "soccerdonna_profiller.json"
BEKLEME   = 1.5    # istek arası bekleme (saniye)
ES_SINIRI = 0.55   # fuzzy match eşiği (0-1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.soccerdonna.de/en/",
}


def temizle(metin: str) -> str:
    """Büyük harf, Türkçe/özel karakter → ASCII benzeri karşılaştırma için."""
    metin = metin.upper().strip()
    # Unicode normalize: "Č" → "C" gibi
    metin = unicodedata.normalize("NFD", metin)
    metin = "".join(c for c in metin if unicodedata.category(c) != "Mn")
    return metin


def eslesme_skoru(isim1: str, isim2: str) -> float:
    return SequenceMatcher(None, temizle(isim1), temizle(isim2)).ratio()


def soyadi_cikart(tam_isim: str) -> str:
    """Son kelimeyi soyad olarak döndür."""
    parcalar = tam_isim.strip().split()
    return parcalar[-1] if parcalar else tam_isim


def ara(session, soyad: str):
    """SoccerDonna'da soyada göre ara. {isim: ..., url: ...} listesi döner."""
    slug = soyad.lower().replace(" ", "-")
    url  = f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html"
    try:
        r = session.get(url, params={"quicksearch": soyad}, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.content, "lxml")
        sonuclar = []
        for a in soup.find_all("a", href=re.compile(r"/profil/spieler_\d+")):
            isim = a.get_text(strip=True)
            if isim and len(isim) > 2:
                tam_url = "https://www.soccerdonna.de" + a["href"]
                sonuclar.append({"isim": isim, "url": tam_url})
        return sonuclar
    except Exception:
        return []


def profil_cek(session, profil_url: str) -> dict:
    """Profil sayfasından tüm bilgileri çeker."""
    try:
        r = session.get(profil_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.content, "lxml")

        veri = {"profil_url": profil_url}

        # Bilgi tablosunu bul
        GECERLI_ANAHTARLAR = {
            "Date of birth", "Place of birth", "Age", "Name in native country",
            "Height", "Nationality", "2nd Nationality", "Position", "Foot",
            "Market value", "Contract until", "Outfitter", "Debut (Club)"
        }
        for tablo in soup.find_all("table"):
            txt = tablo.get_text(" ", strip=True)
            if "Date of birth" not in txt and "Position" not in txt:
                continue
            for tr in tablo.find_all("tr"):
                huc = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if len(huc) >= 2:
                    anahtar = huc[0].rstrip(":").strip()
                    deger   = huc[1].strip()
                    if anahtar in GECERLI_ANAHTARLAR and deger:
                        veri[anahtar] = deger
            break

        # Kulüp fotoğraf alt metni (bazen mevcut kulüp burada)
        img = soup.find("img", {"class": re.compile(r"vereinlogo|club")})
        if img and img.get("alt"):
            veri["Mevcut Kulüp"] = img["alt"]

        return veri
    except Exception:
        return {}


def ana_calistir():
    print("=" * 60)
    print("  SoccerDonna Zenginleştirme Scraper'ı")
    print("=" * 60)

    with open("oyuncular.json", encoding="utf-8") as f:
        oyuncular = json.load(f)

    # Mevcut sonuçları yükle (kaldığı yerden devam)
    try:
        with open(CIKTI, encoding="utf-8") as f:
            mevcut = json.load(f)
    except FileNotFoundError:
        mevcut = {}

    session = requests.Session()
    basarili = len([v for v in mevcut.values() if v])
    atlan    = 0

    for i, oyuncu in enumerate(oyuncular, 1):
        tam_isim = oyuncu["oyuncu"]

        # Zaten işlendiyse atla
        if tam_isim in mevcut:
            atlan += 1
            continue

        soyad = soyadi_cikart(tam_isim)
        print(f"[{i:3d}/{len(oyuncular)}] {tam_isim[:40]:<40} (soyad: {soyad})")

        sonuclar = ara(session, soyad)
        time.sleep(BEKLEME)

        if not sonuclar:
            # İlk isimle dene
            ad = tam_isim.split()[0] if " " in tam_isim else tam_isim
            sonuclar = ara(session, ad)
            time.sleep(BEKLEME)

        # En iyi eşleşmeyi bul
        en_iyi = None
        en_iyi_skor = 0.0
        for sonuc in sonuclar:
            skor = eslesme_skoru(tam_isim, sonuc["isim"])
            if skor > en_iyi_skor:
                en_iyi_skor = skor
                en_iyi = sonuc

        if en_iyi and en_iyi_skor >= ES_SINIRI:
            print(f"    ✓ Bulundu: {en_iyi['isim']} (skor: {en_iyi_skor:.2f})")
            profil = profil_cek(session, en_iyi["url"])
            profil["sd_isim"]   = en_iyi["isim"]
            profil["es_skoru"]  = round(en_iyi_skor, 3)
            mevcut[tam_isim]    = profil
            basarili           += 1
            time.sleep(BEKLEME)
        else:
            print(f"    ✗ Bulunamadı (en iyi skor: {en_iyi_skor:.2f})")
            mevcut[tam_isim] = {}

        # Her 20 oyuncuda bir kaydet
        if i % 20 == 0:
            with open(CIKTI, "w", encoding="utf-8") as f:
                json.dump(mevcut, f, ensure_ascii=False, indent=2)
            print(f"    [Ara kayıt: {basarili} başarılı / {i} işlendi]")

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(mevcut, f, ensure_ascii=False, indent=2)

    print(f"\nBitti! {basarili}/{len(oyuncular)} oyuncu için profil çekildi → {CIKTI}")


if __name__ == "__main__":
    ana_calistir()
