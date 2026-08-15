# -*- coding: utf-8 -*-
"""Gerçek kulüp değişimlerini Sco 🌐 sheet'ine yazar — Baran'ın kuralıyla.

BARAN'IN KURALI (Yiğit üzerinden, 2026-08-15):
  · HANGİ kulüp  → SoccerDonna karar verir. Transferleri bizden iyi takip
    ediyorlar (Baran SD çalışanı).
  · NASIL yazılır → Excel karar verir. SD'de eski sürüm/Almanca adlar var
    (AS Rom, Sky Blue FC, WFC LA); ad neredeyse aynıysa Excel'deki kalır.

Bu ikisi çelişmez: `kulup_denetim.ayni_mi` "aynı kulüp mü" sorusunu ayırır.
Aynıysa hiç dokunulmaz (Excel'in yazımı korunur). Farklıysa transfer kabul
edilir ve SD'nin kulübü yazılır — ama SD'nin ham adıyla değil, o kulüp Excel'de
başka bir satırda nasıl yazılıyorsa o biçimde (`excel_yazimi`). Böylece hem
güncel kulüp hem bizim ad formatımız korunur.

TEK İSTİSNA — kulüp → Serbest yazılmaz:
  Klil Keshwar SD'de 'Serbest' görünüyor ama Ünye ile idmana çıkıyor; kulüp
  resmî açıklama yapmadığı için SD henüz işlememiş. Bu yönde Excel her zaman
  SD'den ileride olabilir, o yüzden boşaltma yapılmaz.

Kullanım:
    python kulup_transfer_yaz.py          # KURU (önizleme)
    python kulup_transfer_yaz.py --yaz    # gerçek yazma
"""
import json
import sys
from collections import Counter
from pathlib import Path

import gspread

from kulup_denetim import ayni_mi, kanonik_ad, norm

sys.stdout.reconfigure(encoding="utf-8")

KOK       = Path(__file__).parent
CREDS     = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
BASLIKLAR = ("Kulüp", "Club Name", "Club")

SERBEST = {"", "serbest", "free", "free agent", "vereinslos", "without club"}
GECERSIZ = {"pausiert", "karriereende", "unbekannt", "unknown", "-", "?"}


def excel_yazim_sozlugu(kadro: dict) -> dict:
    """Excel'de geçen kulüp adlarından {normalize: en sık kullanılan yazım}.
    SD 'Sky Blue FC' dediğinde Excel'de 'Gotham FC' varsa onu yazabilelim diye."""
    sayac = {}
    for v in kadro.values():
        ad = (v.get("kulup") or "").strip()
        if not ad or ad.lower() in SERBEST | GECERSIZ:
            continue
        sayac.setdefault(norm(ad), Counter())[ad] += 1
    return {k: c.most_common(1)[0][0] for k, c in sayac.items()}


def main():
    yaz = "--yaz" in sys.argv
    kadro = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
    kar = json.load(open(KOK / "scouting_leistungsdaten.json", encoding="utf-8"))
    sozluk = excel_yazim_sozlugu(kadro)

    # oyuncu -> SD'nin GÜNCEL kulübü.
    #
    # Kaynak neden `guncel_kulup`, "26/27'de en çok maç oynadığı kulüp" değil:
    # sezon ortası transferlerde maç sayısı ESKİ kulübü gösteriyor. Lilly Reale
    # 17 Haziran 2026'da Gotham'dan Boston Legacy'ye takas edildi; SD'nin 26/27
    # satırlarında hâlâ 14 Gotham maçı var, yani maç sinyali onu geri
    # götürecekti. `guncel_kulup` ise doğru ('NWSL Boston') — kontrol edilen 8
    # çelişkili vakanın 8'inde de Excel'i doğruladı.
    sd_prof = json.load(open(KOK / "scouting_sd_profiller.json", encoding="utf-8"))
    hedef = {isim: (v.get("guncel_kulup") or "").strip()
             for isim, v in sd_prof.items()
             if isinstance(v, dict) and (v.get("guncel_kulup") or "").strip()}

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_DUNYA)
    vals = ws.get_all_values()
    hdr = vals[1]
    assert hdr[1] in ("İsim - Soyisim", "Name & Surname"), \
        f"KOLON KAYMASI (kol2={hdr[1]!r}) — iptal"
    baslik = next((b for b in BASLIKLAR if b in hdr), None)
    assert baslik, f"Kulüp sütunu bulunamadı (aranan: {BASLIKLAR}) — iptal"
    kol = hdr.index(baslik)

    hucreler, yazilacak, atlanan = [], [], []
    for i, r in enumerate(vals[2:], start=3):
        ad = r[1].strip() if len(r) > 1 else ""
        eski = r[kol].strip() if len(r) > kol else ""
        yeni_sd = hedef.get(ad)
        if not ad or not yeni_sd or not eski:
            continue
        if ayni_mi(eski, yeni_sd):
            continue                                   # aynı kulüp → Excel yazımı kalır
        if yeni_sd.lower() in SERBEST | GECERSIZ:
            atlanan.append((ad, eski, yeni_sd, "SD serbest/geçersiz — boşaltılmaz"))
            continue
        # Önce SD'nin eski/birleşik adını bizim ada çevir (LdB FC Malmö →
        # rosengard), sonra Excel'de o kulüp nasıl yazılıyorsa o biçimi al.
        kanon = kanonik_ad(yeni_sd)
        yazim = sozluk.get(norm(kanon), kanon if kanon != yeni_sd else yeni_sd)
        hucreler.append(gspread.Cell(i, kol + 1, yazim))
        yazilacak.append((ad, eski, yazim, yeni_sd))

    print(f"'{baslik}' sütunu (kol {kol + 1})\n")
    print(f"YAZILACAK — gerçek kulüp değişimi: {len(yazilacak)}")
    for a, e, y, ham in yazilacak:
        nt = "" if y == ham else f"   (SD: {ham} → Excel yazımı)"
        print(f"   {a[:24]:24} {e[:24]:24} → {y}{nt}")
    if atlanan:
        print(f"\nATLANDI: {len(atlanan)}")
        for a, e, y, sebep in atlanan:
            print(f"   {a[:24]:24} {e[:24]:24} → {y}  ({sebep})")

    print(f"\nTOPLAM {len(hucreler)} hücre")
    if yaz and hucreler:
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print("✓ yazıldı — diğer kulüp adlarına DOKUNULMADI.")
    elif not yaz:
        print("[KURU MOD] yazılmadı. Gerçek yazma: python kulup_transfer_yaz.py --yaz")


if __name__ == "__main__":
    main()
