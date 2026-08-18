# -*- coding: utf-8 -*-
"""Dünya (Sco 🌐) sekmesinde bulanık-eşleşme ile bulunan gerçek mükerrer
kayıtları temizler.

Yiğit'in sorusu (2026-08-18): "mükerrer oyuncu var mı emin misin?" —
birebir isim eşleşmesi kontrolü "hayır" demişti ama YETERSİZDİ; token
paylaşımı + difflib ile 70 şüpheli çift bulundu, 120 sütunun TAMAMI elle
karşılaştırılarak 5 gerçek mükerrer + 1 belirsiz (çözülmedi) tespit edildi.

SADECE bu script'te sabit kodlanmış 4 çift işlenir — genel bir "mükerrer
sil" aracı DEĞİLDİR; her çift insan gözüyle 120 sütun karşılaştırılarak
onaylandı:

  1136 "Mariem Houji"  -> SİL   (bos yer tutucu; Age=126, Ultimate Note=FF,
                                  tek gercek veri yok)
  1237 "Mariem Houij"  -> TUT   (dolu profil: dogum, boy, 34 nitelik, DE)

   795 "Rose Bella"     -> TUT   (FM-taslak nitelikleri dolu, gercek veri)
  1058 "Rosella Bella"  -> SİL   (Ultimate Note=FF, sadece bos ✘ etiketleri)

   654 "Hwa-yeon Son"       -> TUT (birlestirilir: bos hucreler B'den doldurulur)
   716 "Son Hwa-yeon"       -> SİL (ayni kisi, isim sirasi ters — CELISEN
                                    NITELIK YOK, sadece Yas/Boy 1 birim farkli)

   335 "Stine Ballisager"          -> TUT (birlestirilir)
   411 "Stine Ballisager Pedersen" -> SİL ([FM taslak] — CELISEN 2 alanda
                                            (Concentration, Cost) TUT'un
                                            DEGERI KORUNUR, taslak sessizce
                                            atilir — fm_sheete_yaz.py'nin
                                            ayni kuralı: taslak mevcut
                                            degeri asla ezmez)

ELENMEDİ — Baran'a bırakıldı:
  567 "Ngozi Okobi-Okeoghene" / 671 "Ngozi Okobi" — 42 hücrede GERÇEK
  (taslak olmayan) nitelik çakışması var, ayrıca lig/sözleşme de farklı.
  Ayni kişinin iki ayrı degerlendirmesi mi yoksa iki farklı Nijeryalı
  oyuncu mu belirsiz — kör birleştirme yanlış olabilir.

Kullanım:
    python mukerrer_temizle.py --kuru
    python mukerrer_temizle.py --yaz
"""
import sys

import gspread

sys.stdout.reconfigure(encoding="utf-8")

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_WORLD = 1707810792

# (tutulacak_satir, silinecek_satir, aciklama)
CIFTLER = [
    (1237, 1136, "Mariem Houji/Houij"),
    (795, 1058, "Rose Bella/Rosella Bella"),
    (654, 716, "Hwa-yeon Son / Son Hwa-yeon"),
    (335, 411, "Stine Ballisager / Pedersen"),
]


def main():
    yaz_gercek = "--yaz" in sys.argv
    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_WORLD)
    vals = ws.get_all_values()
    hdr = vals[1]

    hucreler = []
    for tut_sat, sil_sat, ad in CIFTLER:
        tut = vals[tut_sat - 1]
        sil = vals[sil_sat - 1]
        print(f"=== {ad} — TUT satır{tut_sat} ({tut[1]!r}), "
              f"SİL satır{sil_sat} ({sil[1]!r}) ===")
        doldurulan = 0
        for i, h in enumerate(hdr):
            if i in (0, 1):          # Nu ve isim — dokunulmaz
                continue
            tv = tut[i].strip() if i < len(tut) else ""
            sv = sil[i].strip() if i < len(sil) else ""
            if not tv and sv:
                print(f"   + col{i:3} {h[:26]:26} <- {sv[:40]!r}")
                hucreler.append(gspread.Cell(tut_sat, i + 1, sv))
                doldurulan += 1
        if doldurulan == 0:
            print("   (dolduracak boş hücre yok)")
        print()

    print(f"Toplam doldurulacak hücre: {len(hucreler)}")
    print(f"Silinecek satırlar (büyükten küçüğe): "
          f"{sorted((s for _, s, _ in CIFTLER), reverse=True)}")

    if not yaz_gercek:
        print("\n[KURU MOD] yazılmadı/silinmedi. Gerçek işlem: --yaz")
        return

    if hucreler:
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ {len(hucreler)} hücre dolduruldu.")

    # Büyükten küçüğe sil — erken silme sonraki satır numaralarını kaydırmasın
    for sil_sat in sorted((s for _, s, _ in CIFTLER), reverse=True):
        ws.delete_rows(sil_sat)
        print(f"✓ satır {sil_sat} silindi.")


if __name__ == "__main__":
    main()
