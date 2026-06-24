# -*- coding: utf-8 -*-
"""
Sco 🌍 sayfasındaki YENİ İŞLENMİŞ verileri scout_kadro_raporlar.json'a entegre eder
— HAM (değerlendirilmemiş) YENİ oyuncuları (Afrika milli takım bloğu vb.) HARİÇ TUTARAK.

Birleştirme kuralı:
  • Mevcut (commit'li) oyuncu     → canlı sheet'teki haliyle GÜNCELLE
                                    (sheet'te yapılan yeni scout değerlendirmelerini çeker)
  • Yeni + DEĞERLENDİRİLMİŞ       → EKLE
  • Yeni + HAM (değerlendirilmemiş) → ATLA   ← ham Afrika bloğu böyle elenir

Neden: fetch_scout_kadro.py'nin gap-stop'u (≥20 boş satır) artık tetiklenmiyor
(blok arası boşluk daraldı) → tam fetch ham Afrika kadrolarını geri getiriyor.
Bu script kalite eşiğini (degerlendirildi) kullanarak onları eler.

Kullanım:
    python entegre_islenmis.py            # rapor + yaz
    python entegre_islenmis.py --kuru     # sadece rapor (dosyaya yazma)
"""
import json
import sys
from pathlib import Path

from fetch_scout_kadro import cek, parse, yas_backfill, CIKTI


def main():
    kuru = "--kuru" in sys.argv

    canli = parse(cek())
    comm = json.load(open(CIKTI, encoding="utf-8")) if Path(CIKTI).exists() else {}

    sonuc = dict(comm)
    eklenen, guncellenen, atlanan = [], 0, []
    for isim, rec in canli.items():
        if isim in comm:
            sonuc[isim] = rec            # mevcut → sheet'teki güncel haliyle yenile
            guncellenen += 1
        elif rec.get("degerlendirildi"):
            sonuc[isim] = rec            # yeni + işlenmiş → ekle
            eklenen.append(isim)
        else:
            atlanan.append(isim)         # yeni + ham → ATLA (Afrika bloğu)

    bf = yas_backfill(sonuc)

    print(f"Canlı sheet      : {len(canli)} oyuncu")
    print(f"Commit (önceki)  : {len(comm)} oyuncu")
    print(f"  ↻ güncellenen  : {guncellenen}")
    print(f"  + yeni eklenen : {len(eklenen)} (işlenmiş)")
    print(f"  ✗ atlanan (ham): {len(atlanan)} (ham Afrika bloğu — eklenmedi)")
    print(f"Yaş backfill     : {bf}")
    print(f"SONUÇ            : {len(sonuc)} oyuncu")
    if eklenen:
        print("\nYeni eklenen işlenmiş oyuncular:")
        for ad in eklenen:
            print("  +", ad)

    if kuru:
        print("\n[KURU MOD] Dosyaya yazılmadı.")
        return

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] {CIKTI.name} güncellendi.")


if __name__ == "__main__":
    main()
