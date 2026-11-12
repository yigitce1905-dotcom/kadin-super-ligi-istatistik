"""Hudl StatsBomb açık verisini (kadın: 2023/24 ligleri, NWSL 2023, Euro 2025, Dünya Kupası 2023) indirir.

Kaynak: github.com/statsbomb/open-data — maç listeleri, kadrolar ve olay dosyaları (~866 maç, ~3 GB).
Hedef: depo DIŞINDA bir klasör (varsayılan Masaüstü\\statsbomb_veri). Ham veri depoya KONMAZ:
depo herkese açık ve lisans veriyi yeniden dağıtmayı yasaklıyor; ayrıca 3 GB.

    python sb_indir.py [hedef klasör]

Yarıda kesilirse yeniden çalıştır: inmiş dosyalar atlanır.
LİSANS (LICENSE.pdf): ticari kullanım ve yeniden dağıtım yasak; yayımlanan her analizde StatsBomb logosuyla kaynak gösterilir.
"""
import concurrent.futures as cf
import gzip
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
HEDEF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser("~"), "Desktop", "statsbomb_veri")
KOK = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
SEZON = {(37, 281): "WSL 2023/24", (131, 281): "Serie A 2023/24", (135, 281): "Frauen-Bundesliga 2023/24", (182, 281): "Liga F 2023/24",
         (49, 107): "NWSL 2023", (53, 315): "Euro 2025", (72, 107): "Dünya Kupası 2023"}


def getir(url, yol, deneme=4):
    if os.path.exists(yol) and os.path.getsize(yol) > 2:
        return 0
    son = None
    for i in range(deneme):
        try:
            # gzip iste: olay dosyaları ~3,5 MB JSON, sıkıştırılmış aktarımda ~10 kat küçük (sıkıştırmasız 27 dk'da 1,2 GB inmişti)
            istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(istek, timeout=120) as r:
                veri = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    veri = gzip.decompress(veri)
            if not veri.lstrip()[:1] in (b"[", b"{"):
                raise ValueError("JSON değil")
            with open(yol + ".kismi", "wb") as f:
                f.write(veri)
            os.replace(yol + ".kismi", yol)
            return len(veri)
        except Exception as e:
            son = e
            time.sleep(3 * (i + 1))
    raise son


def main():
    for alt in ("matches", "lineups", "events"):
        os.makedirs(os.path.join(HEDEF, alt), exist_ok=True)
    getir(f"{KOK}/competitions.json", os.path.join(HEDEF, "competitions.json"))
    maclar = {}
    for (c, s), ad in SEZON.items():
        yol = os.path.join(HEDEF, "matches", f"{c}_{s}.json")
        getir(f"{KOK}/matches/{c}/{s}.json", yol)
        m = json.load(open(yol, encoding="utf-8"))
        print(f"{ad:28} {len(m):4} maç", flush=True)
        for x in m:
            maclar[x["match_id"]] = ad
    isler = [(f"{KOK}/{alt}/{mid}.json", os.path.join(HEDEF, alt, f"{mid}.json")) for mid in maclar for alt in ("lineups", "events")]
    t0, toplam, biten, hata = time.time(), 0, 0, []
    with cf.ThreadPoolExecutor(8) as ex:
        gelecek = {ex.submit(getir, u, y): (u, y) for u, y in isler}
        for g in cf.as_completed(gelecek):
            biten += 1
            try:
                toplam += g.result()
            except Exception as e:
                hata.append((gelecek[g][0], f"{type(e).__name__}: {e}"))
            if biten % 200 == 0:
                print(f"  {biten}/{len(isler)} dosya · {toplam / 1e6:.0f} MB indi · {time.time() - t0:.0f} sn", flush=True)
    boyut = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(HEDEF) for f in fs)
    print(f"BİTTİ: {len(maclar)} maç · klasör {boyut / 1e9:.2f} GB · bu çalıştırmada {toplam / 1e6:.0f} MB · {time.time() - t0:.0f} sn · hata {len(hata)}")
    for u, e in hata[:10]:
        print("  HATA", u.rsplit('/', 2)[-2:], e)


if __name__ == "__main__":
    main()
