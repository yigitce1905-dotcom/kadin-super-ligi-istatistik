"""
'Scouting is life' Google Sheet --> 'Sco 🌍' sekmesi (gid=1707810792)
Tüm scout kadro tablosunu çeker -> scout_kadro_raporlar.json

Bu dosya artık Scouting sayfasının HEM roster (oyuncu listesi) HEM zengin
rapor kaynağıdır. Tüm oyuncular alınır (değerlendirilmemiş olanlar dahil);
boş/yanlış (126) yaş alanları SoccerDonna profilinden (scouting_sd_profiller.json)
backfill edilir.

Sütun düzeni dinamik: grup sınırları header satırındaki başlık adlarından
bulunur (kolon eklense de kaymaz). Kullanım:  python fetch_scout_kadro.py
"""
import csv, io, json
from pathlib import Path
import requests

GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID       = "1707810792"
CIKTI     = Path(__file__).parent / "scout_kadro_raporlar.json"
SD_YOL    = Path(__file__).parent / "scouting_sd_profiller.json"
GECERLI_NOTLAR = {"AA","AB","BB","BC","CC","CD","DD","DE","EE","FF","A+"}


def cek() -> str:
    url = (f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
           f"/export?format=csv&gid={GID}")
    r = requests.get(url, timeout=25); r.raise_for_status()
    return r.content.decode("utf-8")


def _yas_hesapla(dogum: str):
    """'30.10.2007' -> yaş (int). Geçersizse None."""
    import datetime
    for sep in (".", "/", "-"):
        if sep in dogum:
            parca = dogum.split(sep)
            if len(parca) == 3:
                try:
                    g, a, y = (int(x) for x in parca)
                    if y < 100:
                        y += 2000 if y < 30 else 1900
                    bugun = datetime.date.today()
                    yas = bugun.year - y - ((bugun.month, bugun.day) < (a, g))
                    if 5 <= yas <= 60:
                        return yas
                except Exception:
                    return None
    return None


def parse(metin: str) -> dict:
    rows = list(csv.reader(io.StringIO(metin)))
    hdr  = rows[1]

    def idx(ad):
        return hdr.index(ad)

    def idx_baslar(*adaylar):
        """Başlığı verilen ön-eklerden biriyle başlayan ilk kolon indexi."""
        for i, h in enumerate(hdr):
            for a in adaylar:
                if h.strip().startswith(a):
                    return i
        raise ValueError(f"Kolon bulunamadı: {adaylar}")

    # Nitelik grup sınırları (makro NOT başlıkları 'BECERİ N' biçiminde)
    i_beceri0 = idx("Bitiricilik")
    i_beceri9 = idx_baslar("BECERİ")
    i_beseri0, i_beseri9 = i_beceri9 + 1, idx_baslar("BEŞERİ")
    i_fiziki0, i_fiziki9 = i_beseri9 + 1, idx_baslar("FİZİKİ")
    i_sahsi0,  i_sahsi9  = i_fiziki9 + 1, idx_baslar("ŞAHSİ")
    i_tarz0  = i_sahsi9 + 1
    i_nihai  = idx_baslar("NİHAİ")
    i_ivme   = idx_baslar("İVME")

    # ── Sabit alan kolonları BAŞLIK ADINA göre (kolon kaymalarına dayanıklı) ──
    # Not: 2024→ sheet'te kolonlar 2 sola kaydı (Oyuncu Adı 3→1). Sabit indeks
    # yerine başlık adıyla bulmak, ileride yine kayarsa kırılmayı önler.
    c_isim   = idx_baslar("Oyuncu Adı")
    c_tam    = idx_baslar("Tam İsim")
    c_vat    = idx_baslar("Vatandaşlık")        # "Vatandaşlık (Millî)" — "2." ile başlamaz
    c_mil    = idx_baslar("2. Vatandaşlık")     # = 2. pasaport. DİKKAT: bu MİLLİ TAKIM DEĞİL!
    # (app milli takımı 'vatandaslik' = "Vatandaşlık (Millî)" alanından alır. milli_takim
    #  adı tarihsel/yanıltıcı; aslında ikinci vatandaşlık. NT için kullanma.)
    c_dog    = idx_baslar("Doğum")
    c_yas    = idx_baslar("Yaş")
    c_boy    = idx_baslar("Boy")
    c_ayak   = idx_baslar("Ayak")
    c_vucut  = idx_baslar("Vücut")
    c_bolge  = idx_baslar("Bölge")
    c_mevki  = [idx_baslar("Mevki 1"), idx_baslar("Mevki 2"), idx_baslar("Mevki 3")]
    c_rol    = idx_baslar("Rol")
    c_kulup  = idx_baslar("Kulüp")
    c_lig    = idx_baslar("Lig")
    c_deger  = idx_baslar("Değer")
    c_sozl   = idx_baslar("Sözleşme")

    def h(r, i):
        return r[i].strip() if i < len(r) else ""

    def nitelik(r, i0, i9):
        return {hdr[i]: h(r, i) for i in range(i0, i9) if h(r, i) in GECERLI_NOTLAR}

    veriler = {}
    _bos_ardisik = 0
    for r in rows[2:]:
        if not r or not h(r, c_isim):      # Oyuncu Adı (eşleşme anahtarı)
            _bos_ardisik += 1
            # Ana liste ile ALTTAKİ ayrı bölüm (Afrika milli takım kadroları vb.) arasında
            # ~200 satırlık boşluk var. Büyük boşluk = ikinci blok başladı → DUR.
            if veriler and _bos_ardisik >= 20:
                break
            continue
        _bos_ardisik = 0
        isim = h(r, c_isim)

        beceri = nitelik(r, i_beceri0, i_beceri9)
        beseri = nitelik(r, i_beseri0, i_beseri9)
        fiziki = nitelik(r, i_fiziki0, i_fiziki9)
        sahsi  = nitelik(r, i_sahsi0,  i_sahsi9)
        tum = (list(beceri.values()) + list(beseri.values())
               + list(fiziki.values()) + list(sahsi.values()))
        degerlendirildi = bool(tum) and any(n != "FF" for n in tum)

        tarz = []
        for i in range(i_tarz0, i_nihai):
            v = h(r, i)
            if v and v != "✘":             # ✘ = özellik yok; ✔/✔︎ = var
                tarz.append(hdr[i])

        mevki = [h(r, j).replace("-", "") for j in c_mevki
                 if h(r, j) and h(r, j) != "-"]

        dogum = h(r, c_dog)
        yas_h = h(r, c_yas)
        # Sheet yaşı sadece geçerliyse al (126 = boş DT formülü → atılır)
        try:
            yas = int(yas_h)
            if not (5 <= yas <= 60):
                yas = ""
        except ValueError:
            yas = ""
        if yas == "" and dogum:
            y2 = _yas_hesapla(dogum)
            if y2:
                yas = y2

        kayit = {
            "tam_isim":    h(r, c_tam),
            "vatandaslik": h(r, c_vat),
            "milli_takim": h(r, c_mil),
            "dogum":       dogum,
            "yas":         yas,
            "boy":         h(r, c_boy),
            "ayak":        h(r, c_ayak),
            "vucut_tipi":  h(r, c_vucut),
            "bolge":       h(r, c_bolge),
            "mevki":       mevki,
            "rol":         h(r, c_rol),
            "kulup":       h(r, c_kulup),
            "lig":         h(r, c_lig),
            "deger":       h(r, c_deger),
            "sozlesme":    h(r, c_sozl),
            "beceri": beceri, "beseri": beseri, "fiziki": fiziki, "sahsi": sahsi,
            "makro": {
                "beceri": h(r, i_beceri9) if h(r, i_beceri9) in GECERLI_NOTLAR else "",
                "beseri": h(r, i_beseri9) if h(r, i_beseri9) in GECERLI_NOTLAR else "",
                "fiziki": h(r, i_fiziki9) if h(r, i_fiziki9) in GECERLI_NOTLAR else "",
                "sahsi":  h(r, i_sahsi9)  if h(r, i_sahsi9)  in GECERLI_NOTLAR else "",
            },
            "tarz":       tarz,
            "nihai":      h(r, i_nihai) if h(r, i_nihai) in GECERLI_NOTLAR else "",
            "ivme":       h(r, i_ivme) if h(r, i_ivme) not in ("", "-") else "",
            "yetenek_kumesi": h(r, idx("Yetenek Kümesi")),
            "iktisadi_durum": h(r, idx("İktisadi Durum")),
            "tr_gorusu":  h(r, idx("TR Görüşü")),
            "scout_notu": h(r, idx("Scout Notları")),
            "degerlendirildi": degerlendirildi,
        }

        # Çift kayıt (transfer/duplike): değerlendirilmiş olan kazanır
        if isim in veriler and veriler[isim]["degerlendirildi"] and not degerlendirildi:
            continue
        veriler[isim] = kayit

    return veriler


def yas_backfill(veriler: dict) -> int:
    """Yaşı/doğumu boş olanları SoccerDonna profilinden tamamla."""
    if not SD_YOL.exists():
        return 0
    sd = json.load(open(SD_YOL, encoding="utf-8"))
    n = 0
    for isim, k in veriler.items():
        if k.get("yas"):
            continue
        p = sd.get(isim)
        if not isinstance(p, dict):
            continue
        dob = p.get("Date of birth", "")
        if not k.get("dogum") and dob:
            k["dogum"] = dob
        # SD 'Age' alanı "18" veya "18 years" olabilir
        y = _yas_hesapla(k.get("dogum", "")) if k.get("dogum") else None
        if not y:
            import re
            m = re.search(r"\d{1,2}", str(p.get("Age", "")))
            if m:
                yy = int(m.group())
                y = yy if 5 <= yy <= 60 else None
        if y:
            k["yas"] = y
            n += 1
    return n


def main():
    veriler = parse(cek())
    bf = yas_backfill(veriler)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)
    n_ok = sum(1 for v in veriler.values() if v["degerlendirildi"])
    n_yas = sum(1 for v in veriler.values() if v.get("yas"))
    print(f"{len(veriler)} oyuncu ({n_ok} değerlendirilmiş) -> {CIKTI.name}")
    print(f"Yaş dolu: {n_yas}/{len(veriler)} (SD backfill: {bf})")


if __name__ == "__main__":
    main()
