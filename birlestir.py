"""
Aynı takımın farklı isimlerini birleştirir ve veriyi yeniden kaydeder.
"""
import json, csv

TAKIM_NORM = {
    # ALG SPOR grubu → tek isim
    "SERCAN İNŞAAT GAZİANTEP ALG SPOR": "GAZİANTEP ALG SPOR",
    "GAZİANTEP ALG SPOR KULÜBÜ":        "GAZİANTEP ALG SPOR",
    "ALG SPOR":                          "GAZİANTEP ALG SPOR",

    # BİLGİDOĞA grubu → tek isim
    "ÇEKMEKÖY BİLGİDOĞA":                             "ŞİLE BİLGİDOĞA",
    "ŞİLE BİLGİDOĞA SPORTİF YATIRIM HİZMETLERİ A.Ş": "ŞİLE BİLGİDOĞA",
    "ŞİLE BİLGİDOĞA SPORTİF YATIRIM HİZM":           "ŞİLE BİLGİDOĞA",
}

with open("oyuncular.json", encoding="utf-8") as f:
    oyuncular = json.load(f)

for o in oyuncular:
    o["takim"] = TAKIM_NORM.get(o["takim"], o["takim"])

# Aynı kisiId'ye sahip oyuncular normalleşme sonrası birleşmez (farklı kisiId var),
# ama aynı oyuncunun iki farklı takım kaydı yoktu zaten — takım adı sadece güncellendi.

with open("oyuncular.json", "w", encoding="utf-8") as f:
    json.dump(oyuncular, f, ensure_ascii=False, indent=2)

with open("kadınlar_super_ligi_2026.csv", "w", newline="", encoding="utf-8-sig") as f:
    alan_adlari = list(oyuncular[0].keys()) if oyuncular else ["oyuncu","takim","mac_sayisi","gol_sayisi"]
    writer = csv.DictWriter(f, fieldnames=alan_adlari)
    writer.writeheader()
    writer.writerows(oyuncular)

# Özet
takimlar = sorted(set(o["takim"] for o in oyuncular))
print(f"Güncellendi. Toplam {len(oyuncular)} oyuncu, {len(takimlar)} takım:\n")
for t in takimlar:
    print(f"  {t}")
