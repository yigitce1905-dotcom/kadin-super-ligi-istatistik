# -*- coding: utf-8 -*-
"""Tek seferlik: scraper_arsiv.py'nin ESKI kod ile (henuz duzeltme oncesi calisan
arka plan islemi) HAM dict formatinda yazdigi arsiv_*.json dosyalarini,
app.py'nin bekledigi donusturulmus LISTE formatina (oyuncular.json ile ayni) cevirir.
Kullanim: python _arsiv_donustur.py arsiv_2024_25.json arsiv_2023_24.json"""
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
import scraper_arsiv as sa

for dosya in sys.argv[1:]:
    with open(dosya, encoding="utf-8") as f:
        veri = json.load(f)
    if isinstance(veri, list):
        print(f"[ATLA] {dosya} zaten liste formatinda.")
        continue
    liste = sa._oyuncu_dict_to_liste(veri)
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=1)
    print(f"[OK] {dosya}: {len(liste)} oyuncu -> liste formatina donusturuldu.")
