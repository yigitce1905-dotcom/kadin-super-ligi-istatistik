# -*- coding: utf-8 -*-
"""FM26 (Genie/plugin) 6 nitelik CSV'sini birleştir -> harf -> Sco 🌍 sheet.
Aralık (14-20) -> orta nokta. 1-20 -> *5 (0-100). SADECE değerlendirilmemişe yazar.
Kullanım: python fm_sheet_yaz.py --kuru   |   python fm_sheet_yaz.py --yaz
"""
import csv, json, re, sys, unicodedata, glob, os
sys.stdout.reconfigure(encoding="utf-8")

DIR  = r"C:\Users\MSI\Documents\Sports Interactive\Football Manager 26\FM26PlayerExport by vinteset\Exports CSV"
POOL = r"C:\Users\MSI\Desktop\tff_kadin_ligi\scout_kadro_raporlar.json"

BANT = [("A+",99,100),("AA",95,98),("AB",85,94),("BB",75,84),("BC",65,74),
        ("CC",55,64),("CD",45,54),("DD",35,44),("DE",25,34),("EE",15,24),("FF",0,14)]
def harf(n):
    try: n=int(round(float(n)))
    except: return ""
    for h,lo,hi in BANT:
        if lo<=n<=hi: return h
    return "FF" if n<0 else "A+"

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",s)).strip()

def deger(v):
    """'17' -> 17.0 ; '14-20' -> 17.0 ; boş/'-' -> None"""
    v=str(v or "").strip()
    if not v or v=="-": return None
    m=re.match(r"^(\d+)\s*-\s*(\d+)$",v)
    if m: return (int(m.group(1))+int(m.group(2)))/2
    if v.isdigit(): return float(v)
    return None

# FM export TR adı -> sheet KOL TR adı
FM2SHEET={
 "Bitiricilik":"Bitiricilik","Teknik":"Top Tekniği","Penaltı Kullanma":"Penaltı Vuruşu",
 "Markaj":"Markaj","Top Kapma":"Top Kapma","Uzun Taç":"Uzun Taç",
 "Serbest Vuruş Kullanma":"Duran Top","İlk Kontrol":"İlk Kontrol","Kafa Vuruşu":"Kafa Vuruşu",
 "Orta Yapma":"Orta Yapma","Pas":"Kısa Pas","Dripling":"Top Sürme","Uzaktan Şut":"Uzaktan Şut",
 "Agresiflik":"Agresiflik","Cesaret":"Cesaret","Karar Alma":"Karar Alma","Kararlılık":"Kararlılık",
 "Konsantrasyon":"Konsantrasyon","Liderlik":"Liderlik","Önsezi":"Önsezi","Mevki Alma":"Konumlanma",
 "Soğukkanlılık":"Soğukkanlılık","İşbirliği":"Takım Oyunu","Topsuz Alan":"Topsuz Alan","Vizyon":"Görüş",
 "Hızlanma":"Hızlanma","Çeviklik":"Çeviklik","Denge":"Denge","Zıplama":"Zıplama",
 "Vücut Zindeliği":"Zindelik","Hız":"Sürat","Dayanıklılık":"Dayanıklılık","Güç":"Güç",
 "Çalışkanlık":"Çalışkanlık",
}
GRUP={"beceri":["Bitiricilik","Top Tekniği","Penaltı Vuruşu","Markaj","Top Kapma","Uzun Taç",
        "Duran Top","İlk Kontrol","Kafa Vuruşu","Orta Yapma","Kısa Pas","Top Sürme","Uzaktan Şut"],
      "beseri":["Agresiflik","Cesaret","Karar Alma","Kararlılık","Konsantrasyon","Liderlik","Önsezi",
        "Konumlanma","Soğukkanlılık","Takım Oyunu","Topsuz Alan","Görüş"],
      "fiziki":["Hızlanma","Çeviklik","Denge","Zıplama","Zindelik","Sürat","Dayanıklılık","Güç"],
      "sahsi":["Çalışkanlık"]}

NONATTR={"Bil","Oyuncu","Piyasa Değeri","Tavsiye"}
files=sorted(glob.glob(os.path.join(DIR,"moneyball_export_2026071*_00*.csv")))
files=[f for f in files if os.path.basename(f)>="moneyball_export_20260710_003517"]

players={}
for f in files:
    with open(f,encoding="utf-8-sig") as fh:
        rd=csv.reader(fh,delimiter=";"); hdr=next(rd)
        acols=[(i,h) for i,h in enumerate(hdr) if h not in NONATTR and h]
        ni=hdr.index("Oyuncu")
        for r in rd:
            if len(r)<=ni: continue
            nn=norm(r[ni])
            if not nn: continue
            d=players.setdefault(nn,{"_ad":r[ni]})
            for i,h in acols:
                if i<len(r):
                    val=deger(r[i])
                    if val is not None and h in FM2SHEET:
                        d[FM2SHEET[h]]=val   # sheet adıyla sakla

def grade_card(d):
    out={"beceri":{},"beseri":{},"fiziki":{},"sahsi":{}}
    for g,adlar in GRUP.items():
        for ad in adlar:
            if ad in d:
                out[g][ad]=harf(min(100,d[ad]*5))
    makro={}
    for g,adlar in GRUP.items():
        vals=[d[ad] for ad in adlar if ad in d]
        makro[g]=harf(min(100,(sum(vals)/len(vals))*5)) if vals else ""
    allv=[d[ad] for adlar in GRUP.values() for ad in adlar if ad in d]
    nihai=harf(min(100,(sum(allv)/len(allv))*5)) if allv else ""
    return out,makro,nihai,len(allv)

pool=json.load(open(POOL,encoding="utf-8"))
degvar=[i for i in pool if not pool[i].get("degerlendirildi")]
hedef=[i for i in degvar if norm(i) in players]

MINATTR=20
yeterli=[]
for i in hedef:
    d=players[norm(i)]
    _,_,_,n=grade_card(d)
    if n>=MINATTR: yeterli.append((i,n))

print(f"Değerlendirilmemiş havuz: {len(degvar)}")
print(f"  FM'de eşleşen: {len(hedef)}")
print(f"  ≥{MINATTR} nitelik dolu (yazılabilir): {len(yeterli)}")

print("\n=== ÖRNEK 3 OYUNCU GRADE KARTI ===")
for i,n in yeterli[:3]:
    d=players[norm(i)]
    out,makro,nihai,cnt=grade_card(d)
    print(f"\n### {i}  ({cnt} nitelik)  NİHAİ={nihai}  makro={makro}")
    print(f"  BECERİ: "+", ".join(f"{k}:{v}" for k,v in out['beceri'].items()))
    print(f"  BEŞERİ: "+", ".join(f"{k}:{v}" for k,v in out['beseri'].items()))
    print(f"  FİZİKİ: "+", ".join(f"{k}:{v}" for k,v in out['fiziki'].items()))
