# -*- coding: utf-8 -*-
"""SD'ye göre GERÇEKTEN kulüp değiştirmiş oyuncuları Sco 🌐 sheet'ine yazar.

NEDEN AYRI BİR SCRIPT (2026-08-13):
`guncel_kulup_sheet_yaz.py` tüm Kulüp sütununu SD ile eziyordu. Ölçüldü:
588 hücre değişiyordu ama 354'ü SADECE yazım farkıydı (Arsenal FC → Arsenal
LFC), kalanların da çoğu SoccerDonna'nın Almanca/eski adlandırmasıydı
(Gotham FC → Sky Blue FC [eski ad], AS Roma → AS Rom, Inter → Inter Mailand,
Rayadas → Rayados). Yani toplu ezme Baran'ın DAHA DOĞRU adlarını bozuyordu.

Bu script yalnızca TARTIŞMASIZ durumları yazar:
  A) Sheet boş/Serbest  →  SD'de kulüp var   (oyuncu imzalamış)
  B) Sheet'te kulüp var →  SD'de serbest     (oyuncu ayrılmış)
Kulüpten kulübe geçişlere DOKUNMAZ — orada SD'nin adlandırması güvenilmez.

Kullanım:
    python kulup_gercek_degisim_yaz.py         # KURU (önizleme)
    python kulup_gercek_degisim_yaz.py --yaz   # gerçek yazma
"""
import sys, json, re, unicodedata
import gspread

sys.stdout.reconfigure(encoding="utf-8")

CREDS     = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
# Baran başlığı zaman zaman yeniden adlandırıyor: Kulüp → Club → Club Name
BASLIK_ADAYLARI = ("Kulüp", "Club Name", "Club")

# "Kulüpsüz" sayılan değerler (iki dil + SD'nin kendi terimleri)
SERBEST = {"", "serbest", "free", "free agent", "vereinslos", "without club"}
# SD'de kulüp yerine geçen ama kulüp OLMAYAN durumlar — yazılmaz
GECERSIZ = {"pausiert", "karriereende", "unbekannt", "unknown", "-", "?"}

SERBEST_YAZ = "Serbest"     # sheet'e yazılacak kanonik "kulüpsüz" ifadesi


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def main():
    yaz = "--yaz" in sys.argv
    sd = json.load(open("scouting_sd_profiller.json", encoding="utf-8"))
    sdn = {norm(k): (v.get("guncel_kulup") or "").strip()
           for k, v in sd.items()
           if isinstance(v, dict) and (v.get("guncel_kulup") or "").strip()}

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_DUNYA)
    vals = ws.get_all_values()
    hdr = vals[1]

    assert hdr[1] in ("İsim - Soyisim", "Name & Surname"), \
        f"KOLON KAYMASI (kol2={hdr[1]!r}) — iptal"
    _baslik = next((b for b in BASLIK_ADAYLARI if b in hdr), None)
    assert _baslik, f"Kulüp sütunu bulunamadı (aranan: {BASLIK_ADAYLARI}) — iptal"
    kol = hdr.index(_baslik)
    print(f"'{_baslik}' sütunu (kol {kol + 1}) — yalnız gerçek değişimler yazılacak.\n")

    hucreler, imzaladi, ayrildi, atlanan = [], [], [], []
    for i, r in enumerate(vals[2:], start=3):          # sheet satır no
        ad = r[1].strip() if len(r) > 1 else ""
        if not ad:
            continue
        yeni = sdn.get(norm(ad))
        if not yeni:
            continue
        eski = r[kol].strip() if len(r) > kol else ""
        if eski == yeni:
            continue

        e_bos = eski.lower() in SERBEST
        y_bos = yeni.lower() in SERBEST
        y_gecersiz = yeni.lower() in GECERSIZ

        if e_bos and not y_bos:
            if y_gecersiz:                             # 'pausiert' vb. kulüp değil
                atlanan.append((ad, eski or "(boş)", yeni)); continue
            hucreler.append(gspread.Cell(i, kol + 1, yeni))
            imzaladi.append((ad, eski or "(boş)", yeni))
        elif y_bos and not e_bos:
            hucreler.append(gspread.Cell(i, kol + 1, SERBEST_YAZ))
            ayrildi.append((ad, eski, SERBEST_YAZ))
        # kulüpten kulübe geçiş → DOKUNULMAZ (SD adlandırması güvenilmez)

    print(f"A) İMZALAMIŞ (boş/serbest → kulüp) : {len(imzaladi)}")
    for a, e, y in imzaladi:
        print(f"     {a[:28]:28} {e[:12]:12} → {y}")
    print(f"\nB) AYRILMIŞ (kulüp → serbest)      : {len(ayrildi)}")
    for a, e, y in ayrildi:
        print(f"     {a[:28]:28} {e[:26]:26} → {y}")
    if atlanan:
        print(f"\nATLANAN (SD'de kulüp değil)        : {len(atlanan)}")
        for a, e, y in atlanan:
            print(f"     {a[:28]:28} {e[:12]:12} → {y}  (yazılmadı)")

    print(f"\nTOPLAM yazılacak hücre: {len(hucreler)}")
    if yaz and hucreler:
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"✓ {len(hucreler)} hücre yazıldı. Diğer kulüp adlarına DOKUNULMADI.")
    elif not yaz:
        print("[KURU MOD] yazılmadı. Gerçek yazma: python kulup_gercek_degisim_yaz.py --yaz")


if __name__ == "__main__":
    main()
