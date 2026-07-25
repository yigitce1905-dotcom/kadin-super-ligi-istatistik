# -*- coding: utf-8 -*-
"""SD 'guncel_kulup' + 'Contract until' değerlerini Dünya sheet'inde Baran'ın
'Kulüp' (kol 16) ve 'Sözleşme' (kol 19) sütunlarına DOĞRUDAN yazar (EZER).

Yalnız SD'de GEÇERLİ değer olan hücreler ezilir → SD '?'/boş/unbekannt ise Baran'ın
değeri KORUNUR (veri kaybı olmaz). Header'lara/kolon sırasına dokunulmaz (in-place),
fetch_scout_kadro index-parse'ı bozulmaz.

Kullanım:  python sd_sheet_ez.py            # KURU önizleme
           python sd_sheet_ez.py --yaz      # gerçek yazma (EZME)
"""
import sys, json, re, unicodedata
import gspread

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
KOL_KULUP, KOL_SOZ = 16, 19
_GECERSIZ = {"", "?", "-", "—", "unbekannt", "unknown", "vereinslos"}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()

def gecerli(x):
    return bool(x) and str(x).strip().lower() not in _GECERSIZ

def main():
    yaz = "--yaz" in sys.argv
    sd = json.load(open("scouting_sd_profiller.json", encoding="utf-8"))
    kulup_map = {norm(k): (v.get("guncel_kulup") or "").strip()
                 for k, v in sd.items() if isinstance(v, dict) and gecerli(v.get("guncel_kulup"))}
    soz_map = {norm(k): (v.get("Contract until") or "").strip()
               for k, v in sd.items() if isinstance(v, dict) and gecerli(v.get("Contract until"))}

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_DUNYA)
    hdr = ws.row_values(2)
    assert hdr[1] == "İsim - Soyisim", f"KOLON KAYMASI (kol2={hdr[1]!r}) — iptal"
    assert hdr[KOL_KULUP-1] == "Kulüp", f"kol{KOL_KULUP}={hdr[KOL_KULUP-1]!r} != Kulüp — iptal"
    assert hdr[KOL_SOZ-1] == "Sözleşme", f"kol{KOL_SOZ}={hdr[KOL_SOZ-1]!r} != Sözleşme — iptal"

    isimler = ws.col_values(2)
    eski_k = ws.col_values(KOL_KULUP)
    eski_s = ws.col_values(KOL_SOZ)
    def _es(col, i): return col[i].strip() if i < len(col) else ""

    hucreler, k_yaz, s_yaz, ornek = [], 0, 0, []
    for i in range(2, len(isimler)):      # row 3+
        ad = isimler[i].strip()
        if not ad:
            continue
        n = norm(ad); r = i + 1
        yk, ys = kulup_map.get(n), soz_map.get(n)
        deg = []
        if yk and yk != _es(eski_k, i):
            hucreler.append(gspread.Cell(r, KOL_KULUP, yk)); k_yaz += 1
            deg.append(f"Kulüp: {_es(eski_k,i) or '—'} → {yk}")
        if ys and ys != _es(eski_s, i):
            hucreler.append(gspread.Cell(r, KOL_SOZ, ys)); s_yaz += 1
            deg.append(f"Söz: {_es(eski_s,i) or '—'} → {ys}")
        if deg and len(ornek) < 14:
            ornek.append(f"  {ad[:24]:24} | " + "  ·  ".join(deg))

    print(f"Değişecek Kulüp hücresi: {k_yaz} | Sözleşme hücresi: {s_yaz} | toplam {len(hucreler)}")
    print("Örnekler (eski → yeni):")
    print("\n".join(ornek))

    if yaz:
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ EZİLDİ: {k_yaz} Kulüp + {s_yaz} Sözleşme hücresi (kol {KOL_KULUP}/{KOL_SOZ}).")
    else:
        print(f"\n[KURU MOD] {len(hucreler)} hücre ezilecekti. Yazmak için: python sd_sheet_ez.py --yaz")

if __name__ == "__main__":
    main()
