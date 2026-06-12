"""
'Scouting is life' Google Sheet --> 'Sco Tr' sekmesi (gid=864990475)
Tum lig scout raporu tablosunu ceker, temiz JSON'a donusturur:
scotr_raporlar.json

Parse INDEX BAZLIDIR: kolon adlari tekrarlansa bile kayma olmaz.
Grup sinirlari header satirindaki sabit kolonlardan dinamik bulunur.

Kullanim:  python fetch_scotr.py
"""
import csv
import io
import json
from pathlib import Path

import requests

GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID       = "864990475"
CIKTI     = Path(__file__).parent / "scotr_raporlar.json"

GECERLI_NOTLAR = {"AA", "AB", "BB", "BC", "CC", "CD", "DD", "DE", "EE", "FF", "A+"}


def cek() -> str:
    url = (f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
           f"/export?format=csv&gid={GID}")
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    return r.content.decode("utf-8")


def parse(metin: str) -> dict:
    rows = list(csv.reader(io.StringIO(metin)))
    hdr  = rows[1]  # 2. satir = kolon adlari

    def idx(ad: str) -> int:
        return hdr.index(ad)

    # Grup sinirlari (dinamik; kolon eklense de calisir)
    i_beceri0 = idx("Bitiricilik")
    i_beceri9 = idx("BECERİ NOT")
    i_beseri0 = i_beceri9 + 1
    i_beseri9 = idx("BEŞERİ NOT")
    i_fiziki0 = i_beseri9 + 1
    i_fiziki9 = idx("FİZİKİ NOT")
    i_sahsi0  = i_fiziki9 + 1
    i_sahsi9  = idx("ŞAHSİ NOT")
    i_tarz0   = i_sahsi9 + 1
    i_nihai   = idx("NİHAİ")
    i_ivme    = idx("İVME")
    i_not     = idx("Scout Notları")

    def hucre(r, i):
        return r[i].strip() if i < len(r) else ""

    def nitelikler(r, i0, i9):
        out = {}
        for i in range(i0, i9):
            v = hucre(r, i)
            if v in GECERLI_NOTLAR:
                out[hdr[i]] = v
        return out

    veriler = {}
    for r in rows[2:]:
        if not r or not hucre(r, 0):
            continue
        isim = hucre(r, 0)

        beceri = nitelikler(r, i_beceri0, i_beceri9)
        beseri = nitelikler(r, i_beseri0, i_beseri9)
        fiziki = nitelikler(r, i_fiziki0, i_fiziki9)
        sahsi  = nitelikler(r, i_sahsi0,  i_sahsi9)

        # Degerlendirilmis = FF disinda en az bir nitelik notu var
        tum = (list(beceri.values()) + list(beseri.values())
               + list(fiziki.values()) + list(sahsi.values()))
        degerlendirildi = any(n != "FF" for n in tum)

        # Tarz: '✘' = ozellik yok; isaretli (✘ disi dolu) olanlar listelenir
        tarz = []
        for i in range(i_tarz0, i_nihai):
            v = hucre(r, i)
            if v and v != "✘":
                tarz.append(hdr[i])

        nihai = hucre(r, i_nihai)
        ivme  = hucre(r, i_ivme)
        kayit = {
            "takim":      hucre(r, 1),
            "dogum":      hucre(r, 2),
            "bolge":      hucre(r, 3),
            "mevki1":     hucre(r, 4).replace("-", ""),
            "mevki2":     hucre(r, 5).replace("-", ""),
            "rol":        hucre(r, 6).replace("-", ""),
            "yas":        hucre(r, 7),
            "uyruk":      hucre(r, 8),
            "beceri":     beceri,
            "beseri":     beseri,
            "fiziki":     fiziki,
            "sahsi":      sahsi,
            "makro": {
                "beceri": hucre(r, i_beceri9) if hucre(r, i_beceri9) in GECERLI_NOTLAR else "",
                "beseri": hucre(r, i_beseri9) if hucre(r, i_beseri9) in GECERLI_NOTLAR else "",
                "fiziki": hucre(r, i_fiziki9) if hucre(r, i_fiziki9) in GECERLI_NOTLAR else "",
                "sahsi":  hucre(r, i_sahsi9)  if hucre(r, i_sahsi9)  in GECERLI_NOTLAR else "",
            },
            "tarz":       tarz,
            "nihai":      nihai if nihai in GECERLI_NOTLAR else "",
            "ivme":       ivme if ivme not in ("", "-") else "",
            "scout_notu": hucre(r, i_not),
            "degerlendirildi": degerlendirildi,
        }

        # Cift kayit (transfer): degerlendirilmis olan kazanir
        if isim in veriler:
            eski = veriler[isim]
            if eski["degerlendirildi"] and not degerlendirildi:
                continue
        veriler[isim] = kayit

    return veriler


def main():
    metin = cek()
    veriler = parse(metin)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)
    n_ok = sum(1 for v in veriler.values() if v["degerlendirildi"])
    print(f"Toplam {len(veriler)} oyuncu ({n_ok} degerlendirilmis) -> {CIKTI.name}")


if __name__ == "__main__":
    main()
