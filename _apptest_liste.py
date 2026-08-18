# -*- coding: utf-8 -*-
"""AppTest ile scouting listesini gerçek bağlamda üret, HTML'i incele."""
import sys, re
sys.stdout.reconfigure(encoding="utf-8")
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=180)
at.session_state["kulup_giris"] = True
at.session_state["kulup_kullanici"] = "admin"
at.session_state["kulup_tier"] = "admin"
at.session_state["sayfa"] = "scouting"
at.run()
if at.exception:
    print("EXC:", at.exception[0].value if at.exception else "")
# ws-table içeren markdown'ı bul
sat = None
for md in at.markdown:
    if "ws-table" in (md.value or ""):
        sat = md.value
        break
if not sat:
    print("liste markdown'ı bulunamadı; toplam markdown:", len(at.markdown))
    sys.exit(0)
print(f"liste HTML uzunluğu: {len(sat)}")
# bütünlük taramaları
ham = [(m.start(), hex(ord(sat[m.start()]))) for m in re.finditer(r"[\x00-\x1f\ud800-\udfff�]", sat) if sat[m.start()] != "\n"]
print("kontrol/surrogate:", ham[:5])
print("satır sonu (\n) sayısı:", sat.count("\n"))
# markdown'ı bölen çift newline?
if "\n\n" in sat:
    k = sat.index("\n\n")
    print("⚠️ ÇİFT \n bulundu! bağlam:", repr(sat[max(0,k-200):k+80]))
elif "\n" in sat:
    k = sat.index("\n")
    print("tek \n bağlamı:", repr(sat[max(0,k-200):k+80]))
# tr/td dengesi
print("tr aç/kapa:", len(re.findall(r"<tr>", sat)), len(re.findall(r"</tr>", sat)))
print("td aç/kapa:", len(re.findall(r"<td", sat)), len(re.findall(r"</td>", sat)))
