# -*- coding: utf-8 -*-
"""
Baran'in WhatsApp'tan verdigi manuel SD linkleriyle eksik scouting oyuncularini
ekler; bulunamayan/cikarilanlari siler. Tek seferlik yardimci.

- 6 oyuncu: profil dogrudan verilen URL'den cekilir (es_skoru=1.0 manuel).
- Lorall Romain: sistemden tamamen silinir (kadro + sd profiller).
- Arna Asgeirsdottir: Baran'da yok -> dokunulmaz (bulunamadi kalir).

Kullanim:  python scrape_baran_eksik.py
"""
import json
from pathlib import Path
from scrape_scouting_eksik import profil_cek   # ayni klasor, SES(verify=False) hazir

DIZIN     = Path(__file__).parent
SD_YOL    = DIZIN / "scouting_sd_profiller.json"
KADRO_YOL = DIZIN / "scout_kadro_raporlar.json"

# (kadro anahtari -> SoccerDonna profil URL).  /tr/ -> /en/ (parser Ingilizce etiket okur)
EKLE = {
    "A. Le Moguédec":   "https://www.soccerdonna.de/en/anale-le-moguedec/profil/spieler_60148.html",
    "Sabrina D'Angelo": "https://www.soccerdonna.de/en/sabrina-dangelo/profil/spieler_17039.html",
    "Mun Eun-ju":       "https://www.soccerdonna.de/en/eun-joo-mun/profil/spieler_59779.html",
    "Zhu Yu":           "https://www.soccerdonna.de/en/yu-zhu/profil/spieler_44140.html",
    "Yang Lina":        "https://www.soccerdonna.de/en/lina-yang/profil/spieler_59390.html",
    "Shao Ziqin":       "https://www.soccerdonna.de/en/ziqin-shao/profil/spieler_71242.html",
}
SIL = ["Lorall Romain"]


def main():
    sd    = json.load(open(SD_YOL, encoding="utf-8"))
    kadro = json.load(open(KADRO_YOL, encoding="utf-8"))

    # 1) Manuel profil ekleme
    for isim, url in EKLE.items():
        if isim not in kadro:
            print(f"[ATLA] {isim} kadroda yok"); continue
        p = profil_cek(url)
        if not p or "Date of birth" not in p and "Position" not in p:
            print(f"[HATA] {isim}: profil cekilemedi -> {url}"); continue
        eski = sd.get(isim, {})
        p["sd_isim"]     = p.get("Name in native country") or isim
        p["es_skoru"]    = 1.0   # manuel link -> kesin
        p["vatandaslik"] = eski.get("vatandaslik", kadro[isim].get("vatandaslik", ""))
        p.pop("bulunamadi", None)
        sd[isim] = p
        print(f"[OK] {isim} | {p.get('Nationality','?')} | {p.get('Position','?')} | {url.split('/')[-1]}")

    # 2) Sistemden silme
    for isim in SIL:
        k = kadro.pop(isim, None)
        s = sd.pop(isim, None)
        print(f"[SIL] {isim} | kadro={'-' if k is None else 'silindi'} | sd={'-' if s is None else 'silindi'}")

    json.dump(sd,    open(SD_YOL,    "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(kadro, open(KADRO_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    kalan = [n for n, v in sd.items() if isinstance(v, dict) and v.get("bulunamadi")]
    print(f"\n[BITTI] kadro={len(kadro)} sd={len(sd)} | hala bulunamadi: {kalan}")


if __name__ == "__main__":
    main()
