# -*- coding: utf-8 -*-
"""Tanıtım görseli: "Transfer döneminde bonservissiz alınabilecek oyuncular" (Sözleşme Takibi 2027 verisi).

Instagram (1080×1350) ve LinkedIn için TR + EN PNG üretir. Veri sitenin KENDİ işlevlerinden gelir
(_kulup_adaylari, _musait_ozet, _transfer_donemi — AppTest kancasıyla), yani görsel sitedeki sayfayla birebir aynıdır.
İsimler GİZLİ (sitedeki misafir görünümü gibi): mevki, yaş, uyruk, lig, değer, sözleşme ve scout notu görünür;
isimler sitede üyelere açık. Görseli YALNIZ üretir — paylaşmak elle yapılır (toplu gönderim yok).

    python tanitim_bonservissiz.py [ULKE=TUR] [ÇIKTI_KLASÖRÜ]

Çıktı: <klasör>/bonservissiz_<ülke>_<tarih>_{tr,en}.png  (varsayılan klasör: Masaüstü\\tanitim)
Linkler ?ref=ig taşır → Kokpit › Ziyaretler › Kaynak'ta Instagram'dan geleni görürsün."""
import html
import json
import os
import pathlib
import subprocess
import sys
import tempfile

KOK = pathlib.Path(__file__).resolve().parent
ULKE = (sys.argv[1] if len(sys.argv) > 1 else "TUR").upper()
CIKTI = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path.home() / "Desktop" / "tanitim"
GORUNEN = 7            # görselde gösterilecek aday sayısı


def veri_cek(dil: str = "TR") -> dict:
    """AppTest ile app.py'yi çalıştırıp Sözleşme Takibi'nin aday listesini ve özetini JSON'a döker."""
    from streamlit.testing.v1 import AppTest
    cikti = pathlib.Path(tempfile.mkdtemp()) / "veri.json"
    src = (KOK / "app.py").read_text(encoding="utf-8")
    kanca = '''
def _tanitim_dok():
    import json as _j
    from datetime import datetime as _dt, timedelta as _td
    gun = (_dt.utcnow() + _td(hours=3)).date().isoformat()
    kayit = dict(kulup_ihtiyac_yukle().get("sozlesme-2027") or {})
    kayit["ulke"] = %r
    gruplar = _kulup_adaylari(_j.dumps(kayit, sort_keys=True, ensure_ascii=False), gun)
    gruplar = [[{**a, "uyruk_g": ulke_goster(_uyruk_goster(str(a.get("uyruk") or ""))), "lig_g": _lig_goster(str(a.get("lig") or ""))}
                for a in g] for g in gruplar]
    _j.dump({"gun": gun, "ihtiyaclar": kayit.get("ihtiyaclar", []), "gruplar": gruplar,
             "ozet": _musait_ozet(gun, %r), "donem": _transfer_donemi(%r, gun),
             "takvim": [x for x in takvim_yukle().get("ulkeler", []) if x.get("fifa") == %r]},
            open(%r, "w", encoding="utf-8"), ensure_ascii=False, default=str)
_tanitim_dok()

def render_kokpit():''' % (ULKE, ULKE, ULKE, ULKE, str(cikti))
    assert src.count("\ndef render_kokpit():") == 1
    kopya = KOK / "_tanitim_app.py"
    kopya.write_text(src.replace("\ndef render_kokpit():", kanca, 1), encoding="utf-8")
    try:
        at = AppTest.from_file(str(kopya), default_timeout=600)
        at.query_params["dil"] = dil
        for k, v in {"kulup_giris": True, "kulup_rol": "admin", "kulup_kullanici": "admin", "girildi": True, "sayfa": "kokpit", "dil": dil}.items():
            at.session_state[k] = v
        at.run()
        if at.exception or not cikti.exists():
            raise SystemExit("veri alınamadı: " + str([str(e.value)[:300] for e in at.exception]))
    finally:
        kopya.unlink(missing_ok=True)
    return json.loads(cikti.read_text(encoding="utf-8"))


AY_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AY_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def tarih(iso: str, dil: str) -> str:
    try:
        y, a, g = (int(x) for x in str(iso)[:10].split("-"))
    except Exception:
        return str(iso or "")
    return f"{g} {(AY_TR if dil == 'tr' else AY_EN)[a - 1]} {y}"


MEVKI_EN = {"Kaleci": "Goalkeeper", "Stoper": "Centre-back", "Sol bek": "Left-back", "Sağ bek": "Right-back", "Ön libero": "Defensive mid",
            "Merkez orta saha": "Central mid", "Ofansif orta saha": "Attacking mid", "Sol kanat": "Left wing", "Sağ kanat": "Right wing",
            "Santrfor": "Striker", "Santrafor": "Striker"}
NOT_RENK = {"A": "#3b82f6", "B": "#22c55e", "C": "#eab308", "D": "#f97316", "E": "#ef4444", "F": "#6b7280"}
ULKE_EN_KUCUK = {}


def kart_html(v: dict, dil: str) -> str:
    E = dil == "en"
    oz, dn = v.get("ozet") or {}, v.get("donem") or {}
    # mevki başına en iyi aday (yalnız sıradaki dönemde alınabilir: serbest / donem), sonra genel sıralama
    secim = []
    for bas, grup in zip(v.get("ihtiyaclar") or [], v.get("gruplar") or []):
        aday = next((a for a in grup if a.get("durum") in ("serbest", "donem")), None)
        if aday:
            secim.append(((bas.get("baslik_en") if E else bas.get("baslik")) if isinstance(bas, dict) else str(bas), aday))
    secim.sort(key=lambda x: ("ABCDEF".find((x[1].get("nihai") or "F")[0]), "ABCDEF".find((x[1].get("nihai") or "FF")[1:2] or "F")))
    secim = secim[:GORUNEN]
    acilis = tarih(dn.get("bas", ""), dil)
    kapanis = tarih(dn.get("bit", ""), dil)
    gun = dn.get("gun")
    tk = (v.get("takvim") or [{}])[0]
    ulke_ad = (tk.get("ulke_en") if E else tk.get("ulke")) or ULKE
    bayrak = tk.get("bayrak", "")
    serbest = oz.get("serbest", 0)
    donem = oz.get("donem", 0)
    sezon = oz.get("sezon", 0)

    def satir(baslik, a):
        n = (a.get("nihai") or "—")
        r = NOT_RENK.get(n[:1], "#6b7280")
        mevki = baslik
        if a.get("durum") == "serbest":
            soz = "Free agent" if E else "Serbest oyuncu"
        else:
            soz = (f"Contract to {a.get('bitis')}" if E else f"Sözleşme {a.get('bitis')}")
        uyruk = html.escape(str(a.get("uyruk_g") or a.get("uyruk") or "—"))
        lig = html.escape(str(a.get("lig_g") or ""))
        yas = a.get("yas") or "—"
        deger = html.escape(str(a.get("deger") or "")) or "—"
        return (f"<div class='satir'><div class='mevki'>{html.escape(mevki)}</div>"
                f"<div class='bilgi'><div class='gizli'></div><div class='alt'>{yas} {'y/o' if E else 'yaş'} · {uyruk}{(' · ' + lig) if lig else ''}</div></div>"
                f"<div class='soz'><div class='deger'>{deger}</div><div class='durum'>{html.escape(soz)}</div></div>"
                f"<div class='not' style='border-color:{r};color:{r};'>{html.escape(n)}</div></div>")

    if gun is not None and not dn.get("acik"):
        # Türkçe ek tarihe göre değişir ('2027'de', '2026'da'); ekten kaçınmak için iki nokta
        ust = (f"{bayrak} {ulke_ad}: transfer window opens {acilis} — in {gun} days" if E
               else f"{bayrak} {ulke_ad} transfer dönemi açılıyor: {acilis} · {gun} gün kaldı")
    elif dn.get("acik"):
        ust = (f"{bayrak} {ulke_ad}: the transfer window is OPEN until {kapanis}" if E
               else f"{bayrak} {ulke_ad} transfer dönemi AÇIK · son gün {kapanis}")
    else:
        ust = f"{bayrak} {ulke_ad}"
    baslik = ("Who can you sign <em>for free</em> in the next window?" if E
              else "Sıradaki dönemde <em>bonservissiz</em> kimi alabilirsin?")
    # Görseldeki link tıklanamaz (Instagram): sade adres. ?ref=ig'li tam link gönderi açıklamasına / bio'ya konur.
    link = "womenfootballscouting.com"
    # lang: CSS text-transform:uppercase Türkçede i→İ yapsın ("TAKİBİ", "İSİMLER"; lang yoksa "TAKIBI" çıkıyordu)
    return f"""<!doctype html><html lang="{'en' if E else 'tr'}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Sora:wght@700;800&display=swap">
<style>
@font-face{{font-family:'Twemoji Country Flags';src:url('https://cdn.jsdelivr.net/npm/country-flag-emoji-polyfill@0.1.8/dist/TwemojiCountryFlags.woff2') format('woff2');
 unicode-range:U+1F1E6-1F1FF,U+1F3F4,U+E0062-E0063,U+E0065,U+E0067,U+E006C,U+E006E,U+E0073-E0074,U+E0077,U+E007F;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;background:#0b0b14;font-family:'Twemoji Country Flags','Inter',sans-serif;color:#e5e7eb;overflow:hidden}}
.kap{{position:relative;width:1080px;height:1350px;padding:64px 64px 56px;
 background:radial-gradient(1200px 600px at 100% 0%,rgba(124,58,237,.30),transparent 60%),radial-gradient(900px 500px at 0% 100%,rgba(219,39,119,.22),transparent 60%),#0b0b14}}
.marka{{font-family:Sora,sans-serif;font-weight:800;font-size:22px;letter-spacing:.18em;color:#c4b5fd;text-transform:uppercase}}
.ust{{margin-top:18px;font-size:27px;font-weight:700;color:#e9d5ff}}
h1{{margin-top:14px;font-family:Sora,sans-serif;font-weight:800;font-size:62px;line-height:1.08;color:#fff}}
h1 em{{font-style:normal;background:linear-gradient(90deg,#a78bfa,#f472b6);-webkit-background-clip:text;color:transparent}}
.kutular{{display:flex;gap:16px;margin-top:30px}}
.kutu{{flex:1;background:rgba(17,17,30,.85);border:1px solid #3b2d6e;border-radius:18px;padding:18px 20px}}
.kutu b{{display:block;font-family:Sora,sans-serif;font-size:50px;font-weight:800}}
.kutu span{{font-size:19px;color:#a1a1aa;line-height:1.3;display:block;margin-top:4px}}
.liste{{margin-top:30px;background:rgba(13,13,22,.92);border:1px solid #3b2d6e;border-radius:20px;padding:8px 22px}}
.lbas{{font-size:17px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#8b8ba7;padding:14px 0 6px}}
.satir{{display:flex;align-items:center;gap:16px;padding:13px 0;border-top:1px solid #241d3d}}
.mevki{{width:190px;font-weight:800;font-size:21px;color:#e9d5ff}}
.bilgi{{flex:1;min-width:0}}
.gizli{{height:15px;width:62%;border-radius:8px;background:linear-gradient(90deg,#4c3a8a,#2a2150)}}
.alt{{margin-top:8px;font-size:18px;color:#a1a1aa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.soz{{width:230px;text-align:right}}
.deger{{font-family:Sora,sans-serif;font-weight:800;font-size:22px;color:#fff}}
.durum{{font-size:17px;font-weight:700;color:#22c55e;margin-top:3px}}
.not{{width:58px;height:58px;border-radius:50%;border:3px solid;display:flex;align-items:center;justify-content:center;font-family:Sora,sans-serif;font-weight:800;font-size:19px}}
.alt-bilgi{{position:absolute;left:64px;right:64px;bottom:52px}}
.cta{{display:flex;align-items:center;justify-content:space-between;gap:20px;background:linear-gradient(135deg,#7c3aed,#db2777);border-radius:18px;padding:22px 26px}}
.cta b{{font-size:25px;color:#fff}}
.cta span{{font-size:21px;color:#fde7f3;font-weight:700;white-space:nowrap}}
.dip{{margin-top:12px;font-size:15px;color:#71717a}}
</style></head><body><div class="kap">
<div class="marka"><span lang="en">Women's Football Scouting</span> · {'Contract Watch 2027' if E else 'Sözleşme Takibi 2027'}</div>
<div class="ust">{html.escape(ust)}</div>
<h1>{baslik}</h1>
<div class="kutular">
 <div class="kutu"><b style="color:#22c55e">{serbest}</b><span>{'free agents: sign now' if E else 'serbest oyuncu: hemen'}</span></div>
 <div class="kutu"><b style="color:#22c55e">{donem}</b><span>{'contracts end within the window' if E else 'sözleşmesi dönem içinde bitiyor'}</span></div>
 <div class="kutu"><b style="color:#f59e0b">{sezon}</b><span>{'free at season end' if E else 'sezon sonunda bonservissiz'}</span></div>
</div>
<div class="liste"><div class="lbas">{'Highest-graded option per position · names for members' if E else 'Mevki başına en yüksek notlu aday · isimler üyelere açık'}</div>
{''.join(satir(b, a) for b, a in secim)}
</div>
<div class="alt-bilgi">
 <div class="cta"><b>{'Names and the full list →' if E else 'İsimler ve tam liste →'}</b><span>{html.escape(link)} · {'Contract Watch 2027' if E else 'Sözleşme Takibi 2027'}</span></div>
 <div class="dip">{'Scout grades AA–FF · contract dates from SoccerDonna and club sources, verify before acting' if E else 'Scout notu AA–FF · sözleşme tarihleri SoccerDonna ve kulüp kaynaklarından, işlem öncesi doğrulayın'} · {tarih(v.get('gun'), dil)}</div>
</div></div></body></html>"""


def cek(html_yol: pathlib.Path, png_yol: pathlib.Path):
    edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p))
    subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1350",
                    "--virtual-time-budget=8000", f"--screenshot={png_yol}", html_yol.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    CIKTI.mkdir(parents=True, exist_ok=True)
    for dil in ("tr", "en"):
        v = veri_cek(dil.upper())
        h = CIKTI / f"bonservissiz_{ULKE.lower()}_{v['gun']}_{dil}.html"
        p = h.with_suffix(".png")
        h.write_text(kart_html(v, dil), encoding="utf-8")
        cek(h, p)
        print("hazır:", p)
