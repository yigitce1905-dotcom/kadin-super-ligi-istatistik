# -*- coding: utf-8 -*-
"""IDEAL Sports Management — kulüplere gönderilecek oyuncu portföyü PDF'i.

Rakip 'FV Shortlist' şablonuyla aynı kurgu: Sayfa 1 = diziliş sahası,
Sayfa 2 = bilgi tablosu. Fark: ISM markası (koyu zemin + #B5E500 lime) ve
her oyuncuda TIKLANABİLİR womenfootballscouting.com scout raporu linki.

Kullanım:  python portfoy_ism.py          -> Desktop\\ISM_Turkiye_Portfoyu_2026.pdf
Kadro değişikliği: aşağıdaki KADRO/YEDEK listelerini düzenle, tekrar çalıştır.
"""
import json, pathlib, sys
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

# ── Marka ──
LIME  = (181, 229, 0)      # #B5E500 (logodan örneklendi)
KOYU  = (11, 15, 20)       # koyu zemin
CIM   = (35, 122, 31)
CIM2  = (42, 143, 38)
BEYAZ = (255, 255, 255)
GRI   = (120, 133, 151)

# ── Kadro: (isim, saha_etiketi, x%, y%) — 4-2-3-1, y: 0 üst(kale) ──
# y: 0 üst (rakip kalesi/hücum) — 100 alt (bizim kale). Kaleci ALTTA.
KADRO = [
    ("Kader Hancar",      "ST",  50, 17),
    ("Ana Barjaktarovic", "SLK", 16, 34), ("Miray Cin",      "OOS", 50, 33.5),
    ("Aude Gbedjissi",    "SĞK", 84, 34),
    ("Meryem Cal",        "DOS", 37, 55), ("Sibel Koksal",   "DOS", 63, 55),
    ("Sumaya Komuntale",  "SLB", 16, 72), ("Tanja Malesija", "STP", 37, 74),
    ("Aude Bizet",        "STP", 63, 74), ("Miray Ayhan",    "SĞB", 84, 72),
    ("Angelina Portnova", "KL",  50, 86.5),
]
YEDEK = ["Ajsa Kalac", "Ceylin Erata", "Fatma Sakar", "Natalia Wrobel"]

# Elle doğrulanmış highlight videoları (oEmbed teyitli). Bu listede olmayan
# oyuncunun Video linki YouTube aramasına gider. Yeni link: isim -> watch URL.
VIDEO_OZEL = {
    "Tanja Malesija":   "https://www.youtube.com/watch?v=xcnlaBSvE0U",
    "Sumaya Komuntale": "https://www.youtube.com/watch?v=jZrWPtQ7mes",
    "Meryem Cal":       "https://www.youtube.com/watch?v=t3ipOG4dtCg",
    "Aude Gbedjissi":   "https://www.youtube.com/watch?v=kxAw0NevflY",
    "Kader Hancar":     "https://www.youtube.com/watch?v=N6JZzG15pG8",
}

d = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))

def bilgi_cumlesi(r):
    """Kısa satış cümlesi: boy + rol + TR görüşü/serbestlik."""
    parca = []
    if r.get("boy"):
        parca.append(f"{r['boy']} boy")
    if r.get("rol"):
        parca.append(r["rol"])
    tr = (r.get("tr_gorusu") or "").strip()
    if "Çok İstekli" in tr:
        parca.append("Türkiye'ye ÇOK istekli")
    elif "İstekli" in tr and "İsteksiz" not in tr:
        parca.append("Türkiye'ye istekli")
    if (r.get("kulup") or "").strip().lower() == "serbest":
        parca.append("BONSERVİSSİZ")
    return " · ".join(parca) if parca else "—"

def dogum_yili(r):
    dg = str(r.get("dogum") or "")
    return dg.split(".")[-1] if "." in dg else (dg or str(r.get("yas") or "—"))

from fpdf import FPDF
_f = KOK / "fonts"
pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(False)
pdf.add_font("DV", "", str(_f / "DejaVuSans.ttf"))
pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))

# ════════ SAYFA 1 — KAPAK + DİZİLİŞ SAHASI ════════
pdf.add_page()
pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, 297, "F")

# üst bant: logo + başlık
logo = KOK / "static" / "ism_logo_beyaz.png"
if logo.exists():
    pdf.image(str(logo), x=14, y=12, w=52)
pdf.set_xy(14, 26); pdf.set_font("DV", "B", 22); pdf.set_text_color(*BEYAZ)
pdf.cell(0, 10, "TÜRKİYE PORTFÖYÜ", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 11); pdf.set_text_color(*LIME)
pdf.cell(0, 6, "KADIN FUTBOLU · YAZ 2026 TRANSFER DÖNEMİ", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 8.5); pdf.set_text_color(*GRI)
pdf.cell(0, 5, "Scout altyapısı: womenfootballscouting.com — 1.400+ oyuncu, 47 nitelik", ln=1)

# saha
SX, SY, SW, SH = 30, 58, 150, 205
serit = SH / 7
for i in range(7):
    pdf.set_fill_color(*(CIM if i % 2 == 0 else CIM2))
    pdf.rect(SX, SY + i * serit, SW, serit, "F")
pdf.set_draw_color(255, 255, 255); pdf.set_line_width(0.7)
pdf.rect(SX, SY, SW, SH)                                   # sınır
pdf.line(SX, SY + SH / 2, SX + SW, SY + SH / 2)            # orta çizgi
pdf.ellipse(SX + SW/2 - 18, SY + SH/2 - 18, 36, 36)        # orta daire
pdf.rect(SX + SW*0.22, SY, SW*0.56, 34)                    # üst ceza sahası
pdf.rect(SX + SW*0.36, SY, SW*0.28, 13)
pdf.rect(SX + SW*0.22, SY + SH - 34, SW*0.56, 34)          # alt ceza sahası
pdf.rect(SX + SW*0.36, SY + SH - 13, SW*0.28, 13)

# oyuncular
for isim, etiket, xp, yp in KADRO:
    r = d.get(isim, {})
    cx = SX + SW * xp / 100
    cy = SY + SH * yp / 100
    pdf.set_fill_color(*KOYU); pdf.set_draw_color(*LIME); pdf.set_line_width(0.9)
    pdf.ellipse(cx - 6.5, cy - 6.5, 13, 13, "DF")
    pdf.set_xy(cx - 6.5, cy - 3.4); pdf.set_font("DV", "B", 7); pdf.set_text_color(*LIME)
    pdf.cell(13, 7, etiket, align="C")
    pdf.set_xy(cx - 26, cy + 7.2); pdf.set_font("DV", "B", 8.2); pdf.set_text_color(*BEYAZ)
    pdf.cell(52, 4, isim, align="C")
    alt = f"{r.get('yas','?')} · {(r.get('kulup') or '—')[:20]}"
    pdf.set_xy(cx - 26, cy + 11.2); pdf.set_font("DV", "", 6.4); pdf.set_text_color(225, 232, 240)
    pdf.cell(52, 3.4, alt, align="C")

# yedekler şeridi
pdf.set_xy(14, 270); pdf.set_font("DV", "B", 9); pdf.set_text_color(*LIME)
pdf.cell(28, 6, "KADRO EKİ:")
pdf.set_font("DV", "", 9); pdf.set_text_color(*BEYAZ)
pdf.cell(0, 6, "  ·  ".join(YEDEK), ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 7.5); pdf.set_text_color(*GRI)
pdf.cell(0, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43", ln=1)

# ════════ SAYFA 2 — BİLGİ TABLOSU ════════
pdf.add_page()
pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, 26, "F")
if logo.exists():
    pdf.image(str(logo), x=14, y=7, w=40)
pdf.set_xy(120, 9); pdf.set_font("DV", "B", 12); pdf.set_text_color(*BEYAZ)
pdf.cell(76, 8, "OYUNCU LİSTESİ", align="R")

hepsi = [k[0] for k in reversed(KADRO)] + YEDEK  # tablo: kaleciden hücuma
KOL = [("İSİM", 33), ("MEVKİ", 19), ("KULÜP", 27), ("DOĞUM", 13),
       ("UYRUK", 19), ("BİLGİ", 49), ("VİDEO", 13), ("RAPOR", 13)]
y = 34
pdf.set_xy(7, y); pdf.set_font("DV", "B", 7.5); pdf.set_text_color(60, 70, 85)
for ad, w in KOL:
    pdf.cell(w, 7, ad, border="B")
pdf.ln(7)
for isim in hepsi:
    r = d.get(isim, {})
    url = f"https://womenfootballscouting.com/?paylas={quote(isim)}"
    satir = [
        (isim, "B", KOYU),
        ("/".join(r.get("mevki") or []), "", (70, 80, 95)),
        ((r.get("kulup") or "—")[:22], "", (70, 80, 95)),
        (dogum_yili(r), "", (70, 80, 95)),
        ((r.get("vatandaslik") or "—")[:16], "", (70, 80, 95)),
        (bilgi_cumlesi(r), "", (70, 80, 95)),
    ]
    pdf.set_x(7)
    yb = pdf.get_y()
    for (metin, stil, renk), (ad, w) in zip(satir, KOL):
        pdf.set_font("DV", stil, 7.6 if ad == "İSİM" else 7)
        pdf.set_text_color(*renk)
        metin = str(metin)
        while metin and pdf.get_string_width(metin) > w - 2.5:
            metin = metin[:-2].rstrip() + "…" if len(metin) > 3 else metin[:-1]
        pdf.cell(w, 11, metin, border="B")
    yt = VIDEO_OZEL.get(isim) or ("https://www.youtube.com/results?search_query="
          + quote(f"{isim} football highlights"))
    pdf.set_font("DV", "B", 7.4); pdf.set_text_color(200, 30, 30)
    pdf.cell(KOL[-2][1], 11, "Video →", border="B", link=yt)
    pdf.set_text_color(90, 140, 0)
    pdf.cell(KOL[-1][1], 11, "Rapor →", border="B", link=url, ln=1)

pdf.set_y(-38)
pdf.set_fill_color(*KOYU); pdf.rect(0, 297 - 30, 210, 30, "F")
pdf.set_xy(14, 297 - 24); pdf.set_font("DV", "B", 9.5); pdf.set_text_color(*LIME)
pdf.cell(0, 6, "'Video' → YouTube highlights · 'Rapor' → detaylı scout raporu (tıklanabilir)", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 8.5); pdf.set_text_color(*BEYAZ)
pdf.cell(0, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43 · womenfootballscouting.com", ln=1)

cikti = pathlib.Path.home() / "Desktop" / "ISM_Turkiye_Portfoyu_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size//1024} KB)")
