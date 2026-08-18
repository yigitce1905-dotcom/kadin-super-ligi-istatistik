# -*- coding: utf-8 -*-
"""FM26 kaleci niteliklerini Sco 🌍 sheet'in KALECİ bloğuna yazar.
Hedef: dün FM ile yazılan 18 kaleci (+ GK verisi dolu, değerlendirilmemiş ek kaleciler).
Kullanım: python fm_gk_yaz.py --kuru | --yaz
"""
import csv, json, re, sys, unicodedata, glob, os, time
sys.stdout.reconfigure(encoding="utf-8")

# DNS bazen googleapis için sadece IPv6 dönüyor / zaman aşımına uğruyor (VPN).
# Çözülemezse Google GFE IPv4'üne düş (SNI sayesinde doğru sertifika gelir).
import socket
_gai = socket.getaddrinfo
def _gai_yedek(host, port, *a, **k):
    try:
        return _gai(host, port, *a, **k)
    except socket.gaierror:
        if isinstance(host, str) and ("googleapis.com" in host or "google.com" in host):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.251.127.95", port))]
        raise
socket.getaddrinfo = _gai_yedek

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

# 6 CSV'yi birleştir (tüm görünümler — GK + teknik değerler lazım)
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
                    if val is not None: d[h]=val

def ort(d,*adlar):
    v=[d[a] for a in adlar if a in d]
    return sum(v)/len(v) if v else None

# sheet GK sütun adı -> FM değeri (hepsi 1-20)
def gk_kart(d):
    out={}
    M={ "Elle Kontrol - Sahiplenme": d.get("Elle Kontrol"),
        "Ayakla Kontrol - İlk Temas": d.get("İlk Kontrol"),
        "Top Tekniği": d.get("Teknik"),
        "Alan Hakimiyeti": d.get("Bölge Hakimiyeti"),
        "Çizgi Hakimiyeti": ort(d,"Refleksler","Birebir"),
        "Hava Hakimiyeti": d.get("Hava Topları"),
        "Yan Top Hakimiyeti": ort(d,"Hava Topları","Bölge Hakimiyeti"),
        "Elle Oyun Kurma": d.get("Elle Oyun Başlatma"),
        "Ayak ile Oyun Kurma - Kısa": d.get("Pas"),
        "Degaj ile Oyun Kurma - Uzun": d.get("Degaj"),
        "Kaleden Ani Çıkış": d.get("Ani Çıkış Eğilimi"),
        "Yumruklama Kabiliyeti": d.get("Yumruklama"),
        "İletişim": d.get("İletişim"),
        "Kaleci Dışı Meziyetler": ort(d,"Pas","Teknik","İlk Kontrol","Dripling"),
      }
    for ad,v in M.items():
        if v is not None: out[ad]=harf(min(100,v*5))
    # KALECİ makro + kaleci-nihai: çekirdek GK nitelik ortalaması
    cekirdek=ort(d,"Elle Kontrol","Refleksler","Birebir","Hava Topları","Bölge Hakimiyeti",
                   "Degaj","Elle Oyun Başlatma","İletişim","Ani Çıkış Eğilimi","Yumruklama")
    makro=harf(min(100,cekirdek*5)) if cekirdek is not None else ""
    return out,makro

pool=json.load(open(POOL,encoding="utf-8"))
yaz=set(open("_fm_yazilan.txt",encoding="utf-8").read().splitlines())
def gk_mi(i):
    r=pool.get(i,{})
    return r.get("bolge")=="Kaleci" or "GK" in (r.get("mevki") or [])

hedef=[i for i in yaz if gk_mi(i) and norm(i) in players]
# ek: yazılmamış (dün <20 outfield idi) değerlendirilmemiş GK'ler, GK verisi doluysa
ek=[i for i in pool if i not in yaz and not pool[i].get("degerlendirildi")
    and gk_mi(i) and norm(i) in players
    and len(gk_kart(players[norm(i)])[0])>=10]
print(f"Dün yazılan kaleci: {len(hedef)} | Ek yazılabilir kaleci: {len(ek)}")
for i in ek: print("  EK:", i)

ornek=hedef[0] if hedef else None
if ornek:
    out,makro=gk_kart(players[norm(ornek)])
    print(f"\n=== ÖRNEK: {ornek} | KALECİ makro={makro} ===")
    for k,v in out.items(): print(f"  {k:28}: {v}")

if "--yaz" not in sys.argv:
    print("\n[KURU] yazılmadı."); sys.exit(0)

import gspread
gc=gspread.service_account(filename=CREDS)
ws=gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID)
hdr2=ws.row_values(2)
# GK sütun indeksleri (0-based) başlık adıyla
GKCOL={}
for j,h in enumerate(hdr2):
    hs=h.strip()
    if hs in ("Elle Kontrol - Sahiplenme","Ayakla Kontrol - İlk Temas","Alan Hakimiyeti",
              "Çizgi Hakimiyeti","Hava Hakimiyeti","Yan Top Hakimiyeti","Elle Oyun Kurma",
              "Ayak ile Oyun Kurma - Kısa","Degaj ile Oyun Kurma - Uzun","Kaleden Ani Çıkış",
              "Yumruklama Kabiliyeti","İletişim","Kaleci Dışı Meziyetler"):
        GKCOL[hs]=j
    elif hs=="Top Tekniği" and j>60:   # GK bloğundaki ikinci "Top Tekniği" (beceri'deki 20. kolon değil)
        GKCOL["Top Tekniği"]=j
    elif hs.startswith("KALECİ") and "_MAKRO" not in GKCOL: GKCOL["_MAKRO"]=j
print("\nBulunan GK sütunları:", {k:v+1 for k,v in sorted(GKCOL.items(),key=lambda x:x[1])})
eksik=[a for a in ("Elle Kontrol - Sahiplenme","KALECİ Dışı Meziyetler".replace("KALECİ Dışı","Kaleci Dışı"),"_MAKRO") if a not in GKCOL]
assert "_MAKRO" in GKCOL and "Elle Kontrol - Sahiplenme" in GKCOL, "GK sütunları bulunamadı — İPTAL"

isimler=ws.col_values(2)
nmap={}
for idx,v in enumerate(isimler): nmap.setdefault(norm(v), idx+1)

cells=[]; yazilan=[]
for i in hedef+ek:
    row=nmap.get(norm(i))
    if not row: print("  sheet'te yok:",i); continue
    out,makro=gk_kart(players[norm(i)])
    for ad,notu in out.items():
        if ad in GKCOL: cells.append(gspread.Cell(row,GKCOL[ad]+1,notu))
    if makro: cells.append(gspread.Cell(row,GKCOL["_MAKRO"]+1,makro))
    yazilan.append(i)
print(f"\nYazılacak: {len(yazilan)} kaleci, {len(cells)} hücre")
CH=1500
for k in range(0,len(cells),CH):
    ws.update_cells(cells[k:k+CH]); time.sleep(1)
print(f"✓ {len(yazilan)} kaleci GK bloğu YAZILDI")
open("_fm_gk_yazilan.txt","w",encoding="utf-8").write("\n".join(yazilan))
