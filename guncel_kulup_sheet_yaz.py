# -*- coding: utf-8 -*-
"""SD güncel kulübü ('guncel_kulup') Sco 🌐 (Dünya) sheet'ine YENİ 'Güncel Kulüp'
sütunu olarak yazar. Mevcut 'Kulüp' sütununa DOKUNMAZ (geri alınabilir).

İNDEKS GÜVENLİĞİ: yeni sütun SONA eklenir → fetch_scout_kadro index-parse'ı bozulmaz.
Eşleşme: İsim - Soyisim (kol 2) → scouting_sd_profiller.json guncel_kulup.

Kullanım:
    python guncel_kulup_sheet_yaz.py            # KURU (önizleme, yazmaz)
    python guncel_kulup_sheet_yaz.py --yaz      # gerçek yazma
"""
import sys, json, re, unicodedata
import gspread

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
BASLIK = "Güncel Kulüp"

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

def main():
    yaz = "--yaz" in sys.argv
    sd = json.load(open("scouting_sd_profiller.json", encoding="utf-8"))
    sd_norm = {norm(k): (v.get("guncel_kulup") or "").strip()
               for k, v in sd.items() if isinstance(v, dict) and (v.get("guncel_kulup") or "").strip()}

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_DUNYA)
    hdr = ws.row_values(2)
    assert hdr[1] == "İsim - Soyisim", f"KOLON KAYMASI (kol2={hdr[1]!r}) — iptal"

    # Zaten 'Güncel Kulüp' sütunu var mı? Varsa onu kullan; yoksa SONA ekle
    if BASLIK in hdr:
        hedef_kol = hdr.index(BASLIK) + 1
        print(f"'{BASLIK}' sütunu zaten var (kol {hedef_kol}) — güncellenecek.")
    else:
        hedef_kol = len(hdr) + 1     # header'ın son dolu sütunundan sonra
        print(f"'{BASLIK}' YENİ sütun olarak kol {hedef_kol}'e eklenecek.")

    isimler = ws.col_values(2)       # İsim - Soyisim
    hucreler = [gspread.Cell(2, hedef_kol, BASLIK)]   # başlık row 2'de
    yazilan = 0
    ornek = []
    for i in range(2, len(isimler)):   # row 3+
        ad = isimler[i].strip()
        if not ad:
            continue
        gk = sd_norm.get(norm(ad))
        if gk:
            hucreler.append(gspread.Cell(i + 1, hedef_kol, gk))
            yazilan += 1
            if len(ornek) < 10:
                ornek.append((ad[:26], gk[:26]))

    print(f"\nEşleşen (yazılacak) oyuncu: {yazilan}")
    print("Örnekler (isim → güncel kulüp):")
    for a, g in ornek:
        print(f"  {a:26} → {g}")

    if yaz:
        if hedef_kol > ws.col_count:      # grid'i genişlet (yeni sütun için)
            ws.add_cols(hedef_kol - ws.col_count)
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ {yazilan} hücre + başlık YAZILDI (kol {hedef_kol}).")
        print("Not: Baran'ın 'Kulüp' sütununa dokunulmadı.")
    else:
        print(f"\n[KURU MOD] {len(hucreler)} hücre yazılacaktı (yazılmadı). "
              f"Gerçek yazma için: python guncel_kulup_sheet_yaz.py --yaz")

if __name__ == "__main__":
    main()
