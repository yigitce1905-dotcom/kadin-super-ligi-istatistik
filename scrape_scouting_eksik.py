# -*- coding: utf-8 -*-
"""
'Bulunamadı' işaretli scouting oyuncularını AKILLI yeniden ara — SoccerDonna.
scrape_scouting_yeni.py tam-isimle arayıp ilk sonucu alıyordu; kısaltılmış ad
('P. Peyraud-Magnin'), Korece isim sırası, çok-parçalı adlarda patlıyordu.
Bu script: her isim parçasıyla ara → adayları topla → fuzzy + UYRUK doğrulamasıyla
en iyi eşleşmeyi seç (uyruk en güçlü ayraç). Bulunca profili yazar (bulunamadi'yi siler).

Kullanım:  python scrape_scouting_eksik.py            # tümünü dene
           python scrape_scouting_eksik.py Peyraud    # sadece eşleşen isim (test)
"""
import json, re, sys, time, unicodedata
import requests, urllib3
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
urllib3.disable_warnings()

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
     "Accept-Language": "en-US,en;q=0.9"}
SD_YOL    = "scouting_sd_profiller.json"
KADRO_YOL = "scout_kadro_raporlar.json"
SES = requests.Session(); SES.verify = False

# Uyruk doğrulaması için TR→EN (scout_kadro Türkçe, SD İngilizce)
TR2EN = {
    "Fransa": "France", "Almanya": "Germany", "Hollanda": "Netherlands", "Kanada": "Canada",
    "Avustralya": "Australia", "Norveç": "Norway", "Danimarka": "Denmark", "İzlanda": "Iceland",
    "İsviçre": "Switzerland", "Güney Kore": "South Korea", "İspanya": "Spain", "İngiltere": "England",
    "İtalya": "Italy", "Belçika": "Belgium", "İsveç": "Sweden", "Portekiz": "Portugal",
    "Brezilya": "Brazil", "ABD": "United States", "Amerika": "United States", "Japonya": "Japan",
    "Trinidad ve Tobago": "Trinidad and Tobago", "Nijerya": "Nigeria", "İrlanda": "Ireland",
    "Avusturya": "Austria", "Polonya": "Poland", "Finlandiya": "Finland", "İskoçya": "Scotland",
    "Meksika": "Mexico", "Çin": "China", "Yeni Zelanda": "New Zealand",
}


def _norm(s):
    s = (s or "").upper().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Transliterasyon farkları: Wälti↔Waelti, Müller↔Mueller, Søn↔Son
    for a, b in (("AE", "A"), ("OE", "O"), ("UE", "U"), ("Ø", "O"), ("SS", "S")):
        s = s.replace(a, b)
    return s


def fuzzy(a, b):
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def sd_ara(terim):
    """SoccerDonna soyad/kelime araması → [(isim, url)]."""
    slug = re.sub(r"[^a-z0-9]+", "-", _norm(terim).lower()).strip("-")
    try:
        r = SES.get(f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html",
                    params={"quicksearch": terim}, headers=H, timeout=15)
        soup = BeautifulSoup(r.content, "lxml")
        out = []
        for a in soup.find_all("a", href=re.compile(r"/profil/spieler_\d+")):
            nm = a.get_text(strip=True)
            if nm and len(nm) > 2:
                out.append((nm, "https://www.soccerdonna.de" + a["href"]))
        return out
    except Exception:
        return []


def profil_cek(url):
    try:
        soup = BeautifulSoup(SES.get(url, headers=H, timeout=15).content, "lxml")
    except Exception:
        return {}
    veri = {"profil_url": url}
    GECERLI = {"Date of birth", "Place of birth", "Age", "Name in native country", "Height",
               "Nationality", "2nd Nationality", "Position", "Foot", "Market value",
               "Contract until", "Outfitter", "Debut (Club)"}
    for tablo in soup.find_all("table"):
        txt = tablo.get_text(" ", strip=True)
        if "Date of birth" not in txt and "Position" not in txt:
            continue
        for tr in tablo.find_all("tr"):
            huc = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(huc) >= 2:
                k = huc[0].rstrip(":").strip()
                if k in GECERLI and huc[1].strip():
                    veri[k] = huc[1].strip()
        break
    return veri


def aday_terimleri(isim):
    """Aranacak terimler: kelimeler (kısaltma 'P.' hariç) + tam ad. Korece için her kelime."""
    kelimeler = [w for w in re.split(r"\s+", isim) if len(w.strip(".")) > 1]
    terimler = []
    if kelimeler:
        terimler.append(kelimeler[-1])      # soyad
        if len(kelimeler) > 1:
            terimler.append(kelimeler[0])   # ilk kelime (Korece aile adı)
        terimler.append(" ".join(kelimeler))
    # uniq, sıra korunur
    return list(dict.fromkeys(terimler))


def _tokenlar(isim):
    """Anlamlı kelimeler (kısaltma 'P.' ve tek harf hariç), normalize."""
    return [_norm(w) for w in re.split(r"\s+", isim) if len(w.strip(".")) > 1]


def _ad_uyar(isim, aday_ad):
    """İLK ve SON anlamlı kelime adayda olmalı (orta ad serbest). İlk kelimede
    önek toleransı (Steph↔Stephanie). Korece: hem aile adı hem ad gerektiği için
    'Min-jung Ko' ≠ 'Kim Min-jung' (Kim yok) → reddedilir."""
    a = _norm(aday_ad)
    toks = _tokenlar(isim)
    if not toks:
        return False
    son = toks[-1]
    if son not in a:
        return False
    ilk = toks[0]
    if ilk == son or ilk in a:
        return True
    for w in a.split():                         # önek paylaşımı (≥4 harf)
        if len(ilk) >= 4 and len(w) >= 4 and (ilk[:4] == w[:4]):
            return True
    return False


def _tum_token_uyar(isim, aday_ad):
    a = _norm(aday_ad)
    toks = _tokenlar(isim)
    return bool(toks) and all(t in a for t in toks)


def _uyruk_uyar(uyruk_en, nat):
    """Ülke kelime-örtüşmesi: 'South Korea' ~ 'Korea, South', 'Canada' ⊂ 'CanadaJamaica'."""
    if not uyruk_en or not nat:
        return False
    nat_n = _norm(nat)
    return all((w in nat_n) for w in _norm(uyruk_en).split() if len(w) > 2)


def en_iyi_eslesme(isim, uyruk_en):
    adaylar = {}
    for terim in aday_terimleri(isim):
        for nm, url in sd_ara(terim):
            adaylar.setdefault(url, nm)
        time.sleep(0.4)
        if len(adaylar) >= 30:
            break
    # KATI ön-filtre: adayın adı oyuncunun tüm kelimelerini içermeli
    uygun = [(url, nm) for url, nm in adaylar.items() if _ad_uyar(isim, nm)]
    uygun.sort(key=lambda kv: fuzzy(isim, kv[1]), reverse=True)
    en_iyi, en_skor = None, 0.0
    for url, nm in uygun[:4]:
        p = profil_cek(url)
        time.sleep(0.4)
        uok = _uyruk_uyar(uyruk_en, p.get("Nationality", ""))
        skor = fuzzy(isim, nm) + (0.5 if uok else 0.0)
        if skor > en_skor:
            en_skor, en_iyi = skor, (nm, p, fuzzy(isim, nm), uok)
    return en_iyi, en_skor


def main():
    test = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    kadro = json.load(open(KADRO_YOL, encoding="utf-8"))
    sd = json.load(open(SD_YOL, encoding="utf-8"))
    hedef = [n for n in kadro
             if isinstance(sd.get(n), dict) and sd[n].get("bulunamadi")
             and (not test or test.lower() in n.lower())]
    print(f"Yeniden aranacak: {len(hedef)}")
    bulundu = 0
    for i, isim in enumerate(hedef, 1):
        uyruk_en = TR2EN.get(kadro[isim].get("vatandaslik", ""), "")
        print(f"[{i}/{len(hedef)}] {isim} (uyruk={uyruk_en or '?'}) ...", end=" ", flush=True)
        en_iyi, skor = en_iyi_eslesme(isim, uyruk_en)
        # Kabul: ilk+son ad eşleşmesi (ön-filtre) + UYRUK doğrulandı VEYA isim ~birebir
        if en_iyi and (en_iyi[3] or en_iyi[2] >= 0.85):
            nm, p, fs, uok = en_iyi
            p["sd_isim"] = nm
            p["es_skoru"] = round(fs, 3)
            p["vatandaslik"] = kadro[isim].get("vatandaslik", "")
            sd[isim] = p
            bulundu += 1
            print(f"✓ {nm} | {p.get('Nationality','?')} | {p.get('Position','?')}")
        else:
            print("✗")
        if i % 10 == 0:
            json.dump(sd, open(SD_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(sd, open(SD_YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[OK] {bulundu}/{len(hedef)} bulundu → {SD_YOL}")


if __name__ == "__main__":
    main()
