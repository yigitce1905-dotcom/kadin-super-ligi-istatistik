# -*- coding: utf-8 -*-
"""Sco 26-27 🇹🇷'de olup Sco 🌐'da (Dünya) OLMAYAN oyuncuları Dünya'ya kopyalar.

Yiğit'in talebi (2026-08-18): "excelde sco tr 26-27 görmüşsündür orda olup
dünya kısmında olmayan oyuncular varsa onları da dünya copy paste et,
sitede scouting kısmında gözüksün."

NEDEN GEREKLİ
Sitenin Scouting/Dünya havuzu yalnızca Sco 🌐 sekmesini okur (scout_kadro_
raporlar.json → fetch_scout_kadro.py). Sco 26-27 🇹🇷'ye eklenmiş oyuncular
oraya hiç bağlı değil; kopyalanmadıkça sitede hiçbir yerde görünmezler.

SÜTUN UYUMU
İki sekme de 120 sütun ve BİREBİR AYNI başlık sırasına sahip — TEK istisna:
sütun 103 World'de "🇹🇷 Perspective" (tr_gorusu — TR kulüpleri bu YABANCI
oyuncuyu ister mi), TR26-27'de "🌐 Perspective" (yurtdisi_gorusu — bu YERLİ
oyuncunun yurtdışı ihtimali). Aynı pozisyon, TERS anlam, FARKLI değer
sözlüğü. Düz kopya bu sütunu yanlış etiketle sitede gösterirdi (fetch_
scout_kadro.py o pozisyonu her zaman "TR Görüşü" diye okur) — bu yüzden
BOŞ bırakılır, diğer 119 sütun aynen kopyalanır.

"Nu" sütunu (ilk sütun) da boş bırakılır — salt görsel sıra numarası,
kodun hiçbir yerinde okunmuyor (grep ile doğrulandı); World'ün kendi
numaralandırmasıyla çakışmasın diye taşınmaz.

Kullanım:
    python tr2627_dunyaya_kopyala.py --kuru     # önizleme
    python tr2627_dunyaya_kopyala.py --yaz
"""
import sys
import unicodedata

import gspread

sys.stdout.reconfigure(encoding="utf-8")

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_WORLD = 1707810792
GID_TR2627 = 2094311456


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())


def main():
    yaz_gercek = "--yaz" in sys.argv
    gc = gspread.service_account(filename=CREDS)
    sh = gc.open_by_key(GSHEET_ID)
    ws_world = sh.get_worksheet_by_id(GID_WORLD)
    ws_tr = sh.get_worksheet_by_id(GID_TR2627)

    wv = ws_world.get_all_values()
    tv = ws_tr.get_all_values()
    hdr_w, hdr_t = wv[1], tv[1]
    assert hdr_w[1] == hdr_t[1] == "Name & Surname", "kolon kayması — iptal"

    uyusmayan = [i for i, (a, b) in enumerate(zip(hdr_w, hdr_t)) if a != b]
    print(f"Başlık uyuşmazlığı ({len(uyusmayan)} sütun):")
    for i in uyusmayan:
        print(f"   sütun {i}: World={hdr_w[i]!r}  vs  TR26-27={hdr_t[i]!r}  → BOŞ bırakılacak")

    dolu_w = [(i, r) for i, r in enumerate(wv[2:], start=3) if len(r) > 1 and r[1].strip()]
    assert dolu_w and dolu_w[-1][0] - dolu_w[0][0] + 1 == len(dolu_w), \
        "World'de satır aralarında boşluk var — beklenmedik durum, iptal"
    ilk_bos_satir = dolu_w[-1][0] + 1

    w_isimler = {norm(r[1]) for _, r in dolu_w}
    kopyalanacak = []
    for r in tv[2:]:
        if len(r) <= 1 or not r[1].strip():
            continue
        if norm(r[1]) in w_isimler:
            continue
        satir = (list(r) + [""] * len(hdr_w))[:len(hdr_w)]
        satir[0] = ""                       # Nu — taşınmaz
        for i in uyusmayan:
            satir[i] = ""                   # anlam uyuşmayan sütun — taşınmaz
        kopyalanacak.append((r[1], satir))

    print(f"\nTR 26-27 dolu satır: {sum(1 for r in tv[2:] if len(r) > 1 and r[1].strip())}")
    print(f"World'de zaten var: "
          f"{sum(1 for r in tv[2:] if len(r) > 1 and r[1].strip() and norm(r[1]) in w_isimler)}")
    print(f"World'e kopyalanacak YENİ oyuncu: {len(kopyalanacak)}")
    print(f"Hedef başlangıç satırı: {ilk_bos_satir}\n")
    for isim, _ in kopyalanacak[:15]:
        print("  ", isim)
    if len(kopyalanacak) > 15:
        print(f"   … {len(kopyalanacak) - 15} tane daha")

    if not yaz_gercek:
        print("\n[KURU MOD] yazılmadı. Gerçek yazma: --yaz")
        return
    if not kopyalanacak:
        print("\nYazılacak bir şey yok.")
        return

    satirlar = [s for _, s in kopyalanacak]
    ws_world.update(
        f"A{ilk_bos_satir}",
        satirlar,
        value_input_option="USER_ENTERED",
    )
    print(f"\n✓ {len(satirlar)} satır World'e yazıldı "
          f"(satır {ilk_bos_satir}–{ilk_bos_satir + len(satirlar) - 1}).")


if __name__ == "__main__":
    main()
