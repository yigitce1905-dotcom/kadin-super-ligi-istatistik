"""
U17 Kızlar Gelişim Ligi — requests-only (macId aralık tarama).
Fikstür Telerik postback olduğu için (temiz URL yok) ve Selenium bu ortamda
kurulamadığı için: U17 maçları ardışık macId bloklarında → aralığı tarayıp
HER iki takımı da U17 takım kümesinde olan maçları alıyoruz.

Kullanım:
  python scraper_u17_range.py test          # küçük aralık doğrulama
  python scraper_u17_range.py <bas> <son>    # tam tarama (ör. 314600 316800)
"""
import sys, json, re, time, urllib3
from datetime import date
import requests
from bs4 import BeautifulSoup
import scraper

urllib3.disable_warnings()
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.tff.org/"
PAGE = 1760
LIG_ADI = "U17 Kızlar Gelişim Ligi"
GRUP_IDS = list(range(3450, 3482))

_cache = {}
def fetch(url, tries=3):
    if url in _cache:
        return _cache[url]
    for _ in range(tries):
        try:
            r = requests.get(url, headers=HDR, timeout=30, verify=False)
            r.raise_for_status()
            s = BeautifulSoup(r.content, "lxml")
            _cache[url] = s
            return s
        except Exception:
            time.sleep(1.5)
    return None
scraper.fetch = lambda session, url, yeniden=3: fetch(url)


def takim_grup_cek():
    tg = {}
    for idx, gid in enumerate(GRUP_IDS, 1):
        s = fetch(f"{BASE}default.aspx?pageID={PAGE}&grupID={gid}")
        st = s.find("table", class_="s-table") if s else None
        if not st:
            continue
        for tr in st.find_all("tr"):
            c = [td.get_text(strip=True) for td in tr.find_all("td")]
            if c and c[0]:
                m = re.match(r"^\d+\.(.+)$", c[0])
                if m:
                    tg[m.group(1).strip().upper()] = idx
    return tg


def gol_kralicesi_cek():
    s = fetch(f"{BASE}default.aspx?pageID={PAGE}")
    cand = [t for t in s.find_all("table") if t.find("a", href=re.compile(r"kisiID=", re.I))]
    tbl = max(cand, key=lambda t: len(t.find_all("tr"))) if cand else None
    out = []
    if not tbl:
        return out
    for tr in tbl.find_all("tr"):
        a = tr.find("a", href=re.compile(r"kisiID=", re.I))
        if not a:
            continue
        nums = [x.get_text(strip=True) for x in tr.find_all("td") if x.get_text(strip=True).isdigit()]
        if nums:
            out.append({"oyuncu": a.get_text(" ", strip=True), "gol": int(nums[-1]),
                        "kisi_id": re.search(r"kisiID=(\d+)", a["href"], re.I).group(1)})
    return out


def mac_takimlari(mid):
    s = fetch(f"{BASE}Default.aspx?pageID=29&macId={mid}")
    if not s:
        return None
    tk = [e.get_text(strip=True) for e in s.select(".TakimAdi")][:2]
    return tk if len(tk) == 2 else None


def main():
    args = sys.argv[1:]
    print("U17 takım kümesi çekiliyor (32 grup)...")
    tg = takim_grup_cek()
    bizim = set(tg.keys())
    print(f"  U17 takım: {len(bizim)}")

    if args and args[0] == "test":
        bas, son = 314690, 314760
        print(f"TEST aralığı {bas}-{son}")
    elif len(args) == 2:
        bas, son = int(args[0]), int(args[1])
    else:
        bas, son = 314600, 316800
    print(f"macId taraması: {bas}-{son} ({son-bas} id)")

    # Çok-thread tarama (TFF gecikmesini gizler)
    from concurrent.futures import ThreadPoolExecutor
    ids = list(range(bas, son + 1))
    bulundu = {}
    sayac = {"n": 0}
    def kontrol(mid):
        tk = mac_takimlari(mid)
        sayac["n"] += 1
        if sayac["n"] % 200 == 0:
            print(f"  taranan {sayac['n']}/{len(ids)} / U17 {len(bulundu)}", flush=True)
        if tk and tk[0].upper() in bizim and tk[1].upper() in bizim:
            bulundu[mid] = tk
    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(kontrol, ids))
    u17_macids = sorted(bulundu.items())
    print(f"U17 maç bulundu: {len(u17_macids)}")

    if args and args[0] == "test":
        for mid, tk in u17_macids[:10]:
            print(f"  {mid}: {tk}")
        print("314713 bulundu mu:", any(mid == 314713 for mid, _ in u17_macids))
        return

    print("Maç detayları işleniyor...")
    oyuncu_dict = {}
    for i, (mid, tk) in enumerate(u17_macids, 1):
        scraper.mac_detayi_isle(None, {"url": f"{BASE}Default.aspx?pageID=29&macId={mid}",
                                       "ev": tk[0], "dep": tk[1]}, oyuncu_dict, i)
        if i % 50 == 0:
            print(f"  işlenen {i}/{len(u17_macids)}")

    resmi_list = gol_kralicesi_cek()
    resmi = {r["kisi_id"]: r["gol"] for r in resmi_list}

    oyuncular = []
    for kid, v in oyuncu_dict.items():
        mac = v["mac"]
        ts = v.get("takim_stats", {})
        birincil = max(ts, key=lambda t: ts[t]["mac"]) if ts else v.get("_takim_set", "")
        takim_listesi = sorted(ts.items(), key=lambda x: -x[1]["mac"])
        gol_final = resmi.get(kid, v["gol"])
        oyuncular.append({
            "kisi_id": kid, "oyuncu": v["isim"], "takim": birincil,
            "tum_takimlar": " / ".join(t for t, _ in takim_listesi),
            "grup": tg.get(birincil.upper(), ""), "lig": LIG_ADI,
            "mac_sayisi": mac, "ilk11_mac": v.get("ilk11_mac", 0),
            "yedek_mac": v.get("yedek_mac", 0), "gol_sayisi": gol_final,
            "gol_hesaplanan": v["gol"], "gol_ayak": v.get("gol_ayak", 0),
            "gol_kafa": v.get("gol_kafa", 0), "penalti_gol": v.get("penalti_gol", 0),
            "gol_ort": round(gol_final / mac, 2) if mac else 0,
            "sari_kart": v["sari"], "kirmizi_kart": v["kirmizi"],
            "toplam_dakika": v["dakika"],
            "mac_gecmisi": sorted(v.get("mac_gecmisi", []), key=lambda x: x["hafta"]),
        })
    oyuncular.sort(key=lambda x: (-x["gol_sayisi"], -x["mac_sayisi"]))
    kid_takim = {o["kisi_id"]: o["takim"] for o in oyuncular if o.get("takim")}
    gol_kralicesi = sorted([{"oyuncu": r["oyuncu"], "takim": kid_takim.get(r["kisi_id"], ""),
                             "gol": r["gol"], "kisi_id": r["kisi_id"]} for r in resmi_list],
                           key=lambda x: -x["gol"])

    out = {"lig": LIG_ADI, "kategori": "altyas", "guncelleme": date.today().isoformat(),
           "gol_kralicesi": gol_kralicesi, "oyuncular": oyuncular}
    json.dump(out, open("altlig_u17.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[OK] altlig_u17.json — {len(oyuncular)} oyuncu, {len(u17_macids)} maç")


if __name__ == "__main__":
    main()
