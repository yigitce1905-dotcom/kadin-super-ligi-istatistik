# -*- coding: utf-8 -*-
"""Fatih Vatan Spor Kulübü — Angel Halla Fowler teklifi (No. 2026/4) üzerine ISM'in
eklediği tamamlayıcı şartlarla birlikte İNGİLİZCE tam metin. Orijinal kulüp
antetli belgesi değildir; kulübün gönderdiği asıl şartlar + ISM'in eklediği
menajerlik/aracılık/ödeme takvimi/uçuş düzeltmesi/clean sheet primi birleştirilmiştir."""
import sys, pathlib
from fpdf import FPDF

sys.stdout.reconfigure(encoding="utf-8")

# ── OYUNCU KÜNYESİ (Fatih Vatan'ın orijinal teklifinden) ──
OYUNCU     = "Angel Halla Fowler"
UYRUK      = "United Kingdom of Great Britain and Northern Ireland"
DOGUM      = "31.10.2002"
KULUP      = "Fatih Vatan Spor Kulübü"
TEKLIF_NO  = "2026/4"
TARIH      = "05.08.2026"

# ── MALİ ŞARTLAR (orijinal teklif) ──
AY       = 8
AYLIK    = 900
TOPLAM   = AY * AYLIK             # 7.200 USD
KOMISYON = 500                    # sabit (yüzde değil) — kullanıcı talebi
ODEME_BASLANGIC = "September 2026"
ODEME_BITIS     = "April 2027"
CLEAN_SHEET_PRIM = 50

# ── MENAJERLİK / ARACILIK (Sydney Bellamy / Aurea del Carmen sözleşmeleriyle aynı yapı) ──
AJAN_SIRKET  = "Moojen Sports Ventures Pro"
AJAN_YETKILI = "Frederico Moojen"
AJAN_FIFA    = "FIFA Agent ID 202411-8422"
INTERMEDIARY = "Ideal Sports Management"

SIYAH = (20, 24, 30)

pdf = FPDF(orientation="P", unit="mm", format="A4")
F = r"C:\Windows\Fonts"
pdf.add_font("TMS", "",  rf"{F}\times.ttf")
pdf.add_font("TMS", "B", rf"{F}\timesbd.ttf")
pdf.add_font("TMS", "I", rf"{F}\timesi.ttf")
pdf.set_auto_page_break(True, margin=20)
pdf.set_margins(25, 20, 25)
pdf.add_page()
pdf.set_text_color(*SIYAH)

def baslik_ortali(txt, sz=13):
    pdf.set_font("TMS", "B", sz)
    pdf.cell(0, 8, txt, align="C", ln=1)

def bolum(txt):
    pdf.ln(2)
    pdf.set_font("TMS", "B", 11.5)
    pdf.multi_cell(0, 6.6, txt)
    pdf.ln(0.5)

def para(txt, bold=False, gap=2.2):
    pdf.set_font("TMS", "B" if bold else "", 11)
    pdf.multi_cell(0, 6, txt)
    pdf.ln(gap)

def etiket(bold_kisim, deger):
    pdf.set_font("TMS", "B", 11)
    pdf.write(6, bold_kisim + " ")
    pdf.set_font("TMS", "", 11)
    pdf.write(6, deger)
    pdf.ln(6.5)

# ── ANTET ──
baslik_ortali("FATİH VATAN SPOR KULÜBÜ", 14)
baslik_ortali("OFFICIAL OFFER — SUPPLEMENTARY TERMS", 12)
pdf.ln(6)
para(f"This document reflects the terms of Official Offer No. {TEKLIF_NO} issued by "
     f"{KULUP} to the player named below, together with the additional terms agreed "
     f"regarding player representation, payment schedule and performance bonus.", gap=6)

# ── KÜNYE ──
etiket("Date:", TARIH)
etiket("Player:", OYUNCU)
etiket("Date of Birth:", DOGUM)
etiket("Nationality:", UYRUK)
etiket("Club:", f"{KULUP} — Official Offer No. {TEKLIF_NO}")
pdf.ln(3)

# ── 1. ORİJİNAL ŞARTLAR (Fatih Vatan teklifinden aynen) ──
bolum("1. TERMS OF THE CLUB'S OFFICIAL OFFER")
para("Duration of contract: from the signature of the contract up to the last match of "
     "the women's football team of the Club to be played in the 2026/2027 season of the "
     "TFF Women's Super Leagues.")
para(f"{AY} months contract.")
para(f"USD {AYLIK} net salary (after taxes) per month.")
para("Transport to training.")
para("Food.")
para("Housing/Accommodation with bills (electricity, internet, etc.).")
para("The club will be responsible for the legalization of the player in Turkish territory.")

# ── 2. ÖDEME TAKVİMİ ──
bolum("2. SALARY PAYMENT SCHEDULE")
para(f"The monthly net salary of USD {AYLIK} will be paid in {AY} equal monthly "
     f"instalments, covering the period from {ODEME_BASLANGIC} to {ODEME_BITIS}. "
     f"The total net salary for the contract period will be USD {TOPLAM:,}.")

# ── 3. UÇAK BİLETİ (düzeltilmiş) ──
bolum("3. FLIGHT TICKET")
para("Departure and return will be to and from Atlanta, Georgia (USA), with at least "
     "1 bag (23kg) included.")

# ── 4. CLEAN SHEET PRİMİ ──
bolum("4. CLEAN SHEET BONUS")
para(f"The player will be entitled to a bonus of USD {CLEAN_SHEET_PRIM} for every clean "
     "sheet kept in official matches played by the club's women's football team.")

# ── 5. MENAJERLİK KOMİSYONU / ARACILIK ──
bolum("5. AGENT COMMISSION / INTERMEDIARY")
para(f"Upon completion of this transfer and execution of the football player contract, "
     f"{KULUP} will pay an agent commission of USD {KOMISYON} to {AJAN_SIRKET} "
     f"(represented by {AJAN_YETKILI}, {AJAN_FIFA}), the player's representative.")
para(f"{INTERMEDIARY} acts as the intermediary in this transfer.")
para(f"The agent commission will be paid separately by the club and will not be deducted "
     f"from the player's salary.")

# ── 6. GENERAL ──
bolum("6. GENERAL")
para("All other terms and conditions of the club's Official Offer remain unchanged and "
     "in full effect. This document is supplementary to, and shall be read together with, "
     f"{KULUP}'s Official Offer No. {TEKLIF_NO}.")

# ── İMZA BLOKLARI ──
pdf.ln(6)
para("FOR AND ON BEHALF OF FATİH VATAN SPOR KULÜBÜ", bold=True, gap=3)
para("Signature:", bold=True, gap=3)
para("Date:", bold=True, gap=10)

para("PLAYER'S ACCEPTANCE", bold=True, gap=1)
para("I hereby confirm that I have read and understood the terms stated above (together "
     "with the Official Offer No. 2026/4) and that I accept them.", gap=4)
para("Player's Full Name:", bold=True, gap=8)
para("Signature:", bold=True, gap=8)
para("Date:", bold=True, gap=2)

cikti = pathlib.Path.home() / "Desktop" / "Teklif_FatihVatan_Angel_Fowler_Ek_Sartlar.pdf"
pdf.output(str(cikti))
print(f"OK {cikti} ({cikti.stat().st_size // 1024} KB)")
