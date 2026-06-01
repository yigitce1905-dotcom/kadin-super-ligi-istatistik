"""
TFF Kadınlar Süper Ligi 2025-2026 — Hoca Veri Toplayıcı
Tüm maçlardaki "Teknik Sorumlu" bölümlerini tarayarak
hangi hoca hangi takımda çalıştı bilgisini toplar.
"""
import json, re, time, requests
from bs4 import BeautifulSoup
from collections import defaultdict

TOPLAM_HAFTA = 30
HAFTA_URL    = "https://www.tff.org/Default.aspx?pageID=1000&hafta={hafta}"
DETAY_BASE   = "https://www.tff.org/"
CIKTI        = "coaches.json"
HEADERS      = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(session, url):
    for _ in range(3):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.content, "lxml")
        except Exception as e:
            print(f"  HATA: {e}")
            time.sleep(2)
    return None


def mac_listesi(session, hafta):
    soup = fetch(session, HAFTA_URL.format(hafta=hafta))
    if not soup: return []
    maclar = []
    for tr in soup.select("tr.haftaninMaclariTr"):
        td = tr.find("td", class_="haftaninMaclariSkor")
        if not td: continue
        a = td.find("a", href=True)
        if not a or "macId=" not in a["href"]: continue
        ev_td  = tr.find("td", class_="haftaninMaclariEv")
        dep_td = tr.find("td", class_="haftaninMaclariDeplasman")
        maclar.append({
            "url": DETAY_BASE + a["href"].lstrip("/"),
            "ev":  ev_td.get_text(strip=True)  if ev_td  else "",
            "dep": dep_td.get_text(strip=True) if dep_td else "",
        })
    return maclar


def mac_hocalari(session, mac):
    soup = fetch(session, mac["url"])
    if not soup: return {}

    # Ertelendi kontrolü
    if "ertelendi" in soup.get_text(" ").lower():
        return {}

    takim_els = soup.select(".TakimAdi")
    ev_takim  = takim_els[0].get_text(strip=True) if len(takim_els) > 0 else mac["ev"]
    dep_takim = takim_els[1].get_text(strip=True) if len(takim_els) > 1 else mac["dep"]

    # İlk 11 sırasına göre hangi Teknik Sorumlu hangi takımın
    bolumler = []
    for tablo in soup.find_all("table"):
        bs = tablo.select(".MacDetayMiniBaslik")
        if len(bs) == 1:
            bolumler.append((bs[0].get_text(strip=True), tablo))

    ilk11_sira   = 0
    current_team = ev_takim
    sonuc        = {}  # takım → hoca adı

    for bolum_adi, tablo in bolumler:
        if bolum_adi == "İlk 11":
            current_team = ev_takim if ilk11_sira == 0 else dep_takim
            ilk11_sira  += 1
        elif bolum_adi == "Teknik Sorumlu":
            # Hoca linkleri pageId=219 kullanır (pageId=30 değil)
            for a in tablo.find_all("a", href=True):
                isim = a.get_text(strip=True)
                if isim and len(isim) > 3 and isim.upper() == isim:
                    # Büyük harfle yazılı isim → hoca adı
                    sonuc[current_team] = isim
                    break

    return sonuc


def ana():
    print("=" * 55)
    print("  TFF Kadınlar Süper Ligi — Hoca Toplayıcı")
    print("=" * 55)

    session = requests.Session()
    # takım → hoca listesi (sezon boyunca birden fazla olabilir)
    takim_hoca: dict[str, set] = defaultdict(set)

    toplam_mac = 0
    for hafta in range(1, TOPLAM_HAFTA + 1):
        print(f"\n[{hafta:2d}. HAFTA]")
        maclar = mac_listesi(session, hafta)
        if not maclar:
            print("  Maç bulunamadı")
            time.sleep(1)
            continue

        for mac in maclar:
            hocalar = mac_hocalari(session, mac)
            for takim, hoca in hocalar.items():
                takim_hoca[takim].add(hoca)
                print(f"  {takim[:30]:<30} → {hoca}")
            toplam_mac += 1
            time.sleep(1.0)

        time.sleep(1.5)

    # JSON'a kaydet: {takım: [hoca1, hoca2, ...], ...}
    cikti = {t: sorted(h) for t, h in takim_hoca.items()}
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] {CIKTI} kaydedildi")
    print(f"Toplam: {len(cikti)} takım, {sum(len(v) for v in cikti.values())} hoca kaydı")


if __name__ == "__main__":
    ana()
