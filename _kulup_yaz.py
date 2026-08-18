# -*- coding: utf-8 -*-
"""_kulup_yazim_log.txt'teki değişiklikleri (artifact'ler hariç) Sco 🌍 Kulüp kolonuna yaz."""
import re, sys
import gspread
sys.stdout.reconfigure(encoding="utf-8")
CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"; GID = 1707810792
KULUP_KOL = 16
ARTIFACT = ("löschen", "spielerin", "unbekannt", "pausiert", "karriereende", "?")

degisim, atlanan = [], []
for ln in open("_kulup_yazim_log.txt", encoding="utf-8").read().splitlines():
    m = re.match(r"\s+satır(\d+): (.+?) \| (.+?) -> (.+)$", ln)
    if not m: continue
    row, isim, eski, yeni = int(m.group(1)), m.group(2), m.group(3).strip(), m.group(4).strip()
    if any(a in yeni.lower() for a in ARTIFACT):
        atlanan.append((isim, yeni)); continue
    degisim.append((row, isim, eski, yeni))

print(f"Yazılacak: {len(degisim)} | Artifact atlanan: {len(atlanan)}")
for i, y in atlanan: print(f"  ATLANDI (artifact): {i} -> {y}")

gc = gspread.service_account(filename=CREDS)
ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID)
hdr = ws.row_values(2)
assert "Kulüp" in hdr[15], "Kulüp kolonu kaymış!"
cells = [gspread.Cell(row, KULUP_KOL, yeni) for row, _, _, yeni in degisim]
ws.update_cells(cells)
print(f"\n✓ {len(cells)} Kulüp hücresi YAZILDI")
