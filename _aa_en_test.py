# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")
sorgular = [
    "left-footed u23 centre back good in the air",
    "free agent bargain winger",
    "young keeper with great reflexes",
    "fast striker under 25 max 100k",
    "creative midfielder between 20 and 26",
    "experienced leader centre back",
    "clinical finisher willing to move",
    "strong holding mid over 28",
]
for q in sorgular:
    ozet, son = app.akilli_arama(q)
    if ozet is None:
        print(f"{q:46} -> ÇÖZÜLEMEDİ ⚠️"); continue
    ilk = (son[0]["isim"] + f" ({son[0]['nihai']})") if son else "—"
    print(f"{q:46} -> {' · '.join(ozet)}  [{len(son)} sonuç, 1.: {ilk}]")
