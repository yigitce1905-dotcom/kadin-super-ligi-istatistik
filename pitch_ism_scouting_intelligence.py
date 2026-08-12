# -*- coding: utf-8 -*-
"""IDEAL Sports Management — SCOUTING INTELLIGENCE pitch (İNGİLİZCE).

Hedef: UEFA Women's Champions League / Women's Europa Cup seviyesindeki Avrupa
kulüplerinin sportif direktör & recruitment departmanları.

Ana argüman: kadın futbolunda Wyscout/InStat/Hudl kapsaması top-5 lig dışında
çok zayıf — biz o boşluğu İNSAN scout değerlendirmesiyle dolduruyoruz.

Çıktı: Desktop\\ISM_Scouting_Intelligence_2026.pdf
"""
import json, pathlib, sys
from fpdf import FPDF

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent

KREM  = (250, 248, 242); KART = (255, 255, 255); KENAR = (228, 224, 214)
METIN = (26, 32, 44);    GRIM = (122, 130, 142)
LIME  = (181, 229, 0);   OLIV = (106, 140, 0);  KOYU = (11, 15, 20)

# ── Canlı veriden sayılar (pitch'te uydurma rakam olmasın) ──
_d  = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
_tr = json.load(open(KOK / "scotr_raporlar.json", encoding="utf-8"))
N_TOPLAM = len(_d) + len(_tr)
N_DEGER  = (sum(1 for v in _d.values() if v.get("degerlendirildi"))
            + sum(1 for v in _tr.values() if v.get("degerlendirildi")))
N_ULKE   = len({(v.get("vatandaslik") or "").strip() for v in _d.values()
                if (v.get("vatandaslik") or "").strip()})

pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(False)
_f = KOK / "fonts"
pdf.add_font("DV", "",  str(_f / "DejaVuSans.ttf"))
pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
pdf.add_font("IMZA", "", r"C:\Windows\Fonts\segoesc.ttf")
logo = KOK / "static" / "ism_logo_beyaz.png"

X0, CW = 14, 182

def zemin():
    pdf.set_fill_color(*KREM); pdf.rect(0, 0, 210, 297, "F")

def marka_bandi(h=13, baslik=""):
    pdf.set_fill_color(*KOYU); pdf.rect(0, 0, 210, h, "F")
    if logo.exists(): pdf.image(str(logo), x=10, y=h/2 - 3.2, w=32)
    if baslik:
        pdf.set_xy(100, h/2 - 3); pdf.set_font("DV", "B", 10.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(100, 6, baslik, align="R")

def alt_bilgi(no):
    pdf.set_y(-16); pdf.set_font("DV", "", 7.6); pdf.set_text_color(*GRIM)
    pdf.set_x(X0)
    pdf.cell(CW / 2, 5, "Yiğit Çelebi · IDEAL Sports Management · +90 506 578 46 43")
    pdf.cell(CW / 2, 5, f"Page {no}", align="R")

def bolum_basligi(y, tr):
    pdf.set_fill_color(*LIME); pdf.rect(X0, y, 3.2, 8, "F")
    pdf.set_xy(X0 + 7, y + 0.6); pdf.set_font("DV", "B", 15); pdf.set_text_color(*METIN)
    pdf.cell(160, 7, tr)

def paragraf(y, metin, boy=9.4, satir=5.6, genislik=168, renk=(60, 68, 82)):
    pdf.set_xy(X0, y); pdf.set_font("DV", "", boy); pdf.set_text_color(*renk)
    pdf.multi_cell(genislik, satir, metin)
    return pdf.get_y()

def madde(y, baslik, aciklama):
    pdf.set_xy(X0 + 2, y); pdf.set_font("DV", "B", 9.6); pdf.set_text_color(*OLIV)
    pdf.cell(4, 5.4, "▸")
    pdf.set_text_color(*METIN)
    pdf.cell(0, 5.4, baslik, ln=1)
    pdf.set_xy(X0 + 8, pdf.get_y() + 0.4); pdf.set_font("DV", "", 8.8)
    pdf.set_text_color(60, 68, 82)
    pdf.multi_cell(160, 5.0, aciklama)
    return pdf.get_y() + 2.6

# ══════════════════ SAYFA 1 — KAPAK / ANA ARGÜMAN ══════════════════
pdf.add_page(); zemin()
marka_bandi(h=34)

pdf.set_xy(14, 44); pdf.set_font("DV", "B", 24); pdf.set_text_color(*METIN)
pdf.cell(0, 11, "SCOUTING INTELLIGENCE", ln=1)
pdf.set_x(14); pdf.set_font("DV", "B", 10.5); pdf.set_text_color(*OLIV)
pdf.cell(0, 6, "FOR WOMEN'S FOOTBALL CLUBS · UEFA COMPETITION LEVEL · 2026-27", ln=1)

pdf.set_xy(14, 66); pdf.set_font("DV", "B", 13); pdf.set_text_color(*METIN)
pdf.multi_cell(178, 7.4,
    "The data tools that work in men's football do not work the same way\n"
    "in the women's game. We built the layer that is missing.")

y = paragraf(88,
    "Wyscout, InStat and Hudl are excellent products — but their women's football coverage "
    "collapses outside the top five leagues. Event data is thin or absent, video is "
    "incomplete, and player profiles in Eastern Europe, Scandinavia, the Balkans, Africa, "
    "Asia and South America are frequently empty shells: a name, a birth year, nothing else.",
    boy=9.6, satir=5.8, genislik=170)

y = paragraf(y + 4,
    "That is exactly where most of the value in the women's transfer market currently sits. "
    "Clubs competing in the UEFA Women's Champions League and the Women's Europa Cup are "
    "routinely asked to make six-figure decisions on players they cannot properly verify.",
    boy=9.6, satir=5.8, genislik=170)

y = paragraf(y + 4,
    "We close that gap with human scouting at scale — a curated, continuously maintained "
    "database of players assessed by our own analysts against a fixed 47-attribute framework, "
    "not scraped from an API.",
    boy=9.6, satir=5.8, genislik=170)

# ── Sayı kutuları ──
_ozet = [(f"{N_TOPLAM:,}".replace(",", "."), "PLAYERS TRACKED"),
         (f"{N_DEGER:,}".replace(",", "."), "FULLY ASSESSED"),
         (f"{N_ULKE}+", "NATIONALITIES"),
         ("47", "ATTRIBUTES / PLAYER")]
oy = 168; bw, bh = 42, 26
for i, (deger, et) in enumerate(_ozet):
    x = 14 + i * (bw + 3.5)
    pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
    pdf.rect(x, oy, bw, bh, "DF")
    pdf.set_fill_color(*LIME); pdf.rect(x, oy, bw, 1.6, "F")
    pdf.set_xy(x, oy + 5); pdf.set_text_color(*METIN); pdf.set_font("DV", "B", 16)
    pdf.cell(bw, 8, deger, align="C")
    pdf.set_xy(x, oy + 16); pdf.set_text_color(*GRIM); pdf.set_font("DV", "", 6.2)
    pdf.cell(bw, 4, et, align="C")

pdf.set_xy(14, 204); pdf.set_font("DV", "", 8.6); pdf.set_text_color(*GRIM)
pdf.multi_cell(170, 5.0,
    "Every assessment is produced by a named analyst, is dated, and is revisited each season — "
    "so you always know who formed the opinion and when.")

# imza
pdf.set_xy(14, 244); pdf.set_font("IMZA", "", 17); pdf.set_text_color(*METIN)
pdf.cell(80, 9, "Yiğit Çelebi", ln=1)
pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
pdf.line(15, 255, 76, 255)
pdf.set_xy(15, 256); pdf.set_font("DV", "B", 8.5); pdf.set_text_color(*METIN)
pdf.cell(90, 5, "Yiğit Çelebi · IDEAL Sports Management", ln=1)
pdf.set_x(15); pdf.set_font("DV", "", 7.8); pdf.set_text_color(*GRIM)
pdf.cell(90, 4.5, "+90 506 578 46 43 · womenfootballscouting.com", ln=1)

# ══════════════════ SAYFA 2 — NE SUNUYORUZ ══════════════════
pdf.add_page(); zemin()
marka_bandi(h=13, baslik="SCOUTING INTELLIGENCE · 2026-27")
bolum_basligi(20, "What we do for your recruitment desk")

y = 34
y = madde(y, "1.  Value identification — the \"moneyball\" question",
    "You have a shortlisted player and a price. We tell you, from our own assessments, which "
    "players in comparable or overlooked leagues reach the same profile at a materially lower "
    "cost — with the attribute-by-attribute comparison behind the claim, not just a name.")

y = madde(y, "2.  Due diligence on agent-led proposals",
    "When an intermediary brings you a player, you receive their highlight reel and their best "
    "numbers. We give you the rest: our independent assessment, contract status, real minutes "
    "played, injury and continuity record, professionalism and adaptability markers, and — "
    "where relevant — whether the player is realistically willing to move to your league.")

y = madde(y, "3.  Free-agent and January-window intelligence",
    "A continuously updated view of who is genuinely out of contract, whose deal expires within "
    "6/12/18 months, and who is available now. In a market where this information is scattered "
    "across federation sites in a dozen languages, this alone shortens your search by weeks.")

y = madde(y, "4.  Position-specific shortlists on request",
    "Give us the brief — position, age ceiling, budget, playing style, passport requirements "
    "(EU-eligibility filtering included) — and receive a ranked shortlist with full profiles, "
    "video, and our honest reservations about each candidate.")

y = madde(y, "5.  Squad and opposition analysis",
    "Multi-season development curves for individual players, squad-depth mapping by tactical "
    "zone, and profiling of squads you are about to face in European competition.")

pdf.set_xy(X0, y + 4)
pdf.set_fill_color(*KART); pdf.set_draw_color(*KENAR); pdf.set_line_width(0.3)
pdf.rect(X0, y + 4, CW, 30, "DF")
pdf.set_fill_color(*LIME); pdf.rect(X0, y + 4, 2, 30, "F")
pdf.set_xy(X0 + 8, y + 9); pdf.set_font("DV", "B", 10); pdf.set_text_color(*METIN)
pdf.cell(0, 5.5, "What we are not", ln=1)
pdf.set_xy(X0 + 8, y + 16); pdf.set_font("DV", "", 8.8); pdf.set_text_color(60, 68, 82)
pdf.multi_cell(162, 5.0,
    "We are not a data feed and we do not claim to replace your existing providers. We are the "
    "human layer on top of them — covering the players and leagues they do not reach, and "
    "giving you a named opinion you can challenge.")

alt_bilgi(2)

# ══════════════════ SAYFA 3 — KAPSAMA + NASIL ÇALIŞIRIZ ══════════════════
pdf.add_page(); zemin()
marka_bandi(h=13, baslik="SCOUTING INTELLIGENCE · 2026-27")
bolum_basligi(20, "Coverage & how we work")

y = paragraf(34,
    "Our pool is deliberately weighted towards the markets where public data is weakest and "
    "where value is therefore highest. Alongside the traditional top divisions (England, "
    "Germany, Spain, Italy, France, USA), we maintain assessed profiles across Scandinavia, "
    "Central & Eastern Europe, the Balkans, Türkiye, the Gulf, North & West Africa, and Asia.",
    boy=9.4, satir=5.6, genislik=170)

y = madde(y + 4, "A fixed framework, applied by the same analysts",
    "Every player is assessed on 47 attributes across four groups — technical, mental, physical "
    "and personal — plus a dedicated 14-attribute set for goalkeepers. Because the framework "
    "and the assessors are constant, players from different continents remain directly "
    "comparable. Ratings are letter-graded and each carries a momentum indicator.")

y = madde(y, "Live, not archived",
    "Club, contract expiry, market value and playing status are refreshed continuously against "
    "primary sources. Assessments are revisited each season, so a two-year-old opinion is never "
    "presented to you as current.")

y = madde(y, "Delivery",
    "Web platform access (individual login per club), shareable single-player report links, and "
    "PDF shortlists produced to your brief. Working languages: English and Turkish.")

y = madde(y, "Engagement",
    "Season-long subscription for continuous access, or project-based work for a specific "
    "window or position. We are happy to start with one live brief so you can judge the output "
    "before committing.")

pdf.set_xy(X0, y + 6)
pdf.set_fill_color(*KOYU); pdf.rect(X0, y + 6, CW, 34, "F")
pdf.set_xy(X0 + 9, y + 12); pdf.set_font("DV", "B", 11); pdf.set_text_color(*LIME)
pdf.cell(0, 6, "Next step", ln=1)
pdf.set_xy(X0 + 9, y + 20); pdf.set_font("DV", "", 9); pdf.set_text_color(235, 238, 242)
pdf.multi_cell(162, 5.2,
    "Send us one real brief — the position you need to fill this window, your budget ceiling and "
    "your constraints. We will return a ranked shortlist with full assessments, at no cost, so "
    "you can measure our work against what you already have.")

pdf.set_xy(X0, y + 46); pdf.set_font("DV", "B", 9.6); pdf.set_text_color(*METIN)
pdf.cell(0, 5.6, "Yiğit Çelebi  ·  IDEAL Sports Management", ln=1)
pdf.set_x(X0); pdf.set_font("DV", "", 9); pdf.set_text_color(60, 68, 82)
pdf.cell(0, 5.4, "+90 506 578 46 43   ·   womensfootballscouting@gmail.com", ln=1)
pdf.set_x(X0)
pdf.cell(0, 5.4, "womenfootballscouting.com", ln=1,
         link="https://womenfootballscouting.com")

alt_bilgi(3)

cikti = pathlib.Path.home() / "Desktop" / "ISM_Scouting_Intelligence_2026.pdf"
pdf.output(str(cikti))
print(f"OK {cikti} ({cikti.stat().st_size // 1024} KB) · {N_TOPLAM} oyuncu / {N_DEGER} degerlendirilmis")
