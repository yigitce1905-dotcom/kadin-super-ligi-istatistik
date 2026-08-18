# -*- coding: utf-8 -*-
"""Haymana Spor Kulübü — Paola Blue Ellis RESMÎ TRANSFER TEKLİFİ (iki dilli, Kaio/Markovska şablonu)."""
import sys, pathlib
from fpdf import FPDF

sys.stdout.reconfigure(encoding="utf-8")

# ── OYUNCU KÜNYESİ ──
OYUNCU   = "Sydney Rosa Louise Cradle"
UYRUK    = "ABD / United States"
DOGUM    = "02.05.2002"
TARIH    = "24.07.2026"

# ── MALİ ŞARTLAR (menajerlik komisyonu YOK) ──
AY       = 9
AYLIK    = 500                    # USD net / ay
TOPLAM   = AY * AYLIK             # 4.500 USD

def usd(n):    return f"{n:,}".replace(",", ".")   # TR: 8.100
def usd_en(n): return f"{n:,}"                     # EN: 8,100

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
baslik_ortali("HAYMANA SPOR KULÜBÜ", 14)
baslik_ortali("RESMÎ TRANSFER TEKLİFİ - OFFICIAL TRANSFER OFFER", 12)
pdf.ln(8)

# ── KÜNYE BLOĞU ──
etiket("Tarih / Date:", TARIH)
etiket("Oyuncunun Adı Soyadı / Player's Full Name:", OYUNCU)
etiket("Uyruğu / Nationality:", UYRUK)
etiket("Doğum Tarihi / Date of Birth:", DOGUM)
pdf.set_font("TMS", "B", 11)
pdf.multi_cell(0, 6.5, "2026–2027 Sezonu / 2026–2027 Season")
pdf.ln(4)

# ── GİRİŞ ──
para(f"Sayın {OYUNCU},")
para("Haymana Spor Kulübü olarak, 2026–2027 futbol sezonunda kadın futbol takımımızda forma "
     "giymeniz amacıyla aşağıdaki şartları içeren resmî teklifimizi sunmaktan memnuniyet duyarız.")
para(f"Dear {OYUNCU},")
para("Haymana Sports Club is pleased to present you with this official offer to join our women's "
     "football team for the 2026–2027 football season under the following terms and conditions.")

# ── 1. SÖZLEŞME SÜRESİ ──
bolum("1. SÖZLEŞME SÜRESİ / CONTRACT TERM")
para(f"Oyuncuyla {AY} aylık futbolcu sözleşmesi imzalanacaktır.")
para(f"A {AY}-month football player contract will be signed with the player.")

# ── 2. MAAŞ ──
bolum("2. MAAŞ / SALARY")
para(f"Oyuncuya sözleşme süresince aylık net {AYLIK} USD maaş ödenecektir.")
para(f"Toplam dokuz aylık sözleşme bedeli net {usd(TOPLAM)} USD olacaktır.")
para("Maaş ödemeleri, dokuz eşit aylık ödeme hâlinde gerçekleştirilecektir. Ödemeler USD olarak "
     "yapılacaktır. Farklı bir ödeme şekli ancak tarafların yazılı mutabakatıyla uygulanabilir.")
para(f"The player will receive a net monthly salary of USD {AYLIK} during the contract period.")
para(f"The total net salary for the nine-month contract period will be USD {usd_en(TOPLAM)}.")
para("The salary will be paid in nine equal monthly instalments. Payments will be made in USD "
     "unless otherwise agreed in writing by the parties.")

# ── 3. KONAKLAMA ──
bolum("3. KONAKLAMA / ACCOMMODATION")
para("Sözleşme süresince oyuncunun konaklaması Haymana Spor Kulübü tarafından ücretsiz olarak sağlanacaktır.")
para("Accommodation will be provided to the player free of charge by Haymana Sports Club "
     "throughout the contract period.")

# ── 4. YEMEK ──
bolum("4. YEMEK / MEALS")
para("Oyuncuya sözleşme süresince her gün iki öğün yemek sağlanacaktır.")
para("The player will be provided with two meals per day throughout the contract period.")

# ── 5. UÇAK BİLETİ ──
bolum("5. UÇAK BİLETİ / FLIGHT TICKET")
para("Kulüp, oyuncuya sözleşme dönemi için bir adet ekonomi sınıfı gidiş-dönüş uçak bileti sağlayacaktır.")
para("Uçak bileti, oyuncunun ikamet ettiği ülke ile Türkiye arasındaki seyahati kapsayacaktır. "
     "Seyahat tarihleri kulüp ve oyuncu tarafından birlikte belirlenecektir.")
para("The club will provide the player with one economy-class round-trip flight ticket for the contract period.")
para("The ticket will cover travel between the player's country of residence and Türkiye. "
     "The travel dates will be determined jointly by the club and the player.")

# ── 6. TAKIM PRİMLERİ ──
bolum("6. TAKIM PRİMLERİ VE BONUSLAR / TEAM BONUSES")
para("Oyuncu; maç, galibiyet, başarı veya performans nedeniyle kulüp yönetimi tarafından kadın "
     "futbol takımına dağıtılmasına karar verilen prim ve bonuslardan, kulüp yönetiminin "
     "belirleyeceği şartlar ve oranlar dâhilinde yararlanma hakkına sahip olacaktır.")
para("The player will be entitled to receive match, victory, achievement or performance bonuses "
     "distributed to the women's football team, subject to the conditions and payment rates "
     "determined by the club management.")

# ── 7. GENEL HÜKÜMLER ──
bolum("7. GENEL HÜKÜMLER / GENERAL CONDITIONS")
para("Bu belge, Haymana Spor Kulübü tarafından sunulan resmî transfer teklifini göstermektedir. "
     "Transferin tamamlanması; oyuncunun sağlık kontrolünden geçmesine, gerekli çalışma ve oturma "
     "izinlerinin alınabilmesine, Türkiye Futbol Federasyonu nezdindeki tescil işlemlerinin "
     "tamamlanmasına ve taraflar arasında nihai futbolcu sözleşmesinin imzalanmasına bağlıdır.")
para("Nihai sözleşmede yer alacak hükümler, bu teklif metninde belirtilen temel mali ve sosyal "
     "şartlarla çelişmeyecektir.")
para("This document represents the official transfer offer made by Haymana Sports Club. Completion "
     "of the transfer will be subject to the player successfully passing the medical examination, "
     "obtaining the necessary work and residence permits, completing the registration procedures "
     "before the Turkish Football Federation and signing the final football player contract between "
     "the parties.")
para("The provisions of the final contract shall not contradict the principal financial and social "
     "conditions stated in this offer.")

# ── İMZA BLOKLARI ──
pdf.ln(6)
para("HAYMANA SPOR KULÜBÜ ADINA", bold=True, gap=1)
para("FOR AND ON BEHALF OF HAYMANA SPORTS CLUB", bold=True, gap=8)
para("İmza / Signature:", bold=True, gap=3)
para("Tarih / Date:", bold=True, gap=12)

para("OYUNCUNUN TEKLİFİ KABULÜ", bold=True, gap=1)
para("PLAYER'S ACCEPTANCE OF THE OFFER", bold=True, gap=4)
para("Yukarıda belirtilen şartları okuduğumu, anladığımı ve Haymana Spor Kulübü tarafından tarafıma "
     "sunulan bu teklifi kabul ettiğimi beyan ederim.")
para("I hereby confirm that I have read and understood the conditions stated above and that I "
     "accept the offer presented to me by Haymana Sports Club.")
pdf.ln(4)
para("Oyuncunun Adı Soyadı / Player's Full Name:", bold=True, gap=8)
para("İmza / Signature:", bold=True, gap=8)
para("Tarih / Date:", bold=True, gap=2)

cikti = pathlib.Path.home() / "Desktop" / "Resmi_Teklif_Haymana_Cradle.pdf"
pdf.output(str(cikti))
print(f"OK {cikti} ({cikti.stat().st_size // 1024} KB)")
