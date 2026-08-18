# -*- coding: utf-8 -*-
"""SD ile güncel kulübü yeniden karşılaştır + Sco 🌍 sheet Kulüp kolonunu güncelle.
Güvenilir yöntem: isim+uyruk ile SD arama, kulübü arama satırından okur. Emekli/bulunamayan/aynı → dokunma."""
import json, re, sys, time, unicodedata
import requests
from bs4 import BeautifulSoup
import gspread
sys.stdout.reconfigure(encoding="utf-8")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"; GID = 1707810792
KULUP_KOL = 16   # 1-based (0-based 15)
KURU = "--kuru" in sys.argv

d = json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
TR_EN = {"ABD":"United States","Türkiye":"Turkey","İsveç":"Sweden","Bosna Hersek":"Bosnia",
 "Hırvatistan":"Croatia","Cezayir":"Algeria","Brezilya":"Brazil","Kanada":"Canada","Avustralya":"Australia",
 "Danimarka":"Denmark","Almanya":"Germany","Macaristan":"Hungary","Gana":"Ghana","Karadağ":"Montenegro",
 "Vietnam":"Vietnam","Rusya Federasyonu":"Russia","Meksika":"Mexico","Portekiz":"Portugal","İspanya":"Spain",
 "Irak":"Iraq","Porto Riko":"Puerto Rico","Arnavutluk":"Albania","Dominik Cumhuriyeti":"Dominican","Gabon":"Gabon",
 "Bermuda":"Bermuda","Panama":"Panama","İrlanda":"Ireland","Nijerya":"Nigeria","Haiti":"Haiti","İngiltere":"England",
 "Venezuela":"Venezuela","Trinidad ve Tobago":"Trinidad","Gürcistan":"Georgia","Fransa":"France","İtalya":"Italy",
 "Hollanda":"Netherlands","Norveç":"Norway","İsviçre":"Switzerland","Belçika":"Belgium","İzlanda":"Iceland",
 "Japonya":"Japan","Çin":"China","Güney Kore":"South Korea","Kolombiya":"Colombia","Arjantin":"Argentina",
 "Polonya":"Poland","Avusturya":"Austria","Finlandiya":"Finland","Sırbistan":"Serbia","Çekya":"Czech",
 "İskoçya":"Scotland","Yeni Zelanda":"New Zealand","Kamerun":"Cameroon","Fildişi Sahili":"Ivory Coast"}
ALIAS = {"internazionale":"inter","inter milano":"inter","ol lyonnes":"lyon","olympique lyon":"lyon"}
SUFFIX = r"\b(fc|sc|fk|zfk|znk|cf|sv|vfl|vfb|bk|if|il|ff|q|ii|iii|u23|u21|u20|u19|u17|w|women|frauen|feminin|femenin|femenil|femminile|ladies|kvinner|dff|wfc|calcio)\b"
def nk(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    s=re.sub(SUFFIX," ",re.sub(r"[^a-z0-9 ]"," ",s)); s=re.sub(r"\s+"," ",s).strip(); return ALIAS.get(s,s)
def nisim(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",s)).strip()
def ayni_kulup(a,b):
    na,nb=nk(a),nk(b)
    if not na or not nb: return False
    ta,tb=set(na.split()),set(nb.split())
    return na==nb or na in nb or nb in na or bool(ta&tb)
def satir_kulup(row):
    for a in row.find_all("a", href=True):
        if "verein_" in a["href"]: return a.get_text(strip=True)
    t=row.get_text(" ",strip=True)
    for art in ("vereinslos","Karriereende","pausiert","unbekannt"):
        if art.lower() in t.lower(): return art
    return ""
def ara(isim, uen):
    slug=isim.lower().replace(" ","-"); q=isim.replace(" ","+")
    url=f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html?quicksearch={q}"
    soup=BeautifulSoup(requests.get(url,headers=H,timeout=12).text,"html.parser")
    ad_list=[]
    for a in soup.find_all("a",href=True):
        if "spieler_" in a["href"] and a.get_text(strip=True):
            row=a.find_parent("tr")
            if not row: continue
            ad=a.get_text(strip=True); nat=""
            for img in row.find_all("img"):
                ti=img.get("title","")
                if ti and ti!=ad and not ti.replace(" ","").isdigit(): nat=ti; break
            ad_list.append((ad,nat,satir_kulup(row)))
    hn,hu=nisim(isim),(uen or "").lower()
    def sk(c):
        ad,nat,_=c; s=0
        if nisim(ad)==hn: s+=4
        elif hn in nisim(ad) or nisim(ad) in hn: s+=2
        if hu and (hu in nat.lower() or nat.lower() in hu): s+=3
        return s
    if not ad_list: return None
    ad_list.sort(key=sk,reverse=True)
    return ad_list[0] if sk(ad_list[0])>0 else None

gc=gspread.service_account(filename=CREDS)
ws=gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID)
vals=ws.get_all_values(); hdr=vals[1]
assert "Kulüp" in hdr[15], "Kulüp kolonu kaymış!"
degisim=[]
islenen=0
for ri in range(2,len(vals)):
    r=vals[ri]
    isim=r[1].strip() if len(r)>1 else ""
    eski=r[15].strip() if len(r)>15 else ""
    if not isim or not eski or isim not in d: continue
    islenen+=1
    uen=TR_EN.get(d.get(isim,{}).get("vatandaslik",""),"")
    try: c=ara(isim,uen)
    except Exception: c=None
    if not c: continue
    ad,nat,kulup=c; low=kulup.lower()
    if "karriereende" in low: continue
    if "vereinslos" in low or low in ("pausiert","unbekannt"): yeni="Serbest"
    elif ayni_kulup(eski,kulup): continue
    else: yeni=kulup
    if nk(yeni)!=nk(eski) and yeni.strip().lower()!=eski.strip().lower():
        degisim.append((ri+1,isim,eski,yeni))
    if islenen%60==0:
        print(f"  ...{islenen} işlendi | {len(degisim)} değişiklik")
    time.sleep(0.4)

log=[f"İşlenen {islenen} | Değişiklik {len(degisim)}"]
log+=[f"  satır{row}: {isim} | {eski} -> {yeni}" for row,isim,eski,yeni in degisim]
open("_kulup_yazim_log.txt","w",encoding="utf-8").write("\n".join(log))
print("\n".join(log[:1]))
if KURU:
    print("[KURU] yazılmadı."); sys.exit(0)
cells=[gspread.Cell(row,KULUP_KOL,yeni) for row,_,_,yeni in degisim]
if cells:
    ws.update_cells(cells)
    print(f"✓ {len(cells)} Kulüp hücresi YAZILDI -> _kulup_yazim_log.txt")
else:
    print("Değişiklik yok.")
