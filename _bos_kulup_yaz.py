# -*- coding: utf-8 -*-
"""8 boş kulübü Sco 🌍 Kulüp kolonuna yazar (SD isim+uyruk doğrulamalı)."""
import re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
import socket
_g = socket.getaddrinfo
def _y(h, p, *a, **k):
    try: return _g(h, p, *a, **k)
    except socket.gaierror:
        if isinstance(h, str) and "google" in h:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.251.127.95", p))]
        raise
socket.getaddrinfo = _y
import gspread

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"; GID = 1707810792
KULUP_KOL = 16

YENI = {"Ange Bawou":"BIIK-Schymkent","Ifeoma Onumonu":"Serbest",
        "Vivian Ikechukwu":"Club Santos Laguna","Darya Harshkova":"WFC Dinamo-BSUPC",
        "Glory Ogbonna":"FC Kiryat Gat","Sanaa Mssoudy":"AS FAR",
        "Shamirah Nalugya":"WFC Minsk","Chaymaa Mourtaji":"Sporting Club Casablanca"}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z ]"," ", s)).strip()

gc = gspread.service_account(filename=CREDS)
ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID)
hdr = ws.row_values(2)
assert "Kulüp" in hdr[15], "Kulüp kolonu kaymış — İPTAL"
isimler = ws.col_values(2)
nmap = {}
for i, v in enumerate(isimler):
    nmap.setdefault(norm(v), i + 1)

cells = []
for isim, kulup in YENI.items():
    row = nmap.get(norm(isim))
    if not row:
        print(f"  ✗ sheet'te yok: {isim}"); continue
    mevcut = ws.cell(row, KULUP_KOL).value or ""
    if mevcut.strip():
        print(f"  ↷ atlandı (dolu: {mevcut}): {isim}"); continue
    cells.append(gspread.Cell(row, KULUP_KOL, kulup))
    print(f"  ✓ satır {row}: {isim} -> {kulup}")
if cells:
    ws.update_cells(cells)
    print(f"\n{len(cells)} Kulüp hücresi YAZILDI")
