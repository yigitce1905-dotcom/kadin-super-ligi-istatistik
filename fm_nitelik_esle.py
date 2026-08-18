# -*- coding: utf-8 -*-
"""FM nitelik değerlerini bizim harf ölçeğimize çevirir.

Yiğit'in kararı (2026-08-17): FMInside sayfasından okunan nitelikler TASLAK
not olarak işlenecek, Baran üzerinden geçecek. Bu dosya yalnızca ÇEVİRİ
mekaniğini yapar — hangi oyuncuya bakılacağına ve sonucun doğru olup
olmadığına insan karar verir.

⚠️ ÜRETİLEN NOTLAR "TASLAK"TIR. Kaynak alanı 'FM' olarak işaretlenir;
Baran onaylayana kadar scout notu sayılmaz. Kulüplere gönderilen metinde
"scouts who watched them" ifadesi varsa, bu kayıtlar için geçerli değildir.

ÖLÇEK
FMInside nitelikleri 1–99 gösteriyor (klasik FM 1–20'nin 5 katı). Eşik
tablosu 20'lik ölçeğin tam karşılıklarına oturtuldu:
    20 → A+ | 18-19 → AA | 16-17 → AB | 15 → BB | 14 → BC | 13 → CC
    12 → CD | 11 → DD | 9-10 → DE | 6-8 → EE | ≤5 → FF
Bu eşikler BARAN'IN ONAYINA TABİDİR — ölçeğin ne anlama geldiğine o karar
verir, ben yalnızca tutarlı uyguluyorum.

KAPSAM (ölçüldü)
  BEŞERİ  12/12  FM'de birebir karşılığı var
  FİZİKİ   8/10  Koordinasyon ve Zayıf Ayak FM'de yok
                 (Zayıf Ayak, FM'in Left/Right foot değerinden türetilir)
  BECERİ  ~11/14 saha oyuncusunda; Penaltı/Uzun Taç FM'de ayrı yok
  KALECİ   9/13  FM'in GK bloğundan
  ŞAHSİ    0/8   FM'de GİZLİ NİTELİK — FMInside'da üyelik arkasında
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# FM 1-99 → harf. EŞİKLER YİĞİT'TEN (2026-08-17) — benim ilk önerim 20'lik
# ölçeğin karşılıklarına oturtulmuştu ve daha cimriydi; bu tablo esastır.
#   A+ 99-100 · AA 95-98 · AB 85-94 · BB 75-84 · BC 65-74 · CC 55-64
#   CD 45-54  · DD 35-44 · DE 25-34 · EE 15-24 · FF 0-14
ESIK = [(99, "A+"), (95, "AA"), (85, "AB"), (75, "BB"), (65, "BC"),
        (55, "CC"), (45, "CD"), (35, "DD"), (25, "DE"), (15, "EE"), (0, "FF")]


def harf(deger) -> str:
    try:
        v = int(deger)
    except (TypeError, ValueError):
        return ""
    for esik, h in ESIK:
        if v >= esik:
            return h
    return "FF"


# ── FM adı → bizim nitelik adı ───────────────────────────────────────────────
# Saha oyuncusu blokları
FM_BECERI = {
    "Finishing": "Bitiricilik", "Technique": "Top Tekniği",
    "Marking": "Markaj", "Tackling": "Top Kapma",
    "Long Throws": "Uzun Taç", "Free Kick Taking": "Duran Top",
    "First Touch": "İlk Kontrol", "Heading": "Kafa Vuruşu",
    "Crossing": "Orta Yapma", "Passing": "Kısa Pas",
    "Dribbling": "Top Sürme", "Long Shots": "Uzaktan Şut",
    "Penalty Taking": "Penaltı Vuruşu", "Corners": "Duran Top",
}
FM_BESERI = {
    "Aggression": "Agresiflik", "Bravery": "Cesaret",
    "Decisions": "Karar Alma", "Determination": "Kararlılık",
    "Concentration": "Konsantrasyon", "Leadership": "Liderlik",
    "Anticipation": "Önsezi", "Positioning": "Konumlanma",
    "Composure": "Soğukkanlılık", "Teamwork": "Takım Oyunu",
    "Off the Ball": "Topsuz Alan", "Vision": "Görüş",
}
FM_FIZIKI = {
    "Agility": "Çeviklik", "Stamina": "Dayanıklılık", "Balance": "Denge",
    "Strength": "Güç", "Pace": "Sürat", "Acceleration": "Hızlanma",
    "Natural Fitness": "Zindelik", "Jumping Reach": "Zıplama",
}
FM_KALECI = {
    "Handling": "Elle Kontrol - Sahiplenme", "First Touch": "Ayakla Kontrol - İlk Temas",
    "Command of Area": "Alan Hakimiyeti", "Reflexes": "Çizgi Hakimiyeti",
    "Aerial Reach": "Hava Hakimiyeti", "Throwing": "Elle Oyun Kurma",
    "Kicking": "Degaj ile Oyun Kurma - Uzun", "Passing": "Ayak ile Oyun Kurma - Kısa",
    "Rushing Out (Tendency)": "Kaleden Ani Çıkış", "Punching (Tendency)": "Yumruklama Kabiliyeti",
    "Communication": "İletişim",
}
# FM'de karşılığı OLMAYAN — boş bırakılır, uydurulmaz
KARSILIKSIZ = {
    "fiziki": ["Koordinasyon"],
    "sahsi": ["Sakatlanma Direnci", "Sportmenlik", "Profesyonellik", "Sadakat",
              "Baskıya Dayanıklılık", "Uyumluluk", "Süreklilik", "Çalışkanlık"],
}


def sayfa_ayristir(metin: str) -> dict:
    """FMInside oyuncu sayfası metninden 'Nitelik: değer' çiftlerini çıkarır."""
    ham = {}
    for ad, deg in re.findall(r"([A-Za-z][A-Za-z '()/-]{2,30}?)\s+(\d{1,2})(?=\s|$)", metin):
        ad = ad.strip()
        if ad and 1 <= int(deg) <= 99:
            ham.setdefault(ad, int(deg))
    return ham


def cevir(ham: dict, kaleci: bool = False) -> dict:
    """FM ham değerleri → {blok: {nitelik: harf}} + eksik listesi."""
    out = {"beceri": {}, "beseri": {}, "fiziki": {}, "sahsi": {}, "kaleci": {}}
    for fm, tr in FM_BESERI.items():
        if fm in ham:
            out["beseri"][tr] = harf(ham[fm])
    for fm, tr in FM_FIZIKI.items():
        if fm in ham:
            out["fiziki"][tr] = harf(ham[fm])
    if kaleci:
        for fm, tr in FM_KALECI.items():
            if fm in ham:
                out["kaleci"][tr] = harf(ham[fm])
    else:
        for fm, tr in FM_BECERI.items():
            if fm in ham:
                out["beceri"][tr] = harf(ham[fm])
    # Zayıf ayak: FM'in Left/Right foot değerlerinden zayıf olanı
    ayaklar = [ham[k] for k in ("Left foot", "Right foot") if k in ham]
    if len(ayaklar) == 2:
        out["fiziki"]["Zayıf Ayak"] = harf(min(ayaklar))
    return out


def rapor(ad: str, ham: dict, kaleci: bool = False):
    c = cevir(ham, kaleci)
    print(f"\n=== {ad} {'(KALECİ)' if kaleci else ''} ===")
    for blok in ("beceri", "kaleci", "beseri", "fiziki"):
        if not c[blok]:
            continue
        print(f"  {blok.upper()}")
        for k, v in c[blok].items():
            fm = next((f for f, t in {**FM_BECERI, **FM_BESERI, **FM_FIZIKI,
                                      **FM_KALECI}.items() if t == k), "?")
            print(f"    {k:34} {v:3}   (FM {fm}={ham.get(fm, '-')})")
    eksik = KARSILIKSIZ["sahsi"] + KARSILIKSIZ["fiziki"]
    print(f"  DOLDURULAMAYAN ({len(eksik)}): {', '.join(eksik)}")
    return c


if __name__ == "__main__":
    print(__doc__)
