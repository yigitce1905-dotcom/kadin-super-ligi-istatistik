# -*- coding: utf-8 -*-
"""Havuz oyuncularının güncel yaş + kulübünü SoccerDonna'dan çeker."""
import re, sys, time, unicodedata, json
import requests
from bs4 import BeautifulSoup
sys.stdout.reconfigure(encoding="utf-8")
import socket
_g=socket.getaddrinfo
def _y(h,p,*a,**k):
    try: return _g(h,p,*a,**k)
    except socket.gaierror:
        if isinstance(h,str) and "google" in h:
            return [(socket.AF_INET,socket.SOCK_STREAM,6,"",("142.251.127.95",p))]
        raise
socket.getaddrinfo=_y
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def nisim(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",s)).strip()

def satir_kulup(row):
    for a in row.find_all("a",href=True):
        if "verein_" in a["href"]: return a.get_text(strip=True)
    t=row.get_text(" ",strip=True)
    for art in ("vereinslos","Karriereende","pausiert","unbekannt"):
        if art.lower() in t.lower(): return art
    return ""

def profil_yas(purl):
    try:
        soup=BeautifulSoup(requests.get(purl,headers=H,timeout=15).text,"html.parser")
    except Exception: return "",""
    txt=soup.get_text(" ",strip=True)
    dob=""
    m=re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})",txt)
    if m: dob=m.group(0)
    age=""
    m2=re.search(r"\((\d{2})\)",txt)          # "12/08/1998 (27)"
    if m2: age=m2.group(1)
    return age,dob

def ara(isim,uen):
    slug=isim.lower().replace(" ","-"); q=isim.replace(" ","+")
    url=f"https://www.soccerdonna.de/en/{slug}/suche/ergebnis.html?quicksearch={q}"
    try:
        soup=BeautifulSoup(requests.get(url,headers=H,timeout=15).text,"html.parser")
    except Exception: return None
    ad_list=[]
    for a in soup.find_all("a",href=True):
        if "spieler_" in a["href"] and a.get_text(strip=True):
            row=a.find_parent("tr")
            if not row: continue
            ad=a.get_text(strip=True); nat=""
            for img in row.find_all("img"):
                ti=img.get("title","")
                if ti and ti!=ad and not ti.replace(" ","").isdigit(): nat=ti; break
            purl=a["href"]
            if purl.startswith("/"): purl="https://www.soccerdonna.de"+purl
            ad_list.append((ad,nat,satir_kulup(row),purl))
    if not ad_list: return None
    hn,hu=nisim(isim),(uen or "").lower()
    def sk(c):
        ad,nat,_,_=c; s=0
        if nisim(ad)==hn: s+=4
        elif hn in nisim(ad) or nisim(ad) in hn: s+=2
        if hu and (hu in nat.lower() or nat.lower() in hu): s+=3
        return s
    ad_list.sort(key=sk,reverse=True)
    return ad_list[0] if sk(ad_list[0])>0 else None

TR_EN={"USA":"United States","Japan":"Japan","Canada":"Canada","Philippines":"Philippines",
 "Morocco":"Morocco","Slovakia":"Slovakia","Bosnia":"Bosnia","Kenya":"Kenya"}

if __name__=="__main__":
    test=[("Ashley Orkus","United States"),("Riko Yasuzawa","Japan"),
          ("Chaymaa Mourtaji","Morocco"),("Nikola Rybanska","Slovakia")]
    for isim,u in test:
        c=ara(isim,u)
        if not c: print(f"{isim:22} -> BULUNAMADI"); continue
        ad,nat,club,purl=c
        age,dob=profil_yas(purl)
        print(f"{isim:22} -> {ad} | {nat} | kulüp={club} | yaş={age} dob={dob}")
        time.sleep(0.8)
