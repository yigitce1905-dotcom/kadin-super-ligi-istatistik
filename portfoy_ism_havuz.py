# -*- coding: utf-8 -*-
"""IDEAL Sports Management — MEVCUT OYUNCU HAVUZU (başvuru/aday katalogu) PDF'i.

Türkiye Portföyü'nden farkı: bunlar ajansa gelen/önerilen, SİTEDE OLMAYAN
uluslararası adaylar (çoğu serbest). Diziliş yerine mevki-grupları kart ızgarası;
her oyuncuda direkt highlight video linki (+ sitede olan için scout raporu).

Kadro güncelleme: OYUNCULAR listesini düzenle → python portfoy_ism_havuz.py
Çıktı: Desktop\\ISM_Oyuncu_Havuzu_2026.pdf
"""
import json, pathlib, sys, unicodedata, re
from urllib.parse import quote
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

# ── Marka ──
LIME  = (181, 229, 0); KOYU = (11, 15, 20); PANEL = (18, 22, 34)
BEYAZ = (240, 244, 252); GRI = (120, 133, 151); CIZGI = (38, 44, 69)
KIRMIZI = (220, 60, 60); YESIL = (90, 150, 20)

ISO = {"USA":"US","Japan":"JP","Canada":"CA","Philippines":"PH","Morocco":"MA",
       "Slovakia":"SK","Croatia":"HR","Bosnia":"BA"}
def bayrak(iso):
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in iso) if len(iso) == 2 else ""

def yas(iso_dob):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso_dob or "")
    if not m:
        return "—"
    y, a, g = map(int, m.groups())
    t = date(2026, 7, 12)
    return t.year - y - ((t.month, t.day) < (a, g))

# (isim, mevki, grup, uyruk, dob_iso, boy_cm, ayak, kulup, not, video)
OYUNCULAR = [
 # ── KALECİ ──
 ("Ashley Orkus","GK","KL","USA","1998-10-09",180,"Right","Tampa Bay Sun (USL S)",
  "Güçlü iletişim + güvenilir kurtarışlar; 1.80m fiziki üstünlük","https://www.youtube.com/watch?v=roub7T62jRU"),
 ("Briana Lee O'Dell","GK","KL","USA","2001-11-27",173,"Right","Serbest (son: Vllaznia, Arnavutluk)",
  "Fiziksel varlık, güvenilir çizgi kalecisi","https://www.youtube.com/watch?v=dAghe0EO_ZE"),
 # ── DEFANS ──
 ("Jodi Smith","LCB / LB","DEF","USA","2003-01-17",170,"Left","Roses FC (NSL)",
  "Çok hızlı, sol ayaklı; LCB/LB/LW oynayabilir","https://www.youtube.com/watch?v=nPqFpcyg2-8"),
 ("Hannah Marie Russell","CB / CM","DEF","USA","2001-12-08",168,"Right","WFC Lanchkhuti (Gürcistan)",
  "Oyun kuran stoper, orta sahada da görev alır","https://youtu.be/J9-K-TRxCj8"),
 ("Myla Schneider","CB / FB","DEF","Canada","2003-10-23",165,"Right","Calgary Foothills",
  "Hızlı stoper, 1v1 savunmada güçlü","https://youtu.be/_UfG-N5eyEQ"),
 ("Asha Nikole Zuniga","CB","DEF","USA","2001-09-05",175,"Right","Serbest (son: HK, İzlanda)",
  "Güçlü hava hakimiyeti, oyunu iyi okur","https://www.youtube.com/watch?v=szf2QXYuRT0"),
 ("Enez Mango","LB","DEF","","",0,"","",
  "Sol bek — 2025/26 sezon highlights","https://youtu.be/WYqBwmWzl4I"),
 ("Melisa Hasanbegovic","RCB / LCB","DEF","Bosnia","",0,"","Al-Ula FC",
  "Merkez defans — gol, savunma & oyun kurma","https://youtu.be/PbqsUg-L_ms"),
 # ── ORTA SAHA ──
 ("Riko Yasuzawa","AM (L)","OS","Japan","2000-07-26",160,"Left","Serbest",
  "Sol ayaklı ofansif orta; kaliteli orta ve ara pas, şut gücü","https://www.youtube.com/watch?v=CqVOxjhDm5U"),
 ("Morgan Janice Burnap","FB / W / CM","OS","USA","2003-01-09",170,"Ambidextrous","Sligo Rovers (İrlanda)",
  "Teknik 1v1 oyuncu, yorulmaz motor, çok yönlü","https://www.youtube.com/watch?v=pMjQZNOhtMQ"),
 ("Claudia Muessig","CM","OS","USA","2002-07-15",163,"Both","Kalamazoo United FC",
  "Çift ayak güçlü orta saha, NCAA D1 All-Conference","https://www.youtube.com/watch?v=L6VGRERDVYw"),
 ("Brina Micheels","CM","OS","USA","2002-08-16",170,"Ambidextrous","Serbest",
  "Yüksek teknik merkez orta, dar alanda tempo belirler","https://www.youtube.com/watch?v=lREW6pHKTwo"),
 ("Adaira Nakano","AM / W","OS","Canada","2003-09-22",157,"Right","Southern Miss (NCAA)",
  "Yaratıcı oyun kurucu, üstün vizyon","https://www.hudl.com/video/3/20075233/674df9d7a523797f61bb591d"),
 ("Vina Crnoja","W / CM","OS","","",0,"","",
  "Kanat / merkez orta — 2025/26 sezon highlights","https://youtu.be/xpLCmtB0Ebw"),
 # ── HÜCUM ──
 ("Hailey Russell","ST","FW","USA","2001-12-08",157,"Right","Serbest",
  "Golcü — 23 maçta 27 gol, MFPA En İyi 11 adayı","https://www.youtube.com/watch?v=gBZtVFFeV9Q"),
 ("Abbie Burgess","W / F","FW","USA","2003-05-01",173,"Right","Serbest",
  "Hızlı, çok yönlü forvet; iki ayağıyla şut","https://youtu.be/Eqc9UTmal3o"),
 ("Gracie Dunaway","W / F","FW","USA","2003-02-21",163,"Right","Lonestar (USL W)",
  "Patlayıcı hız, atletik kanat/forvet","https://youtu.be/hrzYaJG13AU"),
 ("Maddie Eastus","ST / M","FW","USA","2003-04-30",168,"Right","Serbest",
  "Agresif, teknik, bitirici; geniş vizyon","https://youtu.be/cupFHfHo6Vg"),
 ("Lexi Fraley","F / W / AM","FW","USA","2003-01-04",157,"Ambidextrous","Purdue (NCAA)",
  "Çok yönlü forvet, güçlü top taşıma + patlayıcı hız","https://www.youtube.com/watch?v=H1Dyp6D94Ho"),
 ("Camille Sahirul","W / ST","FW","Philippines","2001-01-23",168,"Right","Eastern Suburbs (Avustralya)",
  "Dinamik kanat, hız + Filipinler A Milli oyuncusu","https://www.youtube.com/watch?v=js_eB9qgdb8"),
 ("Chaymaa Mourtaji","ST","FW","Morocco","1995-12-08",0,"","Sporting Club Casablanca",
  "Baskı yapan golcü, keskin pozisyon alma","https://www.youtube.com/results?search_query=Chaymaa+Mourtaji+football"),
 ("Nikola Rybanska","ST","FW","Slovakia","",0,"","",
  "Golcü — 2025/26 highlights (Slovak Milli)","https://youtu.be/ACA2GLmZfSE"),
]

# sitede rapor linki olanlar
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
pdf.cell(0, 5, "IDEAL Sports Management portföyündeki transfere açık uluslararası oyuncular", ln=1)

# özet kutuları
_say = {g: sum(1 for o in OYUNCULAR if o[2] == g) for g, _, _ in GRUPLAR}
_serbest = sum(1 for o in OYUNCULAR if "serbest" in o[7].lower())
_ozet = [(str(len(OYUNCULAR)), "OYUNCU"), (str(_serbest), "SERBEST"),
         (f"{_say['KL']}", "KALECİ"), (f"{_say['DEF']}", "DEFANS"),
         (f"{_say['OS']}", "ORTA SAHA"), (f"{_say['FW']}", "HÜCUM")]
ox, oy = 14, 62; bw = 30
for i, (deg, et) in enumerate(_ozet):
    x = ox + (i % 3) * (bw + 4); y = oy + (i // 3) * 26
    pdf.set_fill_color(*PANEL); pdf.set_draw_color(*CIZGI)
    pdf.rect(x, y, bw, 22, "DF")
    pdf.set_xy(x, y + 3); pdf.set_text_color(*LIME); pdf.set_font("DV", "B", 15)
    pdf.cell(bw, 7, deg, align="C")
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
sut, sat = 2, 6                          # 2 sütun × 6 satır = 12 kart/sayfa
i_slot = 0

def yeni_sayfa(baslik):
    global i_slot
    pdf.add_page(); zemin()
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, 13, "F")
    if logo.exists(): pdf.image(str(logo), x=9, y=3.5, w=34)
    pdf.set_xy(120, 4); pdf.set_font("DV", "B", 11); pdf.set_text_color(*BEYAZ)
    pdf.cell(81, 6, baslik, align="R")
    i_slot = 0

def kart(o, x, y):
    isim, mevki, grup, uyruk, dob, boy, ayak, kulup, notu, video = o
    pdf.set_fill_color(*PANEL); pdf.set_draw_color(*CIZGI); pdf.set_line_width(0.3)
    pdf.rect(x, y, CW, CH, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(x, y, 1.4, CH, "F")          # sol şerit
    # isim + mevki rozeti
    pdf.set_xy(x + 5, y + 3.5); pdf.set_font("DV", "B", 10); pdf.set_text_color(*BEYAZ)
    pdf.cell(CW - 30, 5, isim[:26])
    pdf.set_xy(x + CW - 26, y + 3.2); pdf.set_font("DV", "B", 7); pdf.set_text_color(*LIME)
    pdf.cell(22, 5.5, mevki, align="R")
    # meta (bayrak font'ta yok → ülke adı yeterli)
    _y = yas(dob)
    meta = "  ·  ".join(x2 for x2 in [
        (f"{_y} yaş" if _y != "—" else ""), uyruk,
        (f"{boy} cm" if boy else ""), ayak] if x2)
    pdf.set_xy(x + 5, y + 10.5); pdf.set_font("DV", "", 7); pdf.set_text_color(170, 182, 200)
    pdf.cell(CW - 8, 4, meta[:60])
    # kulüp
    pdf.set_xy(x + 5, y + 15.5); pdf.set_font("DV", "B", 7.5); pdf.set_text_color(150, 200, 90)
    pdf.cell(CW - 8, 4, (kulup or "—")[:54])
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
    if yy + 8 + CH > ALT:
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
