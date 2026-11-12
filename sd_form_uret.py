"""Maç raporlarından (sd_dizilis_*.json) oyuncu başına BU SEZON özeti üretir → sd_form_2026_27.json

Neden (13 Kasım 2026): açık olay verisi (StatsBomb) 2023/24'te kalıyor, FBref gelişmiş veriyi kaldırdı.
Havuzdaki oyuncunun bu sezon oynayıp oynamadığını gösteren güncel ve kullanabildiğimiz tek kaynak
SoccerDonna maç raporları: kadroya girdi mi, ilk 11 mi, kaç dakika, son beş maçta ne oldu.

Kayıt anahtarı SoccerDonna oyuncu kimliğidir (profil_url'deki spieler_<id>):
  {"ad", "takim", "lig", "tm" (takımın, oyuncunun o takımdaki İLK kadro gününden beri raporu olan maç sayısı),
   "kadro" (maç kadrosuna girdiği), "ilk11", "sonradan", "dk", "gol", "asist", "sari", "kirmizi",
   "son5" (takımın son 5 maçı, eskiden yeniye: S ilk 11 · Y sonradan girdi · B yedekte kaldı · - kadroda yok),
   "son" (son forma giydiği maçın tarihi, yyyy-aa-gg)}

TAKIM DEĞİŞTİREN OYUNCU: sayılar takım takım tutulur; yalnız EN SON kadroya girdiği takımın dönemi yazılır
(ilk sürüm iki takımı toplayıp eski takımın maç sayısına bölüyordu: NWSL'den WSL'e geçen kaleci "9/29" görünüyordu).
Ligin son maçından 60 günden fazla önce kadrodan çıkmış ve başka takımda görünmeyen oyuncunun kaydı YAZILMAZ:
büyük olasılıkla kapsam dışı bir lige gitmiştir; eski takımın "kadroda yok" satırı yanıltır.

Dakika hesabı yaklaşıktır: maç 90 dk sayılır, uzatmalar ve kırmızı kart sonrası eksik süre hesaba
katılmaz (ilk 11 → çıktığı dakika ya da 90; sonradan giren → 90 − girdiği dakika).

Kullanım:
    python sd_form_tazele.py                # yedi ligi tazeler + bu betiği çalıştırır
    python sd_form_uret.py                  # yalnız özeti yeniden üret
"""
import datetime
import glob
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
CIKTI = KOK / "sd_form_2026_27.json"
BAYAT_GUN = 60


def _dk(s):
    m = re.match(r"(\d+)", str(s or ""))
    return min(int(m.group(1)), 90) if m else None


def _tarih(s):
    try:
        g, a, y = str(s).split(".")
        return datetime.date(int(y), int(a), int(g))
    except Exception:
        return datetime.date(1900, 1, 1)


def main():
    donem = {}            # (sd_id, takım kimliği) → sayaçlar
    takim_mac = {}        # (lig, takım kimliği) → [(tarih, {sd_id: durum})]
    lig_son, ligler = {}, []
    for yol in sorted(glob.glob(str(KOK / "sd_dizilis_*.json"))):
        veri = json.load(open(yol, encoding="utf-8"))
        kod = veri.get("lig_kod") or "TUR1"
        maclar = sorted((m for m in veri.get("maclar", []) if m.get("ilk11", {}).get("ev") and m.get("ilk11", {}).get("dep")),
                        key=lambda m: _tarih(m.get("tarih")))
        if not maclar:
            continue
        for m in maclar:
            tarih = _tarih(m.get("tarih"))
            macta = {}                                   # sd_id → dönem kaydı (gol/kart yazmak için)
            for taraf in ("ev", "dep"):
                tid = (kod, m.get(taraf + "_id") or m.get(taraf))
                tad = m.get(taraf, "")
                durum = {}
                giren = {d["giren_sd_id"]: _dk(d["dk"]) for d in m.get("degisiklikler", []) if d["taraf"] == taraf and d.get("giren_sd_id")}
                cikan = {d["cikan_sd_id"]: _dk(d["dk"]) for d in m.get("degisiklikler", []) if d["taraf"] == taraf and d.get("cikan_sd_id")}
                for p in m["ilk11"].get(taraf, []):
                    if p.get("sd_id"):
                        durum[p["sd_id"]] = ("S", (cikan.get(p["sd_id"]) or 90), p["ad"])
                for p in m.get("yedekler", {}).get(taraf, []):
                    sid = p.get("sd_id")
                    if not sid or sid in durum:
                        continue
                    if sid in giren and giren[sid] is not None:
                        durum[sid] = ("Y", max(1, (cikan.get(sid) or 90) - giren[sid]), p["ad"])
                    else:
                        durum[sid] = ("B", 0, p["ad"])
                takim_mac.setdefault(tid, []).append((tarih, durum))
                for sid, (kod_d, dk, ad) in durum.items():
                    o = donem.setdefault((sid, tid), {"ad": ad, "takim": tad, "lig": kod, "kadro": 0, "ilk11": 0, "sonradan": 0,
                                                      "dk": 0, "gol": 0, "asist": 0, "sari": 0, "kirmizi": 0, "son": "",
                                                      "_ilk": tarih, "_sonk": tarih})
                    o["kadro"] += 1
                    o["ilk11"] += kod_d == "S"
                    o["sonradan"] += kod_d == "Y"
                    o["dk"] += dk
                    o["_sonk"] = tarih
                    if kod_d in ("S", "Y"):
                        o["son"] = tarih.isoformat()
                    macta[sid] = o
            for g in m.get("goller", []):
                if g.get("sd_id") in macta and "own goal" not in (g.get("tur") or "").lower():
                    macta[g["sd_id"]]["gol"] += 1
                if g.get("asist_sd_id") in macta:
                    macta[g["asist_sd_id"]]["asist"] += 1
            for k in m.get("kartlar", []):
                if k.get("sd_id") in macta:
                    macta[k["sd_id"]]["kirmizi" if "red" in (k.get("kart") or "").lower() else "sari"] += 1
        lig_son[kod] = _tarih(maclar[-1].get("tarih"))
        ligler.append({"kod": kod, "ad": veri.get("lig", kod), "mac": len(maclar), "raporsuz": len(veri.get("raporsuz", [])),
                       "son_mac": lig_son[kod].isoformat(), "guncelleme": veri.get("guncelleme", "")})
        print(f"{kod:5} {veri.get('lig', ''):26} {len(maclar):4} maç · son maç {ligler[-1]['son_mac']} · raporsuz {ligler[-1]['raporsuz']}")

    # oyuncu başına en son kadroya girdiği dönem
    guncel = {}
    for (sid, tid), o in donem.items():
        if sid not in guncel or o["_sonk"] > guncel[sid][1]["_sonk"]:
            guncel[sid] = (tid, o)
    oyuncu, bayat, cok_takim = {}, 0, 0
    sayim = {}
    for (sid, _tid) in donem:
        sayim[sid] = sayim.get(sid, 0) + 1
    for sid, (tid, o) in guncel.items():
        if (lig_son[o["lig"]] - o["_sonk"]).days > BAYAT_GUN:
            bayat += 1
            continue
        cok_takim += sayim[sid] > 1
        tm = [(t, d) for t, d in takim_mac[tid] if t >= o["_ilk"]]
        kayit = {k: v for k, v in o.items() if not k.startswith("_")}
        kayit["tm"] = len(tm)
        kayit["son5"] = "".join((d.get(sid) or ("-",))[0] for _, d in tm[-5:])
        oyuncu[str(sid)] = kayit
    cikti = {"guncelleme": datetime.date.today().isoformat(), "kaynak": "soccerdonna.de maç raporları", "ligler": ligler,
             "oyuncular": oyuncu}
    json.dump(cikti, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"\n{len(oyuncu)} oyuncu → {CIKTI.name} ({CIKTI.stat().st_size // 1024} KB) · "
          f"birden çok takımda görünen {cok_takim} · bayat olduğu için yazılmayan {bayat}")


if __name__ == "__main__":
    main()
