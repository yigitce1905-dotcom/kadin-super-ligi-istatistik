"""
SoccerDonna Zenginleştirme Scraper'ı
oyuncular.json'daki her oyuncuyu SoccerDonna'da arar,
profil bilgilerini çekip soccerdonna_profiller.json'a kaydeder.
"""

import datetime, json, re, time, unicodedata
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

CIKTI     = "soccerdonna_profiller.json"
BEKLEME   = 1.5    # istek arası bekleme (saniye)
ES_SINIRI = 0.55   # display-isim fuzzy match eşiği (0-1) — son çare fallback

# 2026-09-08 (Yiğit: "Paola Ellis ve Katie Bowen'ın yaşları hatalı"): eski mantık
# sadece arama sonucundaki KISA görünen ismi (ör. "Kelisha Bowens") TFF'nin TAM
# adıyla (ör. "KATE ELIZABETH BOWEN") SequenceMatcher ile kıyaslıyordu — bu, uzun
# TFF adlarını (orta isim eksik görünen doğru eşleşmeleri) haksız yere cezalandırıp
# rastgele karakter örtüşmesi yüksek olan YANLIŞ kişileri öne çıkarabiliyordu.
# Gerçek çare: SoccerDonna'nın her profilde tuttuğu "Name in native country" alanı
# (oyuncunun TAM/resmi adı) — bu, kısa takma-ad yerine gerçek kimliği verir.
# Artık: DISPLAY_YUKSEK üstü net eşleşmeler hızlı yoldan geçer (ekstra istek yok);
# belirsiz/düşük skorlu adaylarda en iyi ADAY_LIMIT aday için TAM profil çekilip
# "Name in native country" TFF adıyla token-bazlı (kelime sırasız + orta isim
# eksik/fazla toleranslı) karşılaştırılır — gerçek kimlik bu şekilde doğrulanır.
DISPLAY_YUKSEK = 0.85   # bu skorun üstünde native-doğrulama atlanır (hızlı yol)
NATIVE_SINIRI  = 0.6    # native-isim token-skoru bu değerin altındaysa reddedilir
# NOT (test): ADAY_LIMIT=6 iken doğru kişi ("Blue Ellis", "Jessica Silva") kısa
# görünen adı yüzünden display-skor sıralamasında ilk 6'ya bile girmiyordu —
# tam da bu scraper'ın düzeltmeye çalıştığı önyargı. 20'ye çıkarıldı (soyad
# aramaları genelde <40 sonuç veriyor); maliyet yalnız BELİRSİZ vakalarda ödenir.
ADAY_LIMIT     = 20     # native-doğrulama için TAM profili çekilecek en fazla aday

_STOPWORD = {"DE", "DA", "DO", "DOS", "DAS", "DEL", "DELLA", "VAN", "VON",
             "EL", "AL", "BINTI", "BIN", "Y", "E", "AND", "&"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.soccerdonna.de/en/",
}


def temizle(metin: str) -> str:
    """Büyük harf, Türkçe/özel karakter → ASCII benzeri karşılaştırma için."""
    metin = metin.upper().strip()
    # Unicode normalize: "Č" → "C" gibi
    metin = unicodedata.normalize("NFD", metin)
    metin = "".join(c for c in metin if unicodedata.category(c) != "Mn")
    return metin


def eslesme_skoru(isim1: str, isim2: str) -> float:
    return SequenceMatcher(None, temizle(isim1), temizle(isim2)).ratio()


def native_eslesme_skoru(tff_isim: str, native_isim: str) -> float:
    """TFF'nin tam adı ile SD'nin 'Name in native country' alanını kıyaslar.
    Kelime sırasından bağımsız + orta isim eksik/fazla toleranslı (Jaccard,
    bağlaç/edat kelimeleri hariç) ile ham karakter-dizisi benzerliğinin (sıralı
    token'lar üstünden, transliterasyon/yazım farkına dayanıklı) BÜYÜĞÜ alınır —
    ikisi de düşük çıkarsa gerçekten farklı kişidir (bkz. Ellis/Bowen vakaları)."""
    if not tff_isim or not native_isim:
        return 0.0
    t1 = set(temizle(tff_isim).split())
    t2 = set(temizle(native_isim).split())
    if not t1 or not t2:
        return 0.0
    t1e, t2e = t1 - _STOPWORD, t2 - _STOPWORD
    if not t1e or not t2e:
        t1e, t2e = t1, t2
    birlik = t1e | t2e
    jaccard = len(t1e & t2e) / len(birlik) if birlik else 0.0
    dizi = SequenceMatcher(None, " ".join(sorted(t1e)), " ".join(sorted(t2e))).ratio()
    return max(jaccard, dizi)


def soyadi_cikart(tam_isim: str) -> str:
    """Son kelimeyi soyad olarak döndür."""
    parcalar = tam_isim.strip().split()
    return parcalar[-1] if parcalar else tam_isim


def _ilk_isim(tam_isim: str) -> str:
    parcalar = tam_isim.strip().split()
    return parcalar[0] if parcalar else tam_isim


def kisayol_skoru(tff_isim: str, aday_isim: str) -> float:
    """Native-doğrulama kısa listesine kimin gireceğini belirleyen ön-eleme
    skoru — tam_skor (eski davranış) ile İLK İSİM eşleşmesinin büyüğü.
    Neden: soyad zaten ara()'nın kendisinde filtrelendi; ilk isim eşleşmesi
    çok daha güçlü bir kimlik sinyali, ama TFF'nin uzun tam adı ('JESSICA
    LISANDRA MAJENJE NOGUEIRA DA SILVA') SD'nin kısa görünen adına ('Jessica
    Silva') karşı ham SequenceMatcher'da haksız düşük çıkıyor — kalabalık
    soyad havuzlarında (ör. 'Silva' → 800+ sonuç) doğru aday ilk ADAY_LIMIT'e
    hiç girmiyordu. Yalnız SIRALAMA için kullanılır; kabul kararı hâlâ ya
    DISPLAY_YUKSEK'teki tam_skor ya da native doğrulamadan geçer."""
    tam_skor = eslesme_skoru(tff_isim, aday_isim)
    ilk_skor = SequenceMatcher(None, temizle(_ilk_isim(tff_isim)), temizle(_ilk_isim(aday_isim))).ratio()
    return max(tam_skor, ilk_skor)


def ara(session, soyad: str):
    """SoccerDonna'da soyada göre ara. {isim: ..., url: ...} listesi döner."""
    slug = soyad.lower().replace(" ", "-")
    url  = f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html"
    try:
        r = session.get(url, params={"quicksearch": soyad}, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.content, "lxml")
        sonuclar = []
        for a in soup.find_all("a", href=re.compile(r"/profil/spieler_\d+")):
            isim = a.get_text(strip=True)
            if isim and len(isim) > 2:
                tam_url = "https://www.soccerdonna.de" + a["href"]
                sonuclar.append({"isim": isim, "url": tam_url})
        return sonuclar
    except Exception:
        return []


def profil_cek(session, profil_url: str) -> dict:
    """Profil sayfasından tüm bilgileri çeker."""
    try:
        r = session.get(profil_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.content, "lxml")

        veri = {"profil_url": profil_url}

        # Bilgi tablosunu bul
        GECERLI_ANAHTARLAR = {
            "Date of birth", "Place of birth", "Age", "Name in native country",
            "Height", "Nationality", "2nd Nationality", "Position", "Foot",
            "Market value", "Contract until", "Outfitter", "Debut (Club)"
        }
        for tablo in soup.find_all("table"):
            txt = tablo.get_text(" ", strip=True)
            if "Date of birth" not in txt and "Position" not in txt:
                continue
            for tr in tablo.find_all("tr"):
                huc = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if len(huc) >= 2:
                    anahtar = huc[0].rstrip(":").strip()
                    deger   = huc[1].strip()
                    if anahtar in GECERLI_ANAHTARLAR and deger:
                        veri[anahtar] = deger
            break

        # Kulüp fotoğraf alt metni (bazen mevcut kulüp burada)
        img = soup.find("img", {"class": re.compile(r"vereinlogo|club")})
        if img and img.get("alt"):
            veri["Mevcut Kulüp"] = img["alt"]

        # SD'nin ham "Age" alanı yeni eklenen profillerde bazen "0"/boş geliyor
        # (SD kendi tarafında henüz senkron değil) — "Date of birth" güvenilirse
        # ondan hesapla (Yiğit, 2026-09-01: Rita Doku vb. bu yüzden yaşsız
        # görünüyordu, sitede de aynı sorun tekrarlamasın diye kaynağında düzeltildi).
        _ham_yas = str(veri.get("Age", "")).strip()
        try:
            _yas_gecerli = 13 <= float(_ham_yas.split()[0]) <= 45
        except Exception:
            _yas_gecerli = False
        if not _yas_gecerli and veri.get("Date of birth"):
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", veri["Date of birth"])
            if m:
                g, a, y = map(int, m.groups())
                bugun = datetime.date.today()
                hesap_yas = bugun.year - y - ((bugun.month, bugun.day) < (a, g))
                if 13 <= hesap_yas <= 45:
                    veri["Age"] = str(hesap_yas)

        return veri
    except Exception:
        return {}


def ana_calistir():
    print("=" * 60)
    print("  SoccerDonna Zenginleştirme Scraper'ı")
    print("=" * 60)

    with open("oyuncular.json", encoding="utf-8") as f:
        oyuncular = json.load(f)

    # Mevcut sonuçları yükle (kaldığı yerden devam)
    try:
        with open(CIKTI, encoding="utf-8") as f:
            mevcut = json.load(f)
    except FileNotFoundError:
        mevcut = {}

    session = requests.Session()
    basarili = len([v for v in mevcut.values() if v])
    atlan    = 0

    for i, oyuncu in enumerate(oyuncular, 1):
        tam_isim = oyuncu["oyuncu"]

        # Zaten işlendiyse atla
        if tam_isim in mevcut:
            atlan += 1
            continue

        soyad = soyadi_cikart(tam_isim)
        print(f"[{i:3d}/{len(oyuncular)}] {tam_isim[:40]:<40} (soyad: {soyad})")

        sonuclar = ara(session, soyad)
        time.sleep(BEKLEME)

        if not sonuclar:
            # İlk isimle dene
            ad = tam_isim.split()[0] if " " in tam_isim else tam_isim
            sonuclar = ara(session, ad)
            time.sleep(BEKLEME)

        # Kabul kararı için ham display-skor (DISPLAY_YUKSEK hızlı yolu bunu kullanır)
        skorlu = sorted(
            ((eslesme_skoru(tam_isim, s["isim"]), s) for s in sonuclar),
            key=lambda x: -x[0],
        )
        # Native-doğrulama kısa listesine kimin gireceği: ilk-isim-ağırlıklı
        # ön-eleme skoru (kalabalık soyad havuzlarında doğru adayı üste çeker)
        kisa_liste = sorted(
            ((kisayol_skoru(tam_isim, s["isim"]), s) for s in sonuclar),
            key=lambda x: -x[0],
        )

        en_iyi = en_iyi_profil = None
        en_iyi_skor = 0.0
        yontem = "yok"

        if skorlu and skorlu[0][0] >= DISPLAY_YUKSEK:
            # Net eşleşme — native-doğrulama için ekstra istek atmaya gerek yok
            en_iyi_skor, en_iyi = skorlu[0]
            yontem = "display"
        elif skorlu:
            # Belirsiz/düşük skor: en iyi ADAY_LIMIT adayın TAM profilini çekip
            # gerçek kimliği "Name in native country" alanından doğrula
            en_native_skor = 0.0
            en_native = en_native_profil = None
            for _, aday in kisa_liste[:ADAY_LIMIT]:
                profil = profil_cek(session, aday["url"])
                time.sleep(BEKLEME)
                native = profil.get("Name in native country", "")
                n_skor = native_eslesme_skoru(tam_isim, native)
                if n_skor > en_native_skor:
                    en_native_skor, en_native, en_native_profil = n_skor, aday, profil

            if en_native and en_native_skor >= NATIVE_SINIRI:
                en_iyi, en_iyi_skor, en_iyi_profil = en_native, en_native_skor, en_native_profil
                yontem = "native"
            elif skorlu[0][0] >= ES_SINIRI:
                # native-doğrulama da netleştiremedi — eski düşük-güven fallback
                # (şüpheli eşleşme olarak es_skoru<0.75 ile işaretli kalır)
                en_iyi_skor, en_iyi = skorlu[0]
                yontem = "display-dusuk"

        if en_iyi:
            print(f"    ✓ Bulundu [{yontem}]: {en_iyi['isim']} (skor: {en_iyi_skor:.2f})")
            profil = en_iyi_profil if en_iyi_profil is not None else profil_cek(session, en_iyi["url"])
            if en_iyi_profil is None:
                time.sleep(BEKLEME)
            profil["sd_isim"]   = en_iyi["isim"]
            profil["es_skoru"]  = round(en_iyi_skor, 3)
            profil["es_yontem"] = yontem
            mevcut[tam_isim]    = profil
            basarili           += 1
        else:
            print(f"    ✗ Bulunamadı (en iyi skor: {(skorlu[0][0] if skorlu else 0.0):.2f})")
            mevcut[tam_isim] = {}

        # Her 20 oyuncuda bir kaydet
        if i % 20 == 0:
            with open(CIKTI, "w", encoding="utf-8") as f:
                json.dump(mevcut, f, ensure_ascii=False, indent=2)
            print(f"    [Ara kayıt: {basarili} başarılı / {i} işlendi]")

    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(mevcut, f, ensure_ascii=False, indent=2)

    print(f"\nBitti! {basarili}/{len(oyuncular)} oyuncu için profil çekildi → {CIKTI}")


if __name__ == "__main__":
    ana_calistir()
