# -*- coding: utf-8 -*-
"""AYLIK BAKIM — SD kulüp senkronu + siteye entegre + deploy. Tek komut:

    python aylik_sd_bakim.py            # tam akış (sheet yazar + push eder)
    python aylik_sd_bakim.py --kuru     # sadece rapor, hiçbir şey yazmaz

Akış: 1) SoccerDonna'dan güncel kulüpleri doğrula (isim+uyruk eşleşmeli,
sd_kulup_guncelle.py) → Sco 🌍 Kulüp kolonunu güncelle  2) entegre_islenmis.py
ile JSON'a çek  3) değişiklik varsa commit + push (Render otomatik deploy).
Windows Görev Zamanlayıcı'ya eklemek için: aylik_sd_bakim.bat'ı ayda bir çalıştır.
"""
import runpy, subprocess, sys, pathlib

sys.stdout.reconfigure(encoding="utf-8")
KOK = pathlib.Path(__file__).parent
KURU = "--kuru" in sys.argv

# DNS bazen googleapis/google için IPv6-only dönüyor (VPN) → IPv4 yedeği
import socket
_gai = socket.getaddrinfo
def _yedek(host, port, *a, **k):
    try:
        return _gai(host, port, *a, **k)
    except socket.gaierror:
        if isinstance(host, str) and "google" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.251.127.95", port))]
        raise
socket.getaddrinfo = _yedek


def adim(baslik):
    print(f"\n{'='*60}\n{baslik}\n{'='*60}")


def calistir(script, argv):
    sys.argv = [script] + argv
    runpy.run_path(str(KOK / script), run_name="__main__")


adim("1/4 — SD profillerinden güncel kulüp tarama (guncel_kulup)")
if not KURU:
    calistir("kulup_guncelle_sd.py", [])
else:
    print("[KURU] atlandı")

adim("2/4 — SoccerDonna kulüp doğrulama" + (" [KURU]" if KURU else ""))
calistir("sd_kulup_guncelle.py", ["--kuru"] if KURU else [])

if KURU:
    print("\n[KURU] Sheet yazılmadı, entegre/deploy atlandı. Log: _kulup_yazim_log.txt")
    sys.exit(0)

adim("3/4 — Siteye entegre (sheet → JSON)")
calistir("entegre_islenmis.py", [])
calistir("fetch_scout_kadro.py", [])   # yaş + SD kulüp override'ı JSON'a işlensin

adim("4/4 — Commit + push (değişiklik varsa)")
_izlenen = ["scout_kadro_raporlar.json", "scouting_sd_profiller.json",
            "soccerdonna_profiller.json"]
degisti = subprocess.run(["git", "diff", "--quiet", "--"] + _izlenen,
                         cwd=KOK).returncode != 0
if not degisti:
    print("JSON değişmedi — deploy gereksiz.")
    sys.exit(0)
for cmd in (["git", "add"] + _izlenen,
            ["git", "commit", "-m", "chore: aylik SD kulup senkronu (otomatik bakim)"],
            ["git", "push", "origin", "main"]):
    r = subprocess.run(cmd, cwd=KOK)
    if r.returncode != 0:
        print(f"✗ komut başarısız: {' '.join(cmd)}"); sys.exit(1)
print("\n✓ Aylık bakım tamam — Render deploy tetiklendi (~2-3 dk).")
