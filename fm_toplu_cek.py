# -*- coding: utf-8 -*-
"""FMInside'dan öncelik listesindeki oyuncuların niteliklerini toplu çeker.

Yiğit'in talebi (2026-08-18): "kalan 93'ünü de yap, engel gelince bekle,
geçince tekrar başla."

NEDEN TARAYICI DEĞİL
Sayfa giriş istemiyor; aynı HTML'i düz HTTP isteğiyle de veriyor. Tarayıcıda
tek tek tıklamak 93 oyuncu için ne daha doğru ne daha hızlı — aynı açık
sayfanın aynı içeriği. Tarayıcı yalnızca giriş gerekseydi gerekliydi.

AKIŞ
  1. site-search.php ile isim aranır → profil URL'i + "FM 26 / Kulüp / Age N"
  2. profil sayfasından tr[id] satırları okunur (36 nitelik)
  3. fm_nitelik_esle.cevir ile harfe çevrilir
  4. _fm_bekleyen.json'a yazılır → fm_sheete_yaz.py --yaz sheet'e işler

DURAKLAMA (Yiğit'in kuralı)
429/403/5xx gelirse üstel bekleme ile tekrar denenir (30s → 60s → …→ 10dk).
Vazgeçilmez; sadece bekler. Ctrl+C ile durdurulabilir, ilerleme kaydedilir.

KİMLİK
Arama sonucundaki yaş ve kulüp kayda yazılır; kimlik kararını
fm_sheete_yaz.py verir (isim + en az bir bağımsız sinyal). Buradan asla
kulüp/sözleşme geçmez — FM'in anlık görüntüsü bizim SD verimizden eskidir.
"""
import csv
import difflib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

KOK = Path(__file__).parent
LISTE = Path.home() / "Desktop" / "NOTLANACAK_oncelik_listesi.csv"
BEKLEYEN = KOK / "_fm_bekleyen.json"
ONBELLEK = KOK / "_fm_ham_cache.json"      # çekilen ham FM verisi (tekrar çekme)
BULUNAMAYAN = KOK / "_fm_bulunamayan.json"

KOK_URL = "https://fminside.net"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


# NFKD bu harfleri ÇÖZMEZ — ayrı bir aksan değil, ayrı bir harftirler.
# Møller → "Mller" oluyordu ve İskandinav/İzlandalı oyuncular "bulunamadı"
# sayılıyordu. kulup_denetim._HARF ile aynı mantık.
_HARF = str.maketrans({
    "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "å": "a", "Å": "A",
    "ð": "d", "Ð": "D", "þ": "th", "Þ": "TH", "ß": "ss",
    "ı": "i", "İ": "I", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D",
    "ħ": "h", "ŋ": "n", "œ": "oe", "Œ": "OE",
})


def norm(s):
    s = str(s or "").translate(_HARF)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = " ".join(s.casefold().split())
    # Bizim sheet umlaut'u AÇARAK yazıyor (Waelti, Boehi, Saevik), FM özgün
    # yazımı tutuyor (Wälti, Böhi, Sævik) — NFKD sonrası "walti"/"waelti"
    # ayrışıyordu. İki yazımı da aynı tabana indiriyoruz.
    for cift, tek in (("ae", "a"), ("oe", "o"), ("ue", "u")):
        s = s.replace(cift, tek)
    return s


def _jeton(isim):
    """Ad parçaları kümesi — sıra ve fazladan soyadı farkını yutar."""
    return {p for p in re.split(r"[\s\-]+", norm(isim)) if p}


def _cekirdek(isim):
    """Göbek adı atılmış hâli: 'Rikke Marie Madsen' → 'rikke madsen'.
    Sheet göbek adını taşır, FM çoğu zaman taşımaz (ya da tersi)."""
    p = norm(isim).split()
    return f"{p[0]} {p[-1]}" if len(p) > 2 else norm(isim)


class Engellendi(Exception):
    pass


def _iste(oturum, url, **kw):
    """Engel gelirse bekler ve tekrar dener. Asla vazgeçmez, sadece bekler."""
    bekle = 30
    while True:
        try:
            r = oturum.get(url, timeout=30, **kw)
            if r.status_code in (403, 429) or r.status_code >= 500:
                raise Engellendi(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r
        except (Engellendi, requests.RequestException) as e:
            print(f"      ⏸  {e} — {bekle}sn bekleyip tekrar denenecek", flush=True)
            time.sleep(bekle)
            bekle = min(bekle * 2, 600)


def _sor(oturum, q):
    r = _iste(oturum, f"{KOK_URL}/resources/inc/ajax/site-search.php",
              params={"q": q}, headers={"X-Requested-With": "XMLHttpRequest"})
    try:
        d = r.json()
    except ValueError:
        return []
    return [it for g in (d.get("groups") or []) for it in (g.get("items") or [])
            if it.get("type") == "player"]


def _teyit(meta, ipucu):
    """meta = 'FM 26 / Kulüp / Age 24'. Kulüp ya da yaş bizimkini tutuyor mu?"""
    parca = [x.strip() for x in (meta or "").split("/")]
    fm_kulup = norm(parca[1]) if len(parca) > 1 else ""
    m = re.search(r"Age\s*(\d+)", meta or "")
    bizim_kulup = norm(ipucu.get("kulup"))
    if fm_kulup and bizim_kulup and (fm_kulup in bizim_kulup or bizim_kulup in fm_kulup):
        return True
    yas = str(ipucu.get("yas") or "")
    if m and yas.isdigit() and yas != "126":
        return abs(int(m.group(1)) - int(yas)) <= 1
    return False


def ara(oturum, isim, ipucu=None):
    """site-search.php → (url, meta, nasıl). Bulunamazsa (None, '', '').

    FM'in arama kutusu AKSANA DUYARLI: "Waelti" sıfır sonuç, "Wälti" bulur.
    Bizim sheet ise umlaut'u açarak yazıyor. Aksanlı biçimi üretemeyeceğimiz
    için ADI da sorguya sokuyoruz (ilk adlar hemen her zaman ASCII).
    Ayrıca FM göbek adını taşımıyor ("Olivia Holdt"), Kore adlarını ters
    yazıyor ("Soo-Jeong Park"), bazen fazladan soyadı taşıyor
    ("Alberte Vingum Andersen").
    """
    ipucu = ipucu or {}
    p = isim.split()
    sorgular = [isim]
    if len(p) > 2:
        sorgular += [f"{p[0]} {p[-1]}", f"{p[0]} {p[1]}"]
    if len(p) >= 2:
        sorgular.append(f"{p[-1]} {p[0]}")       # Kore: ters sıra
    sorgular += [p[-1], p[0]]                    # soyadı, sonra ad

    gorulen = {}
    for q in dict.fromkeys(sorgular):
        for it in _sor(oturum, q):
            gorulen[it.get("url")] = (it.get("title") or "", it.get("meta") or "")
        time.sleep(0.8)

    bizim = _jeton(isim)

    # 1) jeton kümesi birebir — sıra farkı ve aksan yazımı yutulur
    tam = [(u, t, m) for u, (t, m) in gorulen.items() if _jeton(t) == bizim]
    if len(tam) == 1:
        return tam[0][0], tam[0][2], "birebir"

    # 2) biri diğerini kapsıyor (göbek/fazla soyadı). Tek aday OLMALI ve
    #    kulüp ya da yaş teyit ETMELİ — kardeş/akraba aynı ada sahip olabilir.
    alt = [(u, t, m) for u, (t, m) in gorulen.items()
           if len(bizim & _jeton(t)) >= 2 and (bizim <= _jeton(t) or _jeton(t) <= bizim)]
    alt = [x for x in alt if _teyit(x[2], ipucu)]
    if len(alt) == 1:
        return alt[0][0], alt[0][2], "kapsama"

    # 3) yazım hatası (bizde "Llyod-Smith", doğrusu "Lloyd-Smith"). En katı
    #    kapı: yüksek benzerlik + tek aday + kulüp/yaş teyidi.
    yakin = [(u, t, m) for u, (t, m) in gorulen.items()
             if difflib.SequenceMatcher(None, norm(t), norm(isim)).ratio() >= 0.85]
    yakin = [x for x in yakin if _teyit(x[2], ipucu)]
    if len(yakin) == 1:
        return yakin[0][0], yakin[0][2], f"yazım? FM: {gorulen[yakin[0][0]][0]}"

    # Yanlış kişiye nitelik yazmaktansa boş bırakmak yeğdir.
    return None, "", ""


def profil(oturum, yol):
    """Profil sayfası → {"ham": {FM adı: değer}, "bilgi": {...}}"""
    t = _iste(oturum, KOK_URL + yol).text
    s = BeautifulSoup(t, "html.parser")

    ham = {}
    for tr in s.select("tr[id]"):
        ad = tr.select_one("td.name")
        dg = tr.select_one("td.stat")
        if not (ad and dg):
            continue
        v = dg.get_text(strip=True)
        if v.isdigit():
            ham[" ".join(ad.get_text(" ", strip=True).split())] = int(v)

    duz = " ".join(re.sub(r"<[^>]+>", " ", t).split())

    def alan(etiket, son=r"[A-Z][a-z]"):
        m = re.search(rf"{etiket}:\s*(.+?)(?=\s+{son}|$)", duz)
        return m.group(1).strip() if m else ""

    for ayak in ("Left foot", "Right foot"):
        m = re.search(rf"{ayak}:\s*(\d+)", duz)
        if m:
            ham[ayak] = int(m.group(1))

    m_boy = re.search(r"Height:\s*(\d+)\s*CM", duz)
    m_yas = re.search(r"Age:\s*(\d+)", duz)
    m_poz = re.search(r"Positions:\s*(.+?)\s+Database version", duz)
    m_kul = re.search(r"Contract\s+Club:\s*([^€]+?)(?:\s+(?:On loan|Sell value))", duz)
    # Uyruk: <a href="/players/br"><img .../br.svg">Brazil</a>. Sheet'te yaş
    # 126 (boş doğum tarihi) ve boy boş olan oyuncularda kimliği doğrulayacak
    # TEK bağımsız sinyal bu — kulüp FM'de eski kalıyor.
    # Ülke kodu tire taşıyabiliyor: gb-eng, gb-sct, gb-wls.
    # HEPSİNİ alıyoruz: çifte vatandaşlarda FM DOĞUM uyruğunu öne yazıyor,
    # bizim sheet MİLLÎ TAKIMI tutuyor. Shae Yáñez FM'de "United States",
    # bizde "Spain" (İspanya millîsi); Michaela Abam FM'de "United States",
    # bizde "Cameroon". İlkini alınca ikisi de yanlış eşleşme gibi görünüyordu.
    uyruklar = [b.strip() for _, b in re.findall(
        r"href=\"/players/([a-z]{2}(?:-[a-z]{2,4})?)\"[^>]*>"
        r"\s*<img[^>]*>\s*([A-Za-zÀ-ÿ .'-]+)", t)]
    return {
        "fm_uyruk": (uyruklar[0] if uyruklar else ""),
        "fm_uyruklar": uyruklar,
        "ham": ham,
        "yas": int(m_yas.group(1)) if m_yas else None,
        "boy": int(m_boy.group(1)) if m_boy else None,
        "mevkiler": [x.strip() for x in (m_poz.group(1) if m_poz else "").split(",") if x.strip()],
        "fm_kulup": (m_kul.group(1).strip() if m_kul else ""),
    }


def main():
    from fm_nitelik_esle import cevir

    sinir = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--adet=")), 999))
    esik = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--puan=")), 5))

    satirlar = [r for r in csv.DictReader(open(LISTE, encoding="utf-8-sig"))
                if int(r["Öncelik"]) >= esik]

    onbellek = json.load(open(ONBELLEK, encoding="utf-8")) if ONBELLEK.exists() else {}
    yok = json.load(open(BULUNAMAYAN, encoding="utf-8")) if BULUNAMAYAN.exists() else {}

    oturum = requests.Session()
    oturum.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

    kalan = [r for r in satirlar if r["Oyuncu"] not in onbellek and r["Oyuncu"] not in yok]
    print(f"öncelik ≥{esik}: {len(satirlar)} · çekilmiş: {len(onbellek)} · "
          f"bulunamayan: {len(yok)} · sırada: {len(kalan)}\n", flush=True)

    for i, r in enumerate(kalan[:sinir], 1):
        isim = r["Oyuncu"]
        print(f"[{i}/{min(sinir, len(kalan))}] {isim}", flush=True)
        yol, meta, nasil = ara(oturum, isim,
                               {"kulup": r.get("Kulüp"), "yas": r.get("Yaş")})
        if not yol:
            print("      ✗ FMInside'da bu yazımla yok", flush=True)
            yok[isim] = "arama sonucu yok"
            json.dump(yok, open(BULUNAMAYAN, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            time.sleep(1.5)
            continue

        p = profil(oturum, yol)
        kaleci = any(m.upper().startswith("GK") for m in p["mevkiler"])
        bloklar = cevir(p["ham"], kaleci=kaleci)
        nitelikler = {k: v for blok in bloklar.values() for k, v in blok.items()}

        onbellek[isim] = {
            "url": KOK_URL + yol, "meta": meta, "kaleci": kaleci,
            "fm_yas": p["yas"], "fm_boy": p["boy"], "fm_kulup": p["fm_kulup"],
            "fm_uyruk": p["fm_uyruk"], "fm_uyruklar": p["fm_uyruklar"],
            "mevkiler": p["mevkiler"], "nitelikler": nitelikler, "eslesme": nasil,
        }
        json.dump(onbellek, open(ONBELLEK, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"      ✓ {len(nitelikler)} nitelik{' (KALECİ)' if kaleci else ''} "
              f"· {meta} [{nasil}]", flush=True)
        time.sleep(1.5)

    # fm_sheete_yaz.py'nin beklediği biçim
    json.dump(onbellek, open(BEKLEYEN, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n✓ {len(onbellek)} oyuncu {BEKLEYEN.name} içinde. "
          f"Sheet'e yazmak için: python fm_sheete_yaz.py --kuru")


if __name__ == "__main__":
    main()
