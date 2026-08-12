"""
'Scouting is life' Google Sheet --> 'Sco 🌍' sekmesi (gid=1707810792)
Tüm scout kadro tablosunu çeker -> scout_kadro_raporlar.json

Bu dosya artık Scouting sayfasının HEM roster (oyuncu listesi) HEM zengin
rapor kaynağıdır. Tüm oyuncular alınır (değerlendirilmemiş olanlar dahil);
boş/yanlış (126) yaş alanları SoccerDonna profilinden (scouting_sd_profiller.json)
backfill edilir.

Sütun düzeni dinamik: grup sınırları header satırındaki başlık adlarından
bulunur (kolon eklense de kaymaz). Kullanım:  python fetch_scout_kadro.py
"""
import csv, io, json
from pathlib import Path
import requests

GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID       = "1707810792"
CIKTI     = Path(__file__).parent / "scout_kadro_raporlar.json"
SD_YOL    = Path(__file__).parent / "scouting_sd_profiller.json"
GECERLI_NOTLAR = {"AA","AB","BB","BC","CC","CD","DD","DE","EE","FF","A+"}


def cek() -> str:
    url = (f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}"
           f"/export?format=csv&gid={GID}")
    r = requests.get(url, timeout=25); r.raise_for_status()
    return r.content.decode("utf-8")


def _yas_hesapla(dogum: str):
    """'30.10.2007' -> yaş (int). Geçersizse None."""
    import datetime
    for sep in (".", "/", "-"):
        if sep in dogum:
            parca = dogum.split(sep)
            if len(parca) == 3:
                try:
                    g, a, y = (int(x) for x in parca)
                    if y < 100:
                        y += 2000 if y < 30 else 1900
                    bugun = datetime.date.today()
                    yas = bugun.year - y - ((bugun.month, bugun.day) < (a, g))
                    if 5 <= yas <= 60:
                        return yas
                except Exception:
                    return None
    return None


# ── Baran 2026-08'de Dünya sheet'inin başlıklarını İNGİLİZCEYE çevirdi. ────────
# JSON şeması TÜRKÇE kalmalı: app.py nitelik adlarını `_NITELIK_EN` ile çeviriyor,
# kart_uret.py / portfoy_* scriptleri de Türkçe anahtar bekliyor. Bu yüzden başlık
# satırı okunur okunmaz kanonik Türkçe adlara çevrilir; sheet TR'ye dönerse de
# çalışmaya devam eder (eşleşmeyen başlık aynen geçer).
_EN_TR_GENEL = {
    "Name & Surname": "İsim - Soyisim",
    "Country Name": "Sporcunun Tam İsmi",      # Baran yanlış etiketlemiş: içerik TAM İSİM
    "Citizenship (National Team)": "Vatandaşlık (Millî)",
    "Secondary Citizenship": "2. Vatandaşlık",
    "Date of Birth": "Doğum Tarihi", "Age": "Yaş", "Height": "Boy",
    "Strong Foot": "Ayak", "Body Type": "Vücut Tipi", "Zone": "Bölge",
    "Main Position": "Mevki 1", "Alternative Position": "Mevki 2",
    "Playable Position": "Mevki 3", "Role": "Rol",
    # BECERİ
    "Finishing": "Bitiricilik", "Ball Technique": "Top Tekniği",
    "Penalty Kick": "Penaltı Vuruşu", "Marking": "Markaj", "Tackling": "Top Kapma",
    "Long Throw": "Uzun Taç", "Set Pieces": "Duran Top", "First Touch": "İlk Kontrol",
    "Heading": "Kafa Vuruşu", "Crossing": "Orta Yapma", "Short Passing": "Kısa Pas",
    "Long Passing": "Uzun Pas", "Dribbling": "Top Sürme", "Long Shot": "Uzaktan Şut",
    "Technical Note": "BECERİ Not",
    # BEŞERİ
    "Aggression": "Agresiflik", "Bravery": "Cesaret", "Decision": "Karar Alma",
    "Determination": "Kararlılık", "Concentration": "Konsantrasyon",
    "Leadership": "Liderlik", "Perception": "Önsezi", "Positioning": "Konumlanma",
    "Calmness": "Soğukkanlılık", "Strategy": "Takım Oyunu", "Free Spaces": "Topsuz Alan",
    "Vision": "Görüş", "Mental Note": "BEŞERİ Not",
    # FİZİKİ
    "Agility": "Çeviklik", "Durability": "Dayanıklılık", "Balance": "Denge",
    "Strength": "Güç", "Pace": "Sürat", "Acceleration": "Hızlanma",
    "Coordination": "Koordinasyon", "Fitness": "Zindelik", "Jumping": "Zıplama",
    "Weak Foot": "Zayıf Ayak", "Physical Note": "FİZİKİ Not",
    # ŞAHSİ
    "Injury Resistance": "Sakatlanma Direnci", "Sportsmanship": "Sportmenlik",
    "Professionalism": "Profesyonellik", "Loyalty": "Sadakat",
    "Pressure Resistance": "Baskıya Dayanıklılık", "Compatibility": "Uyumluluk",
    "Permanence": "Süreklilik", "Diligence": "Çalışkanlık", "Individual Note": "ŞAHSİ Not",
    # Özet / notlar
    "Ultimate Note": "NİHAİ", "Development": "İVME", "Class": "Yetenek Kümesi",
    "Cost": "İktisadi Durum", "🇹🇷 Perspective": "TR Görüşü", "Perspective": "TR Görüşü",
    "Scouting Notes": "Scout Notları",
    # Kulüp bilgileri (Baran bunları da çevirdi — TR hâlleri de destekleniyor)
    "Club": "Kulüp", "League": "Lig", "Value": "Değeri", "Market Value": "Değeri",
    "Contract": "Sözleşme", "Current Club": "Güncel Kulüp",
    "Current Contract (SD)": "Güncel Sözleşme (SD)",
}
# Kaleci bloğu: aynı İngilizce ad saha oyuncusunda BAŞKA bir Türkçe niteliğe denk
# geliyor (First Touch/Ball Technique) → bu blok ayrı haritayla çevrilir.
_EN_TR_KALECI = {
    "Handling": "Elle Kontrol - Sahiplenme",
    "First Touch": "Ayakla Kontrol - İlk Temas",
    "Ball Technique": "Top Tekniği",
    "Area Domination": "Alan Hakimiyeti", "Line Domination": "Çizgi Hakimiyeti",
    "Aerial Domination": "Hava Hakimiyeti", "Side-Ball Domination": "Yan Top Hakimiyeti",
    "Throwing": "Elle Oyun Kurma", "Kicking": "Ayak ile Oyun Kurma - Kısa",
    "Punt / Clearance": "Degaj ile Oyun Kurma - Uzun", "Rushing Out": "Kaleden Ani Çıkış",
    "Punching": "Yumruklama Kabiliyeti", "Communication": "İletişim",
    "In-Side Virtues": "Kaleci Dışı Meziyetler",
    "Goalkeeping Note": "KALECİ Not",
}


# ── DEĞER kanonlaştırma ────────────────────────────────────────────────────────
# Baran başlıklarla birlikte HÜCRE DEĞERLERİNİ de İngilizceye çevirdi. Site
# Türkçe-anahtarlı (filtreler, renk/grup eşlemeleri, `_ROL_EN`/`_BOLGE_EN` gibi
# çeviri sözlükleri hep Türkçe değer bekliyor), bu yüzden okuma anında geri
# kanonik Türkçeye çevrilir. Kesin 1:1 karşılığı OLMAYAN (Baran'ın yeni
# tanımladığı) roller BİLEREK dokunulmadan bırakılır — uydurma çeviri yapılmaz.
_DEGER_BOLGE = {
    "goalkeeper": "Kale", "defender": "Savunma",
    "midfielder": "Orta Saha", "attacker": "Hücum",
}
_DEGER_AYAK = {"right": "Sağ", "left": "Sol", "both": "Çift"}
_DEGER_VUCUT = {
    "ectomorph": "Ektomorf", "endomorph": "Endomorf", "mesomorph": "Mezomorf",
    "meso-ectomorph": "Mezo-Ektomorf", "meso-endomorph": "Mezo-Endomorf",
}
# Sitenin mevcut Türkçe rol sözlüğüyle birebir örtüşenler
_DEGER_ROL = {
    "line keeper": "Çizgi Kalecisi", "sweeper keeper": "Libero Kaleci",
    "libero keeper": "Libero Kaleci", "regnant keeper": "Hükmeden Kaleci",
    "playmaker winger": "Oyun Kurucu Kanat",   # Baran'ın kendi TR karşılığı veride mevcut
    "playmaker": "Oyun Kurucu", "deep lying playmaker": "Derinden Oyun Kurucu",
    "inverted winger": "İçe Kat Eden Kanat", "target winger": "Hedef Kanat",
    "target striker": "Hedef Santrfor", "false #9": "Sahte 9",
    "balanced full-back": "Dengeli Bek", "poacher": "Tilki",
    "warrior": "Savaşçı", "dynamo": "Dinamo", "anchor": "Çapa",
    "no-nonsense back": "Çakılı Stoper", "ball-playing back": "Oyun Kurucu Stoper",
    "limited back": "Limitli Stoper", "overlapping full-back": "Kanat Bek",
    "mezzala": "Mezzala", "volante": "Volante", "raumdeuter": "Raumdeuter",
}
# Emoji'si birebir eşleşen yetenek kümeleri (emoji farklıysa çevrilmez)
_DEGER_KUME = {
    "🩹 insufficient": "🩹 Yedek", "🎁 inadvertent": "🎁 Kalburüstü",
    "🏅 important": "🏅 Önemli", "🍂 redundant": "🍂 Tercih Dışı",
}
_DEGER_ALAN = {
    "bolge": _DEGER_BOLGE, "ayak": _DEGER_AYAK, "vucut_tipi": _DEGER_VUCUT,
    "rol": _DEGER_ROL, "yetenek_kumesi": _DEGER_KUME,
}


def deger_kanonlastir(alan: str, deger: str) -> str:
    """Tek bir alan değerini kanonik Türkçeye çevirir (eşleşme yoksa aynen döner)."""
    s = (deger or "").strip()
    if not s:
        return s
    return _DEGER_ALAN.get(alan, {}).get(s.lower(), s)


def hdr_kanonlastir(hdr: list) -> list:
    """Başlık satırını kanonik TÜRKÇE adlara çevirir (EN sheet desteği)."""
    gk0 = next((i for i, h in enumerate(hdr)
                if h.strip().startswith(("Handling", "Elle Kontrol"))), len(hdr))
    out = []
    for i, h in enumerate(hdr):
        hs = h.strip()
        if i >= gk0 and hs in _EN_TR_KALECI:
            out.append(_EN_TR_KALECI[hs])
        else:
            out.append(_EN_TR_GENEL.get(hs, h))
    return out


def parse(metin: str) -> dict:
    rows = list(csv.reader(io.StringIO(metin)))
    hdr  = hdr_kanonlastir(rows[1])

    def idx(ad):
        return hdr.index(ad)

    def idx_baslar(*adaylar):
        """Başlığı verilen ön-eklerden biriyle başlayan ilk kolon indexi."""
        for i, h in enumerate(hdr):
            for a in adaylar:
                if h.strip().startswith(a):
                    return i
        raise ValueError(f"Kolon bulunamadı: {adaylar}")

    # Nitelik grup sınırları (makro NOT başlıkları 'BECERİ N' biçiminde)
    i_beceri0 = idx("Bitiricilik")
    i_beceri9 = idx_baslar("BECERİ")
    i_beseri0, i_beseri9 = i_beceri9 + 1, idx_baslar("BEŞERİ")
    i_fiziki0, i_fiziki9 = i_beseri9 + 1, idx_baslar("FİZİKİ")
    i_sahsi0,  i_sahsi9  = i_fiziki9 + 1, idx_baslar("ŞAHSİ")
    i_tarz0  = i_sahsi9 + 1
    i_nihai  = idx_baslar("NİHAİ")
    i_ivme   = idx_baslar("İVME")
    # KALECİ YETKİNLİKLERİ grubu (sadece kaleciler için dolu) — 14 nitelik + "KALECİ Not"
    i_kaleci0 = idx_baslar("Elle Kontrol")
    i_kaleci9 = idx_baslar("KALECİ")

    # ── Sabit alan kolonları BAŞLIK ADINA göre (kolon kaymalarına dayanıklı) ──
    # Not: 2024→ sheet'te kolonlar 2 sola kaydı (Oyuncu Adı 3→1). Sabit indeks
    # yerine başlık adıyla bulmak, ileride yine kayarsa kırılmayı önler.
    c_isim   = idx_baslar("İsim - Soyisim", "Oyuncu Adı")      # eşleşme anahtarı (kısa ad)
    c_tam    = idx_baslar("Sporcunun Tam İsmi", "Tam İsim")
    c_vat    = idx_baslar("Vatandaşlık")        # "Vatandaşlık (Millî)" — "2." ile başlamaz
    c_mil    = idx_baslar("2. Vatandaşlık")     # = 2. pasaport. DİKKAT: bu MİLLİ TAKIM DEĞİL!
    # (app milli takımı 'vatandaslik' = "Vatandaşlık (Millî)" alanından alır. milli_takim
    #  adı tarihsel/yanıltıcı; aslında ikinci vatandaşlık. NT için kullanma.)
    c_dog    = idx_baslar("Doğum")
    c_yas    = idx_baslar("Yaş")
    c_boy    = idx_baslar("Boy")
    c_ayak   = idx_baslar("Ayak")
    c_vucut  = idx_baslar("Vücut")
    c_bolge  = idx_baslar("Bölge")
    c_mevki  = [idx_baslar("Mevki 1"), idx_baslar("Mevki 2"), idx_baslar("Mevki 3")]
    c_rol    = idx_baslar("Rol")
    c_kulup  = idx_baslar("Kulüp")
    c_lig    = idx_baslar("Lig")
    c_deger  = idx_baslar("Değer")
    c_sozl   = idx_baslar("Sözleşme")

    def h(r, i):
        return r[i].strip() if i < len(r) else ""

    def nitelik(r, i0, i9):
        return {hdr[i]: h(r, i) for i in range(i0, i9) if h(r, i) in GECERLI_NOTLAR}

    veriler = {}
    _bos_ardisik = 0
    for r in rows[2:]:
        if not r or not h(r, c_isim):      # Oyuncu Adı (eşleşme anahtarı)
            _bos_ardisik += 1
            # Ana liste ile ALTTAKİ ayrı bölüm (Afrika milli takım kadroları vb.) arasında
            # ~200 satırlık boşluk var. Büyük boşluk = ikinci blok başladı → DUR.
            if veriler and _bos_ardisik >= 20:
                break
            continue
        _bos_ardisik = 0
        isim = h(r, c_isim)

        beceri = nitelik(r, i_beceri0, i_beceri9)
        beseri = nitelik(r, i_beseri0, i_beseri9)
        fiziki = nitelik(r, i_fiziki0, i_fiziki9)
        sahsi  = nitelik(r, i_sahsi0,  i_sahsi9)
        # Kaleci yetkinlikleri SADECE mevkii GK olanlar için (saha oyuncularında FF dolu → atla)
        _kaleci_mi = any(h(r, j).strip().upper() == "GK" for j in c_mevki)
        kaleci = nitelik(r, i_kaleci0, i_kaleci9) if _kaleci_mi else {}
        tum = (list(beceri.values()) + list(beseri.values())
               + list(fiziki.values()) + list(sahsi.values()) + list(kaleci.values()))
        degerlendirildi = bool(tum) and any(n != "FF" for n in tum)

        tarz = []
        for i in range(i_tarz0, i_nihai):
            v = h(r, i)
            if v and v != "✘":             # ✘ = özellik yok; ✔/✔︎ = var
                tarz.append(hdr[i])

        mevki = [h(r, j).replace("-", "") for j in c_mevki
                 if h(r, j) and h(r, j) != "-"]

        dogum = h(r, c_dog)
        yas_h = h(r, c_yas)
        # Sheet yaşı sadece geçerliyse al (126 = boş DT formülü → atılır)
        try:
            yas = int(yas_h)
            if not (5 <= yas <= 60):
                yas = ""
        except ValueError:
            yas = ""
        if yas == "" and dogum:
            y2 = _yas_hesapla(dogum)
            if y2:
                yas = y2

        kayit = {
            "tam_isim":    h(r, c_tam),
            "vatandaslik": h(r, c_vat),
            "milli_takim": h(r, c_mil),
            "dogum":       dogum,
            "yas":         yas,
            "boy":         h(r, c_boy),
            "ayak":        deger_kanonlastir("ayak", h(r, c_ayak)),
            "vucut_tipi":  deger_kanonlastir("vucut_tipi", h(r, c_vucut)),
            "bolge":       deger_kanonlastir("bolge", h(r, c_bolge)),
            "mevki":       mevki,
            "rol":         deger_kanonlastir("rol", h(r, c_rol)),
            "kulup":       h(r, c_kulup),
            "lig":         h(r, c_lig),
            "deger":       h(r, c_deger),
            "sozlesme":    h(r, c_sozl),
            "beceri": beceri, "beseri": beseri, "fiziki": fiziki, "sahsi": sahsi,
            "kaleci": kaleci,
            "makro": {
                "beceri": h(r, i_beceri9) if h(r, i_beceri9) in GECERLI_NOTLAR else "",
                "beseri": h(r, i_beseri9) if h(r, i_beseri9) in GECERLI_NOTLAR else "",
                "fiziki": h(r, i_fiziki9) if h(r, i_fiziki9) in GECERLI_NOTLAR else "",
                "sahsi":  h(r, i_sahsi9)  if h(r, i_sahsi9)  in GECERLI_NOTLAR else "",
                "kaleci": h(r, i_kaleci9) if (_kaleci_mi and h(r, i_kaleci9) in GECERLI_NOTLAR) else "",
            },
            "tarz":       tarz,
            "nihai":      h(r, i_nihai) if h(r, i_nihai) in GECERLI_NOTLAR else "",
            "ivme":       h(r, i_ivme) if h(r, i_ivme) not in ("", "-") else "",
            "yetenek_kumesi": deger_kanonlastir("yetenek_kumesi", h(r, idx("Yetenek Kümesi"))),
            "iktisadi_durum": h(r, idx("İktisadi Durum")),
            "tr_gorusu":  h(r, idx("TR Görüşü")),
            "scout_notu": h(r, idx("Scout Notları")),
            "degerlendirildi": degerlendirildi,
        }

        # Çift kayıt (transfer/duplike): değerlendirilmiş olan kazanır;
        # ikisi de aynı statüdeyse KÜNYE ALANI DAHA DOLU olan kazanır
        # (ham Afrika bloğundaki boş kopyanın dolu kaydı ezmesini önler)
        if isim in veriler:
            eski = veriler[isim]
            if eski["degerlendirildi"] and not degerlendirildi:
                continue
            if eski["degerlendirildi"] == degerlendirildi:
                def _doluluk(k):
                    return sum(1 for f in ("kulup", "lig", "dogum", "boy", "deger", "sozlesme")
                               if (k.get(f) or "").strip())
                if _doluluk(kayit) < _doluluk(eski):
                    continue
        veriler[isim] = kayit

    return veriler


def yas_backfill(veriler: dict) -> int:
    """Yaşı/doğumu boş olanları SoccerDonna profilinden tamamla."""
    if not SD_YOL.exists():
        return 0
    sd = json.load(open(SD_YOL, encoding="utf-8"))
    n = 0
    for isim, k in veriler.items():
        if k.get("yas"):
            continue
        p = sd.get(isim)
        if not isinstance(p, dict):
            continue
        dob = p.get("Date of birth", "")
        if not k.get("dogum") and dob:
            k["dogum"] = dob
        # SD 'Age' alanı "18" veya "18 years" olabilir
        y = _yas_hesapla(k.get("dogum", "")) if k.get("dogum") else None
        if not y:
            import re
            m = re.search(r"\d{1,2}", str(p.get("Age", "")))
            if m:
                yy = int(m.group())
                y = yy if 5 <= yy <= 60 else None
        if y:
            k["yas"] = y
            n += 1
    return n


def kulup_guncelle(veriler: dict) -> int:
    """Sitede görünen takım SoccerDonna'dan gelsin: SD profilindeki
    `guncel_kulup` (kulup_guncelle_sd.py yazar) sheet kulübünü EZER.
    SD bilmiyorsa (alan yok/boş) sheet kulübü kalır; sheet değeri
    `kulup_sheet` alanında saklanır."""
    if not SD_YOL.exists():
        return 0
    sd = json.load(open(SD_YOL, encoding="utf-8"))
    n = 0
    for isim, k in veriler.items():
        p = sd.get(isim)
        if not isinstance(p, dict):
            continue
        g = (p.get("guncel_kulup") or "").strip()
        if g and g != k.get("kulup"):
            k["kulup_sheet"] = k.get("kulup", "")
            k["kulup"] = g
            n += 1
    return n


def main():
    veriler = parse(cek())
    bf = yas_backfill(veriler)
    kg = kulup_guncelle(veriler)
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)
    n_ok = sum(1 for v in veriler.values() if v["degerlendirildi"])
    n_yas = sum(1 for v in veriler.values() if v.get("yas"))
    print(f"{len(veriler)} oyuncu ({n_ok} değerlendirilmiş) -> {CIKTI.name}")
    print(f"Yaş dolu: {n_yas}/{len(veriler)} (SD backfill: {bf})")
    print(f"Kulüp SD'den güncellendi: {kg}")


if __name__ == "__main__":
    main()
