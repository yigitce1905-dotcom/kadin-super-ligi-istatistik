# -*- coding: utf-8 -*-
"""IDEAL Sports Management — MEVCUT OYUNCU HAVUZU (aday katalogu) PDF'i.

Tasarım: AÇIK KREM zemin (sunum dosyası kriterleri) + ISM lime aksan.
Kurgu: Kapak (özet + içindekiler + imza) → her mevki bölgesi için AYRI sayfa,
tam genişlik zengin oyuncu kartları (künye + öne çıkanlar + video butonu).

Kadro güncelleme: OYUNCULAR listesini düzenle → python portfoy_ism_havuz.py
Çıktı: Desktop\\ISM_Oyuncu_Havuzu_2026.pdf
"""
import json, pathlib, sys, unicodedata, re
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

# ── Palet: krem bazlı + ISM kimliği ──
KREM  = (250, 248, 242)     # sayfa zemini
KART  = (255, 255, 255)     # kart zemini
KENAR = (228, 224, 214)     # kart kenarı
METIN = (26, 32, 44)        # ana metin (antrasit)
GRIM  = (122, 130, 142)     # ikincil metin
LIME  = (181, 229, 0)       # ISM lime (dolgu/rozet)
OLIV  = (106, 140, 0)       # lime'ın okunur koyusu (açık zeminde metin)
KOYU  = (11, 15, 20)        # marka bandı

# (isim, mevki, grup, uyruk, "yaş (doğum yılı)", boy_cm, ayak, kulüp, not, video)
OYUNCULAR = [
 # ── KALECİ ──
 ("Ashley Orkus","KL","KL","ABD","27 (1998)",180,"Sağ","Fram (İzlanda Top Division) — Eylül ortası itibarıyla serbest",
  "ABD U15–U18 milli; Profesyonel seviyede düzenli maç deneyimi (son: Tampa Bay Sun, USL S)",
  "https://www.youtube.com/watch?v=hnzyTjfz1zY"),
 ("Chloé Lachance-Soulard","KL","KL","Kanada","25 (2001)",170,"Sağ","Ottawa Rapids (NSL) — profesyonel lig bünyesinde",
  "Carleton Üniv. Takım MVP'si (2022); 2x OUA East All-Star (2022, 2025)",
  "https://www.youtube.com/watch?v=F0cRZCQpyg0"),
 ("Udoka Rachael Unachukwu","KL","KL","Nijerya","20 (2005)",172,"Çift","Nasarawa Amazons (Nijerya)",
  "WAFCON 2024 Şampiyonu (Super Falcons); 2024 Yılın Kalecisi ödülü; refleks + çift ayak dağıtım",
  "https://youtu.be/J6bnIZ7kLjg"),
 # ── DEFANS ──
 ("Angel Fowler","STP","DEF","İngiltere","24 (2002)",175,"Sağ","Carolina Ascent (USL W)",
  "2025 sezonu Yılın Oyuncusu; Brighton Akademi + AFC Wimbledon A Takım geçmişi",
  "https://www.youtube.com/watch?v=r6Kqyzsj9ls"),
 ("Emma Schneider","SĞB / KNT","DEF","Kanada / Trinidad-Tobago","24 (2002)",175,"Sağ","Son kulüp: Rio Tinto (Portekiz)",
  "Trinidad-Tobago A Milli; UMaine Yılın Defans Oyuncusu (2024) ve takım kaptanı",
  "https://youtu.be/pG7WMo1ZF8A"),
 ("Myla Schneider","STP / DOS","DEF","Kanada / Trinidad-Tobago","23 (2003)",165,"Sağ","Son kulüp: Rio Tinto (Portekiz)",
  "Trinidad-Tobago A Milli; 2x All-Conference First Team; Şampiyonluk MVP'si",
  "https://youtu.be/gY2iuPN8tuw"),
 ("Enez Mango","SLB","DEF","Kenya","33",0,"","Farul Constanța (Romanya)",
  "Takım kaptanı karakterinde, tecrübeli ve lider sol bek; 2025/26 sezon highlights",
  "https://youtu.be/WYqBwmWzl4I"),
 ("Pavlinka Nikolovska","STP / DOS","DEF","K. Makedonya","",0,"","ZFK Tiverija (K. Makedonya)",
  "K. Makedonya A Milli; fiziksel dominant modern stoper + lider; 1v1 + uzun pas + duran toplarda hava tehdidi",
  "https://www.youtube.com/watch?v=iykGGq4T9H8"),
 ("Anđela Savović","SLB / SLK","DEF","Karadağ","22 (2004)",0,"Sol","Serbest — hemen müsait",
  "Karadağ A/U19/U17 Milli; UEFA WCL eleme deneyimi; keskin savunma zamanlaması + kaliteli orta",
  "https://www.youtube.com/watch?v=niFwBfCuoH0"),
 ("Kolawole Racheal Opeyemi","STP","DEF","Nijerya","27 (1998)",182,"Sağ","RS Berkane (Fas)",
  "Nijerya Federasyon Kupası altın madalya (2020); güçlü hava topu + akıllı markaj; isabetli uzun paslarla oyun kurar",
  "https://www.youtube.com/watch?v=fk8n-1nzx1c"),
 ("Lucky Ugberhu","DEF","DEF","Nijerya","26 (2000)",166,"Sağ","Abia Angels (Nijerya)",
  "Nijerya Kadınlar Ligi şampiyonu (2018); hızlı ve güçlü; hava hakimiyeti, baskı altında etkili",
  "https://youtu.be/y9elVsexHkM"),
 ("Mache Tella Prisca","STP / DOS","DEF","Kamerun","19 (2007)",0,"Çift","Fossito Foot Académie (Kamerun)",
  "Kamerun A Milli (18 yaşında Nijerya'ya karşı debüt); U20 kilit oyuncu; robust stoper, hava hakimiyeti",
  "https://drive.google.com/drive/folders/1LDdPAna5acc9iombNo-thNSFdXJOWR7U?usp=drive_link"),
 # ── ORTA SAHA ──
 ("Chinatsu Kaio","OOS / KNT","OS","Japonya","23 (2003)",152,"Sağ","Adelaide University SC (Avustralya)",
  "Japonya U17 Milli; CUSA şampiyonu ve CUSA En İyi 11",
  "https://www.youtube.com/watch?v=eB2IV6ubMsY"),
 ("Joya-Maria Azzi","DOS / BEK","OS","Lübnan","25 (2000)",0,"Sağ","Central Methodist Eagles (ABD)",
  "Lübnan A Milli (Dünya Kupası + Olimpiyat elemeleri); WPSL All-Conference Best XI; çok yönlü, elit çalışkanlık",
  "https://youtu.be/LAioEruBNl0"),
 ("Aleksandra Markovska","DOS","OS","K. Makedonya","29 (1997)",0,"","ŽFK Ljuboten (K. Makedonya) — yeni sezon için serbest",
  "K. Makedonya Milli KAPTAN; zeki, zarif No.6 anchor; elit saha görüşü + UEFA WCL deneyimi",
  "https://www.youtube.com/watch?v=a8Q8PFDuIXE"),
 ("Ana Paula Villela","MOS / KNT","OS","Brezilya","29 (1997)",0,"","Serbest",
  "Deneyimli Brezilyalı; hem merkez hem kanatta; elit teknik + yaratıcı vizyon, keskin pas menzili",
  "https://www.youtube.com/watch?v=tfrMpFBe0cU"),
 # ── HÜCUM ──
 ("Enzi Starks Broussard","KNT","FW","ABD","25 (2001)",170,"Sağ","Son kulüp: Dallas Trinity FC (USL Super League)",
  "ABD U17 Milli; 2x Yılın Ofansif Oyuncusu (US Development Academy)",
  "https://www.youtube.com/watch?v=DBkKjJxH1ik"),
 ("Nikola Rybanska","ST","FW","Slovakya","31 (1995)",0,"","OFI Kreta (Yunanistan)",
  "Slovakya Milli Takımı as forveti; Golcü — Hedef Santrafor",
  "https://youtu.be/ACA2GLmZfSE"),
 ("Doosuur Anastasia Atume","ST","FW","Nijerya","20 (2005)",0,"Sağ","Edo Queens (Nijerya)",
  "2025/26 NWFL gol kraliçesi (11 gol, Altın Ayakkabı); güçlü fizik + hava; baskı altında golcü",
  "https://youtu.be/_IMZH6r7ecA"),
 ("Ljubica Bulum","ST / KNT","FW","Hırvatistan","21 (2004)",0,"Çift","ŽNK Donat-Zadar (Hırvatistan)",
  "Bu sezon 35 GOL — ligini domine etti; patlayıcı hızlanma + çift ayak bitiricilik; ceza sahası içgüdüsü",
  "https://www.youtube.com/watch?v=NO-Fsck0P2U"),
 ("Paola Blue Ellis","KNT / ST","FW","ABD / Haiti","27 (1999)",0,"Sol","Serbest — son: Finlandiya üst lig",
  "Haiti A Milli; elit hız, sol ayak; sol kanat/ileri çok yönlü, yüksek çalışkanlık",
  "https://www.youtube.com/watch?v=xXEOCJwz1fs"),
 ("Moses Esther Chioma","KNT","FW","Nijerya","20 (2006)",165,"Çift","Edo Queens (Nijerya)",
  "Nijerya U20 (Falconets); hız + bitiricilik; NWFL 2023/24 + WAFU B şampiyonu",
  "https://youtu.be/-68PygF3owI"),
 ("Essien Emem Peace","KNT / ST","FW","Nijerya","24 (2001)",170,"Çift","Kickstart FC (Hindistan)",
  "Super Falcons (A Milli); NWFL + WAFU B gol kralı (6 gol); U17/U20 geçmişi, çok yönlü hücum",
  ""),
]

# sitede rapor linki olanlar (varsa karta ★ Scout Raporu eklenir)
_scout = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
def _norm(s): return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower())).strip()
_site_isim = {_norm(k): k for k in _scout}

GRUPLAR = [("KL","KALECİLER","GOALKEEPERS"), ("DEF","DEFANS","DEFENDERS"),
           ("OS","ORTA SAHA","MIDFIELDERS"), ("FW","HÜCUM","FORWARDS")]

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
    """Üst koyu bant: beyaz logo + sağda sayfa başlığı."""
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
pdf.cell(0, 11, "OYUNCU HAVUZU", ln=1)
pdf.set_x(14); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*OLIV)
pdf.cell(0, 6, "MEVCUT ADAYLAR · KADIN FUTBOLU · YAZ 2026", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 9); pdf.set_text_color(*GRIM)
pdf.cell(0, 6, "Tamamı transfere açık, temsil ettiğimiz uluslararası oyuncular", ln=1)

# özet kutuları (beyaz kart + lime üst şerit)
_say = {g: sum(1 for o in OYUNCULAR if o[2] == g) for g, _, _ in GRUPLAR}
_ulkeler = {p.strip() for o in OYUNCULAR for p in o[3].split("/")}
_ozet = [(str(len(OYUNCULAR)), "OYUNCU"), (str(len(_ulkeler)), "FARKLI ÜLKE"),
         (f"{_say['KL']}", "KALECİ"), (f"{_say['DEF']}", "DEFANS"),
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

# tanıtım paragrafı
pdf.set_xy(14, 112); pdf.set_font("DV", "", 9.2); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(150, 5.4,
    "Bu dosyada, kulübünüzün kadro planlamasına doğrudan katkı sunabilecek "
    "uluslararası oyuncularımız mevki bölgelerine göre sunulmuştur. Her oyuncu "
    "kartında güncel kulüp, künye, öne çıkan başarılar ve tek tıkla izlenebilen "
    "highlight videosu yer alır. İlgilendiğiniz oyuncular için detaylı scout "
    "raporu, referans ve görüşme organizasyonu hızlıca sağlanır.")

# imza
imza_blogu(14, 246)

# ════════ BÖLGE SAYFALARI — her grup ayrı sayfa, tam genişlik kartlar ════════
CW, CH = 182, 47
X0 = 14

def kart(o, y):
    isim, mevki, grup, uyruk, yas_str, boy, ayak, kulup, notu, video = o
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(X0, y, CW, CH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 2, CH, "F")           # sol şerit
    # isim
    pdf.set_xy(X0 + 7, y + 5); pdf.set_font("DV", "B", 12.5); pdf.set_text_color(*METIN)
    pdf.cell(120, 6, isim)
    # mevki rozeti (koyu çip + lime yazı)
    pdf.set_font("DV", "B", 8)
    cw_ = pdf.get_string_width(mevki) + 8
    pdf.set_fill_color(*KOYU); pdf.rect(X0 + CW - 6 - cw_, y + 4.6, cw_, 7, "F")
    pdf.set_xy(X0 + CW - 6 - cw_, y + 5.1); pdf.set_text_color(*LIME)
    pdf.cell(cw_, 6, mevki, align="C")
    # meta satırı
    yas_gorunum = (yas_str.replace(" (", " yaş (", 1) if "(" in yas_str
                   else (f"{yas_str} yaş" if yas_str else ""))
    meta = "  ·  ".join(x2 for x2 in [
        yas_gorunum, uyruk, (f"{boy} cm" if boy else ""),
        (f"{ayak} ayak" if ayak else "")] if x2)
    pdf.set_xy(X0 + 7, y + 13); pdf.set_font("DV", "", 8.4); pdf.set_text_color(*GRIM)
    pdf.cell(CW - 14, 5, meta)
    # kulüp
    pdf.set_font("DV", "B", 9)
    while pdf.get_string_width(kulup or "—") > CW - 16 and pdf.font_size_pt > 7:
        pdf.set_font_size(pdf.font_size_pt - 0.2)
    pdf.set_xy(X0 + 7, y + 19.5); pdf.set_text_color(*OLIV)
    pdf.cell(CW - 14, 5, kulup or "—")
    # öne çıkanlar (nottan madde işaretli)
    maddeler = [m.strip(" .") for m in re.split(r"[;]|\s·\s", notu) if m.strip()][:3]
    yy = y + 26.5
    pdf.set_font("DV", "", 8.2)
    for m in maddeler:
        pdf.set_xy(X0 + 7, yy); pdf.set_text_color(*OLIV)
        pdf.cell(4, 4.6, "•")
        pdf.set_text_color(60, 68, 82)
        pdf.cell(CW - 20, 4.6, m[:100])
        yy += 4.8
    # video butonu (lime hap + koyu yazı) — sağ alt (video varsa)
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

Y0, Y_MAX = 34, 278          # ilk kart y'si · sayfa alt sınırı (footer üstü)

def _grup_sayfa_ac(tr, en, adet):
    pdf.add_page(); zemin()
    marka_bandi(h=13, baslik="OYUNCU HAVUZU · YAZ 2026")
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

_sayfa_no = 1                 # kapak = 1
for g, tr, en in GRUPLAR:
    grup_oyun = [o for o in OYUNCULAR if o[2] == g]
    if not grup_oyun:
        continue
    _sayfa_no += 1
    _grup_sayfa_ac(tr, en, len(grup_oyun))
    y = Y0
    for o in grup_oyun:
        if y + CH > Y_MAX:                 # sayfa doldu → yeni sayfa (grup devam)
            _alt_bilgi(_sayfa_no)
            _sayfa_no += 1
            _grup_sayfa_ac(tr + " · devam", en, len(grup_oyun))
            y = Y0
        kart(o, y)
        y += CH + 6
    _alt_bilgi(_sayfa_no)

cikti = pathlib.Path.home() / "Desktop" / "ISM_Oyuncu_Havuzu_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu · {_sayfa_no} sayfa")
