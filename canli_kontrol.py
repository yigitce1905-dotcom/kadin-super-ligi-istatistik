# -*- coding: utf-8 -*-
"""Canlı site duman testi — deploy sonrası statik dosyalar ve sağlık kontrolü.

Neden: 01.11.2026'da Render taze build'de starlette/anyio'nun yeni sürümlerini kurdu,
/app/static/* 500 döndü ve site logosu + kulüp armaları sessizce kayboldu. Uygulama
ayakta göründüğü için kimse fark etmedi. Bu script o tür kırılmaları yakalar.

Kullanım:
    python canli_kontrol.py              # canlı site
    python canli_kontrol.py --bekle      # deploy bitene kadar (en çok ~10 dk) tekrar dener
    python canli_kontrol.py --url=http://127.0.0.1:8501
Çıkış kodu: 0 = her şey yolunda, 1 = sorun var.
"""
import json
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
URL = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--url=")), "https://womenfootballscouting.com").rstrip("/")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) wfs-canli-kontrol"}


def hedefler():
    t = ["/_stcore/health", "/app/static/logo.png", "/app/static/hero.jpg", "/app/static/manifest.json"]
    try:   # kokpit'teki tüm kulüp armaları
        k = json.load(open(KOK / "kokpit_kadrolar.json", encoding="utf-8"))
        t += sorted({"/app/static/" + c["arma"] for c in k["kulupler"].values() if c.get("arma")})
    except Exception:
        pass
    return t


def kontrol():
    hatalar = []
    for yol in hedefler():
        try:
            r = requests.get(URL + yol, headers=H, timeout=30)
            ok = r.status_code == 200 and (yol.endswith(("health", ".json")) or r.headers.get("content-type", "").startswith("image/"))
            if not ok:
                hatalar.append(f"{yol} → {r.status_code} {r.headers.get('content-type', '')}")
        except Exception as e:
            hatalar.append(f"{yol} → {type(e).__name__}")
    return hatalar


def main():
    deneme = 20 if "--bekle" in sys.argv else 1
    for i in range(deneme):
        hatalar = kontrol()
        if not hatalar:
            print(f"✓ {URL}: sağlık ve {len(hedefler()) - 1} statik dosya sorunsuz")
            return 0
        if i < deneme - 1:
            time.sleep(30)
    print(f"✗ {URL}: {len(hatalar)} sorun")
    for h in hatalar:
        print("  -", h)
    return 1


if __name__ == "__main__":
    sys.exit(main())
