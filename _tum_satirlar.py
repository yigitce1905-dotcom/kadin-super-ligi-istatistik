# -*- coding: utf-8 -*-
"""Liste satırı şablonunu tüm oyuncular için üretip HTML bütünlüğünü doğrula."""
import sys, re
sys.stdout.reconfigure(encoding="utf-8")
try:
    import app
except BaseException:
    pass
app = sys.modules.get("app")

b = app.birlesik_scout_yukle()
sd_data = app.birlesik_sd_yukle()
leistung_data = app.birlesik_leistung_yukle()

def _esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

sorunlu = []
for tam_isim, _kd in b.items():
    sd = sd_data.get(tam_isim, {})
    _yas = _kd.get("yas") or sd.get("Age","") or ""
    _kl = _kd.get("kulup","") or ""
    _lg = _kd.get("lig","") or ""
    _sz = _kd.get("sozlesme","") or sd.get("Contract until","") or ""
    _dg = _kd.get("deger","") or ""
    _nh = _kd.get("nihai","")
    _poz = (_kd.get("mevki") or [""])[0]
    satir = (
        "<tr>"
        f"<td><a href='?oyuncu=x'>{_esc(tam_isim)}</a></td>"
        f"<td>{_esc(_poz)}</td>"
        f"<td>{_esc(_kl)}<div>{_esc(_lg)}</div></td>"
        f"<td class='num ws-mono' data-label='Yaş'>{_yas or '—'}</td>"
        f"<td style='color:#fff;'>{_esc(_sz) or '—'}</td>"
        f"<td>{_esc(_dg) or '—'}</td>"
        f"<td><span style='border-color:#fff;'>{_nh}</span></td></tr>"
    )
    # bütünlük: kontrol karakteri, çift-tırnak dengesizliği, ham < kalıntısı
    ham = [c for c in satir if (ord(c) < 32) or ord(c) == 0xFFFD or 0xD800 <= ord(c) <= 0xDFFF]
    if ham:
        sorunlu.append((tam_isim, "kontrol-karakteri", [hex(ord(c)) for c in ham],
                        {k: repr(v)[:40] for k,v in (("yas",_yas),("kl",_kl),("sz",_sz),("dg",_dg),("nh",_nh),("poz",_poz)) if any(c2 in str(v) for c2 in ham)}))
print(f"{len(b)} oyuncudan sorunlu satır: {len(sorunlu)}")
for s in sorunlu[:10]:
    print(" ", s)
