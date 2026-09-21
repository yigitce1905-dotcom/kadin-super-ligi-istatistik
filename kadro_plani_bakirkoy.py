# -*- coding: utf-8 -*-
"""IDEAL Sports Management — BAKIRKÖY YENİMAHALLE kadro planı (Kulüp Kokpiti düzeninde) PDF.

Kokpit saha düzeni (app.py render_kokpit, `.kk-saha`): kale solda, hücum sağda;
ızgara 4 sütun × 3 satır  →  '. SOL BEK ÖN LİBERO SOL KANAT' / 'KALECİ STOPER 10 NO FORVET'
/ '. SAĞ BEK MERKEZ ORTA SAHA SAĞ KANAT'. Kutuda mevki başlığı + oyuncu sayısı + oyuncular.
Sayfa 1 saha düzeni · Sayfa 2 oyuncu listesi (+ video linkleri) · Sayfa 3 öne çıkan özellikler.

Oyuncu listesi: OYUNCULAR / EKSTRA düzenle → python kadro_plani_bakirkoy.py
Çıktı: Desktop\\ISM_Bakirkoy_Yenimahalle_Kadro_Plani_2026-27.pdf
Veri notu: yaş/boy/uyruk/kulüp SoccerDonna + site veri tabanı + Yiğit'in ilettiği bilgiler
(2026-09-21). Bilinmeyen alanlar '—' ile gösterilir, uydurma veri girilmez.
"""
import pathlib, sys
from fpdf import FPDF

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)
LIME  = (181, 229, 0);   OLIV = (106, 140, 0);  KOYU = (11, 15, 20)
SAHA  = (236, 240, 226); SAHA_CIZGI = (205, 214, 186)

KULUP = "BAKIRKÖY YENİMAHALLE"
TARIH = "21.09.2026"

MEVCUT, TRANSFER = "MEVCUT", "TRANSFER"
# grup, isim, statü, yaş, uyruk, boy, kulüp/durum (liste), kulüp (saha kutusu, kısa)
OYUNCULAR = [
    ("KALECİ", "Grace O'Shaughnessy", TRANSFER, "", "Manchester, İngiltere", "1,88",
     "Serbest · son: Southern Miss (ABD üniv.)", "Serbest"),
    ("KALECİ", "Lara Karaca", MEVCUT, "17", "Türkiye", "1,68", "Bakırköy", "Bakırköy"),
    ("SAĞ BEK", "Sümeyra Kıvanç", MEVCUT, "27", "Türkiye", "1,65", "Bakırköy", "Bakırköy"),
    ("SAĞ BEK", "Rabia Balaban", MEVCUT, "27", "Türkiye", "1,65", "Bakırköy", "Bakırköy"),
    ("STOPER", "Sibel Duman", MEVCUT, "36", "Türkiye", "1,73", "Bakırköy", "Bakırköy"),
    ("SOL BEK", "Mareme Babou", TRANSFER, "23", "Senegal", "1,65", "Serbest", "Serbest"),
    ("SOL BEK", "Ferda İpek Çevik", TRANSFER, "25", "Türkiye", "1,59", "Serbest", "Serbest"),
    ("ÖN LİBERO", "Abigail Appiah", TRANSFER, "", "Gana", "", "Son kulüp: Hapoel Ra'anana (İsrail, 2025/26)",
     "Hapoel Ra'anana"),
    ("MERKEZ ORTA SAHA", "Helin Erbulun", MEVCUT, "19", "Türkiye", "1,64", "Bakırköy", "Bakırköy"),
    ("MERKEZ ORTA SAHA", "Gizem Gönültaş", MEVCUT, "33", "Türkiye", "1,66", "Bakırköy", "Bakırköy"),
    ("MERKEZ ORTA SAHA", "Frankie Finlayson", TRANSFER, "20", "Kanada / İngiltere", "1,68", "Serbest", "Serbest"),
    ("SAĞ KANAT", "Astou Ngom", TRANSFER, "32", "Senegal", "1,63", "AS Cherbourg", "AS Cherbourg"),
    ("SAĞ KANAT", "Cemile Günay", MEVCUT, "17", "Türkiye", "1,61", "Bakırköy", "Bakırköy"),
    ("SOL KANAT", "Christelle Demba", TRANSFER, "28", "Orta Afrika Cumhuriyeti", "1,70",
     "Serbest · son: Riga FC (Letonya)", "Serbest"),
    ("10 NO", "Aurea Del Carmen", TRANSFER, "25", "ABD", "1,62", "Son okul: Northwestern Üniv. (NCAA Div. I)",
     "Northwestern Üniv."),
    ("FORVET", "Mia Darden", TRANSFER, "26", "ABD", "1,70", "Son kulüp: Al Ahly SC (Mısır)", "Al Ahly SC"),
    ("FORVET", "Milica Babic", TRANSFER, "21", "Sırbistan / İsveç", "1,85",
     "Serbest · son: ŽFK Emina Mostar (Bosna-Hersek)", "Serbest"),
]

# isim → {"link": [(etiket, url)], "not": [madde, ...]}   — link etiketi 'VİDEO' ise listede ▶ olarak görünür
EKSTRA = {
    "Grace O'Shaughnessy": {
        "link": [("PROFİL", "https://southernmiss.com/sports/womens-soccer/roster/grace-o-shaughnessy/10425")],
        "not": ["Kaleci; 1,88 m (6-2), yüksek boylu",
                "Southern Miss (NCAA Div. I) kalecisi; önceki okul: Georgia Southwestern",
                "Memleketi Manchester, İngiltere · şu an serbest"],
    },
    "Mareme Babou": {
        "link": [("VİDEO", "https://youtu.be/ZI91F886PZ0")],
        "not": ["Sol bek; 23 yaşında, Senegal",
                "Video başlığına göre kulüp ve Senegal kadın milli takımı performanslarını içeriyor",
                "Şu an serbest görünüyor (SoccerDonna)"],
    },
    "Abigail Appiah": {
        "link": [("VİDEO 1", "https://drive.google.com/open?id=1nVuTDCtcCorWO9sAqOyu55oN-wXmmvYy"),
                 ("VİDEO 2", "https://youtu.be/HclgMGpxM9E"),
                 ("HABER", "https://www.myjoyonline.com/wafcon-2026q-abigail-appiah-receives-late-black-queens-call-up-for-egypt-doubleheader/"),
                 ("PROFİL", "https://globalsportsarchive.com/en/soccer/athlete/abigail-appiah/7888588")],
        "not": ["Uzun boylu savunmacı orta saha (stoper de oynayabilir)",
                "Son kulüp: Hapoel Ra'anana (İsrail) — 2025/26 sezonu; öncesinde Jonina Ladies",
                "Gana A Milli (Black Queens): WAFCON 2026 elemelerinde Mısır maçları için çağrıldı (Ekim 2025)"],
    },
    "Christelle Demba": {
        "link": [("VİDEO 1", "https://youtu.be/lN6Y336gYf0"),
                 ("VİDEO 2", "https://youtu.be/2uSMtHiNvic"),
                 ("WIKI", "https://en.m.wikipedia.org/wiki/Christelle_Demba"),
                 ("TRANSFERLER", "https://www.soccerdonna.de/en/christelle-ursula-demba/transfers/spieler_70515.html")],
        "not": ["Sağ / sol kanat oynayabiliyor (SoccerDonna'da santrafor); Orta Afrika A Milli",
                "14 maçta 13 gol (ISM notu)",
                "Türkiye deneyimi: Amed (2021-23) ve ALG Spor (2023-24); son kulüp Riga FC (Letonya)",
                "Fransa'da ikamet kartı var, şu an Fransa'da"],
    },
    "Aurea Del Carmen": {
        "link": [("VİDEO", "https://www.youtube.com/watch?v=kEbbUcHKDzw")],
        "not": ["Forvet / hücumcu orta saha; sağ ayaklı, 1,62 m (5'4)",
                "Big Ten Konferansı 2. Takımı (Second Team All-Big Ten)",
                "United Soccer Coaches Kuzey Bölgesi 3. Takımı (3rd Team All-North Region)",
                "Son okul: Northwestern University (NCAA Div. I)"],
    },
    "Mia Darden": {
        "link": [("VİDEO", "https://www.youtube.com/watch?v=MKq0evg9SKU")],
        "not": ["Forvet / kanat; iki ayağını da kullanıyor, 1,70 m (5'7)",
                "Al Ahly (Mısır): Mısır Ligi ikincisi (2025-26), Mısır Kupası şampiyonu (2025)",
                "Moterų A Lyga (Litvanya) 2023 sezonunda gol krallığında ilk 3"],
    },
    "Milica Babic": {
        "link": [("VİDEO", "https://youtu.be/WFRCQhMvBcs")],
        "not": ["Bosna Ligi ve Bosna Kupası gol kralı: yarım sezonda 12 gol, 2 asist",
                "Sezonun Takımı'na seçildi; ŽFK Emina Mostar (2026)",
                "1,85 m; iki ayağıyla da güçlü bitirici",
                "Eski Sırbistan A Milli; 2024 UEFA Kadınlar Avrupa Şampiyonası kapsamında Sırbistan adına gol attı"],
    },
}

# kokpit ızgarası: (satır, sütun) — 0-indeksli
YERLESIM = {
    "SOL BEK": (0, 1), "ÖN LİBERO": (0, 2), "SOL KANAT": (0, 3),
    "KALECİ": (1, 0), "STOPER": (1, 1), "10 NO": (1, 2), "FORVET": (1, 3),
    "SAĞ BEK": (2, 1), "MERKEZ ORTA SAHA": (2, 2), "SAĞ KANAT": (2, 3),
}
SIRA = ["KALECİ", "SAĞ BEK", "STOPER", "SOL BEK", "ÖN LİBERO", "MERKEZ ORTA SAHA",
        "SAĞ KANAT", "SOL KANAT", "10 NO", "FORVET"]

_f = KOK / "fonts"
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(False)
pdf.add_font("DV", "", str(_f / "DejaVuSans.ttf"))
pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
logo = KOK / "static" / "ism_logo_beyaz.png"

W, H = 297, 210
X0 = 10; CW = W - 2 * X0


def zemin():
    pdf.set_fill_color(*KREM); pdf.rect(0, 0, W, H, "F")


def marka_bandi(baslik):
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, W, 16, "F")
    if logo.exists():
        pdf.image(str(logo), x=X0, y=4.6, w=32)
    pdf.set_xy(W - X0 - 200, 5.3); pdf.set_font("DV", "B", 10.5)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(200, 6, baslik, align="R")


def sayfa_basligi(baslik, alt=""):
    pdf.set_fill_color(*LIME); pdf.rect(X0, 21, 3, 7.5, "F")
    pdf.set_xy(X0 + 6, 21.2); pdf.set_font("DV", "B", 13.5); pdf.set_text_color(*METIN)
    pdf.cell(150, 7, baslik)
    if alt:
        pdf.set_font("DV", "", 8.6); pdf.set_text_color(*GRIM)
        pdf.set_xy(X0 + 6, 28.4)
        pdf.cell(200, 4, alt)
    lejant(W - X0 - 70, 24.5)


def alt_bilgi(no):
    pdf.set_y(-11); pdf.set_font("DV", "", 7); pdf.set_text_color(*GRIM)
    pdf.set_x(X0)
    pdf.cell(CW * 0.62, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43 · womenfootballscouting.com")
    pdf.cell(CW * 0.38, 5, f"Sayfa {no}", align="R")


def sigdir(metin, maks, boyut, bold=False):
    pdf.set_font("DV", "B" if bold else "", boyut)
    while pdf.get_string_width(metin) > maks and pdf.font_size_pt > 5.2:
        pdf.set_font_size(pdf.font_size_pt - 0.2)


def marker(x, y, statu):
    pdf.set_line_width(0.25)
    if statu == TRANSFER:
        pdf.set_fill_color(*LIME); pdf.set_draw_color(*OLIV)
    else:
        pdf.set_fill_color(*KOYU); pdf.set_draw_color(*KOYU)
    pdf.rect(x, y, 2.8, 2.8, "DF")


def lejant(x, y):
    pdf.set_font("DV", "", 7.2)
    for et, st in (("Mevcut oyuncu", MEVCUT), ("Transfer önerisi", TRANSFER)):
        marker(x, y + 0.6, st)
        pdf.set_xy(x + 4.5, y); pdf.set_text_color(*GRIM)
        pdf.cell(30, 4, et)
        x += 34


def boy_str(b):
    return f"{b} m" if b and b[0].isdigit() else (b or "")


mevcut_n = sum(1 for o in OYUNCULAR if o[2] == MEVCUT)
transfer_n = sum(1 for o in OYUNCULAR if o[2] == TRANSFER)
gruplu = {g: [o for o in OYUNCULAR if o[0] == g] for g in SIRA}

# ════════ SAYFA 1 — KOKPİT SAHA DÜZENİ ════════
pdf.add_page(); zemin()
marka_bandi(f"{KULUP} · KADRO PLANI 2026-27")
sayfa_basligi("Kadro Planı",
              f"{len(OYUNCULAR)} oyuncu · {mevcut_n} mevcut · {transfer_n} transfer önerisi · kale solda, hücum sağda")

BY0, BH = 35, 158          # saha çerçevesi
pdf.set_fill_color(*SAHA); pdf.set_draw_color(*SAHA_CIZGI); pdf.set_line_width(0.5)
pdf.rect(X0, BY0, CW, BH, "DF", round_corners=True, corner_radius=3)
pdf.set_line_width(0.4)
ch = BH * 0.46
pdf.rect(X0, BY0 + BH / 2 - ch / 2, 20, ch)
pdf.rect(X0 + CW - 20, BY0 + BH / 2 - ch / 2, 20, ch)

PAD, GAP = 4.5, 4.5
oran = [0.9, 1.05, 1.05, 1.05]
ic_w = CW - 2 * PAD - 3 * GAP
kol_w = [ic_w * o / sum(oran) for o in oran]
kol_x = [X0 + PAD + sum(kol_w[:i]) + i * GAP for i in range(4)]
sat_h = (BH - 2 * PAD - 2 * GAP) / 3
sat_y = [BY0 + PAD + i * (sat_h + GAP) for i in range(3)]

for grup, (sat, kol) in YERLESIM.items():
    x, y, w, h = kol_x[kol], sat_y[sat], kol_w[kol], sat_h
    oy = gruplu.get(grup, [])
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.35)
    pdf.rect(x, y, w, h, "DF", round_corners=True, corner_radius=2)
    pdf.set_fill_color(*LIME); pdf.rect(x, y + 2.2, 1.4, 5.2, "F")
    pdf.set_xy(x + 3.6, y + 2.7); pdf.set_font("DV", "B", 8.3); pdf.set_text_color(*METIN)
    pdf.cell(w - 16, 4.4, grup)
    bx = x + w - 9.5
    pdf.set_fill_color(*KOYU); pdf.rect(bx, y + 2.3, 6.4, 5, "F", round_corners=True, corner_radius=1.2)
    pdf.set_xy(bx, y + 2.9); pdf.set_font("DV", "B", 7.6); pdf.set_text_color(*LIME)
    pdf.cell(6.4, 4, str(len(oy)), align="C")
    pdf.set_draw_color(*KENAR); pdf.set_line_width(0.25)
    pdf.line(x + 2, y + 9.4, x + w - 2, y + 9.4)
    satir_h = min(15.5, (h - 12.6) / max(len(oy), 1))
    yy = y + 11.4
    for _, isim, statu, yas, uyruk, boy, kulup, kisa in oy:
        marker(x + 3.2, yy + 1.1, statu)
        sigdir(isim, w - 12.5, 8.4, bold=True)
        pdf.set_xy(x + 8, yy); pdf.set_text_color(*METIN)
        pdf.cell(w - 11, 4.2, isim)
        veri_yok = not (yas or uyruk or boy or kulup)
        meta = "detay bilgisi bekleniyor" if veri_yok else (
            " · ".join(p for p in [(f"{yas} yaş" if yas else ""), uyruk, boy_str(boy)] if p) or "—")
        sigdir(meta, w - 11, 6.6)
        pdf.set_xy(x + 8, yy + 4.2); pdf.set_text_color(*GRIM)
        pdf.cell(w - 11, 3.4, meta)
        if not veri_yok:
            kl = kisa or "—"
            sigdir(kl, w - 11, 6.6, bold=True)
            pdf.set_xy(x + 8, yy + 7.4); pdf.set_text_color(*OLIV)
            pdf.cell(w - 11, 3.4, kl)
        yy += satir_h
alt_bilgi(1)

# ════════ SAYFA 2 — OYUNCU LİSTESİ ════════
pdf.add_page(); zemin()
marka_bandi(f"{KULUP} · KADRO PLANI 2026-27")
sayfa_basligi("Oyuncu Listesi")

kolonlar = [("MEVKİ", 32), ("OYUNCU", 48), ("DURUM", 22), ("YAŞ", 11), ("UYRUK", 46), ("BOY", 13),
            ("KULÜP / DURUM", 70), ("VİDEO", 35)]
ty = 34
pdf.set_fill_color(*KOYU); pdf.rect(X0, ty, CW, 8.5, "F")
tx = X0
pdf.set_font("DV", "B", 7.4); pdf.set_text_color(255, 255, 255)
for ad, w in kolonlar:
    pdf.set_xy(tx + 3, ty + 2.2); pdf.cell(w - 3, 4, ad)
    tx += w
ty += 8.5
RH = 7.7
sira_no = 0
for grup in SIRA:
    for _, isim, statu, yas, uyruk, boy, kulup, kisa in gruplu[grup]:
        sira_no += 1
        pdf.set_fill_color(*(KART if sira_no % 2 else (245, 243, 236)))
        pdf.rect(X0, ty, CW, RH, "F")
        tx = X0
        degerler = [grup, isim, "", yas or "—", uyruk or "—", (boy_str(boy) or "—"), kulup or "—", ""]
        for i, ((ad, w), d) in enumerate(zip(kolonlar, degerler)):
            if i == 2:
                marker(tx + 3, ty + 2.5, statu)
                pdf.set_xy(tx + 7.5, ty + 2), pdf.set_font("DV", "B", 7)
                pdf.set_text_color(*(OLIV if statu == TRANSFER else METIN))
                pdf.cell(w - 8, 4, "Transfer" if statu == TRANSFER else "Mevcut")
            elif i == 7:
                linkler = [l for l in EKSTRA.get(isim, {}).get("link", []) if l[0].startswith(("VİDEO", "PROFİL"))]
                lx = tx + 2
                pdf.set_font("DV", "B", 6.6); pdf.set_text_color(*OLIV)
                for et, url in linkler[:2]:
                    yazi = "▶ " + et.replace("VİDEO", "Video").replace("PROFİL", "Profil")
                    gw = pdf.get_string_width(yazi) + 1
                    pdf.set_xy(lx, ty + 2.2); pdf.cell(gw, 4, yazi, link=url)
                    lx += gw + 2.5
            else:
                bold = i == 1
                sigdir(str(d), w - 4, 8.0 if i != 0 else 7.0, bold=bold)
                pdf.set_xy(tx + 3, ty + 2.0)
                pdf.set_text_color(*(METIN if i in (1, 3, 5) else (GRIM if i == 0 else (60, 68, 82))))
                pdf.cell(w - 4, 4.2, str(d))
            tx += w
        ty += RH
pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3); pdf.line(X0, ty, X0 + CW, ty)
pdf.set_xy(X0, ty + 3.5); pdf.set_font("DV", "", 7.2); pdf.set_text_color(*GRIM)
pdf.multi_cell(CW, 3.8,
    f"Yaş, uyruk, boy ve kulüp/durum bilgileri SoccerDonna, ISM veri tabanı ve oyuncu temsilcilerinden {TARIH} itibarıyla "
    "derlenmiştir; güncel durumlar (özellikle 'Serbest' yazanlar) teyit edilmelidir. "
    "'—' işareti, doğrulanabilir veri bulunmayan alanları gösterir. Video/profil bağlantıları tıklanabilir.")
alt_bilgi(2)

# ════════ SAYFA 3+ — ÖNE ÇIKAN ÖZELLİKLER (sayfa başına 4 kart) ════════
notlu = [o for o in OYUNCULAR if o[1] in EKSTRA]
KW = (CW - 6) / 2; KH = 72; KGAP = 6
sayfa_no = 2
for parca_i in range(0, len(notlu), 4):
    parca = notlu[parca_i:parca_i + 4]
    sayfa_no += 1
    pdf.add_page(); zemin()
    marka_bandi(f"{KULUP} · KADRO PLANI 2026-27")
    sayfa_basligi("Transfer Önerileri · Öne Çıkan Özellikler",
                  f"{len(notlu)} oyuncu · bilgiler ISM notları ve açık kaynaklardan")
    for n, o in enumerate(parca):
        grup, isim, statu, yas, uyruk, boy, kulup, kisa = o
        x = X0 + (n % 2) * (KW + KGAP)
        y = 35 + (n // 2) * (KH + 6)
        pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
        pdf.rect(x, y, KW, KH, "DF")
        pdf.set_fill_color(*LIME); pdf.rect(x, y, 1.8, KH, "F")
        pdf.set_xy(x + 6, y + 4); pdf.set_font("DV", "B", 12.5); pdf.set_text_color(*METIN)
        pdf.cell(KW - 50, 7, isim)
        pdf.set_font("DV", "B", 7.6)
        pw = pdf.get_string_width(grup) + 7
        pdf.set_fill_color(*KOYU); pdf.rect(x + KW - 5 - pw, y + 4.4, pw, 6, "F")
        pdf.set_xy(x + KW - 5 - pw, y + 5); pdf.set_text_color(*LIME); pdf.cell(pw, 4.8, grup, align="C")
        meta = " · ".join(p for p in [(f"{yas} yaş" if yas else ""), uyruk, boy_str(boy)] if p) or "—"
        sigdir(meta, KW - 12, 8.4)
        pdf.set_xy(x + 6, y + 12.6); pdf.set_text_color(*GRIM); pdf.cell(KW - 12, 4.4, meta)
        sigdir(kulup, KW - 12, 8.8, bold=True)
        pdf.set_xy(x + 6, y + 18); pdf.set_text_color(*OLIV); pdf.cell(KW - 12, 4.4, kulup)
        yy = y + 26
        pdf.set_font("DV", "", 8)
        for m in EKSTRA[isim]["not"]:
            pdf.set_xy(x + 6, yy); pdf.set_text_color(*OLIV); pdf.cell(3, 4.2, "•")
            pdf.set_xy(x + 9.5, yy); pdf.set_text_color(60, 68, 82)
            pdf.multi_cell(KW - 15, 4.2, m, align="L")
            yy = pdf.get_y() + 0.9
        bx = x + 6; by = y + KH - 10
        pdf.set_font("DV", "B", 7.2)
        for et, url in EKSTRA[isim]["link"]:
            yazi = ("▶ " if et.startswith("VİDEO") else "") + et
            bw_ = pdf.get_string_width(yazi) + 7
            pdf.set_fill_color(*LIME); pdf.rect(bx, by, bw_, 6.2, "F")
            pdf.set_xy(bx, by + 1.05); pdf.set_text_color(*KOYU); pdf.cell(bw_, 4, yazi, align="C", link=url)
            bx += bw_ + 2.5
    alt_bilgi(sayfa_no)

cikti = pathlib.Path.home() / "Desktop" / "ISM_Bakirkoy_Yenimahalle_Kadro_Plani_2026-27.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu · {sayfa_no} sayfa")
