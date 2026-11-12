"""Hudl StatsBomb açık olay verisinden oyuncu × yarışma özeti üretir → sb_ozet.json (küçük dosya; ham veri depoya girmez).

    python sb_indir.py                 # önce ham veri (Masaüstü\\statsbomb_veri, ~3 GB)
    python sb_ozet_uret.py [veri klasörü]

Ölçüler (yarışma başına, ham sayılar; 90 dk başına değerler gösterilirken hesaplanır):
  mac, ilk11, dk · gol, pg (penaltı golü), sut, xg, npxg · asist, kp (şutla biten pas), xa (asist edilen şutların xG toplamı)
  pas, pas_ok, ip (ilerletici pas), cb (ceza sahasına pas) · it (ilerletici top taşıma) · dr, dr_ok (çalım)
  pres, tk (top kazanma), md, md_ok (ikili mücadele: müdahale), ag (araya girme), hv, hv_ok (hava topu), uz (uzaklaştırma), blok
  kaleci: kt (kurtarış), yg (yenilen gol), ks (karşılaşılan isabetli şut), kxg (bu şutların xG toplamı)

İlerletici pas/taşıma (sade tanım): açık oyunda, kendi kalesine yakın %40'lık bölgenin dışından başlayıp topu rakip kale merkezine
en az 10 yarda yaklaştıran tamamlanmış pas/taşıma, ya da ceza sahası dışından ceza sahasına giren. Penaltı atışları (seri) sayılmaz.

LİSANS: StatsBomb Public Data User Agreement — ticari kullanım ve verinin yeniden dağıtımı yasak; yayımlanan her analizde
"StatsBomb" logosuyla kaynak gösterilir. Bu dosya ham veri değil, türetilmiş özettir.
"""
import collections
import json
import math
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
VERI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser("~"), "Desktop", "statsbomb_veri")
CIKTI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sb_ozet.json")
SEZON = {(37, 281): "WSL 2023/24", (131, 281): "Serie A 2023/24", (135, 281): "Frauen-Bundesliga 2023/24", (182, 281): "Liga F 2023/24",
         (49, 107): "NWSL 2023", (53, 315): "Euro 2025", (72, 107): "Dünya Kupası 2023"}
P_BAS = {1: 0.0, 2: 45.0, 3: 90.0, 4: 105.0}
DURAN = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}
BASARI = {"Won", "Success", "Success In Play", "Success Out"}


def dk_coz(s):
    if not s:
        return None
    p = str(s).split(":")
    try:
        return int(p[0]) + int(p[1]) / 60.0 if len(p) == 2 else int(p[0]) * 60 + int(p[1]) + int(p[2]) / 60.0
    except Exception:
        return None


def kaleye(x, y):
    return math.hypot(120.0 - x, 40.0 - y)


def kutuda(x, y):
    return x >= 102.0 and 18.0 <= y <= 62.0


def ilerletici(a, b):
    if not a or not b:
        return False
    if kutuda(b[0], b[1]) and not kutuda(a[0], a[1]):
        return True
    return a[0] >= 48.0 and kaleye(a[0], a[1]) - kaleye(b[0], b[1]) >= 10.0


def main():
    oyuncu = {}          # sb id → {"ad","takma","ulke","k": {yarışma: sayaçlar}}
    t0, n = time.time(), 0
    for (c, s), yad in SEZON.items():
        maclar = json.load(open(os.path.join(VERI, "matches", f"{c}_{s}.json"), encoding="utf-8"))
        for mac in maclar:
            mid = mac["match_id"]
            ey, ky = os.path.join(VERI, "events", f"{mid}.json"), os.path.join(VERI, "lineups", f"{mid}.json")
            if not (os.path.exists(ey) and os.path.exists(ky)):
                continue
            olaylar = json.load(open(ey, encoding="utf-8"))
            kadro = json.load(open(ky, encoding="utf-8"))
            n += 1
            p_son = dict(P_BAS)
            for e in olaylar:
                p = e.get("period", 1)
                if p in P_BAS:
                    p_son[p] = max(p_son[p], e.get("minute", 0) + e.get("second", 0) / 60.0)
            son_periyot = max((e.get("period", 1) for e in olaylar if e.get("period", 1) in P_BAS), default=2)

            def say(pid):
                return oyuncu[pid]["k"].setdefault(yad, collections.Counter())

            for takim in kadro:
                for pl in takim["lineup"]:
                    poz = pl.get("positions") or []
                    if not poz:
                        continue
                    pid = pl["player_id"]
                    o = oyuncu.setdefault(pid, {"ad": pl["player_name"], "takma": pl.get("player_nickname") or "",
                                                "ulke": (pl.get("country") or {}).get("name", ""), "k": {}, "_t": {}, "_p": {}})
                    sy = say(pid)
                    dk = 0.0
                    for z in poz:
                        pf, pt = z.get("from_period") or 1, z.get("to_period") or son_periyot
                        tf, tt = dk_coz(z.get("from")) or 0.0, dk_coz(z.get("to"))
                        sure = 0.0
                        for p in range(pf, min(pt, 4) + 1):
                            bas = tf if p == pf else P_BAS[p]
                            bit = tt if (p == pt and tt is not None) else p_son.get(p, P_BAS[p])
                            sure += max(0.0, bit - bas)
                        dk += sure
                        o["_p"].setdefault(yad, collections.Counter())[z.get("position", "")] += sure
                    sy["mac"] += 1
                    sy["ilk11"] += 1 if (poz[0].get("start_reason") == "Starting XI") else 0
                    sy["dk"] += dk
                    o["_t"].setdefault(yad, collections.Counter())[takim["team_name"]] += dk

            pas_xg = {}                                 # kilit pas kimliği → şutun xG'si
            for e in olaylar:
                if e["type"]["name"] == "Shot" and e.get("period", 1) <= 4:
                    kid = e["shot"].get("key_pass_id")
                    if kid:
                        pas_xg[kid] = e["shot"].get("statsbomb_xg", 0.0)
            for e in olaylar:
                pid = (e.get("player") or {}).get("id")
                if pid not in oyuncu or e.get("period", 1) > 4:
                    continue
                sy, tur = say(pid), e["type"]["name"]
                if tur == "Shot":
                    sh = e["shot"]
                    pen = sh.get("type", {}).get("name") == "Penalty"
                    xg = sh.get("statsbomb_xg", 0.0)
                    sy["sut"] += 1
                    sy["xg"] += xg
                    if not pen:
                        sy["npxg"] += xg
                    if sh.get("outcome", {}).get("name") == "Goal":
                        sy["gol"] += 1
                        sy["pg"] += pen
                    if sh.get("aerial_won"):
                        sy["hv"] += 1; sy["hv_ok"] += 1
                elif tur == "Pass":
                    ps = e["pass"]
                    tamam = "outcome" not in ps
                    duran = ps.get("type", {}).get("name") in DURAN
                    sy["pas"] += 1
                    sy["pas_ok"] += tamam
                    if ps.get("goal_assist"):
                        sy["asist"] += 1
                    if ps.get("goal_assist") or ps.get("shot_assist"):
                        sy["kp"] += 1
                        sy["xa"] += pas_xg.get(e["id"], 0.0)
                    if tamam and not duran:
                        a, b = e.get("location"), ps.get("end_location")
                        if ilerletici(a, b):
                            sy["ip"] += 1
                        if a and b and kutuda(b[0], b[1]) and not kutuda(a[0], a[1]):
                            sy["cb"] += 1
                    if ps.get("aerial_won"):
                        sy["hv"] += 1; sy["hv_ok"] += 1
                elif tur == "Carry":
                    if ilerletici(e.get("location"), e["carry"].get("end_location")):
                        sy["it"] += 1
                elif tur == "Dribble":
                    sy["dr"] += 1
                    sy["dr_ok"] += e["dribble"].get("outcome", {}).get("name") == "Complete"
                elif tur == "Pressure":
                    sy["pres"] += 1
                elif tur == "Ball Recovery":
                    if not e.get("ball_recovery", {}).get("recovery_failure"):
                        sy["tk"] += 1
                elif tur == "Duel":
                    d = e.get("duel", {})
                    if d.get("type", {}).get("name") == "Tackle":
                        sy["md"] += 1
                        sy["md_ok"] += d.get("outcome", {}).get("name") in BASARI
                    elif d.get("type", {}).get("name") == "Aerial Lost":
                        sy["hv"] += 1
                elif tur == "Interception":
                    if e.get("interception", {}).get("outcome", {}).get("name") in BASARI:
                        sy["ag"] += 1
                elif tur == "Clearance":
                    sy["uz"] += 1
                    if e.get("clearance", {}).get("aerial_won"):
                        sy["hv"] += 1; sy["hv_ok"] += 1
                elif tur == "Block":
                    sy["blok"] += 1
                elif tur == "Miscontrol":
                    if e.get("miscontrol", {}).get("aerial_won"):
                        sy["hv"] += 1; sy["hv_ok"] += 1
                elif tur == "Goal Keeper":
                    g = e.get("goalkeeper", {})
                    gt = g.get("type", {}).get("name", "")
                    if gt in ("Shot Saved", "Penalty Saved", "Shot Saved to Post", "Saved to Post", "Shot Saved Off Target"):
                        sy["kt"] += 1; sy["ks"] += 1
                    elif gt in ("Goal Conceded", "Penalty Conceded"):
                        sy["yg"] += 1; sy["ks"] += 1
            # kalecinin karşılaştığı isabetli şutların xG'si (kurtarılan + gol)
            kaleci = {}
            for takim in kadro:
                for pl in takim["lineup"]:
                    for z in pl.get("positions") or []:
                        if z.get("position") == "Goalkeeper":
                            kaleci.setdefault(takim["team_name"], []).append((pl["player_id"], z))
            for e in olaylar:
                if e["type"]["name"] == "Shot" and e.get("period", 1) <= 4 and e["shot"].get("outcome", {}).get("name") in ("Goal", "Saved", "Saved to Post"):
                    t = e.get("minute", 0) + e.get("second", 0) / 60.0
                    for takim_ad, liste in kaleci.items():
                        if takim_ad == e["team"]["name"]:
                            continue
                        for pid, z in liste:
                            tf, tt = dk_coz(z.get("from")) or 0.0, dk_coz(z.get("to"))
                            if (z.get("from_period") or 1) <= e.get("period", 1) <= (z.get("to_period") or 4) and tf <= t + 0.01 and (tt is None or t <= tt + 0.01):
                                say(pid)["kxg"] += e["shot"].get("statsbomb_xg", 0.0)
                                break
            if n % 100 == 0:
                print(f"  {n} maç işlendi · {time.time() - t0:.0f} sn", flush=True)

    cikti = {"kaynak": "Hudl StatsBomb açık verisi (github.com/statsbomb/open-data)",
             "not": "Türetilmiş özet. Yayımlarken StatsBomb logosuyla kaynak göster; ticari kullanım ve yeniden dağıtım lisansça yasak.",
             "yarismalar": list(SEZON.values()), "oyuncular": {}}
    for pid, o in oyuncu.items():
        kayit = []
        for yad in SEZON.values():
            sy = o["k"].get(yad)
            if not sy or sy["dk"] < 1:
                continue
            d = {k: (round(v, 2) if isinstance(v, float) else int(v)) for k, v in sy.items() if v}
            d["dk"] = int(round(sy["dk"]))
            d["y"] = yad
            d["takim"] = o["_t"][yad].most_common(1)[0][0]
            d["poz"] = o["_p"][yad].most_common(1)[0][0]
            kayit.append(d)
        if kayit:
            cikti["oyuncular"][str(pid)] = {"ad": o["ad"], "takma": o["takma"], "ulke": o["ulke"], "k": kayit}
    json.dump(cikti, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"\n{n} maç · {len(cikti['oyuncular'])} oyuncu → {CIKTI} ({os.path.getsize(CIKTI) // 1024} KB) · {time.time() - t0:.0f} sn")


if __name__ == "__main__":
    main()
