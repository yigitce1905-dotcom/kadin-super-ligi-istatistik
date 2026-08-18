# -*- coding: utf-8 -*-
"""Notlandırılmamış oyuncular için ÖNCELİK LİSTESİ (Baran'ın çalışma sırası).

NEDEN BU DOSYA VAR
Dünya havuzunda 469 oyuncu henüz notlandırılmamış. Hepsini sırayla notlamak
gerçekçi değil ve gerekli de değil: çoğu, kulüplere sunacağımız hiçbir
senaryoda karşımıza çıkmayacak isimler. Bu script "önce hangisi" sorusunu
elimizdeki nesnel veriden cevaplar.

ÖNCELİK PUANI (0-11)
  +3  üst düzey ligde oynuyor (WSL, NWSL, Bundesliga, Liga F, Serie A,
      Première Ligue, Damallsvenskan, Toppserien, Eredivisie, A-Liga, Liga MX)
  +3  şu an serbest       → hemen transfer edilebilir
  +2  sözleşmesi 2026'da biter → Ocak penceresine düşer
  +2  25/26'da 900+ dakika  (+1 için 300+)  → gerçekten oynuyor
  +1  23 yaş ve altı        → gelişime açık, satış değeri yüksek

NOT: bu bir DEĞERLENDİRME DEĞİLDİR. Oyuncunun iyi olup olmadığı hakkında
hiçbir şey söylemez; yalnızca "bu oyuncuyu izlemek bizim için ne kadar acil"
sorusunu cevaplar. Nitelik notlarını yalnızca maçı izleyen insan verir.

Kullanım:
    python notlanacak_oncelik.py            # özet + ilk 25
    python notlanacak_oncelik.py --csv      # Excel'de açılacak tam liste
"""
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
CIKTI = Path.home() / "Desktop" / "NOTLANACAK_oncelik_listesi.csv"

SERBEST = {"serbest", "free", "free agent", "vereinslos"}
UST_LIG = ("WSL", "NWSL", "Bundesliga", "Première Ligue", "Liga F", "Serie A",
           "Damallsvenskan", "Toppserien", "Eredivisie", "A-Liga", "Liga MX")


def dakika(isim, kar):
    return sum(s.get("dakika", 0) for s in (kar.get(isim, {}) or {}).get("sezonlar", [])
               if s.get("sezon") == "25/26" and not s.get("milli"))


def mac(isim, kar):
    return sum(s.get("mac", 0) for s in (kar.get(isim, {}) or {}).get("sezonlar", [])
               if s.get("sezon") == "25/26" and not s.get("milli"))


def yas_int(v):
    y = str(v.get("yas") or "")
    return int(y) if y.isdigit() else None


def puanla(isim, v, kar):
    lig = v.get("lig") or ""
    dk = dakika(isim, kar)
    y = yas_int(v)
    p, gerekce = 0, []
    if any(u in lig for u in UST_LIG):
        p += 3; gerekce.append("üst lig")
    if (v.get("kulup") or "").strip().lower() in SERBEST:
        p += 3; gerekce.append("serbest")
    if "2026" in str(v.get("sozlesme", "")):
        p += 2; gerekce.append("2026'da biter")
    if dk >= 900:
        p += 2; gerekce.append("çok oynuyor")
    elif dk >= 300:
        p += 1; gerekce.append("oynuyor")
    if y is not None and y <= 23:
        p += 1; gerekce.append("genç")
    return p, " · ".join(gerekce)


def main():
    d = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
    kar = json.load(open(KOK / "scouting_leistungsdaten.json", encoding="utf-8"))
    sd = json.load(open(KOK / "scouting_sd_profiller.json", encoding="utf-8"))

    satirlar = []
    for isim, v in d.items():
        if v.get("degerlendirildi"):
            continue
        p, gerekce = puanla(isim, v, kar)
        satirlar.append({
            "Öncelik": p,
            "Oyuncu": isim,
            "Gerekçe": gerekce,
            "Lig": v.get("lig", ""),
            "Kulüp": v.get("kulup", ""),
            "Mevki": "/".join(x for x in (v.get("mevki") or []) if x),
            "Yaş": v.get("yas", ""),
            "Boy": v.get("boy", ""),
            "Ayak": v.get("ayak", ""),
            "Uyruk": v.get("vatandaslik", ""),
            "Sözleşme": v.get("sozlesme", ""),
            "25/26 maç": mac(isim, kar),
            "25/26 dk": dakika(isim, kar),
            "SoccerDonna": (sd.get(isim, {}) or {}).get("profil_url", ""),
        })
    satirlar.sort(key=lambda r: (-r["Öncelik"], -r["25/26 dk"], r["Oyuncu"]))

    toplam = len(satirlar)
    kritik = [r for r in satirlar if r["Öncelik"] >= 5]
    orta = [r for r in satirlar if 3 <= r["Öncelik"] < 5]
    print(f"Notlandırılmamış oyuncu : {toplam}")
    print(f"  ÖNCE BUNLAR (puan ≥5) : {len(kritik)}")
    print(f"  sonra (3-4)           : {len(orta)}")
    print(f"  düşük öncelik (0-2)   : {toplam - len(kritik) - len(orta)}")

    if "--csv" in sys.argv:
        with open(CIKTI, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(satirlar[0]))
            w.writeheader()
            w.writerows(satirlar)
        print(f"\n✓ {CIKTI}")
        return

    print("\nİLK 25 — bu sırayla izlenmeli:\n")
    for i, r in enumerate(satirlar[:25], 1):
        print(f"{i:3}. [{r['Öncelik']:2}] {r['Oyuncu'][:26]:26} "
              f"{str(r['Lig'])[:18]:18} {str(r['Kulüp'])[:20]:20} "
              f"{str(r['Yaş']):>3}y {r['25/26 dk']:>5}dk   {r['Gerekçe']}")


if __name__ == "__main__":
    main()
