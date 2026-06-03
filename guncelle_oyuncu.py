"""
Tek oyuncunun SoccerDonna verisini günceller.
Kullanım: python guncelle_oyuncu.py <index> <soccerdonna_url>
Örnek:    python guncelle_oyuncu.py 102 https://www.soccerdonna.de/en/izzy-daquila/profil/spieler_99999.html
"""
import json, sys, requests
from bs4 import BeautifulSoup
from pathlib import Path

JSON_YOL = Path(__file__).parent / "scouting_sd_profiller.json"
HEADERS   = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

if len(sys.argv) < 3:
    print("Kullanım: python guncelle_oyuncu.py <index> <url>")
    sys.exit(1)

idx = int(sys.argv[1])
url = sys.argv[2].replace("/tr/", "/en/")  # tr → en'e çevir

with open(JSON_YOL, encoding="utf-8") as f:
    sd = json.load(f)

keys = list(sd.keys())
if idx >= len(keys):
    print(f"Hata: index {idx} yok (max {len(keys)-1})")
    sys.exit(1)

isim = keys[idx]
print(f"Güncelleniyor [{idx}]: {isim}")
print(f"URL: {url}")

r    = requests.get(url, headers=HEADERS, timeout=10)
soup = BeautifulSoup(r.text, "html.parser")

data = {}
for row in soup.select("table tr"):
    cells = [c.get_text(strip=True) for c in row.select("td")]
    if len(cells) >= 2 and cells[0]:
        key = cells[0].rstrip(":")
        if key not in ("Market value", "2.Club (Number)"):
            data[key] = cells[1]

for tablo in soup.select("table"):
    if "Competition" in [th.get_text(strip=True) for th in tablo.select("th")]:
        sezon_rows = []
        for sat in tablo.select("tr"):
            cells = [td.get_text(strip=True) for td in sat.select("td")]
            if len(cells) >= 3 and cells[0] and cells[1]:
                try:
                    if int(cells[1]) == 0:
                        continue
                except:
                    pass
                sezon_rows.append(cells)
        if sezon_rows:
            data["sezon_istatistikleri"] = sezon_rows
        break

data["profil_url"] = url
vat = sd[isim].get("vatandaslik", "")
sd[isim] = data
sd[isim]["vatandaslik"] = vat

with open(JSON_YOL, "w", encoding="utf-8") as f:
    json.dump(sd, f, ensure_ascii=False, indent=2)

print(f"OK — Mevki: {data.get('Position','?')} | Doğum: {data.get('Date of birth','?')}")
