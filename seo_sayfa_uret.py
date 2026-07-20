# -*- coding: utf-8 -*-
"""SEO PUBLIC OYUNCU SAYFALARI — statik HTML üretici.

Streamlit WebSocket içeriğini Google indeksleyemediği için oyuncu profillerinin
hafif, statik, indekslenebilir kopyaları üretilir → Cloudflare Pages'te
oyuncu.womenfootballscouting.com altında yayınlanır (ücretsiz).

İçerik SINIRI: yalnız public veri (künye + sezon istatistiği + kariyer).
Scout notu/nitelikler SIZDIRILMAZ — "rapor mevcut" rozeti + üye ol CTA'sı.

Kullanım:  python seo_sayfa_uret.py     → seo_site/ (gitignore'lu çıktı)
Deploy:    npx wrangler pages deploy seo_site --project-name wfs-oyuncu
"""
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
CIKTI = KOK / "seo_site"

ANA_SITE = "https://womenfootballscouting.com"
# Ana domain altında path (SEO otoritesi tek domainde birleşir);
# Worker route womenfootballscouting.com/oyuncu* → wfs-oyuncu.pages.dev proxy'ler.
SEO_KOK = "https://womenfootballscouting.com/oyuncu"

oyuncular = json.load(open(KOK / "oyuncular.json", encoding="utf-8"))
sd = json.load(open(KOK / "soccerdonna_profiller.json", encoding="utf-8"))
kariyer = json.load(open(KOK / "analig_leistungsdaten.json", encoding="utf-8"))
try:
    scotr = json.load(open(KOK / "scotr_raporlar.json", encoding="utf-8"))
except Exception:
    scotr = {}

def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "oyuncu"

def _e(s) -> str:
    return html.escape(str(s or ""))

_MEVKI_TR = {  # SD İngilizce mevki → TR görünüm
    "Goalkeeper": "Kaleci", "Defender - Right Back": "Sağ Bek",
    "Defender - Left Back": "Sol Bek", "Defender - Centre Back": "Stoper",
    "Defence": "Defans", "Midfield - Defensive Midfield": "Savunmacı Orta Saha",
    "Midfield - Central Midfield": "Merkez Orta Saha",
    "Midfield - Attacking Midfield": "Hücumcu Orta Saha",
    "Midfield - Left Wing": "Sol Kanat", "Midfield - Right Wing": "Sağ Kanat",
    "Midfield": "Orta Saha", "Striker - Left Wing": "Sol Kanat Forvet",
    "Striker - Right Wing": "Sağ Kanat Forvet",
    "Striker - Centre Forward": "Santrafor", "Striker": "Forvet",
}

def _takim_kisa(ad: str) -> str:
    """app.py'deki kısaltmanın hafif kopyası (üretici bağımsız kalsın)."""
    up = (ad or "").upper()
    for sub, kisa in [("BEŞİKTAŞ", "Beşiktaş"), ("GALATASARAY", "Galatasaray"),
                      ("FENERBAHÇE", "Fenerbahçe"), ("TRABZONSPOR", "Trabzonspor"),
                      ("FOMGET", "FOMGET"), ("AMED", "Amed"), ("YÜKSEKOVA", "Yüksekovaspor"),
                      ("HAKKARİ", "Hakkarigücü"), ("ÜNYE", "Ünye"), ("GİRESUN", "Giresun Sanayi"),
                      ("FATİH VATAN", "Fatih Vatan"), ("ÇEKMEKÖY", "Çekmeköy Bilgidoğa"),
                      ("BİLGİDOĞA", "Şile Bilgidoğa"), ("1207", "1207 Antalya"),
                      ("BEYLERBEYİ", "Beylerbeyi"), ("BORNOVA", "Bornova Hitab"), ("ALG", "ALG")]:
        if sub in up:
            return kisa
    for bp in [" SPORTİF YATIRIM HİZMETLERİ A.Ş", " SPORTİF FAALİYETLER",
               " KADIN FUTBOL SPOR KULÜBÜ", " KADIN FUTBOL KULÜBÜ", " KADIN FUTBOL TAKIMI",
               " KADIN SPOR KULÜBÜ", " GENÇLİK VE SPOR", " FUTBOL KULÜBÜ",
               " SPOR KULÜBÜ", " KULÜBÜ", " A.Ş.", " A.Ş"]:
        ad = (ad or "").replace(bp, "").replace(bp.title(), "")
    return " ".join((ad or "").split()).strip(" -·")

STIL = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b0e1a;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;line-height:1.55}
a{color:#a78bfa;text-decoration:none}
.sarici{max-width:860px;margin:0 auto;padding:20px 16px 40px}
.marka{display:flex;justify-content:space-between;align-items:center;padding:10px 0 18px;
 border-bottom:1px solid #1e2340;margin-bottom:22px;flex-wrap:wrap;gap:8px}
.marka .logo{font-weight:800;font-size:1.02rem;color:#f1f5f9;letter-spacing:0.02em}
.marka .logo span{color:#a78bfa}
.isim{font-size:1.7rem;font-weight:800;color:#a78bfa;text-transform:uppercase;line-height:1.15}
.altsatir{color:#8899aa;font-size:0.92rem;margin:4px 0 18px}
.kutular{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:20px}
.kutu{background:#101829;border:1px solid #243149;border-radius:11px;padding:12px 14px}
.kutu .et{color:#a78bfa;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em}
.kutu .dg{color:#f1f5f9;font-size:1.02rem;font-weight:600;margin-top:3px}
.blokbaslik{color:#a78bfa;font-weight:700;font-size:0.95rem;text-transform:uppercase;
 letter-spacing:0.05em;margin:22px 0 8px}
.statlar{display:flex;gap:12px;flex-wrap:wrap}
.stat{background:#101829;border:1px solid #243149;border-radius:11px;padding:12px 18px;
 text-align:center;min-width:86px}
.stat b{display:block;font-size:1.45rem;color:#1db954;font-weight:800}
.stat i{font-style:normal;color:#8899aa;font-size:0.72rem}
table{width:100%;border-collapse:collapse;font-size:0.85rem;background:#101829;
 border:1px solid #243149;border-radius:11px;overflow:hidden}
th{background:#0d1220;color:#8899aa;text-transform:uppercase;font-size:0.68rem;
 letter-spacing:0.08em;padding:8px 10px;text-align:left}
td{padding:7px 10px;border-top:1px solid #1a2138;color:#d7dde8}
td.num,th.num{text-align:right}
.rozet{display:inline-block;background:#1e1338;border:1px solid #7c3aed;color:#c4b5fd;
 border-radius:8px;padding:6px 14px;font-size:0.82rem;font-weight:600;margin:14px 0}
.cta{display:block;text-align:center;background:linear-gradient(135deg,#7c3aed,#db2777);
 color:#fff;font-weight:700;border-radius:11px;padding:14px;margin:24px 0 8px;font-size:0.95rem}
.altbilgi{color:#566179;font-size:0.74rem;text-align:center;margin-top:26px;
 padding-top:14px;border-top:1px solid #1e2340}
.oyliste{columns:2;column-gap:24px;font-size:0.9rem}
.oyliste a{display:block;padding:3px 0;border-bottom:1px solid #141a2e}
.takimbas{column-span:all;color:#1db954;font-weight:700;margin:16px 0 6px;font-size:0.95rem}
@media(max-width:600px){.oyliste{columns:1}.isim{font-size:1.35rem}}
"""

def _sayfa(baslik, aciklama, kanonik, govde, jsonld=""):
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(baslik)}</title>
<meta name="description" content="{_e(aciklama)}">
<link rel="canonical" href="{kanonik}">
<meta property="og:title" content="{_e(baslik)}">
<meta property="og:description" content="{_e(aciklama)}">
<meta property="og:type" content="profile">
<meta property="og:url" content="{kanonik}">
<meta property="og:site_name" content="Women's Football Scouting">
<meta name="robots" content="index,follow">
{jsonld}
<style>{STIL}</style>
</head>
<body><div class="sarici">
<div class="marka">
 <div class="logo">WOMEN'S FOOTBALL <span>SCOUTING</span></div>
 <a href="{ANA_SITE}">womenfootballscouting.com →</a>
</div>
{govde}
<div class="altbilgi">Veri: TFF &amp; SoccerDonna · {date.today().year} © Women's Football Scouting ·
 <a href="{ANA_SITE}">Tüm istatistikler ve scout raporları için üye olun</a></div>
</div></body></html>"""

def oyuncu_sayfasi(o, slug):
    isim = o["oyuncu"]
    p = sd.get(isim, {}) or {}
    takim = _takim_kisa(o.get("tum_takimlar") or o.get("takim") or "")
    mevki = _MEVKI_TR.get((p.get("Position") or "").strip(), (p.get("Position") or "").strip())
    mac, gol = o.get("mac_sayisi", 0), o.get("gol_sayisi", 0)
    dk = o.get("toplam_dakika", 0)
    kunye = [("Takım", takim), ("Mevki", mevki),
             ("Doğum", (p.get("Date of birth") or "").strip()),
             ("Yaş", str(p.get("Age") or "").split()[0] if p.get("Age") else ""),
             ("Uyruk", (p.get("Nationality") or "").strip()),
             ("Boy", (p.get("Height") or "").strip()),
             ("Ayak", (p.get("Foot") or "").strip().capitalize())]
    kutular = "".join(
        f"<div class='kutu'><div class='et'>{_e(et)}</div><div class='dg'>{_e(dg)}</div></div>"
        for et, dg in kunye if str(dg).strip())
    statlar = "".join(
        f"<div class='stat'><b>{v}</b><i>{e}</i></div>"
        for v, e in [(mac, "Maç"), (gol, "Gol"), (o.get("ilk11_mac", 0), "İlk 11"),
                     (dk, "Dakika"), (o.get("sari_kart", 0), "Sarı Kart")])
    # kariyer (kulüp satırları; milli ayrı)
    kry = kariyer.get(isim, {}).get("sezonlar", [])
    kulup_s = [s for s in kry if not s.get("milli")][:10]
    milli_s = [s for s in kry if s.get("milli")][:6]
    def _tbl(rows, kolon):
        if not rows:
            return ""
        tr = "".join(
            f"<tr><td>{_e(s.get('sezon',''))}</td><td>{_e(_takim_kisa(s.get('kulup','')))}</td>"
            f"<td>{_e(s.get('lig',''))}</td><td class='num'>{s.get('mac',0)}</td>"
            f"<td class='num'>{s.get('gol',0)}</td><td class='num'>{s.get('dakika',0)}</td></tr>"
            for s in rows)
        return (f"<table><tr><th>Sezon</th><th>{kolon}</th><th>Lig</th>"
                f"<th class='num'>Maç</th><th class='num'>Gol</th><th class='num'>Dk</th></tr>{tr}</table>")
    kry_html = ""
    if kulup_s:
        kry_html += f"<div class='blokbaslik'>Kulüp Kariyeri</div>{_tbl(kulup_s,'Kulüp')}"
    if milli_s:
        kry_html += f"<div class='blokbaslik'>Milli Takım</div>{_tbl(milli_s,'Takım')}"
    rozet = ("<div class='rozet'>🔬 Bu oyuncu için detaylı scout raporu mevcut</div>"
             if scotr.get(isim, {}).get("degerlendirildi") else "")
    aciklama = (f"{isim} — {takim} · {mevki or 'Kadın Futbol Süper Ligi oyuncusu'}. "
                f"2025-26 sezonu: {mac} maç, {gol} gol. İstatistikler, kariyer ve scout raporu.")
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Person", "name": isim,
        "url": f"{SEO_KOK}/{slug}",
        "jobTitle": "Professional footballer",
        "affiliation": {"@type": "SportsTeam", "name": takim,
                        "sport": "Football",
                        "memberOf": {"@type": "SportsOrganization",
                                     "name": "Turkish Women's Football Super League"}},
        "nationality": (p.get("Nationality") or "").strip() or "Turkey",
    }, ensure_ascii=False)
    govde = f"""
<h1 class="isim">{_e(isim)}</h1>
<div class="altsatir">{_e(takim)}{(' · ' + _e(mevki)) if mevki else ''} · Kadın Futbol Süper Ligi 2025-26</div>
<div class="kutular">{kutular}</div>
<div class="blokbaslik">2025-26 Sezon İstatistikleri</div>
<div class="statlar">{statlar}</div>
{kry_html}
{rozet}
<a class="cta" href="{ANA_SITE}/?oyuncu={_e(isim).replace(' ', '%20')}">
 📊 Detaylı profil · percentile · scout raporu — womenfootballscouting.com</a>"""
    baslik = f"{isim} — {takim} | İstatistik & Scout Profili"
    return _sayfa(baslik, aciklama, f"{SEO_KOK}/{slug}", govde,
                  f'<script type="application/ld+json">{jsonld}</script>')

def main():
    CIKTI.mkdir(exist_ok=True)
    for eski in CIKTI.glob("*.html"):
        eski.unlink()
    slugs = {}
    for o in oyuncular:
        s = _slug(o["oyuncu"])
        while s in slugs:            # çakışan isim → sonek
            s += "-2"
        slugs[s] = o
    for s, o in slugs.items():
        (CIKTI / f"{s}.html").write_text(oyuncu_sayfasi(o, s), encoding="utf-8")

    # index: takıma göre gruplu tam liste
    gruplar = {}
    for s, o in slugs.items():
        gruplar.setdefault(_takim_kisa(o.get("takim", "")) or "Diğer", []).append((s, o["oyuncu"]))
    liste = ""
    for takim in sorted(gruplar):
        liste += f"<div class='takimbas'>{_e(takim)}</div>"
        for s, ad in sorted(gruplar[takim], key=lambda x: x[1]):
            liste += f"<a href='/oyuncu/{s}'>{_e(ad)}</a>"
    govde = f"""
<h1 class="isim">Kadın Futbol Süper Ligi Oyuncuları</h1>
<div class="altsatir">2025-26 sezonu · {len(slugs)} oyuncu · istatistik, kariyer ve scout profilleri</div>
<div class="oyliste">{liste}</div>
<a class="cta" href="{ANA_SITE}">📊 Karşılaştırma · percentile · scouting havuzu — womenfootballscouting.com</a>"""
    (CIKTI / "index.html").write_text(
        _sayfa("Kadın Futbol Süper Ligi Oyuncuları — İstatistik & Scout Profilleri",
               f"Türkiye Kadın Futbol Süper Ligi {len(slugs)} oyuncunun istatistik, kariyer ve scout profilleri.",
               f"{SEO_KOK}/", govde), encoding="utf-8")

    # sitemap + robots
    bugun = date.today().isoformat()
    urls = "".join(f"<url><loc>{SEO_KOK}/{s}</loc><lastmod>{bugun}</lastmod></url>"
                   for s in slugs)
    (CIKTI / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{SEO_KOK}/</loc><lastmod>{bugun}</lastmod></url>{urls}</urlset>",
        encoding="utf-8")
    (CIKTI / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SEO_KOK}/sitemap.xml\n", encoding="utf-8")
    print(f"[OK] {len(slugs)} oyuncu sayfası + index + sitemap → {CIKTI}")

if __name__ == "__main__":
    main()
