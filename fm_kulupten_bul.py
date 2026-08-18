# -*- coding: utf-8 -*-
"""Aramada bulunamayan oyuncuları KULÜP KADROSUNDAN bulur (ikinci geçiş).

NEDEN GEREKLİ
FMInside'in arama ucu düşük kapsamlı: "Johnson" için 5, "Smith" için 7 sonuç
dönüyor — yani veri tabanındaki her oyuncu aramada çıkmıyor. Oysa KULÜP
sayfası kadronun tamamını listeliyor (Orlando Pride'da 30+ oyuncu, aramada
çıkmayan Angelina dâhil).

AKIŞ
  1. oyuncunun bizdeki kulübü aranır → /clubs/7-fm-26/... adresi
  2. kulüp sayfasındaki kadro çekilir
  3. isim, fm_toplu_cek'teki jeton mantığıyla kadroda aranır
  4. bulunursa profil çekilip önbelleğe eklenir

Bulunamazsa oyuncu FM26 veri tabanında GERÇEKTEN yok demektir; FM Uganda,
Togo, Burundi, Malta, Kıbrıs gibi ligleri modellemiyor.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.argv = sys.argv or ["x"]
sys.stdout.reconfigure(encoding="utf-8")

import fm_toplu_cek as F
from fm_nitelik_esle import cevir

KOK = Path(__file__).parent
LISTE = Path.home() / "Desktop" / "NOTLANACAK_oncelik_listesi.csv"

# Kulüp adının aramada işe yaramayan kuyrukları (şehir/tüzel ek)
_KUYRUK = re.compile(
    r"\b(fotball|fotboll|football|futbol|women|womens|w|wfc|fc|sc|sk|if|ff|"
    r"bk|cf|afc|club|kadin|kadın|damer|feminin|feminino|femenil)\b", re.I)


def kulup_adaylari(ad: str):
    """'Stabæk Fotball' → ['Stabæk Fotball', 'Stabæk']; 'Breiðablik Kópavogur'
    → [..., 'Breiðablik']. Aksan KORUNUR: arama aksana duyarlı."""
    ad = (ad or "").strip()
    if not ad or ad.lower() in ("serbest", "-", ""):
        return []
    c = [ad]
    sade = _KUYRUK.sub(" ", ad)
    sade = " ".join(sade.split())
    if sade and sade != ad:
        c.append(sade)
    p = sade.split()
    if len(p) > 1:
        c.append(p[0])                      # 'Breiðablik Kópavogur' → 'Breiðablik'
    return list(dict.fromkeys(c))


def kulup_bul(oturum, ad):
    for q in kulup_adaylari(ad):
        r = F._iste(oturum, f"{F.KOK_URL}/resources/inc/ajax/site-search.php",
                    params={"q": q}, headers={"X-Requested-With": "XMLHttpRequest"})
        try:
            d = r.json()
        except ValueError:
            d = {}
        time.sleep(0.8)
        for g in d.get("groups") or []:
            if g.get("key") != "clubs":
                continue
            for it in g.get("items") or []:
                # U23/U19 takımları ana kadro değil — atla
                if re.search(r"\bU\d\d\b", it.get("title") or ""):
                    continue
                yield it.get("title"), it.get("url")


def kadro(oturum, yol):
    t = F._iste(oturum, F.KOK_URL + yol).text
    s = BeautifulSoup(t, "html.parser")
    out = {}
    for a in s.select('a[href^="/players/7-fm-26/"]'):
        n = " ".join(a.get_text(" ", strip=True).split())
        # bağlantı metni bazen "Ad Soyad 21 years" / "Ad Soyad Brazil · First
        # team …" biçiminde geliyor — kuyruğu kes
        n = re.split(r"\s+\d+\s+years|\s{2,}|\s+·\s+", n)[0].strip()
        n = re.sub(r"\s+(?:United States|England|Brazil|FMInside suggestion).*$", "", n)
        if n and len(n) > 2:
            out.setdefault(F.norm(n), (n, a["href"]))
    return out


def main():
    onbellek = json.load(open(F.ONBELLEK, encoding="utf-8"))
    yok = json.load(open(F.BULUNAMAYAN, encoding="utf-8"))
    satir = {r["Oyuncu"]: r for r in csv.DictReader(open(LISTE, encoding="utf-8-sig"))}

    oturum = requests.Session()
    oturum.headers.update({"User-Agent": F.UA, "Accept-Language": "en-US,en;q=0.9"})

    bulunan, hala_yok = [], []
    for isim in list(yok):
        r = satir.get(isim, {})
        kadro_onbellek = {}
        eslesme = None
        for kad, kyol in kulup_bul(oturum, r.get("Kulüp")):
            if kyol in kadro_onbellek:
                continue
            k = kadro(oturum, kyol)
            kadro_onbellek[kyol] = k
            time.sleep(0.8)
            hedef = F._jeton(isim)
            for nrm, (ad, purl) in k.items():
                j = F._jeton(ad)
                if j == hedef or (len(j & hedef) >= 2 and (j <= hedef or hedef <= j)):
                    eslesme = (ad, purl, kad)
                    break
            if eslesme:
                break

        if not eslesme:
            hala_yok.append(isim)
            print(f"   ✗ {isim[:26]:26} ({r.get('Kulüp','')[:22]}) FM26'da yok",
                  flush=True)
            continue

        ad, purl, kad = eslesme
        p = F.profil(oturum, purl)
        kaleci = any(m.upper().startswith("GK") for m in p["mevkiler"])
        b = cevir(p["ham"], kaleci=kaleci)
        onbellek[isim] = {
            "url": F.KOK_URL + purl, "meta": f"FM 26 / {kad} / Age {p['yas']}",
            "kaleci": kaleci, "fm_yas": p["yas"], "fm_boy": p["boy"],
            "fm_kulup": p["fm_kulup"], "fm_uyruk": p["fm_uyruk"],
            "fm_uyruklar": p["fm_uyruklar"], "mevkiler": p["mevkiler"],
            "nitelikler": {k: v for bl in b.values() for k, v in bl.items()},
            "eslesme": f"kulüp kadrosu ({kad}) · FM adı: {ad}",
        }
        bulunan.append((isim, ad, kad))
        print(f"   ✓ {isim[:26]:26} → {ad} @ {kad}", flush=True)
        json.dump(onbellek, open(F.ONBELLEK, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        time.sleep(1.0)

    json.dump(onbellek, open(F.ONBELLEK, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(onbellek, open(F.BEKLEYEN, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({k: "FM26 veri tabanında yok" for k in hala_yok},
              open(F.BULUNAMAYAN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nkurtarılan {len(bulunan)} · hâlâ yok {len(hala_yok)} · "
          f"önbellek {len(onbellek)}")


if __name__ == "__main__":
    main()
