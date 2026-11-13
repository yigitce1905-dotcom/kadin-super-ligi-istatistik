"""Ligler arası özet → lig_capraz.json (site: sol menüde "Tüm Ligler" kipi + herkese açık ?ligler=1 sayfası).

Neden (13 Kasım 2026, Yiğit: Opta'nın ilk 20 ligi "iyi ligler çünkü verileri çekilebilir"): her lig ayrı ayrı gezilebiliyordu
ama "bütün liglerde en çok gol atan 20 yaş altı kim" sorusunun cevabı yoktu. Site 21 ligin tamamını aynı anda belleğe
alamaz (Render 512 MB; lig başına ~8 MB) → özet çevrimdışı üretilir, site yalnız bu küçük dosyayı okur.

    python lig_capraz_uret.py

sd_form_tazele.py haftalık tazelemenin sonunda bunu da çalıştırır. Kupalar (UEFA) dahil DEĞİL: aynı oyuncu iki kez sayılmasın.
Oyuncu eşiği: en az 90 dakika ya da en az bir gol/asist (tek maçta 5 dakika oynayanlar listeyi şişirmesin).
"""
import datetime
import json
import sys

import lig_motor as M

sys.stdout.reconfigure(encoding="utf-8")
CIKTI = M.KOK / "lig_capraz.json"
TR = ("🇹🇷", "Kadınlar Süper Ligi", M.KOK / "sd_dizilis_2026_27.json")
# oyuncu satırı sütunları (dosya küçük kalsın diye liste; site bu sırayla okur)
SUTUN = ["sid", "ad", "takim", "lig", "yas", "grup", "mac", "ilk11", "dk", "gol", "asist", "sari", "kirmizi", "yg", "gy", "tm"]


def main():
    kaynak = [("TUR1", TR[0], TR[1], TR[2])]
    kaynak += [(k, b, ad, M.lig_dosya(k)) for k, (b, ad, _) in M.LIG_SAYFA.items() if k not in M.LIG_KUPA]
    ligler, oyuncular = [], []
    for kod, bayrak, ad, yol in kaynak:
        if not yol.exists():
            print(f"{kod:5} dosya yok, atlandı")
            continue
        veri = json.load(open(yol, encoding="utf-8"))
        L = M.hesapla(veri)
        if not L["mac_sayisi"]:
            continue
        saha = [o for o in L["oyuncu"].values() if o["mac"] > 0]
        golcu = max(saha, key=lambda o: (o["gol"], -o["dk"])) if saha else None
        lider = L["puan"][0] if L["puan"] else {}
        ligler.append({"kod": kod, "bayrak": bayrak, "ad": ad, "opta": M.OPTA_SIRA.get(kod), "mac": L["mac_sayisi"], "raporsuz": L["raporsuz"],
                       "takim": len(L["takim"]), "oyuncu": len(saha), "son_mac": L["son_mac"],
                       "gol": sum(int(m["skor"].split(":")[0]) + int(m["skor"].split(":")[1]) for m in veri.get("maclar", [])
                                  if str(m.get("skor") or "").replace(":", "").isdigit()),
                       "lider": lider.get("ad", ""), "lider_p": 3 * lider.get("g", 0) + lider.get("b", 0), "lider_o": lider.get("o", 0),
                       "golcu": ([golcu["ad"], golcu["takim"], golcu["gol"]] if golcu and golcu["gol"] else None),
                       "guncelleme": veri.get("guncelleme", "")})
        n = 0
        for o in saha:
            if o["dk"] < 90 and not o["gol"] and not o["asist"]:
                continue
            tm = (L["takim"].get(o["takim"]) or {}).get("rapor", 0)
            oyuncular.append([o["sid"], o["ad"], o["takim"], kod, (int(o["yas"]) if o.get("yas") else None), o.get("grup", ""), o["mac"], o["ilk11"],
                              o["dk"], o["gol"], o["asist"], o["sari"], o["kirmizi"], o["yg"], o["gy"], tm])
            n += 1
        print(f"{kod:5} {ad[:28]:28} maç {L['mac_sayisi']:3} · oyuncu {n:3} · lider {lider.get('ad', '')[:24]:24} · golcü "
              + (f"{golcu['ad']} {golcu['gol']}" if golcu and golcu["gol"] else "—"))
    ligler.sort(key=lambda x: (x["opta"] is None, x["opta"] or 0, x["kod"] != "TUR1", x["ad"]))
    json.dump({"guncelleme": datetime.date.today().isoformat(), "sutun": SUTUN, "ligler": ligler, "oyuncular": oyuncular},
              open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"\n{len(ligler)} lig · {len(oyuncular)} oyuncu → {CIKTI.name} ({CIKTI.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
