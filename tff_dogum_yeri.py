# -*- coding: utf-8 -*-
"""TFF DOĞUM YERİ + DOĞUM TARİHİ TAMAMLAMA — SoccerDonna'da doğum yeri/yaşı boş
olan TR süper lig oyuncularını TFF profillerinden doldurur (Yiğit: sadece
eksikleri, tek tek; 2026-09-15: "yaş None yazması hoş durmuyor" — SD'de hiç
profili olmayan ~49 oyuncu için app.py'nin _yas() zinciri artık bu dosyayı da
okuyor, bkz. app.py _tff_yas_harita()).

Akış:
 1) Hedef = oyuncular.json ∩ (SD "Place of birth" boş VEYA yaş hesaplanamıyor).
 2) kisiId: önce manual_ages.json (source: TFF kisiID=…); kalanı sezon maç
    detay sayfalarından hasat (scraper.py fonksiyonları; tüm hedef bulununca durur).
 3) Her hedefin TFF profilinden (pageId=30&kisiId=) "Doğum Yeri" VE "Doğum
    Tarihi" çekilir.
 4) tff_dogum_yeri.json  ({isim: {"dogum_yeri":…, "dogum_tarihi":…, "kisiId":…}}).

Kullanım:  python tff_dogum_yeri.py
"""
import json, re, sys, time, unicodedata
from pathlib import Path
import requests
from bs4 import BeautifulSoup

import scraper as S   # fetch, _kisi_links, mac_linklerini_topla (module-level güvenli)

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
requests.packages.urllib3.disable_warnings()

def n(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())

_TR_AY = {"ocak":1, "şubat":2, "subat":2, "mart":3, "nisan":4, "mayıs":5, "mayis":5,
          "haziran":6, "temmuz":7, "ağustos":8, "agustos":8, "eylül":9, "eylul":9,
          "ekim":10, "kasım":11, "kasim":11, "aralık":12, "aralik":12}

def _tr_baslik(s):
    """Türkçe-doğru başlık düzeni (İ/I korunur; .title() combining-dot bug'ı yok)."""
    low = str(s).replace("I", "ı").replace("İ", "i").lower()
    return " ".join(w[:1].replace("i", "İ").replace("ı", "I").upper() + w[1:]
                    for w in low.split())

# ── 1) Hedef listesi ──
oy = json.load(open(KOK / "oyuncular.json", encoding="utf-8"))
sd = json.load(open(KOK / "soccerdonna_profiller.json", encoding="utf-8"))
man = json.load(open(KOK / "manual_ages.json", encoding="utf-8"))
tr_isimler = [o["oyuncu"] for o in oy]

def _yasi_var_mi(isim):
    """app.py _yas()'in aynısı — manuel/SD'den yaş çıkarılabiliyor mu."""
    if isim in man:
        return True
    p = sd.get(isim, {}) or {}
    try:
        age = float(str(p.get("Age", "")).split()[0])
        if 15 <= age <= 40:
            return True
    except Exception:
        pass
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", p.get("Date of birth", "") or "")
    if m:
        import datetime as _dt
        g, a, y = map(int, m.groups())
        t = _dt.date.today()
        yas = t.year - y - ((t.month, t.day) < (a, g))
        if 15 <= yas <= 40:
            return True
    return False

hedef = [k for k in tr_isimler
         if not (sd.get(k, {}) or {}).get("Place of birth", "").strip()
         or not _yasi_var_mi(k)]
hedef_norm = {n(k): k for k in hedef}
print(f"Hedef (SD doğum yeri VEYA yaşı boş): {len(hedef)} oyuncu")

# ── 2) kisiId eşleştirme (önce ÖNBELLEK: önceki çıktı → 10dk hasat tekrar etmesin) ──
isim_kisi = {}   # gerçek_isim → kisiId
_onbellek = KOK / "tff_dogum_yeri.json"
if _onbellek.exists():
    for k, v in json.load(open(_onbellek, encoding="utf-8")).items():
        if k in hedef and v.get("kisiId"):
            isim_kisi[k] = v["kisiId"]
    print(f"  önbellekten kisiId: {len(isim_kisi)}")
for k in hedef:
    m = re.search(r"kisiID=(\d+)", (man.get(k, {}) or {}).get("source", ""))
    if m and k not in isim_kisi:
        isim_kisi[k] = m.group(1)
print(f"  + manual_ages ile toplam kisiId: {len(isim_kisi)}")

kalan = {kn: gk for kn, gk in hedef_norm.items() if gk not in isim_kisi}
if kalan:
    print(f"  {len(kalan)} oyuncu için sezon maçlarından kisiId hasadı…")
    sess = requests.Session()
    for hafta in range(1, S.TOPLAM_HAFTA + 1):
        if not kalan:
            break
        maclar = S.mac_linklerini_topla(sess, hafta)
        print(f"    [{hafta:2d}. hafta] {len(maclar)} maç · kalan hedef: {len(kalan)}")
        for mac in maclar:
            if not kalan:
                break
            soup = S.fetch(sess, mac["url"])
            if not soup:
                continue
            for kid, (isim, _sp) in S._kisi_links(soup).items():
                ni = n(isim)
                if ni in kalan:
                    isim_kisi[kalan.pop(ni)] = kid
            time.sleep(0.4)
        time.sleep(0.6)
print(f"kisiId bulunan toplam: {len(isim_kisi)} / {len(hedef)}")

# ── 3) TFF profilinden Doğum Yeri + Doğum Tarihi ──
def tff_profil_kunye(kid):
    url = f"https://www.tff.org/Default.aspx?pageId=30&kisiId={kid}"
    try:
        r = requests.get(url, headers=H, timeout=18, verify=False)
        tx = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    except Exception:
        return "", ""
    yer = re.search(r"Doğum Yeri\s*:?\s*([A-Za-zÇĞİÖŞÜçğıöşü\.\- ]{2,40}?)\s*Doğum Tarihi", tx)
    dogum_yeri = _tr_baslik(yer.group(1).strip()) if yer else ""
    # TFF profilinde tarih SAYIYLA değil Türkçe ay adıyla yazılı: "19 Aralık 1999"
    # (ilk versiyon "\d{2}[./]\d{2}[./]\d{4}" arıyordu → 99 profilde de 0 eşleşme).
    tarih = re.search(r"Doğum Tarihi\s*:?\s*(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})", tx)
    dogum_tarihi = ""
    if tarih:
        gun, ay_adi, yil = tarih.groups()
        ay = _TR_AY.get(ay_adi.strip().lower())
        if ay:
            dogum_tarihi = f"{int(gun):02d}.{ay:02d}.{yil}"
    return dogum_yeri, dogum_tarihi

# Önceki çıktıyı koru (bu run'da hedef dışı kalanlar silinmesin) — yeni alanlarla merge.
onceki_cikti = {}
if _onbellek.exists():
    onceki_cikti = json.load(open(_onbellek, encoding="utf-8"))

cikti = dict(onceki_cikti)
for i, (isim, kid) in enumerate(isim_kisi.items(), 1):
    dy, dt_ = tff_profil_kunye(kid)
    if dy or dt_:
        kayit = {"kisiId": kid}
        if dy: kayit["dogum_yeri"] = dy
        if dt_: kayit["dogum_tarihi"] = dt_
        cikti[isim] = kayit
    if i % 15 == 0:
        print(f"    profil {i}/{len(isim_kisi)}…")
    time.sleep(0.3)

json.dump(cikti, open(KOK / "tff_dogum_yeri.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
yeni_yas = sum(1 for k, v in cikti.items() if k in isim_kisi and v.get("dogum_tarihi"))
print(f"\n[OK] {len(cikti)} kayıt (toplam) → tff_dogum_yeri.json"
      f"  ({yeni_yas} oyuncuya bu run'da doğum tarihi eklendi/güncellendi)")
for k, v in list(cikti.items())[:8]:
    print(f"   {k[:26]:26} → {v.get('dogum_yeri','—')} · {v.get('dogum_tarihi','—')}")
