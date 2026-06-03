"""
SoccerDonna scraper — scouting oyuncuları için
Yiğit.xlsx'ten isimleri okur, SoccerDonna'dan profil + son sezon istatistiklerini çeker.
Çıktı: scouting_sd_profiller.json
"""
import json
import time
import sys
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
CIKTI   = Path(__file__).parent / "scouting_sd_profiller.json"
EXCEL   = r"C:\Users\MSI\Desktop\Yiğit.xlsx"

# Mevcut JSON varsa yükle (kaldığı yerden devam)
if CIKTI.exists():
    with open(CIKTI, encoding="utf-8") as f:
        sonuclar = json.load(f)
else:
    sonuclar = {}


def sd_ara(isim: str) -> str | None:
    """SoccerDonna'da oyuncu ara, profil URL'sini döndür."""
    slug  = isim.lower().replace(" ", "-")
    query = isim.replace(" ", "+")
    url   = f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html?quicksearch={query}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True) if "spieler_" in a.get("href","")]
        return links[0] if links else None
    except Exception:
        return None


def sd_profil_cek(path: str) -> dict:
    """Profil sayfasından temel bilgi + son sezon istatistiklerini çek."""
    url  = "https://www.soccerdonna.de" + path
    try:
        r    = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return {}

    # Temel bilgiler
    data = {}
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 2 and cells[0]:
            key = cells[0].rstrip(":")
            if key not in ("Market value", "2.Club (Number)"):  # piyasa değeri istemiyoruz
                data[key] = cells[1]

    # Sezon istatistikleri — sadece en son sezon tablosunu al
    sezon_rows = []
    tablolar   = soup.select("table")
    for tablo in tablolar:
        basliklar = [th.get_text(strip=True) for th in tablo.select("th")]
        if "Competition" in basliklar or "Matches" in basliklar:
            satirlar = tablo.select("tr")
            for sat in satirlar:
                cells = [td.get_text(strip=True) for td in sat.select("td")]
                # Boş veya sadece ayırıcı satırları atla
                if len(cells) >= 3 and cells[0] and cells[1]:
                    # "Total:" satırı dahil et, ama boş maçları atla
                    mac_sayisi = cells[1] if len(cells) > 1 else ""
                    if mac_sayisi == "-" or mac_sayisi == "":
                        continue
                    try:
                        if int(mac_sayisi) == 0:
                            continue
                    except ValueError:
                        pass
                    sezon_rows.append(cells)
            break  # Sadece ilk istatistik tablosunu al (en son sezon)

    if sezon_rows:
        data["sezon_istatistikleri"] = sezon_rows

    data["profil_url"] = url
    return data


# Excel'i oku
df = pd.read_excel(EXCEL, header=None)
df.columns = ["isim", "soyisim", "yerli_isim", "vatan1", "vatan2"]

# İlk satır header değil, data — hepsini al
oyuncular = []
for _, row in df.iterrows():
    ad     = str(row["isim"]).strip()
    soyad  = str(row["soyisim"]).strip()
    tam    = f"{ad} {soyad}"
    vatan  = str(row["vatan1"]).strip()
    oyuncular.append({"tam_isim": tam, "vatandaslik": vatan})

print(f"Toplam oyuncu: {len(oyuncular)}")
print(f"Mevcut kayıt:  {len(sonuclar)}")
print()

yeni = 0
bulunamadi = []

for i, o in enumerate(oyuncular):
    tam = o["tam_isim"]

    # Zaten varsa atla
    if tam in sonuclar:
        print(f"[{i+1:3}/{len(oyuncular)}] ATLA  {tam}")
        continue

    print(f"[{i+1:3}/{len(oyuncular)}] ARA   {tam} ... ", end="", flush=True)

    path = sd_ara(tam)
    if not path:
        print("BULUNAMADI")
        bulunamadi.append(tam)
        sonuclar[tam] = {"vatandaslik": o["vatandaslik"], "bulunamadi": True}
        time.sleep(0.4)
        continue

    profil = sd_profil_cek(path)
    profil["vatandaslik"] = o["vatandaslik"]

    sonuclar[tam] = profil
    yeni += 1

    mac_bilgi = ""
    if "sezon_istatistikleri" in profil:
        mac_bilgi = f"| {len(profil['sezon_istatistikleri'])} satır istatistik"

    print(f"OK — {profil.get('Position','?')} {mac_bilgi}")

    # Her 10 oyuncuda bir kaydet
    if yeni % 10 == 0:
        with open(CIKTI, "w", encoding="utf-8") as f:
            json.dump(sonuclar, f, ensure_ascii=False, indent=2)
        print(f"  >> Ara kayıt yapıldı ({len(sonuclar)} kayıt)")

    time.sleep(0.5)  # sunucuyu yormamak için

# Final kayıt
with open(CIKTI, "w", encoding="utf-8") as f:
    json.dump(sonuclar, f, ensure_ascii=False, indent=2)

print()
print(f"Tamamlandı. Toplam: {len(sonuclar)} | Yeni: {yeni} | Bulunamadı: {len(bulunamadi)}")
if bulunamadi:
    print("Bulunamayanlar:")
    for b in bulunamadi:
        print(f"  - {b}")
