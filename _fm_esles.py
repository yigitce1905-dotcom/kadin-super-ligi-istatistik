# -*- coding: utf-8 -*-
import csv, json, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8")

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z ]"," ",s)).strip()

CSV=r"C:\Users\MSI\Documents\Sports Interactive\Football Manager 26\FM26PlayerExport by vinteset\Exports CSV\moneyball_export_20260709_224001.csv"
rows=[]
with open(CSV, encoding="utf-8") as f:
    rd=csv.reader(f, delimiter=";")
    hdr=next(rd)
    for r in rd:
        if len(r)>=6: rows.append(r)
print("Export kolonları:", hdr)
print("Export oyuncu:", len(rows))

# fm isim -> satır
fm={}
for r in rows:
    fm.setdefault(norm(r[1]), r)

d=json.load(open("scout_kadro_raporlar.json", encoding="utf-8"))
havuz=list(d.keys())
degerlendirilmemis=[i for i in havuz if not d[i].get("degerlendirildi")]

eslesen=[i for i in havuz if norm(i) in fm]
esl_degerlendirilmemis=[i for i in degerlendirilmemis if norm(i) in fm]
print(f"\nBizim havuz: {len(havuz)} | değerlendirilmemiş: {len(degerlendirilmemis)}")
print(f"Export'ta EŞLEŞEN havuz: {len(eslesen)}")
print(f"Export'ta EŞLEŞEN değerlendirilmemiş: {len(esl_degerlendirilmemis)}")

print("\n--- Eşleşen örnekler (isim | ülke | kulüp | mevki | yaş | yetenek) ---")
for i in eslesen[:25]:
    r=fm[norm(i)]
    print(f"  {i:28} | {r[2]:4} | {r[3][:22]:22} | {r[4][:14]:14} | {r[5]:3} | {r[6]}")
