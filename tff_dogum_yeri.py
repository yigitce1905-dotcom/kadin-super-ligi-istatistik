# -*- coding: utf-8 -*-
"""TFF DOĞUM YERİ TAMAMLAMA — SoccerDonna'da doğum yeri boş olan TR süper lig
oyuncularını TFF profillerinden doldurur (Yiğit: sadece eksikleri, tek tek).

Akış:
 1) Hedef = oyuncular.json ∩ (SD "Place of birth" boş).
 2) kisiId: önce manual_ages.json (source: TFF kisiID=…); kalanı sezon maç
    detay sayfalarından hasat (scraper.py fonksiyonları; tüm hedef bulununca durur).
 3) Her hedefin TFF profilinden (pageId=30&kisiId=) "Doğum Yeri" çekilir.
 4) tff_dogum_yeri.json  ({isim: {"dogum_yeri":…, "kisiId":…}}).

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
hedef = [k for k in tr_isimler if not (sd.get(k, {}) or {}).get("Place of birth", "").strip()]
hedef_norm = {n(k): k for k in hedef}
print(f"Hedef (SD doğum yeri boş): {len(hedef)} oyuncu")

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

# ── 3) TFF profilinden Doğum Yeri ──
def tff_dogum_yeri(kid):
    url = f"https://www.tff.org/Default.aspx?pageId=30&kisiId={kid}"
    try:
        r = requests.get(url, headers=H, timeout=18, verify=False)
        tx = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    except Exception:
        return ""
    m = re.search(r"Doğum Yeri\s*:?\s*([A-Za-zÇĞİÖŞÜçğıöşü\.\- ]{2,40}?)\s*Doğum Tarihi", tx)
    return _tr_baslik(m.group(1).strip()) if m else ""

cikti = {}
for i, (isim, kid) in enumerate(isim_kisi.items(), 1):
    dy = tff_dogum_yeri(kid)
    if dy:
        cikti[isim] = {"dogum_yeri": dy, "kisiId": kid}
    if i % 15 == 0:
        print(f"    profil {i}/{len(isim_kisi)}…")
    time.sleep(0.3)

json.dump(cikti, open(KOK / "tff_dogum_yeri.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\n[OK] {len(cikti)} oyuncunun doğum yeri TFF'den alındı → tff_dogum_yeri.json")
for k, v in list(cikti.items())[:8]:
    print(f"   {k[:26]:26} → {v['dogum_yeri']}")
