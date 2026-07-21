# -*- coding: utf-8 -*-
"""KULÜP KOKPİTİ (2026-27) — SoccerDonna kadro çekici.

Verilen SD kulüp sayfalarından güncel kadroyu çeker (isim, mevki kodu, yaş,
uyruk, piyasa değeri, profil URL) ve elimizdeki SD profil JSON'larından
sözleşme/boy ile zenginleştirir → kokpit_kadrolar.json

Kullanım:  python kokpit_sd_cek.py
Yeni kulüp eklemek: KULUPLER sözlüğüne (ad, url) ekle, tekrar çalıştır.
"""
import json, re, sys, time, unicodedata
from datetime import date
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 2026-27 sezonu — 16 kulüp (ALG yok; Beylerbeyi/Bornova Süper Lig'de değil)
# FB/GS/BJK/FOMGET yeni SD kayıtları; diğerleri eski verein ID'leriyle (SD yönlendirir)
KULUPLER = {
    "Fenerbahçe":     "https://www.soccerdonna.de/en/fenerbahce-sk/startseite/verein_9522.html",
    "Galatasaray":    "https://www.soccerdonna.de/en/galatasaray-sk/startseite/verein_9537.html",
    "Beşiktaş":       "https://www.soccerdonna.de/en/besiktas-jk/startseite/verein_6981.html",
    "Trabzonspor":    "https://www.soccerdonna.de/en/trabzonspor/startseite/verein_792.html",
    "FOMGET":         "https://www.soccerdonna.de/en/abb-fomget-sk/startseite/verein_7247.html",
    "Amed":           "https://www.soccerdonna.de/en/amed-sfk/startseite/verein_7245.html",
    "Fatih Vatan":    "https://www.soccerdonna.de/en/fatih-vatan-sk/startseite/verein_7246.html",
    "Hakkarigücü":    "https://www.soccerdonna.de/en/hakkariguecue-sk/startseite/verein_7066.html",
    "Ünye":           "https://www.soccerdonna.de/en/uenye-guecue-fk/startseite/verein_13095.html",
    "Giresun Sanayi": "https://www.soccerdonna.de/en/giresun-sanayi-sk/startseite/verein_14056.html",
    "1207 Antalya":   "https://www.soccerdonna.de/en/1207-antalyaspor/startseite/verein_7352.html",
    "Yüksekovaspor":  "https://www.soccerdonna.de/en/yuksekova-sk/startseite/verein_15697.html",
    "Şile Bilgidoğa": "https://www.soccerdonna.de/en/bilgi-doga-sk/startseite/verein_15914.html",
    "Haymana":        "https://www.soccerdonna.de/en/haymanaspor/startseite/verein_16154.html",
    "Bakırköy Yenimahalle": "https://www.soccerdonna.de/en/bakirkoy-kadin-futbol-sk/startseite/verein_14028.html",
    "Kayserispor":    "https://www.soccerdonna.de/en/kayseri-kadin-fk/startseite/verein_7356.html",
}

# SD mevki kodu → saha grubu (kokpit yerleşimi)
# Baran standardı: TÜM gruplar İSİM (numara/kod karışımı yok)
KOD_GRUP = {
    "TW": "KALECİ", "IV": "STOPER", "LV": "SOL BEK", "RV": "SAĞ BEK",
    "DM": "SAVUNMACI ORTA SAHA", "ZM": "MERKEZ ORTA SAHA", "OM": "HÜCUMCU ORTA SAHA",
    "LM": "SOL KANAT", "LA": "SOL KANAT",
    "RM": "SAĞ KANAT", "RA": "SAĞ KANAT",
    "MS": "SANTRFOR",
}

def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())

def _deger_eur(s: str):
    """'€ 100 Th.' / '€ 1,50 mil.' → int EUR; yoksa None."""
    if not s or "€" not in s:
        return None
    m = re.search(r"€?\s*([\d.,]+)\s*(mil|Th)?", s.replace("€", "€ "))
    if not m:
        return None
    sayi = float(m.group(1).replace(".", "").replace(",", "."))
    birim = (m.group(2) or "").lower()
    if birim == "mil":
        return int(sayi * 1_000_000)
    if birim == "th":
        return int(sayi * 1_000)
    return int(sayi)

def arma_indir(url: str, kulup_ad: str) -> str:
    """Kulüp armasını indirir (SD: /static/bilder_sd/mediumfotos/<verein_id>.jpg).
    static/armalar/<slug>.jpg olarak kaydeder; dosya adını döndürür ('' = yok)."""
    m = re.search(r"verein_(\d+)", url)
    if not m:
        return ""
    src = f"https://www.soccerdonna.de/static/bilder_sd/mediumfotos/{m.group(1)}.jpg"
    slug = unicodedata.normalize("NFKD", kulup_ad).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    hedef = KOK / "static" / "armalar" / f"{slug}.jpg"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    try:
        veri = requests.get(src, headers=H, timeout=15).content
        if len(veri) > 500:
            hedef.write_bytes(veri)
            return f"armalar/{slug}.jpg"
    except Exception:
        pass
    return ""


def kadro_cek(url: str, kulup_ad: str = "") -> tuple:
    r = requests.get(url, headers=H, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    arma = arma_indir(url, kulup_ad) if kulup_ad else ""
    kadro, gorulen = [], set()
    for tr in soup.select("table tr"):
        a = tr.select_one("a[href*='/profil/spieler_']")
        if not a:
            continue
        isim = a.get_text(" ", strip=True)
        if not isim or isim in gorulen:
            continue
        satir = tr.get_text(" ", strip=True)
        mkod = ""
        mk = re.search(r"\(\s*(TW|RV|LV|IV|DM|ZM|OM|LM|RM|LA|RA|MS)\s*\)", satir)
        if mk:
            mkod = mk.group(1)
        # yaş: satırdaki bağımsız 14-45 arası sayı (forma no ile karışmasın diye sondan ara)
        yas = ""
        for tok in reversed(re.findall(r"\b(\d{2})\b", satir)):
            if 14 <= int(tok) <= 45:
                yas = tok
                break
        # uyruk: yalnız bayrak img'leri (src'de /flaggen/; ülke adı alt'ta temiz)
        uyruk = " / ".join(dict.fromkeys(
            img.get("alt", "") for img in tr.find_all("img")
            if "/flaggen/" in (img.get("src") or "") and img.get("alt")))
        # değer: € içeren hücre
        deger = ""
        for td in tr.find_all("td"):
            t = td.get_text(" ", strip=True)
            if "€" in t:
                deger = t
                break
        gorulen.add(isim)
        kadro.append({
            "isim": isim, "kod": mkod, "grup": KOD_GRUP.get(mkod, "DİĞER"),
            "yas": yas, "uyruk": uyruk, "deger": deger,
            "deger_eur": _deger_eur(deger),
            "profil_url": "https://www.soccerdonna.de" + a["href"]
                          if a["href"].startswith("/") else a["href"],
        })
    return kadro, arma

def zenginlestir(kadro: list) -> int:
    """Elimizdeki SD profillerinden sözleşme/boy ekle (isim-norm eşleşmesi)."""
    sd = {}
    for dosya in ("soccerdonna_profiller.json", "scouting_sd_profiller.json"):
        yol = KOK / dosya
        if yol.exists():
            sd.update(json.load(open(yol, encoding="utf-8")))
    sd_norm = {_norm(k): v for k, v in sd.items()}
    n = 0
    for o in kadro:
        p = sd_norm.get(_norm(o["isim"]))
        if isinstance(p, dict) and not p.get("bulunamadi"):
            o["sozlesme"] = (p.get("Contract until") or "").strip()
            o["boy"] = (p.get("Height") or "").strip()
            n += 1
        else:
            o["sozlesme"] = ""
            o["boy"] = ""
    return n

def main():
    yol = KOK / "kokpit_kadrolar.json"
    eski = json.load(open(yol, encoding="utf-8")) if yol.exists() else {"kulupler": {}}
    eski["sezon"] = "2026-27"
    for ad, url in KULUPLER.items():
        print(f"── {ad} çekiliyor…")
        time.sleep(0.4)
        kadro, arma = kadro_cek(url, ad)
        z = zenginlestir(kadro)
        # Arma boş dönerse (SD'de yok — Bakırköy/Haymana gibi elle eklenenler)
        # ESKİ armayı KORU; boşla ezme.
        if not arma:
            arma = (eski.get("kulupler", {}).get(ad, {}) or {}).get("arma", "")
        eski["kulupler"][ad] = {
            "sd_url": url, "cekilis": date.today().isoformat(),
            "arma": arma, "kadro": kadro}
        toplam = sum(o["deger_eur"] or 0 for o in kadro)
        print(f"   {len(kadro)} oyuncu · sözleşme/boy eşleşen: {z} · toplam değer ~€{toplam:,}")
    json.dump(eski, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[OK] {yol.name} yazıldı.")

if __name__ == "__main__":
    main()
