# -*- coding: utf-8 -*-
"""Rol matrisi kalibrasyon raporu — Baran için.

Matrisin önerdiği rol ile scout'un atadığı (oyunda kullanılan) rol nerede
ayrışıyor? İki tür bulgu var:

  A) SİSTEMATİK  — aynı yön tekrar tekrar çıkıyorsa (ör. 27 oyuncuda
     "Çakılı Stoper" yerine "Limitli Stoper") bu tek tek oyuncularla değil,
     o iki rolün AĞIRLIKLARIYLA ilgilidir. Kalibrasyon buradan yapılır.
  B) TEKİL      — puan farkı çok büyük olan bireysel vakalar. Bunlar ya
     gerçekten yanlış konumlandırılmış oyunculardır ya da nitelik notlarında
     bir tuhaflık vardır.

Kullanım:  python rapor_rol_kalibrasyon.py
"""
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from fpdf import FPDF

from rol_matris import matris_yukle, rol_onerisi

KOK = Path(__file__).parent
CIKTI = Path.home() / "Desktop" / "ROL_MATRISI_Kalibrasyon.pdf"

KREM = (250, 247, 240)
KOYU = (22, 26, 34)
LIME = (120, 170, 60)
GRI = (110, 118, 130)


def veri_topla():
    m = matris_yukle()
    havuz = [("TR", json.load(open(KOK / "scotr_raporlar.json", encoding="utf-8"))),
             ("Dünya", json.load(open(KOK / "scout_kadro_raporlar.json", encoding="utf-8")))]
    ciftler = defaultdict(list)
    ayni = hesapsiz = 0
    for kaynak, hav in havuz:
        for isim, k in hav.items():
            r = rol_onerisi(k, m)
            if not r["kullanilan"]:
                continue
            if not r["hesaplandi"]:
                hesapsiz += 1
                continue
            s = r["siralama"]
            if not s:
                continue
            if s[0][0] == r["kullanilan"]:
                ayni += 1
                continue
            kul = next((x for x in s if x[0] == r["kullanilan"]), None)
            fark = (s[0][1] - kul[1]) if kul else None
            ciftler[(r["kullanilan"], s[0][0])].append(
                (isim, kaynak, fark, "-".join(r["mevkiler"])))
    return m, ciftler, ayni, hesapsiz


class Rapor(FPDF):
    def header(self):
        self.set_fill_color(*KOYU)
        self.rect(0, 0, 210, 22, "F")
        self.set_font("DV", "B", 12)
        self.set_text_color(*KREM)
        self.set_xy(14, 7)
        self.cell(0, 8, "ROL MATRİSİ — KALİBRASYON RAPORU")
        self.set_font("DV", "", 7.5)
        self.set_text_color(*LIME)
        self.set_xy(14, 14.5)
        self.cell(0, 4, f"Ideal Sports Management · {date.today().strftime('%d.%m.%Y')}")
        self.ln(16)

    def footer(self):
        self.set_y(-12)
        self.set_font("DV", "", 7)
        self.set_text_color(*GRI)
        self.cell(0, 5, f"{self.page_no()}", align="C")


def main():
    m, ciftler, ayni, hesapsiz = veri_topla()
    toplam_ayrisan = sum(len(v) for v in ciftler.values())
    rol_toplam = {r["ad"]: r["toplam"] for r in m["roller"]}

    pdf = Rapor()
    _f = KOK / "fonts"
    pdf.add_font("DV", "", str(_f / "DejaVuSans.ttf"))
    pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
    pdf.set_auto_page_break(True, 16)
    pdf.add_page()
    pdf.set_fill_color(*KREM)
    pdf.rect(0, 22, 210, 275, "F")

    pdf.set_text_color(*KOYU)
    pdf.set_font("DV", "", 8.5)
    pdf.set_x(14)
    pdf.multi_cell(182, 4.6,
                   "Matrisin en yüksek puanlı rolü ile oyuncuya atanmış rolün (oyunda "
                   "kullanıldığı rol) ayrıştığı vakalar. Ayrışma başlı başına hata "
                   "değildir — bu analiz zaten \"başka hangi rolde daha verimli "
                   "olabilir\" sorusunu cevaplamak için var. Ama AYNI ayrışma tekrar "
                   "tekrar çıkıyorsa, sorun oyuncularda değil o iki rolün "
                   "ağırlıklarındadır. Aşağıdaki ilk tablo bunun içindir.")
    pdf.ln(2)
    pdf.set_font("DV", "B", 9)
    pdf.set_x(14)
    pdf.cell(0, 6, f"Örtüşen: {ayni}    ·    Ayrışan: {toplam_ayrisan}    ·    "
                   f"Hesaplanamayan (notlar ayırt edici değil): {hesapsiz}", ln=1)
    pdf.ln(3)

    # ── A) SİSTEMATİK ────────────────────────────────────────────────────────
    pdf.set_font("DV", "B", 10)
    pdf.set_text_color(*KOYU)
    pdf.set_x(14)
    pdf.cell(0, 7, "A) SİSTEMATİK AYRIŞMALAR — ağırlık kalibrasyonu gerektirebilir", ln=1)
    pdf.set_font("DV", "", 7)
    pdf.set_text_color(*GRI)
    pdf.set_x(14)
    pdf.cell(0, 4, "Parantez içi sayı: o rolün matristeki toplam ağırlığı.", ln=1)
    pdf.ln(1)

    bas = [("Kişi", 12), ("Atanan rol", 52), ("Matrisin önerdiği", 52),
           ("Ort. fark", 18), ("Ağırlık", 26)]
    pdf.set_font("DV", "B", 7.5)
    pdf.set_fill_color(*KOYU)
    pdf.set_text_color(*KREM)
    pdf.set_x(14)
    for b, w in bas:
        pdf.cell(w, 6, b, border=0, fill=True, align="C")
    pdf.ln(6)

    sirali = sorted(ciftler.items(), key=lambda x: -len(x[1]))
    pdf.set_font("DV", "", 7.5)
    for i, ((a, b), lst) in enumerate(sirali[:18]):
        farklar = [f for _, _, f, _ in lst if f is not None]
        ort = sum(farklar) / len(farklar) if farklar else 0
        pdf.set_fill_color(238, 234, 226) if i % 2 else pdf.set_fill_color(*KREM)
        pdf.set_text_color(*KOYU)
        pdf.set_x(14)
        pdf.cell(12, 5.4, str(len(lst)), fill=True, align="C")
        pdf.cell(52, 5.4, f" {a}", fill=True)
        pdf.cell(52, 5.4, f" {b}", fill=True)
        pdf.cell(18, 5.4, f"+{ort:.0f}", fill=True, align="C")
        pdf.cell(26, 5.4, f"{rol_toplam.get(a,'?')} → {rol_toplam.get(b,'?')}",
                 fill=True, align="C")
        pdf.ln(5.4)

    pdf.ln(4)
    pdf.set_font("DV", "", 8)
    pdf.set_text_color(*KOYU)
    pdf.set_x(14)
    pdf.multi_cell(182, 4.4,
                   "Okuma notu: son sütun iki rolün toplam ağırlığını gösterir. "
                   "Matris sürekli DÜŞÜK toplamlı rolü öneriyorsa, o rolün istediği "
                   "nitelikler oyuncularda yüksek not alıyor demektir; ağırlıkların "
                   "dağılımına bakmak gerekir.")

    # ── B) TEKİL ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*KREM)
    pdf.rect(0, 22, 210, 275, "F")
    pdf.set_font("DV", "B", 10)
    pdf.set_text_color(*KOYU)
    pdf.set_x(14)
    pdf.cell(0, 7, "B) EN BÜYÜK FARKLI TEKİL VAKALAR", ln=1)
    pdf.set_font("DV", "", 7)
    pdf.set_text_color(*GRI)
    pdf.set_x(14)
    pdf.cell(0, 4, "Atanan rol ile önerilen rol arasındaki puan farkı en yüksek 40 oyuncu.", ln=1)
    pdf.ln(1)

    tekil = []
    for (a, b), lst in ciftler.items():
        for isim, kaynak, fark, mev in lst:
            if fark is not None:
                tekil.append((fark, isim, kaynak, mev, a, b))
    tekil.sort(reverse=True)

    bas2 = [("Fark", 14), ("Oyuncu", 46), ("Mevki", 24), ("Atanan", 44), ("Önerilen", 44)]
    pdf.set_font("DV", "B", 7.5)
    pdf.set_fill_color(*KOYU)
    pdf.set_text_color(*KREM)
    pdf.set_x(14)
    for b_, w in bas2:
        pdf.cell(w, 6, b_, fill=True, align="C")
    pdf.ln(6)
    pdf.set_font("DV", "", 7.5)
    for i, (fark, isim, kaynak, mev, a, b) in enumerate(tekil[:40]):
        pdf.set_fill_color(238, 234, 226) if i % 2 else pdf.set_fill_color(*KREM)
        pdf.set_text_color(*KOYU)
        pdf.set_x(14)
        pdf.cell(14, 5.2, f"+{fark:.0f}", fill=True, align="C")
        pdf.cell(46, 5.2, f" {isim[:26]}", fill=True)
        pdf.cell(24, 5.2, f" {mev[:12]}", fill=True)
        pdf.cell(44, 5.2, f" {a[:22]}", fill=True)
        pdf.cell(44, 5.2, f" {b[:22]}", fill=True)
        pdf.ln(5.2)

    pdf.output(str(CIKTI))
    kb = CIKTI.stat().st_size // 1024
    print(f"OK {CIKTI} ({kb} KB)")
    print(f"   örtüşen {ayni} · ayrışan {toplam_ayrisan} · hesaplanamayan {hesapsiz}")
    print(f"   sistematik çift: {len(ciftler)} · tekil vaka: {len(tekil)}")


if __name__ == "__main__":
    main()
