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
import csv, io, json, re, sys
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8")

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
    "Club": "Kulüp", "Club Name": "Kulüp", "League": "Lig",
    "Value": "Değeri", "Market Value": "Değeri",
    "Contract": "Sözleşme", "Current Club": "Güncel Kulüp",
    "Current Contract (SD)": "Güncel Sözleşme (SD)",
    # ── OYUN TARZI (2026-08-13) ────────────────────────────────────────────
    # Baran bu 32 kolonu da İngilizceye çevirdi. Sıra ve anlam eski Türkçe
    # başlıklarla birebir örtüşüyor. Bu başlıklar aynı zamanda `tarz` listesinin
    # DEĞERLERİ olarak JSON'a yazılıyor → site `_TARZ_EN` ile TR→EN çevirdiği
    # için kanonik Türkçeye döndürülür.
    "Maker an Overlap": "Kanattan Bindirme Yapar",
    "Supporter the Attack": "Fırsat Buldukça Hücuma Katılır",
    "Supporter the Defense": "Fırsat Buldukça Savunmaya Katılır",
    "Try Key / Line-Breaking Passer": "Sık Sık Ara/Kilit Pas Dener",
    "Long-Range Striker": "Kaleyi Uzaktan Yoklar",
    "Prefer Passing to Shooting": "Şut Çekmek Yerine Pas Vermeyi Tercih Eder",
    "Power Shooter/Crosser": "Sert Şutlar/Ortalar Yapabilir",
    "Curved Shooter/Crosser": "Başarılıı Plase veya Kavisli Şut/Orta Dener",
    "Provooker Rivals": "Rakip Oyunculara Sataşır",
    "Sharp Defender": "Temaslı-Agresif Markaj Yapar",
    "Leader with Area Dominance": "Alanına Hakim Bir Liderdir",
    "Objector Against the Referees": "Hakemlere İtiraz Etmeyi Sever",
    "Station Player": "Kaleye Sırtı Dönük Oynayabilir - İstasyon Olabilir",
    "Comer for get the Ball": "Topu Almak İçin Gerilere Kadar Gelir",
    "Responsible, if Necessary": "Gerektiğinde Sorumluluk Alarak Bireysel Oynar",
    "Tempo Setter": "Maçın Temposuna Yön Verir",
    "Show-woman": "Şov Oyunu Sergiler",
    "Player at a High Tempo": "Yüksek Tempolu Oynar",
    "Road-Runner": "Hızını Sahaya Yansıtır",
    "Ball Juggler": "Tekniği İle Rakipten Sıyrılabilir",
    "Strong Weak-Foot": "Zayıf Ayağını Kullanabilir",
    "Set Piece Master": "Duran Toplarda Topun Başına Geçer",
    "Sliding Tackler": "Kayarak Top Çalar",
    "Player to the Gallery": "Tribüne Oynar, Abartılı Sevinir",
    "Card-Prone Player": "Karta Meyilli Hamleler Yapabilir",
    "Ball-Lover": "Topla Oyalanmayı Sever",
    "GK / Long Clearances": "Uzun Degajmanlar Yapabilir",
    "GK / Joiner the Game": "Oyuna Katılımı Yüksektir",
    "GK / Collector with Long Arms": "Kol Boyu Sayesinde Yan Toplarda Etkili Olur",
    "GK / Thrower Long-Range": "Eliyle Uzun Paslar Çıkartabilir",
    "GK / Penalty Kick Saver": "Penaltı Canavarıdır",
    "GK / Complete Keeper": "Çizgide, Alanda, Alan Dışında Oynayabilir; Komple Kalecidir",
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
# TEK KANONİK ROL SÖZLÜĞÜ (2026-08-17, Baran kararı).
# Daha önce iki ayrı Türkçe adlandırma vardı: burada uydurulanlar ile Baran'ın
# "Matrisler" dosyasındakiler. 14 rolde çakışıyorlardı. Matris adları esas
# alındı; Baran'ın gerekçeleri:
#   · "Hücum Bek" bir ROL adı, "Kanat Bek" ise bir MEVKİ adı — karıştırılmamalı
#     (Overlapping Full-Back = Hücum Bek; Diligent Liner = Çalışkan Kenar,
#      o da bir kanat bek rolüdür)
#   · Forvet yerine Santrfor: "Yardımcı Santrfor" daha doğru kullanım
#   · Poacher = "Fırsatçı Golcü" ("Tilki" değil)
# TEK İSTİSNA: Old-School #10 → matris "Tam #10" diyor ama Baran "Eski Tip #10"
# demenin daha doğru olduğunu söyledi.
# AYRICA DÜZELTİLDİ: 'sweeper keeper' ile 'libero keeper' İKİSİ DE "Libero
# Kaleci"ye gidiyordu — matris bunları ayrı roller olarak tanımlıyor.
_DEGER_ROL = {
    "line keeper": "Çizgi Kalecisi",
    "sweeper keeper": "Süpürücü Kaleci",
    "libero keeper": "Libero Kaleci",
    "regnant keeper": "Hükmeden Kaleci",
    "complete back": "Komple Stoper",
    "limited back": "Limitli Stoper",
    "no-nonsense back": "Çakılı Stoper",
    "cover back": "Pozisyoncu Stoper",
    "ball-playing back": "Oyun Kurucu Stoper",
    "traditional full-back": "Savunmacı Bek",
    "balanced full-back": "Dengeli Bek",
    "overlapping full-back": "Hücum Bek",
    "inverted/playmaker liner": "Oyun Kurucu Bek",
    "diligent liner": "Çalışkan Kenar",
    "anchor": "Çapa",
    "volante": "Volante",
    "warrior": "Savaşçı",
    "deep lying playmaker": "Derin Oyun Kurucu",
    "dynamo": "Dinamo/İki Yönlü",
    "mezzala": "Mezzala",
    "playmaker": "Hücumcu Oyun Kurucu",
    "old-school #10": "Eski Tip #10",        # istisna (matris: "Tam #10")
    "false #9": "Sahte #9",
    "assistant forward": "Yardımcı Santrfor",
    "assistant striker": "Yardımcı Santrfor",
    "raumdeuter": "Raumdeuter",
    "line winger": "Çizgi Kanat",
    "inverted winger": "İçe Kat Eden Kanat",
    "playmaker winger": "Oyun Kurucu Kanat",
    "target winger": "Hedef Kanat",
    "complete striker #9": "Komple #9",
    "diligent forward": "Çalışkan Santrfor",
    "poacher": "Fırsatçı Golcü",
    "target striker": "Hedef Santrfor",
    "versatile": "Çok Yönlü",
    "versatile player": "Çok Yönlü",
}
# Emoji'si birebir eşleşen yetenek kümeleri (emoji farklıysa çevrilmez)
# NOT: ⭐️ Star · ✨ Wondergirl · ⁉️ Unpredictable · ✔️ Young Talent için
# Türkçe karşılık Baran'dan alınmadı → bilerek çevrilmiyor (uydurulmaz).
_DEGER_KUME = {
    "🩹 insufficient": "🩹 Yedek", "🎁 inadvertent": "🎁 Kalburüstü",
    "🏅 important": "🏅 Önemli", "🍂 redundant": "🍂 Tercih Dışı",
    "🔮 promising": "🔮 Gelecek Vaad Eden", "💎 unique": "💎 Eşsiz",
    "🧒 callow": "🧒 Genç",
}
# İktisadi durum (maliyet) skalası — Baran 2026-08'de İngilizceye çevirdi
_DEGER_IKTISADI = {
    "prohibitive": "Fahiş", "high": "Yüksek", "medium": "Orta",
    "low": "Düşük", "cheap": "Ucuz", "undefined": "Tanımlanmamış",
}
_DEGER_ALAN = {
    "bolge": _DEGER_BOLGE, "ayak": _DEGER_AYAK, "vucut_tipi": _DEGER_VUCUT,
    "rol": _DEGER_ROL, "yetenek_kumesi": _DEGER_KUME,
    "iktisadi_durum": _DEGER_IKTISADI,
}


def _sadelestir(s: str) -> str:
    """Noktalama/boşluk farkını siler: 'Balanced FullBack' == 'balanced full-back'.
    Baran aynı rolü zaman zaman tireli, zaman zaman bitişik yazıyor; sabit
    anahtarla arayınca 5 rol (Nononsense Back dâhil, 30 oyuncu) çevrilmeden
    kalıyordu (2026-08 fix)."""
    return re.sub(r"[\s\-_/.]", "", s.lower())


def deger_kanonlastir(alan: str, deger: str) -> str:
    """Tek bir alan değerini kanonik Türkçeye çevirir (eşleşme yoksa aynen döner)."""
    s = (deger or "").strip()
    if not s:
        return s
    harita = _DEGER_ALAN.get(alan, {})
    if s.lower() in harita:
        return harita[s.lower()]
    sade = _sadelestir(s)
    for k, v in harita.items():
        if _sadelestir(k) == sade:
            return v
    return s


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
            # boşluk var. 2026-08-23: sheet'te ARA blok icinde 51 satırlık YENİ bir boşluk
            # belirdi (rows 1143-1193) — eşik 20'yken bu, ikinci blok sanılıp erken kesiliyor
            # ve arkasındaki 57 gerçek oyuncu (Megan Campbell, Pernille Mosegaard Harder dahil)
            # sessizce siliniyordu. Eşik 100'e çıkarıldı: sheet sonu zaten döngünün doğal
            # bitişiyle (rows tükenince) durur, break yalnızca gerçekten anormal/çok büyük
            # bir boşluk için bir güvenlik supabı.
            if veriler and _bos_ardisik >= 100:
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
            "iktisadi_durum": deger_kanonlastir("iktisadi_durum", h(r, idx("İktisadi Durum"))),
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


def yas_dogumdan_tazele(veriler: dict) -> int:
    """Doğum tarihi varsa yaşı ONDAN hesapla (sheet'teki yazılı yaşı ezerek).

    Elle yazılan yaş her yıl bayatlar, doğum tarihi bayatlamaz. Sheet'te bu
    yüzden kendi içinde çelişen kayıtlar birikiyordu (ör. Blessing Demehin:
    doğum 13.03.2002 ama yaş 28 yazıyordu — 24 olmalı). Aynı hatanın profil
    ekranındaki sürümü 2026-08-16'da düzeltilmişti; kaynak veride de kapatıldı."""
    n = 0
    for k in veriler.values():
        dg = (k.get("dogum") or "").strip()
        if not dg:
            continue
        y = _yas_hesapla(dg)
        if y and str(k.get("yas") or "") != str(y):
            k["yas"] = y
            n += 1
    return n


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


# SD'nin kulüp yerine döndürdüğü, kulüp OLMAYAN değerler
_KULUP_COP = {"", "-", "?", "pausiert", "karriereende", "unbekannt", "unknown",
              "vereinslos", "without club"}

# Kulüp adı karşılaştırması — app.py'deki _havuz_kalite ile AYNI kural (_KLT_GENEL / _KLT_ES orada da var; birini
# değiştirirsen ötekini de değiştir).
_KLT_GENEL = {"fc", "cf", "sk", "fk", "if", "bk", "ac", "as", "sc", "sv", "cd", "ud", "kulubu", "spor", "women", "ladies", "kadin", "futbol", "club",
              "de", "la", "the", "wfc", "lfc", "afc", "frauen", "femenino", "feminin", "femminile", "fem", "klubu", "genclik", "ve", "united", "city",
              "real", "sporting", "olympique", "athletic", "atletico", "team", "dff", "ff", "kif", "fotball", "football"}
_KLT_ES = {"nurnberg": "nuremberg", "munchen": "munich", "koln": "cologne"}


def _klt_n(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "").replace("ı", "i").replace("İ", "I").replace("ø", "o").replace("ß", "ss"))
    return re.sub(r"[^a-z0-9 ]", " ", s.encode("ascii", "ignore").decode().lower())


def _klt_ayni(a, b):
    """İki kulüp adı aynı kulübü mü gösteriyor? True / False / None (karar verilemiyor)."""
    x = {_KLT_ES.get(w, w) for w in _klt_n(a).split() if len(w) >= 3 and w not in _KLT_GENEL}
    y = {_KLT_ES.get(w, w) for w in _klt_n(b).split() if len(w) >= 3 and w not in _KLT_GENEL}
    if not x or not y:
        return None
    if x & y:
        return True
    na, nb = _klt_n(a).replace(" ", ""), _klt_n(b).replace(" ", "")
    return any(w in nb for w in x if len(w) >= 5) or any(w in na for w in y if len(w) >= 5)


def _klt_siki(a, b):
    """Sıkı kulüp eşleşmesi (yalnız ada dayanan kararlar için): ayırt edici kelime kümeleri aynı ya da biri
    ötekinin alt kümesi VE küçük kümede en az bir 5+ harfli kelime. _klt_ayni'nin alt dize kuralı burada fazla
    gevşek: "Monte Real Football Academy" ↔ "Rayados de Monterrey", "University of Fort Hare" ↔ "Fort Lauderdale"."""
    x = {_KLT_ES.get(w, w) for w in _klt_n(a).split() if len(w) >= 3 and w not in _KLT_GENEL}
    y = {_KLT_ES.get(w, w) for w in _klt_n(b).split() if len(w) >= 3 and w not in _KLT_GENEL}
    if not x or not y:
        return False
    kucuk, buyuk = (x, y) if len(x) <= len(y) else (y, x)
    return kucuk <= buyuk and any(len(w) >= 5 for w in kucuk)


def lig_formdan_duzelt(veriler: dict) -> list:
    """Havuzdaki lig etiketi bu sezonun maç raporlarıyla (sd_form_2026_27.json) çelişiyorsa düzeltir.

    13-14 Kasım 2026 taraması: 19 oyuncuda lig etiketi yanlış ya da boştu (Rosengård/Hammarby oyuncuları
    "Toppserien", Manchester City'li kaleci "NWSL", Benfica'lı oyuncu "Süper Lig"...). Yanlış ülke, transfer
    dönemi hesabını da bozuyordu (öneriler yanlış ülkenin tescil dönemine göre).

    Yalnız şu durumda dokunur: havuzdaki KULÜP, oyuncunun bu sezon maç kadrosuna girdiği takımla AYNI kulüp
    (transfer değil, salt etiket hatası) VE etiket boş ya da başka ülkenin bayrağını taşıyor. Yeni etiket
    Baran'ın o lig için kullandığı yazımdır (havuzda o ligde oynayıp bayrağı doğru olan kayıtlarda en sık
    geçen etiket) — kulup_guncelle'deki "sheet'in yazım biçimi kalır" kuralı. Sheet'teki ilk değer
    `lig_sheet`te saklanır; Kokpit veri kalitesi panelinde gösterilmeye devam eder. Dönüş: düzeltilen adlar."""
    import collections
    form_yol = Path(__file__).parent / "sd_form_2026_27.json"
    if not form_yol.exists() or not SD_YOL.exists():
        return []
    form = json.load(open(form_yol, encoding="utf-8")).get("oyuncular", {})
    sd = json.load(open(SD_YOL, encoding="utf-8"))
    try:
        from lig_motor import LIG_SAYFA
        bayrak = {k: b for k, (b, _, _) in LIG_SAYFA.items()}
        ad = {k: a for k, (_, a, _) in LIG_SAYFA.items()}
    except Exception:
        return []
    bayrak["TUR1"], ad["TUR1"] = "🇹🇷", "TSL"

    def _f(isim):
        p = sd.get(isim)
        m = re.search(r"spieler_(\d+)", str((p or {}).get("profil_url") or "")) if isinstance(p, dict) else None
        f = form.get(m.group(1)) if m else None
        return f if f and f.get("lig") in bayrak and f.get("takim") and (f.get("kadro") or f.get("tm")) else None

    bos = {"", "-", "—", "–", "?"}
    sayac = collections.defaultdict(collections.Counter)
    adaylar = []
    for isim, k in veriler.items():
        if not isinstance(k, dict):
            continue
        f = _f(isim)
        if not f:
            continue
        lig = str(k.get("lig_sheet") or k.get("lig") or "").strip()
        b = bayrak[f["lig"]]
        if lig not in bos and lig.split(" ")[0] == b:
            sayac[f["lig"]][lig] += 1
        elif _klt_ayni(k.get("kulup") or "", f["takim"]) is True:
            adaylar.append((isim, f["lig"], lig))
    duzelen = []
    for isim, kod, eski in adaylar:
        yeni = sayac[kod].most_common(1)[0][0] if sayac[kod] else f"{bayrak[kod]} {ad[kod]}"
        k = veriler[isim]
        k.setdefault("lig_sheet", eski or "-")
        k["lig"] = yeni
        duzelen.append(isim)
    # İkinci geçiş (maç verisi olmayanlar): aynı kulübün EN AZ 2 başka oyuncusu oybirliğiyle aynı etiketi taşıyor,
    # bu oyuncununki boş ya da başka ülke bayraklı → takım arkadaşlarının etiketi (Stephanie Sow: kulübü Burkina
    # Faso'daki USFA, 4 takım arkadaşı "🇧🇫 W-Championnat D1", kendisi eski "🇩🇪 Regionalliga West").
    kulup_lig = collections.defaultdict(list)
    for isim, k in veriler.items():
        if isinstance(k, dict) and isim not in duzelen:
            kl = str(k.get("kulup") or "").strip()
            if kl.lower() not in _KULUP_COP:
                kulup_lig[_klt_n(kl).strip()].append(isim)
    for kl, adlar in kulup_lig.items():
        if not kl or len(adlar) < 3:
            continue
        for isim in adlar:
            k = veriler[isim]
            lig = str(k.get("lig_sheet") or k.get("lig") or "").strip()
            digerleri = {str(veriler[o].get("lig") or "").strip() for o in adlar if o != isim}
            if len(digerleri) != 1:
                continue
            yeni = digerleri.pop()
            if yeni in bos or yeni == lig:
                continue
            if lig in bos or lig.split(" ")[0] != yeni.split(" ")[0]:
                k.setdefault("lig_sheet", lig or "-")
                k["lig"] = yeni
                duzelen.append(isim)
    # Üçüncü geçiş (yalnız BOŞ etiket, oyuncunun kendi maç kaydı yok): kulüp, maç verisinde TEK bir ligin takımına
    # denk geliyorsa o lig (ABB Fomget SK → Süper Lig, Kolbotn IL → Toppserien...). Serbest/ara verenlere dokunmaz.
    lig_takim = collections.defaultdict(set)
    for f in form.values():
        if f.get("lig") in bayrak and f.get("takim"):
            lig_takim[f["lig"]].add(f["takim"])
    for isim, k in veriler.items():
        if not isinstance(k, dict) or isim in duzelen:
            continue
        lig = str(k.get("lig") or "").strip()
        kl = str(k.get("kulup") or "").strip()
        if lig not in bos or kl.lower() in _KULUP_COP or kl.lower() in ("serbest", "free agent", "free agents", "career break"):
            continue
        kodlar = {kod for kod, tk in lig_takim.items() if any(_klt_siki(kl, x) for x in tk)}
        if len(kodlar) != 1:
            continue
        kod = kodlar.pop()
        k.setdefault("lig_sheet", lig or "-")
        k["lig"] = sayac[kod].most_common(1)[0][0] if sayac[kod] else f"{bayrak[kod]} {ad[kod]}"
        duzelen.append(isim)
    return duzelen


def kulup_guncelle(veriler: dict) -> int:
    """Sitede görünen takım SHEET'ten gelir; SD yalnızca boşluğu doldurur.

    2026-08 öncesi tam tersiydi: SD `guncel_kulup` sheet'i EZİYORDU ve sitede
    Excel'dekinden daha kötü adlar çıkıyordu. Ölçüldü — 587 ezmeden yalnızca
    1'i gerçek bilgi katıyordu:
      · 196'sı aynı kulübün farklı yazımıydı (AS FAR→AS Far, Piteå→Pitea,
        Breiðablik→Breidablik: Türkçe/İzlandaca aksanlar da kayboluyordu),
      · gerisi SD'nin Almanca/eski adlandırmasıydı (AS Roma→AS Rom,
        Angel City FC→WFC LA, Gotham FC→Sky Blue FC [2021'de bırakılan ad]),
      · Klil Keshwar sitede 'Serbest' görünüyordu — transferi biz yaptık,
        sheet doğruydu, SD henüz işlememişti.
    Yiğit'in kuralı: takım adları Baran'ın yazdığı formatta kalır.

    SD yalnızca sheet boş ya da çöp değer (Almanca 'pausiert' vb.) taşıyorsa
    devreye girer. SD'nin görüşü her hâlükârda `kulup_sd`de saklanır ki
    gerçek transferleri yakalayan denetim scriptleri veriyi kaybetmesin."""
    if not SD_YOL.exists():
        return 0
    sd = json.load(open(SD_YOL, encoding="utf-8"))
    n = 0
    for isim, k in veriler.items():
        p = sd.get(isim)
        if not isinstance(p, dict):
            continue
        g = (p.get("guncel_kulup") or "").strip()
        if not g:
            continue
        k["kulup_sd"] = g
        # SD "Without Club" / "vereinslos" = serbest oyuncu: sheet'te kulüp boşsa bu BİLGİDİR, çöp değil
        # (14 Kasım 2026: 3 oyuncunun künyesinde takım satırı boş kalıyordu)
        if g.lower() in ("without club", "vereinslos") and (k.get("kulup") or "").strip().lower() in _KULUP_COP:
            k["kulup"] = "Serbest"
            n += 1
            continue
        if g.lower() in _KULUP_COP:
            continue
        if (k.get("kulup") or "").strip().lower() in _KULUP_COP:
            k["kulup"] = g          # sheet boş/çöp → SD doldurur
            n += 1
    return n


# Baran (2026-10-29): Dünya listesinin odağı f/p oyuncu, yetenek keşfi ve transfer.
# Türkiye vatandaşı olup "⁉️ Unpredictable" ya da "🧒 Callow" (sitede "🧒 Genç")
# sınıfındaki oyuncular Dünya listesine alınmaz. Sheet'te kalırlar, sadece siteye girmezler.
# Milli takımı Türkiye olanlar da (çift vatandaş) Türkiye vatandaşı sayılır.
_ODAK_DISI_KUME = ("⁉", "🧒", "unpredictable", "callow")


def _turk_mu(rec: dict) -> bool:
    for alan in ("vatandaslik", "milli_takim"):
        s = (rec.get(alan) or "").lower().replace("ü", "u")
        if "turkiye" in s or "turkey" in s:
            return True
    return False


def dunya_odak_filtre(veriler: dict) -> list:
    """Kuralı uygular, çıkarılan oyuncuların adlarını döndürür (yerinde siler)."""
    cikan = [isim for isim, rec in veriler.items()
             if _turk_mu(rec) and any(k in (rec.get("yetenek_kumesi") or "").lower()
                                      for k in _ODAK_DISI_KUME)]
    for isim in cikan:
        del veriler[isim]
    return cikan


def main():
    veriler = parse(cek())
    bf = yas_backfill(veriler)
    yt = yas_dogumdan_tazele(veriler)
    kg = kulup_guncelle(veriler)
    odak = dunya_odak_filtre(veriler)
    print(f"Dünya odak filtresi (TR vatandaşı Unpredictable/Callow): {len(odak)} oyuncu çıkarıldı")
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=2)
    n_ok = sum(1 for v in veriler.values() if v["degerlendirildi"])
    n_yas = sum(1 for v in veriler.values() if v.get("yas"))
    print(f"{len(veriler)} oyuncu ({n_ok} değerlendirilmiş) -> {CIKTI.name}")
    print(f"Yaş dolu: {n_yas}/{len(veriler)} (SD backfill: {bf})")
    print(f"Yaş doğumdan tazelendi: {yt}")
    print(f"Kulüp SD'den güncellendi: {kg}")


if __name__ == "__main__":
    main()
