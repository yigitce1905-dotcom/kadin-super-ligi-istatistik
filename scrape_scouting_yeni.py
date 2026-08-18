"""
Sco 🌍 sekmesinde olup scouting_sd_profiller.json'da OLMAYAN yeni oyuncular için
SoccerDonna profili arar + çeker, JSON'a ekler (mevcut kayıtlara dokunmaz).

İsim/uyruk kaynağı: scout_kadro_raporlar.json (Oyuncu Adı = eşleşme anahtarı).
Çıktı formatı scrape_scouting_sd.py ile birebir aynıdır.

Kullanım:  python scrape_scouting_yeni.py
"""
import json, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SD_YOL    = Path(__file__).parent / "scouting_sd_profiller.json"
KADRO_YOL = Path(__file__).parent / "scout_kadro_raporlar.json"


def _ara_tek(isim: str):
    slug  = isim.lower().replace(" ", "-")
    query = isim.replace(" ", "+")
    url   = f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html?quicksearch={query}"
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        links = [a["href"] for a in soup.find_all("a", href=True)
                 if "spieler_" in a.get("href", "")]
        return links[0] if links else None
    except Exception:
        return None


def isim_varyantlari(isim: str) -> list:
    """SD, sheet'teki tam adı nadiren birebir taşır: İspanyol çift soyadını ve
    göbek adını atar (Rosalía Domínguez Navarro → Rosalía Domínguez, Janne
    Sophie Krumme → Janne Krumme). Tam ad tutmazsa bu kısaltmalar denenir.
    Yanlış oyuncuya düşmeyi doğum tarihi kontrolü engeller (bkz. main)."""
    p = isim.split()
    if len(p) < 3:
        return [isim]
    return [isim,
            " ".join(p[:-1]),        # son soyadı at  (2. soyad)
            f"{p[0]} {p[-1]}"]       # göbek adı at


def sd_ara(isim: str):
    """(path, kullanilan_ad) — kısaltılmış varyantla bulunduysa ad farklı gelir."""
    for i, aday in enumerate(isim_varyantlari(isim)):
        path = _ara_tek(aday)
        if path:
            return path, aday
        if i:
            time.sleep(0.4)
    return None, None


def _dogum_uyusuyor(profil: dict, beklenen: str) -> bool:
    """Kısaltılmış ad başka bir oyuncuya düşebilir; iki tarih de doluysa eşleşme
    şart. Biri boşsa doğrulanamaz → kabul (eski davranış)."""
    sd_d = (profil.get("Date of birth") or "").strip()
    bk   = (beklenen or "").strip()
    return not (sd_d and bk) or sd_d == bk


def sd_profil_cek(path: str) -> dict:
    url = "https://www.soccerdonna.de" + path
    try:
        r    = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return {}

    data = {}
    for row in soup.select("table tr"):
        cells = [c.get_text(strip=True) for c in row.select("td")]
        if len(cells) >= 2 and cells[0]:
            key = cells[0].rstrip(":")
            if key not in ("Market value", "2.Club (Number)"):
                data[key] = cells[1]

    sezon_rows = []
    for tablo in soup.select("table"):
        basliklar = [th.get_text(strip=True) for th in tablo.select("th")]
        if "Competition" in basliklar or "Matches" in basliklar:
            for sat in tablo.select("tr"):
                cells = [td.get_text(strip=True) for td in sat.select("td")]
                if len(cells) >= 3 and cells[0] and cells[1]:
                    mac = cells[1]
                    if mac in ("-", ""):
                        continue
                    try:
                        if int(mac) == 0:
                            continue
                    except ValueError:
                        pass
                    sezon_rows.append(cells)
            break
    if sezon_rows:
        data["sezon_istatistikleri"] = sezon_rows
    data["profil_url"] = url
    return data


def main():
    sd    = json.load(open(SD_YOL, encoding="utf-8")) if SD_YOL.exists() else {}
    kadro = json.load(open(KADRO_YOL, encoding="utf-8"))

    # 'bulunamadi' işaretli kayıtlar da yeniden denenir: eski sürüm yalnızca tam
    # adı arıyordu ve SD'nin kısa adlı oyuncuları kalıcı olarak dışarıda kalıyordu.
    yeni = [(isim, k.get("vatandaslik", ""), k.get("dogum", ""))
            for isim, k in kadro.items()
            if isim not in sd or (sd.get(isim) or {}).get("bulunamadi")]
    print(f"SD havuzu: {len(sd)} | Sco 🌍: {len(kadro)} | çekilecek yeni: {len(yeni)}")
    print()

    eklendi, bulunamadi = 0, []
    for i, (isim, vat, dogum) in enumerate(yeni, 1):
        print(f"[{i:3}/{len(yeni)}] {isim} ... ", end="", flush=True)
        path, kullanilan = sd_ara(isim)
        profil = sd_profil_cek(path) if path else {}
        if profil and kullanilan != isim and not _dogum_uyusuyor(profil, dogum):
            # kısaltılmış ad başka bir oyuncuyu getirdi → kabul etme
            print(f"RED (doğum {profil.get('Date of birth','?')} ≠ {dogum})")
            profil = {}
        if not profil:
            print("BULUNAMADI") if path is None else None
            bulunamadi.append(isim)
            sd[isim] = {"vatandaslik": vat, "bulunamadi": True}
            time.sleep(0.4)
            continue
        profil["vatandaslik"] = vat
        sd[isim] = profil
        eklendi += 1
        ist = (f"| {len(profil['sezon_istatistikleri'])} ist.satır"
               if "sezon_istatistikleri" in profil else "")
        not_ = "" if kullanilan == isim else f"  [SD adı: {kullanilan}]"
        print(f"OK — {profil.get('Position','?')} {ist}{not_}")
        if eklendi % 10 == 0:
            json.dump(sd, open(SD_YOL, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"  >> ara kayıt ({len(sd)})")
        time.sleep(0.5)

    json.dump(sd, open(SD_YOL, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print()
    print(f"Bitti. Toplam SD: {len(sd)} | eklenen: {eklendi} | bulunamadı: {len(bulunamadi)}")
    if bulunamadi:
        for b in bulunamadi:
            print("  -", b)


if __name__ == "__main__":
    main()
