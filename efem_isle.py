# -*- coding: utf-8 -*-
"""
efem.club oyuncu linkini bizim scout_kadro_raporlar.json formatına işler.
FM 0-99 nitelik -> harf bant (aşağıdaki BANT) -> beceri/beşeri/fiziki/şahsi.

Kullanım:
    python efem_isle.py <efem_url> [<efem_url> ...]      # işle + yaz
    python efem_isle.py --kuru <efem_url>                # sadece önizleme
    python efem_isle.py --test                           # ağsız bant/eşleme testi

Not: SADECE değerlendirilmemiş oyuncuya yazar (Baran'ın manuel notunu ezmez).
Kaynak şeffaflığı: kayda "kaynak":"efem-fm" eklenir (insan scout'u değil).
"""
import re, sys, json, time, unicodedata
from pathlib import Path

CIKTI = Path(__file__).parent / "scout_kadro_raporlar.json"

# --- Kullanıcının harf bant tablosu (0-99) ---
BANT = [("A+",99,100),("AA",95,98),("AB",85,94),("BB",75,84),("BC",65,74),
        ("CC",55,64),("CD",45,54),("DD",35,44),("DE",25,34),("EE",15,24),("FF",0,14)]
def harf(n):
    try: n = int(round(float(n)))
    except Exception: return ""
    for h, lo, hi in BANT:
        if lo <= n <= hi: return h
    return "FF" if n < 0 else "A+"

# --- FM (efem küçük-harf anahtar) -> bizim TR nitelik adı ---
BECERI = {"finishing":"Bitiricilik","technique":"Top Tekniği","penalties":"Penaltı Vuruşu",
    "marking":"Markaj","tackling":"Top Kapma","longThrow":"Uzun Taç","freekicks":"Duran Top",
    "firstTouch":"İlk Kontrol","heading":"Kafa Vuruşu","crossing":"Orta Yapma","passing":"Kısa Pas",
    "dribbling":"Top Sürme","longshots":"Uzaktan Şut"}
BESERI = {"aggression":"Agresiflik","bravery":"Cesaret","decisions":"Karar Alma",
    "determination":"Kararlılık","concentration":"Konsantrasyon","leadership":"Liderlik",
    "anticipation":"Önsezi","positioning":"Konumlanma","composure":"Soğukkanlılık",
    "teamwork":"Takım Oyunu","offTheBall":"Topsuz Alan","vision":"Görüş"}
FIZIKI = {"agility":"Çeviklik","stamina":"Dayanıklılık","balance":"Denge","strength":"Güç",
    "pace":"Sürat","acceleration":"Hızlanma","naturalFitness":"Zindelik","jumpingReach":"Zıplama",
    "_zayifAyak":"Zayıf Ayak"}
SAHSI  = {"injuryResistance":"Sakatlanma Direnci","sportsmanship":"Sportmenlik",
    "professionalism":"Profesyonellik","loyalty":"Sadakat","pressure":"Baskıya Dayanıklılık",
    "consistency":"Süreklilik","workrate":"Çalışkanlık","adaptability":"Uyumluluk"}
# Kaleci nitelikleri (bizim KALECİ YETKİNLİKLERİ ile eşleşir; şimdilik not/GK için)
GK = {"aerialReach","commandOfArea","communication","eccentricity","handling","kicking",
      "oneVsOne","reflexes","rushingOut","punching","throwing"}

UA = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

def cek(url, deneme=3):
    import requests
    son = None
    for i in range(deneme):
        try:
            r = requests.get(url, headers=UA, timeout=25); r.raise_for_status()
            return r.text
        except Exception as e:
            son = e; time.sleep(1.5)
    raise son

def coz(raw):
    """efem ham HTML -> {meta, sayisal nitelikler}."""
    u = raw.encode().decode("unicode_escape", errors="ignore")
    def b(p, d=""):
        m = re.search(p, u); return m.group(1) if m else d
    meta = {"isim":b(r'"name":"([^"]+)"'),"gender":b(r'"gender":"([^"]+)"'),
        "nationality":b(r'"nationality":"([^"]+)"'),"club":b(r'"club":"([^"]*)"'),
        "contract":b(r'"contract[^"]*":"([^"]+)"'),"value":b(r'"(?:value|marketValue)":"?€?([^",]+)"?'),
        "CA":b(r'"currentAbility":(\d+)'),"PA":b(r'"(?:predictedP|p)otentialAbility":(\d+)')}
    tum = {}
    for grup in (BECERI,BESERI,FIZIKI,SAHSI):
        for fm in grup:
            m = re.search(r'"%s":(\d{1,3})' % fm, u)
            if m: tum[fm] = int(m.group(1))
    # Zayıf Ayak: efem leftFoot/rightFoot (1-20) -> zayıf ayak = min, 0-99'a ölçekle
    lf = re.search(r'"leftFoot":(\d{1,3})', u); rf = re.search(r'"rightFoot":(\d{1,3})', u)
    if lf and rf:
        tum["_zayifAyak"] = round(min(int(lf.group(1)), int(rf.group(1))) / 20 * 99)
    gk = {}
    for fm in GK:
        m = re.search(r'"%s":(\d{1,3})' % fm, u)
        if m: gk[fm] = int(m.group(1))
    return meta, tum, gk

def kayit_yap(meta, tum, gk):
    def grup_harf(eslem):
        return {ad: harf(tum[fm]) for fm, ad in eslem.items() if fm in tum}
    beceri, beseri, fiziki, sahsi = (grup_harf(BECERI), grup_harf(BESERI),
                                     grup_harf(FIZIKI), grup_harf(SAHSI))
    def makro(eslem):
        vals = [tum[fm] for fm in eslem if fm in tum]
        return harf(sum(vals)/len(vals)) if vals else ""
    nihai = harf(meta["CA"]) if meta.get("CA") else ""
    gk_not = (" | Kaleci(0-99): " + ", ".join(f"{k}:{v}" for k,v in gk.items())) if gk else ""
    return {
        "beceri":beceri,"beseri":beseri,"fiziki":fiziki,"sahsi":sahsi,
        "makro":{"beceri":makro(BECERI),"beseri":makro(BESERI),
                 "fiziki":makro(FIZIKI),"sahsi":makro(SAHSI)},
        "nihai":nihai,"degerlendirildi":bool(beceri or beseri or fiziki),
        "kaynak":"efem-fm","scout_notu":("Otomatik (efem/FM)"+gk_not).strip(),
    }

def isle(urls, kuru=False):
    d = json.load(open(CIKTI, encoding="utf-8"))
    def norm(s): return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9 ]"," ",
        unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower())).strip()
    isim2key = {norm(k): k for k in d}
    for url in urls:
        raw = cek(url)
        meta, tum, gk = coz(raw)
        yeni = kayit_yap(meta, tum, gk)
        key = isim2key.get(norm(meta["isim"]))
        print(f"\n=== {meta['isim']} ({meta.get('nationality')}) ===")
        print(f"  havuzda: {key or 'YOK'} | nitelik sayısı: {len(tum)} | kaleci-attr: {len(gk)}")
        print(f"  nihai={yeni['nihai']} makro={yeni['makro']}")
        print(f"  beceri={yeni['beceri']}")
        print(f"  beseri={yeni['beseri']}")
        print(f"  fiziki={yeni['fiziki']}")
        print(f"  sahsi={yeni['sahsi']}")
        if not key:
            print("  -> havuzda yok, atlandı (şimdilik sadece mevcut oyuncuları zenginleştir)"); continue
        if d[key].get("degerlendirildi"):
            print("  -> zaten DEĞERLENDİRİLMİŞ (Baran notu), DOKUNULMADI"); continue
        if not kuru:
            d[key].update(yeni)
            if meta.get("contract") and not d[key].get("sozlesme"):
                pass  # istenirse sözleşme/değer de güncellenebilir
            print("  -> YAZILDI")
    if not kuru:
        json.dump(d, open(CIKTI,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print("\n[OK] scout_kadro_raporlar.json güncellendi.")

def test():
    print("BANT testi:", [(n, harf(n)) for n in (99,94,84,74,68,64,50,33,3,0)])
    print("Eşleme adedi: beceri=%d beseri=%d fiziki=%d sahsi=%d" %
          (len(BECERI),len(BESERI),len(FIZIKI),len(SAHSI)))
    ornek = {"finishing":68,"composure":80,"agility":72,"professionalism":90,"passing":55}
    r = kayit_yap({"CA":"82"}, ornek, {})
    print("Örnek kayıt:", json.dumps(r, ensure_ascii=False))

if __name__ == "__main__":
    a = sys.argv[1:]
    if "--test" in a: test()
    else:
        kuru = "--kuru" in a
        urls = [x for x in a if x.startswith("http")]
        if not urls: print("Kullanım: python efem_isle.py [--kuru] <efem_url> ..."); sys.exit(1)
        isle(urls, kuru=kuru)
