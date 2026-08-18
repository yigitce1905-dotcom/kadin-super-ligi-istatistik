# -*- coding: utf-8 -*-
"""Oyuncu Yetkinlik Kartı üretici — scout verisinden veri çeker, HTML şablonu doldurur, PNG basar.
Kullanım:  python kart_uret.py "Trinity Rodman"
"""
import sys, os, re, json, subprocess, pathlib

sys.stdout.reconfigure(encoding="utf-8")
DIR = pathlib.Path(__file__).resolve().parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# ── AA→FF harf skalası → 1-10 ──
SC = {"AA":10,"A+":10,"AB":9,"BB":8,"BC":7,"CC":6,"CD":5,"DD":4,"DE":3,"EE":2,"EF":1,"FF":1}

def puan(grup, keys):
    vals = [SC[grup[k]] for k in keys if grup.get(k) in SC]
    return max(1, min(10, round(sum(vals)/len(vals)))) if vals else 1

# ── 6 KRİTER EŞLEŞMESİ ──
OUTFIELD = [
    ("Finishing & Attack",     [("beceri",["Bitiricilik","Uzaktan Şut","Kafa Vuruşu","Penaltı Vuruşu"])]),
    ("Playmaking & Vision",    [("beceri",["Kısa Pas","Uzun Pas"]),("beseri",["Görüş","Karar Alma"])]),
    ("Technique & Dribbling",  [("beceri",["Top Tekniği","Top Sürme","İlk Kontrol","Orta Yapma"])]),
    ("Defending & Duels",      [("beceri",["Markaj","Top Kapma"]),("beseri",["Önsezi","Konumlanma","Agresiflik"])]),
    ("Athleticism & Power",    [("fiziki",["Güç","Sürat","Hızlanma","Zıplama","Dayanıklılık","Çeviklik"])]),
    ("Mentality & Character",  [("beseri",["Kararlılık","Konsantrasyon","Liderlik","Soğukkanlılık","Takım Oyunu"]),("sahsi",["Çalışkanlık"])]),
]
KALECI = [
    ("Regional Domination",  [("kaleci",["Alan Hakimiyeti","Kaleden Ani Çıkış"])]),
    ("Goal-Line Domination", [("kaleci",["Çizgi Hakimiyeti","Elle Kontrol - Sahiplenme"])]),
    ("Aerial Domination",    [("kaleci",["Hava Hakimiyeti","Yumruklama Kabiliyeti"])]),
    ("Build-up Play",        [("kaleci",["Ayak ile Oyun Kurma - Kısa","Degaj ile Oyun Kurma - Uzun","Elle Oyun Kurma"])]),
    ("Ball Technique",       [("kaleci",["Top Tekniği","Ayakla Kontrol - İlk Temas"])]),
    ("Reflexes & Power",     [("kaleci",["Yan Top Hakimiyeti"]),("fiziki",["Güç","Çeviklik","Zıplama"])]),
]

def kriter_hesapla(v, kaleci_mi):
    plan = KALECI if kaleci_mi else OUTFIELD
    bars = []
    for etiket, parcalar in plan:
        vals = []
        for grup_ad, keys in parcalar:
            g = v.get(grup_ad) or {}
            vals += [SC[g[k]] for k in keys if g.get(k) in SC]
        skor = max(1, min(10, round(sum(vals)/len(vals)))) if vals else 1
        bars.append([etiket, skor])
    return bars

def ivme_yon(s):
    s = str(s or "")
    if any(c in s for c in "⬈↗⬀"): return "up"
    if any(c in s for c in "⬊↘⬂"): return "down"
    return "flat"

def veri_hazirla(isim):
    d = json.load(open(DIR/"scout_kadro_raporlar.json", encoding="utf-8"))
    if isim not in d:
        # esnek arama
        aday = [k for k in d if k.lower() == isim.lower()] or [k for k in d if isim.lower() in k.lower()]
        if not aday: sys.exit(f"Bulunamadı: {isim}")
        isim = aday[0]
    v = d[isim]
    kaleci_mi = bool(v.get("kaleci") and any(v["kaleci"].values()))
    mev = v.get("mevki") or []
    pos = (mev[0] if isinstance(mev, list) and mev else str(mev)) or ""
    yil = (v.get("dogum") or "")[-4:]
    boy = (v.get("boy") or "").replace(",", ".")
    boy = f"{boy}m" if boy else ""
    meta = " | ".join(x for x in [yil, pos, boy, v.get("vucut_tipi") or ""] if x)
    return {
        "name": isim,
        "club": v.get("kulup") or "", "nationality": v.get("vatandaslik") or "",
        "meta": meta,
        "grade": v.get("nihai") or "-",
        "trend": ivme_yon(v.get("ivme")),
        "photo": None,
        "scout": "Mehmet Baran Daniş",
        "bars": kriter_hesapla(v, kaleci_mi),
    }

def html_uret(data, sablon=DIR/"kart_sablon.html"):
    html = sablon.read_text(encoding="utf-8")
    # meta doğrudan hazır string; şablon meta'yı parçalardan kuruyordu → sadeleştir
    data_js = dict(data)
    js = json.dumps(data_js, ensure_ascii=False, indent=2)
    html = re.sub(r"const DATA = \{.*?\};", "const DATA = " + js + ";", html, flags=re.DOTALL)
    # şablon meta'yı [year,pos,height,body]'den kuruyor; biz hazır 'meta' verdik → onu kullan
    html = html.replace(
        '[d.year,d.pos,d.height,d.body].filter(Boolean).join("  |  ")',
        'd.meta')
    return html

def main():
    isim = sys.argv[1] if len(sys.argv) > 1 else "Trinity Rodman"
    data = veri_hazirla(isim)
    print("KRİTER PUANLARI:", {b[0]: b[1] for b in data["bars"]})
    print("nihai:", data["grade"], "| ivme:", data["trend"], "| meta:", data["meta"])
    slug = re.sub(r"[^a-z0-9]+", "_", isim.lower()).strip("_")
    html_yol = DIR / f"kart_{slug}.html"
    png_yol  = pathlib.Path.home() / "Desktop" / f"Kart_{slug}.png"
    html_yol.write_text(html_uret(data), encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--window-size=1080,1080",
                    "--virtual-time-budget=5000", "--default-background-color=00000000",
                    f"--screenshot={png_yol}", f"file:///{html_yol.as_posix()}"],
                   check=False, capture_output=True)
    print(f"OK → {png_yol} ({png_yol.stat().st_size//1024} KB)")

if __name__ == "__main__":
    main()
