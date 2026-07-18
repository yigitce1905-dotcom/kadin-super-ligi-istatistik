# -*- coding: utf-8 -*-
"""KIRIK PROFİL TARAMASI — kaynaklar arası anahtar tutarlılığı raporu.

Sheet ↔ SoccerDonna ↔ kariyer dosyaları arasında isim yazımı (diakritik/
büyük-küçük) uyuşmazlıklarını ve eksik bağları listeler. Kod toleranslı
olsa da bu rapor veri hijyeni için aylık bakımda çalışır (Yiğit, 18.07.2026:
'böyle hataları bana derhal ilet').

Kullanım:  python profil_tutarlilik_tarama.py     (ağ erişimi gerektirmez)
"""
import json, sys, unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent

def n(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())

def yukle(ad):
    yol = KOK / ad
    return json.load(open(yol, encoding="utf-8")) if yol.exists() else {}

dunya  = yukle("scout_kadro_raporlar.json")
scotr  = yukle("scotr_raporlar.json")
sd_d   = yukle("scouting_sd_profiller.json")
sd_tr  = yukle("soccerdonna_profiller.json")
l_d    = yukle("scouting_leistungsdaten.json")

sd_hepsi = {**sd_d, **sd_tr}
sd_norm  = {n(k): k for k in sd_hepsi}
l_norm   = {n(k): k for k in l_d}

sorun = 0
def bolum(baslik, liste, ornek=8):
    global sorun
    print(f"\n── {baslik}: {len(liste)}")
    for x in liste[:ornek]:
        print(f"   {x}")
    if len(liste) > ornek:
        print(f"   … +{len(liste) - ornek} daha")
    sorun += len(liste)

# 1) Diakritik uyuşmazlığı: sheet anahtarı SD'de birebir yok ama norm'da var
farkli = [f"sheet={k!r}  sd={sd_norm[n(k)]!r}"
          for k in list(dunya) + list(scotr)
          if k not in sd_hepsi and n(k) in sd_norm]
bolum("Yazım farkı (kod toleranslı; sheet/SD eşitlenirse daha temiz)", farkli)

# 2) SD profili hiç olmayanlar (bulunamadı işaretli olanlar hariç)
sd_yok = [k for k in list(dunya) + list(scotr)
          if n(k) not in sd_norm]
bolum("SD profili HİÇ yok (profil künyesi eksik kalır)", sd_yok)

# 3) Dünya + TR havuzlarında ÇİFT kayıt (aynı kişi iki sheet'te)
d_norm = {n(k) for k in dunya}
cift = [k for k in scotr if n(k) in d_norm]
bolum("İki sheet'te birden kayıtlı (dünya kaydı öncelik alır)", cift)

# 4) Değerlendirilmiş ama kariyeri (leistung) olmayan dünya oyuncuları
kariyersiz = [k for k, v in dunya.items()
              if v.get("degerlendirildi") and n(k) not in l_norm]
bolum("Değerlendirilmiş ama kariyer verisi yok", kariyersiz)

print(f"\n{'='*56}\nTOPLAM bulgu: {sorun}"
      + ("  →  Yiğit'e ilet!" if sorun else "  —  tertemiz ✓"))
