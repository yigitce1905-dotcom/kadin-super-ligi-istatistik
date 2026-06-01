"""
TFF Kadınlar Süper Ligi 2025-2026 — Web Scraper
Tüm 30 haftayı tarayarak oyuncu maç ve gol istatistiklerini toplar.
"""

import time
import json
import csv
import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

# ─── AYARLAR ────────────────────────────────────────────────────────────────
TOPLAM_HAFTA   = 30
HAFTA_BEKLEME  = 2.0   # saniye
MAC_BEKLEME    = 1.5   # saniye
CIKTI_JSON     = "oyuncular.json"
CIKTI_CSV      = "kadınlar_super_ligi_2026.csv"

HAFTA_URL  = "https://www.tff.org/Default.aspx?pageID=1000&hafta={hafta}"
DETAY_BASE = "https://www.tff.org/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
# ────────────────────────────────────────────────────────────────────────────


def fetch(session, url, yeniden=3):
    """URL'yi indir, hata durumunda yeniden dene."""
    for deneme in range(yeniden):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            # Site windows-1254 — r.content kullanarak BeautifulSoup'a bırak
            return BeautifulSoup(r.content, "lxml")
        except Exception as e:
            print(f"      [HATA {deneme+1}/{yeniden}] {url[:60]}: {e}")
            time.sleep(3)
    return None


def mac_linklerini_topla(session, hafta_no):
    """Verilen haftanın maç detay linklerini (macId'lerini) döndürür."""
    url = HAFTA_URL.format(hafta=hafta_no)
    soup = fetch(session, url)
    if not soup:
        return []

    mac_linkleri = []
    for tr in soup.select("tr.haftaninMaclariTr"):
        # Skor hücresindeki link: pageId=29&macId=XXXXXX
        skor_td = tr.find("td", class_="haftaninMaclariSkor")
        if not skor_td:
            continue
        a = skor_td.find("a", href=True)
        if not a:
            # Alternatif: Detay td
            detay_td = tr.find("td", class_="haftaninMaclariDetay")
            a = detay_td.find("a", href=True) if detay_td else None
        if not a:
            continue

        href = a["href"]
        if "macId=" not in href:
            continue
        tam_url = DETAY_BASE + href.lstrip("/")

        # Takım adları
        ev_td  = tr.find("td", class_="haftaninMaclariEv")
        dep_td = tr.find("td", class_="haftaninMaclariDeplasman")
        ev  = ev_td.get_text(strip=True)  if ev_td  else ""
        dep = dep_td.get_text(strip=True) if dep_td else ""

        mac_linkleri.append({"url": tam_url, "ev": ev, "dep": dep})

    return mac_linkleri


def mac_detayi_isle(session, mac_info, oyuncu_dict):
    """
    Maç detay sayfasını işler:
      - İlk 11 ve Oyuna Girenler → +1 maç
      - Goller → +1 gol (kendi kaleye gol hariç)
    oyuncu_dict: { kisiId: {"isim": ..., "takim": ..., "mac": 0, "gol": 0} }
    """
    soup = fetch(session, mac_info["url"])
    if not soup:
        return

    # Ertelenen veya iptal edilen maçları atla
    sayfa_metni = soup.get_text(" ", strip=True).lower()
    if "ertelendi" in sayfa_metni or "iptal" in sayfa_metni:
        print("      [ATLA] Ertelendi/İptal — bu maç geçiliyor.")
        return

    ev_takim  = mac_info["ev"]
    dep_takim = mac_info["dep"]

    # TFF sayfası takım adlarını .TakimAdi ile de verir; bunları kullan
    takim_els = soup.select(".TakimAdi")
    if len(takim_els) >= 2:
        ev_takim  = takim_els[0].get_text(strip=True)
        dep_takim = takim_els[1].get_text(strip=True)

    # kisiId → takım haritası (İlk 11 + Yedekler bölümlerinden doldurulur)
    kisi_takim: dict[str, str] = {}

    # Sayfa yapısı: her takım kendi bloğunu oluşturur
    #   Ev sahibi:  İlk 11 → Yedekler → [Goller] → [Kartlar] → [Oyundan Çıkanlar] → [Oyuna Girenler]
    #   Deplasman:  İlk 11 → Yedekler → [Goller] → [Kartlar] → [Oyundan Çıkanlar] → [Oyuna Girenler]
    # İlk 11 her bloğun başlangıcını işaret eder; current_team buna göre güncellenir.

    # Sayfada kaç tane İlk 11 var? İkiden azsa TFF kaydı eksik — maçı atla.
    toplam_ilk11 = sum(
        1 for t in soup.find_all("table")
        if len(t.select(".MacDetayMiniBaslik")) == 1
        and t.select_one(".MacDetayMiniBaslik").get_text(strip=True) == "İlk 11"
    )
    if toplam_ilk11 < 2:
        print("      [ATLA] Eksik kadro verisi — bu maç geçiliyor.")
        return

    ilk11_sira  = 0
    current_team = ev_takim  # ilk bölüm her zaman ev sahibi

    for tablo in soup.find_all("table"):
        basliklar = tablo.select(".MacDetayMiniBaslik")
        if len(basliklar) != 1:
            continue
        bolum_adi = basliklar[0].get_text(strip=True)

        # Bu tablodaki oyuncu linkleri — kisiId ile tekilleştir
        kisi_links: dict[str, str] = {}
        for a in tablo.select('a[href*="pageId=30"]'):
            m = re.search(r"kisiId=(\d+)", a["href"])
            if m:
                kid = m.group(1)
                if kid not in kisi_links:
                    kisi_links[kid] = a.get_text(strip=True)

        # ── İlk 11: yeni takım bloğunun başlangıcı ─────────────────────────
        if bolum_adi == "İlk 11":
            current_team = ev_takim if ilk11_sira == 0 else dep_takim
            ilk11_sira += 1
            for kid, isim in kisi_links.items():
                kisi_takim[kid] = current_team
                _oyuncu_ekle(oyuncu_dict, kid, isim, current_team, mac=1, gol=0)

        # ── Yedekler: aynı bloğun takımı, kisi_takim'e kaydet (maç sayma) ──
        elif bolum_adi == "Yedekler":
            for kid in kisi_links:
                kisi_takim[kid] = current_team

        # ── Oyuna Girenler: aynı bloğun takımı ─────────────────────────────
        elif bolum_adi == "Oyuna Girenler":
            for kid, isim in kisi_links.items():
                takim = kisi_takim.get(kid, current_team)
                _oyuncu_ekle(oyuncu_dict, kid, isim, takim, mac=1, gol=0)

        # ── Goller: aynı bloğun takımı ──────────────────────────────────────
        elif bolum_adi == "Goller":
            gorulen = set()
            for a in tablo.select('a[href*="pageId=30"]'):
                m = re.search(r"kisiId=(\d+)", a["href"])
                if not m:
                    continue
                kid = m.group(1)
                metin = a.get_text(strip=True)
                anahtar = f"{kid}|{metin}"
                if anahtar in gorulen:
                    continue
                gorulen.add(anahtar)

                if re.search(r"\(KKG\)|\(OG\)", metin, re.IGNORECASE):
                    continue

                takim = kisi_takim.get(kid, current_team)
                isim_temiz = re.sub(r",.*$", "", metin).strip()
                _oyuncu_ekle(oyuncu_dict, kid, isim_temiz, takim, mac=0, gol=1)


def _oyuncu_ekle(oyuncu_dict, kid, isim, takim, mac, gol):
    """Oyuncu sözlüğüne ekle / güncelle."""
    isim = isim.strip()
    if not isim or len(isim) < 2:
        return
    if kid not in oyuncu_dict:
        oyuncu_dict[kid] = {"isim": isim, "takim": takim, "mac": 0, "gol": 0}
    oyuncu_dict[kid]["mac"] += mac
    oyuncu_dict[kid]["gol"] += gol
    # Takımı yalnızca boşsa yaz — bozuk maç kayıtlarının üstüne yazmasını önler
    if takim and not oyuncu_dict[kid]["takim"]:
        oyuncu_dict[kid]["takim"] = takim


def veriyi_kaydet(oyuncu_dict):
    """Toplanan veriyi JSON ve CSV olarak kaydeder."""
    liste = [
        {
            "oyuncu":     v["isim"],
            "takim":      v["takim"],
            "mac_sayisi": v["mac"],
            "gol_sayisi": v["gol"],
        }
        for v in oyuncu_dict.values()
    ]
    liste.sort(key=lambda x: (-x["mac_sayisi"], -x["gol_sayisi"]))

    with open(CIKTI_JSON, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] JSON kaydedildi -> {CIKTI_JSON}  ({len(liste)} oyuncu)")

    with open(CIKTI_CSV, "w", newline="", encoding="utf-8-sig") as f:
        yazar = csv.DictWriter(
            f, fieldnames=["oyuncu", "takim", "mac_sayisi", "gol_sayisi"]
        )
        yazar.writeheader()
        yazar.writerows(liste)
    print(f"[OK] CSV  kaydedildi -> {CIKTI_CSV}")


def ana_calistir():
    print("=" * 62)
    print("  TFF Kadinlar Super Ligi 2025-2026 -- Veri Toplayici")
    print("=" * 62)

    session = requests.Session()
    oyuncu_dict: dict[str, dict] = {}

    toplam_mac = 0
    bos_hafta  = 0

    try:
        for hafta in range(1, TOPLAM_HAFTA + 1):
            print(f"\n[{hafta:2d}. HAFTA] taranıyor...")
            mac_listesi = mac_linklerini_topla(session, hafta)

            if not mac_listesi:
                bos_hafta += 1
                print(f"  [!] Mac linki bulunamadi  (bos hafta: {bos_hafta})")
                if bos_hafta >= 5:
                    print("  [X] Cok fazla bos hafta -- duruluyor.")
                    break
                time.sleep(HAFTA_BEKLEME)
                continue

            bos_hafta = 0
            print(f"  -> {len(mac_listesi)} mac bulundu")

            for i, mac in enumerate(mac_listesi, 1):
                ev  = mac["ev"][:35]
                dep = mac["dep"][:35]
                print(f"    [{i}/{len(mac_listesi)}] {ev} vs {dep}")
                mac_detayi_isle(session, mac, oyuncu_dict)
                toplam_mac += 1
                time.sleep(MAC_BEKLEME)

            print(f"  OK  Hafta tamamlandi -- toplam islenen mac: {toplam_mac}")
            time.sleep(HAFTA_BEKLEME)

    except KeyboardInterrupt:
        print("\n[!] Durduruluyor... veriler kaydediliyor.")

    veriyi_kaydet(oyuncu_dict)
    print(f"\nBitti! {len(oyuncu_dict)} oyuncu, {toplam_mac} mac islendi.")


if __name__ == "__main__":
    ana_calistir()
