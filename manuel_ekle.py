"""
Manuel olarak verilen SoccerDonna URL'lerinden profil çekip JSON'a ekler.
Scraper bittikten sonra çalıştır.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import json, time, requests
from bs4 import BeautifulSoup
from soccerdonna_scraper import profil_cek

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

MANUEL = {
    "MARIE GISELE DIVINE NGAH MANGA":      "https://www.soccerdonna.de/en/marie-ngah/profil/spieler_37725.html",
    "NGO MBELECK GENEVIEVE EDITH":         "https://www.soccerdonna.de/en/genevieve-ngo-mbeleck/profil/spieler_28201.html",
    "DANA MARGARETHA WILHELMINA FOEDERER": "https://www.soccerdonna.de/en/dana-foederer/profil/spieler_35135.html",
    "PEREIRA DA SILVA SYLVIA BEATRIZ":         "https://www.soccerdonna.de/en/sylvia-da-silva/profil/spieler_113663.html",
    "MARIA ASUNCION QUINONES GOICOECHEA":      "https://www.soccerdonna.de/en/mariasun-quiones/profil/spieler_32231.html",
}

with open("soccerdonna_profiller.json", encoding="utf-8") as f:
    profiller = json.load(f)

session = requests.Session()

for oyuncu, url in MANUEL.items():
    print(f"Çekiliyor: {oyuncu}")
    profil = profil_cek(session, url)
    if profil:
        profil["sd_isim"]  = oyuncu
        profil["es_skoru"] = 1.0
        profiller[oyuncu]  = profil
        print(f"  ✓ Pozisyon: {profil.get('Position','?')} | Uyruk: {profil.get('Nationality','?')}")
    else:
        print(f"  ✗ Profil çekilemedi")
    time.sleep(1.5)

with open("soccerdonna_profiller.json", "w", encoding="utf-8") as f:
    json.dump(profiller, f, ensure_ascii=False, indent=2)

print("\nKaydedildi.")
