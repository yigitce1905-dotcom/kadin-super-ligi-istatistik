# -*- coding: utf-8 -*-
import csv, json, re, sys, unicodedata, glob, os, time
sys.stdout.reconfigure(encoding="utf-8")
import gspread

DIR  = r"C:\Users\MSI\Documents\Sports Interactive\Football Manager 26\FM26PlayerExport by vinteset\Exports CSV"
POOL = r"C:\Users\MSI\Desktop\tff_kadin_ligi\scout_kadro_raporlar.json"
CREDS= r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID="1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"; GID=1707810792

BANT=[("A+",99,100),("AA",95,98),("AB",85,94),("BB",75,84),("BC",65,74),
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
    v=str(v or "").strip()
    if not v or v=="-": return None
    m=re.match(r"^(\d+)\s*-\s*(\d+)$",v)
    if m: return (int(m.group(1))+int(m.group(2)))/2
    if v.isdigit(): return float(v)
    return None

FM2SHEET={"Bitiricilik":"Bitiricilik","Teknik":"Top Tekniği","Penaltı Kullanma":"Penaltı Vuruşu",
 "Markaj":"Markaj","Top Kapma":"Top Kapma","Uzun Taç":"Uzun Taç","Serbest Vuruş Kullanma":"Duran Top",
 "İlk Kontrol":"İlk Kontrol","Kafa Vuruşu":"Kafa Vuruşu","Orta Yapma":"Orta Yapma","Pas":"Kısa Pas",
 "Dripling":"Top Sürme","Uzaktan Şut":"Uzaktan Şut","Agresiflik":"Agresiflik","Cesaret":"Cesaret",
 "Karar Alma":"Karar Alma","Kararlılık":"Kararlılık","Konsantrasyon":"Konsantrasyon","Liderlik":"Liderlik",
 "Önsezi":"Önsezi","Mevki Alma":"Konumlanma","Soğukkanlılık":"Soğukkanlılık","İşbirliği":"Takım Oyunu",
 "Topsuz Alan":"Topsuz Alan","Vizyon":"Görüş","Hızlanma":"Hızlanma","Çeviklik":"Çeviklik","Denge":"Denge",
 "Zıplama":"Zıplama","Vücut Zindeliği":"Zindelik","Hız":"Sürat","Dayanıklılık":"Dayanıklılık","Güç":"Güç",
 "Çalışkanlık":"Çalışkanlık"}
GRUP={"beceri":["Bitiricilik","Top Tekniği","Penaltı Vuruşu","Markaj","Top Kapma","Uzun Taç","Duran Top",
        "İlk Kontrol","Kafa Vuruşu","Orta Yapma","Kısa Pas","Top Sürme","Uzaktan Şut"],
      "beseri":["Agresiflik","Cesaret","Karar Alma","Kararlılık","Konsantrasyon","Liderlik","Önsezi",
        "Konumlanma","Soğukkanlılık","Takım Oyunu","Topsuz Alan","Görüş"],
      "fiziki":["Hızlanma","Çeviklik","Denge","Zıplama","Zindelik","Sürat","Dayanıklılık","Güç"],
      "sahsi":["Çalışkanlık"]}
KOL={"Bitiricilik":19,"Top Tekniği":20,"Penaltı Vuruşu":21,"Markaj":22,"Top Kapma":23,"Uzun Taç":24,
 "Duran Top":25,"İlk Kontrol":26,"Kafa Vuruşu":27,"Orta Yapma":28,"Kısa Pas":29,"Top Sürme":31,
 "Uzaktan Şut":32,"Agresiflik":34,"Cesaret":35,"Karar Alma":36,"Kararlılık":37,"Konsantrasyon":38,
 "Liderlik":39,"Önsezi":40,"Konumlanma":41,"Soğukkanlılık":42,"Takım Oyunu":43,"Topsuz Alan":44,"Görüş":45,
 "Çeviklik":47,"Dayanıklılık":48,"Denge":49,"Güç":50,"Sürat":51,"Hızlanma":52,"Zindelik":54,"Zıplama":55,
 "Çalışkanlık":65}
MAKRO_KOL={"beceri":33,"beseri":46,"fiziki":57,"sahsi":66}; NIHAI_KOL=99

# --- merge ---
NONATTR={"Bil","Oyuncu","Piyasa Değeri","Tavsiye"}
files=sorted(glob.glob(os.path.join(DIR,"moneyball_export_2026071*_00*.csv")))
files=[f for f in files if os.path.basename(f)>="moneyball_export_20260710_003517"]
players={}
for f in files:
    with open(f,encoding="utf-8-sig") as fh:
        rd=csv.reader(fh,delimiter=";"); hdr=next(rd)
        acols=[(i,h) for i,h in enumerate(hdr) if h not in NONATTR and h]; ni=hdr.index("Oyuncu")
        for r in rd:
            if len(r)<=ni: continue
            nn=norm(r[ni])
            if not nn: continue
            d=players.setdefault(nn,{})
            for i,h in acols:
                if i<len(r):
                    val=deger(r[i])
                    if val is not None and h in FM2SHEET: d[FM2SHEET[h]]=val

def card(d):
    out={g:{} for g in GRUP}; makro={}
    for g,adlar in GRUP.items():
        for ad in adlar:
            if ad in d: out[g][ad]=harf(min(100,d[ad]*5))
        vals=[d[ad] for ad in adlar if ad in d]
        makro[g]=harf(min(100,(sum(vals)/len(vals))*5)) if vals else ""
    allv=[d[ad] for adlar in GRUP.values() for ad in adlar if ad in d]
    nihai=harf(min(100,(sum(allv)/len(allv))*5)) if allv else ""
    return out,makro,nihai,len(allv)

pool=json.load(open(POOL,encoding="utf-8"))
degvar=[i for i in pool if not pool[i].get("degerlendirildi")]
hedef=[i for i in degvar if norm(i) in players and card(players[norm(i)])[3]>=20]
print(f"Yazılacak hedef: {len(hedef)}")

gc=gspread.service_account(filename=CREDS)
ws=gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID)
hdr2=ws.row_values(2)
assert "Bitiricilik" in hdr2[19] and "Agresiflik" in hdr2[34] and "Çalışkanlık" in hdr2[65], "KOLON KAYMASI — İPTAL"
isimler=ws.col_values(2)
nmap={}
for idx,v in enumerate(isimler):
    nmap.setdefault(norm(v), idx+1)

cells=[]; yazilan=[]; bulunamadi=[]
for i in hedef:
    row=nmap.get(norm(i))
    if not row: bulunamadi.append(i); continue
    out,makro,nihai,cnt=card(players[norm(i)])
    for g in GRUP:
        for ad,notu in out[g].items():
            if ad in KOL and notu: cells.append(gspread.Cell(row,KOL[ad]+1,notu))
    for g,ki in MAKRO_KOL.items():
        if makro.get(g): cells.append(gspread.Cell(row,ki+1,makro[g]))
    if nihai: cells.append(gspread.Cell(row,NIHAI_KOL+1,nihai))
    yazilan.append(i)

print(f"Sheet'te bulunan: {len(yazilan)} | bulunamadı: {len(bulunamadi)} | toplam hücre: {len(cells)}")
if bulunamadi[:10]: print("Bulunamayanlar (ilk 10):", bulunamadi[:10])

# chunk yaz
CH=1500
for k in range(0,len(cells),CH):
    ws.update_cells(cells[k:k+CH]); print(f"  ...{min(k+CH,len(cells))}/{len(cells)} hücre yazıldı"); time.sleep(1)
print(f"\n✓ {len(yazilan)} oyuncu, {len(cells)} hücre YAZILDI")
open("_fm_yazilan.txt","w",encoding="utf-8").write("\n".join(yazilan))
