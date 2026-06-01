"""
TFF Kadınlar Süper Ligi 2025-2026 — Web Scraper
Oyuncu: maç sayısı, gol, sarı/kırmızı kart, toplam dakika
"""

import time, json, csv, re, requests
from bs4 import BeautifulSoup
from collections import defaultdict

# ─── AYARLAR ────────────────────────────────────────────────────────────────
TOPLAM_HAFTA  = 30
HAFTA_BEKLEME = 2.0
MAC_BEKLEME   = 1.5
CIKTI_JSON    = "oyuncular.json"
CIKTI_CSV     = "kadınlar_super_ligi_2026.csv"

HAFTA_URL  = "https://www.tff.org/Default.aspx?pageID=1000&hafta={hafta}"
DETAY_BASE = "https://www.tff.org/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
# ────────────────────────────────────────────────────────────────────────────


def fetch(session, url, yeniden=3):
    for deneme in range(yeniden):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return BeautifulSoup(r.content, "lxml")
        except Exception as e:
            print(f"      [HATA {deneme+1}/{yeniden}] {url[:60]}: {e}")
            time.sleep(3)
    return None


def parse_dakika(metin):
    """'85.dk', '90+4.dk' gibi metni dakika sayısına çevirir."""
    m = re.search(r"(\d+)\+(\d+)", metin)
    if m:
        return int(m.group(1)) + int(m.group(2))
    m = re.search(r"(\d+)", metin)
    return int(m.group(1)) if m else 90


def mac_linklerini_topla(session, hafta_no):
    url = HAFTA_URL.format(hafta=hafta_no)
    soup = fetch(session, url)
    if not soup:
        return []

    mac_linkleri = []
    for tr in soup.select("tr.haftaninMaclariTr"):
        skor_td = tr.find("td", class_="haftaninMaclariSkor")
        if not skor_td:
            continue
        a = skor_td.find("a", href=True)
        if not a:
            detay_td = tr.find("td", class_="haftaninMaclariDetay")
            a = detay_td.find("a", href=True) if detay_td else None
        if not a or "macId=" not in a["href"]:
            continue

        tam_url = DETAY_BASE + a["href"].lstrip("/")
        ev_td  = tr.find("td", class_="haftaninMaclariEv")
        dep_td = tr.find("td", class_="haftaninMaclariDeplasman")
        mac_linkleri.append({
            "url": tam_url,
            "ev":  ev_td.get_text(strip=True)  if ev_td  else "",
            "dep": dep_td.get_text(strip=True) if dep_td else "",
        })
    return mac_linkleri


def _kisi_links(tablo):
    """Tablodaki oyuncu linklerini {kisiId: (isim, span_metin)} olarak döndürür."""
    sonuc = {}
    for tr in tablo.find_all("tr"):
        a = tr.find("a", href=re.compile(r"pageId=30"))
        if not a:
            continue
        m = re.search(r"kisiId=(\d+)", a["href"])
        if not m:
            continue
        kid = m.group(1)
        if kid in sonuc:
            continue
        span = tr.find("span")
        span_txt = span.get_text(strip=True) if span else ""
        sonuc[kid] = (a.get_text(strip=True), span_txt)
    return sonuc


def mac_detayi_isle(session, mac_info, oyuncu_dict):
    soup = fetch(session, mac_info["url"])
    if not soup:
        return

    sayfa_metni = soup.get_text(" ", strip=True).lower()
    if "ertelendi" in sayfa_metni or "iptal" in sayfa_metni:
        print("      [ATLA] Ertelendi/Iptal")
        return

    ev_takim  = mac_info["ev"]
    dep_takim = mac_info["dep"]
    takim_els = soup.select(".TakimAdi")
    if len(takim_els) >= 2:
        ev_takim  = takim_els[0].get_text(strip=True)
        dep_takim = takim_els[1].get_text(strip=True)

    # Yalnızca tek MacDetayMiniBaslik içeren tablolar
    bolumler = []
    for tablo in soup.find_all("table"):
        bs = tablo.select(".MacDetayMiniBaslik")
        if len(bs) != 1:
            continue
        bolumler.append((bs[0].get_text(strip=True), tablo))

    # En az 2 İlk 11 yoksa eksik kayıt — atla
    if sum(1 for ad, _ in bolumler if ad == "İlk 11") < 2:
        print("      [ATLA] Eksik kadro verisi")
        return

    # ── Per-maç geçici veri ─────────────────────────────────────────────────
    kisi_takim: dict[str, str] = {}
    # Oynanan dakikaları hesaplamak için çıkma/girme dakikaları
    cikan_dk:  dict[str, int] = {}   # İlk 11'den çıkan
    giren_dk:  dict[str, int] = {}   # Oyuna giren
    ilk11_kids: list[str] = []       # Sıralı İlk 11 listesi
    giren_kids: list[str] = []       # Oyuna girenler

    current_team = ev_takim
    ilk11_sira   = 0

    for bolum_adi, tablo in bolumler:

        if bolum_adi == "İlk 11":
            current_team = ev_takim if ilk11_sira == 0 else dep_takim
            ilk11_sira  += 1
            for kid, (isim, _) in _kisi_links(tablo).items():
                kisi_takim[kid] = current_team
                ilk11_kids.append(kid)
                _ekle(oyuncu_dict, kid, isim, current_team, mac=1)

        elif bolum_adi == "Yedekler":
            for kid in _kisi_links(tablo):
                kisi_takim[kid] = current_team

        elif bolum_adi == "Oyundan Çıkanlar":
            gorulen = set()
            for kid, (_, span) in _kisi_links(tablo).items():
                if kid not in gorulen and span:
                    cikan_dk[kid] = parse_dakika(span)
                    gorulen.add(kid)

        elif bolum_adi == "Oyuna Girenler":
            gorulen = set()
            for kid, (isim, span) in _kisi_links(tablo).items():
                if kid not in gorulen:
                    dk = parse_dakika(span) if span else 90
                    giren_dk[kid] = dk
                    giren_kids.append(kid)
                    takim = kisi_takim.get(kid, current_team)
                    _ekle(oyuncu_dict, kid, isim, takim, mac=1)
                    gorulen.add(kid)

        elif bolum_adi == "Goller":
            gorulen = set()
            for a in tablo.select('a[href*="pageId=30"]'):
                m = re.search(r"kisiId=(\d+)", a["href"])
                if not m:
                    continue
                kid  = m.group(1)
                metin = a.get_text(strip=True)
                anahtar = f"{kid}|{metin}"
                if anahtar in gorulen:
                    continue
                gorulen.add(anahtar)
                if re.search(r"\(KKG\)|\(OG\)", metin, re.IGNORECASE):
                    continue
                takim     = kisi_takim.get(kid, current_team)
                isim_temiz = re.sub(r",.*$", "", metin).strip()
                _ekle(oyuncu_dict, kid, isim_temiz, takim, gol=1)

        elif bolum_adi == "Kartlar":
            gorulen = set()
            for tr in tablo.find_all("tr"):
                a = tr.find("a", href=re.compile(r"pageId=30"))
                if not a:
                    continue
                m = re.search(r"kisiId=(\d+)", a["href"])
                if not m:
                    continue
                kid = m.group(1)
                if kid in gorulen:
                    continue
                gorulen.add(kid)
                # Kart tipini img alt'tan belirle
                img = tr.find("img", alt=True)
                alt = img["alt"].lower() if img else ""
                takim = kisi_takim.get(kid, current_team)
                isim  = a.get_text(strip=True)
                if "sarı" in alt or "sari" in alt:
                    _ekle(oyuncu_dict, kid, isim, takim, sari=1)
                elif "kırmızı" in alt or "kirmizi" in alt:
                    _ekle(oyuncu_dict, kid, isim, takim, kirmizi=1)

    # ── Oynanan dakikaları hesapla ──────────────────────────────────────────
    # İlk 11: 0'dan çıkma dakikasına (yoksa 90'a) kadar
    for kid in set(ilk11_kids):
        dk = cikan_dk.get(kid, 90)
        dk = min(dk, 90)  # 90+ ekstra süreyi 90'a yuvarla
        oyuncu_dict[kid]["dakika"] = oyuncu_dict[kid].get("dakika", 0) + dk

    # Oyuna girenler: giriş dakikasından 90'a kadar
    for kid in set(giren_kids):
        dk = max(0, 90 - giren_dk.get(kid, 90))
        oyuncu_dict[kid]["dakika"] = oyuncu_dict[kid].get("dakika", 0) + dk


def _ekle(oyuncu_dict, kid, isim, takim, mac=0, gol=0, sari=0, kirmizi=0):
    isim = isim.strip()
    if not isim or len(isim) < 2:
        return
    if kid not in oyuncu_dict:
        oyuncu_dict[kid] = {
            "isim": isim, "takim": takim,
            "mac": 0, "gol": 0, "sari": 0, "kirmizi": 0, "dakika": 0
        }
    oyuncu_dict[kid]["mac"]     += mac
    oyuncu_dict[kid]["gol"]     += gol
    oyuncu_dict[kid]["sari"]    += sari
    oyuncu_dict[kid]["kirmizi"] += kirmizi
    if takim and not oyuncu_dict[kid]["takim"]:
        oyuncu_dict[kid]["takim"] = takim


def veriyi_kaydet(oyuncu_dict):
    liste = []
    for v in oyuncu_dict.values():
        mac = v["mac"]
        liste.append({
            "oyuncu":        v["isim"],
            "takim":         v["takim"],
            "mac_sayisi":    mac,
            "gol_sayisi":    v["gol"],
            "gol_ort":       round(v["gol"] / mac, 2) if mac else 0,
            "sari_kart":     v["sari"],
            "kirmizi_kart":  v["kirmizi"],
            "toplam_dakika": v["dakika"],
        })
    liste.sort(key=lambda x: (-x["mac_sayisi"], -x["gol_sayisi"]))

    with open(CIKTI_JSON, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] JSON -> {CIKTI_JSON}  ({len(liste)} oyuncu)")

    with open(CIKTI_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=liste[0].keys())
        writer.writeheader()
        writer.writerows(liste)
    print(f"[OK] CSV  -> {CIKTI_CSV}")


def ana_calistir():
    print("=" * 62)
    print("  TFF Kadinlar Super Ligi 2025-2026 -- Veri Toplayici")
    print("=" * 62)

    session      = requests.Session()
    oyuncu_dict  = {}
    toplam_mac   = 0
    bos_hafta    = 0

    try:
        for hafta in range(1, TOPLAM_HAFTA + 1):
            print(f"\n[{hafta:2d}. HAFTA] taranıyor...")
            maclar = mac_linklerini_topla(session, hafta)

            if not maclar:
                bos_hafta += 1
                print(f"  [!] Mac bulunamadi (bos: {bos_hafta})")
                if bos_hafta >= 5:
                    print("  [X] Cok fazla bos hafta -- duruluyor.")
                    break
                time.sleep(HAFTA_BEKLEME)
                continue

            bos_hafta = 0
            print(f"  -> {len(maclar)} mac")

            for i, mac in enumerate(maclar, 1):
                print(f"    [{i}/{len(maclar)}] {mac['ev'][:30]} vs {mac['dep'][:30]}")
                mac_detayi_isle(session, mac, oyuncu_dict)
                toplam_mac += 1
                time.sleep(MAC_BEKLEME)

            print(f"  OK  toplam mac: {toplam_mac}")
            time.sleep(HAFTA_BEKLEME)

    except KeyboardInterrupt:
        print("\n[!] Durduruluyor...")

    veriyi_kaydet(oyuncu_dict)
    print(f"\nBitti! {len(oyuncu_dict)} oyuncu, {toplam_mac} mac.")


if __name__ == "__main__":
    ana_calistir()
