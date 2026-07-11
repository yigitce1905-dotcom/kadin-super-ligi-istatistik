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
    """2026-07: Baran Sco Tr sekmesini Sco 🌍 düzenine geçirdi (isim 1. kolon,
    'BECERİ Not' başlıkları, +KALECİ bloğu). Başlık adları büyük/küçük harf
    duyarsız aranır; çıktı şeması (site uyumu için) DEĞİŞMEDİ + kaleci eklendi."""
    rows = list(csv.reader(io.StringIO(metin)))
    hdr  = [h.strip() for h in rows[1]]  # 2. satir = kolon adlari
    HU   = [h.upper() for h in hdr]

    def idx(*adlar) -> int:
        for ad in adlar:                       # önce tam eşleşme
            au = ad.upper()
            if au in HU:
                return HU.index(au)
        for ad in adlar:                       # sonra 'başlar' eşleşmesi
            au = ad.upper()
            for j, h in enumerate(HU):
                if h.startswith(au):
                    return j
        raise ValueError(f"Kolon bulunamadı: {adlar}")

    i_isim    = idx("İsim - Soyisim", "Oyuncu Adı")
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
    # KALECİ bloğu (yeni) — yoksa None
    try:
        i_kaleci0 = idx("Elle Kontrol")
        i_kaleci9 = idx("KALECİ NOT")
    except ValueError:
        i_kaleci0 = i_kaleci9 = None
    i_bolge  = idx("Bölge")
    c_mevki  = [j for j, h in enumerate(hdr) if h.startswith("Mevki")]
    i_kulup  = idx("Kulüp")
    i_dogum  = idx("Doğum Tarihi")
    i_yas    = idx("Yaş")
    i_uyruk  = idx("Vatandaşlık")
    i_rol    = idx("Rol")

    def hucre(r, i):
        return r[i].strip() if (i is not None and i < len(r)) else ""

    def nitelikler(r, i0, i9):
        out = {}
        for i in range(i0, i9):
            v = hucre(r, i)
            if v in GECERLI_NOTLAR:
                out[hdr[i]] = v
        return out

    veriler = {}
    for r in rows[2:]:
        isim = hucre(r, i_isim)
        if not isim:
            continue

        beceri = nitelikler(r, i_beceri0, i_beceri9)
        beseri = nitelikler(r, i_beseri0, i_beseri9)
        fiziki = nitelikler(r, i_fiziki0, i_fiziki9)
        sahsi  = nitelikler(r, i_sahsi0,  i_sahsi9)

        # Kaleci bloğu SADECE kalecilere (diğerlerinde FF ile dolu geliyor)
        _gk = (hucre(r, i_bolge) == "Kaleci"
               or any(hucre(r, j).upper() == "GK" for j in c_mevki))
        kaleci = (nitelikler(r, i_kaleci0, i_kaleci9)
                  if (_gk and i_kaleci0 is not None) else {})

        # Degerlendirilmis = FF disinda en az bir nitelik notu var
        tum = (list(beceri.values()) + list(beseri.values())
               + list(fiziki.values()) + list(sahsi.values()) + list(kaleci.values()))
        degerlendirildi = any(n != "FF" for n in tum)

        # Tarz: '✘' = ozellik yok; isaretli (✘ disi dolu) olanlar listelenir
        tarz = []
        for i in range(i_tarz0, i_nihai):
            v = hucre(r, i)
            if v and v != "✘":
                tarz.append(hdr[i])

        nihai = hucre(r, i_nihai)
        ivme  = hucre(r, i_ivme)

        def _ops(*adlar):
            """İsteğe bağlı kolon (yeni şemada var, yoksa boş döner)."""
            try:
                return hucre(r, idx(*adlar))
            except ValueError:
                return ""

        kayit = {
            "takim":      hucre(r, i_kulup),
            "dogum":      hucre(r, i_dogum),
            "bolge":      hucre(r, i_bolge),
            "mevki1":     hucre(r, c_mevki[0]).replace("-", "") if c_mevki else "",
            "mevki2":     hucre(r, c_mevki[1]).replace("-", "") if len(c_mevki) > 1 else "",
            "rol":        hucre(r, i_rol).replace("-", ""),
            "yas":        hucre(r, i_yas),
            "uyruk":      hucre(r, i_uyruk),
            # ── Scouting entegrasyonu için zengin künye (yeni şema kolonları) ──
            "tam_isim":   _ops("Sporcunun Tam İsmi", "Tam İsim"),
            "milli_takim": _ops("2. Vatandaşlık"),   # dünya parser konvansiyonu (2. pasaport)
            "boy":        _ops("Boy"),
            "ayak":       _ops("Ayak"),
            "lig":        _ops("Lig"),
            "deger":      _ops("Değeri", "Değer"),
            "sozlesme":   _ops("Sözleşme"),
            "yetenek_kumesi":  _ops("Yetenek Kümesi"),
            "iktisadi_durum":  _ops("İktisadi Durum"),
            "yurtdisi_gorusu": _ops("Yurtdışı Görüşü"),
            "beceri":     beceri,
            "beseri":     beseri,
            "fiziki":     fiziki,
            "sahsi":      sahsi,
            "kaleci":     kaleci,
            "makro": {
                "beceri": hucre(r, i_beceri9) if hucre(r, i_beceri9) in GECERLI_NOTLAR else "",
                "beseri": hucre(r, i_beseri9) if hucre(r, i_beseri9) in GECERLI_NOTLAR else "",
                "fiziki": hucre(r, i_fiziki9) if hucre(r, i_fiziki9) in GECERLI_NOTLAR else "",
                "sahsi":  hucre(r, i_sahsi9)  if hucre(r, i_sahsi9)  in GECERLI_NOTLAR else "",
                "kaleci": hucre(r, i_kaleci9) if (_gk and hucre(r, i_kaleci9) in GECERLI_NOTLAR) else "",
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
