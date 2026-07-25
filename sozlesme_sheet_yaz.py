# -*- coding: utf-8 -*-
"""SD güncel sözleşme bitişi ('Contract until') Sco 🌐 (Dünya) sheet'ine YENİ
'Güncel Sözleşme (SD)' sütunu olarak yazar. Baran'ın 'Sözleşme' sütununa DOKUNMAZ.

İNDEKS GÜVENLİĞİ: yeni sütun SONA eklenir → fetch_scout_kadro index-parse'ı bozulmaz.
Eşleşme: İsim - Soyisim (kol 2) → scouting_sd_profiller.json 'Contract until'.
Yalnız GEÇERLİ tarih yazılır (SD '?'/boş atlanır — Baran'ın verisi korunur).

Kullanım:
    python sozlesme_sheet_yaz.py            # KURU (önizleme, yazmaz)
    python sozlesme_sheet_yaz.py --yaz      # gerçek yazma
"""
import sys, json, re, unicodedata
import gspread

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
BASLIK = "Güncel Sözleşme (SD)"
_GECERSIZ = {"", "?", "-", "—", "unbekannt", "unknown"}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

def main():
    yaz = "--yaz" in sys.argv
    sd = json.load(open("scouting_sd_profiller.json", encoding="utf-8"))
    sd_norm = {}
    for k, v in sd.items():
        if not isinstance(v, dict):
            continue
        c = (v.get("Contract until") or "").strip()
        if c and c.lower() not in _GECERSIZ:
            sd_norm[norm(k)] = c

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_DUNYA)
    hdr = ws.row_values(2)
    assert hdr[1] == "İsim - Soyisim", f"KOLON KAYMASI (kol2={hdr[1]!r}) — iptal"

    if BASLIK in hdr:
        hedef_kol = hdr.index(BASLIK) + 1
        print(f"'{BASLIK}' sütunu zaten var (kol {hedef_kol}) — güncellenecek.")
    else:
        hedef_kol = len(hdr) + 1
        print(f"'{BASLIK}' YENİ sütun olarak kol {hedef_kol}'e eklenecek.")

    isimler = ws.col_values(2)
    hucreler = [gspread.Cell(2, hedef_kol, BASLIK)]
    yazilan = 0
    ornek = []
    for i in range(2, len(isimler)):
        ad = isimler[i].strip()
        if not ad:
            continue
        c = sd_norm.get(norm(ad))
        if c:
            hucreler.append(gspread.Cell(i + 1, hedef_kol, c))
            yazilan += 1
            if len(ornek) < 12:
                ornek.append((ad[:26], c))

    print(f"\nSD'de geçerli sözleşme tarihi olan: {len(sd_norm)}")
    print(f"Sheet'te eşleşen (yazılacak): {yazilan}")
    print("Örnekler (isim → SD sözleşme):")
    for a, c in ornek:
        print(f"  {a:26} → {c}")

    if yaz:
        if hedef_kol > ws.col_count:
            ws.add_cols(hedef_kol - ws.col_count)
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ {yazilan} hücre + başlık YAZILDI (kol {hedef_kol}).")
        print("Not: Baran'ın 'Sözleşme' sütununa dokunulmadı.")
    else:
        print(f"\n[KURU MOD] {len(hucreler)} hücre yazılacaktı (yazılmadı). "
              f"Gerçek yazma için: python sozlesme_sheet_yaz.py --yaz")

if __name__ == "__main__":
    main()
