"""SoccerDonna profili bağlı OLMAYAN oyuncuları çözer (Süper Lig TFF listesi + scouting havuzu).

Neden (13 Kasım 2026, Yiğit: "bizim ligden bile bir sürü oyuncu eksik… bir oyuncu bile kalmayacak şekilde çöz"):
eski betikler yalnız soyadla SD araması yapıyordu; yazımı farklı (ÇIKILI/Çakılı), adı uzun (Brezilyalı çift soyad) ya da
yeni transfer oyuncular bulunamıyordu. Bu betik üç kaynağı sırayla dener:
  1) maç kadroları (sd_dizilis_*.json): SD oyuncu kimliği + ad + takım — bu sezon forma giymiş herkes burada;
  2) Süper Lig kulüplerinin SD kadro sayfaları (maça çıkmamış kayıtlı oyuncular);
  3) SD araması (soyad, ad, tam ad) — ülke/kulüp tutarlılığıyla.
Eşleşme ölçütü: ad benzerliği + (aynı takım | aynı ülke). Kuşkulu olanlar YAZILMAZ, listelenir.

SD çoğu oyuncuyu TAKMA / KISA adla tutar; gerçek ad profilin "Name in native country" alanındadır (Jeannette Yango →
"Grace Yango", Estefane Rossetto → "Tetê", Precious Onyinyechi → "Precious Christopher"). SD araması o alanı da tarar, bu
yüzden adın HER sözcüğüyle aranır ve aday, tam adla da karşılaştırılır (tam_ad_uyumu).

Elle kararlar sd_eksik_elle.json'da durur (kanıtıyla): "kabul" = bu oyuncu şu SD kimliği, "yok" = SoccerDonna'da kaydı yok
(yazılırken "bulunamadi" işaretlenir, bir daha eksik sayılmaz).

    python sd_eksik_coz.py <sd_eksik.json>            # yalnız rapor (öneriler)
    python sd_eksik_coz.py <sd_eksik.json> --yaz      # güvenli eşleşmeleri profil dosyalarına yazar

Girdi: uygulamadan dökülen eksik listesi ({"tr": [...], "havuz": [...]}; scratchpad sd_eksik_dok.py üretir).
"""
import datetime
import glob
import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}
TABAN = "https://www.soccerdonna.de"
BUGUN = datetime.date.today().isoformat()
ALANLAR = {"Date of birth", "Place of birth", "Age", "Name in native country", "Height", "Nationality", "2nd Nationality",
           "Position", "Foot", "Market value", "Contract until", "Debut (Club)"}
ULKE_ES = {"turkiye": "turkey", "türkiye": "turkey", "botsuana": "botswana", "cote d'ivoire": "ivory coast", "cote divoire": "ivory coast", "trinidad&tobago": "trinidad and tobago",
           "bosnia&herzegovina": "bosnia-herzegovina", "united states": "united states", "south korea": "korea, south", "danmark": "denmark"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "").replace("ı", "i").replace("İ", "I").replace("ø", "o").replace("đ", "d").replace("ł", "l").replace("ß", "ss"))
    s = s.encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def benzerlik(a, b):
    """0-1: sıra bağımsız ad benzerliği (ortak sözcük oranı + harf benzerliği; 'Elanur Çıkılı' ↔ 'Elanur Çakılı' yüksek çıkar)."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    ta, tb = na.split(), nb.split()
    # her sözcük için karşı taraftaki en benzer sözcük
    def tek(x, liste):
        return max((SequenceMatcher(None, x, y).ratio() for y in liste), default=0.0)
    kisa, uzun = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    soz = sum(tek(x, uzun) for x in kisa) / len(kisa)
    tam = SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return round(max(tam, 0.85 * soz + 0.15 * tam), 3)


def tam_ad_uyumu(isim, tam_ad):
    """Bizdeki adın sözcüklerinden kaçı SD'deki TAM adda geçiyor (0-1). 2+ sözcük ve hepsi geçiyorsa 1.0."""
    a, b = norm(isim).split(), norm(tam_ad).split()
    if len(a) < 2 or len(b) < 2:
        return 0.0
    return round(sum(1 for x in a if max((SequenceMatcher(None, x, y).ratio() for y in b), default=0) >= 0.84) / len(a), 3)


def getir(url, params=None):
    for i in range(3):
        try:
            r = requests.get(url, params=params, headers=H, timeout=20)
            if r.status_code == 200:
                time.sleep(0.6)
                return r.text
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    return ""


def profil_cek(url):
    soup = BeautifulSoup(getir(url), "html.parser")
    veri = {"profil_url": url}
    for tablo in soup.find_all("table"):
        txt = tablo.get_text(" ", strip=True)
        if "Date of birth" not in txt and "Position" not in txt:
            continue
        for tr in tablo.find_all("tr"):
            h = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(h) >= 2 and h[0].rstrip(":").strip() in ALANLAR and h[1].strip():
                veri[h[0].rstrip(":").strip()] = h[1].strip()
        break
    b = soup.find("h1")
    if b:
        veri["sd_isim"] = re.sub(r"^\d+\s*", "", b.get_text(" ", strip=True)).strip()
    for a in soup.find_all("a", href=True):
        if "/startseite/verein_" in a["href"] and a.get_text(strip=True) and not a.get_text(strip=True).isdigit():
            veri.setdefault("guncel_kulup", a.get_text(strip=True))
            break
    return veri


def sd_ara(terim):
    slug = re.sub(r"[^a-z0-9]+", "-", norm(terim)).strip("-") or "x"
    soup = BeautifulSoup(getir(f"{TABAN}/en/{slug}/suche/ergebnis.html", {"quicksearch": terim}), "html.parser")
    out, gor = [], set()
    for a in soup.find_all("a", href=re.compile(r"/profil/spieler_\d+")):
        ad = a.get_text(strip=True)
        sid = re.search(r"spieler_(\d+)", a["href"]).group(1)
        if ad and len(ad) > 2 and sid not in gor:
            gor.add(sid)
            out.append((sid, ad, TABAN + a["href"]))
    return out


def ulke_uyar(a, b):
    na, nb = norm(a), norm(b)
    na, nb = ULKE_ES.get(na, na), ULKE_ES.get(nb, nb)
    if not na or not nb:
        return None
    return na == nb or na in nb or nb in na or bool(set(na.split()) & set(nb.split()) - {"and", "of", "the", "republic"})


def main():
    girdi = json.load(open(sys.argv[1], encoding="utf-8"))
    yaz = "--yaz" in sys.argv
    # 1) aday dizini: maç kadroları (tüm ligler) — sd_id → {ad, takımlar, lig}
    aday = {}
    tr_takim = {}                                   # SD takım kimliği → ad (Süper Lig)
    for yol in glob.glob(str(KOK / "sd_dizilis_*.json")):
        v = json.load(open(yol, encoding="utf-8"))
        kod = v.get("lig_kod") or "TUR1"
        for m in v.get("maclar", []):
            for tf in ("ev", "dep"):
                if kod == "TUR1" and m.get(tf + "_id"):
                    tr_takim[m[tf + "_id"]] = m.get(tf, "")
                for p in (m.get("ilk11") or {}).get(tf, []) + (m.get("yedekler") or {}).get(tf, []):
                    if p.get("sd_id"):
                        a = aday.setdefault(str(p["sd_id"]), {"ad": p["ad"], "takim": set(), "lig": kod, "kaynak": "maç kadrosu"})
                        a["takim"].add(m.get(tf, ""))
    # 2) Süper Lig kulüp kadro sayfaları
    for vid, tad in tr_takim.items():
        soup = BeautifulSoup(getir(f"{TABAN}/en/x/kader/verein_{vid}.html"), "html.parser")
        for a in soup.select("a[href*='/profil/spieler_']"):
            ad = a.get_text(" ", strip=True)
            sid = re.search(r"spieler_(\d+)", a["href"]).group(1)
            if ad and sid not in aday:
                aday[sid] = {"ad": ad, "takim": {tad}, "lig": "TUR1", "kaynak": "kulüp kadrosu"}
    print(f"aday dizini: {len(aday)} oyuncu · Süper Lig takımı {len(tr_takim)}")

    def takim_uyar(aranan, aday_takimlar):
        n = norm(aranan)
        anahtar = [w for w in n.split() if len(w) > 3 and w not in ("spor", "kulubu", "kadin", "futbol", "jimnastik", "belediyesi", "buyuksehir", "sportif", "yatirim", "faaliyetler", "grup")]
        return any(any(w in norm(t) for w in anahtar) for t in aday_takimlar)

    def en_iyi(isim, takim="", uyruk="", yalniz_tr=False):
        sonuc = []
        for sid, a in aday.items():
            if yalniz_tr and a["lig"] != "TUR1":
                continue
            b = benzerlik(isim, a["ad"])
            if b >= 0.72:
                sonuc.append((b + (0.08 if takim and takim_uyar(takim, a["takim"]) else 0), b, sid, a))
        sonuc.sort(key=lambda x: -x[0])
        return sonuc[:3]

    elle_yol = KOK / "sd_eksik_elle.json"
    elle = json.load(open(elle_yol, encoding="utf-8")) if elle_yol.exists() else {}
    cozum, kuskulu, yok, yok_kesin = [], [], [], []
    eksik = [("tr", x["isim"], x["takim"], "") for x in girdi["tr"] if not x.get("sd_id")]
    eksik += [("havuz", x["isim"], x["kulup"], x["uyruk"]) for x in girdi["havuz"] if not x.get("sd_id") and not x.get("dusuk")]
    for tur, isim, takim, uyruk in eksik:
        if isim in elle.get("yok", {}):
            yok_kesin.append((tur, isim, takim, uyruk, elle["yok"][isim]))
            continue
        adaylar = en_iyi(isim, takim, uyruk)
        secilen = None
        if isim in elle.get("kabul", {}):
            sid, kanit = elle["kabul"][isim]
            secilen = (str(sid), "", f"{TABAN}/en/x/profil/spieler_{sid}.html", "elle doğrulandı · " + kanit)
        elif adaylar:
            skor, b, sid, a = adaylar[0]
            ayni_takim = bool(takim) and takim_uyar(takim, a["takim"])
            tek = len(adaylar) == 1 or adaylar[0][0] - adaylar[1][0] >= 0.06
            if (b >= 0.93 and tek) or (b >= 0.80 and ayni_takim and tek):
                secilen = (sid, a["ad"], f"{TABAN}/en/x/profil/spieler_{sid}.html", f"{a['kaynak']} · {', '.join(sorted(a['takim']))[:40]} · benzerlik {b}")
        if not secilen:                              # 3) SD araması
            p = norm(isim).split()
            terimler = list(dict.fromkeys(([p[-1], p[0]] + [w for w in p if len(w) >= 4] + [" ".join(p)]) if len(p) > 1 else p))
            bulunan = {}
            for tm in terimler:
                for sid, ad, url in sd_ara(tm):
                    bulunan[sid] = (ad, url)
            sirali = sorted(((benzerlik(isim, ad), sid, ad, url) for sid, (ad, url) in bulunan.items()), reverse=True)
            for b, sid, ad, url in sirali[:4]:
                if b < 0.80:
                    break
                pr = profil_cek(url)
                uy = ulke_uyar(uyruk, pr.get("Nationality", "")) if uyruk else None
                tk = bool(takim) and takim_uyar(takim, {pr.get("guncel_kulup", "")})
                if (b >= 0.92 and uy is not False) or (b >= 0.80 and (uy or tk)):
                    secilen = (sid, ad, url, f"SD araması · {pr.get('Nationality', '?')} · {pr.get('guncel_kulup', '?')} · benzerlik {b}")
                    break
            if not secilen:                          # takma adla kayıtlı olabilir: TAM adla karşılaştır (ülke ya da kulüp tutmalı)
                for b, sid, ad, url in sirali[:14]:
                    pr = profil_cek(url)
                    tam = tam_ad_uyumu(isim, pr.get("Name in native country", ""))
                    uy = ulke_uyar(uyruk, pr.get("Nationality", "")) if uyruk else None
                    tk = bool(takim) and takim_uyar(takim, {pr.get("guncel_kulup", "")})
                    if tam >= 0.99 and (uy or tk):
                        secilen = (sid, ad, url, f"SD araması, tam ad '{pr.get('Name in native country', '')}' · {pr.get('Nationality', '?')} · "
                                                 f"{pr.get('guncel_kulup', '?')}")
                        break
            sirali = sirali[:4]
            if not secilen and sirali and sirali[0][0] >= 0.70:
                kuskulu.append((tur, isim, takim, uyruk, [(b, ad, url) for b, sid, ad, url in sirali[:3]]))
                continue
            if not secilen and adaylar:
                kuskulu.append((tur, isim, takim, uyruk, [(b, a["ad"] + " [" + ", ".join(sorted(a["takim"]))[:30] + "]", f"{TABAN}/en/x/profil/spieler_{sid}.html") for _, b, sid, a in adaylar]))
                continue
        if secilen:
            cozum.append((tur, isim, takim, uyruk) + secilen)
        else:
            yok.append((tur, isim, takim, uyruk))

    print(f"\nÇÖZÜLEN {len(cozum)}")
    for tur, isim, takim, uyruk, sid, ad, url, kanit in cozum:
        print(f"  [{tur}] {isim:32} → {ad:30} ({sid}) · {kanit}")
    print(f"\nKUŞKULU {len(kuskulu)} (yazılmaz; elle bak)")
    for tur, isim, takim, uyruk, liste in kuskulu:
        print(f"  [{tur}] {isim:32} {takim[:24]:24} {uyruk[:12]:12} ? " + " | ".join(f"{b} {ad} {url.split('spieler_')[-1].split('.')[0]}" for b, ad, url in liste))
    print(f"\nBULUNAMAYAN {len(yok)}")
    for tur, isim, takim, uyruk in yok:
        print(f"  [{tur}] {isim:32} {takim[:28]:28} {uyruk}")
    print(f"\nSOCCERDONNA'DA KAYDI YOK (elle doğrulandı) {len(yok_kesin)}")
    for tur, isim, takim, uyruk, kanit in yok_kesin:
        print(f"  [{tur}] {isim:32} {kanit}")
    json.dump({"cozum": cozum, "kuskulu": kuskulu, "yok": yok, "yok_kesin": yok_kesin}, open(str(Path(sys.argv[1]).with_name("sd_eksik_cozum.json")), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if yaz and (cozum or yok_kesin):
        dosya = {"tr": KOK / "soccerdonna_profiller.json", "havuz": KOK / "scouting_sd_profiller.json"}
        veri = {k: json.load(open(p, encoding="utf-8")) for k, p in dosya.items()}
        for tur, isim, takim, uyruk, sid, ad, url, kanit in cozum:
            pr = profil_cek(url)
            if len(pr) <= 3:
                print("  ! profil okunamadı:", isim, url)
                continue
            pr.update({"_sd_ts": BUGUN, "kunye_guncelleme": BUGUN, "_eslesme": kanit})
            eski = dict(veri[tur].get(isim)) if isinstance(veri[tur].get(isim), dict) else {}
            eski.pop("bulunamadi", None)
            veri[tur][isim] = {**eski, **pr}
        for tur, isim, takim, uyruk, kanit in yok_kesin:
            eski = dict(veri[tur].get(isim)) if isinstance(veri[tur].get(isim), dict) else {}
            veri[tur][isim] = {**eski, "bulunamadi": True, "_sd_yok": kanit, "_sd_ts": BUGUN}
        for k, p in dosya.items():
            json.dump(veri[k], open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nyazıldı: {len(cozum)} oyuncu")


if __name__ == "__main__":
    main()
