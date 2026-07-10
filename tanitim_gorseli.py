# -*- coding: utf-8 -*-
"""Oyuncu tanıtım görseli (Instagram 1080x1350) — scout kartı şablonu.

Kullanım:
    python tanitim_gorseli.py "Naomi Girma"
    python tanitim_gorseli.py "Naomi Girma" "Sam Kerr"     # birden çok
Çıktı: Desktop\\tanitim_<isim>.png
"""
import json, os, re, sys, unicodedata, pathlib
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent
W, H = 1080, 1350

# ── Marka paleti ──
BG     = (15, 17, 23)
PANEL  = (18, 23, 43)
MOR    = (124, 58, 237)
MOR2   = (167, 139, 250)
WHITE  = (240, 244, 252)
MUTE   = (148, 163, 184)
GRAY   = (100, 112, 138)
CIZGI  = (38, 44, 69)

# Neon not skalası (siteyle aynı)
def not_renk(nt):
    S = ["EE","DE","DD","CD","CC","BC","BB","AB","AA","A+"]
    p = (S.index(nt) + 1) if nt in S else 0
    if p >= 9: return (31, 81, 255)     # AA-A+  neon mavi
    if p >= 7: return (57, 255, 20)     # BB-AB  neon yeşil
    if p >= 5: return (255, 240, 31)    # CC-BC  neon sarı
    if p >= 3: return (255, 95, 31)     # DD-CD  neon turuncu
    if p >= 1: return (255, 49, 49)     # EE-DE  neon kırmızı
    return (107, 114, 128)

SEGMAN = {"EE":1,"DE":2,"DD":3,"CD":4,"CC":5,"BC":6,"BB":7,"AB":8,"AA":9,"A+":10}

FD = r"C:\Windows\Fonts"
def f(name, size): return ImageFont.truetype(os.path.join(FD, name), size)
reg  = lambda s: f("arial.ttf", s)
bold = lambda s: f("arialbd.ttf", s)

# ── Radar eksenleri (siteyle aynı mantık) ──
RADAR_SAHA = [
    ("ATTACKING", "Hücum",      [("beceri","Bitiricilik"),("beceri","Uzaktan Şut"),("beceri","Kafa Vuruşu"),("beceri","Top Sürme")]),
    ("CREATIVITY", "Yaratıcılık",[("beceri","Kısa Pas"),("beceri","Orta Yapma"),("beceri","Duran Top"),("beseri","Görüş")]),
    ("DEFENDING", "Savunma",    [("beceri","Markaj"),("beceri","Top Kapma"),("beseri","Önsezi"),("beseri","Konumlanma")]),
    ("PHYSICAL", "Fiziksel",    [("fiziki","Sürat"),("fiziki","Hızlanma"),("fiziki","Güç"),("fiziki","Dayanıklılık"),("fiziki","Zıplama")]),
    ("MENTAL", "Mental",        [("beseri","Karar Alma"),("beseri","Soğukkanlılık"),("beseri","Konsantrasyon"),("beseri","Kararlılık")]),
    ("CHARACTER", "Karakter",   [("sahsi","Çalışkanlık"),("sahsi","Profesyonellik"),("sahsi","Süreklilik"),("sahsi","Baskıya Dayanıklılık")]),
]
RADAR_GK = [
    ("SHOT STOPPING", "Kurtarış",       [("kaleci","Çizgi Hakimiyeti"),("kaleci","Elle Kontrol - Sahiplenme")]),
    ("AERIAL / AREA", "Hava/Alan",      [("kaleci","Hava Hakimiyeti"),("kaleci","Yan Top Hakimiyeti"),("kaleci","Alan Hakimiyeti")]),
    ("FEET", "Ayakla Oyun",             [("kaleci","Ayak ile Oyun Kurma - Kısa"),("kaleci","Degaj ile Oyun Kurma - Uzun"),("kaleci","Ayakla Kontrol - İlk Temas")]),
    ("HANDS", "Elle Oyun",              [("kaleci","Elle Oyun Kurma"),("kaleci","Yumruklama Kabiliyeti")]),
    ("LEADERSHIP", "Liderlik",          [("kaleci","İletişim"),("beseri","Liderlik"),("beseri","Soğukkanlılık")]),
    ("ATHLETICISM", "Atletizm",         [("fiziki","Çeviklik"),("fiziki","Zıplama"),("fiziki","Sürat"),("fiziki","Güç")]),
]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z ]"," ", s)).strip()

def vektor(r):
    v = {}
    gruplar = ("kaleci","beseri","fiziki") if r.get("kaleci") else ("beceri","beseri","fiziki","sahsi")
    for g in gruplar:
        for a, nt in (r.get(g) or {}).items():
            if nt in SEGMAN: v[(g, a)] = SEGMAN[nt]
    return v

def eksen_deger(v, attrs):
    vals = [v[a] for a in attrs if a in v]
    return sum(vals)/len(vals) if len(vals) >= 2 else None

def yuzdelikler(d, isim):
    r = d[isim]; gk = bool(r.get("kaleci"))
    eksenler = RADAR_GK if gk else RADAR_SAHA
    havuz = [vektor(x) for x in d.values()
             if x.get("degerlendirildi") and bool(x.get("kaleci")) == gk]
    q = vektor(r)
    out = []
    for en, tr, attrs in eksenler:
        qd = eksen_deger(q, attrs)
        if qd is None: continue
        dag = [x for x in (eksen_deger(v, attrs) for v in havuz) if x is not None]
        pct = round(sum(1 for x in dag if x <= qd)/len(dag)*100) if dag else 0
        out.append((en, tr, pct))
    return out

def ciz(isim, d):
    anahtar = next((k for k in d if norm(k) == norm(isim)), None)
    if not anahtar:
        print(f"✗ '{isim}' havuzda yok"); return
    r = d[anahtar]
    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)

    # üst mor şerit + marka
    dr.rectangle([0, 0, W, 8], fill=MOR)
    dr.text((540, 64), "WOMEN'S FOOTBALL SCOUTING", font=bold(30), fill=MOR2, anchor="mm")
    dr.text((540, 104), "SCOUT REPORT · SCOUT RAPORU", font=reg(21), fill=GRAY, anchor="mm")

    # isim + künye (EN vurgu üstte)
    ad = anahtar.upper()
    dr.text((540, 196), ad, font=bold(66 if len(ad) <= 20 else 52), fill=WHITE, anchor="mm")
    mevki = " / ".join(r.get("mevki", [])) if isinstance(r.get("mevki"), list) else str(r.get("mevki") or "")
    kunye = " · ".join(x for x in [mevki, r.get("kulup",""), r.get("vatandaslik","")] if x)
    dr.text((540, 252), kunye, font=reg(27), fill=MUTE, anchor="mm")

    # nihai rozeti
    nihai = r.get("nihai","—"); nr = not_renk(nihai)
    cx, cy, rad = 540, 400, 92
    dr.ellipse([cx-rad, cy-rad, cx+rad, cy+rad], outline=nr, width=7)
    dr.text((cx, cy), nihai, font=bold(72), fill=nr, anchor="mm")
    dr.text((cx, cy+rad+28), "OVERALL · NİHAİ", font=bold(17), fill=GRAY, anchor="mm")

    # yüzdelik barları
    pcts = yuzdelikler(d, anahtar)
    y0 = 570
    dr.text((90, y0-46), "POOL PERCENTILE", font=bold(24), fill=MOR2, anchor="lm")
    dr.text((330, y0-46), "· havuz yüzdeliği", font=reg(20), fill=GRAY, anchor="lm")
    bar_x, bar_w, dy, bh = 400, 560, 74, 30
    for i, (en, tr, pct) in enumerate(pcts):
        y = y0 + i*dy
        dr.text((bar_x-18, y+bh//2-9), en, font=bold(23), fill=WHITE, anchor="rm")
        dr.text((bar_x-18, y+bh//2+16), tr, font=reg(17), fill=GRAY, anchor="rm")
        dr.rounded_rectangle([bar_x, y, bar_x+bar_w, y+bh], radius=7, fill=(30, 37, 64))
        bw = max(12, int(bar_w*pct/100))
        c = (57,255,20) if pct >= 85 else (MOR2 if pct >= 55 else (255,95,31) if pct >= 30 else (255,49,49))
        dr.rounded_rectangle([bar_x, y, bar_x+bw, y+bh], radius=7, fill=c)
        dr.text((bar_x+bar_w+16, y+bh//2), str(pct), font=bold(24), fill=c, anchor="lm")

    # oyun tarzı çipleri (varsa, ilk 3)
    tarz = r.get("tarz") or []
    if tarz:
        ty = y0 + len(pcts)*dy + 40
        dr.text((90, ty), "PLAY STYLE · OYUN TARZI", font=bold(20), fill=MOR2, anchor="lm")
        tx, ty2 = 90, ty + 34
        for oz in tarz[:3]:
            etiket = str(oz).split(" / ")[0].strip()
            tw = dr.textlength(etiket, font=reg(21))
            if tx + tw + 36 > W - 90: break
            dr.rounded_rectangle([tx, ty2, tx+tw+32, ty2+42], radius=21, outline=CIZGI, width=2)
            dr.text((tx+16+tw/2, ty2+21), etiket, font=reg(21), fill=MUTE, anchor="mm")
            tx += tw + 46

    # alt bant
    dr.rectangle([0, H-8, W, H], fill=MOR)
    dr.text((540, H-64), "womenfootballscouting.com", font=bold(26), fill=MOR2, anchor="mm")
    dr.text((540, H-30), "@idealsportsmanagement", font=reg(19), fill=GRAY, anchor="mm")

    out = os.path.join(os.path.expanduser("~"), "Desktop",
                       f"tanitim_{norm(anahtar).replace(' ','_')}.png")
    img.save(out, "PNG")
    print(f"✓ {anahtar} -> {out}")

if __name__ == "__main__":
    isimler = sys.argv[1:]
    if not isimler:
        print(__doc__); sys.exit(0)
    d = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
    for i in isimler:
        ciz(i, d)
