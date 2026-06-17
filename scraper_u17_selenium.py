"""
TFF U17 Kızlar Gelişim Ligi — Selenium tabanlı veri toplayıcı (LOKAL ÇALIŞTIR).

NEDEN SELENIUM: U17 fikstürü Telerik/ASP.NET postback widget'ıyla yükleniyor
(temiz ?hafta= URL'si YOK; haftalar __doPostBack ile geliyor). Süper/1./2. Lig'de
temiz URL vardı, burada yok. Bu yüzden tarayıcıyı sürerek (senin elle yaptığın
gibi: grup → hafta okları → maç) macId'leri topluyoruz. Maç DETAYLARI normal
(requests + mevcut parse mantığı) — sadece macId'leri keşfetmek için Selenium.

KURULUM (lokal):
    pip install selenium
    # Chrome kurulu olmalı (Selenium 4 chromedriver'ı otomatik indirir)

ÇALIŞTIR:
    python scraper_u17_selenium.py

ÇIKTI: altlig_u17.json  (consolidated oyuncu listesi + top-10 gol kraliçesi)
       — grup puan durumu YOK (kullanıcı istemedi), tek toplu liste.
"""
import json, re, time, urllib3
from datetime import date
import requests
from bs4 import BeautifulSoup
import scraper  # süper lig maç-detay parse mantığı (mac_detayi_isle vb.)

urllib3.disable_warnings()
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://www.tff.org/"
PAGE = 1760
LIG_ADI = "U17 Kızlar Gelişim Ligi"
GRUP_IDS = list(range(3450, 3482))   # 32 grup (1..32)
CIKTI = "altlig_u17.json"

# ── Maç detayını requests ile çek (verify=False + cache); Selenium sadece keşif için
_cache = {}
def fetch(url):
    if url in _cache:
        return _cache[url]
    for _ in range(3):
        try:
            r = requests.get(url, headers=HDR, timeout=25, verify=False)
            r.raise_for_status()
            s = BeautifulSoup(r.content, "lxml")
            _cache[url] = s
            return s
        except Exception:
            time.sleep(2)
    return None
scraper.fetch = lambda session, url, yeniden=3: fetch(url)


def standings_takim_grup():
    """Her grubun takımlarını çek → TAKIM(upper) -> grup_no (1..32)."""
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
        print(f"  grup {idx}: standings OK")
    return tg


def gol_kralicesi_cek():
    s = fetch(f"{BASE}default.aspx?pageID={PAGE}")
    tbl = None
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
        if not nums:
            continue
        out.append({"oyuncu": a.get_text(" ", strip=True), "gol": int(nums[-1]),
                    "kisi_id": re.search(r"kisiID=(\d+)", a["href"], re.I).group(1)})
    return out


def macidleri_topla_selenium():
    """Selenium ile her grubun fikstüründe haftaları gezip macId topla."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--log-level=3")
    drv = webdriver.Chrome(options=opts)
    drv.set_page_load_timeout(40)
    macids = set()
    try:
        for idx, gid in enumerate(GRUP_IDS, 1):
            try:
                drv.get(f"{BASE}default.aspx?pageID={PAGE}&grupID={gid}")
            except Exception:
                pass
            time.sleep(2.0)

            def topla():
                for a in drv.find_elements(By.CSS_SELECTOR, 'a[href*="macId="]'):
                    h = a.get_attribute("href") or ""
                    m = re.search(r"macId=(\d+)", h)
                    if m:
                        macids.add(m.group(1))

            topla()
            # « (geri) ve » (ileri) oklarını tıklayarak tüm haftaları gez
            for sym in ("«", "»"):
                bos = 0
                for _ in range(20):
                    onceki = len(macids)
                    try:
                        oklar = [e for e in drv.find_elements(By.TAG_NAME, "a")
                                 if e.text.strip() == sym]
                        if not oklar:
                            break
                        drv.execute_script("arguments[0].click();", oklar[0])
                        time.sleep(1.1)
                    except Exception:
                        break
                    topla()
                    bos = bos + 1 if len(macids) == onceki else 0
                    if bos >= 3:   # 3 ardışık adımda yeni maç yoksa dur
                        break
                drv.get(f"{BASE}default.aspx?pageID={PAGE}&grupID={gid}")
                time.sleep(1.5)
            print(f"  grup {idx}: toplam macId {len(macids)}")
    finally:
        drv.quit()
    return macids


def main():
    print(f"=== {LIG_ADI} (Selenium) ===")
    print("1) Standings → takım/grup eşlemesi...")
    takim_grup = standings_takim_grup()
    bizim = set(takim_grup.keys())
    print(f"   {len(bizim)} U17 takımı")

    print("2) Selenium ile fikstür macId keşfi (uzun sürer)...")
    macids = macidleri_topla_selenium()
    print(f"   toplam tekil macId: {len(macids)}")

    print("3) Maç detayları (requests) → oyuncu istatistikleri...")
    oyuncu_dict = {}
    islenen = 0
    for mid in sorted(macids):
        url = f"{BASE}Default.aspx?pageID=29&macId={mid}"
        s = fetch(url)
        if not s:
            continue
        tk = [e.get_text(strip=True) for e in s.select(".TakimAdi")][:2]
        if len(tk) < 2 or tk[0].upper() not in bizim or tk[1].upper() not in bizim:
            continue   # U17 takımı olmayan (başka lig) maç — atla
        islenen += 1
        scraper.mac_detayi_isle(None, {"url": url, "ev": tk[0], "dep": tk[1]}, oyuncu_dict, islenen)
        time.sleep(0.4)
        if islenen % 50 == 0:
            print(f"   işlenen maç: {islenen}")
    print(f"   işlenen U17 maçı: {islenen}")

    print("4) Resmi gol kraliçesi (top-10)...")
    resmi_list = gol_kralicesi_cek()
    resmi = {r["kisi_id"]: r["gol"] for r in resmi_list}

    oyuncular = []
    for kid, v in oyuncu_dict.items():
        mac = v["mac"]
        ts = v.get("takim_stats", {})
        birincil = max(ts, key=lambda t: ts[t]["mac"]) if ts else v.get("_takim_set", "")
        takim_listesi = sorted(ts.items(), key=lambda x: -x[1]["mac"])
        # Gol: resmi top-10'da varsa onu kullan (otorite), yoksa hesaplanan
        gol_final = resmi.get(kid, v["gol"])
        oyuncular.append({
            "kisi_id": kid, "oyuncu": v["isim"], "takim": birincil,
            "tum_takimlar": " / ".join(t for t, _ in takim_listesi),
            "grup": takim_grup.get(birincil.upper(), ""), "lig": LIG_ADI,
            "mac_sayisi": mac, "ilk11_mac": v.get("ilk11_mac", 0),
            "yedek_mac": v.get("yedek_mac", 0), "gol_sayisi": gol_final,
            "gol_hesaplanan": v["gol"],
            "gol_ayak": v.get("gol_ayak", 0), "gol_kafa": v.get("gol_kafa", 0),
            "penalti_gol": v.get("penalti_gol", 0),
            "gol_ort": round(gol_final / mac, 2) if mac else 0,
            "sari_kart": v["sari"], "kirmizi_kart": v["kirmizi"],
            "toplam_dakika": v["dakika"],
            "mac_gecmisi": sorted(v.get("mac_gecmisi", []), key=lambda x: x["hafta"]),
        })
    oyuncular.sort(key=lambda x: (-x["gol_sayisi"], -x["mac_sayisi"]))

    # gol kraliçesi takımı bizim verimizden
    kid_takim = {o["kisi_id"]: o["takim"] for o in oyuncular if o.get("takim")}
    gol_kralicesi = sorted(
        [{"oyuncu": r["oyuncu"], "takim": kid_takim.get(r["kisi_id"], ""),
          "gol": r["gol"], "kisi_id": r["kisi_id"]} for r in resmi_list],
        key=lambda x: -x["gol"])

    out = {"lig": LIG_ADI, "kategori": "altyas", "guncelleme": date.today().isoformat(),
           "gol_kralicesi": gol_kralicesi, "oyuncular": oyuncular}
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] {CIKTI} — {len(oyuncular)} oyuncu, {islenen} maç, {len(gol_kralicesi)} top golcü")


if __name__ == "__main__":
    main()
