# -*- coding: utf-8 -*-
"""IDEAL Sports Management — JANUARY WINDOW REPORT (İNGİLİZCE).

Hedef kitle: UEFA Women's Champions League / Women's Europa Cup seviyesindeki
Avrupa kulüplerinin sportif direktör & recruitment departmanları.

Tez: Takvim yılı (ilkbahar-sonbahar) takvimiyle oynayan ligler Kasım-Aralık'ta
biter (NWSL, Damallsvenskan, Toppserien, Brezilya, Kore, Çin, Kanada NSL...).
Bu oyuncular tam da Avrupa'nın OCAK penceresi açılırken serbest kalır.

İki kohort:
  A) Sözleşmesi 31.12.2026'da biten, DEĞERLENDİRİLMİŞ oyuncular
  B) Şu an serbest olan, DEĞERLENDİRİLMİŞ oyuncular

Çıktı: Desktop\\ISM_January_Window_Report_2027.pdf
"""
import json, pathlib, re, sys, unicodedata
from urllib.parse import quote
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)

# ── MARKA ANAHTARI (2026-08-17) ──────────────────────────────────────────────
# Kulüplere Women's Football Scouting kimliğiyle yazıyoruz; ek olarak giden
# raporun da o kimlikte olması gerekiyor, yoksa alıcı iki farklı marka görüp
# tereddüt eder. ISM sürümü duruyor:  python rapor_january_window.py --ism
_ISM = "--ism" in sys.argv
if _ISM:
    LIME = (181, 229, 0); OLIV = (106, 140, 0)          # ISM lime/oliv
    LOGO_AD = "ism_logo_beyaz.png"
    ALT_BILGI = "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43"
    DOSYA_ON = "ISM"
else:
    LIME = (168, 85, 247); OLIV = (124, 58, 237)        # site moru (#a855f7)
    LOGO_AD = "logo_beyaz.png"
    ALT_BILGI = "Women's Football Scouting · womenfootballscouting.com"
    DOSYA_ON = "WFS"
KOYU = (15, 17, 23) if not _ISM else (11, 15, 20)      # site arka planı #0f1117

HEDEF_YIL = "2026"          # 31.12.2026 biten sözleşmeler → Ocak 2027 penceresi
BASLIK_YIL = "2027"

PUAN = {"AA": 12, "A+": 11.5, "AB": 11, "BB": 10, "BC": 9,
        "CC": 8, "CD": 7, "DD": 6, "DE": 5, "EE": 4}
SERBEST = {"serbest", "free", "free agent", "bosta", "unemployed", "vereinslos"}

# Bölge alanı Dünya sheet'inde İngilizce, TR sheet'inde Türkçe → tek forma indir
BOLGE_GRUP = {
    "goalkeeper": "GK", "kale": "GK", "kaleci": "GK",
    "defender": "DEF", "savunma": "DEF", "defans": "DEF",
    "midfielder": "MID", "orta saha": "MID",
    "attacker": "FWD", "hücum": "FWD", "forvet": "FWD",
}
# Bölge boşsa mevki kodundan türet
MEVKI_GRUP = {
    "GK": "GK",
    "LCB": "DEF", "RCB": "DEF", "MCB": "DEF", "CB": "DEF",
    "LFB": "DEF", "RFB": "DEF", "LWB": "DEF", "RWB": "DEF",
    "DMF": "MID", "CMF": "MID", "AMF": "MID",
    "LWF": "FWD", "RWF": "FWD", "CFW": "FWD", "2ST": "FWD",
    "ST": "FWD", "CF": "FWD", "2ndST": "FWD",
}
GRUP_ADI = [("GK", "GOALKEEPERS"), ("DEF", "DEFENDERS"),
            ("MID", "MIDFIELDERS"), ("FWD", "FORWARDS")]


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ",
           unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore")
           .decode().lower())).strip()


def yukle():
    dunya = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
    sd    = json.load(open(KOK / "scouting_sd_profiller.json", encoding="utf-8"))
    try:
        kariyer = json.load(open(KOK / "scouting_leistungsdaten.json", encoding="utf-8"))
    except Exception:
        kariyer = {}
    return dunya, sd, kariyer


def kontrat_bitis(isim, v, sd):
    p = sd.get(isim) or {}
    s2 = (p.get("Contract until") or "").strip()
    s  = (v.get("sozlesme") or "").strip()
    return s2 if re.match(r"^\d{2}\.\d{2}\.\d{4}$", s2) else s


def son_sezon_dk(isim, kariyer):
    """25/26 kulüp maçlarındaki toplam dakika + maç (varsa)."""
    v = kariyer.get(isim) or {}
    mac = dk = 0
    for x in (v.get("sezonlar") or []):
        if x.get("sezon") == "25/26" and not x.get("milli"):
            mac += int(x.get("mac") or 0)
            dk  += int(x.get("dakika") or 0)
    return mac, dk


def grup_bul(v):
    b = BOLGE_GRUP.get((v.get("bolge") or "").strip().lower())
    if b:
        return b
    for m in (v.get("mevki") or []):
        g = MEVKI_GRUP.get((m or "").strip())
        if g:
            return g
    return None


def veri_hazirla():
    dunya, sd, kariyer = yukle()
    kohort_a, kohort_b = [], []
    for isim, v in dunya.items():
        if not v.get("degerlendirildi") or v.get("nihai") not in PUAN:
            continue
        grup = grup_bul(v)
        if not grup:
            continue
        kulup = (v.get("kulup") or "").strip()
        kb    = kontrat_bitis(isim, v, sd)
        mac, dk = son_sezon_dk(isim, kariyer)
        kayit = {
            "isim": isim, "grup": grup, "nihai": v.get("nihai"),
            "puan": PUAN[v.get("nihai")],
            "mevki": "/".join([m for m in (v.get("mevki") or []) if m][:3]),
            "yas": str(v.get("yas") or ""),
            "uyruk": (v.get("vatandaslik") or "").strip(),
            "kulup": kulup, "lig": (v.get("lig") or "").strip(),
            "kontrat": kb, "mac": mac, "dk": dk,
        }
        if kulup.lower() in SERBEST:
            kohort_b.append(kayit)
        else:
            m = re.match(r"^\d{2}\.(\d{2})\.(\d{4})$", kb)
            if m and m.group(1) == "12" and m.group(2) == HEDEF_YIL:
                kohort_a.append(kayit)
    for lst in (kohort_a, kohort_b):
        lst.sort(key=lambda x: (-x["puan"], -x["dk"]))
    return kohort_a, kohort_b


# ══════════════════════════ PDF ══════════════════════════
from fpdf import FPDF

_f = KOK / "fonts"
pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(False)
pdf.add_font("DV", "",  str(_f / "DejaVuSans.ttf"))
pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
pdf.add_font("IMZA", "", r"C:\Windows\Fonts\segoesc.ttf")
logo = KOK / "static" / LOGO_AD
X0, CW = 14, 182


def zemin():
    pdf.set_fill_color(*KREM); pdf.rect(0, 0, 210, 297, "F")


def _logo_olcu(genislik_mm):
    """Logonun mm yüksekliği (en-boy oranından). Sabit ofset kullanılamaz:
    ISM logosu 150×35 (yatık), site logosu 850×553 (neredeyse kare) — aynı
    formül ikisini birden ortalayamıyordu, marka geçişinde logo bandın
    dışına taşıyordu."""
    try:
        from PIL import Image as _Im
        w, h = _Im.open(logo).size
        return genislik_mm * h / w
    except Exception:
        return genislik_mm * 0.23          # ISM logosunun oranı (yedek)


def marka_bandi(h=13, baslik=""):
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, h, "F")
    if logo.exists():
        _lw = 32 if _ISM else 26           # kare logo daha dar durmalı
        _lh = _logo_olcu(_lw)
        if _lh > h - 3:                    # bantı taşırmasın
            _lw *= (h - 3) / _lh
            _lh = h - 3
        pdf.image(str(logo), x=10, y=(h - _lh) / 2, w=_lw)
    if baslik:
        pdf.set_xy(100, h / 2 - 3); pdf.set_font("DV", "B", 10.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(100, 6, baslik, align="R")


def alt_bilgi(no):
    pdf.set_y(-14); pdf.set_font("DV", "", 7.4); pdf.set_text_color(*GRIM)
    pdf.set_x(X0)
    pdf.cell(CW / 2, 5, ALT_BILGI)
    pdf.cell(CW / 2, 5, f"Page {no}", align="R")


def not_rengi(nihai):
    p = PUAN.get(nihai, 0)
    if p >= 11:  return (22, 130, 62)      # AA/AB — koyu yeşil
    if p >= 9.5: return (106, 140, 0)      # BB    — oliv
    if p >= 8.5: return (176, 138, 0)      # BC    — hardal
    return (150, 90, 30)                   # CC ↓


# ────────── KAPAK ──────────
def kapak(kohort_a, kohort_b):
    pdf.add_page(); zemin()
    marka_bandi(h=34)
    pdf.set_xy(14, 44); pdf.set_font("DV", "B", 25); pdf.set_text_color(*METIN)
    pdf.cell(0, 11, f"JANUARY WINDOW REPORT", ln=1)
    pdf.set_x(14); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*OLIV)
    pdf.cell(0, 6, f"WOMEN'S FOOTBALL · AVAILABLE FOR JANUARY {BASLIK_YIL}", ln=1)

    pdf.set_xy(14, 64); pdf.set_font("DV", "B", 12); pdf.set_text_color(*METIN)
    pdf.multi_cell(178, 6.6,
        "The calendar-year leagues finish in November and December.\n"
        "Their players come free exactly as your January window opens.")

    pdf.set_xy(14, 84); pdf.set_font("DV", "", 9.4); pdf.set_text_color(60, 68, 82)
    pdf.multi_cell(172, 5.5,
        "While European clubs play an autumn-to-spring calendar, a large part of the world's "
        "women's football — the NWSL and the new Canadian NSL, Sweden, Norway and Finland, "
        "Brazil, South Korea and China — runs on a spring-to-autumn season that ends in "
        "November or December. Contracts in those leagues expire on 31 December.")
    pdf.ln(1)
    pdf.set_x(14)
    pdf.multi_cell(172, 5.5,
        "This report lists the players in our assessed pool who become available in that "
        "window, and the players who are already free agents. Every player here carries our "
        "own analyst assessment against a fixed 44-attribute framework — not a scraped rating.")

    _ozet = [(str(len(kohort_a)), "EXPIRING 31 DEC"), (str(len(kohort_b)), "FREE AGENTS"),
             (str(len({k['uyruk'] for k in kohort_a + kohort_b if k['uyruk']})), "NATIONALITIES"),
             (str(len({k['lig'] for k in kohort_a + kohort_b if k['lig']})), "LEAGUES")]
    oy = 140; bw, bh = 42, 26
    for i, (deger, et) in enumerate(_ozet):
        x = 14 + i * (bw + 3.5)
        pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
        pdf.rect(x, oy, bw, bh, "DF")
        pdf.set_fill_color(*LIME); pdf.rect(x, oy, bw, 1.6, "F")
        pdf.set_xy(x, oy + 5); pdf.set_text_color(*METIN); pdf.set_font("DV", "B", 16)
        pdf.cell(bw, 8, deger, align="C")
        pdf.set_xy(x, oy + 16); pdf.set_text_color(*GRIM); pdf.set_font("DV", "", 6.2)
        pdf.cell(bw, 4, et, align="C")

    # Not skalası açıklaması
    pdf.set_xy(14, 176); pdf.set_font("DV", "B", 9); pdf.set_text_color(*METIN)
    pdf.cell(0, 5.5, "Rating scale", ln=1)
    pdf.set_x(14); pdf.set_font("DV", "", 8.6); pdf.set_text_color(60, 68, 82)
    pdf.multi_cell(172, 5.0,
        "AA (highest) · AB · BB · BC · CC · CD · DD · DE · EE. The grade reflects our analysts' "
        "overall verdict on the player's current level. \"Last season\" columns show 25/26 club "
        "appearances and minutes where available.")

    pdf.set_xy(14, 208); pdf.set_font("DV", "B", 9); pdf.set_text_color(*METIN)
    pdf.cell(0, 5.5, "How to use this report", ln=1)
    pdf.set_x(14); pdf.set_font("DV", "", 8.6); pdf.set_text_color(60, 68, 82)
    pdf.multi_cell(172, 5.0,
        "Tell us the position you need and your budget ceiling. We will return a ranked "
        "shortlist from this pool with full attribute breakdowns, video and our honest "
        "reservations on each candidate — at no cost, so you can measure our work against "
        "what you already have.")

    # imza
    pdf.set_xy(14, 246); pdf.set_font("IMZA", "", 17); pdf.set_text_color(*METIN)
    pdf.cell(80, 9, "Yiğit Çelebi", ln=1)
    pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.line(15, 257, 76, 257)
    pdf.set_xy(15, 258); pdf.set_font("DV", "B", 8.5); pdf.set_text_color(*METIN)
    pdf.cell(90, 5, "Yiğit Çelebi · "
             + ("IDEAL Sports Management" if _ISM else "Women's Football Scouting"), ln=1)
    pdf.set_x(15); pdf.set_font("DV", "", 7.8); pdf.set_text_color(*GRIM)
    pdf.cell(90, 4.5, "+90 506 578 46 43 · womenfootballscouting.com", ln=1)


# ────────── TABLO ──────────
SUT = [("PLAYER", 46), ("POS", 20), ("AGE", 9), ("NATIONALITY", 27),
       ("CURRENT CLUB", 40), ("25/26", 18), ("RATING", 12)]
SATIR_H = 7.4


def tablo_basligi(y):
    pdf.set_fill_color(*KOYU); pdf.rect(X0, y, CW, 7, "F")
    x = X0 + 3
    pdf.set_font("DV", "B", 6.6); pdf.set_text_color(255, 255, 255)
    for ad, w in SUT:
        pdf.set_xy(x, y + 1.2)
        pdf.cell(w, 4.6, ad, align=("C" if ad in ("AGE", "25/26", "RATING") else "L"))
        x += w
    return y + 7


def satir_ciz(k, y, cift):
    if cift:
        pdf.set_fill_color(245, 243, 236); pdf.rect(X0, y, CW, SATIR_H, "F")
    x = X0 + 3
    pdf.set_font("DV", "B", 8.2); pdf.set_text_color(*METIN)
    pdf.set_xy(x, y + 1.6)
    _isim = k["isim"]
    while pdf.get_string_width(_isim) > SUT[0][1] - 2 and len(_isim) > 8:
        _isim = _isim[:-2]
    pdf.cell(SUT[0][1], 4.4, _isim,
             link=f"https://womenfootballscouting.com/?paylas={quote(k['isim'])}")
    x += SUT[0][1]

    pdf.set_font("DV", "", 7.6); pdf.set_text_color(60, 68, 82)
    for deger, (ad, w) in zip(
            [k["mevki"], k["yas"], k["uyruk"], k["kulup"]], SUT[1:5]):
        pdf.set_xy(x, y + 1.6)
        d = str(deger)
        while pdf.get_string_width(d) > w - 2 and len(d) > 4:
            d = d[:-2]
        pdf.cell(w, 4.4, d, align=("C" if ad == "AGE" else "L"))
        x += w

    # 25/26 maç/dakika
    pdf.set_xy(x, y + 1.6)
    ozet = f"{k['mac']}m · {k['dk']}'" if k["mac"] else "—"
    pdf.set_font("DV", "", 7.0)
    pdf.cell(SUT[5][1], 4.4, ozet, align="C")
    x += SUT[5][1]

    # Not rozeti
    r, g, b = not_rengi(k["nihai"])
    pdf.set_fill_color(r, g, b)
    pdf.rect(x + 1, y + 1.3, SUT[6][1] - 3, 5, "F")
    pdf.set_xy(x + 1, y + 1.6); pdf.set_font("DV", "B", 7.6)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(SUT[6][1] - 3, 4.4, k["nihai"], align="C")
    return y + SATIR_H


def bolum_yaz(baslik, altbaslik, kayitlar, sayfa_no):
    """Bir kohortu mevki gruplarına ayırıp tablo hâlinde yazar."""
    gruplu = defaultdict(list)
    for k in kayitlar:
        gruplu[k["grup"]].append(k)

    ilk = True
    for gk, gad in GRUP_ADI:
        lst = gruplu.get(gk) or []
        if not lst:
            continue
        pdf.add_page(); zemin()
        sayfa_no += 1
        marka_bandi(h=13, baslik=f"JANUARY WINDOW {BASLIK_YIL}")
        pdf.set_fill_color(*LIME); pdf.rect(X0, 19, 3.2, 8, "F")
        pdf.set_xy(X0 + 7, 19.4); pdf.set_font("DV", "B", 14); pdf.set_text_color(*METIN)
        pdf.cell(100, 7, gad)
        pdf.set_font("DV", "", 8.6); pdf.set_text_color(*GRIM)
        pdf.set_xy(X0, 19.6); pdf.cell(CW, 7, f"{baslik} · {len(lst)} players", align="R")
        pdf.set_xy(X0 + 7, 26.5); pdf.set_font("DV", "", 7.8); pdf.set_text_color(*GRIM)
        pdf.cell(160, 5, altbaslik)

        y = tablo_basligi(34)
        for i, k in enumerate(lst):
            if y + SATIR_H > 276:
                alt_bilgi(sayfa_no)
                pdf.add_page(); zemin(); sayfa_no += 1
                marka_bandi(h=13, baslik=f"JANUARY WINDOW {BASLIK_YIL}")
                pdf.set_fill_color(*LIME); pdf.rect(X0, 19, 3.2, 8, "F")
                pdf.set_xy(X0 + 7, 19.4); pdf.set_font("DV", "B", 14); pdf.set_text_color(*METIN)
                pdf.cell(100, 7, gad + " · cont.")
                y = tablo_basligi(34)
            y = satir_ciz(k, y, i % 2 == 1)
        alt_bilgi(sayfa_no)
    return sayfa_no


def main():
    kohort_a, kohort_b = veri_hazirla()
    kapak(kohort_a, kohort_b)
    sayfa = 1
    sayfa = bolum_yaz("Contract expires 31 Dec 2026",
                      "Contracts in calendar-year leagues expire on 31 December — "
                      "these players are available for the January window.",
                      kohort_a, sayfa)
    sayfa = bolum_yaz("Free agents",
                      "Currently without a club — available immediately.",
                      kohort_b, sayfa)
    cikti = pathlib.Path.home() / "Desktop" / f"{DOSYA_ON}_January_Window_Report_{BASLIK_YIL}.pdf"
    pdf.output(str(cikti))
    print(f"OK {cikti} ({cikti.stat().st_size // 1024} KB)")
    print(f"   31 Aralık biten: {len(kohort_a)} · serbest: {len(kohort_b)} · sayfa: {sayfa}")


if __name__ == "__main__":
    main()
