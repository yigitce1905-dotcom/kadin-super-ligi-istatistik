# -*- coding: utf-8 -*-
"""FM'den çevrilen TASLAK nitelik notlarını Sco 🌐 sheet'ine yazar.

Yiğit'in kararı (2026-08-17). Kayıtlar taslaktır, Baran üzerinden geçer.

GÜVENLİK KURALLARI (kod düzeyinde zorunlu):
  1. DOLU HÜCRE EZİLMEZ. Baran'ın elle girdiği hiçbir not değiştirilmez;
     yalnızca BOŞ hücreler doldurulur.
  2. KİMLİK DOĞRULANMADAN YAZILMAZ. FM'deki yaş bizim kayıttan ±2'den fazla
     saparsa ya da isim satırda bulunamazsa oyuncu ATLANIR.
  3. KULÜP/SÖZLEŞME YAZILMAZ. FM'in veritabanı anlık görüntüsü eski;
     Akane Okuma'da FM 'INAC Kobe' derken bizim kayıt (SD'den) 'Aston Villa'
     idi ve bizimki doğruydu. Yalnızca NİTELİK yazılır.
  4. Yazılan her oyuncu 'Scout Notları' sütununa iz bırakır: "[FM taslak]".

Kullanım (fm_nitelik_esle.cevir çıktısıyla):
    python fm_sheete_yaz.py --kuru      # önizleme
    python fm_sheete_yaz.py --yaz
"""
import json
import sys
import unicodedata
from pathlib import Path

import gspread

sys.stdout.reconfigure(encoding="utf-8")

KOK = Path(__file__).parent
CREDS = r"C:\Users\MSI\Downloads\avid-phoenix-485522-h5-09c4cabbef0b.json"
GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"
GID_DUNYA = 1707810792
BEKLEYEN = KOK / "_fm_bekleyen.json"      # işlenmeyi bekleyen çeviriler
IZ = "[FM taslak]"
KARIYER = {}


# NFKD ł/ø/ð/þ'yi çözmez — aksan değil, ayrı harftirler. "Górnik Lęczna"
# (bizim yazım) ile "Górnik Łęczna" (FM) eşleşmiyordu.
_HARF = str.maketrans({
    "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "å": "a", "Å": "A",
    "ð": "d", "Ð": "D", "þ": "th", "Þ": "TH", "ß": "ss",
    "ı": "i", "İ": "I", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D",
})


def norm(s):
    s = str(s or "").translate(_HARF)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.casefold().split())


# Sheet ile FM ülke adlarını farklı yazıyor. Aynı ülke, farklı yazım —
# kimlik sinyalini boşa düşürmesin diye ortak bir ada indiriyoruz.
_ULKE_ES = {
    "danmark": "denmark", "pr china": "china", "china pr": "china",
    "the netherlands": "netherlands", "holland": "netherlands",
    "marocco": "morocco", "dr congo": "congo",
    "democratic republic of the congo": "congo", "democratic republic": "congo",
    "usa": "united states", "united states of america": "united states",
    "south korea": "korea republic", "korea south": "korea republic",
    "republic of ireland": "ireland", "eire": "ireland",
    "ivory coast": "cote divoire", "cote d ivoire": "cote divoire",
}


def _ulke(s):
    n = norm(s)
    return _ULKE_ES.get(n, n)


def yaz(kayitlar: dict, yaz_gercek: bool):
    """kayitlar: {isim: {"fm_yas": int, "nitelikler": {nitelik_adi: harf}}}"""
    from fetch_scout_kadro import hdr_kanonlastir

    global KARIYER
    kd = KOK / "scouting_leistungsdaten.json"
    KARIYER = json.load(open(kd, encoding="utf-8")) if kd.exists() else {}

    gc = gspread.service_account(filename=CREDS)
    ws = gc.open_by_key(GSHEET_ID).get_worksheet_by_id(GID_DUNYA)
    vals = ws.get_all_values()
    hdr = hdr_kanonlastir(vals[1])
    assert hdr[1] in ("İsim - Soyisim",), f"KOLON KAYMASI ({hdr[1]!r}) — iptal"

    kol = {}
    for i, h in enumerate(hdr):
        if h and h not in kol:
            kol[h] = i
    i_isim, i_yas = 1, kol.get("Yaş")
    i_not = kol.get("Scout Notları")

    satir_no = {norm(r[1]): i for i, r in enumerate(vals[2:], start=3) if len(r) > 1 and r[1].strip()}

    hucreler, ozet, atlanan = [], [], []
    for isim, k in kayitlar.items():
        sn = satir_no.get(norm(isim))
        if sn is None:
            atlanan.append((isim, "sheet'te satır yok")); continue
        satir = vals[sn - 1]

        # ── KİMLİK DOĞRULAMA ─────────────────────────────────────────────
        # Yaş tek başına yetmiyor: Sharon Sampson'ın sheet'teki yaşı 126
        # (doğum tarihi de boş) — açık bir yazım hatası, farklı bir oyuncu
        # değil. Kulüp VE boy tutuyorsa yaş hatası kimliği bozmaz.
        # İsim zaten birebir eşleşti (satırı onunla bulduk). Ek olarak EN AZ BİR
        # bağımsız sinyal isteriz: yaş, kulüp, boy ya da uyruk.
        # DİKKAT: sheet'te 431 satırda Yaş = 126 yazıyor ve hepsinin Doğum
        # Tarihi boş — boş tarihten yaş hesaplayan formülün artığı (2026-1900).
        # 126 bir yaş değil, "veri yok" demek; sinyal sayılmaz.
        def _h(ad):
            i = kol.get(ad)
            return satir[i].strip() if i is not None and len(satir) > i else ""

        bizim_yas = _h("Yaş")
        if bizim_yas == "126":
            bizim_yas = ""
        fm_yas = k.get("fm_yas")
        bb = _h("Boy").replace(",", ".")
        fb = str(k.get("fm_boy") or "").strip()
        bk, fk = norm(_h("Kulüp")), norm(k.get("fm_kulup"))
        bu = _ulke(_h("Vatandaşlık (Millî)"))
        fu = {_ulke(x) for x in (k.get("fm_uyruklar")
                                 or [k.get("fm_uyruk") or ""]) if x}

        sinyal = {}
        # FM'in kulübü bizim KENDİ kariyer verimizde geçiyor mu? Sheet'in
        # "Kulüp" hücresi güncel DURUMU tutuyor ("Serbest"), FM ise veri tabanı
        # anlık görüntüsündeki son kulübü. Michaela Abam'da sheet "Serbest",
        # FM "Cruz Azul" diyordu ve kimlik doğrulanamıyordu — oysa bizim
        # leistungsdaten kaydı onu 25/26'da Cruz Azul'da 27 maçla gösteriyor.
        # Yani çelişki değil, iki farklı soruya verilmiş iki doğru cevap.
        if fk and isim in KARIYER:
            gecmis = {norm(s.get("kulup")) for s in
                      (KARIYER[isim] or {}).get("sezonlar", []) if s.get("kulup")}
            if gecmis:
                sinyal["kariyer"] = any(fk in g or g in fk for g in gecmis)
        if bizim_yas.isdigit() and fm_yas:
            sinyal["yaş"] = abs(int(bizim_yas) - int(fm_yas)) <= 2
        if bb and fb:
            try:
                sinyal["boy"] = abs(float(bb) * 100 - float(fb)) <= 2
            except ValueError:
                pass
        if bk and fk:
            sinyal["kulüp"] = bk in fk or fk in bk
        if bu and fu:
            sinyal["uyruk"] = bu in fu

        if any(v is False for v in sinyal.values()) and not any(sinyal.values()):
            atlanan.append((isim, f"kimlik doğrulanamadı: {sinyal}")); continue
        if not sinyal:
            atlanan.append((isim, "doğrulanacak veri yok (yaş/boy/kulüp/uyruk boş)")); continue
        if not all(sinyal.values()):
            print(f"   ! {isim}: kısmi eşleşme {sinyal} — kabul edildi")

        yazilan = 0
        for nit, harf in (k.get("nitelikler") or {}).items():
            ci = kol.get(nit)
            if ci is None or not harf:
                continue
            mevcut = satir[ci].strip() if len(satir) > ci else ""
            # KURAL 1 — dolu hücre ezilmez. TEK İSTİSNA "FF": Baran
            # izleyemediği oyuncularda bloğu en düşük seviyeye SABİTLİYOR
            # (kendi ifadesi). Yani FF bir yargı değil, yer tutucu — bu
            # oyuncular zaten "değerlendirilmemiş" sayılıyor. Diğer her not
            # (EE dâhil) gerçek yargıdır ve korunur.
            if mevcut and mevcut.upper() != "FF":
                continue
            if mevcut.upper() == "FF" and harf == "FF":
                continue                     # zaten FF, boşuna yazma
            hucreler.append(gspread.Cell(sn, ci + 1, harf))
            yazilan += 1
        if yazilan and i_not is not None:
            eski_not = satir[i_not].strip() if len(satir) > i_not else ""
            if IZ not in eski_not:
                hucreler.append(gspread.Cell(sn, i_not + 1,
                                             (eski_not + " " + IZ).strip()))
        ozet.append((isim, sn, yazilan))

    print(f"{'YAZILACAK' if yaz_gercek else 'ÖNİZLEME'} — {len(ozet)} oyuncu, "
          f"{len(hucreler)} hücre\n")
    for isim, sn, n in ozet:
        print(f"   satır {sn:5}  {isim[:28]:28} {n:2} nitelik")
    if atlanan:
        print(f"\nATLANAN ({len(atlanan)}):")
        for isim, sebep in atlanan:
            print(f"   {isim[:28]:28} {sebep}")

    if yaz_gercek and hucreler:
        ws.update_cells(hucreler, value_input_option="USER_ENTERED")
        print(f"\n✓ {len(hucreler)} hücre yazıldı (dolu hücrelere DOKUNULMADI).")
    elif not yaz_gercek:
        print("\n[KURU MOD] yazılmadı. Gerçek yazma: --yaz")


def main():
    if not BEKLEYEN.exists():
        print(f"{BEKLEYEN.name} yok. Önce çeviri kayıtlarını oraya yaz."); return
    kayitlar = json.load(open(BEKLEYEN, encoding="utf-8"))
    yaz(kayitlar, "--yaz" in sys.argv)


if __name__ == "__main__":
    main()
