# -*- coding: utf-8 -*-
"""'ÜNYE GÜCÜ' → kulübün güncel adı. (Yiğit, 2026-08-15: "eski ismi Gücü olan")

Ad seçimi: TFF kaydı 'ÜNYE KADIN SPOR KULÜBÜ' (kulupID=9649). Bizim TFF kaynaklı
dosyalarımız (puan_durumu, mac_sonuclari, oyuncular, coaches, arsiv_2024_25)
hepsi bu yazımı kullanıyor — site takım adıyla birleştirme yaptığı için sheet'in
de aynı yazımı taşıması gerekir, yoksa Ünye satırları eşleşmez.

Her sekme kendi yazım geleneğini korur (Baran'ın formatı bozulmasın):
  Sco Tr   : TAM AD, BÜYÜK HARF  ('ANKARA BÜYÜKŞEHİR BELEDİYESİ FOMGET SPOR
             KULÜBÜ' gibi)                        → ÜNYE KADIN SPOR KULÜBÜ
  Sco 🌐   : kısa ad, karışık harf ('Galatasaray SK', 'Trabzonspor AŞ',
             'Hakkarigücü' gibi)                   → Ünye Kadın SK

Kullanım:
    python unye_ad_duzelt.py          # KURU (önizleme)
    python unye_ad_duzelt.py --yaz    # gerçek yazma
"""
import sys
import gspread

sys.stdout.reconfigure(encoding="utf-8")

CREDS     = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
BASLIKLAR = ("Kulüp", "Club Name", "Club")

ESKI = "ÜNYE GÜCÜ"
SEKMELER = [
    ("Sco Tr",  864990475,  "ÜNYE KADIN SPOR KULÜBÜ"),
    ("Sco 🌐", 1707810792, "Ünye Kadın SK"),
]


def main():
    yaz = "--yaz" in sys.argv
    gc = gspread.service_account(filename=CREDS)
    sh = gc.open_by_key(GSHEET_ID)
    toplam = 0

    for ad, gid, yeni in SEKMELER:
        ws = sh.get_worksheet_by_id(gid)
        vals = ws.get_all_values()
        hdr = vals[1]
        baslik = next((b for b in BASLIKLAR if b in hdr), None)
        assert baslik, f"[{ad}] Kulüp sütunu bulunamadı — iptal"
        kol = hdr.index(baslik)

        hucreler = []
        for i, r in enumerate(vals[2:], start=3):
            if len(r) > kol and r[kol].strip().upper() == ESKI:
                hucreler.append(gspread.Cell(i, kol + 1, yeni))

        print(f"[{ad}] '{baslik}' kol {kol + 1} — {len(hucreler)} satır: "
              f"{ESKI!r} → {yeni!r}")
        toplam += len(hucreler)
        if yaz and hucreler:
            ws.update_cells(hucreler, value_input_option="USER_ENTERED")
            print(f"   ✓ yazıldı")

    print(f"\nTOPLAM {toplam} hücre"
          + ("" if yaz else "  [KURU MOD — yazılmadı, --yaz ile çalıştır]"))


if __name__ == "__main__":
    main()
