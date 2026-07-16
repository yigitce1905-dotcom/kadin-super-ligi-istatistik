# -*- coding: utf-8 -*-
"""IDEAL Sports Management — TRABZONSPOR'a özel transfer shortlist PDF'i.

Açık krem tema (havuz portföyüyle aynı dil): Kapak (TS ibaresi + imza) →
STOPER sayfası (Sampson, Hasanbegovic) → FORVET sayfası (Mourtaji, Rybanska).
Kartlarda künye + öne çıkanlar + video/maç/istatistik/rapor linkleri.

Kullanım:  python portfoy_ts_shortlist.py -> Desktop\\ISM_Trabzonspor_Shortlist_2026.pdf
"""
import pathlib, sys
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)
LIME  = (181, 229, 0);   OLIV = (106, 140, 0);  KOYU = (11, 15, 20)
BORDO = (122, 30, 58)

# (isim, mevki_rozet, uyruk, "yaş (yıl)", boy, ayak, kulüp_durumu,
#  profil_cümlesi, [öne çıkanlar], [(etiket, url, tur)])  tur: v=video k=kırmızı, d=diğer
OYUNCULAR = {
"STP": [
 ("Vyan Sampson", "STP / DOS", "Jamaika / İngiltere", "29 (1996)", "1.75", "Sağ",
  "BONSERVİSSİZ — son: INAC Kobe Leonessa (WE League, Japonya)",
  "Dünya Kupası deneyimli, hava hakimiyeti güçlü, pozisyon disiplini ve top "
  "dağıtımı iyi lider stoper; İngiltere, İtalya, İskoçya ve Japonya'da oynamış, "
  "her lige uyum sağlamış profesyonel profil.",
  ["Jamaika A Milli — 2023 FIFA Kadınlar Dünya Kupası kadrosu",
   "Arsenal Akademisi çıkışlı — WSL deneyimi (Arsenal, West Ham United)",
   "Eski İngiltere U17 & U19 milli oyuncusu",
   "Japonya WE League'de 3 sezon (JEF United Chiba, INAC Kobe Leonessa)"],
  [("▶  HIGHLIGHTS 25/26", "https://youtu.be/kT7nHmau_KE", "v"),
   ("SoccerDonna Profili", "https://www.soccerdonna.de/en/vyan-sampson/profil/spieler_14127.html", "d")]),

 ("Melisa Hasanbegović", "STP", "Bosna Hersek", "31 (1995)", "1.78", "Sağ",
  "Al-Ula FC (Suudi Arabistan 1. Lig)",
  "Fiziği güçlü, hava toplarında etkili sağ ayaklı stoper; savunma "
  "organizasyonu ve oyun kurma katkısıyla ceza sahasında iki yönde de "
  "varlık gösterir.",
  ["Suudi liginde düzenli ilk 11 — profesyonel lig temposu",
   "Gol katkısı olan stoper (duran top hedefi)",
   "WFS scout raporu mevcut — tek tıkla tam değerlendirme"],
  [("▶  HIGHLIGHTS", "https://youtu.be/PbqsUg-L_ms", "v"),
   ("Tam Maç 1", "https://www.youtube.com/live/5_3tqseQyGw", "d"),
   ("Tam Maç 2", "https://www.youtube.com/live/IbKGtdghomo", "d"),
   ("Maç (Shahid)", "https://shahid.mbc.net/ar/player/episodes/%D9%83%D8%A3%D8%B3-%D8%A7%D9%84%D8%A7%D8%AA%D8%AD%D8%A7%D8%AF-%D8%A7%D9%84%D8%B3%D8%B9%D9%88%D8%AF%D9%8A-%D9%84%D9%84%D8%B3%D9%8A%D8%AF%D8%A7%D8%AA-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-2026-%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-13/id-49923635035334", "d"),
   ("Video 2", "https://youtu.be/kINtwNGQFGU", "d"),
   ("İstatistik", "https://www.playmakerstats.com/player/melisa-hasanbegovic/329448", "d"),
   ("★ Scout Raporu", "https://womenfootballscouting.com/?paylas=" + quote("Melisa Hasanbegovic"), "s")]),
],
"FW": [
 ("Chaymaa Mourtaji", "ST / 2ST", "Fas", "30 (1995)", "1.64", "Sağ",
  "BONSERVİSSİZ — son: Sporting Club Casablanca (Fas 1. Lig)",
  "Rakip stopere agresif baskı yapan, önde top kazanan yorulmaz santrafor; "
  "keskin pozisyon alma ve doğal gol içgüdüsü, duran toplarda yetenekli.",
  ["Fas A Milli — 2022 Afrika Uluslar Kupası kadrosu",
   "Fas 1. Ligi'nde 10+ yıl: Difaa El Jadidi, SC Casablanca, AS FAR",
   "SC Casablanca ile lig üçüncülüğü, Taç Kupası finalisti",
   "Arapça, Fransızca ve İngilizce konuşuyor — hızlı adaptasyon"],
  [("▶  HIGHLIGHTS", "https://youtu.be/vGNyKuLJrYM", "v"),
   ("★ Scout Raporu", "https://womenfootballscouting.com/?paylas=" + quote("Chaymaa Mourtaji"), "s")]),

 ("Nikola Rybanska", "ST", "Slovakya", "31 (1995)", "", "",
  "OFI Girit (Yunanistan 1. Lig)",
  "Slovakya Milli Takımı'nın as forveti; ceza sahası içinde bitiriciliği "
  "güçlü, hedef adam olarak oynayabilen golcü santrafor.",
  ["Slovakya A Milli — as forvet",
   "Yunanistan 1. Ligi'nde düzenli golcü",
   "Hedef santrafor profili — direkt oyuna uygun"],
  [("▶  HIGHLIGHTS 25/26", "https://youtu.be/ACA2GLmZfSE", "v")]),
],
}
GRUPLAR = [("STP", "STOPER ADAYLARI", "CENTRE BACKS"),
           ("FW",  "FORVET ADAYLARI", "STRIKERS")]

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
pdf.cell(0, 11, "TRANSFER SHORTLIST", ln=1)
pdf.set_x(14); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*OLIV)
pdf.cell(0, 6, "STOPER + FORVET · KADIN FUTBOLU · YAZ 2026", ln=1)

# Trabzonspor şeridi
pdf.set_fill_color(*BORDO); pdf.rect(14, 66, 120, 10, "F")
pdf.set_xy(14, 67.6); pdf.set_font("DV", "B", 9.5); pdf.set_text_color(255, 255, 255)
pdf.cell(120, 7, "  TRABZONSPOR İÇİN HAZIRLANMIŞTIR", ln=1)

# özet kutuları
_say = {g: len(OYUNCULAR[g]) for g, _, _ in GRUPLAR}
_serbest = sum(1 for g in OYUNCULAR for o in OYUNCULAR[g] if "BONSERVİSSİZ" in o[6])
_ozet = [(str(sum(_say.values())), "ADAY"), (str(_say["STP"]), "STOPER"),
         (str(_say["FW"]), "FORVET"), (str(_serbest), "BONSERVİSSİZ")]
ox, oy = 14, 86; bw, bh = 29, 24
for i, (deger, et) in enumerate(_ozet):
    x = ox + i * (bw + 3.6)
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(x, oy, bw, bh, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(x, oy, bw, 1.6, "F")
    pdf.set_xy(x, oy + 5); pdf.set_text_color(*METIN); pdf.set_font("DV", "B", 15)
    pdf.cell(bw, 7, deger, align="C")
    pdf.set_xy(x, oy + 15); pdf.set_text_color(*GRIM); pdf.set_font("DV", "", 6.4)
    pdf.cell(bw, 4, et, align="C")

pdf.set_xy(14, 122); pdf.set_font("DV", "", 9.2); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(150, 5.4,
    "Bu dosya, Trabzonspor Kadın Futbol Takımı'nın stoper ve forvet "
    "ihtiyacına yönelik seçilmiş adayları içerir. Her oyuncu kartında künye, "
    "öne çıkan özellikler ve tek tıkla izlenebilen highlight/maç videoları yer "
    "alır. İlgilendiğiniz oyuncular için detaylı scout raporu, referans ve "
    "görüşme organizasyonu hızlıca sağlanır.")

imza_blogu(14, 246)

# ════════ MEVKİ SAYFALARI — tam genişlik zengin kartlar ════════
X0, CW = 14, 182
CH = 88

def kart(o, y):
    isim, mevki, uyruk, yas, boy, ayak, kulup, profil, maddeler, linkler = o
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(X0, y, CW, CH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 2, CH, "F")
    # isim + rozet
    pdf.set_xy(X0 + 7, y + 5.5); pdf.set_font("DV", "B", 14); pdf.set_text_color(*METIN)
    pdf.cell(120, 7, isim)
    pdf.set_font("DV", "B", 8.5)
    cw_ = pdf.get_string_width(mevki) + 9
    pdf.set_fill_color(*KOYU); pdf.rect(X0 + CW - 6 - cw_, y + 5, cw_, 7.4, "F")
    pdf.set_xy(X0 + CW - 6 - cw_, y + 5.6); pdf.set_text_color(*LIME)
    pdf.cell(cw_, 6.4, mevki, align="C")
    # meta
    meta = "  ·  ".join(x for x in [
        f"{yas} yaş" if "(" not in yas else yas.replace(" (", " yaş ("),
        uyruk, (f"{boy} m" if boy else ""), (f"{ayak} ayak" if ayak else "")] if x)
    pdf.set_xy(X0 + 7, y + 14.5); pdf.set_font("DV", "", 8.6); pdf.set_text_color(*GRIM)
    pdf.cell(CW - 14, 5, meta)
    # kulüp/durum
    pdf.set_font("DV", "B", 9.4)
    while pdf.get_string_width(kulup) > CW - 16 and pdf.font_size_pt > 7:
        pdf.set_font_size(pdf.font_size_pt - 0.2)
    pdf.set_xy(X0 + 7, y + 20.8); pdf.set_text_color(*OLIV)
    pdf.cell(CW - 14, 5, kulup)
    # profil cümlesi
    pdf.set_xy(X0 + 7, y + 27.5); pdf.set_font("DV", "", 8.4)
    pdf.set_text_color(60, 68, 82)
    pdf.multi_cell(CW - 14, 4.6, profil)
    # öne çıkanlar
    yy = pdf.get_y() + 2
    pdf.set_font("DV", "", 8.2)
    for m in maddeler:
        pdf.set_xy(X0 + 7, yy); pdf.set_text_color(*OLIV)
        pdf.cell(4, 4.6, "•")
        pdf.set_text_color(60, 68, 82)
        pdf.cell(CW - 20, 4.6, m[:105])
        yy += 4.9
    # link hapları — gerekirse iki satıra sarar (video lime, rapor çerçeveli, diğer gri)
    pdf.set_font("DV", "B", 7.4)
    genis = [pdf.get_string_width(e) + 7 for e, _, _ in linkler]
    satirlar, mevcut, gen = [[]], 0.0, CW - 12
    for i, w_ in enumerate(genis):
        if mevcut + w_ > gen and satirlar[-1]:
            satirlar.append([]); mevcut = 0.0
        satirlar[-1].append(i); mevcut += w_ + 3
    satirlar = satirlar[:2]
    for ri, sira in enumerate(reversed(satirlar)):        # alttan yukarı diz
        ly = y + CH - 10 - ri * 8
        lx = X0 + 7
        for i in sira:
            etiket, url, tur = linkler[i]; w_ = genis[i]
            if tur == "v":
                pdf.set_fill_color(*LIME); pdf.rect(lx, ly, w_, 6.6, "F")
                pdf.set_text_color(*KOYU)
            elif tur == "s":
                pdf.set_fill_color(255, 255, 255); pdf.set_draw_color(*OLIV)
                pdf.set_line_width(0.4); pdf.rect(lx, ly, w_, 6.6, "DF")
                pdf.set_text_color(*OLIV)
            else:
                pdf.set_fill_color(238, 236, 228); pdf.rect(lx, ly, w_, 6.6, "F")
                pdf.set_text_color(70, 78, 92)
            pdf.set_xy(lx, ly + 0.5)
            pdf.cell(w_, 5.6, etiket, align="C", link=url)
            lx += w_ + 3

for si, (g, tr, en) in enumerate(GRUPLAR):
    pdf.add_page(); zemin()
    marka_bandi(h=13, baslik="TRABZONSPOR SHORTLIST · YAZ 2026")
    pdf.set_fill_color(*LIME); pdf.rect(X0, 20, 3.2, 8, "F")
    pdf.set_xy(X0 + 7, 20.6); pdf.set_font("DV", "B", 15); pdf.set_text_color(*METIN)
    pdf.cell(95, 7, tr)
    pdf.set_font("DV", "", 9.5); pdf.set_text_color(*GRIM)
    pdf.cell(45, 7, "· " + en)
    y = 34
    for o in OYUNCULAR[g]:
        kart(o, y)
        y += CH + 7
    pdf.set_y(-16); pdf.set_font("DV", "", 7.6); pdf.set_text_color(*GRIM)
    pdf.set_x(X0)
    pdf.cell(CW / 2, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43")
    pdf.cell(CW / 2, 5, f"{si + 2} / {len(GRUPLAR) + 1}", align="R")

cikti = pathlib.Path.home() / "Desktop" / "ISM_Trabzonspor_Shortlist_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB)")
