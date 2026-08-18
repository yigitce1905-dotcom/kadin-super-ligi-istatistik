# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")

# 1) dil algılama testi — gerçek notlarla
d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
notlar = [(i, r["scout_notu"]) for i, r in d.items() if len(r.get("scout_notu", "")) > 40]
from collections import Counter
say = Counter(app._not_dili(n) for _, n in notlar)
print(f"Havuzdaki {len(notlar)} uzun not: {dict(say)}")
print("\n--- Örnek algılamalar ---")
for i, n in notlar[:3] + notlar[-3:]:
    print(f"  [{app._not_dili(n).upper()}] {i}: {n[:70]}...")

# 2) sınır durumları
for m, beklenen in [
    ("She is a complete goalkeeper with great reflexes and command.", "en"),
    ("Karar alma ve önsezisi dünya klasıdır.", "tr"),
    ("Cok iyi bir oyuncu ama sakatlik riski var", "tr"),   # TR ama özel harfsiz
    ("Top level box-to-box midfielder, needs a bigger team.", "en"),
]:
    algi = app._not_dili(m)
    print(f"  {'✓' if algi==beklenen else '✗'} [{algi}] {m[:55]}")
