"""
Aynı takımın farklı isimlerini birleştirir ve veriyi yeniden kaydeder.
takim, tum_takimlar ve takim_detay alanlarını günceller.
"""
import json, csv

TAKIM_NORM = {
    "SERCAN İNŞAAT GAZİANTEP ALG SPOR":              "GAZİANTEP ALG SPOR",
    "GAZİANTEP ALG SPOR KULÜBÜ":                      "GAZİANTEP ALG SPOR",
    "ALG SPOR":                                        "GAZİANTEP ALG SPOR",
    "ÇEKMEKÖY BİLGİDOĞA":                             "ŞİLE BİLGİDOĞA",
    "ŞİLE BİLGİDOĞA SPORTİF YATIRIM HİZMETLERİ A.Ş": "ŞİLE BİLGİDOĞA",
    "ŞİLE BİLGİDOĞA SPORTİF YATIRIM HİZM":           "ŞİLE BİLGİDOĞA",
}

def norm(t):
    return TAKIM_NORM.get(t, t)

with open("oyuncular.json", encoding="utf-8") as f:
    oyuncular = json.load(f)

for o in oyuncular:
    # Ana takım
    o["takim"] = norm(o["takim"])

    # takim_detay içindeki takım adlarını normalize et, sonra aynı takımları birleştir
    yeni_detay = {}
    for d in o.get("takim_detay", []):
        t = norm(d["takim"])
        if t not in yeni_detay:
            yeni_detay[t] = {"takim": t, "mac": 0, "gol": 0, "sari": 0, "kirmizi": 0, "dakika": 0}
        for alan in ["mac", "gol", "sari", "kirmizi", "dakika"]:
            yeni_detay[t][alan] += d.get(alan, 0)
    # Maç sayısına göre sırala
    o["takim_detay"] = sorted(yeni_detay.values(), key=lambda x: -x["mac"])

    # tum_takimlar yeniden oluştur
    o["tum_takimlar"] = " / ".join(d["takim"] for d in o["takim_detay"])

    # transfer: birden fazla farklı takım var mı?
    o["transfer"] = len(o["takim_detay"]) > 1

    # Birincil takımı güncelle (en çok maç)
    if o["takim_detay"]:
        o["takim"] = o["takim_detay"][0]["takim"]

with open("oyuncular.json", "w", encoding="utf-8") as f:
    json.dump(oyuncular, f, ensure_ascii=False, indent=2)

with open("kadınlar_super_ligi_2026.csv", "w", newline="", encoding="utf-8-sig") as f:
    alan_adlari = [k for k in oyuncular[0].keys() if k != "takim_detay"]
    writer = csv.DictWriter(f, fieldnames=alan_adlari)
    writer.writeheader()
    for o in oyuncular:
        satir = {k: v for k, v in o.items() if k != "takim_detay"}
        writer.writerow(satir)

takimlar = sorted(set(o["takim"] for o in oyuncular))
transfer_sayisi = sum(1 for o in oyuncular if o["transfer"])
print(f"Güncellendi: {len(oyuncular)} oyuncu, {len(takimlar)} takım, {transfer_sayisi} transfer\n")
for t in takimlar:
    print(f"  {t}")
