# -*- coding: utf-8 -*-
"""Sco 🌐 (Dünya) sekmesine bugün Sco 26-27 🇹🇷'den kopyalanan satırlardan,
ESKİ Sco 🇹🇷 sekmesiyle (zaten sitenin scouting havuzuna bağlı) çarpışanları
siler.

Yiğit'in sorusu (2026-08-18): "Sco Tr'de olanlar zaten scouting kısmında
vardı sitede, onları da sil dünya kısmından. mükerrer oldu şuan? iren eren,
donjeta halilaj vesaire?"

NEDEN GEREKLİ
birlesik_scout_yukle() (app.py) ÇALIŞMA ANINDA World + eski Sco 🇹🇷'yi isme
göre birleştirir; normalize-isim çakışırsa eski-TR kaydı KAZANIR (World
kaydı sessizce silinir). Yani bu 80 satır sitede GÖRÜNÜR mükerrer
YARATMIYOR — ama tamamen ÖLÜ VERİ: bugün bu isimler için çektiğim SD
profili + kariyer verisi hiçbir zaman gösterilmeyecek, her zaman eski-TR
kaydı kazanacak. Kullanıcının sorusu doğruydu, sadece görünmez bir israf.

KAPSAM
Yalnızca "Nu" sütunu BOŞ olan satırlar (= bugün tr2627_dunyaya_kopyala.py
ile eklenenler) silinir. 5 isim (Juliette Nana, Rasmata Sawadogo, Lushomo
Mweemba, Kevine Ossol, Soulaima Jabrani) da eski-TR ile çakışıyor ama
Nu'ları DOLU — bunlar bugünden ÖNCE World'de vardı (kod yorumunda
2026-08-02 tarihli, zaten bilinen bir durum: "Türkiye'ye transfer olup
Dünya sheet'inden silinmemiş"). Onlara dokunulmaz — kapsam dışı.

Kullanım:
    python dunya_carpisanlari_sil.py --kuru
    python dunya_carpisanlari_sil.py --yaz
"""
import json
import sys
import unicodedata

import gspread

sys.stdout.reconfigure(encoding="utf-8")

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_WORLD = 1707810792


def n3(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())


def main():
    yaz_gercek = "--yaz" in sys.argv

    kadro = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
    scotr_ham = json.load(open("scotr_raporlar.json", encoding="utf-8"))
    scotr = {k: v for k, v in scotr_ham.items() if v.get("degerlendirildi")}

    norm_harita = {n3(k): k for k in kadro}
    carpisan_isim = {norm_harita[n3(k)] for k in scotr
                      if n3(k) in norm_harita and norm_harita[n3(k)] != k}

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_WORLD)
    wv = ws.get_all_values()

    silinecek, atlanan_dolu_nu = [], []
    for i, r in enumerate(wv[2:], start=3):
        if len(r) <= 1 or r[1].strip() not in carpisan_isim:
            continue
        if r[0].strip():
            atlanan_dolu_nu.append((i, r[1]))
            continue
        silinecek.append((i, r[1]))

    print(f"Eski Sco TR ile çarpışan toplam isim: {len(carpisan_isim)}")
    print(f"Nu DOLU (kapsam dışı, dokunulmuyor): {len(atlanan_dolu_nu)}")
    for sat, isim in atlanan_dolu_nu:
        print(f"   - satır{sat:5} {isim}")
    print(f"\nSİLİNECEK (Nu boş, bugün kopyalanan): {len(silinecek)}")
    for sat, isim in silinecek:
        print(f"   satır{sat:5} {isim}")

    if not yaz_gercek:
        print("\n[KURU MOD] silinmedi. Gerçek işlem: --yaz")
        return

    for sat, _ in sorted(silinecek, reverse=True):
        ws.delete_rows(sat)
    print(f"\n✓ {len(silinecek)} satır silindi.")


if __name__ == "__main__":
    main()
