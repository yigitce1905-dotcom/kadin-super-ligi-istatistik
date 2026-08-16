# -*- coding: utf-8 -*-
"""Rol uyum skoru — Baran'ın "Matrisler" dosyasındaki rol/nitelik matrisi.

YÖNTEM (Baran, 2026-08):
Her rol farklı sayıda ve farklı ağırlıkta nitelik istiyor, dolayısıyla ham
"not × ağırlık" toplamları roller arasında KARŞILAŞTIRILAMAZ. Örnek: bütün
nitelikleri A+ (=10) olan bir oyuncu Savaşçı'da 50×10=500, Derin Oyun
Kurucu'da 63×10=630 alır — fark oyuncudan değil matristen gelir.

Çözüm: her rolün toplam ağırlığına göre bir katsayı (100 / toplam_ağırlık):
    Savaşçı           100/50 = 2.00
    Derin Oyun Kurucu 100/63 = 1.59
Ham puan bu katsayıyla çarpılınca kusursuz oyuncu HER rolde 1000 alır, yani
roller aynı ölçeğe iner. (Matematiksel olarak bu, ağırlıklı ortalamanın 100
ile ölçeklenmiş hâlidir: Σ(not·w)/Σw × 100.)

Not → puan ölçeği doğrusaldır (Baran onayladı):
    A+ 10 · AA 9 · AB 8 · BB 7 · BC 6 · CC 5 · CD 4 · DD 3 · DE 2 · EE 1 · FF 0
Ağırlıklar: 3 = bu rol için ÇOK değerli nitelik, 1 = gerekli nitelik.

Kullanım:
    python rol_matris.py --cek            # matrisi Sheets'ten çek, JSON'a yaz
    python rol_matris.py "BUSEM ŞEKER"    # bir oyuncunun rol sıralaması
"""
import json
import sys
from pathlib import Path

KOK = Path(__file__).parent
CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
MATRIS_ID = "1T-bKIuHSAjbEcHZvNkKPFnj9qBRYtdE3IhQvDEhzojc"
GID_ROLES = 678353602
CIKTI = KOK / "rol_matrisi.json"

# Harf notu → puan (doğrusal, Baran onaylı). FF listede yok = 0.
NOT_PUAN = {"A+": 10, "AA": 9, "AB": 8, "BB": 7, "BC": 6,
            "CC": 5, "CD": 4, "DD": 3, "DE": 2, "EE": 1, "FF": 0}

# Blok TOPLAM sütunları — nitelik değil, toplanmamalı
_TOPLAM_SUTUN = {"Technical Note", "Mental Note", "Physical Note",
                 "Individual Note", "Goalkeeping Note"}
_MEVKI_SUTUN = ["GK", "SW", "SB", "FB", "WB", "DM", "CM", "AM", "WF", "2S", "ST"]

# Bizim mevki kodumuz → matrisin mevki sütunu. Stoper kodları hem SW hem SB'ye
# bakar: matriste stoper rolleri bu iki sütuna dağılmış (Limitli Stoper=SW,
# Pozisyoncu Stoper=SB, Çakılı Stoper=ikisi).
MEVKI_ESLEME = {
    "GK": ["GK"],
    "LCB": ["SW", "SB"], "MCB": ["SW", "SB"], "RCB": ["SW", "SB"], "CB": ["SW", "SB"],
    "LFB": ["FB"], "RFB": ["FB"], "LB": ["FB"], "RB": ["FB"],
    "LWB": ["WB"], "RWB": ["WB"],
    "DMF": ["DM"], "DM": ["DM"],
    "CMF": ["CM"], "CM": ["CM"],
    "AMF": ["AM"], "AM": ["AM"],
    "LWF": ["WF"], "RWF": ["WF"], "LW": ["WF"], "RW": ["WF"],
    "2ST": ["2S"], "2NDST": ["2S"], "SS": ["2S"],
    "CFW": ["ST"], "ST": ["ST"], "CF": ["ST"],
}


def matrisi_cek() -> dict:
    """Sheets'ten Roles sekmesini çekip rol tanımlarını JSON'a yazar."""
    import gspread
    from fetch_scout_kadro import _EN_TR_GENEL, _EN_TR_KALECI

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(MATRIS_ID).get_worksheet_by_id(GID_ROLES)
    satir = ws.get_all_values()
    hdr = [x.strip() for x in satir[1]]

    # Kaleci bloğu 'Handling' ile başlar; aynı İngilizce ad orada FARKLI bir
    # Türkçe niteliğe karşılık geliyor (First Touch → Ayakla Kontrol - İlk Temas)
    gk0 = next((i for i, h in enumerate(hdr) if h == "Handling"), len(hdr))
    nitelik_kol = [(i, h) for i, h in enumerate(hdr)
                   if h and h not in _TOPLAM_SUTUN and h not in _MEVKI_SUTUN
                   and h not in ("ROLLER", "ROLES")]

    def sayi(x):
        x = (x or "").strip()
        return int(x) if x.isdigit() else 0

    roller = []
    for r in satir[2:]:
        ad = (r[0] or "").strip()
        if not ad:
            continue
        agirlik = {}
        for i, h in nitelik_kol:
            w = sayi(r[i] if i < len(r) else "")
            if not w:
                continue
            tr = (_EN_TR_KALECI.get(h) if i >= gk0 else None) or _EN_TR_GENEL.get(h) or h
            agirlik[tr] = w
        toplam = sum(agirlik.values())
        if not toplam:
            continue          # dosyada roller bir de BOŞ şablon olarak tekrarlıyor
        mevkiler = [m for m in _MEVKI_SUTUN if sayi(r[hdr.index(m)])]
        roller.append({
            "ad": ad,
            "ad_en": (r[1] or "").strip(),
            "mevkiler": mevkiler,
            "agirlik": agirlik,
            "toplam": toplam,
            "katsayi": round(100 / toplam, 4),
        })

    veri = {"roller": roller}
    json.dump(veri, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return veri


def matris_yukle() -> dict:
    if not CIKTI.exists():
        return matrisi_cek()
    return json.load(open(CIKTI, encoding="utf-8"))


def oyuncu_nitelikleri(kayit: dict) -> dict:
    """Oyuncunun tüm nitelik notlarını tek sözlükte toplar (harf)."""
    out = {}
    for blok in ("beceri", "beseri", "fiziki", "sahsi", "kaleci"):
        out.update(kayit.get(blok) or {})
    return out


def ayirt_edici_mi(kayit: dict) -> bool:
    """Notlar rolleri ayırt etmeye yetiyor mu?

    Bütün nitelikleri aynı harf olan oyuncularda (TR havuzunda 24 kişi, hepsi
    EE) HER rol matematiksel olarak aynı puanı alır — katsayı tam da bunu
    sağlıyor. O durumda 'en verimli rol' diye bir şey yoktur, sıralama sadece
    matrisin satır sırasıdır. Böyle kayıtlarda sonuç gösterilmemeli."""
    p = [NOT_PUAN.get(v, 0) for v in oyuncu_nitelikleri(kayit).values()]
    return len(set(p)) > 1


def rol_skorlari(kayit: dict, mevkiler=None, matris=None) -> list:
    """[(rol, skor_1000, kapsam)] — skor yüksekten düşüğe.

    kapsam = rolün istediği ağırlığın yüzde kaçı oyuncuda NOTLANMIŞ. Düşükse
    skor az veriye dayanıyor demektir; sıralama yanıltıcı olabilir.
    """
    matris = matris or matris_yukle()
    notlar = oyuncu_nitelikleri(kayit)
    if not notlar:
        return []

    izin = None
    if mevkiler:
        izin = set()
        for m in mevkiler:
            izin.update(MEVKI_ESLEME.get(str(m).strip().upper(), []))

    sonuc = []
    for rol in matris["roller"]:
        if izin is not None and not (set(rol["mevkiler"]) & izin):
            continue
        ham = 0
        kapsanan = 0
        for nit, w in rol["agirlik"].items():
            harf = (notlar.get(nit) or "").strip()
            if harf not in NOT_PUAN:
                continue          # notlanmamış nitelik → 0 sayılır
            ham += NOT_PUAN[harf] * w
            kapsanan += w
        sonuc.append((rol["ad"], round(ham * rol["katsayi"], 1),
                      round(100 * kapsanan / rol["toplam"], 1)))
    return sorted(sonuc, key=lambda x: -x[1])


def main():
    if "--cek" in sys.argv:
        v = matrisi_cek()
        print(f"{len(v['roller'])} rol -> {CIKTI.name}")
        for r in v["roller"][:5]:
            print(f"  {r['ad']:22} {r['ad_en']:26} {'/'.join(r['mevkiler']):14} "
                  f"toplam={r['toplam']:3} katsayi={r['katsayi']:.2f}")
        return

    isim = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
    if not isim:
        print(__doc__)
        return
    tr = json.load(open(KOK / "scotr_raporlar.json", encoding="utf-8"))
    dn = json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8"))
    kayit = tr.get(isim) or dn.get(isim)
    if not kayit:
        print(f"{isim!r} bulunamadı."); return
    mev = [kayit.get("mevki1"), kayit.get("mevki2"), kayit.get("mevki3")] \
        if "mevki1" in kayit else (kayit.get("mevki") or [])
    mev = [m for m in mev if (m or "").strip()]
    print(f"{isim} — mevki: {'-'.join(mev) or '?'}\n")
    if not ayirt_edici_mi(kayit):
        print("  ! Tüm nitelik notları aynı — her rol eşit puan alır, "
              "sıralama anlamsız.\n")
        return
    s = rol_skorlari(kayit, mev)
    for i, (rol, skor, kap) in enumerate(s, 1):
        isaret = "  ← en verimli" if i == 1 else ""
        print(f"  {i:2}. {rol:26} {skor:7.1f} / 1000   (kapsam %{kap:.0f}){isaret}")
    if len(s) > 1 and abs(s[0][1] - s[1][1]) < 1.0:
        print(f"\n  ! İlk iki rol arasında fark 1 puandan az "
              f"({s[0][0]} / {s[1][0]}) — fiilen berabere.")


if __name__ == "__main__":
    main()
