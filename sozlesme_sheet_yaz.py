# -*- coding: utf-8 -*-
"""SD güncel sözleşme bitişi ('Contract until') Sco 🌐 (Dünya) sheet'inde mevcut
'Sözleşme' sütununun ÜSTÜNE yazar (Yiğit'in talebiyle — eski manuel değer kaybolur,
sheet sürüm geçmişinden geri alınabilir).

Eşleşme: İsim - Soyisim (kol 2) → scouting_sd_profiller.json 'Contract until'.
Yalnız GEÇERLİ tarih yazılır (SD '?'/boş ise o satır atlanır, mevcut hücre korunur).

Kullanım:
    python sozlesme_sheet_yaz.py            # KURU (önizleme, yazmaz)
    python sozlesme_sheet_yaz.py --yaz      # gerçek yazma (mevcut Sözleşme kolonunu ezer)
"""
import sys, json, re, unicodedata
import gspread

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
BASLIK = "Sözleşme"
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
    # Baran 2026-08'de sheet başlıklarını İngilizceye çevirdi → iki ad da kabul
    assert hdr[1] in ("İsim - Soyisim", "Name & Surname"), \
        f"KOLON KAYMASI (kol2={hdr[1]!r}) — iptal"

    assert BASLIK in hdr, f"'{BASLIK}' sütunu sheet'te bulunamadı — iptal"
    hedef_kol = hdr.index(BASLIK) + 1
    print(f"'{BASLIK}' sütunu ÜZERİNE yazılacak (kol {hedef_kol}).")

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
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ {yazilan} hücre 'Sözleşme' kolonunun (kol {hedef_kol}) ÜSTÜNE yazıldı.")
    else:
        print(f"\n[KURU MOD] {len(hucreler)} hücre yazılacaktı (yazılmadı). "
              f"Gerçek yazma için: python sozlesme_sheet_yaz.py --yaz")

if __name__ == "__main__":
    main()
