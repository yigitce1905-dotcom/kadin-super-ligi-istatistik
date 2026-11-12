"""Bütün liglerin maç raporlarını tazeleyip oyuncu 'bu sezon' özetini yeniden üretir (haftada bir, tek komut).

    python sd_form_tazele.py            # yedi lig + üç Avrupa kupası: yalnız yeni maçlar çekilir, sonra sd_form_2026_27.json üretilir
    python sd_form_tazele.py ENG1 BL1   # yalnız seçilen ligler

Her lig ayrı süreçte çalışır (sd_dizilis_cek.py lig kodunu komut satırından okur). İlk tam çekim ~35 dk;
haftalık tazeleme birkaç dakika (tamamlanmış maçlar atlanır). Sonra: git add sd_dizilis_*.json sd_form_2026_27.json → commit + push.
"""
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).parent
# kod → SD sezon anahtarı (NWSL takvim yılı ligi: 2026 sezonu SD'de 2025 anahtarıyla duruyor)
LIGLER = {"TUR1": 2026, "ENG1": 2026, "BL1": 2026, "ESP1": 2026, "IT1": 2026, "DAN1": 2026, "NWSL": 2025,
          "SWE1": 2025, "NOR1": 2025, "3FL": 2026, "Nais": 2025, "ISL1": 2025, "LNF": 2026, "UNG1": 2026,
          "CL": 2026, "CLQ": 2026, "EC": 2026}          # Avrupa kupaları (Şampiyonlar Ligi, ön elemesi, Avrupa Kupası)


def main():
    secili = [a for a in sys.argv[1:] if a in LIGLER] or list(LIGLER)
    for kod in secili:
        print(f"\n=== {kod}", flush=True)
        r = subprocess.run([sys.executable, str(KOK / "sd_dizilis_cek.py"), f"--lig={kod}", f"--sezon={LIGLER[kod]}"],
                           cwd=KOK, capture_output=True, text=True, encoding="utf-8", errors="replace")
        satirlar = (r.stdout or "").strip().splitlines()
        yeni = sum(1 for s in satirlar if s.startswith("[hafta") and "HATA" not in s)
        hata = [s for s in satirlar if "HATA" in s or "alınamadı" in s]
        print(f"yeni çekilen maç: {yeni}" + (f" · hata: {len(hata)}" if hata else ""), flush=True)
        for s in hata[:5]:
            print("  ", s[:140])
        if r.returncode != 0:
            print("  süreç hata koduyla bitti:", (r.stderr or "")[-300:])
    print("\n=== özet", flush=True)
    subprocess.run([sys.executable, str(KOK / "sd_form_uret.py")], cwd=KOK)


if __name__ == "__main__":
    main()
