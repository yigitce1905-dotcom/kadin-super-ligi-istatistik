# -*- coding: utf-8 -*-
"""IDEAL Sports Management — MEVCUT OYUNCU HAVUZU (başvuru/aday katalogu) PDF'i.

Türkiye Portföyü'nden farkı: bunlar ajansa gelen/önerilen, uluslararası
adaylar. Diziliş yerine mevki-grupları kart ızgarası; her oyuncuda direkt
highlight video linki (+ sitede olan varsa scout raporu linki).

Kadro güncelleme: OYUNCULAR listesini düzenle → python portfoy_ism_havuz.py
Çıktı: Desktop\\ISM_Oyuncu_Havuzu_2026.pdf
"""
import json, pathlib, sys, unicodedata, re
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

# ── Marka ──
LIME  = (181, 229, 0); KOYU = (11, 15, 20); PANEL = (18, 22, 34)
BEYAZ = (240, 244, 252); GRI = (120, 133, 151); CIZGI = (38, 44, 69)
KIRMIZI = (220, 60, 60); YESIL = (90, 150, 20)

# (isim, mevki, grup, uyruk, "yaş (doğum yılı)", boy_cm, ayak, kulüp, not, video)
OYUNCULAR = [
 # ── KALECİ ──
 ("Ashley Orkus","KL","KL","ABD","27 (1998)",180,"Sağ","Fram (İzlanda Top Division) — Eylül ortası itibarıyla serbest",
  "ABD U15–U18 milli; profesyonel seviyede düzenli maç deneyimi (son: Tampa Bay Sun, USL S)",
  "https://www.youtube.com/watch?v=hnzyTjfz1zY"),
 ("Chloé Lachance-Soulard","KL","KL","Kanada","25 (2001)",170,"Sağ","Ottawa Rapids (NSL) — profesyonel lig bünyesinde",
  "Carleton Üniv. Takım MVP'si (2022); 2x OUA East All-Star (2022, 2025)",
  "https://www.youtube.com/watch?v=F0cRZCQpyg0"),
 ("Sydney Bellamy","KL","KL","ABD / Jamaika","23 (2003)",175,"Sağ","Son kulüp: Nhrhides Fthias (Yunanistan)",
  "Jamaika A Milli (2 maç); 2x Yılın Kalecisi + 2x First Team All-Conference (2023, 2024)",
  "https://www.youtube.com/watch?v=CAY0ngFXzAE"),
 # ── DEFANS ──
 ("Angel Fowler","STP","DEF","İngiltere","24 (2002)",175,"Sağ","Carolina Ascent (USL W)",
  "2025 sezonu Yılın Oyuncusu; Brighton Akademi + AFC Wimbledon A Takım geçmişi",
  "https://www.youtube.com/watch?v=r6Kqyzsj9ls"),
 ("Emma Schneider","SĞB / KNT","DEF","Kanada / Trinidad-Tobago","24 (2002)",175,"Sağ","Son kulüp: Rio Tinto (Portekiz)",
  "Trinidad-Tobago A Milli; UMaine Yılın Defans Oyuncusu (2024) ve takım kaptanı",
  "https://youtu.be/pG7WMo1ZF8A"),
 ("Myla Schneider","STP / DOS","DEF","Kanada / Trinidad-Tobago","23 (2003)",165,"Sağ","Son kulüp: Rio Tinto (Portekiz)",
  "Trinidad-Tobago A Milli; 2x All-Conference First Team, şampiyonluk MVP'si",
  "https://youtu.be/gY2iuPN8tuw"),
 ("Enez Mango","SLB","DEF","Kenya","33",0,"","Farul Constanța (Romanya)",
  "Takım kaptanı karakterinde, tecrübeli ve lider sol bek — 2025/26 sezon highlights",
  "https://youtu.be/WYqBwmWzl4I"),
 # ── ORTA SAHA ──
 ("Chinatsu Kaio","OOS / KNT","OS","Japonya","23 (2003)",152,"Sağ","Adelaide University SC (Avustralya)",
  "Japonya U17 Milli; CUSA şampiyonu ve CUSA En İyi 11",
  "https://www.youtube.com/watch?v=eB2IV6ubMsY"),
 # ── HÜCUM ──
 ("Enzi Starks Broussard","KNT","FW","ABD","25 (2001)",170,"Sağ","Son kulüp: Dallas Trinity FC (USL Super League)",
  "ABD U17 Milli; 2x Yılın Ofansif Oyuncusu (US Development Academy)",
  "https://www.youtube.com/watch?v=DBkKjJxH1ik"),
 ("Nikola Rybanska","ST","FW","Slovakya","31 (1995)",0,"","OFI Kreta (Yunanistan)",
  "Slovakya Milli Takımı as forveti · Golcü — Hedef Santrafor",
  "https://youtu.be/ACA2GLmZfSE"),
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
logo = KOK / "static" / "ism_logo_beyaz.png"

def zemin():
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, 297, "F")

# ════════ KAPAK ════════
pdf.add_page(); zemin()
if logo.exists(): pdf.image(str(logo), x=14, y=16, w=60)
pdf.set_xy(14, 34); pdf.set_font("DV", "B", 24); pdf.set_text_color(*BEYAZ)
pdf.cell(0, 11, "OYUNCU HAVUZU", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 11); pdf.set_text_color(*LIME)
pdf.cell(0, 6, "MEVCUT ADAYLAR · KADIN FUTBOLU · YAZ 2026", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 8.5); pdf.set_text_color(*GRI)
pdf.cell(0, 5, "Tamamı transfere açık, temsil ettiğimiz uluslararası oyuncular", ln=1)

# özet kutuları
_say = {g: sum(1 for o in OYUNCULAR if o[2] == g) for g, _, _ in GRUPLAR}
_ulkeler = {p.strip() for o in OYUNCULAR for p in o[3].split("/")}
_ozet = [(str(len(OYUNCULAR)), "OYUNCU"), (str(len(_ulkeler)), "FARKLI ÜLKE"),
         (f"{_say['KL']}", "KALECİ"), (f"{_say['DEF']}", "DEFANS"),
         (f"{_say['OS']}", "ORTA SAHA"), (f"{_say['FW']}", "HÜCUM")]
ox, oy = 14, 62; bw = 30
for i, (deger, et) in enumerate(_ozet):
    x = ox + (i % 3) * (bw + 4); y = oy + (i // 3) * 26
    pdf.set_fill_color(*PANEL); pdf.set_draw_color(*CIZGI)
    pdf.rect(x, y, bw, 22, "DF")
    pdf.set_xy(x, y + 3); pdf.set_text_color(*LIME); pdf.set_font("DV", "B", 15)
    pdf.cell(bw, 7, deger, align="C")
    pdf.set_xy(x, y + 13); pdf.set_text_color(*GRI); pdf.set_font("DV", "", 6.5)
    pdf.cell(bw, 4, et, align="C")

pdf.set_xy(14, 122); pdf.set_font("DV", "", 8.5); pdf.set_text_color(200, 208, 220)
pdf.multi_cell(126, 5,
    "Her oyuncunun kartında güncel kulübü, künyesi ve DOĞRUDAN highlight video "
    "linki yer alır. İlgilendiğiniz oyuncular için detaylı görüşme ve scout "
    "raporu talep edebilirsiniz.")

pdf.set_xy(14, 268); pdf.set_font("DV", "B", 10); pdf.set_text_color(*BEYAZ)
pdf.cell(0, 6, "Yiğit Çelebi · IDEAL Sports Management", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 8.5); pdf.set_text_color(*GRI)
pdf.cell(0, 5, "+90 506 578 46 43 · womenfootballscouting.com", ln=1)

# ════════ KART IZGARASI ════════
CW, CH, GX, GY = 92, 40, 8, 6           # kart genişlik/yükseklik, boşluklar
X0, Y0 = 9, 16
sut = 2

def yeni_sayfa(baslik):
    pdf.add_page(); zemin()
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, 13, "F")
    if logo.exists(): pdf.image(str(logo), x=9, y=3.5, w=34)
    pdf.set_xy(120, 4); pdf.set_font("DV", "B", 11); pdf.set_text_color(*BEYAZ)
    pdf.cell(81, 6, baslik, align="R")

def kart(o, x, y):
    isim, mevki, grup, uyruk, yas_str, boy, ayak, kulup, notu, video = o
    pdf.set_fill_color(*PANEL); pdf.set_draw_color(*CIZGI); pdf.set_line_width(0.3)
    pdf.rect(x, y, CW, CH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(x, y, 1.4, CH, "F")          # sol şerit
    # isim + mevki rozeti
    pdf.set_xy(x + 5, y + 3.5); pdf.set_font("DV", "B", 10); pdf.set_text_color(*BEYAZ)
    pdf.cell(CW - 30, 5, isim[:26])
    pdf.set_xy(x + CW - 30, y + 3.2); pdf.set_font("DV", "B", 7); pdf.set_text_color(*LIME)
    pdf.cell(26, 5.5, mevki, align="R")
    # meta satırı
    yas_gorunum = (yas_str.replace(" (", " yaş (", 1) if "(" in yas_str
                   else (f"{yas_str} yaş" if yas_str else ""))
    meta = " · ".join(x2 for x2 in [
        yas_gorunum, uyruk, (f"{boy} cm" if boy else ""), ayak] if x2)
    pdf.set_xy(x + 5, y + 10.5); pdf.set_font("DV", "", 7); pdf.set_text_color(170, 182, 200)
    while meta and pdf.get_string_width(meta) > CW - 10:
        meta = meta[:-2].rstrip()
    pdf.cell(CW - 8, 4, meta)
    # kulüp (uzun satırda punto küçülür, metin kesilmez)
    pdf.set_font("DV", "B", 7.5)
    while pdf.get_string_width(kulup or "—") > CW - 10 and pdf.font_size_pt > 6.2:
        pdf.set_font_size(pdf.font_size_pt - 0.2)
    pdf.set_xy(x + 5, y + 15.5); pdf.set_text_color(150, 200, 90)
    pdf.cell(CW - 8, 4, kulup or "—")
    # not
    pdf.set_xy(x + 5, y + 20.3); pdf.set_font("DV", "", 6.8); pdf.set_text_color(150, 160, 176)
    pdf.multi_cell(CW - 9, 3.5, notu[:118])
    # alt: video (+ sitede olan için rapor)
    site_key = _site_isim.get(_norm(isim))
    pdf.set_xy(x + 5, y + CH - 6.5); pdf.set_font("DV", "B", 7.6); pdf.set_text_color(*KIRMIZI)
    pdf.cell(26, 5, "▶ HIGHLIGHTS", link=video)
    if site_key:
        pdf.set_xy(x + 34, y + CH - 6.5); pdf.set_text_color(*YESIL)
        pdf.cell(34, 5, "★ Scout Raporu",
                 link=f"https://womenfootballscouting.com/?paylas={quote(site_key)}")

def grup_basligi(tr, en, y):
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 3, 6.5, "F")
    pdf.set_xy(X0 + 6, y + 0.5); pdf.set_font("DV", "B", 11); pdf.set_text_color(*BEYAZ)
    pdf.cell(120, 5.5, tr)
    pdf.set_font("DV", "", 8); pdf.set_text_color(*GRI)
    pdf.cell(60, 5.5, "· " + en)

# ── Sürekli akış: mevki grupları başlıklı, 2 sütun, sığmazsa yeni sayfa ──
ALT = 288
yeni_sayfa("OYUNCU HAVUZU · PLAYER POOL")
yy = Y0
for g, tr, en in GRUPLAR:
    grup_oyun = [o for o in OYUNCULAR if o[2] == g]
    if not grup_oyun:
        continue
    # başlık + en az bir kart satırı sığmıyorsa yeni sayfa
    if yy + 9 + CH > ALT:
        yeni_sayfa("OYUNCU HAVUZU · PLAYER POOL (devam)")
        yy = Y0
    grup_basligi(tr, en, yy); yy += 9
    for k in range(0, len(grup_oyun), sut):
        if yy + CH > ALT:
            yeni_sayfa("OYUNCU HAVUZU · PLAYER POOL (devam)")
            yy = Y0
        for c, o in enumerate(grup_oyun[k:k + sut]):
            kart(o, X0 + c * (CW + GX), yy)
        yy += CH + GY
    yy += 3   # gruplar arası nefes

cikti = pathlib.Path.home() / "Desktop" / "ISM_Oyuncu_Havuzu_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu")
