# -*- coding: utf-8 -*-
"""
U17 Kızlar Gelişim Ligi verisinden YANLIŞ eklenen erkek/profesyonel oyuncuları temizler.

Kök neden: scraper_u17_range.py maçları "iki takım da U17 takım-adı kümesinde" diye
alıyor; ama Fenerbahçe/Galatasaray/Beşiktaş/Trabzonspor vb. ERKEK takımları AYNI isimle
geçtiği için erkek maçları da (Guendouzi, Oosterwolde...) karışmış. grup/lig tek tip
atandığından ayırt etmiyor → tek güvenilir sinyal İSİM CİNSİYETİ.

Yöntem (yüksek hassasiyet — kız silmemek öncelikli): ön-adı kesin ERKEK olanlar atılır.
  - ERKEK ad seti (yaygın Türkçe erkek adları)
  - 'MUHAMMED/MUHAMMET' ve 'MEHMET' önekleri
  - yabancı erkek futbolcu adları
Uniseks ama kız-ağırlıklı adlar (Ece, Deniz, Derya, Naz, Su, Eylül...) KORUNUR.

Kullanım:
  python temizle_u17.py          # DRY-RUN: sadece raporlar, dosyayı DEĞİŞTİRMEZ
  python temizle_u17.py --uygula # gerçekten siler + kaydeder (yedek: altlig_u17.bak.json)
"""
import json, sys
from collections import Counter
from pathlib import Path

YOL = Path(__file__).parent / "altlig_u17.json"

# ── Yaygın Türkçe ERKEK ön-adları (kız adlarıyla çakışan uniseksler bilinçli HARİÇ) ──
ERKEK = {
    "MEHMET","MUSTAFA","AHMET","AHMED","ALİ","HÜSEYİN","HASAN","İBRAHİM","İSMAİL",
    "YUSUF","MURAT","ÖMER","EMRE","RAMAZAN","KEMAL","HALİL","ABDULLAH","FATİH",
    "EMİR","ENES","ARDA","KEREM","BERAT","BURAK","KAAN","FURKAN","EREN","EYÜP",
    "HAMZA","YİĞİT","KUZEY","POYRAZ","RÜZGAR","ÇINAR","DORUK","EFE","ONUR","MERT",
    "SEFA","BERA","METE","AYAZ","HARUN","DOĞAN","SÜLEYMAN","YUNUS","SALİH","ARİF",
    "HAKTAN","TAHA","YAĞIZ","UĞUR","ÇAĞATAY","ERK","GÖKAY","ENDER","ŞENER","SELMAN",
    "MAHİR","BÜNYAMİN","ERHAN","SAMED","GÖKTAN","TUĞRA","DEMİR","NECAT","EKREM",
    "CELAL","EGEMEN","ARAS","DOĞANAY","RIDVAN","OSMAN","UTKU","ABDÜLKERİM","KAZIMCAN",
    "MÜNİR","OĞUZ","ÇAĞLAR","CEM","BAHA","NECİP","NAİL","İNANÇ","KAĞAN","MİRAÇ","MİRAC",
    "SEZGİN","ÜMEYR","MÜCAHİT","MUSAB","MUSHAB","FERİT","BİLAL","OĞULCAN","METEHAN",
    "ABDULMECİT","ABDURRAHİM","BEKİRHAN","ADAR","SAİD","ÜNAL","ERCAN","GALİP","CENGİZ",
    "BATIN","NAZIM","TUĞRUL","RESUL","DOĞUKAN","BEDİRHAN","CEMİL","BUĞRA","MUHARREM",
    "ŞENOL","ENSAR","OZAN","BORAN","BERK","EYMEN","BARTU","YASİN","ÇAĞAN","TUNAHAN",
    "ENGİN","MEVLÜT","TARHAN","ORHAN","MİRAN","UHUT","ECMEL","ŞEVKET","AZAD","MAHMUT",
    "PARS","FIRAT","FIRATCAN","ÇAĞDAŞ","HANEFİ","BARIŞ","İLKAY","ÖZGÜR","ETKA","ALP",
    "ALPER","ALPGİRAY","ASIM","BARAN","CİHAN","TALHA","YEKTA","YUZARSİF","ÖZTÜRK",
    "RİTM","ERTUĞRUL","KORAY","SARP","SARPER","TUNA","ATA","ATABERK","BORA","CEYHUN",
    "VOLKAN","SİNAN","SERKAN","SERDAR","TOLGA","TOLGAHAN","UMUT","KEREMCAN","EFEHAN",
    "MUHAMMETALİ","ABDULSAMET","ABDÜLSAMET","ABDULKADİR","ABDULBAKİ","ABDULKERİM",
    "NECMETTİN","NURETTİN","SEYİT","SEYDİ","ŞABAN","ŞAHİN","VEYSEL","ZAFER","ZEKİ",
    "RECEP","REŞİT","RIFAT","ŞEVKİ","ŞÜKRÜ","TAYFUN","TEOMAN","TUFAN","VEDAT","YAVUZ",
    "YALÇIN","HAYDAR","HAKAN","HAKKI","İLYAS","KADİR","KÜRŞAT","LEVENT","NİYAZİ",
    "OKAN","OKTAY","ÖNDER","RAİF","SADIK","SAMİ","SÜMER","TANER","ÜMİT","VAHİT",
    "MAHSUM","ROJAT","RENAS","ARGEŞ","NUDEM",  # (Nudem kadın! aşağıda KORUNAN'da geri alınır)
    "DOĞU","ESERCAN","EVREN","TOPRAK","CAN","EGE",
}
# Erkek setinden yanlışlıkla giren kadın/uniseks adları geri çıkar (koruma):
KORUNAN_KADIN = {"NUDEM","ASRIN","REVŞAN","FİDA","BENAY","HÜRRİYET","HARE","BERİN",
                 "DELFİN","MELODİ","HAYRİYE","NEVBAHAR","NİLA","SÜKEYNA","DİLŞAH",
                 "DİLARASU","KERİME","ELANİL","MELİN","YELİZ"}
ERKEK -= KORUNAN_KADIN

ONEK = ("MUHAMME", "MEHMET", "ABDULL")  # MUHAMMED/MUHAMMET/MEHMET/ABDULLAH...

FOREIGN_ERKEK = {
    "MATTEO","JAYDEN","ANTHONY","MAURO","LEROY","MARIO","DAVINSON","LUCAS","GABRIEL",
    "EDERSON","ANDERSON","DORGELES","RENATO","NOA","WILFRIED","SACHA","VICTOR",
    "DIMITRIOS","THALISSON","SEKOU","AYOTOMIWA","ANDRE","BENJAMIN","WAGNER","MATHIAS",
    "EBERE","OLEKSANDR","CHIBUIKE","CHRIST","FELIPE","ERNEST","ROLAND","MATEJ","FRANCO",
    "OUSMANE","ADAMA","EDRIS","JHON","MARCO","MILAN","VASA","RUGERM","RENAN","CARLOS",
    "DIEGO","BRUNO","PEDRO","JOAO","RAFAEL",
}


def ilk_ad(isim):
    p = isim.strip().split()
    return p[0] if p else ""


def erkek_mi(isim):
    ad = ilk_ad(isim).upper()
    if ad in KORUNAN_KADIN:
        return False
    if ad in ERKEK or ad in FOREIGN_ERKEK:
        return True
    if ad.startswith(ONEK):
        return True
    return False


def main():
    uygula = "--uygula" in sys.argv[1:]
    d = json.load(open(YOL, encoding="utf-8"))
    oy = d["oyuncular"]
    silinecek = [o for o in oy if erkek_mi(o["oyuncu"])]
    kalan = [o for o in oy if not erkek_mi(o["oyuncu"])]

    SUPHELI = ["FENERBAHÇE A.Ş.","GALATASARAY A.Ş.","NATURA DÜNYASI GENÇLERBİRLİĞİ",
               "BEŞİKTAŞ A.Ş.","AMED SPORTİF FAALİYETLER","TRABZONSPOR A.Ş."]
    print(f"Toplam {len(oy)} → silinecek {len(silinecek)} → kalan {len(kalan)}")
    print()
    for tk in SUPHELI:
        kept = sorted(o["oyuncu"] for o in kalan if o["takim"] == tk)
        rem  = len([o for o in silinecek if o["takim"] == tk])
        print(f"### {tk}: silinen {rem}, kalan {len(kept)}")
        print("   ", ", ".join(kept))
        print()

    if uygula:
        # gol_kralicesi'nden de silinen kisi_id'leri at (resmi kadın tablosu, ihtiyaten)
        sil_kid = {o.get("kisi_id") for o in silinecek}
        d["oyuncular"] = kalan
        if "gol_kralicesi" in d:
            d["gol_kralicesi"] = [g for g in d["gol_kralicesi"] if g.get("kisi_id") not in sil_kid]
        bak = YOL.with_suffix(".bak.json")
        if not bak.exists():
            bak.write_text(json.dumps(json.load(open(YOL,encoding="utf-8")),ensure_ascii=False,indent=2),encoding="utf-8")
        json.dump(d, open(YOL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[UYGULANDI] {len(silinecek)} oyuncu silindi → {YOL.name} (yedek: {bak.name})")
    else:
        print("(DRY-RUN — dosya değişmedi. Uygulamak için: python temizle_u17.py --uygula)")


if __name__ == "__main__":
    main()
