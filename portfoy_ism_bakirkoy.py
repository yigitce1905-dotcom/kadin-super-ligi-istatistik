# -*- coding: utf-8 -*-
"""IDEAL Sports Management — BAKIRKÖY YENİMAHALLE'ye özel TRANSFER SHORTLIST PDF'i.

Havuz house style (krem zemin + ISM lime aksan). 1207 Antalyaspor + Yüksekova +
Fomget shortlist'lerinden derlenmiş ortak havuz (bazı isimler çıkarıldı, 4 yeni
isim eklendi — 2026-08-10).

Kadro güncelleme: OYUNCULAR listesini düzenle → python portfoy_ism_bakirkoy.py
Çıktı: Desktop\\ISM_Bakirkoy_Yenimahalle_Shortlist_2026.pdf
"""
import json, pathlib, sys, unicodedata, re
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)
LIME  = (181, 229, 0);   OLIV = (106, 140, 0);  KOYU = (11, 15, 20)

KULUP_TR = "BAKIRKÖY YENİMAHALLE"
KULUP_DOSYA = "Bakirkoy_Yenimahalle"

# (isim, mevki, grup, uyruk, "yaş (yıl)", boy_cm, ayak, kulüp/durum, not, video)
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
 ("Maleni Morales","KL","KL","ABD / Meksika","26 (1999)",173,"","Son kulüp: Pachuca (Meksika)",
  "Fransa ve Meksika'da profesyonel deneyim (Pachuca dahil); Cal State Monterey Bay çıkışlı",
  "https://youtu.be/geND65MHLjg"),

 # ── DEFANS ──
 ("Pavlinka Nikolovska","STP / DOS","DEF","K. Makedonya","",0,"","ZFK Tiverija (K. Makedonya)",
  "K. Makedonya A Milli; fiziksel dominant modern stoper + lider; 1v1 + uzun pas + duran toplarda hava tehdidi",
  "https://www.youtube.com/watch?v=iykGGq4T9H8"),
 ("Reese Mendenhall","SĞB / KNT","DEF","ABD","24 (2002)",0,"","Son kulüp: Szekszárd (Macaristan) · Puerto Rico Pro (şampiyon)",
  "Çok yönlü kanat bek / kanat; FGCU 2024 Yılın Defans Oyuncusu + ASUN İlk 11; kaptan; 25/26 sezonu 21 maç 6 gol 7 asist; elit hız (~29 km/s)",
  "https://www.youtube.com/@reesemendenhall333"),
 ("Emma Schneider","SĞB / KNT","DEF","Kanada / Trinidad-Tobago","24 (2002)",175,"Sağ","Son kulüp: Rio Tinto (Portekiz)",
  "Trinidad-Tobago A Milli; UMaine Yılın Defans Oyuncusu (2024) ve takım kaptanı",
  "https://youtu.be/pG7WMo1ZF8A"),
 ("Enez Mango","SLB","DEF","Kenya","33",0,"","Farul Constanța (Romanya)",
  "Takım kaptanı karakterinde, tecrübeli ve lider sol bek; 2025/26 sezon highlights",
  "https://youtu.be/WYqBwmWzl4I"),
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
 ("Renée Guion","SLB / DEF","DEF","ABD","26 (1999)",173,"","Carolina Ascent FC (USL Super League)",
  "Clemson Üniv. çıkışlı; FC Gintra (Litvanya) + Fortuna Hjørring (Danimarka) Avrupa deneyimi; disiplinli sol bek / savunmacı",
  "https://youtu.be/18Twjs_Ehnk"),
 ("Kiley Dulaney","SĞB","DEF","ABD","23 (2002)",175,"","Dallas Trinity FC (USL Super League)",
  "Arkansas Razorbacks çıkışlı; Washington Spirit (NWSL) deneyimi; hücuma çıkan çok yönlü sağ bek",
  "https://m.youtube.com/watch?v=lSkr7qEazt4"),

 # ── ORTA SAHA ──
 ("Izzy Groves","DOS (6)","OS","Jamaika / Kanada","27 (1999)",178,"","Son kulüpler: Athlone Town (İrlanda) & London City Lionesses (İngiltere)",
  "Jamaika A Milli; 6 numara, top kazanan defansif orta saha; UEFA Ligi elemesinde 2 gol (Athlone Town)",
  "https://youtube.com/watch?v=26VF4wLKvl4"),
 ("Abby Werthman","OOS / KNT","OS","ABD","",0,"Sol","Western Michigan University (ABD üniversite ligi)",
  "Sol ayaklı hücum orta sahası / kanat; 2024 MAC Turnuvası MVP + All-Region; 12 gol 9 asist sezonu",
  "https://m.youtube.com/watch?v=bH5N86u2RPU"),
 ("Joya-Maria Azzi","DOS / BEK","OS","Lübnan","25 (2000)",0,"Sağ","Central Methodist Eagles (ABD)",
  "Lübnan A Milli (Dünya Kupası + Olimpiyat elemeleri); WPSL All-Conference Best XI; çok yönlü, elit çalışkanlık",
  "https://youtu.be/LAioEruBNl0"),
 ("Ana Paula Villela","MOS / KNT","OS","Brezilya","29 (1997)",0,"","Serbest",
  "Deneyimli Brezilyalı; hem merkez hem kanatta; elit teknik + yaratıcı vizyon, keskin pas menzili",
  "https://www.youtube.com/watch?v=tfrMpFBe0cU"),
 ("Sonia Opoku","OOS / MOS","OS","Gana","24 (2001)",0,"","Asa Tel Aviv WFC (İsrail)",
  "Gana A Milli geçmişi; Türkiye Süper Ligi tecrübesi (Trabzonspor + 1207 Antalyaspor, 2022-23); hücum yönlü orta saha",
  "https://youtu.be/xEh_9jk-AWg"),

 # ── HÜCUM ──
 ("Suleiman Yazdadatu","KNT / OOS","FW","Gana","21 (2005)",152,"Çift","Ladies Strikers FC (Gana)",
  "Gana U20 milli; hücum orta sahası / kanat; elit hız + dripling, süper şut; iyi orta ve serbest vuruş; Hassacas & Sung Shinning geçmişi",
  ""),
 ("Fuseina Mumuni","Sağ Kanat","FW","Gana","25 (2001)",164,"Çift","Mubadara (BAE)",
  "Türkiye Süper Ligi tecrübesi (ALG Spor, Fatih Vatan); yüksek teknik kabiliyet; Gana U17/U20 milli (FIFA Dünya Kupaları)",
  "https://youtu.be/0R71fxJZVf8"),
 ("Barakat Kikelomo Olaiya","ST","FW","Nijerya","25 (2000)",0,"","ASA Tel Aviv (İsrail)",
  "Nijeryalı santrafor; İsrail liginde ASA Tel Aviv forması; ceza sahası içi gol tehdidi",
  "https://youtu.be/qadggSeig1U"),
 ("Doosuur Anastasia Atume","ST","FW","Nijerya","20 (2005)",0,"Sağ","Edo Queens (Nijerya)",
  "2025/26 NWFL gol kraliçesi (11 gol, Altın Ayakkabı); güçlü fizik + hava; baskı altında golcü",
  "https://youtu.be/_IMZH6r7ecA"),
 ("Ljubica Bulum","ST / KNT","FW","Hırvatistan","21 (2004)",0,"Çift","ŽNK Donat-Zadar (Hırvatistan)",
  "Bu sezon 35 GOL — ligini domine etti; patlayıcı hızlanma + çift ayak bitiricilik; ceza sahası içgüdüsü",
  "https://www.youtube.com/watch?v=NO-Fsck0P2U"),
 ("Moses Esther Chioma","KNT","FW","Nijerya","20 (2006)",165,"Çift","Edo Queens (Nijerya)",
  "Nijerya U20 (Falconets); hız + bitiricilik; NWFL 2023/24 + WAFU B şampiyonu",
  "https://youtu.be/-68PygF3owI"),
 ("Essien Emem Peace","KNT / ST","FW","Nijerya","24 (2001)",170,"Çift","Kickstart FC (Hindistan)",
  "Super Falcons (A Milli); NWFL + WAFU B gol kralı (6 gol); U17/U20 geçmişi, çok yönlü hücum",
  ""),
 ("Marilyn 'Lali' Esquivel","FW","FW","Arjantin","31 (1995)",0,"","Gimnasia y Esgrima La Plata (Arjantin 1. Lig · KAPTAN)",
  "Deneyimli forvet ve takım kaptanı; Olimpia (Paraguay) ile şampiyonluk (2023) + Copa Libertadores Femenina; Brasil Ladies Cup 2025'te Palmeiras'a gol",
  "https://youtu.be/XG5fMQDCx9c"),
 ("Doly Wabue","CFW","FW","Kamerun","23 (2003)",0,"","Damaiense W",
  "Poacher / Target santrafor profili; ceza sahası içi bitiricilik odaklı",
  "https://www.youtube.com/watch?v=zgOW5O2XoDo"),
 ("Bojana Petkova","ST","FW","K. Makedonya","22 (2003)",0,"","Polonia Środa Wlkp (Polonya)",
  "K. Makedonya A Milli; santrafor; Polonya liginde düzenli forma",
  "https://vimeo.com/1026810455"),
]

# sitede scout raporu olanlar → karta ★ Scout Raporu eklenir
_scout = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
def _norm(s): return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower())).strip()
_site_isim = {_norm(k): k for k in _scout}

GRUPLAR = [("KL","KALECİ","GOALKEEPER"), ("DEF","DEFANS","DEFENDERS"),
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
pdf.cell(0, 6, f"{KULUP_TR} · KADIN FUTBOLU · YAZ 2026", ln=1)
pdf.set_x(14); pdf.set_font("DV", "", 9); pdf.set_text_color(*GRIM)
pdf.cell(0, 6, "Kadro planlamanıza yönelik seçilmiş aday oyuncular", ln=1)

_say = {g: sum(1 for o in OYUNCULAR if o[2] == g) for g, _, _ in GRUPLAR}
_ulkeler = {p.strip() for o in OYUNCULAR for p in o[3].split("/") if p.strip()}
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

pdf.set_xy(14, 112); pdf.set_font("DV", "", 9.2); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(150, 5.4,
    f"Bu dosya, {KULUP_TR} Kadın Futbol Takımı'nın Yaz 2026 kadro planlamasına "
    "yönelik seçilmiş aday oyuncuları mevki bölgelerine göre sunar. Her oyuncu "
    "kartında güncel kulüp/durum, künye, öne çıkan özellikler ve tek tıkla "
    "izlenebilen highlight videosu yer alır. İlgilendiğiniz oyuncular için "
    "detaylı scout raporu, referans ve görüşme organizasyonu hızlıca sağlanır.")

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
    marka_bandi(h=13, baslik=f"{KULUP_TR} SHORTLIST · YAZ 2026")
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

cikti = pathlib.Path.home() / "Desktop" / f"ISM_{KULUP_DOSYA}_Shortlist_2026.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu · {_sayfa_no} sayfa")
