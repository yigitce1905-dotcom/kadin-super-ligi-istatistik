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
# Her satır: sheet'teki ad ile SD'nin adı (ikisi de normalize edilerek eşleşir).
TAKMA_ADLAR = [
    ("gotham", "sky blue"),            # Sky Blue FC 2021'de Gotham FC oldu
    ("angel city", "wfc la"),
    ("rosengard", "ldb malmo"),        # LdB FC Malmö → FC Rosengård
    ("denver summit", "denver nwsl"),  # SD yeni NWSL takımlarına gecici ad veriyor
    ("boston legacy", "nwsl boston"),
    ("bay", "bay area nwsl"),
    ("san diego wave", "sacramento nwsl"),
    ("racing louisville", "proof"),    # 2026 yeniden adlandirma
    ("roma", "rom"),
    ("inter", "inter mailand"),
    ("linkoping", "linkopings"),
    ("ferencvarosi tc", "ferencvaros budapest"),
    ("servette", "cs chenois"),
    ("beijing women", "bg phoenix"),
    ("dinamo bsupc", "dynamo minsk"),
    ("nasaf qarshi", "pfc sevinch karshi"),
    ("rsca women", "rsc anderlecht"),
    ("breidablik kopavogur", "breidablik"),
    ("grindavik njardvik", "umfg umfn"),
    ("hafnarfjordur", "hafnarfjordur"),
]

_GURULTU = re.compile(
    r"\b(fc|cf|sc|lfc|afc|ac|as|ss|ssd|sk|if|bk|zfk|znk|wfc|ufc|club|kulubu|"
    r"kadin|womens?|women|feminin[ae]?|femminile|damen|w|ii|b|university|univ)\b")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = _GURULTU.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def takma_ad_mi(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    for x, y in TAKMA_ADLAR:
        if {na, nb} == {norm(x), norm(y)}:
            return True
    return False


def ayni_mi(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return True                      # karşılaştırılamaz → sessiz geç
    if na == nb:
        return True
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
