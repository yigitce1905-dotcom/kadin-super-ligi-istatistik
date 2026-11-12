"""Bir kulübün SoccerDonna kadrosundan 'fırsat alanları' çıkarır ve kulup_ihtiyac.json'a yazar.

Kulübe özel sayfa (?kulup=<anahtar>) bu dosyayı okur. Buradaki 'ihtiyaç' kulübün bize söylediği
bir şey DEĞİL — herkese açık kadro verisinden (mevki derinliği, sözleşme bitişi, yaş) çıkan
yorumdur; sayfada da öyle sunulur ("kadro verinize göre öne çıkan bölgeler").

Kullanım:
    python kulup_ihtiyac_cikar.py <anahtar> "<Kulüp adı>" <soccerdonna verein id> [--seviye=1|2|3] [--yaz]
    python kulup_ihtiyac_cikar.py sc-freiburg "SC Freiburg" 292 --seviye=1 --yaz
--yaz verilmezse yalnız raporlar (dosyaya dokunmaz).

--seviye kulübün lig kademesi (1 = en üst altı lig, 2 = güçlü profesyonel ligler, 3 = diğerleri;
app.py _lig_seviye ile aynı ölçek): aday listesi buna göre süzülür.

ÇIKTI BİR TASLAKTIR. Yazmadan önce basılan kadro tablosuna GÖZLE bak: gerekçe cümlesi kulübe
gidecek ve yanlış bir iddia ilk izlenimi bitirir. Kayda ayrıca "kendi": ["havuzdaki kulüp adı"]
ekle — kulübün kendi oyuncusu aday çıkmasın. --yaz mevcut kaydın ÜZERİNE yazar (elle
düzeltilmiş gerekçeler gider); mevcut bir kulüpte önce --yaz'sız çalıştırıp farka bak.
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
    if "midfield, left" in alt:       # 'Midfield - Midfield, left' = sol açık/sol orta saha
        return "lw"
    if "midfield, right" in alt:
        return "rw"
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
    # Aynı gün yeniden çalıştırınca SoccerDonna'ya tekrar gitme (kural değişikliği denemeleri için)
    onbellek = KOK / f"_kadro_onbellek_{vid}.json"          # '_*.json' .gitignore'da
    ham = {}
    if onbellek.exists():
        try:
            ham = json.load(open(onbellek, encoding="utf-8"))
        except Exception:
            ham = {}
    if ham.get("gun") != BUGUN.isoformat():
        ham = {"gun": BUGUN.isoformat(), "oyuncular": kadro(vid), "profiller": {}}
    oyuncular = ham["oyuncular"]
    print(f"{ad}: {len(oyuncular)} oyuncu (SoccerDonna verein_{vid})")
    for o in oyuncular:
        if o["url"] not in ham["profiller"]:
            ham["profiller"][o["url"]] = profil(o["url"])
    # Önbellek, tarih nesneleri eklenmeden ÖNCE yazılır (12 Kasım 2026: date nesnesi yüzünden
    # json.dump yarıda kesiliyor, dosya bozuk kalıyor ve her çalıştırma SoccerDonna'ya yeniden gidiyordu).
    try:
        json.dump({"gun": ham["gun"], "profiller": ham["profiller"],
                   "oyuncular": [{"isim": o["isim"], "url": o["url"]} for o in oyuncular]},
                  open(onbellek, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception as e:
        print("önbellek yazılamadı:", e)
    for o in oyuncular:
        p = ham["profiller"][o["url"]]
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

    # ── Kanıt kuralları (12 Kasım 2026 denetimi; ilk sürüm üç hata üretti) ──────────────
    #  1) Tarihi GEÇMİŞ sözleşme sayılmaz: SoccerDonna güncellememiş demektir (Cardiff'te
    #     30.06.2026 tarihli 9 sözleşme "bitiyor" diye sayılmıştı).
    #  2) "Bu mevkide tek oyuncu var" iddiası, o hatta mevkisi AYRINTISIZ yazılmış 20 yaş üstü
    #     oyuncu varsa kurulmaz ('Defence' yazan 7 oyuncunun kaçı stoper, bilinmiyor: Weinberg).
    #  3) Ayrıntılı mevki seyrekse kanıt HAT düzeyinde aranır (savunma / orta saha / hücum).
    #  4) Zayıf kanıt bölge açmaz: "3 kaleciden 1'inin sözleşmesi bitiyor" ihtiyaç değildir.
    HAT = {"gk": "gk", "cb": "def", "lb": "def", "rb": "def", "dm": "mid", "cm": "mid", "am": "mid",
           "lw": "att", "rw": "att", "st": "att"}
    HAT_AD = {"def": ("Savunma", "Defence", ["RCB", "MCB", "LCB", "LFB", "LWB", "RFB", "RWB"], "savunma oyuncusundan", "defenders"),
              "mid": ("Orta saha", "Midfield", ["DMF", "CMF", "AMF"], "orta saha oyuncusundan", "midfielders"),
              "att": ("Hücum", "Attack", ["LWF", "RWF", "CFW", "2ST"], "hücum oyuncusundan", "forwards")}
    ABL = {"gk": "kaleciden", "cb": "stoperden", "lb": "sol bekten", "rb": "sağ bekten", "dm": "ön liberodan",
           "cm": "merkez orta sahadan", "am": "ofansif orta sahadan", "lw": "sol kanattan", "rw": "sağ kanattan", "st": "santrfordan"}
    COGUL_EN = {"gk": "goalkeepers", "cb": "centre-backs", "lb": "left-backs", "rb": "right-backs", "dm": "defensive midfielders",
                "cm": "central midfielders", "am": "attacking midfielders", "lw": "left wingers", "rw": "right wingers", "st": "centre-forwards"}
    IYELIK = {1: "'inin", 2: "'sinin", 3: "'ünün", 4: "'ünün", 5: "'inin", 6: "'sının", 7: "'sinin", 8: "'inin", 9: "'unun", 10: "'unun"}

    def iyelik(k):
        return f"{k}{IYELIK.get(k, chr(39) + 'inin')}"

    def hat_bul(o):
        if o["bolge"]:
            return HAT[o["bolge"]]
        p = (o["poz"] or "").lower()
        return "def" if p.startswith("defence") else "mid" if p.startswith("midfield") else "att" if p.startswith("striker") else ""

    def biten_mi(o):
        return bool(o["bitis"] and BUGUN <= o["bitis"] <= SEZON_SONU)

    def tarih_ifade(biten):
        """(TR, EN): hepsi aynı gün bitiyorsa o gün, değilse en geç tarih 'kadar/by'."""
        gunler = sorted({o["bitis"] for o in biten})
        g = gunler[-1].strftime("%d.%m.%Y")
        return (f"{g} tarihinde", f"on {g}") if len(gunler) == 1 else (f"{g} tarihine kadar", f"by {g}")

    def sozlesme_cumlesi(n, biten, abl_tr, cogul_en):
        k = len(biten)
        t_tr, t_en = tarih_ifade(biten)
        if k == n:
            return (f"Kayıtlı {n} {abl_tr} {iyelik(k)} de sözleşmesi {t_tr} bitiyor",
                    f"All {n} registered {cogul_en} are out of contract {t_en}")
        return (f"Kayıtlı {n} {abl_tr} {iyelik(k)} sözleşmesi {t_tr} bitiyor",
                f"{k} of the {n} registered {cogul_en} are out of contract {t_en}")

    eskimis = [o for o in oyuncular if o["bitis"] and o["bitis"] < BUGUN]
    if eskimis:
        print(f"  ! tarihi geçmiş {len(eskimis)} sözleşme sayılmadı (SoccerDonna bayat): "
              + ", ".join(f"{o['isim']} {o['bitis'].strftime('%d.%m.%Y')}" for o in eskimis[:8]))
    tarihli = [o for o in oyuncular if o["bitis"] and o["bitis"] >= BUGUN]
    if tarihli:
        ortak = max({o["bitis"] for o in tarihli}, key=lambda g: sum(1 for o in tarihli if o["bitis"] == g))
        pay = sum(1 for o in tarihli if o["bitis"] == ortak)
        if len(tarihli) >= 8 and pay >= 0.7 * len(tarihli) and ortak <= SEZON_SONU:
            print(f"  ! sezonluk sözleşme düzeni: tarihli {len(tarihli)} sözleşmenin {pay} tanesi {ortak.strftime('%d.%m.%Y')} bitişli "
                  "→ sözleşme bitişi mevki ayırt etmez; gerekçeyi yaş/derinlikle destekle")

    hatlar = defaultdict(list)
    for o in oyuncular:
        hatlar[hat_bul(o)].append(o)

    aday = []            # (puan, başlık TR, başlık EN, mevki kodları, gerekçe TR, gerekçe EN)
    for kod, tr, en, mevki, ideal, _ in BOLGELER:
        liste = grup.get(kod, [])
        kaba = [o for o in hatlar.get(HAT[kod], []) if not o["bolge"] and (o["yas"] or 20) >= 20] if kod != "gk" else []
        biten = [o for o in liste if biten_mi(o)]
        yasli = [o for o in liste if (o["yas"] or 0) >= 31]
        buyuk = [o for o in liste if (o["yas"] or 20) >= 20]
        print(f"  {tr:18} {len(liste)} oyuncu · biten {len(biten)} · 31+ {len(yasli)} · 20+ {len(buyuk)} · hatta ayrıntısız 20+ {len(kaba)}  "
              + ", ".join(f"{o['isim']}({o['yas']}{', ' + o['bitis'].strftime('%m.%Y') if o['bitis'] else ''})" for o in liste))
        if not liste:
            continue
        ned_tr, ned_en, puan = [], [], 0.0
        art = "an" if en[0].lower() in "aeiou" else "a"
        if not kaba and len(liste) == 1:
            o = liste[0]
            if biten:
                t_tr, t_en = tarih_ifade(biten)
                if o["yas"]:
                    ned_tr.append(f"{tr} olarak kayıtlı tek oyuncu {o['yas']} yaşında ve sözleşmesi {t_tr} bitiyor")
                    ned_en.append(f"The only player registered as {art} {en.lower()} is {o['yas']} and out of contract {t_en}")
                else:
                    ned_tr.append(f"{tr} olarak kayıtlı tek oyuncunun sözleşmesi {t_tr} bitiyor")
                    ned_en.append(f"The only player registered as {art} {en.lower()} is out of contract {t_en}")
                puan += 3
            elif o["yas"] and (o["yas"] >= 30 or o["yas"] <= 19):
                ned_tr.append(f"{tr} olarak kayıtlı tek oyuncu {o['yas']} yaşında")
                ned_en.append(f"The only player registered as {art} {en.lower()} is {o['yas']}")
                puan += 2
        else:
            yasli_biten = [o for o in yasli if o in biten]
            if len(biten) >= 2 and 2 * len(biten) >= len(liste):
                a, b = sozlesme_cumlesi(len(liste), biten, ABL[kod], COGUL_EN[kod])
                if yasli_biten:
                    a += "; " + ("biri" if len(yasli_biten) == 1 else f"{len(yasli_biten)} oyuncu") + " 31 yaş ve üstü"
                    b += "; " + ("one of them is" if len(yasli_biten) == 1 else f"{len(yasli_biten)} of them are") + " 31 or over"
                ned_tr.append(a)
                ned_en.append(b)
                puan += 1 + len(biten)
            elif yasli_biten:
                o = yasli_biten[0]
                t_tr, t_en = tarih_ifade([o])
                ned_tr.append(f"Kayıtlı {len(liste)} {ABL[kod]} biri {o['yas']} yaşında ve sözleşmesi {t_tr} bitiyor")
                ned_en.append(f"One of the {len(liste)} registered {COGUL_EN[kod]} is {o['yas']} and out of contract {t_en}")
                puan += 2.5
            elif yasli and 2 <= len(liste) <= 4:
                o = max(yasli, key=lambda x: x["yas"])
                ned_tr.append(f"Kayıtlı {len(liste)} {ABL[kod]} biri {o['yas']} yaşında")
                ned_en.append(f"One of the {len(liste)} registered {COGUL_EN[kod]} is {o['yas']}")
                puan += 2
            if kod == "gk" and len(buyuk) == 1 and len(liste) > 1:
                ned_tr.append("20 yaş ve üstü tek kayıtlı kaleci var")
                ned_en.append("only one goalkeeper aged 20 or over is registered")
                puan += 2
        if puan >= 2 and ned_en:
            n_tr, n_en = "; ".join(ned_tr) + ".", "; ".join(ned_en) + "."
            aday.append((puan, tr, en, mevki, n_tr[0].upper() + n_tr[1:], n_en[0].upper() + n_en[1:]))

    # Hat düzeyi: ayrıntılı mevkisi olan oyuncu o hattın yarısından azsa
    for hat, (h_tr, h_en, h_mevki, h_abl, h_cogul) in HAT_AD.items():
        liste = hatlar.get(hat, [])
        ayrintili = [o for o in liste if o["bolge"]]
        if len(liste) < 4 or 2 * len(ayrintili) >= len(liste):
            continue
        biten = [o for o in liste if biten_mi(o)]
        yasli = [o for o in liste if (o["yas"] or 0) >= 31]
        print(f"  [hat] {h_tr:12} {len(liste)} oyuncu (ayrıntılı {len(ayrintili)}) · biten {len(biten)} · 31+ {len(yasli)}")
        if len(biten) >= 3 and 5 * len(biten) >= 2 * len(liste):
            a, b = sozlesme_cumlesi(len(liste), biten, h_abl, h_cogul)
            if yasli:
                a += f"; {len(yasli)} oyuncu 31 yaş ve üstü"
                b += f"; {len(yasli)} {'is' if len(yasli) == 1 else 'are'} 31 or over"
            aday.append((1 + len(biten) * 0.8, h_tr, h_en, h_mevki, a + ".", b + "."))

    aday.sort(key=lambda x: -x[0])
    deger_max = max(25000, int(round(max(medyan * 3, (degerler[-1] if degerler else 0) * 0.6) / 25000.0)) * 25000)
    not_min = "BB" if medyan >= 60000 else "BC" if medyan >= 20000 else "CC"
    ihtiyaclar = [{"baslik": tr, "baslik_en": en, "mevki": mevki, "yas_max": 27, "deger_max": deger_max,
                   "not_min": not_min, "neden": n_tr, "neden_en": n_en}
                  for puan, tr, en, mevki, n_tr, n_en in aday[:3]]
    if not ihtiyaclar:
        print("\n  ! Kanıt taşıyan bölge çıkmadı → bu kulübe 'kadro analizi' sayfası KURMA; "
              "ya genel tanıtım gönder ya da kayıtta \"genel\": true ile örnek kısa liste sayfası kur (First Vienna örneği).")
    seviye = next((int(a.split("=", 1)[1]) for a in sys.argv if a.startswith("--seviye=")), 3)
    kayit = {"ad": ad, "sd_verein": int(vid), "guncelleme": BUGUN.isoformat(), "seviye": seviye,
             "not": f"Öne çıkan bölgeler herkese açık kadro verinizden (sözleşme bitişi, yaş, mevki derinliği) çıkarılmıştır. Kaynak: SoccerDonna, {BUGUN.strftime('%d.%m.%Y')}.",
             "not_en": f"The highlighted areas are derived from your public squad data (contract expiry, age, positional depth). Source: SoccerDonna, {BUGUN.strftime('%d.%m.%Y')}.",
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
