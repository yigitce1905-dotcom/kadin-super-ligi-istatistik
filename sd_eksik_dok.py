"""SoccerDonna profili bağlı OLMAYAN oyuncuları döker: (1) Süper Lig (TFF oyuncular.json), (2) scouting havuzu.

    python sd_eksik_dok.py [çıktı.json]        # varsayılan: %TEMP%/sd_eksik.json
    python sd_eksik_coz.py <çıktı.json> --yaz   # eksikleri çözer (maç kadroları, kulüp kadroları, SD araması, elle kararlar)

Uygulamanın kendi eşleştirmesini kullanır (app.py test koşucusuyla çalıştırılır): sitede ne görünüyorsa onu sayar.
"_sd_yok" kanıtı taşıyan kayıtlar (SoccerDonna'da kaydı olmadığı elle doğrulananlar; sd_eksik_elle.json → "yok") eksik sayılmaz.
"""
import collections
import json
import os
import pathlib
import sys
import tempfile

from streamlit.testing.v1 import AppTest

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent
CIKTI = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "sd_eksik.json")
if os.path.exists(CIKTI):
    os.remove(CIKTI)
src = (KOK / "app.py").read_text(encoding="utf-8")
KANCA = '''
def _teshis_sd():
    import json as _j, re as _r
    tr = []
    for o in ham_liste:
        p = _sd_profil_bul(o["oyuncu"]) or {}
        m = _r.search(r"spieler_(\\d+)", str(p.get("profil_url") or ""))
        tr.append({"isim": o["oyuncu"], "takim": o["takim"], "mac": o.get("mac_sayisi"), "dk": o.get("toplam_dakika"), "gol": o.get("gol_sayisi"),
                   "sd_id": m.group(1) if m else None, "sd_isim": p.get("sd_isim", ""), "yok": bool(p.get("_sd_yok"))})
    sd = birlesik_sd_yukle()
    hv = []
    for isim, r in birlesik_scout_yukle().items():
        if not isinstance(r, dict):
            continue
        p = sd.get(isim) or {}
        m = _r.search(r"spieler_(\\d+)", str(p.get("profil_url") or "")) if isinstance(p, dict) else None
        hv.append({"isim": isim, "kulup": str(r.get("kulup") or ""), "lig": str(r.get("lig") or ""), "uyruk": str(r.get("vatandaslik") or ""),
                   "yas": str(r.get("yas") or ""), "dusuk": bool(_dusuk_notlu_tr_mi(r)), "nihai": str(r.get("nihai") or ""),
                   "sd_id": m.group(1) if m else None, "sd_var": bool(p), "yok": bool(isinstance(p, dict) and p.get("_sd_yok") and not m)})
    _j.dump({"tr": tr, "havuz": hv}, open(%r, "w", encoding="utf-8"), ensure_ascii=False)

_teshis_sd()
_bellek_izi()
''' % CIKTI
assert src.count("\n_bellek_izi()\n") == 1
src = src.replace("\n_bellek_izi()\n", KANCA, 1)
yol = KOK / "_teshis_app.py"
yol.write_text(src, encoding="utf-8")
try:
    at = AppTest.from_file(str(yol), default_timeout=600)
    at.query_params["kulup"] = "ornek"
    at.run()
    if at.exception or not os.path.exists(CIKTI):
        print("HATA: uygulama çalışmadı:", [str(e.value)[:300] for e in at.exception])
        sys.exit(1)
finally:
    yol.unlink()
v = json.load(open(CIKTI, encoding="utf-8"))
tr, hv = v["tr"], v["havuz"]
e_tr = [x for x in tr if not x["sd_id"] and not x["yok"]]
print(f"SÜPER LİG (TFF): {len(tr)} oyuncu · SD profili bağlı olmayan {len(e_tr)} · SD'de kaydı yok (doğrulanmış) {sum(1 for x in tr if x['yok'] and not x['sd_id'])}")
for x in sorted(e_tr, key=lambda x: -(x["dk"] or 0))[:60]:
    print(f"   {x['isim']:32} {x['takim'][:30]:30} maç {x['mac']:>2} dk {x['dk']:>4}")
gor = [x for x in hv if not x["dusuk"]]
e_hv = [x for x in gor if not x["sd_id"] and not x["yok"]]
print(f"\nHAVUZ (görünen): {len(gor)} oyuncu · SD kimliği bağlı olmayan {len(e_hv)} · SD'de kaydı yok (doğrulanmış) {sum(1 for x in gor if x['yok'])}")
print("   lige göre:", collections.Counter(x["lig"] for x in e_hv).most_common(12))
for x in e_hv[:70]:
    print(f"   {x['isim']:30} {x['kulup'][:26]:26} {x['lig'][:22]:22} {x['uyruk'][:14]:14} {x['yas']:3} {x['nihai']}")
for x in gor:
    if x["yok"]:
        print(f"   (SD'de yok) {x['isim']} · {x['uyruk']}")
