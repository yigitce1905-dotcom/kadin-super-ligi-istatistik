# -*- coding: utf-8 -*-
"""SoccerDonna'yı sheet'in ÜSTÜNE yaz (Yiğit, 2026-10-19: "excelde soccerdonna ile uyuşmayan veri
varsa ez, soccerdonnadakini kullan").

Sheet (Baran'ın 'Scouting is life' dosyası) ↔ SoccerDonna profili uyuşmazsa SD kazanır:
  • doğum tarihi (+ yaş doğumdan yeniden hesaplanır)   • boy   • güçlü ayak (SD 'Both' hariç)
Kulüp ve sözleşme zaten SD-öncelikli (kulup_guncelle / _kontrat_guncel); burada dokunulmaz.

GÜVENLİK: aynı isimli BAŞKA oyuncunun SD profili eşleşmiş olabilir (ör. Burkina'da Zongo/Sawadogo).
Bu yüzden eşleşme GÜVENİLİR değilse hiçbir alan ezilmez, 'şüpheli' listesine yazılır:
  • uyruk hiç örtüşmüyorsa, veya • doğum tarihi farkı 1 yılı geçiyorsa.
  (Sheet'teki doğum yılı imkânsızsa — ör. 2994 — SD'ye güvenilir.)
Ayak kuralı app._ayak_goster ile aynı (Baran): SD 'Both' derse sheet'teki ayak korunur.
"""
import re, datetime, unicodedata

NATMAP = {"turkiye": "turkey", "abd": "united states", "usa": "united states", "ingiltere": "england"}


def _n(s):
    s = unicodedata.normalize("NFD", str(s or "").replace("ı", "i").replace("İ", "I")
                              .replace("ø", "o").replace("ł", "l").replace("đ", "d"))
    return re.sub(r"[^a-z ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn").lower()).strip()


def _dt(s):
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", str(s or ""))
    if not m:
        return None
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _dt_makul(d):
    return d is not None and 1955 <= d.year <= 2014


def _cm(s):
    m = re.search(r"\d+(?:\.\d+)?", str(s or "").strip().replace(",", "."))
    if not m:
        return None
    v = float(m.group())
    v = int(round(v * 100 if v < 3 else v))
    return v if 120 <= v <= 210 else None


def _ayak(s):
    s = str(s or "").strip().lower()
    if s in ("sağ", "sag", "right"):
        return "Sağ"
    if s in ("sol", "left"):
        return "Sol"
    if s in ("both", "çift", "cift", "iki ayak"):
        return "Çift"
    return None


def _natset(s):
    parts = re.findall(r"[A-Z][a-z'’.\-]+(?:\s[A-Z][a-z'’.\-]+)*", str(s or ""))
    return {NATMAP.get(_n(p), _n(p)) for p in parts if p}


def _ulke_benzer(a, b):
    """Ülke adı yazım/dil farkları (Botswana~Botsuana, Danmark~Denmark, Czezchia~Czech Republic)."""
    from difflib import SequenceMatcher
    return a == b or a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.72


def _ayni_kisi(r, s):
    sh = {NATMAP.get(_n(x), _n(x)) for x in (r.get("vatandaslik"), r.get("uyruk"), r.get("milli_takim")) if x}
    sdn = _natset(s.get("Nationality"))
    if not sh or not sdn:
        return None
    return any(_ulke_benzer(a, b) for a in sh for b in sdn)


def guvenilir(r, s):
    """(True/False, neden). False → o oyuncuda SD'ye dokunma, şüpheli listesine yaz.
    Doğum tarihi birebir aynıysa aynı kişidir (uyruk adı farkı önemsiz); fark 1 yılı geçiyorsa başka kişi
    olabilir; tarih yoksa/yakınsa uyruk örtüşmesine bakılır."""
    a, b = _dt(r.get("dogum")), _dt(s.get("Date of birth"))
    if a and b and _dt_makul(a):
        gun = abs((a - b).days)
        if gun == 0:
            return True, ""
        if gun > 366:
            return False, f"doğum tarihi farkı {gun} gün"
    if _ayni_kisi(r, s) is False:
        return False, "uyruk örtüşmüyor"
    return True, ""


def uygula(kayitlar, sd_bul, kaynak):
    """kayitlar: {isim: sheet_kaydi}; sd_bul(isim, kayit) → SD profil dict | None.
    Yerinde günceller. Döner: (degisim_listesi, suphe_listesi)."""
    deg, suphe = [], []
    for isim, r in kayitlar.items():
        s = sd_bul(isim, r)
        if not isinstance(s, dict):
            continue
        ok, neden = guvenilir(r, s)
        if not ok:
            suphe.append({"kaynak": kaynak, "isim": isim, "neden": neden,
                          "sheet_dogum": r.get("dogum"), "sd_dogum": s.get("Date of birth"),
                          "sheet_uyruk": r.get("vatandaslik") or r.get("uyruk"),
                          "sd_uyruk": s.get("Nationality"), "sd_url": s.get("profil_url")})
            continue

        def yaz(alan, eski, yeni):
            deg.append({"kaynak": kaynak, "isim": isim, "alan": alan, "sheet": eski, "sd": yeni})
            r[alan] = yeni

        # doğum tarihi
        sd_d, sh_d = _dt(s.get("Date of birth")), _dt(r.get("dogum"))
        if sd_d and _dt_makul(sd_d) and (sh_d is None or not _dt_makul(sh_d) or sh_d != sd_d):
            yaz("dogum", r.get("dogum"), s["Date of birth"].strip())
        # boy
        sd_b, sh_b = _cm(s.get("Height")), _cm(r.get("boy"))
        if sd_b and sd_b != sh_b:
            yaz("boy", r.get("boy"), s["Height"].strip())
        # güçlü ayak (SD 'Both' → sheet'i koru; sheet boşsa SD ne diyorsa)
        sd_a, sh_a = _ayak(s.get("Foot")), _ayak(r.get("ayak"))
        if sd_a in ("Sağ", "Sol") and sd_a != sh_a:
            yaz("ayak", r.get("ayak"), sd_a)
        elif sd_a == "Çift" and not sh_a:
            yaz("ayak", r.get("ayak"), "Çift")
    return deg, suphe


def tr_sd_bulucu(tsd):
    """soccerdonna_profiller.json (BÜYÜK HARF tam isim anahtarlı) için bulucu: tam isim → ad+soyad (TEK aday)."""
    harita = {_n(k): v for k, v in tsd.items() if isinstance(v, dict) and v.get("profil_url")}
    ilk_son = {}
    for k, v in harita.items():
        p = k.split()
        if len(p) >= 2:
            ilk_son.setdefault((p[0], p[-1]), []).append(v)

    def bul(isim, r):
        for aday in (r.get("tam_isim"), isim):
            if aday and _n(aday) in harita:
                return harita[_n(aday)]
        p = _n(isim).split()
        if len(p) >= 2:
            c = ilk_son.get((p[0], p[-1]), [])
            if len(c) == 1:
                return c[0]
        return None
    return bul
