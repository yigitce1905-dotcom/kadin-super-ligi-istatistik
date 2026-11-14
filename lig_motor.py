"""Lig motoru: SoccerDonna maç raporlarından (sd_dizilis_<KOD>_*.json) oyuncu / takım / puan özeti.

Streamlit'e bağlı DEĞİL. İki yerden kullanılır — hesap tek yerde dursun diye (13 Kasım 2026):
  · site: app.py → lig_tam_yukle(kod) (lig kipi sekmeleri)
  · çevrimdışı: lig_capraz_uret.py (ligler arası özet → lig_capraz.json)
Lig eklemek: LIG_SAYFA'ya satır + sd_dizilis_cek.py LIGLER + sd_form_tazele.py LIGLER.
"""
import pathlib
import re as _r
import unicodedata as _ud
from collections import Counter as _C

KOK = pathlib.Path(__file__).parent

LIG_SAYFA = {
    # Sıra: Opta'nın kadın ligleri güç sıralaması, ilk 20 (Yiğit'in ilettiği liste, 13 Kasım 2026). Brezilya A1 (8.) ve
    # Kolombiya (15.) SoccerDonna'da yok. Listede olmayanlar sona, UEFA kupaları en sona.
    "NWSL": ("🇺🇸", "NWSL", "2025_26"),                                                                                # 1
    "ENG1": ("\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F", "Women's Super League", "2026_27"),   # 2
    "BL1": ("🇩🇪", "Frauen-Bundesliga", "2026_27"),                                                                    # 3
    "ESP1": ("🇪🇸", "Liga F", "2026_27"),                                                                              # 4
    "SWE1": ("🇸🇪", "Damallsvenskan", "2025_26"),                                                                      # 5
    "IT1": ("🇮🇹", "Serie A Women", "2026_27"),                                                                        # 6
    "DAN1": ("🇫🇷", "Première Ligue", "2026_27"),                                                                      # 7
    "ENG2": ("\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F", "Women's Super League 2", "2026_27"), # 9
    "MXAP": ("🇲🇽", "Liga MX Femenil (Apertura)", "2026_27"),                                                          # 10
    "LNF": ("🇵🇹", "Liga BPI", "2026_27"),                                                                             # 11
    "Ered": ("🇳🇱", "Vrouwen Eredivisie", "2026_27"),                                                                  # 12
    "CA1": ("🇨🇦", "Northern Super League", "2025_26"),                                                                # 13
    "3FL": ("🇩🇰", "A-Liga", "2026_27"),                                                                               # 14
    "JAPW": ("🇯🇵", "WE League", "2026_27"),                                                                           # 16
    "WL": ("🇦🇺", "A-League Women", "2026_27"),                                                                        # 17
    "USGS": ("🇺🇸", "USL Super League", "2025_26"),                                                                    # 18
    "NOR1": ("🇳🇴", "Toppserien", "2025_26"),                                                                          # 19
    "KOR1": ("🇰🇷", "WK League", "2025_26"),                                                                           # 20
    "ISL1": ("🇮🇸", "Besta deild kvenna", "2025_26"),
    "Nais": ("🇫🇮", "Kansallinen Liiga", "2025_26"),
    "UNG1": ("🇭🇺", "Női NB I", "2026_27"),
    "CL": ("🇪🇺", "UEFA Şampiyonlar Ligi", "2026_27"),
    "CLQ": ("🇪🇺", "Şampiyonlar Ligi ön eleme", "2026_27"),
    "EC": ("🇪🇺", "UEFA Avrupa Kupası", "2026_27"),
}
LIG_AD_EN = {"CL": "UEFA Champions League", "CLQ": "Champions League qualifying", "EC": "UEFA Europa Cup"}
LIG_KUPA = {"CL", "CLQ", "EC"}
# Opta'nın kadın ligleri güç sıralaması (ilk 20; Yiğit'in ilettiği liste, 13 Kasım 2026). 8 = Brezilya A1 ve 15 = Kolombiya
# SoccerDonna'da yok. Listede olmayan ligin sırası yok (None).
OPTA_SIRA = {"NWSL": 1, "ENG1": 2, "BL1": 3, "ESP1": 4, "SWE1": 5, "IT1": 6, "DAN1": 7, "ENG2": 9, "MXAP": 10, "LNF": 11, "Ered": 12,
             "CA1": 13, "3FL": 14, "JAPW": 16, "WL": 17, "USGS": 18, "NOR1": 19, "KOR1": 20}


# Lig kodu → ülkenin FIFA kodu (takvim_2026_27.json ile eşleşir): lig sayfasında o ülkenin transfer ve tescil dönemi gösterilir.
LIG_ULKE = {"NWSL": "USA", "ENG1": "ENG", "BL1": "GER", "ESP1": "ESP", "SWE1": "SWE", "IT1": "ITA", "DAN1": "FRA", "ENG2": "ENG", "MXAP": "MEX",
            "LNF": "POR", "Ered": "NED", "CA1": "CAN", "3FL": "DEN", "JAPW": "JPN", "WL": "AUS", "USGS": "USA", "NOR1": "NOR", "KOR1": "KOR",
            "ISL1": "ISL", "Nais": "FIN", "UNG1": "HUN", "TUR1": "TUR"}


def lig_dosya(kod: str) -> pathlib.Path:
    return KOK / f"sd_dizilis_{kod}_{LIG_SAYFA[kod][2]}.json"


def hesapla(veri: dict, kupa: bool = False) -> dict:
    """Bir ligin maç dosyasından özet. {'raporsuz','oyuncu': {sd_id: kayıt},'takim': {ad: kayıt},'puan': [...],'mac_sayisi','son_mac'}
    Oyuncu kaydı: ad, takim (en son), takimlar, yas, grup (K/D/O/F), mac, ilk11, yedek, dk, gol, gk (kafa), gp (penaltı),
    asist, sari, kirmizi, yg (kalecinin sahadayken yediği gol), gy (gol yemeden tam maç), log: [maç satırları].
    Dakika yaklaşık (maç 90 dk sayılır). Puan durumu maç sonuçlarından HESAPLANIR (federasyon cezaları yansımaz)."""
    def _dk(s):
        m = _r.match(r"(\d+)", str(s or ""))
        return min(int(m.group(1)), 90) if m else None

    def _trh(s):
        try:
            g, a, y = str(s).split(".")
            return f"{y}-{a}-{g}"
        except Exception:
            return ""

    def _grup(mv):
        p = (mv or "").lower()
        return "K" if "goalkeeper" in p else "D" if "defen" in p else "O" if "midfield" in p else "F" if p else ""

    oyuncu, takim = {}, {}
    maclar = sorted((m for m in veri.get("maclar", []) if _r.fullmatch(r"\d+:\d+", str(m.get("skor") or ""))),
                    key=lambda m: _trh(m.get("tarih")))
    for m in maclar:
        eg, dg = (int(x) for x in m["skor"].split(":"))
        tarih = _trh(m.get("tarih"))
        goller = [(g.get("taraf"), _dk(g.get("dk")) or 0) for g in m.get("goller", [])]
        for taraf, rakip_taraf, a, y in (("ev", "dep", eg, dg), ("dep", "ev", dg, eg)):
            tad = m.get(taraf, "")
            tk = takim.setdefault(tad, {"ad": tad, "o": 0, "g": 0, "b": 0, "m": 0, "a": 0, "y": 0, "sema": _C(), "hoca": _C(), "mac": []})
            tk["o"] += 1; tk["a"] += a; tk["y"] += y
            tk["g" if a > y else "b" if a == y else "m"] += 1
            dz = (m.get("dizilis") or {}).get(taraf) or {}
            if dz.get("sema"):
                tk["sema"][str(dz["sema"]).split(" ")[0]] += 1
            if dz.get("teknik"):
                tk["hoca"][dz["teknik"]] += 1
            tk["mac"].append({"i": m.get("id"), "t": tarih, "h": m.get("hafta") or 0, "rk": m.get(rakip_taraf, ""), "ev": taraf == "ev", "sk": f"{a}:{y}"})
            giren = {d["giren_sd_id"]: _dk(d["dk"]) for d in m.get("degisiklikler", []) if d["taraf"] == taraf and d.get("giren_sd_id")}
            cikan = {d["cikan_sd_id"]: _dk(d["dk"]) for d in m.get("degisiklikler", []) if d["taraf"] == taraf and d.get("cikan_sd_id")}
            yenen = [dk for tr_, dk in goller if tr_ == rakip_taraf]          # bu takımın yediği gollerin dakikaları
            for liste, ilk in (((m.get("ilk11") or {}).get(taraf, []), True), ((m.get("yedekler") or {}).get(taraf, []), False)):
                for p in liste:
                    sid = p.get("sd_id")
                    if not sid:
                        continue
                    if ilk:
                        durum, bas, bit = "S", 0, (cikan.get(sid) or 90)
                    elif giren.get(sid) is not None:
                        durum, bas, bit = "Y", giren[sid], (cikan.get(sid) or 90)
                    else:
                        durum, bas, bit = "B", 0, 0
                    dk = max(1, bit - bas) if durum == "Y" else (bit if durum == "S" else 0)
                    o = oyuncu.setdefault(str(sid), {"sid": str(sid), "ad": p.get("ad", ""), "takim": tad, "takimlar": [], "yas": None, "_mv": _C(),
                                                     "mac": 0, "ilk11": 0, "yedek": 0, "dk": 0, "gol": 0, "gk": 0, "gp": 0, "asist": 0,
                                                     "sari": 0, "kirmizi": 0, "yg": 0, "gy": 0, "log": []})
                    o["takim"] = tad
                    if tad not in o["takimlar"]:
                        o["takimlar"].append(tad)
                    # SoccerDonna maç raporlarında olanaksız yaşlar var (972, 1, 56 — 14 Kasım 2026 denetimi): 14-50 dışı yok sayılır
                    try:
                        _y = int(str(p.get("yas") or "").strip() or 0)
                    except ValueError:
                        _y = 0
                    if 14 <= _y <= 50:
                        o["yas"] = _y
                    if p.get("mevki"):
                        o["_mv"][_grup(p["mevki"])] += 1
                    satir = {"i": m.get("id"), "t": tarih, "h": m.get("hafta") or 0, "tk": tad, "rk": m.get(rakip_taraf, ""), "ev": taraf == "ev",
                             "sk": f"{a}:{y}", "d": durum, "dk": dk, "g": 0, "a": 0, "s": 0, "k": 0, "yg": 0, "_ar": (bas, bit)}
                    if durum in ("S", "Y"):
                        o["mac"] += 1
                        o["ilk11"] += durum == "S"
                        o["yedek"] += durum == "Y"
                        o["dk"] += dk
                        satir["yg"] = sum(1 for g in yenen if bas <= g <= (bit if bit < 90 else 200))
                    o["log"].append(satir)
        ic = {}
        for o in oyuncu.values():
            if o["log"] and o["log"][-1]["i"] == m.get("id"):
                ic[int(o["sid"])] = (o, o["log"][-1])
        for g in m.get("goller", []):
            tur = (g.get("tur") or "").lower()
            if g.get("sd_id") in ic and "own goal" not in tur:
                o, s = ic[g["sd_id"]]
                o["gol"] += 1; s["g"] += 1
                o["gk"] += "header" in tur
                o["gp"] += "penalty" in tur
            if g.get("asist_sd_id") in ic:
                o, s = ic[g["asist_sd_id"]]
                o["asist"] += 1; s["a"] += 1
        for k in m.get("kartlar", []):
            if k.get("sd_id") in ic:
                o, s = ic[k["sd_id"]]
                kr = "red" in (k.get("kart") or "").lower()
                o["kirmizi" if kr else "sari"] += 1; s["k" if kr else "s"] += 1
    # Raporu olmayan ama sonucu bilinen maçlar (hafta sayfasında skor var, maç raporu açılmamış): oyuncu istatistiğine
    # GİREMEZ ama puan durumuna ve takımın maç listesine girer. 13 Kasım 2026: Finlandiya'da 80 maçın 36'sının, İsveç'te
    # 16'sının raporu yoktu; tablo yalnız raporlu maçlardan hesaplanınca yanlış çıkıyordu.
    import unicodedata as _ud

    def _sd(ad):
        return _r.sub(r"[^a-z0-9]", "", _ud.normalize("NFKD", str(ad).replace("ı", "i")).encode("ascii", "ignore").decode().lower())
    ad_harita = {_sd(a): a for a in takim}
    ad_kimlik = {}                      # SoccerDonna takım kimliği → maç raporlarındaki ad (raporsuz maçı doğru takıma bağlar)
    for m in maclar:
        for tf in ("ev", "dep"):
            if m.get(tf + "_id"):
                ad_kimlik[m[tf + "_id"]] = m.get(tf, "")

    def _ad_bul(ad):
        """Hafta sayfasındaki kısa ad → maç raporlarındaki takım adı ('HJK' → 'HJK Helsinki'); tek aday varsa eşler."""
        n = _sd(ad)
        if n in ad_harita:
            return ad_harita[n]
        aday = [a for k, a in ad_harita.items() if n and (k.startswith(n) or n.startswith(k) or n in k)]
        return aday[0] if len(aday) == 1 else (ad or "")
    rs_say = 0
    for x in veri.get("raporsuz", []):
        sk = _r.fullmatch(r"(\d+):(\d+)", str(x.get("skor") or ""))
        if not sk:
            continue
        eg, dg = int(sk.group(1)), int(sk.group(2))
        ev = ad_kimlik.get(x.get("ev_id")) or _ad_bul(x.get("ev"))
        dep = ad_kimlik.get(x.get("dep_id")) or _ad_bul(x.get("dep"))
        rs_say += 1
        for tad, rk, a, y, evde in ((ev, dep, eg, dg, True), (dep, ev, dg, eg, False)):
            tk = takim.setdefault(tad, {"ad": tad, "o": 0, "g": 0, "b": 0, "m": 0, "a": 0, "y": 0, "sema": _C(), "hoca": _C(), "mac": []})
            tk["o"] += 1; tk["a"] += a; tk["y"] += y
            tk["g" if a > y else "b" if a == y else "m"] += 1
            tk["mac"].append({"i": None, "t": "", "h": x.get("hafta") or 0, "rk": rk, "ev": evde, "sk": f"{a}:{y}", "rs": True})
    for tk in takim.values():
        tk["rapor"] = sum(1 for x in tk["mac"] if x.get("i"))            # raporu olan maç sayısı (ilk 11 oranının paydası)
        if rs_say and not (kupa):
            tk["mac"].sort(key=lambda x: (x["h"], x["t"]))
    for o in oyuncu.values():
        o["grup"] = o["_mv"].most_common(1)[0][0] if o["_mv"] else ""
        del o["_mv"]
        if o["grup"] == "K":
            for s in o["log"]:
                if s["d"] in ("S", "Y"):
                    o["yg"] += s["yg"]
                    o["gy"] += (s["d"] == "S" and s["dk"] >= 90 and s["yg"] == 0)
        for s in o["log"]:
            s.pop("_ar", None)
    tablo = sorted(takim.values(), key=lambda p: (-(3 * p["g"] + p["b"]), -(p["a"] - p["y"]), -p["a"], p["ad"]))
    for i, tk in enumerate(tablo, 1):
        tk["sira"] = i
    return {"raporsuz": rs_say, "oyuncu": oyuncu, "takim": takim, "puan": tablo,
            "mac_sayisi": len(maclar), "son_mac": (_trh(maclar[-1].get("tarih")) if maclar else "")}
