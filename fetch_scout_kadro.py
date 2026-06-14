"""
'Scouting is life' Google Sheet --> zengin scout kadro sekmesi (gid=1707810792)
Tüm scout raporu tablosunu çeker -> scout_kadro_raporlar.json

Bu sekme Sco Tr'den daha zengin: Kulüp/Lig/Sözleşme, Boy/Ayak/Vücut Tipi,
Yetenek Kümesi/İktisadi Durum/TR Görüşü ve TARZ'da gerçek ✔︎ işaretleri.

Parse INDEX BAZLIDIR. Kullanım:  python fetch_scout_kadro.py
"""
import csv, io, json
from pathlib import Path
import requests

GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID       = "1707810792"
CIKTI     = Path(__file__).parent / "scout_kadro_raporlar.json"
GECERLI_NOTLAR = {"AA","AB","BB","BC","CC","CD","DD","DE","EE","FF","A+"}
ISARETLI = {"✔", "✔︎", "✓", "x", "X", "✗"}  # ✘ = yok; geri kalan dolu = var


def cek() -> str:
    url = (f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
           f"/export?format=csv&gid={GID}")
    r = requests.get(url, timeout=25); r.raise_for_status()
    return r.content.decode("utf-8")


def parse(metin: str) -> dict:
    rows = list(csv.reader(io.StringIO(metin)))
    hdr  = rows[1]

    def idx(ad): return hdr.index(ad)
    i_beceri0, i_beceri9 = idx("Bitiricilik"), idx("BECERİ NOT")
    i_beseri0, i_beseri9 = i_beceri9 + 1, idx("BEŞERİ NOT")
    i_fiziki0, i_fiziki9 = i_beseri9 + 1, idx("FİZİKİ NOT")
    i_sahsi0,  i_sahsi9  = i_fiziki9 + 1, idx("ŞAHSİ NOT")
    i_tarz0  = i_sahsi9 + 1
    i_nihai  = idx("NİHAİ")

    def h(r, i): return r[i].strip() if i < len(r) else ""

    def nitelik(r, i0, i9):
        return {hdr[i]: h(r, i) for i in range(i0, i9) if h(r, i) in GECERLI_NOTLAR}

    veriler = {}
    for r in rows[2:]:
        if not r or not h(r, 3):
            continue
        isim = h(r, 3)

        beceri = nitelik(r, i_beceri0, i_beceri9)
        beseri = nitelik(r, i_beseri0, i_beseri9)
        fiziki = nitelik(r, i_fiziki0, i_fiziki9)
        sahsi  = nitelik(r, i_sahsi0,  i_sahsi9)
        tum = list(beceri.values()) + list(beseri.values()) + list(fiziki.values()) + list(sahsi.values())
        degerlendirildi = any(n != "FF" for n in tum) and bool(tum)

        # Sadece tam veri girilmiş oyuncuları al
        if not degerlendirildi:
            continue

        tarz = []
        for i in range(i_tarz0, i_nihai):
            v = h(r, i)
            if v and v != "✘":          # ✘ = özellik yok
                tarz.append(hdr[i])

        mevki = [h(r, j).replace("-", "") for j in (13, 14, 15) if h(r, j) and h(r, j) != "-"]

        veriler[isim] = {
            "tam_isim":   h(r, 4),
            "vatandaslik": h(r, 5),
            "milli_takim": h(r, 6),
            "dogum":      h(r, 7),
            "yas":        h(r, 8),
            "boy":        h(r, 9),
            "ayak":       h(r, 10),
            "vucut_tipi": h(r, 11),
            "bolge":      h(r, 12),
            "mevki":      mevki,
            "rol":        h(r, 16),
            "kulup":      h(r, 17),
            "lig":        h(r, 18),
            "sozlesme":   h(r, 19),
            "beceri": beceri, "beseri": beseri, "fiziki": fiziki, "sahsi": sahsi,
            "makro": {
                "beceri": h(r, i_beceri9) if h(r, i_beceri9) in GECERLI_NOTLAR else "",
                "beseri": h(r, i_beseri9) if h(r, i_beseri9) in GECERLI_NOTLAR else "",
                "fiziki": h(r, i_fiziki9) if h(r, i_fiziki9) in GECERLI_NOTLAR else "",
                "sahsi":  h(r, i_sahsi9)  if h(r, i_sahsi9)  in GECERLI_NOTLAR else "",
            },
            "tarz":       tarz,
            "nihai":      h(r, i_nihai) if h(r, i_nihai) in GECERLI_NOTLAR else "",
            "ivme":       h(r, idx("İVME")) if h(r, idx("İVME")) not in ("", "-") else "",
            "yetenek_kumesi": h(r, idx("Yetenek Kümesi")),
            "iktisadi_durum": h(r, idx("İktisadi Durum")),
            "tr_gorusu":  h(r, idx("TR Görüşü")),
            "scout_notu": h(r, idx("Scout Notları")),
            "degerlendirildi": True,
        }
    return veriler


def main():
    veriler = parse(cek())
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)
    print(f"{len(veriler)} oyuncu -> {CIKTI.name}")
    for k in veriler:
        print(f"  • {k}")


if __name__ == "__main__":
    main()
