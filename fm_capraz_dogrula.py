# -*- coding: utf-8 -*-
"""Boru hattı denetimi: script'in ürettiği harfler, sheet'te ZATEN DOLU olan
hücrelerle çelişiyor mu?

NEDEN
İlk 9 oyuncuyu elle işlemiştim. fm_toplu_cek.py aynı kaynaktan aynı sonucu
üretmeli. Tutmuyorsa ya elle girişimde ya eşik/eşleme tablosunda hata var —
93 oyuncuyu yazmadan önce bilmem gerek.

Hiçbir şey YAZMAZ.
"""
import json
import sys
import unicodedata
from pathlib import Path

import gspread

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())


def main():
    from fetch_scout_kadro import hdr_kanonlastir
    kayit = json.load(open(KOK / "_fm_ham_cache.json", encoding="utf-8"))

    ws = gspread.service_account(filename=CREDS).open_by_key(GSHEET_ID) \
        .get_worksheet_by_id(GID_DUNYA)
    vals = ws.get_all_values()
    hdr = hdr_kanonlastir(vals[1])
    kol = {}
    for i, h in enumerate(hdr):
        if h and h not in kol:
            kol[h] = i
    satirlar = {norm(r[1]): r for r in vals[2:] if len(r) > 1 and r[1].strip()}

    ayni = fark = bos = 0
    catisma = []
    for isim, k in kayit.items():
        r = satirlar.get(norm(isim))
        if not r:
            continue
        for nit, harf in (k.get("nitelikler") or {}).items():
            ci = kol.get(nit)
            if ci is None:
                continue
            mevcut = (r[ci].strip() if len(r) > ci else "")
            if not mevcut:
                bos += 1
            elif mevcut.upper() == harf.upper():
                ayni += 1
            else:
                fark += 1
                catisma.append((isim, nit, mevcut, harf))

    print(f"dolu ve AYNI   : {ayni}")
    print(f"dolu ama FARKLI: {fark}")
    print(f"boş (yazılacak): {bos}\n")
    for isim, nit, m, y in catisma[:40]:
        print(f"   {isim[:24]:24} {nit[:30]:30} sheet={m:3}  script={y}")
    if fark > 40:
        print(f"   … {fark - 40} tane daha")


if __name__ == "__main__":
    main()
