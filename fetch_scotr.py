"""
'Scouting is life' Google Sheet --> 'Sco Tr' sekmesi (gid=864990475)
1207 Antalyaspor oyunculari icin Mr Danis scout raporu tablosunu ceker,
temiz JSON'a donusturur: scotr_raporlar.json

Kullanim:  python fetch_scotr.py
"""
import csv
import io
import json
from pathlib import Path

import requests

GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID       = "864990475"
CIKTI     = Path(__file__).parent / "scotr_raporlar.json"

# Kolon gruplari (2. satirdaki basliklara gore, sirasiyla)
BECERI = ["Bitiricilik", "Top Tekniği", "Penaltı Vuruşu", "Markaj", "Top Kapma",
          "Uzun Taç", "Duran Top", "İlk Kontrol", "Kafa Vuruşu", "Orta Yapma",
          "Kısa Pas", "Uzun Pas", "Top Sürme", "Uzaktan Şut"]
BESERI = ["Agresiflik", "Cesaret", "Karar Alma", "Kararlılık", "Konsantrasyon",
          "Liderlik", "Önsezi", "Konumlanma", "Soğukkanlılık", "Takım Oyunu",
          "Topsuz Alan", "Görüş"]
FIZIKI = ["Çeviklik", "Dayanıklılık", "Denge", "Güç", "Sürat", "Hızlanma",
          "Koordinasyon", "Zindelik", "Zıplama", "Zayıf Ayak"]
SAHSI  = ["Sakatlanma Direnci", "Sportmenlik", "Profesyonellik", "Sadakat",
          "Baskıya Dayanıklılık", "Uyumluluk", "Süreklilik", "Çalışkanlık"]


def cek() -> str:
    url = (f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
           f"/export?format=csv&gid={GID}")
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    return r.content.decode("utf-8")


def parse(metin: str) -> dict:
    rows = list(csv.reader(io.StringIO(metin)))
    headers = rows[1]  # 2. satir = kolon adlari
    veriler = {}

    for row in rows[2:]:
        if not row or not row[0].strip():
            continue
        kayit = dict(zip(headers, row))
        isim = kayit.get("Oyuncu Adı", "").strip()
        if not isim:
            continue

        def notu(k):
            v = (kayit.get(k) or "").strip()
            return v if v and v != "-" else ""

        def grup(kolonlar):
            return {k: notu(k) for k in kolonlar if notu(k)}

        # TARZ: BECERI/BESERI/... disindaki, bos olmayan, MAKRO/NIHAI olmayan kolonlar
        bilinen = set(["Oyuncu Adı", "Takım", "Doğum Yılı", "Bölge", "Mevki1",
                       "Mevki2", "Rol", "Yaş", "Uyruk", "NİHAİ", "POTANSİYEL",
                       "Scout Notları"]) | set(BECERI) | set(BESERI) | set(FIZIKI) | set(SAHSI)
        tarz = []
        makrolar = {}
        for k in headers:
            if not k or k in bilinen:
                continue
            v = notu(k)
            if not v:
                continue
            if k.endswith("MAKRO"):
                # Ayni "T.MAKRO" adi iki kez geciyor (beceri + tarz sonu);
                # dict'e ilk deger yazilir, sonraki tarz toplami olarak ezilmez
                makrolar.setdefault(k, v)
            else:
                tarz.append({"ozellik": k, "derece": v})

        # Tum notlar FF ise -> henuz degerlendirilmemis oyuncu
        tum_notlar = list(grup(BECERI).values()) + list(grup(BESERI).values())
        degerlendirildi = any(n != "FF" for n in tum_notlar) if tum_notlar else False

        veriler[isim] = {
            "takim":      kayit.get("Takım", "").strip(),
            "dogum":      kayit.get("Doğum Yılı", "").strip(),
            "bolge":      kayit.get("Bölge", "").strip(),
            "mevki1":     notu("Mevki1"),
            "mevki2":     notu("Mevki2"),
            "rol":        notu("Rol"),
            "yas":        kayit.get("Yaş", "").strip(),
            "uyruk":      kayit.get("Uyruk", "").strip(),
            "beceri":     grup(BECERI),
            "beseri":     grup(BESERI),
            "fiziki":     grup(FIZIKI),
            "sahsi":      grup(SAHSI),
            "makro":      makrolar,
            "tarz":       tarz,
            "nihai":      notu("NİHAİ"),
            "potansiyel": notu("POTANSİYEL"),
            "scout_notu": notu("Scout Notları"),
            "degerlendirildi": degerlendirildi,
        }
    return veriler


def main():
    metin = cek()
    veriler = parse(metin)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)
    n_ok = sum(1 for v in veriler.values() if v["degerlendirildi"])
    print(f"Toplam {len(veriler)} oyuncu ({n_ok} degerlendirilmis) -> {CIKTI.name}")


if __name__ == "__main__":
    main()
