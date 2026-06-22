# -*- coding: utf-8 -*-
"""
U15 Genç Kızlar (İstanbul) scraper — tffistanbul.org
Gruplar A/B/C → her hafta → her maç-detayı → İlk 11 + Yedekler oyuncuları topla.
Çıktı altlig_u15.json, altlig_u17.json ile BİREBİR aynı şemada (app reuse eder).

Maç-detay ikonları: icon-soccer-ball=gol, icon-in=oyuna girdi, icon-out=çıktı,
icon-yellow-card / icon-red-card. 'Teknik Kadro' bölümü (yönetici/antrenör) hariç.

Kullanım:  python scraper_u15.py
"""
import requests, urllib3, re, json, time, datetime
from bs4 import BeautifulSoup
from collections import defaultdict
urllib3.disable_warnings()

H        = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE     = "https://tffistanbul.org"
LIG_BASE = BASE + "/puantaj-ve-fikstur/2025-2026/u15-genc-kizlar/29/307"
GRUPLAR  = {"A": 6032, "B": 6033, "C": 6038}
SES = requests.Session(); SES.verify = False


def fetch(url, tries=3):
    for i in range(tries):
        try:
            r = SES.get(url, headers=H, timeout=25)
            if r.status_code == 200:
                return BeautifulSoup(r.content, "lxml")
        except Exception:
            pass
        time.sleep(2)
    return None


def grup_maclari(grup_id):
    """Haftaları (1..30) gez, benzersiz maç URL'lerini (macId) topla.
    grup/{hafta} penceresi N ve N+1'i gösterir → dedup şart."""
    bulunan = {}
    bos = 0
    for hafta in range(1, 31):
        soup = fetch(f"{LIG_BASE}/{grup_id}/{hafta}")
        yeni = 0
        if soup:
            for a in soup.find_all("a", href=True):
                h = a["href"]
                if not h.startswith("/mac/"):
                    continue
                m = re.search(r"/(\d+)-haftasi/.*/(\d+)$", h)
                if not m:
                    continue
                hf, mac_id = int(m.group(1)), m.group(2)
                if mac_id in bulunan:
                    continue
                bulunan[mac_id] = {"url": BASE + h, "hafta": hf}
                yeni += 1
        bos = bos + 1 if yeni == 0 else 0
        if bos >= 4:
            break
        time.sleep(0.3)
    return list(bulunan.values())


def mac_detay(url):
    """Maç-detay → İki lineup tablosu (tablo0=ev, tablo1=dep) + temiz takım adları
    (h5.game-result__team-name) → oyuncu olay kayıtları. Oynanmamışsa []."""
    soup = fetch(url)
    if not soup:
        return []
    adlar = [h.get_text(strip=True) for h in soup.select("h5.game-result__team-name")]
    tablolar = [t for t in soup.select("table") if t.select(".lineup__name")]
    cikti = []
    for ti, t in enumerate(tablolar[:2]):
        takim = adlar[ti] if ti < len(adlar) else ""
        bolum = ""
        for tr in t.select("tr"):
            sub = tr.select_one(".lineup__subheader")
            if sub:
                bolum = sub.get_text(strip=True)
                continue
            a = tr.select_one('.lineup__name a[href*="/futbolcu/"]')
            if not a:
                continue
            if ("İlk 11" not in bolum) and ("Yedek" not in bolum):
                continue  # Teknik Kadro (yönetici/antrenör) hariç
            mid = re.search(r"/futbolcu/[^/]+/(\d+)", a["href"])
            kid = mid.group(1) if mid else a.get_text(strip=True)
            info = tr.select_one(".lineup__info")
            cls = " ".join(" ".join(i.get("class", [])) for i in info.select("i")) if info else ""
            ilk11 = "İlk 11" in bolum
            cikti.append({
                "kisi_id": kid, "oyuncu": a.get_text(strip=True), "takim": takim,
                "ilk11": ilk11, "oynadi": ilk11 or ("icon-in" in cls),
                "gol": cls.count("icon-soccer-ball"),
                "sari": cls.count("icon-yellow-card"), "kirmizi": cls.count("icon-red-card"),
            })
    return cikti


def main():
    oy = defaultdict(lambda: {"oyuncu": "", "takimlar": [], "grup": None,
                              "mac": 0, "ilk11": 0, "yedek": 0, "gol": 0, "sari": 0, "kirmizi": 0})
    toplam_mac = 0
    for gad, gid in GRUPLAR.items():
        maclar = grup_maclari(gid)
        print(f"[Grup {gad}] {len(maclar)} maç")
        for i, m in enumerate(maclar, 1):
            kayitlar = mac_detay(m["url"])
            for k in kayitlar:
                r = oy[k["kisi_id"]]
                r["oyuncu"] = k["oyuncu"]; r["grup"] = gad
                if k["takim"] and k["takim"] not in r["takimlar"]:
                    r["takimlar"].append(k["takim"])
                if k["oynadi"]:
                    r["mac"] += 1
                    r["ilk11" if k["ilk11"] else "yedek"] += 1
                r["gol"] += k["gol"]; r["sari"] += k["sari"]; r["kirmizi"] += k["kirmizi"]
            toplam_mac += 1
            time.sleep(0.25)
        print(f"   toplam maç (kümülatif): {toplam_mac}")

    oyuncular = []
    for kid, r in oy.items():
        if r["mac"] == 0 and r["gol"] == 0:
            continue
        tks = r["takimlar"]
        oyuncular.append({
            "kisi_id": kid, "oyuncu": r["oyuncu"], "takim": tks[0] if tks else "",
            "tum_takimlar": " / ".join(tks), "grup": r["grup"], "lig": "U15 Genç Kızlar",
            "mac_sayisi": r["mac"], "ilk11_mac": r["ilk11"], "yedek_mac": r["yedek"],
            "gol_sayisi": r["gol"], "gol_ayak": r["gol"], "gol_kafa": 0, "penalti_gol": 0,
            "gol_ort": round(r["gol"] / r["mac"], 2) if r["mac"] else 0.0,
            "sari_kart": r["sari"], "kirmizi_kart": r["kirmizi"], "toplam_dakika": 0,
        })
    oyuncular.sort(key=lambda x: (-x["mac_sayisi"], -x["gol_sayisi"]))
    golcu = sorted([o for o in oyuncular if o["gol_sayisi"] > 0],
                   key=lambda x: -x["gol_sayisi"])[:10]
    out = {
        "lig": "U15 Genç Kızlar Ligi", "kategori": "U15",
        "guncelleme": datetime.date.today().isoformat(),
        "gol_kralicesi": golcu, "oyuncular": oyuncular,
    }
    json.dump(out, open("altlig_u15.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[OK] {len(oyuncular)} oyuncu, {toplam_mac} maç -> altlig_u15.json")


if __name__ == "__main__":
    main()
