# -*- coding: utf-8 -*-
"""Haymanaspor Kulübü — Aleksandra Markovska FINAL OFFER (Amed şablonu, mavi-beyaz)."""
import sys, pathlib
from fpdf import FPDF

sys.stdout.reconfigure(encoding="utf-8")
SIYAH = (20, 24, 30); GRI = (110, 118, 128)
MAVI = (26, 63, 170); LACIVERT = (16, 34, 96)     # Haymana mavi-beyaz
F = r"C:\Windows\Fonts"
LOGO = r"C:\Users\MSI\Desktop\tff_kadin_ligi\static\armalar\haymana.jpg"

pdf = FPDF(orientation="P", unit="mm", format="A4")
pdf.add_font("TMS", "",  rf"{F}\times.ttf")
pdf.add_font("TMS", "B", rf"{F}\timesbd.ttf")
pdf.add_font("TMS", "I", rf"{F}\timesi.ttf")
pdf.set_auto_page_break(True, margin=20)
pdf.set_margins(22, 16, 22)
pdf.add_page()

# ── Antet: logo + kulüp + mavi çizgi ──
pdf.image(LOGO, x=(210 - 22) / 2, y=14, w=22)
pdf.set_y(38)
pdf.set_font("TMS", "B", 16); pdf.set_text_color(*SIYAH)
pdf.cell(0, 8, "HAYMANASPOR KULÜBÜ", align="C", ln=1)
pdf.set_font("TMS", "", 11); pdf.set_text_color(*GRI)
pdf.cell(0, 6, "Women's Football Team", align="C", ln=1)
y = pdf.get_y() + 2
pdf.set_draw_color(*LACIVERT); pdf.set_line_width(0.8); pdf.line(22, y, 105, y)
pdf.set_draw_color(*MAVI); pdf.line(105, y, 188, y)
pdf.ln(10)

# ── Tarih (sağ) ──
pdf.set_font("TMS", "B", 11); pdf.set_text_color(*SIYAH)
pdf.cell(0, 6, "21.07.2026", align="R", ln=1)
pdf.ln(4)

# ── Başlık ──
pdf.set_font("TMS", "B", 13)
pdf.cell(0, 8, "TO WHOM IT MAY CONCERN — FINAL OFFER", ln=1)
pdf.ln(4)

pdf.set_font("TMS", "", 11.5); pdf.set_text_color(*SIYAH)
pdf.multi_cell(0, 6.4, "Dear Sir/Madam,")
pdf.ln(1)
pdf.multi_cell(0, 6.4,
    "We will be happy to see Ms. Aleksandra Markovska in Haymanaspor Kulübü "
    "Women's Football Team for the 2026-2027 season.")
pdf.ln(4)

pdf.set_font("TMS", "B", 12)
pdf.cell(0, 7, "Our final offer for the player:", ln=1)
pdf.set_draw_color(*SIYAH); pdf.set_line_width(0.3)
pdf.line(22, pdf.get_y(), 22 + pdf.get_string_width("Our final offer for the player:"), pdf.get_y())
pdf.ln(3)

maddeler = [
    "800 US DOLLAR net monthly salary",
    "Win bonus: minimum 200 US DOLLAR per official match won",
    "Accommodation: room in club facility",
    "Round trip flight ticket (home country – Türkiye)",
    "3 meals (breakfast, lunch, dinner in club facilities)",
]
pdf.set_font("TMS", "", 11.5)
for m in maddeler:
    pdf.set_x(28)
    pdf.cell(5, 6.6, "•")
    pdf.multi_cell(0, 6.6, m)
    pdf.ln(0.8)

pdf.ln(4)
pdf.multi_cell(0, 6.4, "We ask for your opinion on the relevant topic.")
pdf.ln(12)

pdf.multi_cell(0, 6.4, "Kind Regards,")
pdf.ln(14)
pdf.set_draw_color(*GRI); pdf.set_line_width(0.3)
pdf.line(22, pdf.get_y(), 90, pdf.get_y())
pdf.ln(1.5)
pdf.set_font("TMS", "B", 11)
pdf.cell(0, 6, "Sports Director / Transfer Committee", ln=1)
pdf.set_font("TMS", "", 11)
pdf.cell(0, 6, "Haymanaspor Kulübü — Women's Football Team", ln=1)

# ── alt bilgi mavi çizgi ──
pdf.set_y(-22)
yb = pdf.get_y()
pdf.set_draw_color(*LACIVERT); pdf.set_line_width(0.6); pdf.line(22, yb, 105, yb)
pdf.set_draw_color(*MAVI); pdf.line(105, yb, 188, yb)

cikti = pathlib.Path.home() / "Desktop" / "Final_Offer_Haymana_Markovska.pdf"
pdf.output(str(cikti))
print(f"✓ {cikti} ({cikti.stat().st_size // 1024} KB)")
