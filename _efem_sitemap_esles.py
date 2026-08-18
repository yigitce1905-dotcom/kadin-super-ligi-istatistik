# -*- coding: utf-8 -*-
"""efem sitemap'ini indir, değerlendirilmemiş oyuncularımızın kaçının URL'si var bak."""
import re, sys, json, unicodedata
from urllib.parse import unquote
import requests
sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z0-9 ]"," ", s)).strip()

# sitemap indeksinden alt-sitemap'leri al, hepsini indir, isim->url
idx = requests.get("https://efem.club/players/sitemap.xml", headers=H, timeout=30)
subs = re.findall(r"<loc>([^<]+)</loc>", idx.text)
if not subs:  # belki tek dosya
    subs = ["https://efem.club/players/sitemap/0.xml"]
n2u = {}
for i, s in enumerate(subs[:5]):   # ilk birkaç dosya (kopya olabilir, birleşik küme yeter)
    try:
        r = requests.get(s, headers=H, timeout=30)
    except Exception:
        continue
    for loc in re.findall(r"/players/(\d+)-([^<]+)</loc>", r.text):
        idd, ad = loc
        n2u[norm(unquote(ad).replace("-", " "))] = f"https://efem.club/players/{idd}-{ad}"
print("sitemap benzersiz isim:", len(n2u))

d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
degerlendirilmemis = [i for i in d if not d[i].get("degerlendirildi")]
tam = {i: n2u[norm(i)] for i in degerlendirilmemis if norm(i) in n2u}
print(f"Değerlendirilmemiş: {len(degerlendirilmemis)} | sitemap'te TAM eşleşen: {len(tam)}")
for i, u in list(tam.items())[:15]:
    print("  ✓", i, "->", u[-45:])
# değerlendirilmiş dahil tüm havuz eşleşmesi
tum_tam = sum(1 for i in d if norm(i) in n2u)
print(f"TÜM havuz ({len(d)}) sitemap eşleşmesi: {tum_tam}")
