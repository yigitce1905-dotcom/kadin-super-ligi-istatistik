# -*- coding: utf-8 -*-
"""Excel'deki kulüp sütununu SD kariyer verisiyle DENETLER (hiçbir şey yazmaz).

Neden `kulup_gercek_degisim_yaz.py` yetmiyor: o script yalnızca boş↔serbest
geçişlerine bakar, kulüpten kulübe gerçek transferleri hiç görmez. Bu script
26/27 sezonunun maç kayıtlarını kullanır — SD'nin bayat `guncel_kulup` alanından
çok daha güvenilir bir sinyaldir.

Zorluk: SD aynı kulübü başka adla tutar (Gotham FC → 'Sky Blue FC' [2021'de
bırakılan ad], Angel City FC → 'WFC LA', NWSL'in yeni takımları için 'Denver
NWSL' gibi geçici adlar). Bunlar transfer DEĞİL. TAKMA_ADLAR bu çiftleri eler;
kalanlar insan gözüyle bakılacak gerçek aday listesidir.

Kullanım:  python kulup_denetim.py
"""
import json
import re
import unicodedata
from pathlib import Path

KOK = Path(__file__).parent

# SD'nin aynı kulüp için kullandığı alternatif/eski adlar → transfer sayılmaz.
# Her satır: (BİZİM yazımımız, SD'nin yazımı). Eşleşme normalize edilerek
# yapılır, ama ilk sütun aynı zamanda `kanonik_ad`ın döndürdüğü GÖRÜNEN ad
# olduğu için düzgün büyük/küçük harfle yazılmalı ('psv' değil 'PSV').
TAKMA_ADLAR = [
    ("PSV", "FCE/PSV"),                    # SD birleşik yazıyor
    ("Gotham FC", "Sky Blue FC"),          # Sky Blue FC 2021'de Gotham FC oldu
    ("Angel City FC", "WFC LA"),
    ("FC Rosengård", "LdB FC Malmö"),      # 2015'te bırakılan ad
    ("Denver Summit FC", "Denver NWSL"),   # SD yeni NWSL takımlarına geçici ad veriyor
    ("Boston Legacy FC", "NWSL Boston"),
    ("Bay FC", "Bay Area NWSL"),
    ("San Diego Wave FC", "Sacramento NWSL"),
    ("Racing Louisville FC", "Proof FC"),  # 2026 yeniden adlandırma
    ("AS Roma", "AS Rom"),
    ("Inter", "Inter Mailand"),
    ("Lokomotiv Moskva", "Lok Moskau"),
    ("Linköping FC", "Linköpings FC"),
    ("Ferencvárosi TC", "Ferencváros Budapest"),
    ("Servette FC", "CS Chenois"),
    ("Beijing Women", "BG Phoenix"),
    ("WFC Dinamo-BSUPC", "Dynamo Minsk"),
    ("FC Nasaf Qarshi", "PFC Sevinch Karshi"),
    ("RSCA Women", "RSC Anderlecht"),
    ("Breiðablik Kópavogur", "Breidablik"),
    ("Grindavík/Njarðvík", "UMFG/UMFN"),
    # SD'nin ALMANCA kulüp adları
    ("Internazionale Milano", "Inter Mailand"),
    ("AC Milan", "ACF Mailand"),
    ("RC Strasbourg", "Racing Straßburg"),
    ("Club YLA", "FC Brügge"),
    # SD'nin uzun/resmî ya da eski adları
    ("FC Nordsjælland", "Farum Boldklub"),
    ("ÍBV Vestmannaeyjar", "Iþrottabandalag Vestmannaeyja"),
    ("UWC FC", "University of Western Cape"),
    ("BDF XI", "Botswana Defence Force"),
    ("Amnokgang SC", "Amrokgang"),
    ("Budaörsi SC", "Budaörs"),
    ("Gazelle FC", "Gazelles"),
]

# Rezerv/alt takım işaretleri — 'II' taşıyan ile taşımayan AYNI kulüp değildir
_REZERV = re.compile(r"(?:^|\s)(ii|2|b|u-?\d{2})$", re.I)

# DİKKAT: 'ii', 'b', '2' BİLEREK GÜRÜLTÜ SAYILMAZ — rezerv takım ayrı kulüptür.
# Eskiden siliniyordu ve '1. FC Köln II' ile '1. FC Köln' aynı kulüp sayılıyordu;
# Vildan Kardeşler ile Lucie Schlime'a A takımı yazılacaktı (2026-08 fix).
_GURULTU = re.compile(
    r"\b(fc|cf|sc|lfc|afc|ac|as|ss|ssd|sk|if|bk|zfk|znk|wfc|ufc|club|kulubu|"
    r"kadin|womens?|women|feminin[ae]?|femminile|damen|w|university|univ)\b")


# NFKD bunları ASCII'ye indirmez, encode('ascii','ignore') de sessizce SİLER:
# 'Breiðablik' → 'Breiablik' olup 'Breidablik' ile eşleşmiyordu (3 İzlandalı
# oyuncu sahte transfer adayı olarak çıkıyordu). Önce elle çevrilir.
_HARF = str.maketrans({
    "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th", "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "Ae", "đ": "d", "Đ": "D", "ł": "l", "Ł": "L",
    "ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
})


def norm(s: str) -> str:
    s = str(s or "").translate(_HARF)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = _GURULTU.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def takma_ad_mi(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    for x, y in TAKMA_ADLAR:
        if {na, nb} == {norm(x), norm(y)}:
            return True
    return False


def kanonik_ad(sd_adi: str) -> str:
    """SD'nin eski/birleşik adını bizim tarafın adına çevirir.

    Transferi SD tespit ediyor ama adı SD'nin yazımıyla almak istemiyoruz:
    Anam Imo gerçekten Rosengård'a geçmiş, SD bunu 2015'te bırakılan
    'LdB FC Malmö' adıyla yazıyor. Eşleşme yoksa ad aynen döner."""
    n = norm(sd_adi)
    for bizim, sd in TAKMA_ADLAR:
        if n == norm(sd):
            return bizim
    return sd_adi


def ayni_mi(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return True                      # karşılaştırılamaz → sessiz geç
    if na == nb:
        return True
    # A takımı ↔ rezerv takım ayrı kulüptür: biri 'II' taşıyıp diğeri
    # taşımıyorsa ortak kelimeye rağmen AYNI sayılmaz.
    if bool(_REZERV.search(na)) != bool(_REZERV.search(nb)):
        return takma_ad_mi(a, b)
    ta, tb = set(na.split()), set(nb.split())
    if ta & tb:                          # ortak ayırt edici kelime → aynı kulüp
        return True
    return takma_ad_mi(a, b)


def main():
    kadro = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
    kar = json.load(open(KOK / "scouting_leistungsdaten.json", encoding="utf-8"))

    uyum, adaylar, veri_yok = 0, [], 0
    for isim, v in kadro.items():
        sheet = (v.get("kulup") or "").strip()
        sezonlar = (kar.get(isim) or {}).get("sezonlar") or []
        # 26/27 = güncel sezon; millî takım satırları kulüp değildir
        kulupler = [x["kulup"] for x in sezonlar
                    if x.get("sezon") == "26/27" and not x.get("milli") and x.get("kulup")]
        if not sheet or not kulupler:
            veri_yok += 1
            continue
        if any(ayni_mi(sheet, k) for k in kulupler):
            uyum += 1
        else:
            adaylar.append((isim, sheet, kulupler[0]))

    print(f"26/27 maç kaydı olan ve karşılaştırılabilen : {uyum + len(adaylar)}")
    print(f"  Excel SD ile UYUŞUYOR                    : {uyum}")
    print(f"  İncelenecek aday (olası gerçek transfer) : {len(adaylar)}")
    print(f"  Karşılaştırılamadı (26/27 verisi yok)    : {veri_yok}")
    print()
    for i, (a, s, k) in enumerate(sorted(adaylar), 1):
        print(f"  {i:3}. {a[:26]:26} excel={s[:26]:26} SD 26/27={k}")


if __name__ == "__main__":
    main()
