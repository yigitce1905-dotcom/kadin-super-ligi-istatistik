# -*- coding: utf-8 -*-
"""Sco Tr 26-27 sekmesini doldur (2026-08, tek seferlik senkron).

'Sco 🇹🇷' (25-26) sekmesindeki oyuncuları kokpit_kadrolar.json'daki (2026-27,
SoccerDonna'dan çekilmiş güncel kadrolar) 201 oyuncuyla eşleştirir:
  - Eşleşen (~115): 25-26 satırı AYNEN (nitelik notları dahil) yeni sekmeye kopyalanır.
  - Eşleşmeyen kokpit oyuncusu (~84, yeni transfer/kulüp): SoccerDonna profilinden
    KÜNYE bilgisi çekilir (uyruk/doğum/boy/ayak/sözleşme/değer/mevki); nitelik
    notları, Rol, Vücut Tipi gibi MANUEL alanlar boş bırakılır (Baran dolduracak).
  - 25-26'da olup kokpit'te olmayan (~314, örn. Göknur Güleryüz) KOPYALANMAZ.
  - Yeni sekmede zaten elle eklenmiş 3 oyuncuya (Blue Ellis, Sydney Bellamy,
    Aleksandra Markovska) DOKUNULMAZ.

Kullanım:
    python _sco_2627_sync.py            # KURU mod (önizleme, yazmaz)
    python _sco_2627_sync.py --yaz      # gerçek yazma
"""
import json, re, sys, time, unicodedata
from pathlib import Path

import gspread
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_ESKI = 864990475     # Sco 🇹🇷 (25-26)
GID_YENI = 2094311456    # Sco 26-27 🇹🇷

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
     "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.soccerdonna.de/en/"}

STOP = {"da", "de", "dos", "das", "van", "von", "bin", "al", "el", "la", "do", "du"}

KULUP_AD = {
    "Fenerbahçe": "FENERBAHÇE SK", "Galatasaray": "GALATASARAY AŞ",
    "Beşiktaş": "BEŞİKTAŞ JK", "Trabzonspor": "TRABZONSPOR AŞ",
    "FOMGET": "ANKARA BÜYÜKŞEHİR BELEDİYESİ FOMGET SPOR KULÜBÜ",
    "Amed": "AMED SPORTİF FAALİYETLER", "Fatih Vatan": "FATİH VATAN SPOR",
    "Hakkarigücü": "HAKKARİGÜCÜ SK", "Ünye": "ÜNYE GÜCÜ",
    "Giresun Sanayi": "GİRESUN SANAYİ SK", "1207 Antalya": "1207 ANTALYASPOR",
    "Yüksekovaspor": "YÜKSEKOVA SK", "Şile Bilgidoğa": "ŞİLE BİLGİ DOĞA",
    "Haymana": "HAYMANASPOR", "Bakırköy Yenimahalle": "BAKIRKÖY KADIN FUTBOL SK",
    "Kayserispor": "KAYSERİ KADIN FK",
}

KOD_MEVKI = {"TW": "GK", "IV": "LCB", "LV": "LFB", "RV": "RFB", "DM": "DMF",
             "ZM": "CMF", "OM": "AMF", "LM": "LWF", "LA": "LWF",
             "RM": "RWF", "RA": "RWF", "MS": "CFW"}
MEVKI_BOLGE = {"GK": "Kale", "LCB": "Savunma", "RCB": "Savunma", "LFB": "Savunma",
               "RFB": "Savunma", "DMF": "Orta Saha", "CMF": "Orta Saha",
               "AMF": "Orta Saha", "LWF": "Hücum", "RWF": "Hücum", "CFW": "Hücum"}

# Position metninden (kod boşsa) kaba mevki tahmini
POS_METIN_MEVKI = [
    ("goalkeeper", "GK"), ("centre-back", "LCB"), ("central defe", "LCB"),
    ("defence", "LCB"), ("left-back", "LFB"), ("left back", "LFB"),
    ("right-back", "RFB"), ("right back", "RFB"),
    ("defensive midfield", "DMF"), ("central midfield", "CMF"), ("midfield", "CMF"),
    ("attacking midfield", "AMF"), ("left wing", "LWF"), ("right wing", "RWF"),
    ("striker", "CFW"), ("forward", "CFW"), ("centre-forward", "CFW"),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip()


def toks(s: str):
    return [t for t in norm(s).split() if t and t not in STOP and len(t) > 1]


def kulup_ad_bul(kokpit_kulup: str) -> str:
    return KULUP_AD.get(kokpit_kulup, kokpit_kulup.upper())


def mevki_tahmin(pos_metin: str) -> str:
    p = (pos_metin or "").lower()
    for anahtar, kod in POS_METIN_MEVKI:
        if anahtar in p:
            return kod
    return ""


ULKE_TR = {"turkey": "Türkiye", "türkei": "Türkiye"}


def ulke_fmt(s: str) -> str:
    return ULKE_TR.get((s or "").strip().lower(), s)


def deger_fmt(eur):
    if not eur:
        return ""
    return f"€{eur:,}".replace(",", ".")


def sd_profil_cek(session, url: str) -> dict:
    """profil sayfasindan kunye alanlarini ceker (coklu-uyruk BÖLÜNMÜŞ)."""
    try:
        r = session.get(url, headers=H, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.content, "lxml")
        gecerli = {"Date of birth", "Height", "Nationality", "Position", "Foot",
                   "Market value", "Contract until", "Name in native country"}
        veri = {}
        for tablo in soup.find_all("table"):
            txt = tablo.get_text(" ", strip=True)
            if "Date of birth" not in txt and "Position" not in txt:
                continue
            for tr in tablo.find_all("tr"):
                tds = tr.find_all(["td", "th"])
                if len(tds) < 2:
                    continue
                anahtar = tds[0].get_text(strip=True).rstrip(":").strip()
                if anahtar not in gecerli:
                    continue
                if anahtar == "Nationality":
                    parcalar = [p.strip() for p in tds[1].get_text("|", strip=True).split("|") if p.strip()]
                    veri["Nationality"] = parcalar[0] if parcalar else ""
                    veri["2nd Nationality"] = parcalar[1] if len(parcalar) > 1 else ""
                else:
                    veri[anahtar] = tds[1].get_text(strip=True)
            break
        return veri
    except Exception as e:
        print(f"    [HATA] {url}: {e}")
        return {}


def main():
    yaz = "--yaz" in sys.argv

    print("Google Sheet'e bağlanılıyor…")
    gc = gspread.service_account(filename=CREDS)
    sh = gc.open_by_key(GSHEET_ID)
    ws_eski = sh.get_worksheet_by_id(GID_ESKI)
    ws_yeni = sh.get_worksheet_by_id(GID_YENI)

    vals_eski = ws_eski.get_all_values()
    hdr = vals_eski[1]
    n_col = len(hdr)
    print(f"25-26 sekmesi: {len(vals_eski)} satır, {n_col} kolon")

    vals_yeni = ws_yeni.get_all_values()
    mevcut_isimler = {norm(r[1]) for r in vals_yeni[2:] if len(r) > 1 and r[1].strip()}
    print(f"26-27 sekmesinde ZATEN olan: {len(mevcut_isimler)} oyuncu (dokunulmayacak) -> {sorted(mevcut_isimler)}")

    kok = json.load(open(KOK / "kokpit_kadrolar.json", encoding="utf-8"))

    old_rows = []
    for r in vals_eski[2:]:
        isim = r[1].strip() if len(r) > 1 else ""
        if not isim:
            continue
        tam = r[2].strip() if len(r) > 2 else ""
        tokset = set(toks(isim)) | set(toks(tam))
        old_rows.append((isim, tam, tokset, r))

    def old_satir_bul(kok_isim: str):
        kt = set(toks(kok_isim))
        if not kt:
            return None
        for isim, tam, tokset, r in old_rows:
            if kt.issubset(tokset):
                return r
        return None

    kok_oyuncular = []
    for kulup, kv in kok["kulupler"].items():
        for o in kv.get("kadro", []):
            kok_oyuncular.append((o["isim"], kulup, o))
    kok_oyuncular.sort(key=lambda x: (x[1], x[0]))

    kopyalanan, yeni_cekilecek = [], []
    for isim, kulup, o in kok_oyuncular:
        if norm(isim) in mevcut_isimler:
            continue   # zaten elle eklenmiş (Blue Ellis / Sydney Bellamy / Markovska)
        eski_satir = old_satir_bul(isim)
        if eski_satir is not None:
            kopyalanan.append((isim, kulup, eski_satir))
        else:
            yeni_cekilecek.append((isim, kulup, o))

    print(f"\n25-26'dan KOPYALANACAK (eşleşen): {len(kopyalanan)}")
    print(f"SoccerDonna'dan YENİ ÇEKİLECEK: {len(yeni_cekilecek)}")

    # ── Kopyalanan satırlar: aynen al (Nu sonra atanacak) ──
    yeni_satirlar = []
    for isim, kulup, eski_satir in kopyalanan:
        satir = list(eski_satir) + [""] * (n_col - len(eski_satir))
        yeni_satirlar.append(("KOPYA", isim, kulup, satir[:n_col]))

    # ── Yeni oyuncular: SoccerDonna'dan çek ──
    session = requests.Session()
    basarisiz = []
    for i, (isim, kulup, o) in enumerate(yeni_cekilecek, 1):
        print(f"  [{i:3d}/{len(yeni_cekilecek)}] {isim} ({kulup})…")
        sd = sd_profil_cek(session, o["profil_url"])
        time.sleep(0.8)
        if not sd:
            time.sleep(3)
            sd = sd_profil_cek(session, o["profil_url"])   # bağlantı hatası -> 1 kez tekrar dene
        if not sd:
            basarisiz.append(isim)

        kod = o.get("kod") or ""
        mevki1 = KOD_MEVKI.get(kod, "")
        if not mevki1:
            mevki1 = mevki_tahmin(sd.get("Position", ""))
        bolge = MEVKI_BOLGE.get(mevki1, "")

        ayak_ham = (sd.get("Foot") or "").lower()
        ayak = {"right": "Sağ", "left": "Sol", "both": "Çift"}.get(ayak_ham, "")

        boy = sd.get("Height", "") or (o.get("boy") or "")
        dogum = sd.get("Date of birth", "")
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", dogum or ""):
            dogum = ""
        sozlesme = sd.get("Contract until", "")
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", sozlesme or ""):
            sozlesme = ""

        deger = deger_fmt(o.get("deger_eur"))

        yas = str(o.get("yas") or "")

        satir = [""] * n_col
        satir[0] = ""  # Nu sonra
        satir[1] = isim.upper()
        satir[2] = (sd.get("Name in native country") or isim).strip()
        satir[3] = ulke_fmt(sd.get("Nationality", "") or (o.get("uyruk") or "").split("/")[0].strip())
        satir[4] = ulke_fmt(sd.get("2nd Nationality", ""))
        satir[5] = dogum
        satir[6] = yas
        satir[7] = boy
        satir[8] = ayak
        # 9 = Vücut Tipi -> boş (manuel)
        satir[10] = bolge
        satir[11] = mevki1
        # 12,13 = Mevki 2/3 -> boş
        # 14 = Rol -> boş (manuel)
        satir[15] = kulup_ad_bul(kulup)
        satir[16] = "🇹🇷 TSL"
        satir[17] = deger
        satir[18] = sozlesme
        yeni_satirlar.append(("YENİ", isim, kulup, satir))

    # ── Sırala (kulüp, isim) ve Nu ata (mevcut 3'ten sonra devam) ──
    yeni_satirlar.sort(key=lambda x: (x[2], x[1]))
    for i, (tur, isim, kulup, satir) in enumerate(yeni_satirlar, start=4):
        satir[0] = str(i)

    print(f"\nToplam yazılacak satır: {len(yeni_satirlar)} (Nu 4..{3+len(yeni_satirlar)})")
    print(f"  - Kopya: {sum(1 for t,_,_,_ in yeni_satirlar if t=='KOPYA')}")
    print(f"  - Yeni (SD): {sum(1 for t,_,_,_ in yeni_satirlar if t=='YENİ')}")
    if basarisiz:
        print(f"  [UYARI] SD'den çekilemeyen {len(basarisiz)}: {basarisiz}")

    # doğrulama ör.
    isimler_final = {norm(isim) for _, isim, _, _ in yeni_satirlar} | mevcut_isimler
    print(f"\nJessica Silva var mı: {'jessica silva' in isimler_final or 'jssica silva' in isimler_final}")
    print(f"Göknur Güleryüz var mı (OLMAMALI): {'goknur guleryuz' in isimler_final}")

    if not yaz:
        print("\n[KURU MOD] Sheet'e yazılmadı. Gerçek yazma için: python _sco_2627_sync.py --yaz")
        json.dump([s for _, _, _, s in yeni_satirlar], open(KOK / "_scratch_yeni_satirlar.json", "w", encoding="utf-8"),
                   ensure_ascii=False, indent=1)
        print("Önizleme -> _scratch_yeni_satirlar.json")
        return

    baslangic_row = 6  # row1=grup, row2=hdr, row3-5=mevcut 3 oyuncu
    bitis_row = baslangic_row + len(yeni_satirlar) - 1
    son_kol_harf = gspread.utils.rowcol_to_a1(1, n_col).rstrip("1")
    aralik = f"A{baslangic_row}:{son_kol_harf}{bitis_row}"
    ws_yeni.update(values=[s for _, _, _, s in yeni_satirlar], range_name=aralik, value_input_option="USER_ENTERED")
    print(f"\n✓ {len(yeni_satirlar)} satır YAZILDI ({aralik}).")


if __name__ == "__main__":
    main()
