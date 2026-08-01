# -*- coding: utf-8 -*-
"""
TFF Kadinlar Super Ligi ARSIV sezonlari scraper (2026-08-02, Baran'in site
mimarisi plani - Faz 3). scraper.py'nin mac-detay parse mantigini (mac_detayi_isle)
yeniden kullanir; sadece haftalik fikstur URL'si sezona gore parametrik.

Dogrulanan pageID'ler (tff.org/default.aspx?pageID=848 arsiv sayfasindan):
  2024-25 -> 1735   2023-24 -> 1653   2022-23 -> 1623 (FARKLI SAYFA YAPISI,
  hafta=N parametresiyle mac donmuyor - ayri inceleme gerekir, bu script'te YOK).

Kullanim:
  python scraper_arsiv.py            # tum tanimli sezonlar
  python scraper_arsiv.py 2023-24    # sadece bir sezon
"""
import sys, time, json
sys.stdout.reconfigure(encoding="utf-8")
import requests, urllib3
urllib3.disable_warnings()
import scraper  # fetch/mac_detayi_isle/HEADERS/DETAY_BASE yeniden kullanilir

SEZONLAR = {
    "2024-25": {"pageid": 1735, "cikti": "arsiv_2024_25.json"},
    "2023-24": {"pageid": 1653, "cikti": "arsiv_2023_24.json"},
}
TOPLAM_HAFTA  = 30
HAFTA_BEKLEME = 1.0
MAC_BEKLEME   = 1.2


def mac_linklerini_topla_arsiv(session, pageid, hafta_no):
    url = f"https://www.tff.org/Default.aspx?pageID={pageid}&hafta={hafta_no}"
    soup = scraper.fetch(session, url)
    if not soup:
        return []
    mac_linkleri = []
    for tr in soup.select("tr.haftaninMaclariTr"):
        td = tr.find("td", class_="haftaninMaclariSkor") or tr.find("td", class_="haftaninMaclariDetay")
        if not td:
            continue
        a = td.find("a", href=True)
        if not a or "macId=" not in a["href"]:
            continue
        ev_td  = tr.find("td", class_="haftaninMaclariEv")
        dep_td = tr.find("td", class_="haftaninMaclariDeplasman")
        mac_linkleri.append({
            "url": scraper.DETAY_BASE + a["href"].lstrip("/"),
            "ev":  ev_td.get_text(strip=True)  if ev_td  else "",
            "dep": dep_td.get_text(strip=True) if dep_td else "",
        })
    return mac_linkleri


def _oyuncu_dict_to_liste(oyuncu_dict):
    """scraper.veriyi_kaydet ile AYNI donusum (oyuncular.json ile ayni liste formati),
    ama dosyaya yazmadan liste dondurur (app.py arsiv_sezon_yukle() bu formati bekler)."""
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
    return liste


def sezon_cek(sezon_ad, pageid, cikti_json, toplam_hafta=TOPLAM_HAFTA, ilk_hafta=1):
    print("=" * 62)
    print(f"  TFF ARSIV -- {sezon_ad} (pageID={pageid})")
    print("=" * 62)
    session     = requests.Session()
    oyuncu_dict = {}
    toplam_mac  = 0
    bos_hafta   = 0
    for hafta in range(ilk_hafta, toplam_hafta + 1):
        maclar = mac_linklerini_topla_arsiv(session, pageid, hafta)
        if not maclar:
            bos_hafta += 1
            print(f"  [{hafta:2d}. hafta] mac yok (bos ust uste: {bos_hafta})")
            if bos_hafta >= 5:
                print("  [X] 5 bos hafta ust uste, duruluyor.")
                break
            time.sleep(HAFTA_BEKLEME)
            continue
        bos_hafta = 0
        print(f"  [{hafta:2d}. hafta] {len(maclar)} mac")
        for i, mac in enumerate(maclar, 1):
            scraper.mac_detayi_isle(session, mac, oyuncu_dict, hafta)
            toplam_mac += 1
            time.sleep(MAC_BEKLEME)
        time.sleep(HAFTA_BEKLEME)
    liste = _oyuncu_dict_to_liste(oyuncu_dict)
    with open(cikti_json, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=1)
    print(f"  BITTI: {len(liste)} oyuncu, {toplam_mac} mac -> {cikti_json}")
    return liste


if __name__ == "__main__":
    hedef = sys.argv[1] if len(sys.argv) > 1 else "all"
    for ad, cfg in SEZONLAR.items():
        if hedef != "all" and hedef != ad:
            continue
        sezon_cek(ad, cfg["pageid"], cfg["cikti"])
    print("\nTum sezonlar tamamlandi.")
