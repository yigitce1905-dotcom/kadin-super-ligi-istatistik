# -*- coding: utf-8 -*-
"""IDEAL Sports Management — SEG FlowSports tanışma takip dosyası (TEK SAYFA, İNGİLİZCE).

ÖNEMLİ ÇERÇEVE: Bu bir temsil portföyü DEĞİL — "diaspora scouting watchlist".
Oyuncular ISM tarafından temsil edilmiyor; kapsama örneği / pazar istihbaratı
olarak sunuluyor (dürüst konumlandırma, ajans-ajans güven için kritik).

Kullanım:  python portfoy_ism_seg_watchlist.py
Çıktı:     Desktop\\ISM_SEG_Diaspora_Watchlist.pdf
"""
import pathlib, sys

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

# ── ISM marka kimliği (krem sunum teması) ──
KREM  = (250, 248, 242)
KART  = (255, 255, 255)
KENAR = (228, 224, 214)
METIN = (26, 32, 44)
GRIM  = (122, 130, 142)
LIME  = (181, 229, 0)
OLIV  = (106, 140, 0)
KOYU  = (11, 15, 20)

# (isim, kulüp+ülke, mevki, doğum yılı, boy, ayak, tek satır İngilizce not)
OYUNCULAR = [
    ("Sude N'Gozi Öztaş", "Chelsea FC (ENG)", "CF / LW", "2008", "1.68", "R",
     "Academy striker; strong hold-up play, elite box positioning. Türkiye U19 international."),
    ("Sana Coşkun", "Bayer 04 Leverkusen (GER)", "DM / CM", "2008", "1.73", "R",
     "Modern No. 6 — duel-winning, tactically disciplined, European physical standards."),
    ("İsra Sıla Gümüştekin", "Excelsior Rotterdam (NED)", "CB / DM", "2009", "1.72", "R",
     "Dutch-school centre-back; back-line control and build-up passing quality."),
    ("Elif Berra Cambaz", "Bayer 04 Leverkusen (GER)", "CB", "2009", "1.71", "R",
     "Sharp, intelligent young centre-back; excellent lateral positional awareness."),
    ("Selen Su Yarayan", "FC Basel 1893 (SUI)", "RB / RWB", "2008", "1.61", "R",
     "Elite game-reading full-back; accurate progressive passing to launch attacks."),
    ("Ceylin Yılmaz", "Montpellier HSC (FRA)", "GK", "2007", "1.76", "L",
     "French-academy goalkeeper; exceptional reflexes, commands the box. Left-footed."),
]

from fpdf import FPDF
_f = KOK / "fonts"
pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(False)
pdf.add_font("DV", "", str(_f / "DejaVuSans.ttf"))
pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
pdf.add_font("IMZA", "", r"C:\Windows\Fonts\segoesc.ttf")
logo = KOK / "static" / "ism_logo_beyaz.png"

pdf.add_page()
pdf.set_fill_color(*KREM); pdf.rect(0, 0, 210, 297, "F")

# ── Marka bandı ──
pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, 20, "F")
if logo.exists():
    pdf.image(str(logo), x=12, y=6.2, w=34)
pdf.set_xy(100, 7); pdf.set_font("DV", "B", 10)
pdf.set_text_color(255, 255, 255)
pdf.cell(98, 6, "TURKISH DIASPORA WATCHLIST", align="R")

# ── Başlık + konumlandırma ──
X0, CW = 14, 182
pdf.set_xy(X0, 27); pdf.set_font("DV", "B", 17); pdf.set_text_color(*METIN)
pdf.cell(0, 8, "Turkish Diaspora — Youth Scouting Overview", ln=1)
pdf.set_x(X0); pdf.set_font("DV", "B", 9); pdf.set_text_color(*OLIV)
pdf.cell(0, 5.5, "PREPARED FOR SEG FLOWSPORTS · SUMMER 2026", ln=1)
pdf.set_xy(X0, 42); pdf.set_font("DV", "", 8.6); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(CW, 4.6,
    "IDEAL Sports Management (Istanbul) recently placed Türkiye international Göknur "
    "Güleryüz in the French league; on the men's side our group brokered Leandro "
    "Trossard's move to Beşiktaş. We operate womenfootballscouting.com — a scouting "
    "platform covering 1,400+ players with complete data on the Turkish Women's Super League.")

# ── Dürüstlük kutusu: temsil DEĞİL, izleme ──
ny = 58
pdf.set_fill_color(255, 251, 235); pdf.set_draw_color(217, 180, 90); pdf.set_line_width(0.35)
pdf.rect(X0, ny, CW, 11, "DF")
pdf.set_xy(X0 + 4, ny + 2.1); pdf.set_font("DV", "B", 8.2); pdf.set_text_color(120, 90, 20)
pdf.multi_cell(CW - 8, 3.6,
    "NOTE — These players are NOT under ISM representation. They are examples of our "
    "diaspora scouting coverage, shared as market intelligence for a possible collaboration.")

# ── Oyuncu satırları ──
y = ny + 16
RH = 21.5
for isim, kulup, poz, dogum, boy, ayak, notu in OYUNCULAR:
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(X0, y, CW, RH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 2, RH, "F")
    # isim + kulüp
    pdf.set_xy(X0 + 6, y + 3); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*METIN)
    pdf.cell(96, 5, isim)
    pdf.set_xy(X0 + 6, y + 9); pdf.set_font("DV", "B", 8); pdf.set_text_color(*OLIV)
    pdf.cell(96, 4, kulup)
    # künye çipleri (sağ blok)
    pdf.set_font("DV", "", 7.6); pdf.set_text_color(*GRIM)
    pdf.set_xy(X0 + 104, y + 3.4)
    pdf.cell(CW - 110, 4,
             f"{poz}   ·   b. {dogum}   ·   {boy} m   ·   {ayak}", align="R")
    # not
    pdf.set_xy(X0 + 6, y + 14); pdf.set_font("DV", "", 7.9); pdf.set_text_color(60, 68, 82)
    pdf.cell(CW - 12, 4, notu)
    y += RH + 3.2

# ── İşbirliği önerisi ──
y += 2
pdf.set_fill_color(*LIME); pdf.rect(X0, y, 3.2, 6.5, "F")
pdf.set_xy(X0 + 6, y + 0.5); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*METIN)
pdf.cell(0, 6, "Where we can work together", ln=1)
pdf.set_font("DV", "", 8.4); pdf.set_text_color(60, 68, 82)
for m in [
    "Turkish market access — direct relationships with the clubs signing foreign players every window.",
    "Diaspora radar — youth internationals across ENG / GER / NED / SUI / FRA, tracked before the wider market.",
    "Co-representation for players moving between Türkiye and your core markets.",
]:
    pdf.set_x(X0 + 6); pdf.set_text_color(*OLIV)
    pdf.cell(4, 4.8, "•")
    pdf.set_text_color(60, 68, 82)
    pdf.cell(CW - 14, 4.8, m, ln=1)

# ── İmza ──
sy = 262
pdf.set_xy(X0, sy); pdf.set_font("IMZA", "", 16); pdf.set_text_color(*METIN)
pdf.cell(80, 8, "Yiğit Çelebi", ln=1)
pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
pdf.line(X0 + 1, sy + 10, X0 + 62, sy + 10)
pdf.set_xy(X0 + 1, sy + 11); pdf.set_font("DV", "B", 8.4); pdf.set_text_color(*METIN)
pdf.cell(90, 4.6, "Yiğit Çelebi · IDEAL Sports Management", ln=1)
pdf.set_x(X0 + 1); pdf.set_font("DV", "", 7.8); pdf.set_text_color(*GRIM)
pdf.cell(90, 4.2, "+90 506 578 46 43 · womenfootballscouting.com", ln=1)

cikti = pathlib.Path.home() / "Desktop" / "ISM_SEG_Diaspora_Watchlist.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu · 1 sayfa")
