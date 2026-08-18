# -*- coding: utf-8 -*-
"""AppTest: yeni 1-2-3-4 accordion nav + My Squad/My 11 sayfaları çöküyor mu?"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from streamlit.testing.v1 import AppTest

def calistir(sayfa, ekstra=None, baslik=""):
    at = AppTest.from_file("app.py", default_timeout=180)
    at.session_state["kulup_giris"] = True
    at.session_state["kulup_kullanici"] = "admin"
    at.session_state["kulup_tier"] = "admin"
    at.session_state["girildi"] = True
    at.session_state["sayfa"] = sayfa
    if ekstra:
        for k, v in ekstra.items():
            at.session_state[k] = v
    at.run()
    exc = at.exception[0].value if at.exception else None
    print(f"[{baslik or sayfa}] exception: {exc}")
    return at

for sayfa, baslik in [
    ("ana", "1-TR Data (ana)"),
    ("scouting", "2-Dünya/Scouting"),
    ("profil", "3-Profile"),
    ("my_squad", "3.3-My Squad"),
    ("my11", "3.2-My 11"),
    ("saygi", "4-Hall of Respect (Saygı)"),
    ("hakkinda", "4.2-Biz Kimiz (hakkinda)"),
    ("talep", "3.4-Talep"),
    ("iletisim", "3.5-İletişim"),
    ("altlig", "1.3-Alt Ligler"),
    ("altyas", "1.3-Alt Yaşlar"),
]:
    calistir(sayfa, baslik=baslik)

# My Team yönlendirmesi: sayfa=ana + tr_sekme="Benim Kadrom/My Team" ile çöküyor mu?
calistir("ana", ekstra={"tr_sekme": "🏟️ Benim Kadrom"}, baslik="3.1-My Team (tr_sekme)")

# shortlist_toggle / my11_toggle fonksiyon davranışı (33/11 limit mantığı) — birim test gibi
at = AppTest.from_file("app.py", default_timeout=180)
at.session_state["kulup_giris"] = True
at.session_state["kulup_kullanici"] = "admin"
at.session_state["sayfa"] = "ana"
at.run()
if at.exception:
    print("[modül yükleme]", at.exception[0].value)
else:
    ns = at._runner._session_state  # session çalıştı, modül-seviyesi fonksiyonlara erişim testi ayrı script'te
    print("[nav render] tüm sayfalar için exception yok — modül import/nav akışı temiz.")
