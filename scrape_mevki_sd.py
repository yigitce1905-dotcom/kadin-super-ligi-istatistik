"""
SoccerDonna takım sayfalarından detaylı mevki kodlarını çeker.
Çıktı: manual_ages.json'a position override olarak eklenir.
"""
import json, requests, time, re
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# SoccerDonna kodu → Türkçe mevki
MEVKI_MAP = {
    "TW": "Goalkeeper",
    "RV": "Defender - Right Back",
    "LV": "Defender - Left Back",
    "IV": "Defender - Centre Back",
    "DM": "Midfield - Defensive Midfield",
    "ZM": "Midfield - Central Midfield",
    "OM": "Midfield - Attacking Midfield",
    "LM": "Midfield - Left Wing",
    "RM": "Midfield - Right Wing",
    "LA": "Striker - Left Wing",
    "RA": "Striker - Right Wing",
    "MS": "Striker - Centre Forward",
}

TAKIM_URLS = {
    "TRABZONSPOR A.Ş.":
        "https://www.soccerdonna.de/en/trabzonspor/startseite/verein_792.html",
    "BEŞİKTAŞ JK KADIN FUTBOL TAKIMI":
        "https://www.soccerdonna.de/en/besiktas-jk/startseite/verein_415.html",
    "FENERBAHÇE ARSAVEV KADIN FUTBOL TAKIMI":
        "https://www.soccerdonna.de/en/fenerbahce/startseite/verein_197.html",
    "GALATASARAY GAIN":
        "https://www.soccerdonna.de/en/galatasaray/startseite/verein_83.html",
    "GAZİANTEP ALG SPOR":
        "https://www.soccerdonna.de/en/alg-spor/startseite/verein_2282.html",
    "PROLİFT GİRESUN SANAYİSPOR":
        "https://www.soccerdonna.de/en/giresun-sanayispor/startseite/verein_1022.html",
    "ANKARA BÜYÜKŞEHİR BELEDİYESİ FOMGET SPOR KULÜBÜ":
        "https://www.soccerdonna.de/en/ankaragucu/startseite/verein_2596.html",
    "1207 ANTALYASPOR  KADIN FUTBOL KULÜBÜ":
        "https://www.soccerdonna.de/en/antalyaspor/startseite/verein_3039.html",
    "FATİH VATAN SPOR":
        "https://www.soccerdonna.de/en/fatih-vatan-spor/startseite/verein_2580.html",
    "AMED SPORTİF FAALİYETLER":
        "https://www.soccerdonna.de/en/amed-sportif/startseite/verein_2623.html",
    "HAKKARİGÜCÜ SPOR":
        "https://www.soccerdonna.de/en/hakkarigucu/startseite/verein_3756.html",
    "ÜNYE KADIN SPOR KULÜBÜ":
        "https://www.soccerdonna.de/en/unye-kadinspor/startseite/verein_3245.html",
    "ŞİLE BİLGİDOĞA":
        "https://www.soccerdonna.de/en/sile-bilgidoga/startseite/verein_3532.html",
    "YÜKSEKOVA SPOR KULÜBÜ":
        "https://www.soccerdonna.de/en/yuksekova-spor/startseite/verein_3891.html",
}


def cek_takim(url):
    r    = requests.get(url, headers=HEADERS, timeout=12)
    soup = BeautifulSoup(r.text, "html.parser")
    sonuc = {}
    for row in soup.select("table tr"):
        cells = [td.get_text(strip=True) for td in row.select("td")]
        if len(cells) >= 5 and cells[3] and cells[4] and "(" in cells[4]:
            isim  = cells[3].strip()
            mevki_raw = cells[4]  # örn: "Defence (RV)"
            match = re.search(r"\((\w+)\)", mevki_raw)
            if match:
                kod = match.group(1)
                sonuc[isim] = MEVKI_MAP.get(kod, None)
    return sonuc


def normalize(s):
    """Basit normalize: küçük harf, özel karakter temizle."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# Oyuncular.json'dan isim listesi
oyuncu_yol = Path(__file__).parent / "oyuncular.json"
with open(oyuncu_yol, encoding="utf-8") as f:
    oyuncular = json.load(f)

oyuncu_isimleri = {o["oyuncu"]: o["oyuncu"] for o in oyuncular}
norm_map = {normalize(k): k for k in oyuncu_isimleri}  # normalize → gerçek isim

# manual_ages.json yükle
manual_yol = Path(__file__).parent / "manual_ages.json"
with open(manual_yol, encoding="utf-8") as f:
    manual = json.load(f)

# Tüm takımları çek
tüm_sd = {}  # sd_isim → mevki
for takim, url in TAKIM_URLS.items():
    print(f"Çekiliyor: {takim}...")
    try:
        sonuc = cek_takim(url)
        print(f"  {len(sonuc)} oyuncu bulundu")
        tüm_sd.update(sonuc)
    except Exception as e:
        print(f"  HATA: {e}")
    time.sleep(0.8)

print(f"\nToplam SD kaydı: {len(tüm_sd)}")

# Eşleştir: SD ismi → oyuncular.json ismi
eslestir = {}
bulunamadi = []

for sd_isim, mevki in tüm_sd.items():
    if not mevki:
        continue
    norm_sd = normalize(sd_isim)
    # Birebir eşleşme
    if norm_sd in norm_map:
        eslestir[norm_map[norm_sd]] = mevki
    else:
        # Kısmi eşleşme: SD isminin tüm kelimeleri oyuncu isminde geçiyor mu
        bulundu = False
        for norm_oyuncu, gercek_isim in norm_map.items():
            if norm_sd in norm_oyuncu or norm_oyuncu in norm_sd:
                eslestir[gercek_isim] = mevki
                bulundu = True
                break
        if not bulundu:
            bulunamadi.append(sd_isim)

print(f"Eşleşen: {len(eslestir)} | Eşleşemeyen: {len(bulunamadi)}")
if bulunamadi:
    print("Eşleşemeyen SD isimleri:")
    for b in bulunamadi[:10]:
        print(f"  {b}")

# manual_ages.json güncelle — sadece position override
guncellenen = 0
for oyuncu_isim, mevki in eslestir.items():
    if oyuncu_isim in manual:
        if manual[oyuncu_isim].get("position") != mevki:
            manual[oyuncu_isim]["position"] = mevki
            guncellenen += 1
    else:
        manual[oyuncu_isim] = {"position": mevki}
        guncellenen += 1

with open(manual_yol, "w", encoding="utf-8") as f:
    json.dump(manual, f, ensure_ascii=False, indent=2)

print(f"\nmanual_ages.json güncellendi: {guncellenen} oyuncu")
