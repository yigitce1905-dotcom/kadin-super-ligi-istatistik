"""
TFF Alt Ligler (Kadınlar 1. Lig / 2. Lig) — genelleştirilmiş veri toplayıcı.

Süper Lig scraper.py'nin maç-detay parse mantığını (İlk 11/Goller/Kartlar)
AYNEN yeniden kullanır; tek fark maç linkleri grup sayfasından toplanır ve
her oyuncu takımının grubuna göre etiketlenir (izolasyon).

Maç-detay şablonu süper ligle birebir aynı (doğrulandı), bu yüzden
scraper.mac_detayi_isle / _ekle olduğu gibi kullanılır.

Çıktı (lig başına ayrı dosya — Süper Lig verisine HİÇ karışmaz):
  altlig_1lig.json , altlig_2lig.json
Yapı: {lig, guncelleme, gruplar:{A:{takimlar,puan_durumu},...}, playoff:[...],
       oyuncular:[{... + grup + lig}]}

Kullanım:  python scraper_altlig.py 1     # 1. Lig
           python scraper_altlig.py 2     # 2. Lig
"""
import sys, json, re, time, urllib3
from datetime import date
import requests
from bs4 import BeautifulSoup
import scraper  # süper lig parse mantığı

urllib3.disable_warnings()
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.tff.org/"

LIGLER = {
    "1": {"ad": "Kadınlar 1. Ligi", "pageID": 1602,
          "gruplar": {"A": 3313, "B": 3314}, "cikti": "altlig_1lig.json"},
    "2": {"ad": "Kadınlar 2. Ligi", "pageID": 1001,
          "gruplar": {}, "cikti": "altlig_2lig.json"},  # grupID'ler runtime'da bulunur
}

_cache = {}
def fetch(url):
    """verify=False + basit cache (aynı sayfa iki kez indirilmez)."""
    if url in _cache:
        return _cache[url]
    for _ in range(3):
        try:
            r = requests.get(url, headers=HDR, timeout=25, verify=False)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "lxml")
            _cache[url] = soup
            return soup
        except Exception as e:
            print(f"   [fetch hata] {url[-40:]}: {e}")
            time.sleep(2)
    return None

# scraper.mac_detayi_isle içindeki fetch'i bizimkine yönlendir (verify=False + cache)
scraper.fetch = lambda session, url, yeniden=3: fetch(url)


def gruplari_bul(page_id):
    """Lig ana sayfasından grup adı→grupID eşlemesini çıkarır."""
    soup = fetch(f"{BASE}default.aspx?pageID={page_id}")
    gruplar = {}
    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True)
        m = re.search(r"grupID=(\d+)", a["href"])
        if m and re.search(r"\bGRUBU\b", t, re.I):
            ad = t.replace("GRUBU", "").strip().upper()[:1] or t.strip()
            gruplar[ad] = int(m.group(1))
    return gruplar


def gol_kralicesi_cek(page_id):
    """Lig ana sayfasındaki RESMİ gol kraliçesi tablosu (kisiID + isim + takım + gol).
    TFF'nin otorite kaynağı; gol sayıları buna göre uzlaştırılır."""
    soup = fetch(f"{BASE}default.aspx?pageID={page_id}")
    tbl = None
    for t in soup.find_all("table"):
        # kisiID linkleri + sondaki gol sayısı olan en uygun tablo
        if t.find("a", href=re.compile(r"kisiID=", re.I)) and re.search(r"\bGol\b", t.get_text(), re.I) is not None:
            tbl = t
            break
    if tbl is None:  # fallback: kisiID linkli en çok satırlı tablo
        c = [t for t in soup.find_all("table") if t.find("a", href=re.compile(r"kisiID=", re.I))]
        tbl = max(c, key=lambda t: len(t.find_all("tr"))) if c else None
    out = {}
    if tbl is None:
        return out
    for tr in tbl.find_all("tr"):
        a = tr.find("a", href=re.compile(r"kisiID=", re.I))
        if not a:
            continue
        m = re.search(r"kisiID=(\d+)", a["href"], re.I)
        if not m:
            continue
        isim = a.get_text(" ", strip=True)
        nums = [x.get_text(strip=True) for x in tr.find_all("td") if x.get_text(strip=True).isdigit()]
        if not nums:
            continue
        takim = re.sub(r"\d+\s*$", "", tr.get_text(" ", strip=True).replace(isim, "", 1)).strip()
        out[m.group(1)] = {"isim": isim, "takim": takim, "gol": int(nums[-1])}
    return out


def _mac_golculer(soup, ev, dep):
    """Maç detayından skor + golcü listesi (playoff gösterimi için)."""
    res = {"ev_gol": 0, "dep_gol": 0, "golculer": []}
    sira = 0
    cur = ev
    for tbl in soup.find_all("table"):
        bs = tbl.select(".MacDetayMiniBaslik")
        if len(bs) != 1:
            continue
        ad = bs[0].get_text(strip=True)
        if ad == "İlk 11":
            cur = ev if sira == 0 else dep
            sira += 1
        elif ad == "Goller":
            for a in tbl.select('a[href*="pageId=30"]'):
                metin = a.get_text(strip=True)
                kidm = re.search(r"kisiId=(\d+)", a["href"], re.I)
                kid = kidm.group(1) if kidm else ""
                if cur == ev:
                    res["ev_gol"] += 1
                else:
                    res["dep_gol"] += 1
                owngoal = bool(re.search(r"\(KKG\)|\(OG\)", metin, re.I))
                res["golculer"].append({"oyuncu": re.sub(r",.*$", "", metin).strip(),
                                        "takim": cur, "detay": metin,
                                        "kid": kid, "og": owngoal})
    return res


def puan_durumu_cek(page_id, grup_id):
    soup = fetch(f"{BASE}default.aspx?pageID={page_id}&grupID={grup_id}")
    st = soup.find("table", class_="s-table")
    macids = set(re.search(r"macId=(\d+)", a["href"]).group(1)
                 for a in soup.find_all("a", href=True) if "macId=" in a["href"])
    if not st:
        return [], macids
    rows = [[td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            for tr in st.find_all("tr")]
    rows = [r for r in rows if r]
    hdr = rows[0]                       # ['', 'O','G','B','M','A','Y','AV','P']
    data = []
    for rr in rows[1:]:
        m = re.match(r"^(\d+)\.(.+)$", rr[0])
        sira = int(m.group(1)) if m else len(data) + 1
        takim = m.group(2).strip() if m else rr[0]
        rec = {"sira": sira, "takim": takim}
        for j, k in enumerate(hdr[1:], 1):
            rec[k] = rr[j] if j < len(rr) else ""
        data.append(rec)
    return data, macids


def main():
    sec = sys.argv[1] if len(sys.argv) > 1 else "1"
    cfg = LIGLER[sec]
    page_id = cfg["pageID"]
    print(f"=== {cfg['ad']} (pageID={page_id}) ===")

    gruplar = cfg["gruplar"] or gruplari_bul(page_id)
    print("Gruplar:", gruplar)

    takim_grup = {}        # TAKIM(upper) -> grup
    gruplar_out = {}
    all_macids = set()
    for g, gid in gruplar.items():
        data, macids = puan_durumu_cek(page_id, gid)
        gruplar_out[g] = {"takimlar": [d["takim"] for d in data], "puan_durumu": data}
        for d in data:
            takim_grup[d["takim"].upper()] = g
        all_macids |= macids
        print(f"  {g} grubu: {len(data)} takım")
    bizim = set(takim_grup.keys())
    print(f"Toplam tekil maç linki: {len(all_macids)} · 1.lig takımı: {len(bizim)}")

    oyuncu_dict = {}
    playoff = []
    playoff_gol = {}   # kisiID -> playoff golü (own-goal hariç)
    islenen = 0
    for i, mid in enumerate(sorted(all_macids), 1):
        url = f"{BASE}Default.aspx?pageID=29&macId={mid}"
        soup = fetch(url)
        if not soup:
            continue
        takimlar = [e.get_text(strip=True) for e in soup.select(".TakimAdi")]
        if len(takimlar) < 2:
            continue
        ev, dep = takimlar[0], takimlar[1]
        if ev.upper() not in bizim or dep.upper() not in bizim:
            continue   # bu lige ait olmayan (sayfa chrome'undan gelen) maç — atla
        ge, gd = takim_grup.get(ev.upper()), takim_grup.get(dep.upper())
        if ge != gd:
            _pd = _mac_golculer(soup, ev, dep)
            playoff.append({"ev": ev, "dep": dep, "macId": mid,
                            "ev_gol": _pd["ev_gol"], "dep_gol": _pd["dep_gol"],
                            "golculer": _pd["golculer"]})
            for gc in _pd["golculer"]:
                if gc.get("kid") and not gc.get("og"):
                    playoff_gol[gc["kid"]] = playoff_gol.get(gc["kid"], 0) + 1
        islenen += 1
        print(f"  [{islenen}] {ev[:24]} vs {dep[:24]}")
        scraper.mac_detayi_isle(None, {"url": url, "ev": ev, "dep": dep}, oyuncu_dict, islenen)
        time.sleep(0.8)

    # RESMİ gol kraliçesi tablosu (otorite) — gol sayıları buna göre uzlaştırılır
    resmi = gol_kralicesi_cek(page_id)
    print(f"Resmi gol kraliçesi: {len(resmi)} oyuncu")

    # Oyuncu listesi (scraper.veriyi_kaydet transform'u + grup/lig etiketi)
    oyuncular = []
    duzeltilen = 0
    for kid, v in oyuncu_dict.items():
        mac = v["mac"]
        ts = v.get("takim_stats", {})
        birincil = max(ts, key=lambda t: ts[t]["mac"]) if ts else v.get("_takim_set", "")
        takim_listesi = sorted(ts.items(), key=lambda x: -x[1]["mac"])
        grup = takim_grup.get(birincil.upper(), "")
        # Gol sayısı = RESMİ normal sezon (kisiID ile, otorite) + PLAYOFF golü.
        # Resmi tablo playoff'u saymaz; oyuncunun kendi verisinde playoff golü de yer alsın.
        gol_hesap = v["gol"]
        gol_normal = resmi.get(kid, {}).get("gol", 0)
        gol_pl = playoff_gol.get(kid, 0)
        gol_final = gol_normal + gol_pl
        if gol_final != gol_hesap:
            duzeltilen += 1
        oyuncular.append({
            "kisi_id": kid,
            "oyuncu": v["isim"], "takim": birincil,
            "tum_takimlar": " / ".join(t for t, _ in takim_listesi),
            "transfer": len(takim_listesi) > 1,
            "grup": grup, "lig": cfg["ad"],
            "mac_sayisi": mac, "ilk11_mac": v.get("ilk11_mac", 0),
            "yedek_mac": v.get("yedek_mac", 0), "gol_sayisi": gol_final,
            "gol_normal": gol_normal, "playoff_gol": gol_pl,   # ayrışım (detay gösterimi)
            "gol_ayak": v.get("gol_ayak", 0), "gol_kafa": v.get("gol_kafa", 0),
            "penalti_gol": v.get("penalti_gol", 0),
            "gol_ort": round(gol_final / mac, 2) if mac else 0,
            "sari_kart": v["sari"], "kirmizi_kart": v["kirmizi"],
            "toplam_dakika": v["dakika"],
            "takim_detay": [{"takim": t, "mac": s["mac"], "gol": s["gol"],
                             "sari": s["sari"], "kirmizi": s["kirmizi"],
                             "dakika": s["dakika"]} for t, s in takim_listesi],
            "mac_gecmisi": sorted(v.get("mac_gecmisi", []), key=lambda x: x["hafta"]),
        })
    oyuncular.sort(key=lambda x: (-x["mac_sayisi"], -x["gol_sayisi"]))

    # Resmi gol kraliçesi tablosu (sıralı). Takım = oyuncunun BİZİM verimizde
    # (maçları oynadığı) takımı — TFF'nin yazdığı güncel/transfer kulübü değil.
    _kid_takim = {o["kisi_id"]: o["takim"] for o in oyuncular if o.get("takim")}
    gol_kralicesi = sorted(
        [{"oyuncu": r["isim"], "takim": _kid_takim.get(kid, r["takim"]),
          "gol": r["gol"], "kisi_id": kid} for kid, r in resmi.items()],
        key=lambda x: -x["gol"])

    out = {"lig": cfg["ad"], "guncelleme": date.today().isoformat(),
           "gruplar": gruplar_out, "playoff": playoff,
           "gol_kralicesi": gol_kralicesi, "oyuncular": oyuncular}
    with open(cfg["cikti"], "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] {cfg['cikti']} — {len(oyuncular)} oyuncu, {islenen} maç, "
          f"{len(playoff)} playoff, {len(gol_kralicesi)} resmi golcü, "
          f"{duzeltilen} gol düzeltildi")


if __name__ == "__main__":
    main()
