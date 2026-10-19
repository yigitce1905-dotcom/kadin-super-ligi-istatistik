# -*- coding: utf-8 -*-
"""TFF haftalık sayfasından (pageID=1000) maç SONUÇLARI + RESMİ PUAN DURUMU → mac_sonuclari.json, puan_durumu.json.

Haftalık rutin (scraper.py oyuncu istatistiklerini çeker; bu betik sonuç/puan tablosunu):
    python scraper.py               # oyuncular.json (oyuncu bazlı maç raporları)
    python tff_sonuc_guncelle.py    # mac_sonuclari.json + puan_durumu.json

• mac_sonuclari.json: mevcut kayıtlar KORUNUR (elle düzeltilmiş hükmen sonuçlar bozulmasın);
  yalnızca dosyada OLMAYAN (hafta, ev, dep) çiftleri eklenir. Oynanmamış maçlar ('-') atlanır.
• puan_durumu.json: TFF'nin resmi tablosu (s-table) o anki halidir, tamamen yenilenir.
"""
import json, re, sys, time, datetime
from pathlib import Path
import requests, urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()
sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
URL = "https://www.tff.org/Default.aspx?pageID=1000&hafta={h}"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SEZON_DOSYA = KOK / "veri" / "2026-27"           # varsa orası, yoksa kök (app.sezon_dosya ile aynı kural)


ANAHTARLAR = ["FENERBAH", "GALATASARAY", "BEŞİKTAŞ", "TRABZON", "FOMGET", "ANKARA", "AMED", "HAKKARİ", "ÜNYE",
              "GİRESUN", "1207", "YÜKSEKOVA", "ŞİLE", "ÇEKMEKÖY", "HAYMANA", "BAKIRKÖY", "KAYSERİ", "SULTANBEYLİ"]


def anahtar(ad):
    """Sponsor/uzun-kısa ad farklarına dayanıklı takım anahtarı (app._kanon ile aynı mantık)."""
    ad = (ad or "").replace("i̇", "i").upper().replace("İ", "İ")
    for k in ANAHTARLAR:
        if k in ad:
            return "FOMGET" if k == "ANKARA" else k
    return ad


def yol(ad):
    p = SEZON_DOSYA / ad
    return p if p.exists() else KOK / ad


def hafta_cek(h):
    """Haftalık sayfa. TFF bazen 200 OK ama maç satırları olmadan döner → birkaç kez dene."""
    son = None
    for _ in range(4):
        try:
            r = requests.get(URL.format(h=h), headers=H, timeout=30, verify=False)
            r.raise_for_status()
            son = BeautifulSoup(r.text, "lxml")
            if son.select("tr.haftaninMaclariTr") or h > 20:
                return son
        except Exception:
            pass
        time.sleep(3)
    return son


def main():
    mp = yol("mac_sonuclari.json")
    mevcut = json.load(open(mp, encoding="utf-8")) if mp.exists() else []
    var = {(m["hafta"], anahtar(m["ev"]), anahtar(m["dep"])) for m in mevcut}
    yeni, son_oynanan, tablo = [], 0, None
    for h in range(1, 31):
        soup = hafta_cek(h)
        if not soup:
            print(f"[{h}] sayfa çekilemedi"); continue
        oynanan = 0
        for tr in soup.select("tr.haftaninMaclariTr"):
            ev = tr.find("td", class_="haftaninMaclariEv"); dep = tr.find("td", class_="haftaninMaclariDeplasman")
            sk = tr.find("td", class_="haftaninMaclariSkor")
            if not (ev and dep and sk):
                continue
            m = re.fullmatch(r"\s*(\d+)\s*-\s*(\d+)\s*", sk.get_text(strip=True))
            if not m:
                continue                                  # '-' = oynanmadı/ertelendi
            oynanan += 1
            ad_ev, ad_dep = ev.get_text(strip=True), dep.get_text(strip=True)
            k = (h, anahtar(ad_ev), anahtar(ad_dep))
            if k not in var:
                yeni.append({"hafta": h, "ev": ad_ev, "dep": ad_dep, "ev_gol": int(m.group(1)), "dep_gol": int(m.group(2))})
                var.add(k)
        if oynanan:
            son_oynanan = h
            tablo = soup.find("table", class_="s-table") or tablo
        elif h > son_oynanan + 2:
            break                                         # arka arkaya boş haftalar → bitti
        time.sleep(1.0)
    print(f"Yeni maç sonucu: {len(yeni)} | son oynanan hafta: {son_oynanan}")
    for m in yeni:
        print(f"  H{m['hafta']}  {m['ev'][:26]:26} {m['ev_gol']}-{m['dep_gol']} {m['dep'][:26]}")
    if yeni:
        mevcut.extend(yeni)
        mevcut.sort(key=lambda m: (m["hafta"], m["ev"]))
        json.dump(mevcut, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[OK] {mp.name} güncellendi ({len(mevcut)} maç)")

    # resmi puan durumu: TFF hafta sayfasındaki tablo O HAFTAYA KADARKİ durumdur (hafta=30 sayfası
    # geride kalan bir tabloyu gösteriyor!) → SON OYNANAN haftanın sayfasındaki tablo kullanılır.
    if not tablo:
        print("[!] s-table bulunamadı, puan_durumu.json değişmedi"); return
    siralar = []
    for tr in tablo.find_all("tr"):
        c = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if len(c) >= 9 and re.match(r"\d+\.", c[0]):
            sira, ad = c[0].split(".", 1)
            siralar.append({"Sıra": int(sira), "Takım": ad.strip(), "O": c[1], "G": c[2], "B": c[3],
                            "M": c[4], "A": c[5], "Y": c[6], "AV": c[7], "P": c[8]})
    if len(siralar) < 14:
        print(f"[!] puan tablosu eksik ({len(siralar)} satır), yazılmadı"); return
    son_oynanan = max(int(x["O"]) for x in siralar if x["O"].isdigit())   # takım başına en çok oynanan maç
    bugun = datetime.date.today().strftime("%d.%m.%Y")
    pp = yol("puan_durumu.json")
    json.dump({"guncelleme": f"2026-27 sezonu {son_oynanan}. hafta ({bugun})",
               "not": "TFF resmi puan durumu (tff.org pageID=1000), tff_sonuc_guncelle.py ile çekildi.",
               "hafta": son_oynanan, "siralar": siralar},
              open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[OK] {pp.name} güncellendi: {len(siralar)} takım, lider {siralar[0]['Takım']} ({siralar[0]['P']} p)")


if __name__ == "__main__":
    main()
