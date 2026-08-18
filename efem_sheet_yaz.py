# -*- coding: utf-8 -*-
"""
efem.club linkindeki oyuncunun FM notlarını -> harf -> Sco 🌍 sheet'teki satırına yazar.
Oyuncu sheet'te (İsim - Soyisim) BULUNMALI. Sadece nitelik/makro/nihai hücrelerini doldurur.
Baran sonradan gözden geçirir. Sonra: python entegre_islenmis.py  (siteye çeker).

Kullanım:
    python efem_sheet_yaz.py <efem_url> [<efem_url> ...]
    python efem_sheet_yaz.py --kuru <efem_url>        # yazmadan önizleme
    python efem_sheet_yaz.py --isim "Tam İsim" <url>  # isim eşleşmezse elle ver
"""
import sys, re, unicodedata
import gspread
from efem_isle import cek, coz, kayit_yap

CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID = 1707810792

KOL = {
    "Bitiricilik":19,"Top Tekniği":20,"Penaltı Vuruşu":21,"Markaj":22,"Top Kapma":23,
    "Uzun Taç":24,"Duran Top":25,"İlk Kontrol":26,"Kafa Vuruşu":27,"Orta Yapma":28,
    "Kısa Pas":29,"Uzun Pas":30,"Top Sürme":31,"Uzaktan Şut":32,
    "Agresiflik":34,"Cesaret":35,"Karar Alma":36,"Kararlılık":37,"Konsantrasyon":38,
    "Liderlik":39,"Önsezi":40,"Konumlanma":41,"Soğukkanlılık":42,"Takım Oyunu":43,
    "Topsuz Alan":44,"Görüş":45,
    "Çeviklik":47,"Dayanıklılık":48,"Denge":49,"Güç":50,"Sürat":51,"Hızlanma":52,
    "Koordinasyon":53,"Zindelik":54,"Zıplama":55,"Zayıf Ayak":56,
    "Sakatlanma Direnci":58,"Sportmenlik":59,"Profesyonellik":60,"Sadakat":61,
    "Baskıya Dayanıklılık":62,"Uyumluluk":63,"Süreklilik":64,"Çalışkanlık":65,
}
MAKRO_KOL = {"beceri":33,"beseri":46,"fiziki":57,"sahsi":66}
NIHAI_KOL = 99


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z0-9 ]"," ", s)).strip()

def isim_cek(raw, url):
    m = re.search(r"<title>([^<|]+?)\s*[-|]", raw)
    if m and m.group(1).strip().lower() != "efem.club":
        return m.group(1).strip()
    m = re.search(r"/players/\d+-(.+)$", url)
    return m.group(1).replace("-", " ").strip() if m else ""

def satir_bul(isimler, isim):
    if isim in isimler:
        return isimler.index(isim) + 1
    hn = _norm(isim)
    for i, v in enumerate(isimler):
        if _norm(v) == hn:
            return i + 1
    return None


def main():
    a = sys.argv[1:]
    kuru = "--kuru" in a
    elle_isim = None
    if "--isim" in a:
        i = a.index("--isim"); elle_isim = a[i+1]; del a[i:i+2]
    urls = [x for x in a if x.startswith("http")]
    if not urls:
        print("Kullanım: python efem_sheet_yaz.py [--kuru] [--isim \"Ad\"] <efem_url> ..."); return

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID)
    hdr = ws.row_values(2)
    assert "Bitiricilik" in hdr[19] and "Agresiflik" in hdr[34], "KOLON KAYMASI — iptal"
    isimler = ws.col_values(2)

    for url in urls:
        raw = cek(url)
        isim = elle_isim or isim_cek(raw, url)
        meta, tum, gk = coz(raw)
        rec = kayit_yap(meta, tum, gk)
        row = satir_bul(isimler, isim)
        print(f"\n=== {isim} ===  nihai={rec['nihai']} makro={rec['makro']}")
        if not row:
            print(f"  ✗ sheet'te bulunamadı. Doğru adı --isim ile ver, ya da önce sheet'e ekle."); continue
        print(f"  satır {row} | nitelik: beceri {len(rec['beceri'])} beseri {len(rec['beseri'])} "
              f"fiziki {len(rec['fiziki'])} sahsi {len(rec['sahsi'])}")
        cells = []
        for grup in ("beceri","beseri","fiziki","sahsi"):
            for ad, notu in rec[grup].items():
                if ad in KOL and notu:
                    cells.append(gspread.Cell(row, KOL[ad]+1, notu))
        for g, ki in MAKRO_KOL.items():
            if rec["makro"].get(g):
                cells.append(gspread.Cell(row, ki+1, rec["makro"][g]))
        if rec.get("nihai"):
            cells.append(gspread.Cell(row, NIHAI_KOL+1, rec["nihai"]))
        if kuru:
            print(f"  [KURU] {len(cells)} hücre yazılacaktı (yazılmadı)")
        else:
            ws.update_cells(cells)
            print(f"  ✓ {len(cells)} hücre YAZILDI")

    if not kuru:
        print("\nSonra: python entegre_islenmis.py  (siteye çeker)")


if __name__ == "__main__":
    main()
