# -*- coding: utf-8 -*-
"""IDEAL Sports Management — BEŞİKTAŞ JK'ya özel TRANSFER SHORTLIST PDF'i (ÖN ALAN odaklı).

Kaleci ve savunma transferleri tamamlandığı için yalnız orta saha / kanat / forvet
adayları. Havuz house style (krem + ISM lime). Kapak → ORTA SAHA / HÜCUM sayfaları.

Kullanım: python portfoy_ism_besiktas.py  → Desktop\\ISM_Besiktas_Shortlist_2026.pdf
"""
import json, pathlib, sys, unicodedata, re
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)
LIME  = (181, 229, 0);   OLIV = (106, 140, 0);  KOYU = (11, 15, 20)

# (isim, mevki, grup, uyruk, "yaş (yıl)", boy_cm, ayak, kulüp/durum, not, video)
OYUNCULAR = [
 # ── ORTA SAHA ──
 ("Ernestina Abambila","DOS / MOS","OS","Gana","27 (1998)",168,"Çift","ETO FC Győr (Macaristan · Női NB I)",
  "Gana A Milli; 'Savaşçı' profil — top kazanan, iki yönlü orta saha; çift ayak; Macaristan üst liginde düzenli",
  "https://www.youtube.com/live/odSkSFVJAtI"),

 # ── HÜCUM (kanat + forvet) ──
 ("Moses Esther Chioma","KNT","FW","Nijerya","20 (2006)",165,"Çift","Edo Queens (Nijerya)",
  "Nijerya U20 (Falconets); hız + bitiricilik; NWFL 2023/24 + WAFU B şampiyonu",
  "https://youtu.be/-68PygF3owI"),
 ("Marilyn 'Lali' Esquivel","FW","FW","Arjantin","31 (1995)",0,"","Gimnasia y Esgrima La Plata (Arjantin 1. Lig · KAPTAN)",
  "Deneyimli forvet ve takım kaptanı; Olimpia (Paraguay) ile şampiyonluk (2023) + Copa Libertadores Femenina; Brasil Ladies Cup 2025'te Palmeiras'a gol",
  "https://youtu.be/XG5fMQDCx9c"),
 ("Nikola Rybanska","ST","FW","Slovakya","31 (1995)",0,"","OFI Kreta (Yunanistan)",
  "Slovakya Milli Takımı as forveti; golcü — hedef santrafor",
  "https://youtu.be/ACA2GLmZfSE"),
 ("Enzi Starks Broussard","KNT","FW","ABD","25 (2001)",170,"Sağ","Son kulüp: Dallas Trinity FC (USL Super League)",
  "ABD U17 Milli; 2x Yılın Ofansif Oyuncusu (US Development Academy)",
  "https://www.youtube.com/watch?v=DBkKjJxH1ik"),
 ("Chaymaa Mourtaji","ST / 2ST","FW","Fas","30 (1995)",164,"Sağ","Son kulüp: Sporting Club Casablanca (Fas 1. Lig)",
  "Fas A Milli (2022 Afrika Uluslar Kupası kadrosu); Fas 1. Ligi'nde 10+ yıl; SC Casablanca ile lig üçüncülüğü + Taç Kupası finali",
  "https://youtu.be/vGNyKuLJrYM"),
]

_scout = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
def _norm(s): return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower())).strip()
_site_isim = {_norm(k): k for k in _scout}

GRUPLAR = [("OS","ORTA SAHA","MIDFIELDERS"), ("FW","HÜCUM","FORWARDS")]

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
        pdf.set_xy(100, h/2 - 3); pdf.set_font("DV", "B", 10.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(100, 6, baslik, align="R")

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
pdf.cell(0, 11, "TRANSFER SHORTLIST", ln=1)
pdf.set_x(14); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*OLIV)
pdf.cell(0, 6, "BEŞİKTAŞ JK · KADIN FUTBOLU · YAZ 2026", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 9); pdf.set_text_color(*GRIM)
pdf.cell(0, 6, "Ön alan takviyesi — orta saha · kanat · forvet adayları", ln=1)

_say = {g: sum(1 for o in OYUNCULAR if o[2] == g) for g, _, _ in GRUPLAR}
_ulkeler = {p.strip() for o in OYUNCULAR for p in o[3].split("/") if p.strip()}
_ozet = [(str(len(OYUNCULAR)), "OYUNCU"), (str(len(_ulkeler)), "FARKLI ÜLKE"),
         (f"{_say['OS']}", "ORTA SAHA"), (f"{_say['FW']}", "HÜCUM")]
ox, oy = 14, 76; bw, bh = 29, 24
for i, (deger, et) in enumerate(_ozet):
    x = ox + i * (bw + 3.6)
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(x, oy, bw, bh, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(x, oy, bw, 1.6, "F")
    pdf.set_xy(x, oy + 5); pdf.set_text_color(*METIN); pdf.set_font("DV", "B", 15)
    pdf.cell(bw, 7, deger, align="C")
    pdf.set_xy(x, oy + 15); pdf.set_text_color(*GRIM); pdf.set_font("DV", "", 6.4)
    pdf.cell(bw, 4, et, align="C")

pdf.set_xy(14, 112); pdf.set_font("DV", "", 9.2); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(150, 5.4,
    "Bu dosya, Beşiktaş JK Kadın Futbol Takımı'nın Yaz 2026 planlamasına yönelik "
    "hazırlanmıştır. Kaleci ve savunma hattı takviyelerinin tamamlandığı bilgisiyle, "
    "yalnızca ÖN ALAN — orta saha, kanat ve forvet — bölgesindeki transfere açık "
    "adaylara odaklanılmıştır. Her oyuncu kartında güncel kulüp/durum, künye, öne "
    "çıkan özellikler ve tek tıkla izlenebilen highlight videosu yer alır. "
    "İlgilendiğiniz oyuncular için detaylı scout raporu, referans ve görüşme "
    "organizasyonu hızlıca sağlanır.")

imza_blogu(14, 246)

# ════════ BÖLGE SAYFALARI ════════
CW, CH = 182, 47
X0 = 14

def kart(o, y):
    isim, mevki, grup, uyruk, yas_str, boy, ayak, kulup, notu, video = o
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(X0, y, CW, CH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 2, CH, "F")
    pdf.set_xy(X0 + 7, y + 5); pdf.set_font("DV", "B", 12.5); pdf.set_text_color(*METIN)
    pdf.cell(120, 6, isim)
    pdf.set_font("DV", "B", 8)
    cw_ = pdf.get_string_width(mevki) + 8
    pdf.set_fill_color(*KOYU); pdf.rect(X0 + CW - 6 - cw_, y + 4.6, cw_, 7, "F")
    pdf.set_xy(X0 + CW - 6 - cw_, y + 5.1); pdf.set_text_color(*LIME)
    pdf.cell(cw_, 6, mevki, align="C")
    yas_gorunum = (yas_str.replace(" (", " yaş (", 1) if "(" in yas_str
                   else (f"{yas_str} yaş" if yas_str else ""))
    meta = "  ·  ".join(x2 for x2 in [
        yas_gorunum, uyruk, (f"{boy} cm" if boy else ""),
        (f"{ayak} ayak" if ayak else "")] if x2)
    pdf.set_xy(X0 + 7, y + 13); pdf.set_font("DV", "", 8.4); pdf.set_text_color(*GRIM)
    pdf.cell(CW - 14, 5, meta)
    pdf.set_font("DV", "B", 9)
    while pdf.get_string_width(kulup or "—") > CW - 16 and pdf.font_size_pt > 7:
        pdf.set_font_size(pdf.font_size_pt - 0.2)
    pdf.set_xy(X0 + 7, y + 19.5); pdf.set_text_color(*OLIV)
    pdf.cell(CW - 14, 5, kulup or "—")
    maddeler = [m.strip(" .") for m in re.split(r"[;]|\s·\s", notu) if m.strip()][:3]
    yy = y + 26.5
    pdf.set_font("DV", "", 8.2)
    for m in maddeler:
        pdf.set_xy(X0 + 7, yy); pdf.set_text_color(*OLIV)
        pdf.cell(4, 4.6, "•")
        pdf.set_text_color(60, 68, 82)
        pdf.cell(CW - 20, 4.6, m[:100])
        yy += 4.8
    bw_ = 42
    if video:
        pdf.set_fill_color(*LIME)
        pdf.rect(X0 + CW - 6 - bw_, y + CH - 10.5, bw_, 7, "F")
        pdf.set_xy(X0 + CW - 6 - bw_, y + CH - 10); pdf.set_font("DV", "B", 8)
        pdf.set_text_color(*KOYU)
        pdf.cell(bw_, 6, "▶  HIGHLIGHTS İZLE", align="C", link=video)
    site_key = _site_isim.get(_norm(isim))
    if site_key:
        pdf.set_xy(X0 + CW - 6 - bw_ - 46, y + CH - 10); pdf.set_font("DV", "B", 8)
        pdf.set_text_color(*OLIV)
        pdf.cell(42, 6, "★ Scout Raporu", align="R",
                 link=f"https://womenfootballscouting.com/?paylas={quote(site_key)}")

Y0, Y_MAX = 34, 278

def _grup_sayfa_ac(tr, en, adet):
    pdf.add_page(); zemin()
    marka_bandi(h=13, baslik="BEŞİKTAŞ JK SHORTLIST · YAZ 2026")
    pdf.set_fill_color(*LIME); pdf.rect(X0, 20, 3.2, 8, "F")
    pdf.set_xy(X0 + 7, 20.6); pdf.set_font("DV", "B", 15); pdf.set_text_color(*METIN)
    pdf.cell(90, 7, tr)
    pdf.set_font("DV", "", 9.5); pdf.set_text_color(*GRIM)
    pdf.cell(50, 7, "· " + en)
    pdf.set_xy(X0, 20.6); pdf.set_font("DV", "", 9); pdf.set_text_color(*GRIM)
    pdf.cell(CW, 7, f"{adet} oyuncu", align="R")

def _alt_bilgi(no):
    pdf.set_y(-16); pdf.set_font("DV", "", 7.6); pdf.set_text_color(*GRIM)
    pdf.set_x(X0)
    pdf.cell(CW / 2, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43")
    pdf.cell(CW / 2, 5, f"Sayfa {no}", align="R")

_sayfa_no = 1
for g, tr, en in GRUPLAR:
    grup_oyun = [o for o in OYUNCULAR if o[2] == g]
    if not grup_oyun:
        continue
    _sayfa_no += 1
    _grup_sayfa_ac(tr, en, len(grup_oyun))
    y = Y0
    for o in grup_oyun:
        if y + CH > Y_MAX:
            _alt_bilgi(_sayfa_no)
            _sayfa_no += 1
            _grup_sayfa_ac(tr + " · devam", en, len(grup_oyun))
            y = Y0
        kart(o, y)
        y += CH + 6
    _alt_bilgi(_sayfa_no)

cikti = pathlib.Path.home() / "Desktop" / "ISM_Besiktas_Shortlist_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu · {_sayfa_no} sayfa")
