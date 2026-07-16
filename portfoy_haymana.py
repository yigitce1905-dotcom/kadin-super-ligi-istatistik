# -*- coding: utf-8 -*-
"""IDEAL Sports Management — HAYMANA transfer dosyası PDF'i.

Krem tema (shortlist şablonu): Kapak + KALECİLER sayfası (Akarekor, Baah)
+ ORTA SAHA & FORVET sayfası (Kisisa, Samuel). Övgüler video/SD verisine dayalı.

Kullanım:  python portfoy_haymana.py -> Desktop\\ISM_Haymana_Transfer_Dosyasi_2026.pdf
"""
import pathlib, sys

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)
LIME  = (181, 229, 0);   OLIV = (106, 140, 0);  KOYU = (11, 15, 20)

# (isim, rozet, uyruk, "yaş (yıl)", boy, ayak, kulüp, profil, [maddeler], [(etiket,url,tur)])
OYUNCULAR = {
"KL": [
 ("Rita Akarekor", "KL", "Nijerya", "25 (2001)", "1.72", "",
  "Yanga Princess SC (Tanzanya WPL)",
  "Çizgi üzerinde refleksleri güçlü, atletik ve cesur bir kaleci; ceza sahası "
  "hakimiyeti ve degajlarındaki isabetle savunmasına güven veren bir profil.",
  ["Nijerya'nın köklü kulübü Sunshine Queens'ten Tanzanya'nın devi Yanga Princess'e uzanan kariyer",
   "2025/26 Tanzanya Kadınlar Premier Ligi'nde düzenli ilk 11",
   "Tam maç kaydı mevcut — 90 dakikalık performansı izlenebilir"],
  [("▶  HIGHLIGHTS", "https://youtu.be/S8coT1U-pnA", "v"),
   ("Video 2", "https://youtu.be/4PbCPtom9vs", "d"),
   ("Tam Maç (Yanga - JKT Queens)", "https://youtu.be/utCe3iB6euQ", "d")]),

 ("Rose Teye Baah", "KL", "Gana", "", "", "",
  "Gana Kadınlar Ligi",
  "Taraftarların 'The Wall' (Duvar) lakabını taktığı Ganalı eldiven; üst üste "
  "yaptığı inanılmaz kurtarışların yanında ayakla oyun kurma becerisiyle de "
  "öne çıkan modern bir kaleci.",
  ["'The Wall' — kurtarış serileriyle tanınan refleks kalecisi",
   "Ayak becerisi güçlü: kısa oyun kurulumuna uygun (kurtarış + pas videosu mevcut)",
   "Batı Afrika kaleci ekolünün fiziksel ve çevik temsilcisi"],
  [("▶  HIGHLIGHTS", "https://youtu.be/XCaYX_CKu78", "v"),
   ("Video 2", "https://youtu.be/HhtqU6hRtvM", "d")]),
],
"OSFW": [
 ("Irene Kisisa", "OS", "Tanzanya", "", "", "",
  "Yanga Princess SC (Tanzanya WPL)",
  "Tanzanya liginin zirvesindeki Yanga Princess'in orta sahasında oynayan, "
  "iki yönde de katkı veren enerjik bir merkez orta saha; top taşıma ve "
  "pres gücüyle oyunun temposunu belirler.",
  ["Tanzanya WPL'nin en büyük kulüplerinden Yanga Princess bünyesinde",
   "Box-to-box profil — savunma katkısı + ileri koşular",
   "Doğu Afrika futbolunun yükselen orta saha profillerinden"],
  [("▶  VIDEO (Instagram)", "https://www.instagram.com/p/DagPHXgxCRe/", "v")]),

 ("Oluwayemisi Samuel", "ST", "Nijerya", "21 (2004)", "", "",
  "TP Mazembe (Kongo DC) — CAF Şampiyonlar Ligi şampiyonu kulüp",
  "Henüz 21 yaşında Afrika'nın en güçlü kadın futbolu yapılarından TP Mazembe "
  "formasını giyen Nijeryalı golcü; hızı, bitiriciliği ve ceza sahasındaki "
  "açlığıyla yaşının çok üzerinde bir olgunluk sergiliyor.",
  ["21 yaşında kıta devinde forma — yüksek potansiyel, yükselen değer",
   "Afrika şampiyonu TP Mazembe altyapısından geçen hücum disiplini",
   "Nijerya forvet ekolü: hız + güç + gol içgüdüsü"],
  [("▶  HIGHLIGHTS", "https://youtu.be/3Oqc8a1nNqk", "v"),
   ("Video 2", "https://youtu.be/ggEJaZ5pSDc", "d")]),
],
}
SAYFALAR = [("KL",   "KALECİLER", "GOALKEEPERS"),
            ("OSFW", "ORTA SAHA & FORVET", "MIDFIELD & ATTACK")]
ROZET_GRUP = {"KL": [("KL", "KALECİLER", "GOALKEEPERS")]}

from fpdf import FPDF
_f = KOK / "fonts"
pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(False)
pdf.add_font("DV", "", str(_f / "DejaVuSans.ttf"))
pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
pdf.add_font("IMZA", "", r"C:\Windows\Fonts\segoesc.ttf")
logo = KOK / "static" / "ism_logo_beyaz.png"

def zemin():
    pdf.set_fill_color(*KREM); pdf.rect(0, 0, 210, 297, "F")

def marka_bandi(h=13, baslik=""):
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, h, "F")
    if logo.exists(): pdf.image(str(logo), x=10, y=h/2 - 3.2, w=32)
    if baslik:
        pdf.set_xy(90, h/2 - 3); pdf.set_font("DV", "B", 10.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(110, 6, baslik, align="R")

def imza_blogu(x, y):
    pdf.set_xy(x, y); pdf.set_font("IMZA", "", 17); pdf.set_text_color(*METIN)
    pdf.cell(80, 9, "Yiğit Çelebi", ln=1)
    pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.line(x + 1, y + 11, x + 62, y + 11)
    pdf.set_xy(x + 1, y + 12); pdf.set_font("DV", "B", 8.5); pdf.set_text_color(*METIN)
    pdf.cell(90, 5, "Yiğit Çelebi · IDEAL Sports Management", ln=1)
    pdf.set_x(x + 1); pdf.set_font("DV", "", 7.8); pdf.set_text_color(*GRIM)
    pdf.cell(90, 4.5, "+90 506 578 46 43 · womenfootballscouting.com", ln=1)

# ════════ KAPAK ════════
pdf.add_page(); zemin()
marka_bandi(h=34)
pdf.set_xy(14, 46); pdf.set_font("DV", "B", 25); pdf.set_text_color(*METIN)
pdf.cell(0, 11, "TRANSFER DOSYASI", ln=1)
pdf.set_x(14); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*OLIV)
pdf.cell(0, 6, "KALECİ + ORTA SAHA + FORVET · KADIN FUTBOLU · YAZ 2026", ln=1)

_toplam = sum(len(v) for v in OYUNCULAR.values())
_ozet = [(str(_toplam), "ADAY"), ("2", "KALECİ"), ("1", "ORTA SAHA"), ("1", "FORVET")]
ox, oy = 14, 72; bw, bh = 29, 24
for i, (deger, et) in enumerate(_ozet):
    x = ox + i * (bw + 3.6)
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(x, oy, bw, bh, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(x, oy, bw, 1.6, "F")
    pdf.set_xy(x, oy + 5); pdf.set_text_color(*METIN); pdf.set_font("DV", "B", 15)
    pdf.cell(bw, 7, deger, align="C")
    pdf.set_xy(x, oy + 15); pdf.set_text_color(*GRIM); pdf.set_font("DV", "", 6.4)
    pdf.cell(bw, 4, et, align="C")

pdf.set_xy(14, 108); pdf.set_font("DV", "", 9.2); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(150, 5.4,
    "Bu dosya, Haymana Kadın Futbol Takımı'nın kadro planlamasına yönelik "
    "seçilmiş adayları içerir. Her oyuncu kartında künye, öne çıkan özellikler "
    "ve tek tıkla izlenebilen highlight/maç videoları yer alır. İlgilendiğiniz "
    "oyuncular için detaylı bilgi, referans ve görüşme organizasyonu hızlıca "
    "sağlanır.")

imza_blogu(14, 246)

# ════════ İÇERİK SAYFALARI ════════
X0, CW = 14, 182
CH = 88
GRUP_AD = {"KL": ("KALECİLER", "GOALKEEPERS"), "OS": ("ORTA SAHA", "MIDFIELD"),
           "ST": ("FORVET", "ATTACK")}

def kart(o, y):
    isim, mevki, uyruk, yas, boy, ayak, kulup, profil, maddeler, linkler = o
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(X0, y, CW, CH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 2, CH, "F")
    pdf.set_xy(X0 + 7, y + 5.5); pdf.set_font("DV", "B", 14); pdf.set_text_color(*METIN)
    pdf.cell(120, 7, isim)
    pdf.set_font("DV", "B", 8.5)
    cw_ = pdf.get_string_width(mevki) + 9
    pdf.set_fill_color(*KOYU); pdf.rect(X0 + CW - 6 - cw_, y + 5, cw_, 7.4, "F")
    pdf.set_xy(X0 + CW - 6 - cw_, y + 5.6); pdf.set_text_color(*LIME)
    pdf.cell(cw_, 6.4, mevki, align="C")
    meta = "  ·  ".join(x for x in [
        (yas.replace(" (", " yaş (") if "(" in yas else (f"{yas} yaş" if yas else "")),
        uyruk, (f"{boy} m" if boy else ""), (f"{ayak} ayak" if ayak else "")] if x)
    pdf.set_xy(X0 + 7, y + 14.5); pdf.set_font("DV", "", 8.6); pdf.set_text_color(*GRIM)
    pdf.cell(CW - 14, 5, meta)
    pdf.set_font("DV", "B", 9.4)
    while pdf.get_string_width(kulup) > CW - 16 and pdf.font_size_pt > 7:
        pdf.set_font_size(pdf.font_size_pt - 0.2)
    pdf.set_xy(X0 + 7, y + 20.8); pdf.set_text_color(*OLIV)
    pdf.cell(CW - 14, 5, kulup)
    pdf.set_xy(X0 + 7, y + 27.5); pdf.set_font("DV", "", 8.4)
    pdf.set_text_color(60, 68, 82)
    pdf.multi_cell(CW - 14, 4.6, profil)
    yy = pdf.get_y() + 2
    pdf.set_font("DV", "", 8.2)
    for m in maddeler:
        pdf.set_xy(X0 + 7, yy); pdf.set_text_color(*OLIV)
        pdf.cell(4, 4.6, "•")
        pdf.set_text_color(60, 68, 82)
        pdf.cell(CW - 20, 4.6, m[:105])
        yy += 4.9
    # link hapları (tek satır yeter — en fazla 3 link var)
    lx = X0 + 7; ly = y + CH - 10
    pdf.set_font("DV", "B", 7.4)
    for etiket, url, tur in linkler:
        w_ = pdf.get_string_width(etiket) + 7
        if lx + w_ > X0 + CW - 5:
            break
        if tur == "v":
            pdf.set_fill_color(*LIME); pdf.rect(lx, ly, w_, 6.6, "F")
            pdf.set_text_color(*KOYU)
        else:
            pdf.set_fill_color(238, 236, 228); pdf.rect(lx, ly, w_, 6.6, "F")
            pdf.set_text_color(70, 78, 92)
        pdf.set_xy(lx, ly + 0.5)
        pdf.cell(w_, 5.6, etiket, align="C", link=url)
        lx += w_ + 3

def grup_basligi(tr, en, y):
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 3.2, 8, "F")
    pdf.set_xy(X0 + 7, y + 0.6); pdf.set_font("DV", "B", 15); pdf.set_text_color(*METIN)
    pdf.cell(95, 7, tr)
    pdf.set_font("DV", "", 9.5); pdf.set_text_color(*GRIM)
    pdf.cell(60, 7, "· " + en)

# Sayfa 2 — Kaleciler
pdf.add_page(); zemin()
marka_bandi(h=13, baslik="TRANSFER DOSYASI · YAZ 2026")
grup_basligi("KALECİLER", "GOALKEEPERS", 20)
y = 34
for o in OYUNCULAR["KL"]:
    kart(o, y); y += CH + 7
pdf.set_y(-16); pdf.set_font("DV", "", 7.6); pdf.set_text_color(*GRIM)
pdf.set_x(X0)
pdf.cell(CW / 2, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43")
pdf.cell(CW / 2, 5, "2 / 3", align="R")

# Sayfa 3 — Orta Saha + Forvet (iki grup tek sayfada)
pdf.add_page(); zemin()
marka_bandi(h=13, baslik="TRANSFER DOSYASI · YAZ 2026")
grup_basligi("ORTA SAHA", "MIDFIELD", 20)
kart(OYUNCULAR["OSFW"][0], 34)
grup_basligi("FORVET", "ATTACK", 34 + CH + 9)
kart(OYUNCULAR["OSFW"][1], 34 + CH + 9 + 14)
pdf.set_y(-16); pdf.set_font("DV", "", 7.6); pdf.set_text_color(*GRIM)
pdf.set_x(X0)
pdf.cell(CW / 2, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43")
pdf.cell(CW / 2, 5, "3 / 3", align="R")

cikti = pathlib.Path.home() / "Desktop" / "ISM_Haymana_Transfer_Dosyasi_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB)")
