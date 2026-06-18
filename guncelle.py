"""
TEK KOMUT GÜNCELLEME — Sco 🌍 sekmesini güncelledikten sonra çalıştır.

Sıra:
  1) fetch_scout_kadro.py        Sco 🌍 → scout_kadro_raporlar.json (roster + rapor)
  2) scrape_scouting_yeni.py     yeni oyuncuların SoccerDonna profilleri
  3) scrape_leistungsdaten.py --eksik   yeni oyuncuların kariyer verileri
  4) fetch_scout_kadro.py        (tekrar) yeni SD profillerinden yaş backfill
  5) AppTest (TR+EN)             scouting sayfası crash kontrolü
  6) git commit + push           (AppTest geçerse)

Kullanım:
  python guncelle.py              # tam akış (scrape + test + commit + push)
  python guncelle.py --no-push    # commit'le ama push etme
  python guncelle.py --no-scrape  # sadece sheet'i yeniden parse et + test + commit
                                  # (SD/kariyer çekme adımlarını atlar — hızlı)
"""
import subprocess, sys, os, json
from datetime import date
from pathlib import Path

KOK = Path(__file__).parent
PY  = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

VERI_DOSYALARI = [
    "scout_kadro_raporlar.json",
    "scouting_sd_profiller.json",
    "scouting_leistungsdaten.json",
    "app.py", "fetch_scout_kadro.py", "scrape_scouting_yeni.py",
]


def kosu(adlar, baslik):
    print(f"\n{'='*64}\n▶ {baslik}\n{'='*64}")
    r = subprocess.run([PY, *adlar], cwd=KOK, env=ENV)
    if r.returncode != 0:
        print(f"\n✖ HATA: {' '.join(adlar)} (kod {r.returncode}) — akış durduruldu.")
        sys.exit(r.returncode)


def apptest_gecer() -> bool:
    print(f"\n{'='*64}\n▶ AppTest (TR + EN) — scouting crash kontrolü\n{'='*64}")
    kod = (
        "from streamlit.testing.v1 import AppTest\n"
        "ok=True\n"
        "for dil in ['TR','EN']:\n"
        "    at=AppTest.from_file('app.py',default_timeout=120)\n"
        "    at.session_state['dil']=dil; at.session_state['girildi']=True\n"
        "    at.session_state['kulup_giris']=True\n"
        "    at.session_state['kulup_kullanici']='admin'; at.session_state['kulup_rol']='admin'\n"
        "    at.session_state['sayfa']='scouting'\n"
        "    at.run()\n"
        "    if at.exception:\n"
        "        ok=False\n"
        "        print(f'[{dil}] EXCEPTION:')\n"
        "        [print('   ',repr(e.value)[:300]) for e in at.exception]\n"
        "    else:\n"
        "        print(f'[{dil}] OK')\n"
        "import sys; sys.exit(0 if ok else 1)\n"
    )
    r = subprocess.run([PY, "-c", kod], cwd=KOK, env=ENV)
    return r.returncode == 0


def degisen_dosyalar():
    r = subprocess.run(["git", "status", "--porcelain", *VERI_DOSYALARI],
                       cwd=KOK, capture_output=True, text=True)
    return [ln[3:] for ln in r.stdout.splitlines() if ln.strip()]


def sayilar():
    def n(dosya, sayac=None):
        p = KOK / dosya
        if not p.exists():
            return 0
        d = json.load(open(p, encoding="utf-8"))
        return sayac(d) if sayac else len(d)
    roster = n("scout_kadro_raporlar.json")
    sd     = n("scouting_sd_profiller.json")
    leist  = n("scouting_leistungsdaten.json")
    return roster, sd, leist


def main():
    args = sys.argv[1:]
    no_push   = "--no-push" in args
    no_scrape = "--no-scrape" in args

    kosu(["fetch_scout_kadro.py"], "1/5  Sco 🌍 → scout_kadro_raporlar.json")
    if not no_scrape:
        kosu(["scrape_scouting_yeni.py"], "2/5  Yeni oyuncuların SD profilleri")
        kosu(["scrape_leistungsdaten.py", "--eksik"], "3/5  Yeni oyuncuların kariyer verileri")
        kosu(["fetch_scout_kadro.py"], "4/5  Yaş backfill (yeni SD profillerinden)")
    else:
        print("\n(--no-scrape: SD/kariyer çekme adımları atlandı)")

    if not apptest_gecer():
        print("\n✖ AppTest BAŞARISIZ — commit YAPILMADI. Hatayı düzeltip tekrar çalıştır.")
        sys.exit(1)

    degisen = degisen_dosyalar()
    if not degisen:
        print("\n✔ Değişiklik yok — commit gerekmiyor. Veri zaten güncel.")
        return

    roster, sd, leist = sayilar()
    print(f"\nDeğişen dosyalar: {', '.join(degisen)}")

    msg = (
        f"chore(scouting): veri guncellemesi ({date.today().isoformat()})\n\n"
        f"- Roster (Sco): {roster} oyuncu\n"
        f"- SD profil havuzu: {sd}\n"
        f"- Kariyer (leistungsdaten): {leist}\n\n"
        f"guncelle.py ile otomatik. AppTest (TR+EN) gecti.\n\n"
        f"Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>\n"
    )
    msg_yol = KOK / "COMMIT_MSG.tmp"
    msg_yol.write_text(msg, encoding="utf-8")

    subprocess.run(["git", "add", *degisen], cwd=KOK, check=True)
    subprocess.run(["git", "commit", "-F", str(msg_yol)], cwd=KOK, check=True)
    msg_yol.unlink(missing_ok=True)
    print("\n✔ Commit edildi.")

    if no_push:
        print("(--no-push: push atlandı. Hazır olunca: git push origin main)")
        return
    subprocess.run(["git", "push", "origin", "main"], cwd=KOK, check=True)
    print("\n✔ Push edildi → Streamlit Cloud ~1-3 dk içinde deploy eder.")


if __name__ == "__main__":
    main()
