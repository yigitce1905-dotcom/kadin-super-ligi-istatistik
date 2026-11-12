"""Lig takvimi + transfer (tescil) dönemleri → takvim_2026_27.json  (sitede ?takvim=1 sayfası okur)

Kaynaklar:
  · Tescil dönemleri ve federasyonun bildirdiği sezon: FIFA federasyon sayfaları
    (inside.fifa.com/en/associations/<KOD>/snapshot → transferRegistrationCalendar.women). Tarihleri federasyonlar
    FIFA'ya kendileri girer; FIFA aracı günlük güncellenir → bu betik ayda bir yeniden çalıştırılmalı.
  · Ligin ilk ve son maç günü: SoccerDonna hafta sayfaları (1. hafta + son hafta), SD kodu bilinen liglerde.

    python takvim_uret.py            # hepsini çek, dosyayı yaz
    python takvim_uret.py --fifa     # yalnız FIFA kısmını tazele (lig tarihleri eldeki dosyadan korunur)

Tahmin YOK: bir federasyon dönem bildirmemişse alan boş kalır ve sayfada "bildirilmemiş" yazar.
"""
import datetime
import html
import json
import re
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
CIKTI = KOK / "takvim_2026_27.json"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}

# FIFA kodu, Türkçe ad, İngilizce ad, bayrak, (SD lig kodu, SD adres parçası, SD sezon anahtarı, lig adı) ya da None
ULKELER = [
    ("ENG", "İngiltere", "England", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", ("ENG1", "womens-super-league", 2026, "Women's Super League")),
    ("USA", "ABD", "United States", "🇺🇸", ("NWSL", "nwsl", 2025, "NWSL")),
    ("GER", "Almanya", "Germany", "🇩🇪", ("BL1", "bundesliga", 2026, "Frauen-Bundesliga")),
    ("FRA", "Fransa", "France", "🇫🇷", ("DAN1", "premire-ligue", 2026, "Première Ligue")),
    ("ESP", "İspanya", "Spain", "🇪🇸", ("ESP1", "primera-division-femenina", 2026, "Liga F")),
    ("ITA", "İtalya", "Italy", "🇮🇹", ("IT1", "serie-a-women", 2026, "Serie A Women")),
    ("TUR", "Türkiye", "Türkiye", "🇹🇷", ("TUR1", "kadin-futbol-sueper-ligi", 2026, "Kadın Futbol Süper Ligi")),
    ("SWE", "İsveç", "Sweden", "🇸🇪", ("SWE1", "damallsvenskan", 2025, "Damallsvenskan")),
    ("NOR", "Norveç", "Norway", "🇳🇴", None),
    ("DEN", "Danimarka", "Denmark", "🇩🇰", ("3FL", "a-liga", 2026, "A-Liga")),
    ("NED", "Hollanda", "Netherlands", "🇳🇱", None),
    ("BEL", "Belçika", "Belgium", "🇧🇪", None),
    ("SUI", "İsviçre", "Switzerland", "🇨🇭", None),
    ("AUT", "Avusturya", "Austria", "🇦🇹", ("A1", "frauen-bundesliga", 2026, "ÖFB Frauen-Bundesliga")),
    ("POR", "Portekiz", "Portugal", "🇵🇹", ("LNF", "campeonato-nacional-feminino", 2026, "Liga BPI")),
    ("SCO", "İskoçya", "Scotland", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", None),
    ("WAL", "Galler", "Wales", "🏴󠁧󠁢󠁷󠁬󠁳󠁿", ("CYM1", "adran-premier", 2026, "Adran Premier")),
    ("IRL", "İrlanda", "Republic of Ireland", "🇮🇪", ("IRL1", "womens-premier-division", 2025, "Women's Premier Division")),
    ("FIN", "Finlandiya", "Finland", "🇫🇮", None),
    ("ISL", "İzlanda", "Iceland", "🇮🇸", None),
    ("POL", "Polonya", "Poland", "🇵🇱", None),
    ("CZE", "Çekya", "Czechia", "🇨🇿", None),
    ("HUN", "Macaristan", "Hungary", "🇭🇺", None),
    ("SVN", "Slovenya", "Slovenia", "🇸🇮", None),
    ("SRB", "Sırbistan", "Serbia", "🇷🇸", None),
    ("CRO", "Hırvatistan", "Croatia", "🇭🇷", None),
    ("GRE", "Yunanistan", "Greece", "🇬🇷", None),
    ("UKR", "Ukrayna", "Ukraine", "🇺🇦", None),
    ("BRA", "Brezilya", "Brazil", "🇧🇷", None),
    ("MEX", "Meksika", "Mexico", "🇲🇽", None),
    ("CAN", "Kanada", "Canada", "🇨🇦", None),
    ("AUS", "Avustralya", "Australia", "🇦🇺", ("WL", "a-league-women", 2026, "A-League Women")),
    ("JPN", "Japonya", "Japan", "🇯🇵", None),
    ("KOR", "Güney Kore", "Korea Republic", "🇰🇷", None),
    ("CHN", "Çin", "China PR", "🇨🇳", None),
    ("KSA", "Suudi Arabistan", "Saudi Arabia", "🇸🇦", None),
    ("RSA", "Güney Afrika", "South Africa", "🇿🇦", None),
    ("MAR", "Fas", "Morocco", "🇲🇦", None),
    ("NGA", "Nijerya", "Nigeria", "🇳🇬", None),
    ("COL", "Kolombiya", "Colombia", "🇨🇴", None),
    ("ARG", "Arjantin", "Argentina", "🇦🇷", None),
]


# FIFA'da kadın futbolu dönemi BİLDİRİLMEMİŞ ülkeler için elle girilen, kaynağı belli tarihler.
# Türkiye'de kadın futbolu amatör statüde → TFF amatör transfer ve tescil dönemleri geçerli (Yiğit, 13 Kasım 2026).
# Yunanistan: 2026-27 amatör dönemi için güvenilir kaynak bulunamadı → boş (tahmin yazma).
ELLE = {
    "TUR": {"pencere": [["2026-07-31", "2026-11-13"], ["2027-01-04", "2027-03-26"]], "amator": True,
            "kaynak": "TFF Yönetim Kurulu kararı, 30.07.2026 (2026-2027 amatör transfer ve tescil dönemleri)",
            "kaynak_en": "Turkish FA board decision, 30 Jul 2026 (2026-27 amateur transfer and registration periods)"},
}


def getir(url, deneme=2):
    for i in range(deneme):
        try:
            r = requests.get(url, headers=H, timeout=25)
            if r.status_code == 200:
                time.sleep(0.6)
                return r.text
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    return ""


def fifa_cek(kod):
    """{'sezon': [bas, bit] | None, 'pencere': [[bas, bit], …]} — kadın futbolu; bulunamazsa None."""
    s = getir(f"https://inside.fifa.com/en/associations/{kod}/snapshot")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, flags=re.S)
    if not m:
        return None
    try:
        tk = json.loads(m.group(1))["props"]["pageProps"]["association"]["pageData"]["transferRegistrationCalendar"].get("women") or {}
    except Exception:
        return None
    sezon, pencere = None, []
    for blok in tk.get("timelineData") or []:
        for d in blok.get("data") or []:
            for it in d.get("timelineItems") or []:
                a, b = (it.get("startDate") or "")[:10], (it.get("endDate") or "")[:10]
                if not a or not b:
                    continue
                if str(it.get("id", "")).endswith("season"):
                    sezon = [a, b]
                elif "Registration" in str(it.get("id", "")):
                    pencere.append([a, b])
    return {"sezon": sezon, "pencere": sorted(pencere)}


def sd_lig_tarih(kod, slug, yil):
    """Ligin ilk ve son maç günü (yyyy-aa-gg) — SoccerDonna 1. hafta ve son hafta sayfalarından."""
    def gunler(h):
        x = getir(f"https://www.soccerdonna.de/en/{slug}/spieltagsuebersicht/wettbewerb_{kod}_{yil}_{h}.html")
        t = sorted({datetime.date(int(y), int(a), int(g)) for g, a, y in re.findall(r"\b(\d{2})\.(\d{2})\.(20\d{2})\b", x)})
        son = 0
        gunler.mac = len(set(re.findall(r"spielbericht_(\d+)", x)))
        for s in re.findall(r"<select[^>]*>.*?</select>", x, flags=re.S):
            if 'name="spieltag"' in s:
                son = max((int(o) for o in re.findall(r'<option[^>]*value="(\d+)"', s)), default=0)
        return t, son
    ilk, son_hafta = gunler(1)
    if not ilk or not son_hafta:
        return None
    takim = 2 * gunler.mac                       # 1. haftadaki maç sayısı × 2
    son, _ = gunler(son_hafta)
    # sayfada başka tarihler (haber, doğum günü) çıkabiliyor → sezon penceresi dışındakileri at
    alt, ust = datetime.date(yil, 1, 1), datetime.date(yil + 2, 1, 1)
    ilk = [g for g in ilk if alt <= g < ust]
    son = [g for g in son if alt <= g < ust]
    if not ilk or not son:
        return None
    # SD fikstürün tamamını girmemiş olabilir (13 Kasım 2026: Fransa 12, İtalya 7 hafta görünüyordu) → çift devreli lig
    # için beklenen hafta sayısına ulaşmamışsa "son maç" YAZILMAZ; yanlış bitiş tarihi göstermektense boş bırak.
    tam = takim >= 6 and son_hafta >= 2 * (takim - 1)
    return {"ilk_mac": ilk[0].isoformat(), "son_mac": son[-1].isoformat() if tam else None, "hafta": son_hafta, "takim": takim}


def cekilen_lig_bitis(kod):
    """sd_dizilis_<kod>_*.json tamamlanmış bir normal sezonu içeriyorsa son maç günü (yyyy-aa-gg), değilse None."""
    import glob
    for yol in glob.glob(str(KOK / f"sd_dizilis_{kod}_*.json")) + ([str(KOK / "sd_dizilis_2026_27.json")] if kod == "TUR1" else []):
        try:
            m = [x for x in json.load(open(yol, encoding="utf-8")).get("maclar", []) if x.get("skor")]
        except Exception:
            continue
        takim = {x.get("ev") for x in m} | {x.get("dep") for x in m}
        n = len(takim)
        if n >= 6 and len(m) >= n * (n - 1):
            g = max(datetime.date(int(x["tarih"][6:]), int(x["tarih"][3:5]), int(x["tarih"][:2])) for x in m if x.get("tarih"))
            return g.isoformat()
    return None


def main():
    eski = {}
    if CIKTI.exists():
        try:
            eski = {u["fifa"]: u for u in json.load(open(CIKTI, encoding="utf-8")).get("ulkeler", [])}
        except Exception:
            eski = {}
    yalniz_fifa = "--fifa" in sys.argv
    out = []
    for kod, tr, en, bayrak, lig in ULKELER:
        f = fifa_cek(kod)
        kayit = {"fifa": kod, "ulke": tr, "ulke_en": en, "bayrak": bayrak,
                 "sezon": (f or {}).get("sezon"), "pencere": (f or {}).get("pencere") or []}
        if not kayit["pencere"] and kod in ELLE:
            kayit.update(ELLE[kod])
        if lig:
            lt = (eski.get(kod) or {}).get("lig") if yalniz_fifa else None
            if not lt:
                t = sd_lig_tarih(lig[0], lig[1], lig[2])
                lt = {"ad": lig[3], **t} if t else None
            # SD'nin hafta listesi eksik kalabiliyor (NWSL: 26 görünüyor, 30 hafta oynandı). Kendi çektiğimiz maç dosyasında
            # çift devreli ligin TÜM maçları (n × (n-1)) varsa normal sezon bitmiştir → son maç günü oradan.
            if lt and not lt.get("son_mac"):
                bitis = cekilen_lig_bitis(lig[0])
                if bitis:
                    lt["son_mac"] = bitis
            kayit["lig"] = lt
        out.append(kayit)
        print(f"{kod} {tr:16} sezon {kayit['sezon']} · dönemler {kayit['pencere']} · lig {kayit.get('lig')}", flush=True)
    json.dump({"guncelleme": datetime.date.today().isoformat(),
               "kaynak": "FIFA federasyon sayfaları (tescil dönemleri) · SoccerDonna (lig maç günleri)", "ulkeler": out},
              open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{len(out)} ülke · dönemi olan {sum(1 for u in out if u['pencere'])} · lig tarihi olan {sum(1 for u in out if u.get('lig'))} → {CIKTI.name}")


if __name__ == "__main__":
    main()
