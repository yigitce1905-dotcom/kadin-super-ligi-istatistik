# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")
# panel HTML üretimini doğrudan test et
import json
d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
r = d["Sam Kerr"]
for grup, ikon in (("beceri","⚽"),("beseri","🧠"),("fiziki","💪"),("sahsi","🎖️")):
    html = app._scotr_nitelik_paneli(grup.upper(), ikon, r.get(grup,{}), r.get("makro",{}).get(grup,""))
    print(f"{grup}: {len(r.get(grup,{}))} nitelik -> HTML {len(html)} karakter")
# render fonksiyonlarını uçtan uca çağır (streamlit no-op modda hata fırlatırsa görürüz)
try:
    app.render_scout_kadro_raporu("Sam Kerr")
    print("render_scout_kadro_raporu: HATASIZ")
except Exception as e:
    import traceback; traceback.print_exc()
