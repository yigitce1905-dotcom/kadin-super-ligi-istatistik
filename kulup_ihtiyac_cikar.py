"""Bir kulübün SoccerDonna kadrosundan 'fırsat alanları' çıkarır ve kulup_ihtiyac.json'a yazar.

Kulübe özel sayfa (?kulup=<anahtar>) bu dosyayı okur. Buradaki 'ihtiyaç' kulübün bize söylediği
bir şey DEĞİL — herkese açık kadro verisinden (mevki derinliği, sözleşme bitişi, yaş) çıkan
yorumdur; sayfada da öyle sunulur ("kadro verinize göre öne çıkan bölgeler").

Kullanım:
    python kulup_ihtiyac_cikar.py <anahtar> "<Kulüp adı>" <soccerdonna verein id> [--yaz]
    python kulup_ihtiyac_cikar.py sc-freiburg "SC Freiburg" 292 --yaz
--yaz verilmezse yalnız raporlar (dosyaya dokunmaz).
"""
import datetime
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}
BUGUN = datetime.date.today()
SEZON_SONU = datetime.date(BUGUN.year + (1 if BUGUN.month >= 7 else 0), 6, 30)

# SoccerDonna 'Position' metni → (bölge anahtarı, TR ad, EN ad, havuz mevki kodları, ideal derinlik)
BOLGELER = [
    ("gk", "Kaleci", "Goalkeeper", ["GK"], 3, ("goalkeeper",)),
    ("cb", "Stoper", "Centre-back", ["RCB", "MCB", "LCB"], 4, ("centre back", "central defence", "sweeper")),
    ("lb", "Sol bek", "Left-back", ["LFB", "LWB"], 2, ("left back", "left wing back")),
    ("rb", "Sağ bek", "Right-back", ["RFB", "RWB"], 2, ("right back", "right wing back")),
    ("dm", "Ön libero", "Defensive midfielder", ["DMF"], 2, ("defensive midfield",)),
    ("cm", "Merkez orta saha", "Central midfielder", ["CMF"], 3, ("central midfield",)),
    ("am", "Ofansif orta saha", "Attacking midfielder", ["AMF"], 2, ("attacking midfield",)),
    ("lw", "Sol kanat", "Left winger", ["LWF"], 2, ("left wing", "left midfield")),
    ("rw", "Sağ kanat", "Right winger", ["RWF"], 2, ("right wing", "right midfield")),
    ("st", "Santrfor", "Centre-forward", ["CFW", "2ST"], 3, ("centre forward", "striker", "second striker", "forward")),
]


def getir(url):
    for deneme in range(3):
        try:
            r = requests.get(url, headers=H, timeout=20)
            r.raise_for_status()
            time.sleep(0.7)
            return r.text
        except Exception:
            time.sleep(3 * (deneme + 1))
    return ""


def kadro(verein_id):
    html = getir(f"https://www.soccerdonna.de/en/x/kader/verein_{verein_id}.html")
    soup = BeautifulSoup(html, "html.parser")
    out, gorulen = [], set()
    for a in soup.select("a[href*='/profil/spieler_']"):
        ad = a.get_text(" ", strip=True)
        href = a["href"]
        if not ad or href in gorulen:
            continue
        gorulen.add(href)
        out.append({"isim": ad, "url": "https://www.soccerdonna.de" + href if href.startswith("/") else href})
    return out


def profil(url):
    soup = BeautifulSoup(getir(url), "html.parser")
    out = {}
    for row in soup.select("table tr"):
        c = [x.get_text(" ", strip=True) for x in row.select("td")]
        if len(c) >= 2 and c[0]:
            k = c[0].rstrip(":")
            if k in ("Position", "Contract until", "Age", "Market value", "Foot", "Height") and k not in out:
                out[k] = c[1]
    return out


def bolge_bul(pozisyon):
    """Yalnız AYRINTILI mevki yazıyorsa bölge döner ('Defence - Centre Back' → cb).
    SoccerDonna oyuncuların yarısında yalnız hattı yazar ('Defence', 'Midfield', 'Striker');
    onları bir bölgeye saymak yanlış sonuç verir (12 Kasım 2026: Freiburg'da 'sıfır bek' çıktı,
    oysa bekler 'Defence' olarak kayıtlıydı) → '' döner, hiçbir bölgeye sayılmazlar."""
    p = (pozisyon or "").lower()
    if "goalkeeper" in p:
        return "gk"
    if "-" not in p:
        return ""
    alt = p.split("-", 1)[1].strip()
    if not alt:
        return ""
    if "fullback, left" in alt:
        return "lb"
    if "fullback, right" in alt:
        return "rb"
    for b in BOLGELER:
        if any(a in alt for a in b[5]):
            return b[0]
    return ""


def tarih(s):
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def euro(s):
    m = re.search(r"([\d.]+)\s*€", s or "")
    return int(m.group(1).replace(".", "")) if m else 0


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    anahtar, ad, vid = sys.argv[1], sys.argv[2], sys.argv[3]
    oyuncular = kadro(vid)
    print(f"{ad}: {len(oyuncular)} oyuncu (SoccerDonna verein_{vid})")
    for o in oyuncular:
        p = profil(o["url"])
        o["poz"] = p.get("Position", "")
        o["bolge"] = bolge_bul(o["poz"])
        o["bitis"] = tarih(p.get("Contract until", ""))
        yas = re.search(r"\d+", p.get("Age", "") or "")
        o["yas"] = int(yas.group()) if yas else None
        o["deger"] = euro(p.get("Market value", ""))
    grup = defaultdict(list)
    for o in oyuncular:
        grup[o["bolge"]].append(o)
    degerler = sorted(o["deger"] for o in oyuncular if o["deger"])
    medyan = degerler[len(degerler) // 2] if degerler else 0
    print(f"değeri bilinen {len(degerler)} · medyan €{medyan:,} · en yüksek €{(degerler[-1] if degerler else 0):,}".replace(",", "."))

    aday = []
    for kod, tr, en, mevki, ideal, _ in BOLGELER:
        liste = grup.get(kod, [])
        biten = [o for o in liste if o["bitis"] and o["bitis"] <= SEZON_SONU]
        yasli = [o for o in liste if (o["yas"] or 0) >= 31]
        genc = [o for o in liste if (o["yas"] or 99) <= 19]
        # Yalnız KANITI olan bölgeler puan alır (ayrıntılı mevkisi yazan en az bir oyuncu):
        # sezon sonunda biten sözleşme + 31 yaş üstü + tek/çok genç derinlik. "Kadroda hiç yok"
        # sonucu ÇIKARILMAZ — mevkisi ayrıntısız oyuncular o bölgede oynuyor olabilir.
        if not liste:
            puan = -9.0
        else:
            buyuk = [o for o in liste if (o["yas"] or 0) >= 20]
            puan = len(biten) + len(yasli) + (1.0 if len(buyuk) <= 1 else 0.0) - 0.5 * max(0, len(buyuk) - ideal)
        print(f"  {tr:18} {len(liste)} oyuncu (ideal {ideal}) · sezon sonu biten {len(biten)} · 31+ {len(yasli)} · 19- {len(genc)} · puan {puan:+.1f}  "
              + ", ".join(f"{o['isim']}({o['yas']}{', ' + o['bitis'].strftime('%m.%Y') if o['bitis'] else ''})" for o in liste))
        aday.append((puan, kod, tr, en, mevki, liste, biten, yasli))
    aday.sort(key=lambda x: -x[0])
    if grup.get(""):
        print("  mevkisi okunamayan:", ", ".join(o["isim"] + " [" + o["poz"] + "]" for o in grup[""]))

    deger_max = max(50000, int(round(max(medyan * 3, (degerler[-1] if degerler else 0) * 0.6) / 25000.0)) * 25000)
    not_min = "BB" if medyan >= 60000 else "BC" if medyan >= 20000 else "CC"
    ihtiyaclar = []
    for puan, kod, tr, en, mevki, liste, biten, yasli in aday[:3]:
        if puan <= 0:
            continue
        ned_tr = [f"bu mevkide kayıtlı {len(liste)} oyuncu"]
        ned_en = [f"{len(liste)} player{'s' if len(liste) != 1 else ''} registered in this position"]
        if biten:
            ned_tr.append(f"{len(biten)} sözleşme {SEZON_SONU.strftime('%d.%m.%Y')}'de bitiyor")
            ned_en.append(f"{len(biten)} contract{'s' if len(biten) != 1 else ''} ending {SEZON_SONU.strftime('%d.%m.%Y')}")
        if yasli:
            ned_tr.append(f"{len(yasli)} oyuncu 31 yaş ve üstü")
            ned_en.append(f"{len(yasli)} aged 31 or over")
        ihtiyaclar.append({"baslik": tr, "baslik_en": en, "mevki": mevki, "yas_max": 27, "deger_max": deger_max,
                           "not_min": not_min, "neden": " · ".join(ned_tr), "neden_en": " · ".join(ned_en)})
    kayit = {"ad": ad, "sd_verein": int(vid), "guncelleme": BUGUN.isoformat(),
             "not": "Öne çıkan bölgeler herkese açık kadro verinizden (mevki derinliği, sözleşme bitişi, yaş) çıkarılmıştır.",
             "not_en": "The highlighted areas are derived from your public squad data (positional depth, contract expiry, age).",
             "ihtiyaclar": ihtiyaclar}
    print("\nÖNERİLEN KAYIT:")
    print(json.dumps(kayit, ensure_ascii=False, indent=1))
    if "--yaz" in sys.argv:
        yol = KOK / "kulup_ihtiyac.json"
        veri = json.load(open(yol, encoding="utf-8")) if yol.exists() else {}
        veri[anahtar] = kayit
        json.dump(veri, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("yazıldı:", yol)


if __name__ == "__main__":
    main()
