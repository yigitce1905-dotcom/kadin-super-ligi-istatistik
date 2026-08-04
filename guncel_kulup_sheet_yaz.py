# -*- coding: utf-8 -*-
"""SD güncel kulübü ('guncel_kulup') Sco 🌐 (Dünya) sheet'ine mevcut 'Kulüp'
sütununun ÜSTÜNE yazar (Yiğit'in talebiyle — eski manuel değer kaybolur,
sheet sürüm geçmişinden geri alınabilir).

Eşleşme: İsim - Soyisim (kol 2) → scouting_sd_profiller.json guncel_kulup.

Kullanım:
    python guncel_kulup_sheet_yaz.py            # KURU (önizleme, yazmaz)
    python guncel_kulup_sheet_yaz.py --yaz      # gerçek yazma (mevcut Kulüp kolonunu ezer)
"""
import sys, json, re, unicodedata
import gspread

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
BASLIK = "Kulüp"

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

    assert BASLIK in hdr, f"'{BASLIK}' sütunu sheet'te bulunamadı — iptal"
    hedef_kol = hdr.index(BASLIK) + 1
    print(f"'{BASLIK}' sütunu ÜZERİNE yazılacak (kol {hedef_kol}).")

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
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ {yazilan} hücre 'Kulüp' kolonunun (kol {hedef_kol}) ÜSTÜNE yazıldı.")
    else:
        print(f"\n[KURU MOD] {len(hucreler)} hücre yazılacaktı (yazılmadı). "
              f"Gerçek yazma için: python guncel_kulup_sheet_yaz.py --yaz")

if __name__ == "__main__":
    main()
