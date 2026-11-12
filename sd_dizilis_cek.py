"""SoccerDonna — Kadın Futbol Süper Ligi maç raporları: diziliş, ilk 11, yedekler,
goller, oyuncu değişiklikleri, kartlar. --lig=<kod> ile başka ligler de çekilir
(ENG1 WSL · BL1 Frauen-Bundesliga · ESP1 Liga F · IT1 Serie A · DAN1 Première Ligue · NWSL).

Kaynak sayfalar (maç başına 2 istek):
  /index/spielbericht_<id>.html       → diziliş ("4-3-3 offensively-minded" + hatlar),
                                        teknik sorumlu, goller, değişiklikler, kartlar
  /aufstellung/spielbericht_<id>.html → forma numaralı ilk 11 + yedekler

Çıktı: sd_dizilis_<sezon>.json  (ör. sd_dizilis_2026_27.json)

DİKKAT — SD dizilişte oyuncuları SAHADAKİ yerine göre değil KAYITLI ANA MEVKİSİNE
göre hatlara dağıtır (Defence / Midfield / Striker). 4-3-3 yazıp savunma hattında
3 isim gösteriyorsa dördüncü savunmacı başka hatta yazılmış demektir (ör. FOMGET'te
Alkhovik forvet hattında görünür ama sağ bek oynar). 'hat_uyumsuz' alanı bunu işaretler.

Kullanım:
    python sd_dizilis_cek.py              # eksik maçları çeker (tamamlananları atlar)
    python sd_dizilis_cek.py --tazele     # hepsini baştan çeker
    python sd_dizilis_cek.py --ozet       # çekmeden, eldeki dosyadan takım özeti
    python sd_dizilis_cek.py --lig=ENG1   # başka lig → sd_dizilis_ENG1_2026_27.json (--sezon=2025, --azami=3 deneme)
"""
import datetime
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

sys.stdout.reconfigure(encoding="utf-8")

KOK = Path(__file__).parent
TABAN = "https://www.soccerdonna.de"
# SD lig kodu → (adres parçası, lig adı). 13 Kasım 2026: Süper Lig'in yanına büyük ligler eklendi
# (havuzdaki oyuncuların BU SEZON oynama süresi için — açık olay verisi 2023/24'te kalıyor).
LIGLER = {
    "TUR1": ("kadin-futbol-sueper-ligi", "Kadın Futbol Süper Ligi"),
    "ENG1": ("womens-super-league", "Women's Super League"),
    "BL1": ("bundesliga", "Frauen-Bundesliga"),
    "ESP1": ("primera-division-femenina", "Liga F"),
    "IT1": ("serie-a-women", "Serie A Women"),
    "DAN1": ("premire-ligue", "Première Ligue"),
    "NWSL": ("nwsl", "NWSL"),
}
LIG_KOD = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--lig=")), "TUR1")
LIG_SLUG, LIG_AD = LIGLER[LIG_KOD]
# SD sezon anahtarı = sezonun başladığı yıl (2026 → 2026/27). Takvim yılı liglerinde (NWSL) de aynı anahtar denenir;
# tutmazsa --sezon=2025 ile çağır.
SEZON_YIL = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--sezon=")), 2026))
CIKTI = KOK / (f"sd_dizilis_{SEZON_YIL}_{str(SEZON_YIL + 1)[2:]}.json" if LIG_KOD == "TUR1"      # eski ad korunur (app.py okuyor)
               else f"sd_dizilis_{LIG_KOD}_{SEZON_YIL}_{str(SEZON_YIL + 1)[2:]}.json")
AZAMI_MAC = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--azami=")), 0))    # deneme için: en çok N maç
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}
BEKLE = 1.0
try:
    import lxml  # noqa: F401
    AYRISTIRICI = "lxml"
except Exception:
    AYRISTIRICI = "html.parser"
AZAMI_HAFTA = 34


def getir(yol):
    """HTML metni. Ağ hatasında 3 kez dener (SD ara ara bağlantı kesiyor)."""
    son = None
    for deneme in range(3):
        try:
            r = requests.get(TABAN + yol, headers=H, timeout=20)
            r.raise_for_status()
            time.sleep(BEKLE)
            return r.text
        except Exception as e:
            son = e
            time.sleep(4 * (deneme + 1))
    raise son


def _sade(ad):
    """Takım adı karşılaştırma anahtarı (hafta sayfası 'Bakirköy', rapor 'Bakirkoy' yazabiliyor)."""
    import unicodedata
    ad = unicodedata.normalize("NFKD", str(ad).replace("ı", "i").replace("İ", "I")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", ad)


def _sid(a):
    m = re.search(r"spieler_(\d+)", (a.get("href") or "") if a else "")
    return int(m.group(1)) if m else None


def _dakika(metin):
    """'90. + 2 min.' → '90+2', '40.  min.' → '40'."""
    m = re.search(r"(\d+)\.\s*(?:\+\s*(\d+)\s*)?min", metin or "")
    if not m:
        return ""
    return m.group(1) + ("+" + m.group(2) if m.group(2) else "")


def bolum_tablolari(soup, baslik):
    """<h2>baslik</h2> altındaki tablolar: [(taraf, takım adı, tablo), ...] — taraf ev/dep."""
    h2 = next((h for h in soup.find_all("h2") if h.get_text(strip=True) == baslik), None)
    out = []
    if not h2:
        return out
    for kardes in h2.find_next_siblings():
        if kardes.name == "h2":
            break
        if kardes.name != "div":
            continue
        tablo = kardes.find("table", class_="tabelle_grafik")
        if not tablo:
            continue
        sinif = kardes.get("class") or []
        th = tablo.find("th")
        out.append(("dep" if "fr" in sinif else "ev", th.get_text(" ", strip=True) if th else "", tablo))
    return out


def dizilisler_coz(html):
    """Ham HTML'den iki takımın dizilişi: {'ev'|'dep': {'takim','sema','hatlar','teknik',...}}.
    Regex ile: html.parser bazı maçlarda diziliş hücresini erken kapatıp oyuncu
    bağlantılarını hücrenin dışına atıyordu (ev sahibi dizilişi boş geliyordu)."""
    out = {}
    for m in re.finditer(r"Line-up:\s*([^<]+)</th>(.*?)</table>", html, re.S):
        blok = m.group(2)
        onceki = html[:m.start()]
        taraf = "dep" if onceki.rfind('<div class="fr"') > onceki.rfind('<div class="fl"') else "ev"
        sm = re.search(r'<b class="s10">([^<]*)</b>', blok)
        if not sm or sm.group(1).strip().lower().startswith("coach"):
            continue
        sema = sm.group(1).strip().rstrip(":").strip()
        govde = blok[sm.end():]
        kesim = re.search(r'<b class="s10">\s*Coach', govde)
        oyuncu_kismi = govde[:kesim.start()] if kesim else govde.split("</td>")[0]
        hatlar = [[]]
        for parca in re.finditer(r'<a href="[^"]*spieler_(\d+)[^"]*"[^>]*>([^<]+)</a>|(?<=>)\s*-\s*(?=<)', oyuncu_kismi):
            if parca.group(1):
                hatlar[-1].append({"ad": parca.group(2).strip(), "sd_id": int(parca.group(1))})
            elif hatlar[-1]:
                hatlar.append([])
        hatlar = [h for h in hatlar if h]
        if not hatlar:
            continue
        tk = re.search(r'trainer_\d+\.html"[^>]*>([^<]+)</a>', govde)
        sayilar = [int(x) for x in re.findall(r"\d+", sema.split(" ")[0])] if sema else []
        saha = [len(h) for h in hatlar[1:]]
        out[taraf] = {"takim": m.group(1).strip(), "sema": sema, "hatlar": hatlar,
                      "teknik": tk.group(1).strip() if tk else "",
                      "oyuncu_sayisi": sum(len(h) for h in hatlar),
                      # SD hatları kayıtlı mevkiye göre yazar: şemayla tutmuyorsa işaretle
                      "hat_uyumsuz": bool(sayilar) and saha != sayilar}
    return out


def index_coz(html):
    soup = BeautifulSoup(html, AYRISTIRICI)
    metin = soup.get_text("\n", strip=True)
    m = {}
    baslik = soup.title.get_text(" ", strip=True) if soup.title else ""
    t = re.search(r"Match report\s+(.+?)\s+-\s+(.+?),\s*(\d{2}\.\d{2}\.\d{4})", baslik)
    if t:
        m["ev"], m["dep"], m["tarih"] = t.group(1).strip(), t.group(2).strip(), t.group(3)
    s = re.search(r"\n(\d+:\d+)\n\((\d+:\d+)\)\n", metin)
    if s:
        m["skor"], m["iy"] = s.group(1), s.group(2)
    h = re.search(r"(\d+)\.\s*Match day", metin)
    if h:
        m["hafta_sd"] = int(h.group(1))
    sa = re.search(r"\d{2}\.\d{2}\.\d{4}\s*\n?-\s*(\d{1,2}:\d{2})", metin)
    if sa:
        m["saat"] = sa.group(1)
    se = re.search(r"([\d.]+)\s*Spectators", metin)
    if se:
        m["seyirci"] = int(se.group(1).replace(".", ""))
    hk = re.search(r"Referee:\s*\n?([^\n]+)", metin)
    if hk:
        m["hakem"] = hk.group(1).strip()
    st = soup.find("a", href=re.compile(r"/stadion/"))
    if st:
        m["stat"] = st.get_text(strip=True)
    kimlik = []
    for a in soup.find_all("a", href=re.compile(r"/startseite/verein_\d+")):
        v = int(re.search(r"verein_(\d+)", a["href"]).group(1))
        if v not in kimlik:
            kimlik.append(v)
        if len(kimlik) == 2:
            break
    if len(kimlik) == 2:
        m["ev_id"], m["dep_id"] = kimlik

    m["dizilis"] = dizilisler_coz(html)

    m["goller"] = []
    for taraf, _, tablo in bolum_tablolari(soup, "Goals"):
        for tr in tablo.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3 or not re.fullmatch(r"\d+:\d+", tds[0].get_text(strip=True)):
                continue
            hucre = tds[-1]
            baglar = [a for a in hucre.find_all("a") if "spieler_" in (a.get("href") or "")]
            ham = hucre.get_text(" ", strip=True)
            on, _, asist_kismi = ham.partition("Assist:")
            tur = re.search(r"min\.?\s*([^,]*)", on)
            g = {"skor": tds[0].get_text(strip=True), "taraf": taraf,
                 "ad": baglar[0].get_text(strip=True) if baglar else "",
                 "sd_id": _sid(baglar[0]) if baglar else None,
                 "dk": _dakika(on), "tur": (tur.group(1).strip() if tur else "")}
            if asist_kismi and len(baglar) > 1:
                g["asist"] = baglar[1].get_text(strip=True)
                g["asist_sd_id"] = _sid(baglar[1])
                at = asist_kismi.replace(g["asist"], "", 1).strip(" ,").split(",")[0].strip()
                if at:
                    g["asist_tur"] = at
            m["goller"].append(g)

    def _skor_anahtar(g):
        a, b = g["skor"].split(":")
        return int(a) + int(b)
    m["goller"].sort(key=_skor_anahtar)

    m["degisiklikler"] = []
    for taraf, _, tablo in bolum_tablolari(soup, "Substitutions"):
        for tr in tablo.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            ca, ga = tds[1].find("a"), tds[2].find("a")
            if not ca or not ga:
                continue
            ham = tds[1].get_text(" ", strip=True)
            neden = re.search(r"min\.?\s*(.*)$", ham)
            m["degisiklikler"].append({
                "taraf": taraf, "dk": _dakika(ham),
                "cikan": ca.get_text(strip=True), "cikan_sd_id": _sid(ca),
                "giren": ga.get_text(strip=True), "giren_sd_id": _sid(ga),
                "neden": neden.group(1).strip() if neden else ""})

    m["kartlar"] = []
    for taraf, _, tablo in bolum_tablolari(soup, "Cards"):
        for tr in tablo.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            a = tds[-1].find("a")
            if not a:
                continue
            resim = tds[0].find("img")
            ham = tds[-1].get_text(" ", strip=True)
            parca = [p.strip() for p in ham.split("min.")[-1].strip(" ,").split(",") if p.strip()]
            m["kartlar"].append({
                "taraf": taraf, "dk": _dakika(ham), "ad": a.get_text(strip=True), "sd_id": _sid(a),
                "kart": (resim.get("title") if resim else "") or "",
                "neden": parca[-1] if parca else ""})
    return m


def kadro_coz(html):
    """Aufstellung sayfası → {'ilk11': {ev, dep}, 'yedekler': {ev, dep}}."""
    soup = BeautifulSoup(html, AYRISTIRICI)
    out = {}
    for baslik, anahtar in (("Starting team", "ilk11"), ("Substitutes", "yedekler")):
        out[anahtar] = {}
        for taraf, _, tablo in bolum_tablolari(soup, baslik):
            liste = []
            for tr in tablo.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                a = tr.find("a", href=re.compile(r"spieler_"))
                if not a:
                    continue
                hucre = a.find_parent("td")
                ham = hucre.get_text("\n", strip=True).split("\n")
                yas = re.search(r"(\d+)\s*years", " ".join(ham))
                mevki = ham[-1].split(",")[0].strip() if ham else ""
                no = tds[0].get_text(strip=True)
                liste.append({"no": int(no) if no.isdigit() else None, "ad": a.get_text(strip=True),
                              "sd_id": _sid(a), "mevki": mevki, "yas": int(yas.group(1)) if yas else None})
            out[anahtar][taraf] = liste
    return out


def hafta_listesi(html):
    """Hafta sayfasında listelenen maçlar: [(ev, dep, skor), ...] — raporu olmayanlar dahil."""
    satirlar = BeautifulSoup(html, AYRISTIRICI).get_text("\n", strip=True).split("\n")
    out = []
    for i in range(len(satirlar) - 3):
        if (" - " in satirlar[i] and satirlar[i].startswith(satirlar[i + 1] + " - ")
                and satirlar[i].endswith(" - " + satirlar[i + 3])):
            out.append((satirlar[i + 1], satirlar[i + 3], satirlar[i + 2]))
    return out


def hafta_maclari(hafta, tumu=None):
    html = getir(f"/en/{LIG_SLUG}/spieltagsuebersicht/wettbewerb_{LIG_KOD}_{SEZON_YIL}_{hafta}.html")
    if tumu is not None:
        tumu.extend(hafta_listesi(html))
    bul = re.findall(r'href="(/en/[^"]*/index/spielbericht_(\d+)\.html)"', html)
    sirali, gorulen = [], set()
    for yol, kimlik in bul:
        if kimlik not in gorulen:
            gorulen.add(kimlik)
            sirali.append((int(kimlik), yol))
    return sirali


def ozet(veri):
    maclar = [m for m in veri.get("maclar", []) if m.get("dizilis")]
    print(f"\n{len(veri.get('maclar', []))} maç kaydı · dizilişi olan {len(maclar)} · "
          f"oynanmamış/boş {len(veri.get('oynanmayan', []))} · SD'de raporu olmayan {len(veri.get('raporsuz', []))}")
    for r in veri.get("raporsuz", []):
        print(f"  raporsuz — hafta {r['hafta']}: {r['ev']} {r['skor']} {r['dep']}")
    takim = {}
    for m in maclar:
        for taraf in ("ev", "dep"):
            d = m["dizilis"].get(taraf)
            if d:
                takim.setdefault(m[taraf], Counter())[d["sema"].split(" ")[0]] += 1
    print(f"\n{'Takım':28} Maç  Dizilişler")
    for ad in sorted(takim):
        c = takim[ad]
        print(f"{ad[:28]:28} {sum(c.values()):>3}  " + ", ".join(f"{k} ×{n}" for k, n in c.most_common()))


def main():
    eski = json.load(open(CIKTI, encoding="utf-8")) if CIKTI.exists() else {}
    if "--ozet" in sys.argv:
        ozet(eski)
        return
    tazele = "--tazele" in sys.argv
    hazir = {} if tazele else {m["id"]: m for m in eski.get("maclar", []) if m.get("tam")}
    maclar, oynanmayan, raporsuz = [], [], []
    bos_hafta, yeni_cekilen = 0, 0
    for hafta in range(1, AZAMI_HAFTA + 1):
        try:
            listelenen = []
            liste = hafta_maclari(hafta, listelenen)
        except Exception as e:
            print(f"[hafta {hafta}] liste alınamadı: {type(e).__name__} {str(e)[:60]}", flush=True)
            break
        if not liste:
            break
        oynanan = 0
        for kimlik, yol in liste:
            if kimlik in hazir:
                maclar.append(hazir[kimlik]); oynanan += 1
                continue
            if AZAMI_MAC and yeni_cekilen >= AZAMI_MAC:
                continue
            yeni_cekilen += 1
            try:
                m = index_coz(getir(yol))
            except Exception as e:
                print(f"[hafta {hafta}] {kimlik} HATA {type(e).__name__}: {str(e)[:60]}", flush=True)
                continue
            m = {"id": kimlik, "hafta": hafta, **m}
            if not m.get("skor"):
                oynanmayan.append({"id": kimlik, "hafta": hafta, "ev": m.get("ev", ""),
                                   "dep": m.get("dep", ""), "tarih": m.get("tarih", "")})
                continue
            oynanan += 1
            try:
                m.update(kadro_coz(getir(yol.replace("/index/", "/aufstellung/"))))
            except Exception as e:
                print(f"[hafta {hafta}] {kimlik} kadro HATA {type(e).__name__}: {str(e)[:60]}", flush=True)
            m["tam"] = bool(m.get("dizilis", {}).get("ev") and m.get("dizilis", {}).get("dep")
                            and m.get("ilk11", {}).get("ev") and m.get("ilk11", {}).get("dep"))
            maclar.append(m)
            d = m.get("dizilis", {})
            print(f"[hafta {hafta}] {m.get('ev', '?')[:22]:22} {m['skor']:>5} {m.get('dep', '?')[:22]:22} "
                  f"{(d.get('ev') or {}).get('sema', '—').split(' ')[0]:>8} | "
                  f"{(d.get('dep') or {}).get('sema', '—').split(' ')[0]:<8}"
                  + ("" if m["tam"] else "  (eksik)"), flush=True)
        # SD'de sonucu girilmiş ama maç raporu açılmamış karşılaşmalar
        if len(listelenen) > len(liste):
            adlar = {_sade(m.get("ev", "")) + "|" + _sade(m.get("dep", ""))
                     for m in maclar + oynanmayan if m.get("hafta") == hafta}
            for ev, dep, skor in listelenen:
                if _sade(ev) + "|" + _sade(dep) not in adlar and re.fullmatch(r"\d+:\d+", skor):
                    raporsuz.append({"hafta": hafta, "ev": ev, "dep": dep, "skor": skor})
        veri = {"sezon": f"{SEZON_YIL}-{str(SEZON_YIL + 1)[2:]}", "lig": LIG_AD, "lig_kod": LIG_KOD,
                "kaynak": "soccerdonna.de", "guncelleme": datetime.date.today().isoformat(),
                "maclar": maclar, "oynanmayan": oynanmayan, "raporsuz": raporsuz}
        json.dump(veri, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # Art arda İKİ haftada oynanmış maç yoksa dur (tek hafta ertelenmiş olabilir: milli ara, hava).
        bos_hafta = bos_hafta + 1 if oynanan == 0 else 0
        if bos_hafta >= 2 or (AZAMI_MAC and yeni_cekilen >= AZAMI_MAC):
            break
    if not CIKTI.exists():
        print(f"Hiç maç bulunamadı ({LIG_KOD}, sezon anahtarı {SEZON_YIL}) — takvim yılı liginde --sezon={SEZON_YIL - 1} dene.")
        return
    ozet(json.load(open(CIKTI, encoding="utf-8")))
    print(f"\nYazıldı: {CIKTI}")


if __name__ == "__main__":
    main()
