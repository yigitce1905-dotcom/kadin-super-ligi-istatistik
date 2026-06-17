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
            playoff.append({"ev": ev, "dep": dep, "macId": mid})
        islenen += 1
        print(f"  [{islenen}] {ev[:24]} vs {dep[:24]}")
        scraper.mac_detayi_isle(None, {"url": url, "ev": ev, "dep": dep}, oyuncu_dict, islenen)
        time.sleep(0.8)

    # Oyuncu listesi (scraper.veriyi_kaydet transform'u + grup/lig etiketi)
    oyuncular = []
    for v in oyuncu_dict.values():
        mac = v["mac"]
        ts = v.get("takim_stats", {})
        birincil = max(ts, key=lambda t: ts[t]["mac"]) if ts else v.get("_takim_set", "")
        takim_listesi = sorted(ts.items(), key=lambda x: -x[1]["mac"])
        grup = takim_grup.get(birincil.upper(), "")
        oyuncular.append({
            "oyuncu": v["isim"], "takim": birincil,
            "tum_takimlar": " / ".join(t for t, _ in takim_listesi),
            "transfer": len(takim_listesi) > 1,
            "grup": grup, "lig": cfg["ad"],
            "mac_sayisi": mac, "ilk11_mac": v.get("ilk11_mac", 0),
            "yedek_mac": v.get("yedek_mac", 0), "gol_sayisi": v["gol"],
            "gol_ayak": v.get("gol_ayak", 0), "gol_kafa": v.get("gol_kafa", 0),
            "penalti_gol": v.get("penalti_gol", 0),
            "gol_ort": round(v["gol"] / mac, 2) if mac else 0,
            "sari_kart": v["sari"], "kirmizi_kart": v["kirmizi"],
            "toplam_dakika": v["dakika"],
            "takim_detay": [{"takim": t, "mac": s["mac"], "gol": s["gol"],
                             "sari": s["sari"], "kirmizi": s["kirmizi"],
                             "dakika": s["dakika"]} for t, s in takim_listesi],
            "mac_gecmisi": sorted(v.get("mac_gecmisi", []), key=lambda x: x["hafta"]),
        })
    oyuncular.sort(key=lambda x: (-x["mac_sayisi"], -x["gol_sayisi"]))

    out = {"lig": cfg["ad"], "guncelleme": date.today().isoformat(),
           "gruplar": gruplar_out, "playoff": playoff, "oyuncular": oyuncular}
    with open(cfg["cikti"], "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] {cfg['cikti']} — {len(oyuncular)} oyuncu, {islenen} maç, "
          f"{len(playoff)} playoff")


if __name__ == "__main__":
    main()
