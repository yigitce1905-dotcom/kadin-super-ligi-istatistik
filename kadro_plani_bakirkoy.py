# -*- coding: utf-8 -*-
"""IDEAL Sports Management — BAKIRKÖY YENİMAHALLE kadro planı (Kulüp Kokpiti düzeninde) PDF.

Kokpit saha düzeni (app.py render_kokpit, `.kk-saha`): kale solda, hücum sağda;
ızgara 4 sütun × 3 satır  →  '. SOL BEK ÖN LİBERO SOL KANAT' / 'KALECİ STOPER 10 NO FORVET'
/ '. SAĞ BEK MERKEZ ORTA SAHA SAĞ KANAT'. Kutuda mevki başlığı + oyuncu sayısı + oyuncular.

Oyuncu listesi: OYUNCULAR düzenle → python kadro_plani_bakirkoy.py
Çıktı: Desktop\\ISM_Bakirkoy_Yenimahalle_Kadro_Plani_2026-27.pdf
Veri notu: yaş/boy/uyruk/kulüp SoccerDonna + site veri tabanından (2026-09-21). Bilgisi
bulunamayan oyuncular (SD'de profili yok) '—' ile gösterilir, uydurma veri girilmez.
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
# grup, isim, statü, yaş, uyruk, boy, kulüp/durum   ("" = veri yok → "—")
OYUNCULAR = [
    ("KALECİ", "Grace O'Shaughnessy", TRANSFER, "", "", "", ""),
    ("KALECİ", "Lara Karaca", MEVCUT, "17", "Türkiye", "1,68", "Bakırköy"),
    ("SAĞ BEK", "Sümeyra Kıvanç", TRANSFER, "27", "Türkiye", "1,65", "Serbest"),
    ("SAĞ BEK", "Rabia Balaban", MEVCUT, "27", "Türkiye", "1,65", "Bakırköy"),
    ("STOPER", "Sibel Duman", MEVCUT, "36", "Türkiye", "1,73", "Bakırköy"),
    ("STOPER", "Myla Schneider", TRANSFER, "22", "Kanada / Trinidad-Tobago", "1,65", "1207 Antalyaspor"),
    ("SOL BEK", "Ena Sabanagic", TRANSFER, "28", "Bosna-Hersek / ABD", "1,63", "Panathinaikos"),
    ("SOL BEK", "Ferda İpek Çevik", TRANSFER, "25", "Türkiye", "1,59", "Serbest"),
    ("ÖN LİBERO", "Abigail Appiah", TRANSFER, "", "", "", ""),
    ("MERKEZ ORTA SAHA", "Helin Erbulun", MEVCUT, "19", "Türkiye", "1,64", "Bakırköy"),
    ("MERKEZ ORTA SAHA", "Gizem Gönültaş", MEVCUT, "33", "Türkiye", "1,66", "Bakırköy"),
    ("MERKEZ ORTA SAHA", "Frankie Finlayson", TRANSFER, "20", "Kanada / İngiltere", "1,68", "Serbest"),
    ("SAĞ KANAT", "Astou Ngom", TRANSFER, "32", "Senegal", "1,63", "AS Cherbourg"),
    ("SAĞ KANAT", "Cemile Günay", TRANSFER, "17", "Türkiye", "1,61", "Beşiktaş (altyapı)"),
    ("SOL KANAT", "Christella Demba", TRANSFER, "", "", "", ""),
    ("10 NO", "Aurea Del Carmen", TRANSFER, "25", "ABD", "", "Northwestern Wildcats (ABD üniv.)"),
    ("FORVET", "Mia Darden", TRANSFER, "26", "ABD", "1,70", "Al Ahly SC"),
    ("FORVET", "Milica Babic", TRANSFER, "21", "Sırbistan / İsveç", "", "Serbest"),
]

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


# ════════ SAYFA 1 — KOKPİT SAHA DÜZENİ ════════
pdf.add_page(); zemin()
marka_bandi(f"{KULUP} · KADRO PLANI 2026-27")
pdf.set_fill_color(*LIME); pdf.rect(X0, 21, 3, 7.5, "F")
pdf.set_xy(X0 + 6, 21.2); pdf.set_font("DV", "B", 13.5); pdf.set_text_color(*METIN)
pdf.cell(150, 7, "Kadro Planı")
pdf.set_font("DV", "", 8.6); pdf.set_text_color(*GRIM)
pdf.set_xy(X0 + 6, 28.4)
mevcut_n = sum(1 for o in OYUNCULAR if o[2] == MEVCUT)
transfer_n = sum(1 for o in OYUNCULAR if o[2] == TRANSFER)
pdf.cell(200, 4, f"{len(OYUNCULAR)} oyuncu · {mevcut_n} mevcut · {transfer_n} transfer önerisi · kale solda, hücum sağda")
lejant(W - X0 - 70, 24.5)

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

gruplu = {g: [o for o in OYUNCULAR if o[0] == g] for g in SIRA}
for grup, (sat, kol) in YERLESIM.items():
    x, y, w, h = kol_x[kol], sat_y[sat], kol_w[kol], sat_h
    oy = gruplu.get(grup, [])
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.35)
    pdf.rect(x, y, w, h, "DF", round_corners=True, corner_radius=2)
    # başlık
    pdf.set_fill_color(*LIME); pdf.rect(x, y + 2.2, 1.4, 5.2, "F")
    pdf.set_xy(x + 3.6, y + 2.7); pdf.set_font("DV", "B", 8.3); pdf.set_text_color(*METIN)
    pdf.cell(w - 16, 4.4, grup)
    bx = x + w - 9.5
    pdf.set_fill_color(*KOYU); pdf.rect(bx, y + 2.3, 6.4, 5, "F", round_corners=True, corner_radius=1.2)
    pdf.set_xy(bx, y + 2.9); pdf.set_font("DV", "B", 7.6); pdf.set_text_color(*LIME)
    pdf.cell(6.4, 4, str(len(oy)), align="C")
    pdf.set_draw_color(*KENAR); pdf.set_line_width(0.25)
    pdf.line(x + 2, y + 9.4, x + w - 2, y + 9.4)
    # oyuncular
    satir_h = min(15.5, (h - 12.6) / max(len(oy), 1))
    yy = y + 11.4
    for _, isim, statu, yas, uyruk, boy, kulup in oy:
        marker(x + 3.2, yy + 1.1, statu)
        sigdir(isim, w - 12.5, 8.4, bold=True)
        pdf.set_xy(x + 8, yy); pdf.set_text_color(*METIN)
        pdf.cell(w - 11, 4.2, isim)
        veri_yok = not (yas or uyruk or boy or kulup)
        meta = "detay bilgisi bekleniyor" if veri_yok else (
            " · ".join(p for p in [(f"{yas} yaş" if yas else ""), uyruk, (f"{boy} m" if boy else "")] if p) or "—")
        sigdir(meta, w - 11, 6.6)
        pdf.set_xy(x + 8, yy + 4.2); pdf.set_text_color(*GRIM)
        pdf.cell(w - 11, 3.4, meta)
        if not veri_yok:
            kl = kulup or "—"
            sigdir(kl, w - 11, 6.6, bold=True)
            pdf.set_xy(x + 8, yy + 7.4); pdf.set_text_color(*OLIV)
            pdf.cell(w - 11, 3.4, kl)
        yy += satir_h
alt_bilgi(1)

# ════════ SAYFA 2 — OYUNCU LİSTESİ ════════
pdf.add_page(); zemin()
marka_bandi(f"{KULUP} · KADRO PLANI 2026-27")
pdf.set_fill_color(*LIME); pdf.rect(X0, 21, 3, 7.5, "F")
pdf.set_xy(X0 + 6, 21.2); pdf.set_font("DV", "B", 13.5); pdf.set_text_color(*METIN)
pdf.cell(150, 7, "Oyuncu Listesi")
lejant(W - X0 - 70, 24.5)

kolonlar = [("MEVKİ", 38), ("OYUNCU", 56), ("DURUM", 25), ("YAŞ", 13), ("UYRUK", 52), ("BOY", 15), ("KULÜP / DURUM", 78)]
ty = 34
pdf.set_fill_color(*KOYU); pdf.rect(X0, ty, CW, 8.5, "F")
tx = X0
pdf.set_font("DV", "B", 7.4); pdf.set_text_color(255, 255, 255)
for ad, w in kolonlar:
    pdf.set_xy(tx + 3, ty + 2.2); pdf.cell(w - 3, 4, ad)
    tx += w
ty += 8.5
RH = 7.6
sira_no = 0
for grup in SIRA:
    for _, isim, statu, yas, uyruk, boy, kulup in gruplu[grup]:
        sira_no += 1
        pdf.set_fill_color(*(KART if sira_no % 2 else (245, 243, 236)))
        pdf.rect(X0, ty, CW, RH, "F")
        tx = X0
        degerler = [grup, isim, "", yas or "—", uyruk or "—", boy or "—", kulup or "—"]
        for i, ((ad, w), d) in enumerate(zip(kolonlar, degerler)):
            if i == 2:
                marker(tx + 3, ty + 2.8, statu)
                pdf.set_xy(tx + 7.5, ty + 2.2); pdf.set_font("DV", "B", 7); pdf.set_text_color(*(OLIV if statu == TRANSFER else METIN))
                pdf.cell(w - 8, 4, "Transfer" if statu == TRANSFER else "Mevcut")
            else:
                bold = i == 1
                sigdir(str(d), w - 4, 8.2 if i != 0 else 7.2, bold=bold)
                pdf.set_xy(tx + 3, ty + 2.1)
                pdf.set_text_color(*(METIN if i in (1, 3, 5) else (GRIM if i == 0 else (60, 68, 82))))
                pdf.cell(w - 4, 4.2, str(d))
            tx += w
        ty += RH
pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3); pdf.line(X0, ty, X0 + CW, ty)
pdf.set_xy(X0, ty + 3.5); pdf.set_font("DV", "", 7.2); pdf.set_text_color(*GRIM)
pdf.multi_cell(CW, 3.8,
    f"Yaş, uyruk, boy ve kulüp/durum bilgileri SoccerDonna ve ISM veri tabanından {TARIH} itibarıyla derlenmiştir; "
    "güncel durumlar (özellikle 'Serbest' ve sözleşmesi biten oyuncular) teyit edilmelidir. "
    "'—' işareti, doğrulanabilir veri bulunmayan alanları gösterir.")
alt_bilgi(2)

cikti = pathlib.Path.home() / "Desktop" / "ISM_Bakirkoy_Yenimahalle_Kadro_Plani_2026-27.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB) · {len(OYUNCULAR)} oyuncu · 2 sayfa")
