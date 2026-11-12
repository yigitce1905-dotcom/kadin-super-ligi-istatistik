"""Avrupa kadın futbolu kulüplerinin RESMÎ sitelerinde YAYIMLADIĞI e-posta adreslerini toplar.

Kural (mail_hedef_listesi_v3_master.md ile aynı): hiçbir adres tahmin edilmez, kalıptan
türetilmez; yalnız kulübün kendi sitesinde açıkça yazan adresler alınır. Özel telefon ya da
WhatsApp numarası TOPLANMAZ. Çıktı ham adaydır — listeye girmeden önce elle ayıklanır
(erkek takımının santraline düşen genel adresler, basın/bilet adresleri vb.).

Kullanım:
    python kulup_iletisim_tara.py                 # KULUPLER listesinin tamamı
    python kulup_iletisim_tara.py --ulke=SE,NO    # yalnız seçilen ülkeler
Çıktı: kulup_iletisim_ham.json  +  ekrana kısa özet
"""
import concurrent.futures as cf
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
KOK = Path(__file__).parent
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
     "Accept-Language": "en-US,en;q=0.9"}
SAYFA_SINIRI = 7
ZAMAN = 9

# (kulüp, ülke kodu, resmî site) — kadın futboluna özel ya da kadın bölümü belirgin kulüpler
KULUPLER = [
    # İsveç
    ("FC Rosengård", "SE", "https://www.fcrosengard.se"), ("BK Häcken", "SE", "https://www.bkhacken.se"),
    ("Linköping FC", "SE", "https://www.linkopingfc.com"), ("Kristianstads DFF", "SE", "https://www.kdff.nu"),
    ("Piteå IF Dam", "SE", "https://www.piteaif.se"), ("Vittsjö GIK", "SE", "https://www.vittsjogik.se"),
    ("Växjö DFF", "SE", "https://www.vaxjodff.se"), ("KIF Örebro DFF", "SE", "https://www.kiforebro.se"),
    ("Umeå IK", "SE", "https://www.umeaik.se"), ("Eskilstuna United", "SE", "https://www.eskilstunaunited.se"),
    ("IK Uppsala Fotboll", "SE", "https://www.ikuppsalafotboll.se"), ("Djurgården Fotboll Dam", "SE", "https://www.dif.se"),
    # Norveç
    ("LSK Kvinner", "NO", "https://www.lsk-kvinner.no"), ("Røa IL", "NO", "https://www.roafotball.no"),
    ("Kolbotn Fotball", "NO", "https://www.kolbotnfotball.no"), ("Stabæk Kvinner", "NO", "https://www.stabak.no"),
    ("Lyn Fotball Damer", "NO", "https://www.lynfotball.no"), ("Arna-Bjørnar", "NO", "https://www.arna-bjornar.no"),
    ("SK Brann Kvinner", "NO", "https://www.brann.no"), ("Åsane Fotball", "NO", "https://www.aasanefotball.no"),
    # Danimarka
    ("HB Køge", "DK", "https://www.hbkoge.dk"), ("Kolding IF", "DK", "https://www.koldingif.dk"),
    ("FC Nordsjælland", "DK", "https://www.fcn.dk"), ("B.93", "DK", "https://www.b93.dk"),
    ("FC Thy-Thisted Q", "DK", "https://www.fcthy.dk"), ("OB Q", "DK", "https://www.ob.dk"),
    # Finlandiya / İzlanda
    ("KuPS", "FI", "https://www.kups.fi"), ("Åland United", "FI", "https://www.alandunited.ax"),
    ("FC Honka", "FI", "https://www.fchonka.fi"), ("PK-35", "FI", "https://www.pk-35.fi"),
    ("Valur", "IS", "https://www.valur.is"), ("Stjarnan", "IS", "https://www.stjarnan.is"),
    ("Þróttur Reykjavík", "IS", "https://www.trottur.is"), ("Víkingur", "IS", "https://www.vikingur.is"),
    # Hollanda / Belçika
    ("Telstar Vrouwen", "NL", "https://www.sctelstar.nl"), ("PEC Zwolle Vrouwen", "NL", "https://www.peczwolle.nl"),
    ("ADO Den Haag Vrouwen", "NL", "https://www.adodenhaag.nl"), ("FC Twente Vrouwen", "NL", "https://www.fctwente.nl"),
    ("OH Leuven Women", "BE", "https://www.ohleuven.com"), ("KAA Gent Ladies", "BE", "https://www.kaagentladies.be"),
    ("Zulte Waregem Ladies", "BE", "https://www.essevee.be"), ("White Star Woluwe", "BE", "https://www.feminawhitestar.be"),
    # İsviçre / Avusturya
    ("Servette FC Chênois Féminin", "CH", "https://www.servettefccf.ch"), ("FC Aarau Frauen", "CH", "https://www.fcaaraufrauen.ch"),
    ("GC Frauen", "CH", "https://www.gcz.ch"), ("FC Luzern Frauen", "CH", "https://www.fcl.ch"),
    ("FC Rapperswil-Jona Frauen", "CH", "https://www.fcrj.ch"), ("FC Thun Frauen", "CH", "https://www.fcthun.ch"),
    ("SKN St. Pölten Frauen", "AT", "https://www.skn-frauen.at"), ("First Vienna FC", "AT", "https://www.firstviennafc.at"),
    ("USV Neulengbach", "AT", "https://www.usvneulengbach.at"), ("FC Bergheim", "AT", "https://www.fcbergheim.at"),
    ("Union Kleinmünchen", "AT", "https://www.unionkleinmuenchen.at"), ("SCR Altach Frauen", "AT", "https://www.scra.at"),
    # Almanya
    ("SV Meppen", "DE", "https://www.svmeppen.de"), ("FSV Gütersloh 2009", "DE", "https://www.fsvguetersloh.de"),
    ("SV 67 Weinberg", "DE", "https://www.sv67weinberg.de"), ("VfR Warbeyen", "DE", "https://www.vfr-warbeyen.de"),
    ("Borussia Bocholt", "DE", "https://www.borussia-bocholt.de"), ("1. FFC Recklinghausen", "DE", "https://www.ffc-recklinghausen.de"),
    # İtalya
    ("Brescia Calcio Femminile", "IT", "https://www.bresciacalciofemminile.it"), ("ACF Arezzo", "IT", "https://www.acfarezzo.it"),
    ("Freedom FC Women", "IT", "https://www.freedomfc.it"), ("San Marino Academy", "IT", "https://www.sanmarinoacademy.sm"),
    ("Orobica Calcio Bergamo", "IT", "https://www.orobicacalcio.it"), ("Pavia Academy", "IT", "https://www.paviaacademy.it"),
    ("Res Women", "IT", "https://www.reswomen.it"), ("Ternana Women", "IT", "https://www.ternanawomen.it"),
    # İspanya
    ("Alhama CF ElPozo", "ES", "https://www.alhamacf.es"), ("FC Badalona Women", "ES", "https://www.fcbadalonawomen.com"),
    ("DUX Logroño", "ES", "https://www.duxlogrono.com"), ("Zaragoza CFF", "ES", "https://www.zaragozacff.com"),
    ("CE Europa Femení", "ES", "https://www.ceeuropa.cat"), ("UD Tenerife (Costa Adeje)", "ES", "https://www.udtenerife.com"),
    ("CP Cacereño Femenino", "ES", "https://www.cacerenofemenino.com"), ("AEM Lleida", "ES", "https://www.aemlleida.cat"),
    # Fransa
    ("FC Fleury 91", "FR", "https://www.fcfleury91.fr"), ("ASJ Soyaux-Charente", "FR", "https://www.asjsoyaux.fr"),
    ("FF Issy", "FR", "https://www.ffissy.fr"), ("FF Yzeure Allier Auvergne", "FR", "https://www.footfemininyzeure.fr"),
    ("Thonon Évian Grand Genève FC", "FR", "https://www.thononeviangrandgenevefc.fr"), ("Dijon FCO", "FR", "https://www.dfco.fr"),
    ("Le Havre AC", "FR", "https://www.hac-foot.com"), ("Rodez AF", "FR", "https://www.rodezaveyronfootball.com"),
    # İskoçya / İngiltere / İrlanda / Galler / K. İrlanda
    ("Glasgow City FC", "SCO", "https://www.glasgowcityfc.co.uk"), ("Spartans Women", "SCO", "https://www.spartansfc.com"),
    ("Hibernian Women", "SCO", "https://www.hibernianfc.co.uk"), ("Partick Thistle Women", "SCO", "https://ptfc.co.uk"),
    ("Montrose FC Women", "SCO", "https://www.montrosefc.co.uk"), ("Motherwell Women", "SCO", "https://www.motherwellfc.co.uk"),
    ("London City Lionesses", "ENG", "https://www.londoncitylionesses.com"), ("Lewes FC", "ENG", "https://www.lewesfc.com"),
    ("Charlton Athletic Women", "ENG", "https://www.charltonafc.com"), ("Ipswich Town Women", "ENG", "https://www.itfc.co.uk"),
    ("Hashtag United Women", "ENG", "https://www.hashtagunited.co.uk"), ("Rugby Borough WFC", "ENG", "https://www.rugbyborough.com"),
    ("Shelbourne FC", "IE", "https://www.shelbournefc.ie"), ("Peamount United", "IE", "https://www.peamountunited.com"),
    ("Wexford FC", "IE", "https://www.wexfordfc.ie"), ("DLR Waves", "IE", "https://www.dlrwaves.com"),
    ("Treaty United", "IE", "https://www.treatyunitedfc.com"), ("Galway United", "IE", "https://www.galwayunitedfc.ie"),
    ("Cliftonville Ladies", "NIR", "https://www.cliftonvillefc.net"), ("Sion Swifts Ladies", "NIR", "https://www.sionswifts.com"),
    ("Cardiff City FC Women", "WAL", "https://www.cardiffcityfc.co.uk"), ("Swansea City Women", "WAL", "https://www.swanseacity.com"),
    # Orta / Doğu Avrupa
    ("Medyk Konin", "PL", "https://www.medykkonin.pl"), ("UKS SMS Łódź", "PL", "https://www.ukssmslodz.pl"),
    ("GKS Katowice Kobiet", "PL", "https://www.gkskatowice.eu"), ("Pogoń Szczecin Kobiet", "PL", "https://www.pogonszczecin.pl"),
    ("Rekord Bielsko-Biała", "PL", "https://www.rekord.com.pl"), ("AP Orlen Gdańsk", "PL", "https://www.apgdansk.pl"),
    ("1. FC Slovácko ženy", "CZ", "https://www.fcslovacko.cz"), ("Lokomotiva Brno HH", "CZ", "https://www.lokomotivabrnohh.cz"),
    ("Haladás Viktória", "HU", "https://www.viktoriafc.hu"), ("Astra HFC", "HU", "https://www.astrahfc.hu"),
    ("MTK Hungária Női", "HU", "https://www.mtkbudapest.hu"), ("Győri ETO Női", "HU", "https://www.eto.hu"),
    ("Olimpia Cluj", "RO", "https://www.olimpiacluj.ro"), ("Vasas Femina Odorhei", "RO", "https://www.vasasfemina.ro"),
    ("ŽNK Osijek", "HR", "https://www.znk-osijek.hr"), ("ŽNK Split", "HR", "https://www.znk-split.hr"),
    ("ŽNK Olimpija Ljubljana", "SI", "https://www.znkolimpija.si"), ("ŽFK Crvena zvezda", "RS", "https://www.zfkcrvenazvezda.rs"),
    ("Gintra", "LT", "https://www.gintra.lt"), ("SFK Rīga", "LV", "https://www.sfkriga.lv"),
    ("Saku Sporting", "EE", "https://www.sakusporting.ee"), ("BIIK-Shymkent", "KZ", "https://www.biik.kz"),
    # Güney Avrupa
    ("Clube de Albergaria", "PT", "https://www.clubealbergaria.pt"), ("Länk FC Vilaverdense", "PT", "https://www.lankfcvilaverdense.pt"),
    ("Atlético Ouriense", "PT", "https://www.atleticoouriense.pt"), ("FC Famalicão Feminino", "PT", "https://www.fcfamalicao.pt"),
    ("Apollon Ladies", "CY", "https://www.apollonladies.com"), ("Lakatamia FC", "CY", "https://www.lakatamiafc.com"),
    ("Swieqi United", "MT", "https://www.swieqiunited.com"), ("Birkirkara FC", "MT", "https://www.birkirkarafc.com"),
    ("REA Rethymno", "GR", "https://www.reafc.gr"), ("PAOK Women", "GR", "https://www.paokfc.gr"),
]

BAG_ANAHTAR = re.compile(
    r"kontakt|contact|contatt|contacto|contato|kapcsolat|yhteys|samband|hafa|staff|personal|personale|"
    r"organi[sz]|ansatt|medewerk|ledelse|styre|bestuur|vorstand|verein|club|klub|about|om-|ueber|uber-uns|"
    r"dam|kvinn|kvenn|naiset|frauen|vrouwen|f[eé]min|femen|femmin|women|ladies|zeny|ženy|kobiet|noi|női|sport",
    re.I)
KADIN = re.compile(r"\bdam|kvinn|kvenn|nais|frauen|vrouwen|f[eé]min|femen|femmin|women|ladies|[zž]eny|[zż]e[nń]sk|kobiet|n[oő]i\b|girls", re.I)
ROL = re.compile(r"sport|direct|direkt|manager|scout|recruit|rekrut|tr[aä]n|trener|coach|tekni|technic|general|ceo|"
                 r"toimitusjohtaja|daglig leder|klubbchef|lagledare|sekret|secretar|president|puheenjohtaja|"
                 r"gesch[aä]ftsf|leiter|leiding|voorzitter|responsable|responsabile|respons[aá]vel|head of|football", re.I)
ATLA = re.compile(r"\.(png|jpe?g|gif|svg|webp|css|js)$|sentry|wixpress|example\.|domain\.|email\.com$|@2x|u003e", re.I)
EPOSTA = re.compile(r"[A-Za-z0-9._%+\-]{2,40}@[A-Za-z0-9.\-]{2,40}\.[A-Za-z]{2,10}")


def getir(url):
    try:
        r = requests.get(url, headers=H, timeout=ZAMAN, allow_redirects=True)
        if r.status_code == 200 and "html" in r.headers.get("content-type", "html"):
            r.encoding = r.apparent_encoding or r.encoding
            return r.url, r.text
    except Exception:
        pass
    return None, None


def epostalar(ham_html):
    metin = html.unescape(ham_html)
    metin = re.sub(r"\s*(\[at\]|\(at\)|\{at\}|\[ät\]|\(a\))\s*", "@", metin, flags=re.I)
    metin = re.sub(r"\s*(\[dot\]|\(dot\)|\[punkt\]|\(punkt\))\s*", ".", metin, flags=re.I)
    duz = BeautifulSoup(metin, "html.parser").get_text(" ", strip=True)
    out = {}
    for m in EPOSTA.finditer(duz):
        e = m.group().strip(".").lower()
        if ATLA.search(e):
            continue
        baglam = re.sub(r"\s+", " ", duz[max(0, m.start() - 90):m.end() + 40]).strip()
        out.setdefault(e, baglam)
    for e in re.findall(r"mailto:([^\"'?> ]+)", metin):
        e = e.strip(".").lower()
        if EPOSTA.fullmatch(e) and not ATLA.search(e):
            out.setdefault(e, "")
    return out


def kulup_tara(kayit):
    ad, ulke, kok = kayit
    son_url, ana = getir(kok)
    if not ana and kok.startswith("https://www."):
        son_url, ana = getir(kok.replace("https://www.", "https://"))
    if not ana:
        return {"kulup": ad, "ulke": ulke, "site": kok, "durum": "ulasilamadi", "adresler": []}
    alan = urlparse(son_url).netloc.replace("www.", "")
    sayfalar, bulunan = [(son_url, ana)], {}
    adaylar = []
    for a in BeautifulSoup(ana, "html.parser").find_all("a", href=True):
        tam = urljoin(son_url, a["href"]).split("#")[0]
        if urlparse(tam).netloc.replace("www.", "") != alan or tam == son_url:
            continue
        iz = (a.get_text(" ", strip=True) + " " + urlparse(tam).path)[:120]
        if BAG_ANAHTAR.search(iz) and tam not in adaylar:
            adaylar.append(tam)
    # önce iletişim/personel/kadın sayfaları
    adaylar.sort(key=lambda u: (0 if re.search(r"kontakt|contact|contatt|contacto|contato|kapcsolat|yhteys|staff|personal|organi", u, re.I)
                                else 1 if KADIN.search(u) else 2, len(u)))
    for u in adaylar[:SAYFA_SINIRI - 1]:
        su, sh = getir(u)
        if sh:
            sayfalar.append((su, sh))
    for su, sh in sayfalar:
        for e, baglam in epostalar(sh).items():
            puan = (3 if KADIN.search(baglam + " " + su) else 0) + (2 if ROL.search(baglam) else 0) \
                + (1 if e.split("@")[1].endswith(alan.split(".")[-2] + "." + alan.split(".")[-1]) else 0)
            if e not in bulunan or puan > bulunan[e]["puan"]:
                bulunan[e] = {"eposta": e, "puan": puan, "baglam": baglam[:170], "sayfa": su}
    return {"kulup": ad, "ulke": ulke, "site": son_url, "durum": "ok", "sayfa_sayisi": len(sayfalar),
            "adresler": sorted(bulunan.values(), key=lambda x: -x["puan"])}


def main():
    ulkeler = next((a.split("=")[1].split(",") for a in sys.argv if a.startswith("--ulke=")), None)
    liste = [k for k in KULUPLER if not ulkeler or k[1] in ulkeler]
    with cf.ThreadPoolExecutor(max_workers=10) as havuz:
        sonuc = list(havuz.map(kulup_tara, liste))
    json.dump(sonuc, open(KOK / "kulup_iletisim_ham.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = [s for s in sonuc if s["durum"] == "ok"]
    print(f"{len(sonuc)} kulüp · ulaşılan {len(ok)} · adres bulunan {sum(1 for s in ok if s['adresler'])} · "
          f"toplam adres {sum(len(s['adresler']) for s in ok)}")
    print("ulaşılamayan:", ", ".join(s["kulup"] for s in sonuc if s["durum"] != "ok"))
    print("adres çıkmayan:", ", ".join(s["kulup"] for s in ok if not s["adresler"]))


if __name__ == "__main__":
    main()
