"""
TFF Kadınlar Süper Ligi 2025-2026 — Web Scraper
Oyuncu: maç geçmişi, gol, penaltı, sarı/kırmızı kart, dakika, ilk11/yedek
"""

import time, json, csv, re, requests
from bs4 import BeautifulSoup

# ─── AYARLAR ────────────────────────────────────────────────────────────────
TOPLAM_HAFTA  = 30
HAFTA_BEKLEME = 2.0
MAC_BEKLEME   = 1.5
CIKTI_JSON    = "oyuncular.json"
CIKTI_CSV     = "kadınlar_super_ligi_2026.csv"
HAFTA_URL     = "https://www.tff.org/Default.aspx?pageID=1000&hafta={hafta}"
DETAY_BASE    = "https://www.tff.org/"
HEADERS       = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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


def parse_dk(metin):
    m = re.search(r"(\d+)\+(\d+)", metin)
    if m: return int(m.group(1)) + int(m.group(2))
    m = re.search(r"(\d+)", metin)
    return int(m.group(1)) if m else 90


def _kisi_links(tablo):
    """kisiId → (isim, span_txt) — tekilleştirilmiş."""
    sonuc = {}
    for tr in tablo.find_all("tr"):
        a = tr.find("a", href=re.compile(r"pageId=30"))
        if not a: continue
        m = re.search(r"kisiId=(\d+)", a["href"])
        if not m or m.group(1) in sonuc: continue
        span = tr.find("span")
        sonuc[m.group(1)] = (a.get_text(strip=True), span.get_text(strip=True) if span else "")
    return sonuc


def mac_linklerini_topla(session, hafta_no):
    soup = fetch(session, HAFTA_URL.format(hafta=hafta_no))
    if not soup: return []
    mac_linkleri = []
    for tr in soup.select("tr.haftaninMaclariTr"):
        td = tr.find("td", class_="haftaninMaclariSkor") or tr.find("td", class_="haftaninMaclariDetay")
        if not td: continue
        a = td.find("a", href=True)
        if not a or "macId=" not in a["href"]: continue
        ev_td  = tr.find("td", class_="haftaninMaclariEv")
        dep_td = tr.find("td", class_="haftaninMaclariDeplasman")
        mac_linkleri.append({
            "url": DETAY_BASE + a["href"].lstrip("/"),
            "ev":  ev_td.get_text(strip=True)  if ev_td  else "",
            "dep": dep_td.get_text(strip=True) if dep_td else "",
        })
    return mac_linkleri


def mac_detayi_isle(session, mac_info, oyuncu_dict, hafta_no):
    soup = fetch(session, mac_info["url"])
    if not soup: return

    sayfa = soup.get_text(" ", strip=True).lower()
    if "ertelendi" in sayfa or "iptal" in sayfa:
        print("      [ATLA] Ertelendi/Iptal"); return

    ev_takim  = mac_info["ev"]
    dep_takim = mac_info["dep"]
    takim_els = soup.select(".TakimAdi")
    if len(takim_els) >= 2:
        ev_takim  = takim_els[0].get_text(strip=True)
        dep_takim = takim_els[1].get_text(strip=True)

    bolumler = []
    for tablo in soup.find_all("table"):
        bs = tablo.select(".MacDetayMiniBaslik")
        if len(bs) == 1:
            bolumler.append((bs[0].get_text(strip=True), tablo))

    if sum(1 for ad, _ in bolumler if ad == "İlk 11") < 2:
        print("      [ATLA] Eksik kadro"); return

    # ── Per-maç tracking ────────────────────────────────────────────────────
    kisi_takim:   dict[str, str] = {}
    ilk11_kids:   list[str]      = []
    giren_kids:   list[str]      = []
    cikan_dk:     dict[str, int] = {}
    giren_dk_map: dict[str, int] = {}
    mac_gol:          dict[str, int]       = {}
    mac_gol_ayak:     dict[str, int]       = {}
    mac_gol_kafa:     dict[str, int]       = {}
    mac_penalti:      dict[str, int]       = {}
    mac_gol_dakika:   dict[str, list]      = {}  # kisiId → [17, 39, ...]
    mac_sari:     dict[str, int] = {}
    mac_kirmizi:  dict[str, int] = {}

    current_team = ev_takim
    ilk11_sira   = 0

    for bolum_adi, tablo in bolumler:
        links = _kisi_links(tablo)

        if bolum_adi == "İlk 11":
            current_team = ev_takim if ilk11_sira == 0 else dep_takim
            ilk11_sira  += 1
            for kid, (isim, _) in links.items():
                kisi_takim[kid] = current_team
                ilk11_kids.append(kid)
                _ekle(oyuncu_dict, kid, isim, current_team, mac=1)

        elif bolum_adi == "Yedekler":
            for kid in links:
                kisi_takim[kid] = current_team

        elif bolum_adi == "Oyundan Çıkanlar":
            seen = set()
            for kid, (_, span) in links.items():
                if kid not in seen and span:
                    cikan_dk[kid] = parse_dk(span); seen.add(kid)

        elif bolum_adi == "Oyuna Girenler":
            seen = set()
            for kid, (isim, span) in links.items():
                if kid in seen: continue
                seen.add(kid)
                dk = parse_dk(span) if span else 90
                giren_dk_map[kid] = dk
                giren_kids.append(kid)
                takim = kisi_takim.get(kid, current_team)
                _ekle(oyuncu_dict, kid, isim, takim, mac=1)

        elif bolum_adi == "Goller":
            seen = set()
            for a in tablo.select('a[href*="pageId=30"]'):
                m = re.search(r"kisiId=(\d+)", a["href"])
                if not m: continue
                kid   = m.group(1)
                metin = a.get_text(strip=True)
                key   = f"{kid}|{metin}"
                if key in seen: continue
                seen.add(key)
                if re.search(r"\(KKG\)|\(OG\)", metin, re.IGNORECASE): continue
                takim      = kisi_takim.get(kid, current_team)
                isim_temiz = re.sub(r",.*$", "", metin).strip()
                # Gol tipi: (F)=ayak (H)=kafa (P)=penaltı
                tip_m = re.search(r"\(([FHP])\)", metin, re.IGNORECASE)
                tip   = tip_m.group(1).upper() if tip_m else "F"
                _ekle(oyuncu_dict, kid, isim_temiz, takim, gol=1,
                      gol_ayak=1 if tip=="F" else 0,
                      gol_kafa=1 if tip=="H" else 0,
                      penalti=1  if tip=="P" else 0)
                mac_gol[kid] = mac_gol.get(kid, 0) + 1
                if tip == "F": mac_gol_ayak[kid] = mac_gol_ayak.get(kid, 0) + 1
                if tip == "H": mac_gol_kafa[kid] = mac_gol_kafa.get(kid, 0) + 1
                if tip == "P": mac_penalti[kid]  = mac_penalti.get(kid,  0) + 1
                # Gol dakikasını çıkar ("17.dk" → 17)
                dk_m = re.search(r",\s*(\d+(?:\+\d+)?)\.dk", metin)
                if dk_m:
                    mac_gol_dakika.setdefault(kid, []).append(parse_dk(dk_m.group(1)))

        elif bolum_adi == "Kartlar":
            seen = set()
            for tr in tablo.find_all("tr"):
                a = tr.find("a", href=re.compile(r"pageId=30"))
                if not a: continue
                m = re.search(r"kisiId=(\d+)", a["href"])
                if not m or m.group(1) in seen: continue
                kid  = m.group(1); seen.add(kid)
                img  = tr.find("img", alt=True)
                alt  = img["alt"].lower() if img else ""
                takim = kisi_takim.get(kid, current_team)
                isim  = a.get_text(strip=True)
                if "sarı" in alt or "sari" in alt:
                    _ekle(oyuncu_dict, kid, isim, takim, sari=1)
                    mac_sari[kid] = mac_sari.get(kid, 0) + 1
                elif "kırmızı" in alt or "kirmizi" in alt:
                    _ekle(oyuncu_dict, kid, isim, takim, kirmizi=1)
                    mac_kirmizi[kid] = mac_kirmizi.get(kid, 0) + 1

    # ── Dakika hesapla + maç geçmişi oluştur ────────────────────────────────
    tum_oyuncular = set(ilk11_kids) | set(giren_kids)
    for kid in tum_oyuncular:
        if kid not in oyuncu_dict: continue
        # Bu maçtaki dakika
        if kid in set(ilk11_kids):
            dk = min(cikan_dk.get(kid, 90), 90)
        else:
            dk = max(0, 90 - giren_dk_map.get(kid, 90))

        # Toplam dakikaya ekle (takım bazlı da)
        oyuncu_dict[kid]["dakika"] = oyuncu_dict[kid].get("dakika", 0) + dk
        takim = kisi_takim.get(kid, "")
        if takim:
            ts = oyuncu_dict[kid].setdefault("takim_stats", {})
            ts.setdefault(takim, {"mac": 0, "gol": 0, "sari": 0, "kirmizi": 0, "dakika": 0})
            ts[takim]["dakika"] += dk

        # İlk 11 / yedek sayacı
        if kid in set(ilk11_kids):
            oyuncu_dict[kid]["ilk11_mac"] = oyuncu_dict[kid].get("ilk11_mac", 0) + 1
        else:
            oyuncu_dict[kid]["yedek_mac"] = oyuncu_dict[kid].get("yedek_mac", 0) + 1

        # Maç geçmişi kaydı
        giris = {
            "hafta":       hafta_no,
            "ilk11":       kid in set(ilk11_kids),
            "dakika":      dk,
            "gol":         mac_gol.get(kid, 0),
            "gol_ayak":    mac_gol_ayak.get(kid, 0),
            "gol_kafa":    mac_gol_kafa.get(kid, 0),
            "penalti_gol": mac_penalti.get(kid, 0),
            "gol_dakikalari": mac_gol_dakika.get(kid, []),
            "sari":        mac_sari.get(kid, 0),
            "kirmizi":     mac_kirmizi.get(kid, 0),
        }
        oyuncu_dict[kid].setdefault("mac_gecmisi", []).append(giris)


def _ekle(oyuncu_dict, kid, isim, takim, mac=0, gol=0,
          gol_ayak=0, gol_kafa=0, penalti=0, sari=0, kirmizi=0):
    isim = isim.strip()
    if not isim or len(isim) < 2: return
    if kid not in oyuncu_dict:
        oyuncu_dict[kid] = {
            "isim": isim, "dakika": 0, "ilk11_mac": 0, "yedek_mac": 0,
            "mac": 0, "gol": 0, "gol_ayak": 0, "gol_kafa": 0,
            "penalti_gol": 0, "sari": 0, "kirmizi": 0,
            "takim_stats": {}, "mac_gecmisi": []
        }
    oyuncu_dict[kid]["mac"]         += mac
    oyuncu_dict[kid]["gol"]         += gol
    oyuncu_dict[kid]["gol_ayak"]    += gol_ayak
    oyuncu_dict[kid]["gol_kafa"]    += gol_kafa
    oyuncu_dict[kid]["penalti_gol"] += penalti
    oyuncu_dict[kid]["sari"]        += sari
    oyuncu_dict[kid]["kirmizi"]     += kirmizi
    if takim:
        ts = oyuncu_dict[kid].setdefault("takim_stats", {})
        ts.setdefault(takim, {"mac": 0, "gol": 0, "sari": 0, "kirmizi": 0, "dakika": 0})
        ts[takim]["mac"]     += mac
        ts[takim]["gol"]     += gol
        ts[takim]["sari"]    += sari
        ts[takim]["kirmizi"] += kirmizi
    if takim and not oyuncu_dict[kid].get("_takim_set"):
        oyuncu_dict[kid]["_takim_set"] = takim


def veriyi_kaydet(oyuncu_dict):
    liste = []
    for v in oyuncu_dict.values():
        mac = v["mac"]
        ts  = v.get("takim_stats", {})
        birincil      = max(ts, key=lambda t: ts[t]["mac"]) if ts else v.get("_takim_set", "")
        takim_listesi = sorted(ts.items(), key=lambda x: -x[1]["mac"])
        transfer      = len(takim_listesi) > 1
        tum_takimlar  = " / ".join(t for t, _ in takim_listesi)
        takim_detay   = [
            {"takim": t, "mac": s["mac"], "gol": s["gol"],
             "sari": s["sari"], "kirmizi": s["kirmizi"], "dakika": s["dakika"]}
            for t, s in takim_listesi
        ]
        gecmis = sorted(v.get("mac_gecmisi", []), key=lambda x: x["hafta"])
        liste.append({
            "oyuncu":        v["isim"],
            "takim":         birincil,
            "tum_takimlar":  tum_takimlar,
            "transfer":      transfer,
            "mac_sayisi":    mac,
            "ilk11_mac":     v.get("ilk11_mac", 0),
            "yedek_mac":     v.get("yedek_mac", 0),
            "gol_sayisi":    v["gol"],
            "gol_ayak":      v.get("gol_ayak", 0),
            "gol_kafa":      v.get("gol_kafa", 0),
            "penalti_gol":   v.get("penalti_gol", 0),
            "gol_ort":       round(v["gol"] / mac, 2) if mac else 0,
            "sari_kart":     v["sari"],
            "kirmizi_kart":  v["kirmizi"],
            "toplam_dakika": v["dakika"],
            "takim_detay":   takim_detay,
            "mac_gecmisi":   gecmis,
        })
    liste.sort(key=lambda x: (-x["mac_sayisi"], -x["gol_sayisi"]))

    with open(CIKTI_JSON, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] JSON -> {CIKTI_JSON}  ({len(liste)} oyuncu)")

    # CSV: mac_gecmisi ve takim_detay hariç
    csv_alanlari = [k for k in liste[0] if k not in ("takim_detay", "mac_gecmisi")]
    with open(CIKTI_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_alanlari)
        writer.writeheader()
        for row in liste:
            writer.writerow({k: row[k] for k in csv_alanlari})
    print(f"[OK] CSV  -> {CIKTI_CSV}")


def ana_calistir():
    print("=" * 62)
    print("  TFF Kadinlar Super Ligi 2025-2026 -- Veri Toplayici")
    print("=" * 62)
    session     = requests.Session()
    oyuncu_dict = {}
    toplam_mac  = 0
    bos_hafta   = 0
    try:
        for hafta in range(1, TOPLAM_HAFTA + 1):
            print(f"\n[{hafta:2d}. HAFTA] taranıyor...")
            maclar = mac_linklerini_topla(session, hafta)
            if not maclar:
                bos_hafta += 1
                print(f"  [!] Mac bulunamadi (bos: {bos_hafta})")
                if bos_hafta >= 5: print("  [X] Duruluyor."); break
                time.sleep(HAFTA_BEKLEME); continue
            bos_hafta = 0
            print(f"  -> {len(maclar)} mac")
            for i, mac in enumerate(maclar, 1):
                print(f"    [{i}/{len(maclar)}] {mac['ev'][:30]} vs {mac['dep'][:30]}")
                mac_detayi_isle(session, mac, oyuncu_dict, hafta)
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
