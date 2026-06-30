"""
Türkiye Kadınlar Süper Ligi 2025-2026 — Streamlit Web Arayüzü
"""
import json, os, pathlib, requests
from urllib.parse import quote as _urlquote
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
try:
    import bcrypt as _bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False
# NOT: plotly.express ve bs4 app'te kullanılmıyordu — kaldırıldı (cold start ~0.3s).
# NOT: groq (AI transfer raporu) verimli değildi — tamamen kaldırıldı.

# ── Render secret bootstrap (st.secrets ilk okunmadan ÖNCE) ────────────────────
# Render "Secret File" adında '/' kabul etmiyor → dosya düz 'secrets.toml' olarak
# /etc/secrets/ altına (veya app köküne) konur. Streamlit ise .streamlit/secrets.toml
# bekler. Burada doğru yere kopyalarız. Lokal/Streamlit Cloud'da kaynak yoktur → no-op.
import shutil as _shutil
for _sec_src in ("/etc/secrets/secrets.toml", "secrets.toml"):
    _sec_dst = pathlib.Path(".streamlit/secrets.toml")
    if os.path.exists(_sec_src) and not _sec_dst.exists():
        _sec_dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            _shutil.copy(_sec_src, _sec_dst)
        except Exception:
            pass
        break

# club_credentials.json: Render "Secret File" olarak yüklenir (/etc/secrets/'a düşer),
# buradan uygulama köküne kopyalanır → kod onu olağan yolla (dosyadan) okur. Repoda DEĞİL.
# Lokalde dosya zaten kökte → kaynak yok, no-op (mevcut dosya korunur).
_cc_src = "/etc/secrets/club_credentials.json"
_cc_dst = pathlib.Path("club_credentials.json")
if os.path.exists(_cc_src) and not _cc_dst.exists():
    try:
        _shutil.copy(_cc_src, _cc_dst)
    except Exception:
        pass

_page_title = "Women's Football Scouting"   # marka adı (tarayıcı sekmesi)
from pathlib import Path as _Path
_favicon = _Path(__file__).parent / "static" / "logo_kare.png"
st.set_page_config(
    page_title=_page_title,
    page_icon=(str(_favicon) if _favicon.exists() else "🎯"), layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Dil (TR varsayılan / EN hedefli sayfalar) ───
# Tercih URL'de (?dil=EN) saklanır → sayfa yenilense de korunur.
if "dil" not in st.session_state:
    _qp_dil = st.query_params.get("dil", "")
    st.session_state["dil"] = _qp_dil if _qp_dil in ("TR", "EN") else "TR"

def t(tr, en):
    """Dile göre metin döndürür (EN seçiliyse İngilizce, değilse Türkçe)."""
    return en if st.session_state.get("dil") == "EN" else tr

EN = st.session_state.get("dil") == "EN"


def _sayfa_banner(img: str, baslik: str, alt: str = ""):
    """Alt sayfa için fotoğraflı banner başlık (static/<img> + koyu overlay). Görsel
    Streamlit statik servisle (app/static/) verilir → rerun'da yeniden gönderilmez."""
    st.markdown(
        f"<div class='sayfa-banner' style=\"background:"
        f"linear-gradient(95deg,#0a0e1bf2 0%,#0b0f1edd 42%,#140c2699 72%,#1d0d2955 100%),"
        f"url('app/static/{img}') center 32%/cover no-repeat;\">"
        f"<div class='sb-baslik'>{baslik}</div>"
        + (f"<div class='sb-alt'>{alt}</div>" if alt else "")
        + "</div>", unsafe_allow_html=True)


# ─── WhatsApp / ödeme iletişim helper'ları (ERKEN tanımlı — pro_paywall_goster/
#     deneme_kilit bunları çağırır; ?oyuncu= route'u paywall'ı bunlardan ÖNCE
#     render ederse NameError olmasın diye dosyanın başında) ───────────────────
def _odeme_bilgi() -> dict:
    """Havale + WhatsApp bilgileri (secrets [odeme]). Yapılandırılmadıysa boş/aktif=False."""
    try:
        d = dict(st.secrets.get("odeme", {}))
    except Exception:
        d = {}
    # WhatsApp numarası herkese gösterilen iletişim bilgisi (gizli değil; e-posta/Instagram gibi
    # zaten koddadır) → varsayılan koda gömülü, secrets [odeme] whatsapp ile override edilebilir.
    return {"iban": d.get("iban", ""), "hesap_adi": d.get("hesap_adi", ""),
            "banka": d.get("banka", ""),
            "whatsapp": str(d.get("whatsapp", "") or "905309546646"),
            "aktif": bool(d.get("iban"))}


def _whatsapp_link(mesaj: str = "") -> str:
    """secrets [odeme] whatsapp numarası varsa önceden-dolu mesajlı wa.me linki, yoksa ''."""
    no = "".join(ch for ch in _odeme_bilgi().get("whatsapp", "") if ch.isdigit())
    if not no:
        return ""
    from urllib.parse import quote
    return f"https://wa.me/{no}" + (f"?text={quote(mesaj)}" if mesaj else "")


def _whatsapp_butonu(mesaj: str = "", etiket_tr: str = "WhatsApp'tan yaz",
                     etiket_en: str = "Message us on WhatsApp"):
    """Yeşil WhatsApp butonu (yeni sekmede wa.me). Numara yoksa hiçbir şey çizmez."""
    _wa = _whatsapp_link(mesaj)
    if not _wa:
        return
    st.markdown(
        f"<a href='{_wa}' target='_blank' style='display:flex;align-items:center;"
        f"justify-content:center;gap:8px;background:#25D366;color:#0b141a;font-weight:800;"
        f"padding:12px 16px;border-radius:10px;text-decoration:none;margin:8px 0;"
        f"font-size:0.95rem;'>💬 {t(etiket_tr, etiket_en)}</a>", unsafe_allow_html=True)


# Profil render bağlam sayacı: aynı çalıştırmada profil birden çok kez
# render edilirse (örn. modal + sekme) widget key'leri çakışmasın diye.
_PROFIL_CTX = {"n": 0}
def _pk(base: str) -> str:
    return f"{base}__{_PROFIL_CTX['n']}"

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sora:wght@600;700;800&family=Oswald:wght@500;600;700&display=swap');

/* ── Streamlit "prototip" chrome'unu gizle (profesyonel görünüm) ──
   ⋮ menü, Deploy, footer ve üst renk şeridi kaldırılır.
   ÖNEMLİ: Header'ı yok etmiyoruz (yalnızca şeffaf) ki sol paneli açan
   ☰ düğmesi erişilebilir kalsın — aksi halde panel kapanınca geri açılamaz. */
/* DİKKAT: stToolbar'ı tümden gizleme! Sol paneli açan ☰ düğmesi onun
   İÇİNDE; gizlersen panel kapanınca geri açılamaz. Yalnızca sağdaki
   aksiyonları (Deploy / ⋮ menü / durum) gizliyoruz. */
#MainMenu { visibility:hidden; }
[data-testid="stToolbarActions"] { display:none !important; }
[data-testid="stAppDeployButton"] { display:none !important; }
[data-testid="stDecoration"] { display:none !important; }
[data-testid="stStatusWidget"] { display:none !important; }
header[data-testid="stHeader"] { background:transparent !important; }
footer { visibility:hidden !important; display:none !important; }
.viewerBadge_link__qRIco, [class*="viewerBadge"] { display:none !important; }
/* Sol panel aç/kapa kontrolü her zaman görünür ve tıklanabilir kalsın */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display:flex !important; visibility:visible !important; opacity:1 !important;
    z-index:1000 !important; }

/* ── Marka kimliği (tek kaynak): Mor = marka/navigasyon · Yeşil = veri/pozitif ── */
:root {
    --marka:        #a855f7;   /* ana mor */
    --marka-koyu:   #7c3aed;
    --marka-acik:   #c084fc;
    --aksan:        #ec4899;   /* pembe vurgu */
    --veri:         #1db954;   /* yeşil — istatistik/pozitif */
    --veri-acik:    #4ade80;
    --zemin:        #0f1117;
    --zemin-kart:   #1a1f36;
    --metin:        #e2e8f0;
    --metin-soluk:  #8899aa;
    --cizgi:        #232a40;
}

/* ── Boşluk/sıkışıklık: gereksiz büyük boşlukları daralt ── */
.block-container { padding-top:2.2rem !important; padding-bottom:2rem !important;
    max-width:1480px !important; }
[data-testid="stVerticalBlock"] { gap:0.55rem; }
[data-testid="stElementContainer"]:empty { display:none; }
[data-testid="stMainBlockContainer"] { padding-top:2.2rem !important; }
/* Geniş modal (oyuncu profili) ── içerik sığsın */
/* Oyuncu profili modalı: geniş + içten kaydırılabilir (görünür sürgü) */
[data-testid="stDialog"] div[role="dialog"] {
    width:min(960px,94vw) !important;
    max-height:88vh !important;
    overflow-y:auto !important;
    overscroll-behavior:contain;
}
[data-testid="stDialog"] div[role="dialog"]::-webkit-scrollbar { width:12px; }
[data-testid="stDialog"] div[role="dialog"]::-webkit-scrollbar-track { background:#11162a; border-radius:6px; }
[data-testid="stDialog"] div[role="dialog"]::-webkit-scrollbar-thumb {
    background:#7c3aed; border-radius:6px; border:2px solid #11162a; }
[data-testid="stDialog"] div[role="dialog"]::-webkit-scrollbar-thumb:hover { background:#a855f7; }

/* ── Genel ── */
.stApp { background-color:#0f1117; color:#e0e0e0;
    font-family:'Inter',-apple-system,'Segoe UI',sans-serif; }
.stApp h1, .stApp h2, .stApp h3 {
    font-family:'Oswald','Sora','Inter',sans-serif; letter-spacing:0.005em; font-weight:700; }
.stApp h4, .stApp h5 { font-family:'Inter',sans-serif; font-weight:700; }
.main hr { border-color:#1d2336; }

/* ── Başlık / Hero ── */
.baslik-kutu {
    position:relative; overflow:hidden;
    background:
       linear-gradient(100deg, #0a0e1bf7 0%, #0b0f1eee 40%, #140c26c2 66%, #1d0d2982 100%),
       url('app/static/hero.jpg') center 28%/cover no-repeat;
    border:1px solid #2c2350; border-radius:16px;
    padding:30px 34px 26px; margin-bottom:24px;
    box-shadow:0 14px 44px -14px #00000088, inset 0 1px 0 #ffffff12;
}
.baslik-kutu::before { content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg,#7c3aed 0%,#a855f7 42%,#ec4899 76%,#f59e0b 100%); }
.baslik-kutu .ust-bant { position:relative; font-size:0.66rem; font-weight:800; letter-spacing:0.26em;
    color:#c084fc; text-transform:uppercase; margin-bottom:11px; }
.baslik-kutu h1 { position:relative; color:#fff; font-size:2.4rem; font-weight:700; margin:0 0 9px 0;
    letter-spacing:0.01em; line-height:1.06; }
.baslik-kutu h1 .vurgu {
    background:linear-gradient(90deg,#c084fc,#ec4899);
    -webkit-background-clip:text; background-clip:text; color:transparent; }
.baslik-kutu p  { position:relative; color:#9fb0c6; margin:0; font-size:0.92rem; line-height:1.6;
    max-width:660px; }
.hero-chips { position:relative; display:flex; gap:9px; flex-wrap:wrap; margin-top:17px; }
.hero-chip { font-size:0.7rem; font-weight:700; letter-spacing:0.05em;
    color:#e2e8f0; background:#ffffff10; border:1px solid #ffffff24;
    border-radius:8px; padding:6px 13px; white-space:nowrap; }
.hero-chip b { color:#4ade80; font-family:'Sora',monospace; }
/* ── Alt sayfa banner'ı (fotoğraflı başlık) ── */
.sayfa-banner { position:relative; border:1px solid #2c2350; border-radius:14px;
    padding:24px 28px; margin:2px 0 18px; overflow:hidden;
    box-shadow:0 10px 36px -16px #000000aa; }
.sayfa-banner::before { content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg,#7c3aed,#a855f7 45%,#ec4899 80%,#f59e0b); }
.sayfa-banner .sb-baslik { position:relative; font-family:'Oswald','Sora',sans-serif; color:#fff;
    font-size:1.7rem; font-weight:700; letter-spacing:0.01em; line-height:1.12; }
.sayfa-banner .sb-alt { position:relative; color:#aebbd0; font-size:0.9rem; margin-top:6px;
    max-width:580px; line-height:1.5; }

/* ── Özet kartlar ── */
.stat-kart { background:linear-gradient(180deg,#1a2038,#12162a);
    border:1px solid #232a45; border-radius:14px; padding:15px 12px;
    text-align:center; margin-bottom:6px;
    /* Satır içi kartlar eşit yükseklik + içerik dikey ortalı */
    min-height:92px; height:100%;
    display:flex; flex-direction:column; justify-content:center;
    transition:transform .15s ease, border-color .15s ease, box-shadow .15s ease; }
.stat-kart:hover { transform:translateY(-2px); border-color:#33406a;
    box-shadow:0 10px 26px -14px #000000aa; }
/* ── Üyelik paket kartları ── */
.paket-kart { transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease; }
.paket-kart:hover { transform:translateY(-3px); box-shadow:0 18px 42px -18px #000000c0; }
/* ── Hizmet (danışmanlık) kartları ── */
.hizmet-kart { transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease; }
.hizmet-kart:hover { transform:translateY(-3px); box-shadow:0 14px 34px -16px #000000b0; border-color:#33406a !important; }
.stat-kart .sayi   { font-size:1.6rem; font-weight:800; color:#1db954;
    font-family:'Sora',sans-serif; line-height:1.12; white-space:nowrap; }
.stat-kart .etiket { font-size:0.66rem; color:#8899aa; margin-top:4px;
    text-transform:uppercase; letter-spacing:0.06em; font-weight:600; line-height:1.25; }
/* Stat kartları içeren sütun satırlarını eşit yükseklikte ger */
[data-testid="stHorizontalBlock"]:has(.stat-kart) { align-items:stretch; }
[data-testid="stHorizontalBlock"]:has(.stat-kart) [data-testid="stColumn"] > div { height:100%; }

/* ── Profil kartı ── */
.profil-kart { background:#1a1f36; border-radius:14px; padding:22px 26px;
    border-left:4px solid #1db954; }
.profil-kart h2 { color:#fff; margin:0 0 4px 0; font-size:1.35rem; }
.profil-stat { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
.profil-stat-item { background:#0f1117; border-radius:8px; padding:10px 14px;
    text-align:center; min-width:70px; flex:1 1 70px; }
.profil-stat-item .deger { font-size:1.4rem; font-weight:700; color:#1db954; }
.profil-stat-item .ad    { font-size:0.68rem; color:#8899aa; margin-top:2px; }

/* ── Diğer bileşenler ── */
.transfer-badge { display:inline-block; background:#1a3a2a; color:#1db954;
    font-size:0.7rem; border-radius:6px; padding:2px 7px; margin-left:6px; }
.takim-detay-satir { background:#0f1117; border-radius:8px; padding:9px 14px;
    margin-bottom:6px; display:flex; justify-content:space-between;
    align-items:center; flex-wrap:wrap; gap:6px; }
.takim-detay-satir .td-adi   { color:#e0e0e0; font-weight:500; }
.takim-detay-satir .td-stats { color:#8899aa; font-size:0.82rem; }
.form-kutu { display:flex; gap:5px; flex-wrap:wrap; margin-top:8px; }
.form-chip { border-radius:6px; padding:4px 8px; font-size:0.78rem;
    font-weight:600; display:inline-block; white-space:nowrap; }
section[data-testid="stSidebar"] { background-color:#12161f; }
.altbilgi { text-align:center; color:#505870; font-size:0.76rem;
    margin-top:36px; padding-top:14px; border-top:1px solid #1e2340; }

/* ── Scouting odaklı profil: büyük isim + gruplu bilgi kutuları ── */
.sc-isim { font-family:'Oswald','Sora',sans-serif; font-size:2.3rem; font-weight:700;
    color:#f5f8ff; line-height:1.06; letter-spacing:0.01em; }
.sc-mevki { color:#93c5fd; font-size:0.96rem; margin:7px 0 2px; font-weight:600; }
.bilgi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
    gap:12px; margin:18px 0 22px; }
.bilgi-kutu { background:linear-gradient(180deg,#101829,#0d1320);
    border:1px solid #243149; border-radius:13px; padding:15px 17px; }
.bk-baslik { font-size:0.64rem; font-weight:800; letter-spacing:0.13em;
    text-transform:uppercase; color:#60a5fa; margin-bottom:11px;
    padding-bottom:8px; border-bottom:1px solid #1c2740; }
.bk-satir { display:flex; justify-content:space-between; gap:12px;
    font-size:0.87rem; padding:5px 0; }
.bk-satir > span { color:#7c8aa3; white-space:nowrap; }
.bk-satir > b { color:#e8eef7; font-weight:600; text-align:right; }

/* ── Scouting listesi: W-Scope tarzı keskin/profesyonel tablo ── */
.ws-wrap { background:#0d0d16; border:1px solid #2a2a38; border-radius:12px;
    overflow:auto; max-height:640px; }
.ws-table { width:100%; border-collapse:collapse; font-size:0.8rem; }
.ws-table thead th { position:sticky; top:0; z-index:2; background:#0d0d16;
    text-align:left; padding:10px 12px; font-size:0.6rem; font-weight:700;
    text-transform:uppercase; letter-spacing:0.13em; color:#71717a;
    border-bottom:1px solid #2a2a38; white-space:nowrap; }
.ws-table th.num, .ws-table td.num { text-align:right; }
.ws-table tbody tr { border-bottom:1px solid #1a1a28; transition:background .12s; }
.ws-table tbody tr:hover { background:#13131f; }
.ws-table td { padding:9px 12px; color:#d4d4d8; white-space:nowrap; vertical-align:middle; }
.ws-ava { width:28px; height:28px; border-radius:50%; background:#221f33;
    color:#a78bfa; display:inline-flex; align-items:center; justify-content:center;
    font-weight:800; font-size:0.78rem; flex-shrink:0; }
.ws-name { color:#f4f4f5; font-weight:600; text-decoration:none; }
.ws-name:hover { color:#c4b5fd; }
.ws-sub { color:#71717a; font-size:0.64rem; margin-top:1px; }
.ws-pos { background:#2a2a38; color:#d4d4d8; padding:2px 7px; border-radius:5px;
    font-size:0.64rem; font-family:'Sora',monospace; font-weight:700; }
.ws-mono { font-family:'Sora',monospace; }
.ws-ring { width:30px; height:30px; border-radius:50%; border:2px solid;
    display:inline-flex; align-items:center; justify-content:center;
    font-size:0.6rem; font-weight:800; font-family:'Sora',monospace; }

/* Benzer Oyuncular — yan yana kutular (5'li grid, mobilde otomatik sarar) */
.benzer-grid { display:flex; flex-wrap:wrap; gap:8px; margin-top:4px; }
.benzer-kutu { background:#0d0d16; border:1px solid #2a2a38; border-radius:11px;
    padding:11px 8px; text-align:center; height:100%;
    transition:border-color .14s, transform .14s, background .14s; }
.benzer-kutu:hover { border-color:#6366f1; background:#13131f; transform:translateY(-2px); }
.benzer-kutu .bk-skor { font-size:1.12rem; font-weight:800; font-family:'Sora',monospace; line-height:1; }
.benzer-kutu .bk-ad   { font-size:0.82rem; font-weight:700; color:#f4f4f5; margin:5px 0 4px;
    line-height:1.2; }
.benzer-kutu .bk-alt  { font-size:0.64rem; color:#8b93a7; line-height:1.35; }
/* Öne çıkan (ilk) öneri — büyük kart */
.benzer-buyuk { padding:16px 14px;
    background:linear-gradient(135deg,#15101f,#0d0d16); border-color:#3a3358; }
.benzer-buyuk .bk-skor { font-size:1.75rem; }
.benzer-buyuk .bk-ad   { font-size:1.08rem; margin:7px 0 5px; }
.benzer-buyuk .bk-alt  { font-size:0.72rem; }

/* ══════════════════════════════════════════════════
   MOBİL RESPONSIVE  (≤ 768px)
══════════════════════════════════════════════════ */
@media (max-width: 768px) {

    /* Streamlit sütunlarını dikey yığ */
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0 !important;
    }
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* Hero/başlık kompakt: uzun açıklama mobilde gizli (yer kazandırır,
       içerik daha yukarıda başlar — özellikle iç sayfalarda). Chip'ler kalır. */
    .baslik-kutu { padding:13px 15px; margin-bottom:12px; }
    .baslik-kutu h1 { font-size:1.18rem; }
    .baslik-kutu p  { display:none; }
    .baslik-kutu .ust-bant { font-size:0.58rem; margin-bottom:5px; }
    .hero-chips { margin-top:10px; gap:6px; }
    .hero-chip { font-size:0.6rem; padding:3px 8px; }

    /* Özet kartlar 2'li grid */
    .stat-kart { padding:10px 12px; margin-bottom:4px; min-height:72px; }
    .stat-kart .sayi   { font-size:1.5rem; }
    .stat-kart .etiket { font-size:0.68rem; }

    /* Stat kartı satırlarını DİKEY yığma — mobilde 2'li grid (az kaydırma).
       Global sütun-yığma kuralını yalnız bu bloklar için ezer (:has). */
    [data-testid="stHorizontalBlock"]:has(.stat-kart) {
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    [data-testid="stHorizontalBlock"]:has(.stat-kart) > [data-testid="stColumn"],
    [data-testid="stHorizontalBlock"]:has(.stat-kart) > [data-testid="column"] {
        width: calc(50% - 3px) !important;
        flex: 0 0 calc(50% - 3px) !important;
        min-width: calc(50% - 3px) !important;
        margin-bottom: 0 !important;
    }

    /* Profil kartı */
    .profil-kart { padding:14px 16px; }
    .profil-kart h2 { font-size:1.1rem; }
    .profil-stat { gap:7px; }
    .profil-stat-item { padding:8px 10px; min-width:60px; flex:1 1 60px; }
    .profil-stat-item .deger { font-size:1.2rem; }
    .profil-stat-item .ad    { font-size:0.62rem; }

    /* Takım detay satırı */
    .takim-detay-satir { flex-direction:column; align-items:flex-start; }
    .takim-detay-satir .td-stats { font-size:0.75rem; }

    /* Form chip'leri */
    .form-chip { font-size:0.72rem; padding:3px 7px; }

    /* Tablo yatay scroll */
    [data-testid="stDataFrame"] { overflow-x: auto !important; }

    /* Sekme etiketleri küçük */
    [data-testid="stTabs"] button { font-size:0.75rem !important; padding:6px 8px !important; }

    /* Dokunma hedefleri — parmakla rahat tıklama (min ~44px).
       (Eskiden min-height:0 idi → dokunması zordu.) */
    [data-testid="stButton"] button,
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stDownloadButton"] button {
        font-size:0.88rem !important; padding:10px 14px !important;
        min-height:44px !important;
    }
    /* Sol nav: biraz daha kompakt ama yine de rahat tıklanır (~40px) */
    section[data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height:40px !important; padding:8px 12px !important;
        font-size:0.9rem !important;
    }
    /* Form girişleri (selectbox/slider/input) dokunma yüksekliği */
    [data-baseweb="select"] > div,
    .stTextInput input, .stNumberInput input {
        min-height:42px !important;
    }
    /* Banner + buton dikey yığılınca aralık */
    [data-testid="stHorizontalBlock"] [data-testid="column"] { margin-bottom:6px; }

    /* Genel padding azalt */
    .block-container { padding:1rem 0.75rem !important; }

    /* Plotly grafik yüksekliği azalt */
    .js-plotly-plot { max-height:300px; }

    /* ── Liste tablosu (.ws-table) → mobilde KART düzeni ───────────────────
       8-10 sütun 375px'e sığmıyordu (yatay taşma; sadece isim + yarım pozisyon
       görünüyordu). Her satır kompakt bir karta döner: üstte isim+uyruk, altta
       etiketli stat'lar (data-label ::before ile). Masaüstü tablo aynen kalır. */
    .ws-wrap {
        overflow-x: visible !important; max-height: none !important;
        background: transparent !important; border: none !important; padding: 0 !important;
    }
    .ws-table, .ws-table tbody, .ws-table tr, .ws-table td { display: block; width: 100%; }
    .ws-table thead { display: none; }
    .ws-table tbody tr {
        display: flex; flex-wrap: wrap; align-items: center; gap: 6px 16px;
        background: #0d0d16; border: 1px solid #2a2a38; border-radius: 12px;
        padding: 12px 14px; margin-bottom: 10px;
    }
    .ws-table tbody tr:hover { background: #0d0d16; }
    .ws-table tbody td {
        display: inline-flex; align-items: center; gap: 5px;
        width: auto; max-width: 100%; min-width: 0;
        padding: 0; border: none; white-space: normal;   /* uzun değerler (takım adı) sarsın → taşma yok */
        font-size: 0.8rem;
    }
    /* İsim hücresi tam genişlik üst satır + ayraç çizgi */
    .ws-table tbody td:first-child {
        flex: 1 1 100%; padding-bottom: 9px; margin-bottom: 3px;
        border-bottom: 1px solid #1c1c2a; white-space: normal;
    }
    .ws-table tbody td:first-child .ws-name { font-size: 0.95rem; }
    /* Etiketli stat hücreleri: küçük gri başlık + değer */
    .ws-table tbody td[data-label]::before {
        content: attr(data-label); color: #6b7280;
        font-size: 0.6rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 0.03em;
    }
}

/* ═══════════════════════════════════════
   KÜÇÜK MOBİL  (≤ 480px)
═══════════════════════════════════════ */
@media (max-width: 480px) {
    .baslik-kutu h1 { font-size:1rem; }
    .profil-stat-item { min-width:52px; flex:1 1 52px; }
    .profil-stat-item .deger { font-size:1rem; }
    [data-testid="stTabs"] button { font-size:0.68rem !important; padding:5px 6px !important; }
}

/* ══════════════════════════════════════════════════
   STREAMLIT BİLEŞEN KESKİNLEŞTİRME (chrome)
══════════════════════════════════════════════════ */

/* Sekmeler: kompakt, uppercase, gradient aktif çizgi */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap:2px; border-bottom:1px solid #232838; }
[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-size:0.72rem; font-weight:700; letter-spacing:0.04em;
    color:#8090a4; padding:9px 13px; }
[data-testid="stTabs"] button[data-baseweb="tab"]:hover { color:#d8b4fe; }
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] { color:#ffffff; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background:linear-gradient(90deg,#a855f7,#ec4899) !important; height:3px !important; }
[data-testid="stTabs"] [data-baseweb="tab-border"] { background:#232838; }

/* ══════════════════════════════════════════════════
   SOL NAVİGASYON — SİTE AĞACI
   (native sekme barı gizli; tüm gezinme sol panelde)
══════════════════════════════════════════════════ */
/* Native sekme barını gizle — yine de JS ile tıklanabilir kalsın */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    height:0 !important; min-height:0 !important; overflow:hidden !important;
    opacity:0 !important; pointer-events:none !important;
    margin:0 !important; padding:0 !important; border:none !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display:none !important; }

/* Sol panel kabı */
section[data-testid="stSidebar"] { background-color:#0c1020 !important;
    border-right:1px solid #232a40; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:0.2rem; }

/* Marka */
.nav-marka { font-family:'Sora',sans-serif; font-weight:800; font-size:1.18rem;
    color:#fff; padding:2px 4px 0; letter-spacing:-0.01em; }
.nav-marka span { color:#a855f7; }
.nav-marka-alt { color:#566179; font-size:0.62rem; padding:0 4px 8px;
    border-bottom:1px solid #1c2238; margin-bottom:2px; }
/* Marka logosu (görsel) */
.nav-marka-logo { padding:6px 4px 14px; margin-bottom:4px; text-align:center;
    border-bottom:1px solid #1c2238; }
.nav-marka-logo img { width:100%; max-width:205px; height:auto; display:inline-block;
    filter:drop-shadow(0 4px 16px rgba(168,85,247,0.40));
    transition:transform .28s ease, filter .28s ease; }
.nav-marka-logo img:hover { transform:translateY(-1px) scale(1.025);
    filter:drop-shadow(0 7px 22px rgba(236,72,153,0.55)); }
@keyframes marka-belir { from{opacity:0; transform:translateY(-6px) scale(.96);}
    to{opacity:1; transform:none;} }
.nav-marka-logo img { animation:marka-belir .55s cubic-bezier(.2,.8,.2,1) both; }

/* Grup başlığı — keskin alt çizgi */
.nav-grup { font-size:0.6rem; font-weight:800; letter-spacing:0.16em;
    color:#6b7494; text-transform:uppercase; margin:15px 4px 7px;
    padding-bottom:5px; border-bottom:1px solid #222a42; }

/* Nav butonları — sol hizalı, düz, net */
section[data-testid="stSidebar"] [data-testid="stButton"] button {
    text-align:left; justify-content:flex-start; width:100%;
    font-size:0.82rem; font-weight:600; line-height:1.2;
    padding:7px 12px; border-radius:6px;
    background:transparent; border:1px solid transparent; color:#aeb8cc; }
section[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background:#161c30; border-color:#283050; color:#fff; }
/* Aktif öğe — düz koyu-mor dolgu + keskin sol aksan çizgisi */
section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
    background:#1b1540 !important; border:1px solid #4c3a8f !important;
    border-left:3px solid #a855f7 !important; color:#fff !important; }
section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover {
    background:#231a52 !important; }

/* Butonlar */
[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
    border-radius:6px; font-weight:600; font-size:0.84rem;
    border:1px solid #2a3146; transition:border-color .15s, color .15s; }
[data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover {
    border-color:#a855f7; color:#e9d5ff; }
[data-testid="stButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background:linear-gradient(135deg,#7c3aed,#db2777); border:none; color:#fff; }
[data-testid="stButton"] button[kind="primary"]:hover {
    background:linear-gradient(135deg,#8b5cf6,#ec4899); color:#fff; }

/* Girdi alanları */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    border-radius:6px; font-size:0.86rem; }
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color:#a855f7; box-shadow:0 0 0 1px #a855f766; }
[data-testid="stSelectbox"] > div > div { border-radius:6px; }

/* Etiketler */
[data-testid="stWidgetLabel"] p { font-size:0.74rem; font-weight:600;
    color:#9aa6ba; letter-spacing:0.02em; }

/* Expander */
[data-testid="stExpander"] {
    border:1px solid #232838; border-radius:8px; background:#12151f; }
[data-testid="stExpander"] summary { font-size:0.84rem; font-weight:600; }
[data-testid="stExpander"] summary:hover { color:#d8b4fe; }

/* Dataframe */
[data-testid="stDataFrame"] {
    border:1px solid #232838; border-radius:8px; overflow:hidden; }

/* Metric kartları */
[data-testid="stMetric"] {
    background:linear-gradient(180deg,#151a2c,#121624);
    border:1px solid #232838; border-left:3px solid #a855f7;
    border-radius:8px; padding:12px 16px; }
[data-testid="stMetric"] label { font-size:0.7rem !important;
    text-transform:uppercase; letter-spacing:0.07em; color:#8899aa !important; }
[data-testid="stMetricValue"] { font-family:'Sora',sans-serif; }

/* Bilgi/uyarı kutuları */
[data-testid="stAlert"] { border-radius:8px; border:1px solid #232838; }

/* Radio (sekme görünümü) */
[data-testid="stRadio"] label p { font-size:0.82rem; }

/* Kaydırma çubuğu */
::-webkit-scrollbar { width:9px; height:9px; }
::-webkit-scrollbar-track { background:#0f1117; }
::-webkit-scrollbar-thumb { background:#2a3146; border-radius:5px; }
::-webkit-scrollbar-thumb:hover { background:#7c3aed; }

/* Caption */
[data-testid="stCaptionContainer"] { color:#5b667a; }

</style>""", unsafe_allow_html=True)

# Sol menü aç/kapa oklarının (<< / >>) yanına dile göre etiket ("Gizle" / "Menü")
st.markdown(f"""<style>
[data-testid="stSidebarCollapseButton"] button::after {{
    content:"{t('Gizle','Hide')}"; font-family:'Sora',sans-serif; font-size:0.72rem;
    font-weight:700; letter-spacing:0.02em; margin-left:5px; color:#c084fc; }}
[data-testid="stExpandSidebarButton"]::after {{
    content:"{t('Menü','Menu')}"; font-family:'Sora',sans-serif; font-size:0.72rem;
    font-weight:700; letter-spacing:0.02em; margin-left:5px; color:#c084fc; }}
[data-testid="stExpandSidebarButton"] {{ width:auto !important; padding:4px 10px !important; }}
</style>""", unsafe_allow_html=True)

# ─── VERİ ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def veri_yukle():
    yol = pathlib.Path(__file__).parent / "oyuncular.json"
    if not yol.exists():
        st.warning(t("oyuncular.json bulunamadı.", "oyuncular.json not found."))
        return pd.DataFrame(), []
    with open(yol, encoding="utf-8") as f:
        liste = json.load(f)
    df = pd.DataFrame([
        {k: v for k, v in o.items() if k not in ("takim_detay","mac_gecmisi")}
        for o in liste
    ])
    col_map = {
        "oyuncu":"Oyuncu","takim":"Takım","tum_takimlar":"TümTakımlar",
        "transfer":"Transfer","mac_sayisi":"Maç","ilk11_mac":"İlk11",
        "yedek_mac":"Yedek","gol_sayisi":"Gol","gol_ayak":"GolF",
        "gol_kafa":"GolH","penalti_gol":"GolP","gol_ort":"Gol/Maç",
        "sari_kart":"Sarı","kirmizi_kart":"Kırmızı","toplam_dakika":"Dakika",
    }
    df.rename(columns=col_map, inplace=True)
    for s in ["Maç","İlk11","Yedek","Gol","GolF","GolH","GolP","Sarı","Kırmızı","Dakika"]:
        if s not in df.columns: df[s] = 0
        df[s] = pd.to_numeric(df[s], errors="coerce").fillna(0).astype(int)
    df["Gol/Maç"] = pd.to_numeric(df.get("Gol/Maç", 0), errors="coerce").fillna(0.0).round(2)
    if "Transfer"    not in df.columns: df["Transfer"]    = False
    if "TümTakımlar" not in df.columns: df["TümTakımlar"] = df["Takım"]
    return df, liste


@st.cache_data(ttl=1800)
def puan_durumu_cek():
    """Kadınlar Süper Ligi puan durumu. Sezon bittiği için yerel
    puan_durumu.json BİRİNCİL kaynaktır (TFF SSL/erişim sorunlarında bile
    tablo görünür); dosya yoksa TFF'den canlı çekilir."""
    yerel = _DIZIN / "puan_durumu.json"
    if yerel.exists():
        try:
            data = json.load(open(yerel, encoding="utf-8"))
            siralar = data.get("siralar", [])
            if siralar:
                kolon = ["O", "G", "B", "M", "A", "Y", "AV", "P"]
                rows = [[s.get("Takım", "")] + [str(s.get(k, "")) for k in kolon]
                        for s in siralar]
                return pd.DataFrame(rows, columns=[""] + kolon)
        except Exception:
            pass
    url = "https://www.tff.org/Default.aspx?pageID=1000&hafta=30"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.content, "lxml")
        tablo = soup.find("table", class_="s-table")
        if not tablo:
            return pd.DataFrame()
        satirlar = []
        for tr in tablo.find_all("tr"):
            huc = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
            if huc: satirlar.append(huc)
        if len(satirlar) < 2:
            return pd.DataFrame()
        # İlk satır başlık — temizle
        baslik = satirlar[0]
        veri   = satirlar[1:]
        df = pd.DataFrame(veri, columns=baslik[:len(veri[0])])
        # Takım adından sıra numarasını ayır (örn. "1.FENERBAHÇE…" → "FENERBAHÇE…")
        takim_col = df.columns[0]
        df[takim_col] = df[takim_col].str.replace(r"^\d+\.", "", regex=True).str.strip()
        return df
    except Exception:
        return pd.DataFrame()


df_tam, ham_liste = veri_yukle()
oyuncu_detay = {o["oyuncu"]: o for o in ham_liste} if ham_liste else {}
# SoccerDonna zenginleştirmesi (sd_profiller yüklendikten sonra)



_DIZIN = pathlib.Path(__file__).parent  # app.py'nin bulunduğu klasör

# ─── GİRİŞ SİSTEMİ ───────────────────────────────────────────────────────────
def kulup_credentials_yukle() -> dict:
    """Kulüp giriş bilgileri → DÜZ dict. Önce dosya (repo/Render Secret File),
    yoksa st.secrets['clubs'] fallback'i.
    NOT: @st.cache_data KASITLI kaldırıldı — st.secrets nesnelerini önbelleğe alırken
    serileştirme (pickle) hatası prod'da çökmeye yol açabiliyordu. Fonksiyon zaten ucuz.
    st.secrets'tan gelen iç nesneler düz dict'e çevrilir (AttrDict serileştirme sorunu olmasın)."""
    # 1) Dosya (repo veya Render Secret File → bootstrap kökü doldurur)
    yol = _DIZIN / "club_credentials.json"
    if yol.exists():
        try:
            data = json.loads(yol.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                return data
        except Exception:
            pass   # bozuk/yanlış içerik (örn. yol yapıştırılmış) → secrets fallback'e düş, ÇÖKME
    # 2) Streamlit Secrets fallback ([clubs]) — düz dict'e DEEP-convert
    try:
        clubs = dict(st.secrets.get("clubs", {}))
        return {k: dict(v) for k, v in clubs.items()}
    except Exception:
        return {}


# ─── ÜYE SİSTEMİ (self-servis kayıt → GSheets "Uyeler") ───────────────────────
def _uyeler_ws():
    """GSheets 'Uyeler' worksheet'i (yoksa oluşturur). Lokalde GSheets yoksa None."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"]); creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Uyeler")
        except Exception:
            ws = sh.add_worksheet(title="Uyeler", rows=5000, cols=9)
            ws.update([["kullanici", "hash", "ad", "kulup", "rol", "tier",
                        "kayit_tarihi", "bitis_tarihi", "durum"]])
            return ws
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def uyeler_yukle() -> dict:
    """Kayıtlı üyeler → {kullanici(lower): {hash, ad, takim, rol, tier, bitis_tarihi, durum}}.
    5 dk cache → her rerun GSheets okumaz (oturum geri-yükleme sıcak yol). Kayıt/değişiklik
    sonrası uyeler_yukle.clear() ile tazelenir. Düz dict döner (serileştirme güvenli)."""
    ws = _uyeler_ws()
    if ws is None:
        return {}
    try:
        out = {}
        for r in ws.get_all_records():
            ku = str(r.get("kullanici", "")).strip().lower()
            if ku and r.get("hash"):
                out[ku] = {
                    "hash": str(r.get("hash", "")),
                    "ad": str(r.get("ad", "") or ku),
                    "takim": str(r.get("kulup", "") or ""),
                    "rol": str(r.get("rol", "") or "kulup"),
                    "tier": (str(r.get("tier", "") or "free").lower()),
                    "bitis_tarihi": str(r.get("bitis_tarihi", "") or ""),
                    "durum": str(r.get("durum", "") or "aktif"),
                }
        return out
    except Exception:
        return {}


def tum_giris_kayitlari() -> dict:
    """Üyeler (GSheets, cache'li) + kulüpler (secrets) birleşik. Anahtarlar lowercase;
    kulüp/admin kayıtları çakışmada önceliklidir."""
    kayit = dict(uyeler_yukle())
    for k, v in kulup_credentials_yukle().items():
        kayit[str(k).strip().lower()] = v
    return kayit


def _eposta_gecerli(e: str) -> bool:
    return bool(_re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (e or "").strip()))


def uye_kaydet(kullanici: str, sifre: str, ad: str, kulup: str = "") -> tuple:
    """Yeni üye kaydı (free tier). Döner: (basarili: bool, mesaj_tr, mesaj_en)."""
    kullanici = (kullanici or "").strip().lower()
    ad = (ad or "").strip()
    if not _eposta_gecerli(kullanici):
        return (False, "Geçerli bir e-posta adresi gir.", "Enter a valid email address.")
    if not ad:
        return (False, "İsim / kurum adı gir.", "Enter your name / organization.")
    if len(sifre or "") < 8:
        return (False, "Şifre en az 8 karakter olmalı.", "Password must be at least 8 characters.")
    if kullanici in {str(k).strip().lower() for k in kulup_credentials_yukle()}:
        return (False, "Bu kullanıcı adı zaten kullanımda.", "This username is already in use.")
    if kullanici in uyeler_yukle():
        return (False, "Bu e-posta zaten kayıtlı. Giriş yapmayı dene.", "This email is already registered. Try logging in.")
    if not _BCRYPT_OK:
        return (False, "Sunucu hatası (şifreleme).", "Server error (hashing).")
    ws = _uyeler_ws()
    if ws is None:
        return (False, "Kayıt servisi şu an kullanılamıyor, sonra tekrar dene.", "Registration service is unavailable, try again later.")
    try:
        from datetime import datetime
        h = _bcrypt.hashpw(sifre.encode(), _bcrypt.gensalt()).decode()
        ws.append_row([kullanici, h, ad, (kulup or "").strip(), "kulup", "free",
                       datetime.now().strftime("%Y-%m-%d %H:%M"), "", "aktif"])
        uyeler_yukle.clear()   # cache tazele → hemen giriş yapabilsin
        return (True, "Kayıt başarılı! Aşağıdan e-posta ve şifrenle giriş yapabilirsin.",
                "Registered! You can now log in with your email and password.")
    except Exception:
        return (False, "Kayıt sırasında bir hata oluştu.", "An error occurred during registration.")


def _uye_satir_bul(ws, kullanici: str):
    """kullanici'nin GSheets satır numarasını döndürür (başlık=1, veri 2'den başlar)."""
    kullanici = (kullanici or "").strip().lower()
    try:
        for i, r in enumerate(ws.get_all_records(), start=2):
            if str(r.get("kullanici", "")).strip().lower() == kullanici:
                return i
    except Exception:
        pass
    return None


def uye_guncelle(kullanici: str, tier: str = None, bitis_tarihi: str = None,
                 durum: str = None) -> bool:
    """Bir üyenin tier / bitiş tarihi / durum alanlarını günceller (admin). GSheets 'Uyeler'.
    Kolonlar: kullanici(A) hash(B) ad(C) kulup(D) rol(E) tier(F) kayit(G) bitis(H) durum(I)."""
    ws = _uyeler_ws()
    if ws is None:
        return False
    idx = _uye_satir_bul(ws, kullanici)
    if not idx:
        return False
    try:
        if tier is not None:
            ws.update_cell(idx, 6, tier)
        if bitis_tarihi is not None:
            ws.update_cell(idx, 8, bitis_tarihi)
        if durum is not None:
            ws.update_cell(idx, 9, durum)
        uyeler_yukle.clear()   # cache tazele
        return True
    except Exception:
        return False


def giris_dogrula(kullanici: str, sifre: str) -> dict | None:
    creds = tum_giris_kayitlari()
    bilgi = creds.get((kullanici or "").strip().lower())
    if not bilgi:
        return None
    try:
        if _BCRYPT_OK and _bcrypt.checkpw(sifre.encode(), bilgi["hash"].encode()):
            return bilgi
    except Exception:
        pass
    return None


# ─── KALICI OTURUM (cookie ile — sayfa yenilense de giriş korunur) ────────────
import hmac as _hmac, hashlib as _hashlib, time as _time, base64 as _b64

_COOKIE_AD   = "wscope_oturum"
_OTURUM_GUN  = 30  # cookie geçerlilik süresi (gün)

def _oturum_secret() -> bytes:
    """Çerez imzalama anahtarı.
    Öncelik: Render/Streamlit secrets['auth_secret'] (deploy'lar arası KALICI — önerilir).
    Yoksa: repoya GİRMEYEN yerel rastgele dosyadan (_auth_secret_local) üretilir/okunur.

    GÜVENLİK: Eskiden public credential hash'lerinden türetiliyordu; repo herkese açık
    olduğu için saldırgan bu anahtarı yeniden hesaplayıp 'admin' çerezi forge edebiliyordu.
    Artık anahtar repo'dan türetilebilir DEĞİL → forge yolu kapalı."""
    try:
        s = st.secrets.get("auth_secret", "")
        if s:
            return str(s).encode()
    except Exception:
        pass
    # Yerel rastgele secret (gitignore'lu, repo'da yok → forge edilemez).
    # NOT: Render diski deploy'lar arası kalıcı değil → auth_secret yoksa her deploy'da
    # mevcut oturumlar bir kez düşer (güvenli varsayılan). Kalıcılık için auth_secret ekle.
    import secrets as _secmod
    yol = _DIZIN / "_auth_secret_local"
    try:
        if yol.exists():
            data = yol.read_bytes()
            if len(data) >= 16:
                return data
        tok = _secmod.token_bytes(32)
        yol.write_bytes(tok)
        return tok
    except Exception:
        return _secmod.token_bytes(32)   # yazılamayan (read-only) FS: süreç-içi rastgele

def _oturum_token_uret(kullanici: str) -> str:
    son = int(_time.time()) + _OTURUM_GUN * 86400
    govde = f"{kullanici}|{son}"
    imza = _hmac.new(_oturum_secret(), govde.encode(), _hashlib.sha256).hexdigest()[:24]
    return _b64.urlsafe_b64encode(f"{govde}|{imza}".encode()).decode()

def _oturum_token_coz(token: str):
    """Token geçerliyse kullanıcı adını döndürür, değilse None."""
    try:
        ham = _b64.urlsafe_b64decode(token.encode()).decode()
        kullanici, son, imza = ham.rsplit("|", 2)
        if int(son) < _time.time():
            return None  # süresi dolmuş
        beklenen = _hmac.new(_oturum_secret(), f"{kullanici}|{son}".encode(),
                             _hashlib.sha256).hexdigest()[:24]
        if _hmac.compare_digest(imza, beklenen):
            return kullanici
    except Exception:
        pass
    return None

# Run başına tek instance (modül her rerun'da yeniden çalıştığından sıfırlanır;
# session_state'te saklamak bileşeni eskitir → cookie senkronu bozulur).
_CK_CACHE = {}

def _cookie_ctrl():
    """CookieController — her run'da bir kez oluşturulur (bileşen yeniden render edilir)."""
    if "ck" not in _CK_CACHE:
        try:
            from streamlit_cookies_controller import CookieController
            _CK_CACHE["ck"] = CookieController()
        except Exception:
            _CK_CACHE["ck"] = None
    return _CK_CACHE["ck"]

def _oturum_session_doldur(kullanici: str, bilgi: dict):
    st.session_state["kulup_giris"]     = True
    st.session_state["kulup_kullanici"] = kullanici
    st.session_state["kulup_takim"]     = bilgi.get("takim", "")
    st.session_state["kulup_ad"]        = bilgi.get("ad", kullanici)
    st.session_state["kulup_rol"]       = bilgi.get("rol", "kulup")
    st.session_state["kulup_tier"]      = _tier_coz(bilgi)
    st.session_state["kulup_pro"]       = tier_yeterli("pro")  # geriye uyumluluk

def _oturum_kaydet(kullanici: str):
    """Cookie yazımını bir sonraki run'a erteler (rerun yazmayı kesmesin diye)."""
    st.session_state["_ck_islem"] = ("set", _oturum_token_uret(kullanici))

def _oturum_cikis():
    """Cookie silmeyi bir sonraki run'a erteler."""
    st.session_state["_ck_islem"] = ("sil",)

def _oturum_geri_yukle():
    """Her run başında: bekleyen cookie işlemini uygula, yoksa oturumu geri yükle."""
    ctrl = _cookie_ctrl()
    if ctrl is None:
        return

    # 1) Bekleyen yazma/silme (login/logout sonrası) — bu run'da uygula,
    #    arkasından rerun YOK ki bileşen cookie'yi yazabilsin.
    islem = st.session_state.pop("_ck_islem", None)
    if islem:
        try:
            if islem[0] == "set":
                ctrl.set(_COOKIE_AD, islem[1], max_age=_OTURUM_GUN * 86400)
            else:
                ctrl.remove(_COOKIE_AD)
        except Exception:
            pass
        return

    # 2) Zaten girişliyse dokunma
    if st.session_state.get("kulup_giris"):
        return

    # 3) Geçerli cookie varsa oturumu geri yükle
    try:
        token = ctrl.get(_COOKIE_AD)
    except Exception:
        token = None
    if not token:
        return
    kullanici = _oturum_token_coz(token)
    if not kullanici:
        return
    # Kulüp (secrets, hızlı) + üye (GSheets, 5dk cache) birleşik — cache hit'te hot path ucuz
    bilgi = tum_giris_kayitlari().get((kullanici or "").strip().lower())
    if bilgi:
        _oturum_session_doldur(kullanici, bilgi)
        st.session_state["girildi"] = True

def giris_gerekli_ekrani():
    """Giriş gerektiren sekmelerde gösterilen yönlendirme + PRO tanıtım ekranı."""
    st.markdown("<br>", unsafe_allow_html=True)

    ozellik_satiri = "".join(
        f"<div style='display:flex;align-items:flex-start;gap:12px;padding:8px 0;"
        f"border-bottom:1px solid #1e2340;'>"
        f"<span style='font-size:1.2rem;min-width:26px;text-align:center;'>{ikon}</span>"
        f"<div><div style='color:#fff;font-weight:600;font-size:0.88rem;'>{baslik}</div>"
        f"<div style='color:#8899aa;font-size:0.76rem;margin-top:1px;'>{aciklama}</div></div>"
        f"</div>"
        for ikon, baslik, aciklama in _PRO_OZELLIKLER
    )

    # ── Kilit kartı (futbol fotoğraflı) ──
    st.markdown(
        f"""
        <div style='max-width:580px;margin:0 auto 14px;'>
          <div style="background:linear-gradient(180deg,#0a0e1bcc 0%,#10152be8 60%,#12161ffa 100%),
               url('app/static/b2.jpg') center 24%/cover no-repeat;
               border:1px solid #1db95455;border-radius:14px;
               padding:30px 28px 26px;text-align:center;overflow:hidden;">
            <div style='font-size:38px;margin-bottom:8px;'>🔐</div>
            <div style='font-family:Oswald,Sora,sans-serif;font-size:1.5rem;font-weight:700;color:#fff;margin-bottom:8px;'>
              {t("Bu özellik üyelere özel", "This feature is members-only")}</div>
            <div style='font-size:13px;color:#aebbd0;line-height:1.7;'>
              {t("Detaylı Oyuncu Profili, Transfer Öner ve Gelişmiş Arama;", "Detailed Player Profile, Transfer Suggest and Advanced Search are")}
              <b style='color:#e8eef7;'>{t("kulüpler, menajerler ve scoutlara özeldir.", "exclusive to clubs, agents and scouts.")}</b>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # ── CTA: kilit mesajının HEMEN altında (sol menüyü aramaya gerek yok) ──
    _cta = st.columns([1, 1.4, 1])[1]
    with _cta:
        _g1, _g2 = st.columns(2)
        if _g1.button(t("🔐 Giriş Yap", "🔐 Log In"), width="stretch", type="primary", key="gge_giris"):
            st.session_state["login_ac"] = True
            st.rerun()
        if _g2.button(t("✍️ Ücretsiz Kayıt Ol", "✍️ Sign Up Free"), width="stretch", key="gge_kayit"):
            if not st.session_state.get("login_ac"):   # kart henüz açılmadıysa radio'yu Kayıt'a kur (güvenli)
                st.session_state["giris_mod_sec"] = t("Kayıt Ol", "Sign Up")
            st.session_state["login_ac"] = True
            st.rerun()
        st.caption(t("Ücretsiz hesapla başla · istediğin zaman yükselt",
                     "Start free · upgrade anytime"))
    # ── PRO özellik listesi + fiyat ──
    st.markdown(
        f"""
        <div style='max-width:580px;margin:18px auto 0;'>
          <div style='background:#12161f;border-radius:12px;padding:20px 24px;
               border:1px solid #1e2340;'>
            <div style='color:#1db954;font-weight:700;font-size:0.88rem;
                 letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>
              ⚡ {t("PRO Pakete Dahil Olanlar", "Included in the PRO Package")}
            </div>
            {ozellik_satiri}
          </div>
          <div style='text-align:center;margin-top:20px;'>
            <span style='background:linear-gradient(135deg,#0d2b1e,#1a1f36);
                 border:2px solid #1db954;border-radius:12px;padding:14px 32px;
                 display:inline-block;'>
              <div style='color:#1db954;font-size:0.75rem;font-weight:700;
                   letter-spacing:2px;text-transform:uppercase;'>{t("PRO Paket", "PRO Package")}</div>
              <div style='color:#fff;font-size:2rem;font-weight:900;line-height:1.1;font-family:Sora,sans-serif;'>
                999 <span style='font-size:1rem;color:#8899aa;'>{t("€/yıl", "€/yr")}</span>
              </div>
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _giris_yap(ku: str, si: str) -> bool:
    """Ortak giriş mantığı: doğrula → session + cookie. Başarılıysa True.
    Kullanıcı adı küçük harfe normalize edilir (kulüp + üye anahtarları lowercase)."""
    ku_n = (ku or "").strip().lower()
    sonuc = giris_dogrula(ku_n, si.strip())
    if sonuc:
        giris_logla(ku_n, basarili=True)
        _oturum_session_doldur(ku_n, sonuc)
        st.session_state["girildi"]  = True
        st.session_state["login_ac"] = False
        _oturum_kaydet(ku_n)   # cookie'ye yaz (kalıcı giriş)
        return True
    if ku_n:
        giris_logla(ku_n, basarili=False)
    return False


def giris_formu():
    """Sidebar'da giriş formu gösterir."""
    if st.session_state.get("kulup_giris"):
        return
    with st.sidebar.expander(t("🔐 Giriş", "🔐 Login"), expanded=False):
        with st.form("giris_form", clear_on_submit=True):
            ku = st.text_input(t("Kullanıcı adı", "Username"),
                               placeholder=t("kullanıcı adı", "username"))
            si = st.text_input(t("Şifre", "Password"), type="password", placeholder="••••")
            if st.form_submit_button(t("Giriş Yap", "Log In"), width="stretch"):
                if _giris_yap(ku, si):
                    st.rerun()
                else:
                    st.error(t("Kullanıcı adı veya şifre hatalı.", "Incorrect username or password."))


def _kayit_formu():
    """Self-servis üye kaydı (free tier). Başarılı kayıtta otomatik giriş yapar."""
    st.caption(t("Ücretsiz hesap oluştur — saniyeler içinde. İstediğin zaman yükseltebilirsin.",
                 "Create a free account in seconds. Upgrade anytime."))
    with st.form("kayit_form_ana", clear_on_submit=False):
        _ad = st.text_input(t("İsim / Kurum", "Name / Organization"),
                            placeholder=t("Adınız veya kulüp / kurum adı", "Your name or club / org"))
        _ep = st.text_input(t("E-posta", "Email"), placeholder="ornek@eposta.com")
        _s1 = st.text_input(t("Şifre (en az 8 karakter)", "Password (min 8 chars)"),
                            type="password", placeholder="••••••••")
        _s2 = st.text_input(t("Şifre (tekrar)", "Password (again)"),
                            type="password", placeholder="••••••••")
        _b1, _b2 = st.columns(2)
        _kyt = _b1.form_submit_button(t("Kayıt Ol", "Sign Up"), width="stretch", type="primary")
        _ipt = _b2.form_submit_button(t("İptal", "Cancel"), width="stretch")
    if _kyt:
        if (_s1 or "") != (_s2 or ""):
            st.error(t("Şifreler uyuşmuyor.", "Passwords do not match."))
        else:
            with st.spinner(t("Hesap oluşturuluyor…", "Creating account…")):
                _ok, _m_tr, _m_en = uye_kaydet(_ep, _s1, _ad)
            if _ok:
                st.success(t(_m_tr, _m_en))
                if _giris_yap(_ep, _s1):   # otomatik giriş → kesintisiz
                    st.rerun()
            else:
                st.error(t(_m_tr, _m_en))
    if _ipt:
        st.session_state["login_ac"] = False
        st.rerun()


def giris_formu_ana():
    """Ana alanda (ortada) giriş + kayıt kartı — sağ üst '🔐 Giriş' butonuyla açılır."""
    if st.session_state.get("kulup_giris") or not st.session_state.get("login_ac"):
        return
    _orta = st.columns([1, 1.4, 1])[1]
    _GIR = t("Giriş Yap", "Log In")
    _KYT = t("Kayıt Ol", "Sign Up")
    with _orta:
        st.markdown(
            f"<div style=\"background:linear-gradient(120deg,#0a0e1bee 0%,#1a1438ee 55%,#2a1145cc 100%),"
            f"url('app/static/hero.jpg') center 28%/cover no-repeat;"
            f"border:1px solid #3b2d6e;border-radius:14px;padding:22px 24px;"
            f"margin:6px 0 14px;overflow:hidden;\">"
            f"<div style='font-size:0.62rem;font-weight:800;color:#c4b5fd;letter-spacing:0.18em;'>"
            f"🔐 {t('KULÜP · SCOUT · MENAJER', 'CLUB · SCOUT · MANAGER')}</div>"
            f"<div style='font-family:Oswald,Sora,sans-serif;font-size:1.5rem;font-weight:700;color:#fff;"
            f"margin-top:5px;line-height:1.1;'>{t('Hesabına Eriş', 'Access Your Account')}</div>"
            f"<div style='color:#aebbd0;font-size:0.8rem;margin-top:3px;'>"
            f"{t('Ücretsiz kayıt ol veya giriş yap — kulüpler ve profesyoneller için.', 'Sign up free or log in — for clubs and professionals.')}</div>"
            f"</div>",
            unsafe_allow_html=True)
        _mod = st.radio(t("Mod", "Mode"), [_GIR, _KYT], horizontal=True,
                        key="giris_mod_sec", label_visibility="collapsed")
        if _mod == _KYT:
            _kayit_formu()
            return
        with st.form("giris_form_ana", clear_on_submit=True):
            ku = st.text_input(t("Kullanıcı adı / E-posta", "Username / Email"),
                               placeholder=t("kullanıcı adı veya e-posta", "username or email"))
            si = st.text_input(t("Şifre", "Password"), type="password", placeholder="••••")
            _b1, _b2 = st.columns(2)
            _gir = _b1.form_submit_button(_GIR, width="stretch", type="primary")
            _ipt = _b2.form_submit_button(t("İptal", "Cancel"), width="stretch")
        if _gir:
            if _giris_yap(ku, si):
                st.rerun()
            else:
                st.error(t("Kullanıcı adı veya şifre hatalı.", "Incorrect username or password."))
        if _ipt:
            st.session_state["login_ac"] = False
            st.rerun()


# ─── ÜYELİK KADEMELERİ (free < basic < pro < premium < admin) ─────────────────
_TIER_RANK = {"free": 0, "basic": 1, "pro": 2, "premium": 3, "admin": 99}

# Kademe görünüm bilgisi: etiket, renk, ikon (sidebar rozeti + her yerde)
_TIER_GORUNUM = {
    "free":    ("Ücretsiz", "#8899aa", "🔓"),
    "basic":   ("Basic",    "#29b6f6", "🔹"),
    "pro":     ("Pro",      "#1db954", "⚡"),
    "premium": ("Premium",  "#e040fb", "👑"),
    "admin":   ("Admin",    "#f59e0b", "🛡️"),
}

def _tier_coz(bilgi: dict) -> str:
    """Credential/üye kaydından EFEKTİF kademeyi belirler.
    Üyelik bitiş tarihi (bitis_tarihi) geçmişse otomatik 'free'ye düşer."""
    if bilgi.get("rol") == "admin":
        return "admin"
    bt = (bilgi.get("bitis_tarihi") or "").strip()
    if bt:
        try:
            from datetime import date
            if date.fromisoformat(bt[:10]) < date.today():
                return "free"   # abonelik süresi dolmuş
        except Exception:
            pass
    t_ = (bilgi.get("tier") or "").lower()
    if t_ in _TIER_RANK:
        return t_
    return "pro" if bilgi.get("pro") else "basic"  # eski kayıtlar için

def kullanici_tier() -> str:
    """Aktif kullanıcının kademesi ('free' = giriş yok). Aktif deneme varsa onu da hesaba katar."""
    if not st.session_state.get("kulup_giris"):
        return "free"
    if (st.session_state.get("kulup_rol") == "admin"
            or st.session_state.get("kulup_kullanici") == "admin"):
        return "admin"
    base = st.session_state.get("kulup_tier", "basic")
    # Aktif deneme daha yüksek bir kademe veriyorsa onu kullan
    dn = aktif_deneme(st.session_state.get("kulup_kullanici", ""))
    if dn:
        d_tier = (dn.get("tier") or "premium").lower()
        if _TIER_RANK.get(d_tier, 0) > _TIER_RANK.get(base, 0):
            return d_tier
    return base

def tier_yeterli(gereken: str) -> bool:
    """Aktif kademe, istenen kademeye eşit/üstün mü?"""
    return _TIER_RANK.get(kullanici_tier(), 0) >= _TIER_RANK.get(gereken, 99)

def pro_kontrol() -> bool:
    """Geriye uyumlu: Pro veya üstü mü? (admin dahil)"""
    return tier_yeterli("pro")


# ─── Deneme modu: kısıtlı vitrin (TR'de 5, Scouting'de 5 oyuncu açık) ──────────
DENEME_TR_OYUNCULAR = {
    "MERYEM SEVENT", "JUANITA AGUADZE", "ARMISA KUÇ",
    "MILICA MIJATOVIC", "FLORENTİNA KOLGECİ",
}
DENEME_SCOUT_OYUNCULAR = {
    "Ana Barjaktarovic", "Tessa Zimmermann", "Natalia Wrobel",
    "Ajsa Kalac", "Tanja Malesija",
}

def deneme_modunda() -> bool:
    """Erişim aktif denemeden geliyorsa True (gerçek ödeyen/admin değil)."""
    if not st.session_state.get("kulup_giris"):
        return False
    if (st.session_state.get("kulup_rol") == "admin"
            or st.session_state.get("kulup_kullanici") == "admin"):
        return False
    dn = aktif_deneme(st.session_state.get("kulup_kullanici", ""))
    if not dn:
        return False
    base   = st.session_state.get("kulup_tier", "basic")
    d_tier = (dn.get("tier") or "premium").lower()
    return _TIER_RANK.get(d_tier, 0) > _TIER_RANK.get(base, 0)

def deneme_kilit(ozellik: str, kaynak: str = "tr"):
    """Deneme kapsamı dışındaki içerik için kilit ekranı + üyelik yönlendirmesi."""
    if kaynak == "scout":
        acik   = len(DENEME_SCOUT_OYUNCULAR)
        toplam = len(scouting_sd_yukle())
        nereden = t("Scouting havuzu", "the scouting pool")
    else:
        acik   = len(DENEME_TR_OYUNCULAR)
        toplam = len(df_tam) if not df_tam.empty else 0
        nereden = t("TR veride", "TR data")
    # Kilit karti (futbol fotografli) — diger donusum ekranlariyla tutarli
    st.markdown(
        f"""
        <div style='max-width:560px;margin:24px auto 14px;'>
          <div style="background:linear-gradient(180deg,#0a0e1bcc 0%,#150b28e8 60%,#12101ffa 100%),
               url('app/static/b1.jpg') center 28%/cover no-repeat;
               border:1px solid #e040fb55;border-radius:16px;padding:32px 30px;text-align:center;overflow:hidden;">
            <div style='font-size:2.4rem;'>🔒</div>
            <div style='font-family:Oswald,Sora,sans-serif;font-size:1.5rem;font-weight:700;color:#fff;margin:6px 0 8px;'>
              {t('Sınırlı Önizleme','Limited Preview')}</div>
            <p style='color:#c7d2e6;font-size:0.92rem;line-height:1.6;margin:0 0 12px;'>
              <b style='color:#e9d5ff;'>{ozellik}</b> {t('tam katalogu üyelikle açılır.','full catalog unlocks with membership.')}</p>
            <div style='display:inline-block;background:#0f0a1ecc;border:1px solid #3b2d6e;border-radius:10px;padding:8px 16px;'>
              <span style='color:#aebbd0;font-size:0.85rem;'>{t('Toplam','Total')} <b style='color:#fff;'>{toplam}</b> {nereden} · {t('açık','open')} <b style='color:#e040fb;'>{acik}</b> {t('örnek','samples')}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Inline CTA: girişliyse Yükselt, değilse Giriş/Kayıt
    _dc = st.columns([1, 1.4, 1])[1]
    with _dc:
        if st.session_state.get("kulup_giris"):
            if st.button(t("💳 Üyeliği Yükselt", "💳 Upgrade Membership"), width="stretch",
                         type="primary", key=f"dk_yukselt_{kaynak}"):
                st.session_state["yukselt_plan"] = "premium" if kaynak == "scout" else "pro"
                st.session_state["sayfa"] = "yukselt"; st.session_state["girildi"] = True
                st.rerun()
        else:
            _dk1, _dk2 = st.columns(2)
            if _dk1.button(t("🔐 Giriş Yap", "🔐 Log In"), width="stretch", type="primary", key=f"dk_giris_{kaynak}"):
                st.session_state["login_ac"] = True; st.rerun()
            if _dk2.button(t("✍️ Ücretsiz Kayıt", "✍️ Sign Up Free"), width="stretch", key=f"dk_kayit_{kaynak}"):
                if not st.session_state.get("login_ac"):
                    st.session_state["giris_mod_sec"] = t("Kayıt Ol", "Sign Up")
                st.session_state["login_ac"] = True; st.rerun()
        _whatsapp_butonu(t("Merhaba, üyelik hakkında bilgi almak istiyorum.", "Hi, I'd like info about membership."),
                         "WhatsApp'tan sor", "Ask on WhatsApp")


_PRO_OZELLIKLER = [
    ("🗄️", t("Tüm Oyuncu Veri Tabanına Erişim", "Access to the Full Player Database"),          t("Süper Lig'deki her oyuncunun tam istatistik geçmişi", "Complete stats history of every player in the Super League")),
    ("📊", t("Sıralanabilir Gelişmiş İstatistikler", "Sortable Advanced Statistics"),      t("Maç, gol, dakika, kart — tüm metrikler anlık sıralama", "Matches, goals, minutes, cards — all metrics instantly sortable")),
    ("🔍", t("Akıllı Oyuncu Arama", "Smart Player Search"),                       t("Uyruk, yaş aralığı, mevki ve performansa göre filtrele", "Filter by nationality, age range, position and performance")),
    ("⭐", t("Oyuncu Listem — Favori Kaydetme", "My Player List — Save Favorites"),            t("Takip ettiğin oyuncuları kişisel listende topla", "Collect the players you follow in a personal list")),
    ("📝", t("Not Ekle + PDF Yazdır / Kaydet", "Add Notes + Print / Save PDF"),            t("Her oyuncu kartına özel not ekle, raporunu dışa aktar", "Add custom notes to each player card, export the report")),
    ("🏗️", t("Stratejik Kadro Planlama Desteği", "Strategic Squad Planning Support"),          t("Bütçe ve ihtiyaca göre akıllı kadro kurma senaryoları", "Smart squad-building scenarios based on budget and needs")),
    ("🔄", t("Talep Üzerine Oyuncu Önerileri", "On-Demand Player Suggestions"),            t("Tek tıkla mevki + bütçe bazlı transfer öneri motoru", "One-click position + budget based transfer suggestion engine")),
    ("🎯", t("Talep Üzerine Oyuncu Değerlendirmesi", "On-Demand Player Assessment"),      t("AI destekli detaylı bireysel oyuncu analiz raporu", "AI-powered detailed individual player analysis report")),
    ("🎬", t("Video Analizleri", "Video Analyses"),                          t("Seçili oyuncular için maç klibi ve taktik breakdown", "Match clips and tactical breakdown for selected players")),
    ("🔑", t("365 Gün Kesintisiz Erişim", "365 Days of Uninterrupted Access"),                 t("Tüm sezon boyunca platform sınırsız kullanım", "Unlimited platform use throughout the season")),
]


# Üyelik kademeleri (paywall görselleri için): ikon, etiket, renk, yıllık fiyat
_TIER_BILGI = {
    "pro":     ("⚡", "PRO",     "#1db954", "999 €"),
    "premium": ("👑", "PREMIUM", "#e040fb", "1.999 €"),
}

def pro_paywall_goster(ozellik_adi: str = None, tier: str = "pro"):
    """Üyelik (Pro/Premium) satın alma sayfasını gösterir."""
    if ozellik_adi is None:
        ozellik_adi = t("Bu özellik", "This feature")
    _ti_ikon, _ti_etiket, _ti_renk, _ti_fiyat = _TIER_BILGI.get(tier, _TIER_BILGI["pro"])
    st.markdown("<br>", unsafe_allow_html=True)

    ozellik_satiri = "".join(
        f"<div style='display:flex;align-items:flex-start;gap:12px;padding:10px 0;"
        f"border-bottom:1px solid #1e2340;'>"
        f"<span style='font-size:1.3rem;min-width:28px;text-align:center;'>{ikon}</span>"
        f"<div><div style='color:#fff;font-weight:600;font-size:0.92rem;'>{baslik}</div>"
        f"<div style='color:#8899aa;font-size:0.78rem;margin-top:2px;'>{aciklama}</div></div>"
        f"</div>"
        for ikon, baslik, aciklama in _PRO_OZELLIKLER
    )

    # ── Kilit kartı (futbol fotoğraflı) ──
    st.markdown(
        f"""
        <div style='max-width:640px;margin:0 auto 14px;'>
          <div style="background:linear-gradient(180deg,#0a0e1bcc 0%,#10152be8 60%,#12161ffa 100%),
               url('app/static/b1.jpg') center 28%/cover no-repeat;
               border:1px solid {_ti_renk}66;border-radius:14px;padding:28px 26px;text-align:center;overflow:hidden;">
            <div style='font-size:34px;margin-bottom:6px;'>🔒</div>
            <div style='font-family:Oswald,Sora,sans-serif;font-size:1.45rem;font-weight:700;color:#fff;'>
              {ozellik_adi}</div>
            <div style='color:#aebbd0;font-size:0.88rem;margin-top:6px;'>
              {t(f"{_ti_etiket} üyelikle açılır — ödeme onayından sonra saniyeler içinde aktive.", f"Unlocks with {_ti_etiket} membership — activated in seconds after payment.")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # ── CTA: Yükselt → ödeme sayfası + WhatsApp ──
    _pc = st.columns([1, 1.5, 1])[1]
    with _pc:
        if st.button(t(f"💳 {_ti_etiket} Üyeliğe Yükselt", f"💳 Upgrade to {_ti_etiket}"),
                     width="stretch", type="primary", key=f"pw_yukselt_{tier}"):
            st.session_state["yukselt_plan"] = tier
            st.session_state["sayfa"] = "yukselt"
            st.session_state["girildi"] = True
            st.rerun()
        _whatsapp_butonu(t(f"Merhaba, {_ti_etiket} üyeliği almak istiyorum.", f"Hi, I'd like the {_ti_etiket} membership."),
                         "WhatsApp'tan sor", "Ask on WhatsApp")
    # ── Fiyat + özellik listesi ──
    st.markdown(
        f"""
        <div style='max-width:640px;margin:16px auto 0;'>
          <div style='background:linear-gradient(135deg,#0d2b1e,#1a1f36);border:2px solid {_ti_renk};
               border-radius:16px;padding:22px 28px;margin-bottom:22px;text-align:center;'>
            <div style='font-size:0.78rem;color:{_ti_renk};letter-spacing:2px;font-weight:700;
                 text-transform:uppercase;'>{_ti_ikon} {_ti_etiket} {t("Paket", "Package")}</div>
            <div style='font-size:2.4rem;font-weight:900;color:#fff;line-height:1;font-family:Sora,sans-serif;'>{_ti_fiyat}</div>
            <div style='color:#8899aa;font-size:0.8rem;margin-top:4px;'>{t("yıllık · KDV dahil", "yearly · VAT included")}</div>
          </div>
          <div style='background:#12161f;border:1px solid #1e2340;border-radius:12px;padding:20px 24px;'>
            <div style='color:#fff;font-weight:700;font-size:0.9rem;margin-bottom:6px;'>
              {t(f"{_ti_etiket} pakete dahil olanlar:", f"Included in {_ti_etiket}:")}</div>
            {ozellik_satiri}
          </div>
          <div style='text-align:center;margin-top:18px;color:#505870;font-size:0.78rem;'>
            {t("Kurumsal teklif veya demo için", "For a corporate offer or demo, write to")}
            <a href='mailto:mehmetbarandanis@gmail.com' style='color:#1db954;text-decoration:none;'>mehmetbarandanis@gmail.com</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600)
def sd_profiller_yukle():
    yol = _DIZIN / "soccerdonna_profiller.json"
    if yol.exists():
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    return {}

sd_profiller = sd_profiller_yukle()


@st.cache_data(ttl=86400)
def mac_sonuclari_yukle() -> list:
    yol = _DIZIN / "mac_sonuclari.json"
    if yol.exists():
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    return []


def _kanon(ad: str) -> str:
    """Takım adını eşleştirme için KANONİK anahtara indirger.
    mac_sonuclari (uzun/sponsorlu adlar) ile oyuncular.json (kısa adlar) ve sezon
    içinde değişen sponsor adları (ör. ALG'nin 4 varyantı) aynı anahtara gelsin diye.
    _takim_kisa kullanır → Çekmeköy/Şile gibi ayrı takımlar ayrı kalır."""
    return _takim_kisa(ad or "").upper()


@st.cache_data(ttl=3600)
def _yenilen_gol_map() -> dict:
    """{(hafta, TAKIM_UPPER): o hafta yenilen gol} — clean sheet hesabı için."""
    m = {}
    for x in mac_sonuclari_yukle():
        h = x.get("hafta")
        ev, dep = (x.get("ev") or ""), (x.get("dep") or "")
        eg, dg = x.get("ev_gol", 0), x.get("dep_gol", 0)
        if ev:  m[(h, _kanon(ev))] = dg   # ev takımının yediği = deplasman golü
        if dep: m[(h, _kanon(dep))] = eg
    return m

def _hafta_yenilen(takim: str, hafta) -> "int | None":
    """O hafta takımın yediği gol (clean sheet için); maç bulunamazsa None."""
    return _yenilen_gol_map().get((hafta, _kanon(takim)))

@st.cache_data(ttl=3600)
def _rakip_map() -> dict:
    """{(hafta, TAKIM_UPPER): rakip_takim_tam_adi}"""
    m = {}
    for x in mac_sonuclari_yukle():
        h = x.get("hafta")
        ev, dep = (x.get("ev") or ""), (x.get("dep") or "")
        if ev:  m[(h, _kanon(ev))] = dep
        if dep: m[(h, _kanon(dep))] = ev
    return m

def _hafta_rakip(takim: str, hafta) -> str:
    return _rakip_map().get((hafta, _kanon(takim)), "")


def _oyuncu_hafta_takim(detay: dict) -> dict:
    """{hafta: TAKIM_TAM_ADI} — oyuncunun o hafta hangi kulüpte olduğunu döndürür.

    Sezon-ortası transferlerde (gol/clean-sheet rakip atfının doğru olması için)
    KRİTİK: rakibi oyuncunun *birincil* takımının değil, o maçta gerçekten
    oynadığı kulübün fikstüründen bulmamız gerekir. tum_takimlar ("İlk / Son")
    kronolojik sırasını + takim_detay maç sayılarını kullanıp mac_gecmisi'ni
    (haftaya göre artan) ardışık bloklara dilimleriz; her giriş tek bir kulübe ait.
    Belirsizlik/uyumsuzlukta birincil takıma güvenli düşüş yapar.
    """
    mg = sorted(detay.get("mac_gecmisi", []), key=lambda m: m.get("hafta", 0))
    td = detay.get("takim_detay", []) or []
    birincil = detay.get("takim", "") or (td[0]["takim"] if td else "")
    # Yeni scrape'ler maç anında kulübü saklar → join'siz kesin sonuç.
    if mg and all(m.get("takim") for m in mg):
        return {m["hafta"]: m["takim"] for m in mg}
    if len(td) <= 1:
        return {m["hafta"]: birincil for m in mg}

    cnt = {d["takim"]: int(d.get("mac", 0) or 0) for d in td}
    order_raw = [s.strip() for s in (detay.get("tum_takimlar") or "").split("/") if s.strip()]
    seq, secili = [], set()
    for nm in order_raw:
        key = nm if nm in cnt else next((k for k in cnt if k[:12] == nm[:12]), None)
        if key and key not in secili:
            seq.append((key, cnt[key])); secili.add(key)
    # tum_takimlar eksik/uyumsuzsa takim_detay sırasına düş
    if sum(c for _, c in seq) != len(mg):
        seq = [(d["takim"], int(d.get("mac", 0) or 0)) for d in td]
    if sum(c for _, c in seq) != len(mg):
        return {m["hafta"]: birincil for m in mg}   # güvenli değil

    out, i = {}, 0
    for tk, c in seq:
        for m in mg[i:i + c]:
            out[m["hafta"]] = tk
        i += c
    return out

@st.cache_data(ttl=3600)
def _forfeit_hafta_takim() -> set:
    """Hükmen (çekilme) maçlarının (hafta, TAKIM_UPPER) kümesi — HER İKİ takım için.
    Tespit: bir takımın SONDAKİ ardışık 0-3 mağlubiyet serisi ≥3 → çekilme tail'i
    (ALG gibi sezon-ortası çekilme dahil; Beylerbeyi/Bornova gibi hiç katılmama da).
    Bu haftalarda gerçek maç oynanmadığı için gol/clean-sheet atfında dışlanır."""
    by_team = {}  # KANON -> [(hafta, attigi, yedigi)]
    for x in mac_sonuclari_yukle():
        ev, dep = _kanon(x.get("ev") or ""), _kanon(x.get("dep") or "")
        eg, dg, h = x.get("ev_gol", 0), x.get("dep_gol", 0), x.get("hafta", 0)
        if ev:  by_team.setdefault(ev, []).append((h, eg, dg))
        if dep: by_team.setdefault(dep, []).append((h, dg, eg))
    cekilen = set()  # (hafta, ÇEKİLEN_TAKIM_KANON)
    for tk, ml in by_team.items():
        ml.sort(key=lambda r: r[0])
        tail = 0
        for h, a, y in reversed(ml):
            if a == 0 and y == 3:
                tail += 1
            else:
                break
        if tail >= 3:
            for h, a, y in ml[-tail:]:
                cekilen.add((h, tk))
    # Forfeit maçın HER İKİ takımını işaretle (ikisi de o hafta gerçek maç oynamadı)
    out = set()
    for x in mac_sonuclari_yukle():
        ev, dep, h = _kanon(x.get("ev") or ""), _kanon(x.get("dep") or ""), x.get("hafta", 0)
        if (h, ev) in cekilen or (h, dep) in cekilen:
            out.add((h, ev)); out.add((h, dep))
    return out

@st.cache_data(ttl=3600)
def _son_lig_haftasi() -> int:
    return max((x.get("hafta", 0) for x in mac_sonuclari_yukle()), default=0)


GSHEET_ID = "1xeViJ3s2aOmZB2LfCQKb4fliFkd_f_ncYa-P69ch2mw"

@st.cache_data(ttl=300)
def scouting_gsheet_yukle() -> pd.DataFrame:
    """Google Sheets'ten scouting oyuncu listesini çeker (251 oyuncu)."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc   = gspread.authorize(creds)
        ws   = gc.open_by_key(GSHEET_ID).sheet1
        rows = ws.get_all_records()
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def scouting_sd_yukle() -> dict:
    """SoccerDonna verilerini JSON'dan yükler."""
    yol = pathlib.Path(__file__).parent / "scouting_sd_profiller.json"
    if not yol.exists():
        return {}
    import json
    with open(yol, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def scouting_leistung_yukle() -> dict:
    """SoccerDonna kariyer (leistungsdaten) verilerini JSON'dan yükler."""
    yol = pathlib.Path(__file__).parent / "scouting_leistungsdaten.json"
    if not yol.exists():
        return {}
    import json
    with open(yol, encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def scotr_yukle() -> dict:
    """Sco Tr scout raporları (1207 Antalyaspor — nitelik notları, rol, tarz)."""
    yol = pathlib.Path(__file__).parent / "scotr_raporlar.json"
    if not yol.exists():
        return {}
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def scout_kadro_yukle() -> dict:
    """Zengin scout kadro raporları (Kulüp/Lig/Sözleşme + Yetenek Kümesi + tarz ✔)."""
    yol = pathlib.Path(__file__).parent / "scout_kadro_raporlar.json"
    if not yol.exists():
        return {}
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def scouting_detay_yukle() -> dict:
    """Mr Daniş scouting detayları (rol, değerlendirme, vücut tipi, mevki kodları)."""
    yol = pathlib.Path(__file__).parent / "scouting_detay.json"
    if not yol.exists():
        return {}
    import json
    with open(yol, encoding="utf-8") as f:
        return json.load(f)

# Mr Daniş değerlendirme seviyeleri → renk
_MR_DANIS_RENK = {
    "Yıldız":     "#fbbf24",  # altın
    "Uzman":      "#a78bfa",  # mor
    "Yeterli":    "#22c55e",  # yeşil
    "Potansiyel": "#3b82f6",  # mavi
    "Yedek":      "#94a3b8",  # gri
}


# ─── Scouting Shortlist (kullanıcı bazlı favoriler) ────────────────────
# Yapı: { "admin": ["Oyuncu1", ...], "fenerbahce": [...] }
# Kalıcılık: Google Sheets "Shortlist" sayfası (kullanici | oyuncu satırları).
# Sheet'e erişilemezse (izin/worksheet yok) yerel shortlist.json'a düşer —
# böylece kurulum öncesi de çalışır, service account'a Editor verilince kalıcı olur.
_SHORTLIST_YOL = pathlib.Path(__file__).parent / "shortlist.json"

def _shortlist_ws():
    """'Shortlist' worksheet'ini döndürür (yoksa oluşturur). Hata → None (yerel JSON)."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Shortlist")
        except Exception:
            ws = sh.add_worksheet(title="Shortlist", rows=2000, cols=2)
            ws.update([["kullanici", "oyuncu"]])
            return ws
    except Exception:
        return None

@st.cache_data(ttl=120, show_spinner=False)
def shortlist_yukle() -> dict:
    ws = _shortlist_ws()
    if ws is not None:
        try:
            d = {}
            for r in ws.get_all_records():
                k = str(r.get("kullanici", "")).strip()
                o = str(r.get("oyuncu", "")).strip()
                if k and o:
                    d.setdefault(k, []).append(o)
            return d
        except Exception:
            pass
    # Yerel JSON fallback
    if not _SHORTLIST_YOL.exists():
        return {}
    import json
    try:
        with open(_SHORTLIST_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def shortlist_kaydet(data: dict):
    ws = _shortlist_ws()
    if ws is not None:
        try:
            rows = [["kullanici", "oyuncu"]]
            for k, lst in data.items():
                for o in lst:
                    rows.append([k, o])
            ws.clear()
            ws.update(rows)
            shortlist_yukle.clear()   # cache tazele → toggle anında yansır
            return
        except Exception:
            pass
    # Yerel JSON fallback
    import json
    with open(_SHORTLIST_YOL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shortlist_yukle.clear()

def shortlist_kullanici(kullanici: str) -> list:
    return shortlist_yukle().get(kullanici, [])

def shortlist_toggle(kullanici: str, oyuncu: str):
    data = shortlist_yukle()
    lst  = data.setdefault(kullanici, [])
    if oyuncu in lst:
        lst.remove(oyuncu)
    else:
        lst.append(oyuncu)
    shortlist_kaydet(data)


# ─── Üyelik Denemeleri (admin elle verir · GSheet kalıcı · yerel JSON fallback) ─
# Yapı: [{kullanici, tier, baslangic, bitis (ISO), veren}]  — "Denemeler" sayfası
_DENEME_YOL = pathlib.Path(__file__).parent / "denemeler.json"

def _deneme_ws():
    """'Denemeler' worksheet'ini döndürür (yoksa oluşturur). Hata → None."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Denemeler")
        except Exception:
            ws = sh.add_worksheet(title="Denemeler", rows=1000, cols=5)
            ws.update([["kullanici", "tier", "baslangic", "bitis", "veren"]])
            return ws
    except Exception:
        return None

@st.cache_data(ttl=120)
def denemeler_yukle() -> list:
    ws = _deneme_ws()
    if ws is not None:
        try:
            return [dict(r) for r in ws.get_all_records()]
        except Exception:
            pass
    if not _DENEME_YOL.exists():
        return []
    import json
    try:
        with open(_DENEME_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _denemeler_kaydet(kayitlar: list):
    ws = _deneme_ws()
    if ws is not None:
        try:
            rows = [["kullanici", "tier", "baslangic", "bitis", "veren"]]
            for d in kayitlar:
                rows.append([d.get("kullanici",""), d.get("tier",""),
                             d.get("baslangic",""), d.get("bitis",""), d.get("veren","")])
            ws.clear(); ws.update(rows)
            denemeler_yukle.clear()
            return
        except Exception:
            pass
    import json
    with open(_DENEME_YOL, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)
    denemeler_yukle.clear()

def _deneme_ts(iso: str) -> float:
    import datetime as _dt
    try:
        return _dt.datetime.fromisoformat(str(iso)).timestamp()
    except Exception:
        return 0.0

def aktif_deneme(kullanici: str):
    """Kullanıcının süresi dolmamış denemesini (en geç bitenini) döndürür, yoksa None."""
    kullanici = (kullanici or "").strip()
    if not kullanici:
        return None
    import time as _t
    simdi = _t.time()
    en_iyi = None
    for d in denemeler_yukle():
        if str(d.get("kullanici","")).strip() != kullanici:
            continue
        try:
            bitis = _deneme_ts(d.get("bitis",""))
        except Exception:
            continue
        if bitis > simdi and (en_iyi is None or bitis > en_iyi[0]):
            en_iyi = (bitis, d)
    return en_iyi[1] if en_iyi else None

def deneme_ver(kullanici: str, tier: str = "premium", gun: int = 2, veren: str = "admin"):
    import datetime as _dt
    bas = _dt.datetime.now()
    bit = bas + _dt.timedelta(days=gun)
    kayitlar = [d for d in denemeler_yukle()
                if str(d.get("kullanici","")).strip() != kullanici.strip()]  # eskiyi değiştir
    kayitlar.append({
        "kullanici": kullanici.strip(), "tier": tier,
        "baslangic": bas.isoformat(timespec="minutes"),
        "bitis":     bit.isoformat(timespec="minutes"), "veren": veren,
    })
    _denemeler_kaydet(kayitlar)

def deneme_iptal(kullanici: str):
    kayitlar = [d for d in denemeler_yukle()
                if str(d.get("kullanici","")).strip() != kullanici.strip()]
    _denemeler_kaydet(kayitlar)


# ─── Internal scout raporları (kişiye özel · GSheet kalıcı · yerel JSON) ──────
# Her kullanıcı kendi maç scout raporlarını yazar ve yalnızca kendininkini görür.
# Kayıt: {id, kullanici, tarih, ev, dep, skor, genel_not, oyuncular[], olusturma}
_INTERNAL_YOL = pathlib.Path(__file__).parent / "internal_raporlar.json"

def _internal_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"]); creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("InternalRaporlar")
        except Exception:
            ws = sh.add_worksheet(title="InternalRaporlar", rows=2000, cols=9)
            ws.update([["id","kullanici","tarih","ev","dep","skor","genel_not","oyuncular_json","olusturma"]])
            return ws
    except Exception:
        return None

@st.cache_data(ttl=60)
def _internal_tum() -> list:
    ws = _internal_ws()
    if ws is not None:
        try:
            out = []
            for r in ws.get_all_records():
                d = dict(r)
                try: d["oyuncular"] = json.loads(d.get("oyuncular_json") or "[]")
                except Exception: d["oyuncular"] = []
                out.append(d)
            return out
        except Exception:
            pass
    if not _INTERNAL_YOL.exists():
        return []
    try:
        with open(_INTERNAL_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

_INTERNAL_SEED_YOL = pathlib.Path(__file__).parent / "internal_seed_raporlar.json"

def _internal_seed() -> list:
    """Repoya gömülü örnek/başlangıç raporları (salt-okunur; GSheet'e yazılmaz)."""
    if not _INTERNAL_SEED_YOL.exists():
        return []
    try:
        with open(_INTERNAL_SEED_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def internal_yukle(kullanici: str) -> list:
    kullanici = (kullanici or "").strip()
    rs = [r for r in _internal_tum() if str(r.get("kullanici","")).strip() == kullanici]
    # Gömülü seed raporları (aynı kullanıcı) okuma anında eklenir — yazma yoluna
    # girmediği için silinmez, kalıcı örnek olarak durur. id çakışması engellenir.
    mevcut = {str(r.get("id","")) for r in rs}
    rs += [r for r in _internal_seed()
           if str(r.get("kullanici","")).strip() == kullanici
           and str(r.get("id","")) not in mevcut]
    return sorted(rs, key=lambda r: str(r.get("olusturma","")), reverse=True)

def _internal_kaydet_hepsi(kayitlar: list):
    ws = _internal_ws()
    if ws is not None:
        try:
            rows = [["id","kullanici","tarih","ev","dep","skor","genel_not","oyuncular_json","olusturma"]]
            for r in kayitlar:
                rows.append([str(r.get("id","")), r.get("kullanici",""), r.get("tarih",""),
                             r.get("ev",""), r.get("dep",""), r.get("skor",""),
                             r.get("genel_not",""),
                             json.dumps(r.get("oyuncular",[]), ensure_ascii=False),
                             r.get("olusturma","")])
            ws.clear(); ws.update(rows)
            _internal_tum.clear()
            return
        except Exception:
            pass
    # Yerel JSON (oyuncular alanını koru, oyuncular_json'ı düşür)
    import datetime as _dt
    temiz = []
    for r in kayitlar:
        rr = {k: v for k, v in r.items() if k != "oyuncular_json"}
        temiz.append(rr)
    with open(_INTERNAL_YOL, "w", encoding="utf-8") as f:
        json.dump(temiz, f, ensure_ascii=False, indent=2)
    _internal_tum.clear()

def internal_ekle(rapor: dict):
    kayitlar = _internal_tum()
    # oyuncular_json alanını kayıt listesinde tutmayalım (yalnızca oyuncular)
    for r in kayitlar:
        r.pop("oyuncular_json", None)
    kayitlar.append(rapor)
    _internal_kaydet_hepsi(kayitlar)

def internal_sil(rapor_id):
    kayitlar = [r for r in _internal_tum() if str(r.get("id","")) != str(rapor_id)]
    for r in kayitlar:
        r.pop("oyuncular_json", None)
    _internal_kaydet_hepsi(kayitlar)


# ─── Giriş Kaydı (Profilim için: ilk/son giriş, sayı, hatalı giriş) ────────────
# GSheets "GirisLog" worksheet'i. Cloud'da kalıcı; lokalde GSheets yoksa sessizce atlanır.
def _giris_log_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("GirisLog")
        except Exception:
            ws = sh.add_worksheet(title="GirisLog", rows=2000, cols=5)
            ws.update([["kullanici", "ilk_giris", "son_giris", "giris_sayisi", "son_hatali_giris"]])
            return ws
    except Exception:
        return None

def giris_log_oku(kullanici: str) -> dict:
    """Bir kullanıcının giriş kaydını döndürür (yoksa boş dict)."""
    kullanici = (kullanici or "").strip()
    ws = _giris_log_ws()
    if ws is None or not kullanici:
        return {}
    try:
        for r in ws.get_all_records():
            if str(r.get("kullanici", "")).strip() == kullanici:
                return r
    except Exception:
        pass
    return {}

def giris_logla(kullanici: str, basarili: bool = True):
    """Başarılı/başarısız girişi GSheets'e işler. Hata → sessiz (giriş akışını bloklamaz)."""
    kullanici = (kullanici or "").strip()
    if not kullanici:
        return
    ws = _giris_log_ws()
    if ws is None:
        return
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        records = ws.get_all_records()
        idx, row = None, {}
        for i, r in enumerate(records, start=2):  # satır 1 = başlık
            if str(r.get("kullanici", "")).strip() == kullanici:
                idx, row = i, r
                break
        if basarili:
            ilk  = str(row.get("ilk_giris", "") or now)
            sayi = int(row.get("giris_sayisi", 0) or 0) + 1
            vals = [kullanici, ilk, now, sayi, str(row.get("son_hatali_giris", "") or "")]
        else:
            vals = [kullanici, str(row.get("ilk_giris", "") or ""),
                    str(row.get("son_giris", "") or ""),
                    int(row.get("giris_sayisi", 0) or 0), now]
        if idx:
            ws.update(f"A{idx}:E{idx}", [vals])
        else:
            ws.append_row(vals)
    except Exception:
        pass


# ─── Scouting Etiketleri (kullanıcı bazlı, oyuncu → etiket) ────────────
# Yapı: { "admin": {"Oyuncu1": "🔴 Öncelik", ...} }
# "Etiketler" worksheet (kullanici | oyuncu | etiket); erişilemezse yerel JSON.
_ETIKETLER  = ["—", "🔴 Öncelik", "👀 İzle", "💰 Pahalı", "✅ Görüşüldü"]
_ETIKET_YOL = pathlib.Path(__file__).parent / "etiketler.json"

def _etiket_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Etiketler")
        except Exception:
            ws = sh.add_worksheet(title="Etiketler", rows=2000, cols=3)
            ws.update([["kullanici", "oyuncu", "etiket"]])
            return ws
    except Exception:
        return None

@st.cache_data(ttl=120, show_spinner=False)
def etiket_yukle() -> dict:
    ws = _etiket_ws()
    if ws is not None:
        try:
            d = {}
            for r in ws.get_all_records():
                k = str(r.get("kullanici", "")).strip()
                o = str(r.get("oyuncu", "")).strip()
                e = str(r.get("etiket", "")).strip()
                if k and o and e:
                    d.setdefault(k, {})[o] = e
            return d
        except Exception:
            pass
    if not _ETIKET_YOL.exists():
        return {}
    import json
    try:
        with open(_ETIKET_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def etiket_kaydet(data: dict):
    ws = _etiket_ws()
    if ws is not None:
        try:
            rows = [["kullanici", "oyuncu", "etiket"]]
            for k, om in data.items():
                for o, e in om.items():
                    if e and e != "—":
                        rows.append([k, o, e])
            ws.clear()
            ws.update(rows)
            etiket_yukle.clear()
            return
        except Exception:
            pass
    import json
    with open(_ETIKET_YOL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    etiket_yukle.clear()

def etiket_kullanici(kullanici: str) -> dict:
    return etiket_yukle().get(kullanici, {})

def etiket_ayarla(kullanici: str, oyuncu: str, etiket: str):
    data = etiket_yukle()
    om = data.setdefault(kullanici, {})
    if etiket and etiket != "—":
        om[oyuncu] = etiket
    else:
        om.pop(oyuncu, None)
    etiket_kaydet(data)


# ─── Scout Notu / Takip (durum · öncelik · not) — shortlist kartları için ──────
# Yapı: {kullanici: {oyuncu: {"durum","oncelik","not","tarih"}}}
# GSheets "ScoutNotu" (kullanici|oyuncu|durum|oncelik|not|tarih) + yerel json fallback.
_SCOUTNOT_YOL = pathlib.Path(__file__).parent / "scoutnot.json"
DURUM_OPSIYON   = ["—", "👀 İzleniyor", "📞 İlgileniyor", "💬 Müzakere",
                   "🤝 Anlaşıldı", "⏳ Beklemede", "❌ Vazgeçildi"]
ONCELIK_OPSIYON = ["—", "🔴 Yüksek", "🟡 Orta", "🟢 Düşük"]
_DURUM_EN   = {"—": "—", "👀 İzleniyor": "👀 Watching", "📞 İlgileniyor": "📞 Interested",
               "💬 Müzakere": "💬 Negotiating", "🤝 Anlaşıldı": "🤝 Agreed",
               "⏳ Beklemede": "⏳ On Hold", "❌ Vazgeçildi": "❌ Dropped"}
_ONCELIK_EN = {"—": "—", "🔴 Yüksek": "🔴 High", "🟡 Orta": "🟡 Medium", "🟢 Düşük": "🟢 Low"}
_DURUM_RENK = {"👀 İzleniyor": "#60a5fa", "📞 İlgileniyor": "#22d3ee", "💬 Müzakere": "#fbbf24",
               "🤝 Anlaşıldı": "#34d399", "⏳ Beklemede": "#94a3b8", "❌ Vazgeçildi": "#f87171"}

def _scoutnot_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"]); creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("ScoutNotu")
        except Exception:
            ws = sh.add_worksheet(title="ScoutNotu", rows=2000, cols=6)
            ws.update([["kullanici", "oyuncu", "durum", "oncelik", "not", "tarih"]])
            return ws
    except Exception:
        return None

@st.cache_data(ttl=120, show_spinner=False)
def scoutnot_yukle() -> dict:
    ws = _scoutnot_ws()
    if ws is not None:
        try:
            d = {}
            for r in ws.get_all_records():
                k = str(r.get("kullanici", "")).strip()
                o = str(r.get("oyuncu", "")).strip()
                if k and o:
                    d.setdefault(k, {})[o] = {
                        "durum":   str(r.get("durum", "")).strip(),
                        "oncelik": str(r.get("oncelik", "")).strip(),
                        "not":     str(r.get("not", "")).strip(),
                        "tarih":   str(r.get("tarih", "")).strip()}
            return d
        except Exception:
            pass
    if not _SCOUTNOT_YOL.exists():
        return {}
    import json
    try:
        with open(_SCOUTNOT_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def scoutnot_kaydet(data: dict):
    ws = _scoutnot_ws()
    if ws is not None:
        try:
            rows = [["kullanici", "oyuncu", "durum", "oncelik", "not", "tarih"]]
            for k, om in data.items():
                for o, v in om.items():
                    rows.append([k, o, v.get("durum",""), v.get("oncelik",""),
                                 v.get("not",""), v.get("tarih","")])
            ws.clear(); ws.update(rows)
            scoutnot_yukle.clear()
            return
        except Exception:
            pass
    import json
    with open(_SCOUTNOT_YOL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    scoutnot_yukle.clear()

def scoutnot_kullanici(kullanici: str) -> dict:
    return scoutnot_yukle().get(kullanici, {})

def scoutnot_ayarla(kullanici: str, oyuncu: str, durum: str, oncelik: str, notu: str):
    from datetime import date as _d
    data = scoutnot_yukle()
    om = data.setdefault(kullanici, {})
    if (durum and durum != "—") or (oncelik and oncelik != "—") or (notu or "").strip():
        om[oyuncu] = {"durum": durum if durum != "—" else "",
                      "oncelik": oncelik if oncelik != "—" else "",
                      "not": (notu or "").strip(), "tarih": _d.today().isoformat()}
    else:
        om.pop(oyuncu, None)
    scoutnot_kaydet(data)


# ─── Öneri Merkezi (Sportif Direktör · oyuncu öneri/takip panosu) ────────────
# Menajer/scout'tan gelen oyuncu önerilerini sportif direktör sisteme ekler ve
# durum + öncelik + not ile takip eder. GSheets "Oneriler" (kalıcı), erişilemezse
# yerel JSON. Her kullanıcı (kulüp) yalnız kendi önerilerini görür; admin tümünü.
_ONERI_YOL = pathlib.Path(__file__).parent / "oneriler.json"
_ONERI_DURUMLAR = ["📥 Yeni Öneri", "📞 İletişimde", "👀 İlgileniyor", "💬 Müzakere",
                   "⏳ Beklemede", "🤝 Anlaşıldı", "❌ Vazgeçildi"]
_ONERI_DURUM_RENK = {"📥 Yeni Öneri": "#a78bfa", "📞 İletişimde": "#60a5fa",
                     "👀 İlgileniyor": "#22d3ee", "💬 Müzakere": "#fbbf24",
                     "⏳ Beklemede": "#94a3b8", "🤝 Anlaşıldı": "#34d399",
                     "❌ Vazgeçildi": "#f87171"}
_ONERI_ONCELIK = ["🔴 Yüksek", "🟡 Orta", "🟢 Düşük"]
_ONERI_KOLON = ["id", "sahip", "tarih", "oyuncu", "kulup", "oneren",
                "durum", "oncelik", "not", "sd_url", "rapor_talep"]

def _oneriler_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"]); creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Oneriler")
        except Exception:
            ws = sh.add_worksheet(title="Oneriler", rows=3000, cols=len(_ONERI_KOLON))
            ws.update([_ONERI_KOLON])
            return ws
    except Exception:
        return None

@st.cache_data(ttl=60, show_spinner=False)
def oneriler_yukle() -> list:
    ws = _oneriler_ws()
    if ws is not None:
        try:
            return [{k: str(r.get(k, "")).strip() for k in _ONERI_KOLON}
                    for r in ws.get_all_records() if str(r.get("id", "")).strip()]
        except Exception:
            pass
    if not _ONERI_YOL.exists():
        return []
    import json
    try:
        with open(_ONERI_YOL, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def oneriler_kaydet(liste: list):
    ws = _oneriler_ws()
    if ws is not None:
        try:
            rows = [_ONERI_KOLON] + [[o.get(k, "") for k in _ONERI_KOLON] for o in liste]
            ws.clear(); ws.update(rows)
            oneriler_yukle.clear()
            return
        except Exception:
            pass
    import json
    with open(_ONERI_YOL, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
    oneriler_yukle.clear()

def oneri_ekle(sahip, oyuncu, kulup, oneren, oncelik, notu, sd_url=""):
    import uuid
    from datetime import date as _d
    liste = list(oneriler_yukle())
    liste.append({"id": uuid.uuid4().hex[:8], "sahip": sahip,
                  "tarih": _d.today().isoformat(), "oyuncu": oyuncu, "kulup": kulup,
                  "oneren": oneren, "durum": _ONERI_DURUMLAR[0],
                  "oncelik": oncelik or _ONERI_ONCELIK[1], "not": notu, "sd_url": sd_url})
    oneriler_kaydet(liste)

def oneri_guncelle(oid, **alanlar):
    liste = oneriler_yukle()
    for o in liste:
        if o.get("id") == oid:
            o.update(alanlar)
    oneriler_kaydet(liste)

def oneri_sil(oid):
    oneriler_kaydet([o for o in oneriler_yukle() if o.get("id") != oid])

def oneri_rapor_talep_et(o: dict):
    """Bir öneri için scout raporu talebi gönderir (Talepler sheet + e-posta),
    sonra öneriyi 'rapor istendi' diye işaretler. (kayit_ok, mail_ok) döndürür."""
    from datetime import date as _d
    detay = (f"Öneri Merkezi'nden scout raporu talebi.\n"
             f"Oyuncu: {o.get('oyuncu', '')}\n"
             f"Kulüp: {o.get('kulup') or '—'}\n"
             f"Öneren: {o.get('oneren') or '—'}\n"
             f"Öncelik: {o.get('oncelik', '')}\n"
             f"Durum: {o.get('durum', '')}\n"
             f"Not: {o.get('not') or '—'}\n"
             f"SoccerDonna: {o.get('sd_url') or '—'}")
    k_ok, m_ok = talep_gonder("Scout Raporu", o.get("oyuncu", ""),
                              o.get("kulup", ""), o.get("sahip", ""), detay)
    oneri_guncelle(o.get("id"), rapor_talep=_d.today().isoformat())
    return k_ok, m_ok

def _sd_url_isim(url: str) -> str:
    """SoccerDonna URL slug'ından oyuncu adını çıkarır (canlı çekim yok)."""
    import re
    url = (url or "").split("?")[0]
    for kal in (r"/(?:player|spieler)/(?:\d+/)?([A-Za-z][A-Za-z0-9\-]+)",
                r"/([A-Za-z][A-Za-z]+-[A-Za-z][A-Za-z\-]+)/"):
        m = re.search(kal, url)
        if m:
            slug = m.group(1).replace("-", " ").strip()
            if slug and not slug.replace(" ", "").isdigit() and "profil" not in slug.lower():
                return " ".join(w.capitalize() for w in slug.split())
    return ""

@st.dialog("➕ Oyuncu Öner")
def _oneri_ekle_dialog(sahip: str):
    _mod0 = st.session_state.get("_oneri_dialog_mod", "url")
    _opts = [t("🔗 SoccerDonna URL", "🔗 SoccerDonna URL"), t("✏️ Elle Ekle", "✏️ Manual")]
    mod = st.radio("yontem", _opts, index=(0 if _mod0 == "url" else 1),
                   horizontal=True, label_visibility="collapsed", key="_oneri_mod")
    url = oyuncu = kulup = ""
    if mod == _opts[0]:
        url = st.text_input(t("SoccerDonna Linki", "SoccerDonna Link"),
                            placeholder="https://www.soccerdonna.de/en/player/...", key="_oneri_url")
        st.caption(t("URL'den oyuncu adı otomatik çıkarılır. (İstersen 'Elle Ekle' ile tam gir.)",
                     "Player name is auto-extracted from the URL. (Use 'Manual' for full control.)"))
    else:
        oyuncu = st.text_input(t("Oyuncu Adı", "Player Name"), key="_oneri_oyuncu")
        kulup = st.text_input(t("Kulüp", "Club"), key="_oneri_kulup")
    oneren = st.text_input(t("Öneren Scout / Menajer", "Recommended by (Scout / Agent)"), key="_oneri_oneren")
    oncelik = st.radio(t("Öncelik", "Priority"), _ONERI_ONCELIK, index=1,
                       horizontal=True, key="_oneri_oncelik")
    notu = st.text_area(t("Not", "Note"), placeholder=t("Scout gözlemi veya not…", "Scout observation or note…"),
                        key="_oneri_not")
    c1, c2 = st.columns(2)
    if c1.button(t("İptal", "Cancel"), use_container_width=True, key="_oneri_iptal"):
        st.rerun()
    if c2.button(t("Ekle", "Add"), type="primary", use_container_width=True, key="_oneri_ekle_btn"):
        if mod == _opts[0]:
            if not (url or "").strip():
                st.warning(t("Lütfen SoccerDonna linki gir.", "Please enter a SoccerDonna link.")); st.stop()
            oyuncu = _sd_url_isim(url) or t("SoccerDonna Oyuncusu", "SoccerDonna Player")
        if not (oyuncu or "").strip():
            st.warning(t("Lütfen oyuncu adı gir.", "Please enter a player name.")); st.stop()
        oneri_ekle(sahip, oyuncu.strip(), kulup.strip(), oneren.strip(),
                   oncelik, notu.strip(), (url or "").strip())
        st.rerun()

def render_oneri_merkezi(sahip: str):
    # Çok kiracılı: her kulüp YALNIZ kendi önerilerini görür; admin tümünü.
    # Giriş yoksa "admin" sezgisine düşmesin diye sahip'i güvenli anahtara sabitle.
    _is_admin = (st.session_state.get("kulup_rol") == "admin"
                 or st.session_state.get("kulup_kullanici") == "admin")
    _kul = st.session_state.get("kulup_kullanici", "")
    sahip = _kul if _kul else "_anon"
    tum = oneriler_yukle()
    benim = tum if _is_admin else [o for o in tum if o.get("sahip", "") == sahip]
    # Başlık + ekleme butonları
    bsol, bsag1, bsag2 = st.columns([3.4, 1.5, 1.4])
    with bsol:
        st.markdown(
            f"<div style='padding:4px 0 2px;'>"
            f"<div style='font-family:Oswald,Sora,sans-serif;font-size:1.5rem;font-weight:700;color:#fff;'>"
            f"📥 {t('Öneri Merkezi','Recommendation Center')}</div>"
            f"<div style='color:#8899aa;font-size:0.82rem;margin-top:2px;'>"
            f"<b style='color:#a78bfa;'>{len(benim)}</b> {t('oyuncu takip ediliyor','players tracked')}</div></div>",
            unsafe_allow_html=True)
    if bsag1.button(t("🔗 SoccerDonna URL ile Ekle", "🔗 Add via SoccerDonna URL"),
                    use_container_width=True, key="_oneri_btn_url"):
        st.session_state["_oneri_dialog_mod"] = "url"; _oneri_ekle_dialog(sahip)
    if bsag2.button(t("➕ Elle Oyuncu Ekle", "➕ Add Player Manually"), type="primary",
                    use_container_width=True, key="_oneri_btn_manuel"):
        st.session_state["_oneri_dialog_mod"] = "manuel"; _oneri_ekle_dialog(sahip)

    if not benim:
        st.info(t("Henüz öneri yok. Yukarıdaki butonlarla menajerden/scout'tan gelen oyuncuları ekle.",
                  "No recommendations yet. Use the buttons above to add players proposed by agents/scouts."))
        return

    # Tablo başlığı
    _orn = {"🔴 Yüksek": 0, "🟡 Orta": 1, "🟢 Düşük": 2}
    benim = sorted(benim, key=lambda o: (_orn.get(o.get("oncelik", ""), 3), o.get("tarih", "")), reverse=False)
    _ORAN = [2.3, 1.55, 1.75, 1.25, 2.5, 0.9, 1.4, 0.45]
    hb = st.columns(_ORAN)
    for col, lbl in zip(hb, [t("OYUNCU", "PLAYER"), t("ÖNEREN", "BY"), t("DURUM", "STATUS"),
                             t("ÖNCELİK", "PRIORITY"), t("NOT", "NOTE"), t("TARİH", "DATE"),
                             t("RAPOR", "REPORT"), ""]):
        col.markdown(f"<div style='font-size:0.62rem;font-weight:800;color:#64748b;"
                     f"letter-spacing:0.08em;padding-bottom:2px;'>{lbl}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#2a2a38;margin:2px 0 8px;'>", unsafe_allow_html=True)

    for o in benim:
        oid = o.get("id", "")
        rc = st.columns(_ORAN, vertical_alignment="center")
        _link = (f"<a href='{o['sd_url']}' target='_blank' style='color:#a78bfa;font-size:0.66rem;"
                 f"text-decoration:none;'>🔗 SoccerDonna</a>") if o.get("sd_url") else ""
        _alt = o.get("kulup", "") or _link
        rc[0].markdown(
            f"<div style='font-weight:700;color:#e8eef7;font-size:0.92rem;'>{o.get('oyuncu','')}</div>"
            f"<div style='color:#7a8699;font-size:0.72rem;'>{_alt}</div>", unsafe_allow_html=True)
        rc[1].markdown(f"<div style='color:#cbd5e1;font-size:0.84rem;padding-top:4px;'>"
                       f"{o.get('oneren','—') or '—'}</div>", unsafe_allow_html=True)
        # Durum (değiştirilebilir)
        _d_idx = _ONERI_DURUMLAR.index(o["durum"]) if o.get("durum") in _ONERI_DURUMLAR else 0
        yeni_d = rc[2].selectbox("durum", _ONERI_DURUMLAR, index=_d_idx,
                                 label_visibility="collapsed", key=f"_od_{oid}")
        if yeni_d != o.get("durum"):
            oneri_guncelle(oid, durum=yeni_d); st.rerun()
        # Öncelik (değiştirilebilir)
        _o_idx = _ONERI_ONCELIK.index(o["oncelik"]) if o.get("oncelik") in _ONERI_ONCELIK else 1
        yeni_o = rc[3].selectbox("oncelik", _ONERI_ONCELIK, index=_o_idx,
                                 label_visibility="collapsed", key=f"_oo_{oid}")
        if yeni_o != o.get("oncelik"):
            oneri_guncelle(oid, oncelik=yeni_o); st.rerun()
        rc[4].markdown(f"<div style='color:#aab4c4;font-size:0.80rem;line-height:1.45;'>"
                       f"{o.get('not','') or '—'}</div>", unsafe_allow_html=True)
        rc[5].markdown(f"<div style='color:#6b7689;font-size:0.74rem;padding-top:4px;'>"
                       f"{o.get('tarih','')}</div>", unsafe_allow_html=True)
        # Scout raporu talebi
        if o.get("rapor_talep"):
            rc[6].markdown(
                f"<div style='color:#34d399;font-size:0.70rem;line-height:1.2;padding-top:3px;'>"
                f"✓ {t('İstendi', 'Requested')}<br>"
                f"<span style='color:#6b7689;font-size:0.64rem;'>{o['rapor_talep']}</span></div>",
                unsafe_allow_html=True)
        elif rc[6].button(t("📄 Rapor İste", "📄 Request"), key=f"_orap_{oid}",
                          use_container_width=True,
                          help=t("Bu oyuncu için scout raporu talep et",
                                 "Request a scout report for this player")):
            _k, _m = oneri_rapor_talep_et(o)
            st.toast(t("📄 Scout raporu talebi gönderildi.", "📄 Scout report request sent.")
                     if (_k or _m) else
                     t("Talep kaydedildi (e-posta gitmedi).", "Request saved (email not sent)."),
                     icon="📄" if (_k or _m) else "⚠️")
            st.rerun()
        if rc[7].button("🗑", key=f"_osil_{oid}", help=t("Sil", "Delete")):
            oneri_sil(oid); st.rerun()
        st.markdown("<hr style='border-color:#20242f;margin:6px 0;'>", unsafe_allow_html=True)


# ─── Danışmanlık Talepleri ─────────────────────────────────────────────
# Talepler Google Sheets "Talepler" sayfasına yazılır + e-posta gönderilir.
# E-posta için secrets["smtp"] = {email, password (Gmail app password)} gerekir;
# yoksa talep yine Sheets'e kaydedilir (sahibi oradan görür).
TALEP_EMAIL = "mehmetbarandanis@gmail.com"

def _talep_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds",
                  "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"])
        creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Talepler")
        except Exception:
            ws = sh.add_worksheet(title="Talepler", rows=2000, cols=7)
            ws.update([["tarih", "tip", "isim", "kulup", "email", "detay", "sistem_on_onerisi"]])
            return ws
    except Exception:
        return None

def talep_gonder(tip, isim, kulup, email, detay, oneri=""):
    """Talebi Sheets'e yazar ve e-posta gönderir. (kayit_ok, mail_ok) döndürür."""
    from datetime import datetime
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    kayit_ok = mail_ok = False
    ws = _talep_ws()
    if ws is not None:
        try:
            ws.append_row([tarih, tip, isim, kulup, email, detay, oneri])
            kayit_ok = True
        except Exception:
            pass
    try:
        import smtplib
        from email.mime.text import MIMEText
        smtp = st.secrets["smtp"]
        body = (f"Yeni danışmanlık talebi\n\nTür: {tip}\nAd Soyad: {isim}\n"
                f"Kulüp: {kulup}\nE-posta / İletişim: {email}\nTarih: {tarih}\n\n"
                f"Detay:\n{detay}\n\n"
                f"--- Sistem ön-önerisi (otomatik) ---\n{oneri or '(yok)'}")
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = f"[Kadın Ligi] Talep: {tip}"
        msg["From"] = smtp["email"]
        msg["To"] = TALEP_EMAIL
        msg["Reply-To"] = email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(smtp["email"], smtp["password"])
            s.send_message(msg)
        mail_ok = True
    except Exception:
        pass
    return kayit_ok, mail_ok


def akilli_oneri(kategori, yas_max, oncelik, n=5):
    """Scouting havuzundan kritere uygun adayları döndürür (talep ön-önerisi)."""
    havuz = _benzer_havuz("scouting")
    adaylar = [o for o in havuz
               if o["kat"] == kategori and o["mac"] >= 10
               and (yas_max == 0 or 0 < o["yas"] <= yas_max)]
    anahtar = {"Gol oranı": "gol_mac", "Asist oranı": "asist_mac",
               "Deneyim (maç)": "mac", "Oynama süresi": "dk_mac"}.get(oncelik, "gol_mac")
    adaylar.sort(key=lambda o: o[anahtar], reverse=True)
    return adaylar[:n]


@st.cache_data(ttl=3600)
def scouting_veri_yukle():
    yol = pathlib.Path(__file__).parent / "scouting_oyuncular.xlsx"
    if not yol.exists():
        return pd.DataFrame()
    df = pd.read_excel(yol, engine="openpyxl")
    df.columns = [
        "İsim","Soyisim","Tam İsmi","Vatandaşlık","Milli Takım",
        "Doğum Yılı","Boy","Ayak","Vücut Tipi","Bölge",
        "Mevki 1","Mevki 2","Mevki 3","Rol","Kulüp","Lig","Sözleşme","Mr Danis 25"
    ]
    return df

_DANIS_ETIKET = {
    "Yıldız":"⭐ Yıldız","Uzman":"🎯 Uzman","Potansiyel":"🌱 Potansiyel",
    "Yeterli":"✅ Yeterli","Yedek":"🔄 Yedek",
}
_DANIS_RENK = {
    "Yıldız":"#f59e0b","Uzman":"#3b82f6","Potansiyel":"#10b981",
    "Yeterli":"#6b7280","Yedek":"#9ca3af",
}
_MEVKI_ACIKLAMA = {
    "GK":"Kaleci","LCB":"Sol Stoper","RCB":"Sağ Stoper","LWB":"Sol Kanat Bek",
    "RWB":"Sağ Kanat Bek","LFB":"Sol Bek","CMF":"Merkez Orta Saha",
    "LWF":"Sol Kanat","RWF":"Sağ Kanat","SST":"İkinci Santrafor","CFW":"Santrafor",
}


@st.cache_data(ttl=86400)
def kaleci_istatistikleri_hesapla() -> pd.DataFrame:
    """Her kaleci için yenilen gol ve maç başına yenilen gol hesaplar."""
    oyuncu_listesi = ham_liste
    _ff = _forfeit_hafta_takim()

    rows = []
    for o in oyuncu_listesi:
        isim  = o["oyuncu"]
        takim = o["takim"]
        pos   = sd_profiller.get(isim, {}).get("Position", "")
        if "Goalkeeper" not in pos:
            continue

        mac_gecmisi = o.get("mac_gecmisi", [])
        if isinstance(mac_gecmisi, str):
            import ast
            mac_gecmisi = ast.literal_eval(mac_gecmisi)

        # Transfer olan kaleci için: her maçta GERÇEKTEN oynadığı kulübün yediği gol
        # (birincil takım değil). _oyuncu_hafta_takim + _kanon + hükmen-atlama.
        _htk = _oyuncu_hafta_takim(o)
        yenilen = 0
        mac_say = 0
        for m in mac_gecmisi:
            if m.get("dakika", 0) < 45:
                continue
            hafta = m.get("hafta")
            tk = _htk.get(hafta) or takim
            if (hafta, _kanon(tk)) in _ff:   # hükmen/çekilme → gerçek maç yok
                continue
            gol = _hafta_yenilen(tk, hafta)
            if gol is not None:
                yenilen += gol
                mac_say += 1

        gpm = round(yenilen / mac_say, 2) if mac_say > 0 else 0.0
        rows.append({
            "Kaleci":     isim,
            "Takım":      takim,
            "Maç":        mac_say,
            "YenilenGol": yenilen,
            "G/Maç":      gpm,
        })

    df = pd.DataFrame(rows).sort_values(["Maç", "G/Maç"], ascending=[False, True])
    return df.reset_index(drop=True)


@st.cache_data
def manuel_yaslar_yukle(file_hash: str = "") -> tuple:
    """file_hash parametresi: dosya değişince cache otomatik bozulur."""
    yol = _DIZIN / "manual_ages.json"
    if not yol.exists():
        return {}, {}, {}
    with open(yol, encoding="utf-8") as f:
        raw = json.load(f)
    ages, positions, nationalities = {}, {}, {}
    today = pd.Timestamp.today()
    for isim, veri in raw.items():
        try:
            born_dt = pd.to_datetime(veri["born"], format="%d.%m.%Y")
            ages[isim] = round((today - born_dt).days / 365.25, 1)
        except Exception:
            pass
        if "position" in veri:
            positions[isim] = veri["position"]
        if "nationality" in veri:
            nationalities[isim] = veri["nationality"]
    return ages, positions, nationalities

_manuel_json = _DIZIN / "manual_ages.json"
_manuel_hash = __import__("hashlib").md5(_manuel_json.read_bytes()).hexdigest() if _manuel_json.exists() else ""
_MANUEL_YAS, _MANUEL_MEVKI, _MANUEL_UYRUK = manuel_yaslar_yukle(_manuel_hash)


def mevki_normalize(pozisyon: str) -> str:
    if not pozisyon: return "Bilinmiyor"
    p = pozisyon.lower()
    # Kaleci
    if "goalkeeper" in p: return "Kaleci"
    # Defans — detaylı
    if "right back" in p or "fullback, right" in p or "rv" == p: return "Sağ Bek"
    if "left back" in p or "fullback, left" in p or "lv" == p: return "Sol Bek"
    if "centre back" in p or "center back" in p or "central back" in p: return "Stoper"
    if "defend" in p or "defence" in p: return "Defans"
    # Orta Saha — detaylı
    if "defensive mid" in p or "midfield - def" in p: return "Savunmacı Orta Saha"
    if "midfield, left" in p or "midfield - left" in p: return "Sol Kanat"
    if "midfield, right" in p or "midfield - right" in p: return "Sağ Kanat"
    if "central mid" in p or "midfield - central" in p or "midfield - midfield" in p: return "Merkez Orta Saha"
    if "attacking mid" in p or "midfield - attack" in p: return "Hücumcu Orta Saha"
    if "left wing" in p and "mid" in p: return "Sol Kanat"
    if "right wing" in p and "mid" in p: return "Sağ Kanat"
    if "midfield" in p: return "Orta Saha"
    # Forvet — detaylı
    if "centre forward" in p or "center forward" in p: return "Santrafor"
    if "second striker" in p: return "İkinci Santrafor"
    if "left wing" in p or "striker - left" in p: return "Sol Kanat Forvet"
    if "right wing" in p or "striker - right" in p: return "Sağ Kanat Forvet"
    if "striker" in p or "forward" in p: return "Forvet"
    return "Bilinmiyor"


import re as _re
import html as _html


def df_tablo(df, basliklar=None, formatlar=None, height=None):
    """DataFrame'i ws-table HTML olarak render eder: masaüstünde tablo, mobilde
    (≤768px) mevcut .ws-table CSS'i sayesinde OTOMATİK kart düzeni (yatay kaydırma yok).
    st.dataframe'in canvas tablosu mobilde sığmıyordu; bu HTML tablo data-label ile
    her hücreyi etiketleyip kart görünümüne dönüşür.

    basliklar: {iç_kolon: görünen_başlık}  (yoksa kolon adı; EN çevirisi için kullan)
    formatlar: {iç_kolon: callable(v)->str} (yoksa otomatik: float→%g, int→tam sayı)
    İlk kolon kart başlığı (ws-name) olur; sayısal kolonlar sağa yaslı (ws-mono).
    NOT: yalnız GÖRÜNTÜ tabloları için — satır-seçimli (on_select) tablolar st.dataframe kalmalı.
    """
    basliklar = basliklar or {}
    formatlar = formatlar or {}
    cols = list(df.columns)
    num = {c for c in cols if pd.api.types.is_numeric_dtype(df[c])}

    def esc(x):
        return _html.escape(str(x))

    def fmt(c, v):
        if c in formatlar:
            try:
                return esc(formatlar[c](v))
            except Exception:
                return esc(v)
        try:
            if pd.isna(v):
                return "—"
        except (TypeError, ValueError):
            pass
        if isinstance(v, float):
            return esc(f"{v:g}")
        return esc(v)

    def th(c):
        return f"<th class='num'>{esc(basliklar.get(c, c))}</th>" if c in num \
            else f"<th>{esc(basliklar.get(c, c))}</th>"
    thead = "<tr>" + "".join(th(c) for c in cols) + "</tr>"

    satirlar = []
    for _, r in df.iterrows():
        hucreler = []
        for i, c in enumerate(cols):
            val = fmt(c, r[c])
            if i == 0:
                hucreler.append(f"<td><span class='ws-name'>{val}</span></td>")
            else:
                cls = "num ws-mono" if c in num else ""
                hucreler.append(f"<td class='{cls}' data-label='{esc(basliklar.get(c, c))}'>{val}</td>")
        satirlar.append("<tr>" + "".join(hucreler) + "</tr>")

    stil = f" style='max-height:{height}px;'" if height else ""
    st.markdown(
        f"<div class='ws-wrap'{stil}><table class='ws-table'>"
        f"<thead>{thead}</thead><tbody>{''.join(satirlar)}</tbody></table></div>",
        unsafe_allow_html=True)


# Mevki kategorileri — geniş → detay (global, her yerde kullanılır)
_MEVKI_DETAY = {
    "Kaleci":    ["Kaleci"],
    "Defans":    ["Sağ Bek", "Sol Bek", "Stoper", "Defans"],
    "Orta Saha": ["Savunmacı Orta Saha", "Merkez Orta Saha", "Hücumcu Orta Saha",
                  "Sol Kanat", "Sağ Kanat", "Orta Saha"],
    "Forvet":    ["Santrafor", "İkinci Santrafor", "Sol Kanat Forvet", "Sağ Kanat Forvet", "Forvet"],
}

# Detaylı mevki → geniş grup (Kaleci/Defans/Orta Saha/Forvet) ters haritası.
# mevki_normalize çoğu oyuncuya detaylı pozisyon verdiği için, geniş kategoriyle
# doğrudan "==" karşılaştırması çoğu oyuncuyu dışarıda bırakıyordu.
_MEVKI_GRUP_MAP = {}
for _g, _ds in _MEVKI_DETAY.items():
    _MEVKI_GRUP_MAP[_g] = _g
    for _d in _ds:
        _MEVKI_GRUP_MAP[_d] = _g

def mevki_grup(m: str) -> str:
    """Detaylı veya geniş mevki adını 4 ana gruptan birine indirger."""
    return _MEVKI_GRUP_MAP.get(m, "Bilinmiyor")

# Mevki → renk (detaylı pozisyonlar da grup üzerinden renklenir; gri kalmaz)
_MEVKI_GRUP_RENK = {
    "Kaleci":    "#fbbf24",   # amber
    "Defans":    "#2979ff",   # mavi
    "Orta Saha": "#ff6d00",   # turuncu
    "Forvet":    "#e040fb",   # macenta
    "Bilinmiyor":"#8899aa",   # gri (gerçekten bilinmeyen)
}
def mevki_renk(m: str) -> str:
    """Herhangi bir mevki adını (detaylı/geniş) ana grup rengine eşler."""
    return _MEVKI_GRUP_RENK.get(mevki_grup(m), "#8899aa")

# Mevki adı TR→EN gösterim haritası (iç değer TR kalır, sadece görünüm çevrilir)
_MEVKI_EN = {
    "Kaleci": "Goalkeeper", "Defans": "Defense", "Orta Saha": "Midfield",
    "Forvet": "Forward", "Bilinmiyor": "Unknown",
    "Sağ Bek": "Right Back", "Sol Bek": "Left Back", "Stoper": "Centre Back",
    "Sağ Kanat Bek": "Right Wing-Back", "Sol Kanat Bek": "Left Wing-Back",
    "Savunmacı Orta Saha": "Defensive Midfield", "Merkez Orta Saha": "Central Midfield",
    "Hücumcu Orta Saha": "Attacking Midfield", "Sol Kanat": "Left Wing", "Sağ Kanat": "Right Wing",
    "Santrafor": "Striker", "İkinci Santrafor": "Second Striker",
    "Sol Kanat Forvet": "Left Winger", "Sağ Kanat Forvet": "Right Winger",
}

def mevki_goster(m):
    """Mevki adını aktif dile göre gösterir (iç değer TR kalır)."""
    if not EN:
        return m
    return _MEVKI_EN.get(m, m)


def mevki_disp(raw: str) -> str:
    """Ham SD pozisyonunu ('Midfield - Defensive Midfield') temiz, DİLE UYGUN ada çevirir.
    TR'de Türkçe ('Savunmacı Orta Saha'), EN'de 'Defensive Midfield'. Eşlenemezse ham bırakır."""
    if not raw or raw == "—":
        return raw or ""
    norm = mevki_normalize(raw)
    return mevki_goster(norm) if norm != "Bilinmiyor" else raw

# Transfer Öner birleşik mevki etiketleri (_TRANSFER_DB anahtarları) + tercih TR→EN
_TR_MEVKI_EN = {
    "Kaleci": "Goalkeeper",
    "Sağ Bek - Sağ Kanat Bek": "Right Back - Right Wing-Back",
    "Sağ Stoper": "Right Centre Back", "Sol Stoper": "Left Centre Back",
    "Sol Bek - Sol Kanat Bek": "Left Back - Left Wing-Back",
    "Savunmacı Orta Saha": "Defensive Midfield", "Merkez Orta Saha": "Central Midfield",
    "Hücumcu Orta Saha": "Attacking Midfield",
    "Sol Kanat": "Left Wing", "Sağ Kanat": "Right Wing", "Santrafor": "Striker",
}
_TR_TERCIH_EN = {"Farketmez": "No preference", "Yerli": "Domestic", "Yabancı": "Foreign"}

# ── Scouting detay (Mr Daniş) görünüm çevirileri — iç değer TR kalır ──
_MR_DANIS_EN = {
    "Yıldız": "Star", "Uzman": "Expert", "Potansiyel": "Potential",
    "Yeterli": "Adequate", "Yedek": "Backup",
}
_ROL_EN = {
    "Dengeli Bek": "Balanced Full-Back", "Hedef Kanat": "Target Winger",
    "Hedef Santrfor": "Target Striker", "Hükmeden Kaleci": "Commanding Goalkeeper",
    "Kanat Bek": "Wing-Back", "Libero Kaleci": "Sweeper Keeper",
    "Limitli Stoper": "Limited Centre-Back", "Modern Bek": "Modern Full-Back",
    "Oyun Kurucu": "Playmaker", "Oyun Kurucu Stoper": "Ball-Playing Centre-Back",
    "Pozisyonunu Tutan": "Positional Holder", "Sahte 9": "False 9",
    "Çakılı Stoper": "No-Nonsense Centre-Back", "Çizgi Kalecisi": "Shot-Stopper",
    "İçe Kat Eden Kanat": "Inverted Winger",
}
_VUCUT_EN = {
    "Ektomorf": "Ectomorph", "Endomorf": "Endomorph", "Mezomorf": "Mesomorph",
    "Mezo-Ektomorf": "Meso-Ectomorph", "Mezo-Endomorf": "Meso-Endomorph",
    "Hücum": "Attack", "Orta Saha": "Midfield", "Orta Sha": "Midfield", "Savunma": "Defense",
}
_BOLGE_EN = {"Hücum": "Attack", "Kale": "Goal", "Orta Saha": "Midfield", "Savunma": "Defense"}
_ETIKET_BADGE_EN = {
    "🔴 Öncelik": "🔴 Priority", "👀 İzle": "👀 Watch",
    "💰 Pahalı": "💰 Expensive", "✅ Görüşüldü": "✅ Contacted",
}
# Yaygın TR→EN ülke adları (GSheets Vatandaşlık kolonu Türkçe gelir)
_ULKE_EN = {
    "Kazakistan": "Kazakhstan", "Almanya": "Germany", "Fransa": "France", "İspanya": "Spain",
    "İtalya": "Italy", "İngiltere": "England", "Hollanda": "Netherlands", "Belçika": "Belgium",
    "Brezilya": "Brazil", "Arjantin": "Argentina", "Portekiz": "Portugal", "Rusya": "Russia",
    "Ukrayna": "Ukraine", "Polonya": "Poland", "İsveç": "Sweden", "Norveç": "Norway",
    "Danimarka": "Denmark", "Finlandiya": "Finland", "İzlanda": "Iceland", "İrlanda": "Ireland",
    "İskoçya": "Scotland", "Galler": "Wales", "Avusturya": "Austria", "İsviçre": "Switzerland",
    "Yunanistan": "Greece", "Sırbistan": "Serbia", "Hırvatistan": "Croatia", "Slovenya": "Slovenia",
    "Slovakya": "Slovakia", "Çekya": "Czechia", "Macaristan": "Hungary", "Romanya": "Romania",
    "Bulgaristan": "Bulgaria", "Arnavutluk": "Albania", "Kosova": "Kosovo", "Karadağ": "Montenegro",
    "Kuzey Makedonya": "North Macedonia", "Bosna-Hersek": "Bosnia-Herzegovina", "Moldova": "Moldova",
    "Litvanya": "Lithuania", "Letonya": "Latvia", "Estonya": "Estonia", "Belarus": "Belarus",
    "Gürcistan": "Georgia", "Ermenistan": "Armenia", "Azerbaycan": "Azerbaijan", "Özbekistan": "Uzbekistan",
    "Kırgızistan": "Kyrgyzstan", "Tacikistan": "Tajikistan", "Türkmenistan": "Turkmenistan",
    "ABD": "USA", "Amerika": "USA", "Kanada": "Canada", "Meksika": "Mexico", "Kolombiya": "Colombia",
    "Şili": "Chile", "Peru": "Peru", "Uruguay": "Uruguay", "Paraguay": "Paraguay", "Ekvador": "Ecuador",
    "Venezuela": "Venezuela", "Bolivya": "Bolivia", "Kosta Rika": "Costa Rica", "Jamaika": "Jamaica",
    "Nijerya": "Nigeria", "Gana": "Ghana", "Kamerun": "Cameroon", "Senegal": "Senegal",
    "Fildişi Sahili": "Ivory Coast", "Fas": "Morocco", "Tunus": "Tunisia", "Cezayir": "Algeria",
    "Mısır": "Egypt", "Güney Afrika": "South Africa", "Kenya": "Kenya", "Zambiya": "Zambia",
    "Kongo": "Congo", "Burkina Faso": "Burkina Faso", "Mali": "Mali", "Togo": "Togo",
    "Japonya": "Japan", "Çin": "China", "Güney Kore": "South Korea", "Avustralya": "Australia",
    "Yeni Zelanda": "New Zealand", "Hindistan": "India", "Tayland": "Thailand", "İran": "Iran",
    "Türkiye": "Turkey",
    # Eksik ülkeler (scout taramasından)
    "Beyaz Rusya": "Belarus", "Bosna Hersek": "Bosnia-Herzegovina",
    "Rusya Federasyonu": "Russia", "Lüksemburg": "Luxembourg", "Irak": "Iraq",
    "Porto Riko": "Puerto Rico", "Dominik Cumhuriyeti": "Dominican Republic",
    "Kongo Demokratik Cumhuriyeti": "DR Congo", "Trinidad ve Tobago": "Trinidad and Tobago",
    "Tanzanya": "Tanzania", "Lübnan": "Lebanon", "Suudi Arabistan": "Saudi Arabia",
    "Yeşil Burun": "Cape Verde", "Ekvator Ginesi": "Equatorial Guinea",
    # Yazım hatası savunmaları (sheet'te düzeltilene kadar doğru göster)
    "Marocco": "Morocco", "Tunusia": "Tunisia", "Türkiey": "Turkey",
}

def danis_goster(m):
    return _MR_DANIS_EN.get(m, m) if EN else m
def rol_goster(m):
    return _ROL_EN.get(m, m) if EN else m
def vucut_goster(m):
    return _VUCUT_EN.get(m, m) if EN else m
def bolge_goster(m):
    return _BOLGE_EN.get(m, m) if EN else m
def etiket_badge_goster(m):
    return _ETIKET_BADGE_EN.get(m, m) if EN else m
# EN→TR ters harita (ilk eşleşme kazanır → typo/ikincil adlar ezmez)
_ULKE_TR = {}
for _tr_ad, _en_ad in _ULKE_EN.items():
    _ULKE_TR.setdefault(_en_ad, _tr_ad)

def ulke_goster(m):
    """Ülke adını aktif dile çevirir (çift yönlü). EN: TR→EN, TR: EN→TR.
    Kaynaklar karışık (sheet Türkçe, SoccerDonna İngilizce) → iki yönde de tutarlı."""
    m = (m or "").strip()
    return _ULKE_EN.get(m, m) if EN else _ULKE_TR.get(m, m)

def _ilk_uyruk(nat_str: str) -> str:
    """'TurkeyGermany' → 'Turkey', 'United StatesEthiopia' → 'United States', 'France' → 'France'.
    SD uyruk sırasında İLK ülke = milli takım (scouting ground-truth'ta 83/83 doğrulandı).
    Çok-kelimeli ülke adlarını (United States, South Korea…) bozmamak için ülke
    SINIRINDA (küçük→büyük) ayırır, kelime kelime değil."""
    nat_str = (nat_str or "").strip()
    if not nat_str:
        return ""
    # Yalnız ülke sınırına (örn. 'States|Ethiopia') ayır; iç boşluklar korunur
    return _re.sub(r"(?<=[a-z])(?=[A-Z])", "|", nat_str).split("|")[0].strip()


# ── Takım adı kısaltma (uzun resmi TFF adları → kısa görünüm) ──────────────────
# Alt-dize eşleşmesi (büyük harf). İç eşleştirme/filtre TAM isimle kalır; bu yalnız GÖSTERİM.
_TAKIM_KISA_MAP = [
    ("BEŞİKTAŞ", "Beşiktaş"), ("GALATASARAY", "Galatasaray"), ("FENERBAHÇE", "Fenerbahçe"),
    ("TRABZONSPOR", "Trabzonspor"), ("FOMGET", "FOMGET"), ("AMED", "Amed"),
    ("YÜKSEKOVA", "Yüksekovaspor"), ("HAKKARİGÜCÜ", "Hakkarigücü"), ("HAKKARIGÜCÜ", "Hakkarigücü"),
    ("ÜNYE", "Ünye"), ("GİRESUN", "Giresun Sanayi"), ("GIRESUN", "Giresun Sanayi"),
    ("FATİH VATAN", "Fatih Vatan"), ("FATIH VATAN", "Fatih Vatan"),
    # Çekmeköy ile Şile İKİ AYRI takım — ikisi de "BİLGİDOĞA" içerir, Çekmeköy ÖNCE gelmeli
    ("ÇEKMEKÖY", "Çekmeköy Bilgidoğa"), ("CEKMEKÖY", "Çekmeköy Bilgidoğa"),
    ("BİLGİDOĞA", "Şile Bilgidoğa"), ("BILGIDOĞA", "Şile Bilgidoğa"),
    ("1207", "1207 Antalya"), ("BEYLERBEYİ", "Beylerbeyi"), ("BEYLERBEYI", "Beylerbeyi"),
    ("BORNOVA", "Bornova Hitab"), ("ALG", "ALG"),
]
_TAKIM_BOILERPLATE = [
    " SPORTİF YATIRIM HİZMETLERİ A.Ş", " SPORTİF FAALİYETLER", " KADIN FUTBOL SPOR KULÜBÜ",
    " KADIN FUTBOL KULÜBÜ", " KADIN FUTBOL TAKIMI", " KADIN SPOR KULÜBÜ",
    " GENÇLİK VE SPOR KULÜBÜ", " GENÇLİK VE SPOR", " FUTBOL KULÜBÜ", " SPOR KULÜBÜ",
    " KULÜBÜ", " A.Ş.", " A.Ş",
]

def _takim_kisa(ad: str) -> str:
    """Uzun TFF takım adını kısa görünüme indirger. 'A / B' (transfer) için her parçayı ayrı kısaltır."""
    if not ad:
        return ad
    if "/" in ad:
        return " / ".join(_takim_kisa(p.strip()) for p in ad.split("/"))
    up = ad.upper()
    for sub, kisa in _TAKIM_KISA_MAP:
        if sub in up:
            return kisa
    # Bilinmeyen (alt lig vb.): boilerplate ekleri at, sadeleştir
    s = ad
    for k in _TAKIM_BOILERPLATE:
        s = s.replace(k, "").replace(k.title(), "")
    return " ".join(s.split()).strip(" -·") or ad


def _kanon_takim_sayisi(takim_serisi) -> int:
    """Süper Lig benzersiz KULÜP sayısı (özet/headline için). İsim varyantları _takim_kisa ile
    birleşir (ör. 'ALG SPOR' / 'GAZİANTEP ALG SPOR' / 'SERCAN İNŞAAT GAZİANTEP ALG SPOR' → tek 'ALG').
    Ayrıca Çekmeköy/Şile Bilgidoğa AYNI kulüptür (kulüp taşındı) → tek sayılır.
    NOT: global _takim_kisa bu ikisini bilinçli AYRI tutar (transfer atfı/clean-sheet için);
    burada yalnız özet sayım amacıyla birleştirilir → 17 isim varyantı → 14 kulüp."""
    kanon = takim_serisi.dropna().map(_takim_kisa).replace({"Çekmeköy Bilgidoğa": "Şile Bilgidoğa"})
    return int(kanon.nunique())


def _uyruk_goster(nat_str: str) -> str:
    """Çift vatandaşlık gösterimi: 'DenmarkFaroe Island' → 'Denmark / Faroe Island'.
    SD profilinde iki uyruk ayraçsız bitişik geliyor; küçük→büyük sınırına ' / ' koyar.
    (Ülke adlarındaki boşluk/tire sınır oluşturmaz → tek uyruk bozulmaz.)"""
    s = (nat_str or "").strip()
    if not s:
        return ""
    return _re.sub(r"(?<=[a-z])(?=[A-Z])", " / ", s)


@st.cache_data
def df_zenginlestir(df: "pd.DataFrame", file_hash: str = "", _v: str = "v2") -> "pd.DataFrame":
    """df_tam'a Mevki, Uyruk, Boy ve Yaş sütunlarını ekler. file_hash + _v cache bozucu."""
    df = df.copy()
    df["Mevki"] = df["Oyuncu"].map(
        lambda o: mevki_normalize(
            _MANUEL_MEVKI.get(o) or sd_profiller.get(o, {}).get("Position", "")
        )
    )
    df["Uyruk"] = df["Oyuncu"].map(
        lambda o: _MANUEL_UYRUK.get(o) or _ilk_uyruk(sd_profiller.get(o, {}).get("Nationality", ""))
    )
    df["Boy"] = df["Oyuncu"].map(
        lambda o: sd_profiller.get(o, {}).get("Height", "")
    )

    def _yas(oyuncu):
        if oyuncu in _MANUEL_YAS:
            return _MANUEL_YAS[oyuncu]
        profil = sd_profiller.get(oyuncu, {})
        try:
            age = float(str(profil.get("Age", "")).split()[0])
            return age if 15 <= age <= 40 else None
        except Exception:
            return None

    df["Yaş"] = df["Oyuncu"].map(_yas)
    return df


if not df_tam.empty:
    df_tam = df_zenginlestir(df_tam, _manuel_hash)  # hash değişince otomatik yeniler


# coaches.json — cache yok, her başlatmada taze okunur
_coaches_yol = _DIZIN / "coaches.json"
coaches_data = json.load(open(_coaches_yol, encoding="utf-8")) if _coaches_yol.exists() else {}

def tum_hocalar() -> list:
    """Sezondaki tüm hocaların listesi (tekrarsız, sıralı)."""
    hocalar = set()
    for isim_listesi in coaches_data.values():
        for h in isim_listesi:
            hocalar.add(h)
    return sorted(hocalar)


# Zayıf takımlar — bu takımlara atılan goller farklı renkte gösterilir
_ZAYIF_TAKIMLAR = {
    "SERCAN İNŞAAT GAZİANTEP ALG SPOR",
    "GAZİANTEP ALG SPOR KULÜBÜ",
    "ALG SPOR",
    "1207 ANTALYASPOR  KADIN FUTBOL KULÜBÜ",
    "1207 ANTALYASPOR KADIN FUTBOL KULÜBÜ",
    "ÇEKMEKÖY BİLGİDOĞA",
    "ŞİLE BİLGİDOĞA",
    "ŞİLE BİLGİDOĞA SPORTİF YATIRIM HİZMETLERİ A.Ş",
    "FATİH VATAN SPOR",
}


def _gol_rakip_dagil(detay: dict) -> dict:
    """
    Oyuncunun mac_gecmisi + mac_sonuclari kullanarak hangi takıma
    kaç gol attığını döndürür: {rakip_adi: gol_sayisi}

    Rakip, oyuncunun o hafta GERÇEKTEN oynadığı kulübün (transferse eski/yeni)
    fikstüründen bulunur (bkz. _oyuncu_hafta_takim). Hükmen/çekilme haftalarında
    gerçek maç oynanmadığından gol atfedilmez.
    """
    hafta_takim = _oyuncu_hafta_takim(detay)
    _ff = _forfeit_hafta_takim()
    rakip_goller: dict = {}
    for m in detay.get("mac_gecmisi", []):
        oyuncu_gol = m.get("gol", 0)
        if oyuncu_gol == 0:
            continue
        hafta = m["hafta"]
        # Maç anında saklanan gerçek rakip varsa onu kullan (en güvenilir)
        rakip = m.get("rakip")
        if not rakip:
            tk = (hafta_takim.get(hafta) or detay.get("takim", "") or "")
            if not tk:
                continue
            # Hükmen/çekilme maçı (gerçek maç oynanmadı) → gol ATFEDİLMEZ
            if (hafta, _kanon(tk)) in _ff:
                continue
            rakip = _hafta_rakip(tk, hafta)
        if not rakip:
            continue
        rakip_goller[rakip] = rakip_goller.get(rakip, 0) + oyuncu_gol
    return dict(sorted(rakip_goller.items(), key=lambda x: -x[1]))


def _gol_rakip_grafik(detay: dict, toplam_gol: int):
    """Rakip bazlı gol dağılımı yatay bar chart. Zayıf takımlar turuncu."""
    dagil = _gol_rakip_dagil(detay)
    if not dagil:
        return
    rakipler = list(dagil.keys())
    goller   = list(dagil.values())
    renkler  = [
        "#ff8f00" if r.upper() in _ZAYIF_TAKIMLAR else "#2979ff"
        for r in rakipler
    ]
    etiketler = [_takim_kisa(r) for r in rakipler]

    zayif_toplam = sum(g for r, g in dagil.items() if r.upper() in _ZAYIF_TAKIMLAR)
    guclu_toplam = toplam_gol - zayif_toplam

    st.markdown(
        f"##### ⚽ {t('Gollerin Rakip Dağılımı', 'Goals by Opponent')}"
    )
    if zayif_toplam > 0:
        st.caption(
            t(
                f"🟠 Zayıf takımlara: **{zayif_toplam}** gol · "
                f"🔵 Diğer rakiplere: **{guclu_toplam}** gol",
                f"🟠 vs. weak opponents: **{zayif_toplam}** goals · "
                f"🔵 vs. others: **{guclu_toplam}** goals",
            )
        )

    fig = go.Figure(go.Bar(
        x=goller, y=etiketler, orientation="h",
        marker_color=renkler,
        text=goller, textposition="outside",
        hovertemplate="%{y}<br>%{x} " + t("gol", "goals") + "<extra></extra>",
    ))
    fig.update_layout(
        height=max(180, len(rakipler) * 38),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=11),
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(title=t("Gol", "Goals"), gridcolor="#1e293b", dtick=1),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10)),
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key=_pk("plt_1717"))


def _clean_sheet_grafik(rakip_dagil: dict, toplam: int):
    """Gol yenmeyen (clean sheet) maçların rakip bazlı dağılımı — yatay bar (yeşil)."""
    if not rakip_dagil:
        return
    items = sorted(rakip_dagil.items(), key=lambda x: x[1])   # plotly yatay: küçük altta
    rakipler = [k for k, _ in items]
    sayilar  = [v for _, v in items]
    st.markdown(f"##### 🧤 {t('Gol Yenmeyen Maçlar — Rakip', 'Clean Sheets — by Opponent')}")
    st.caption(t(f"🧤 Oynadığı maçlarda toplam {toplam} kez gol yenmedi (skor: 0)",
                 f"🧤 {toplam} clean sheets in matches played (conceded: 0)"))
    fig = go.Figure(go.Bar(
        x=sayilar, y=rakipler, orientation="h",
        marker_color="#22c55e", text=sayilar, textposition="outside",
        hovertemplate="%{y}<br>%{x} clean sheet<extra></extra>"))
    fig.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
        font=dict(color="#e0e0e0"), height=max(190, 46 + len(rakipler) * 34),
        xaxis=dict(title=t("Gol Yenmeyen Maç", "Clean Sheets"), gridcolor="#2d3561", dtick=1),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=34, t=8, b=36), showlegend=False)
    st.plotly_chart(fig, width="stretch", key=_pk("plt_cs"))


def max_seri(dizi):
    """Ardışık 1'lerin en uzun serisini döndürür."""
    maks = suan = 0
    for v in dizi:
        suan = suan + 1 if v else 0
        maks = max(maks, suan)
    return maks


def norm_val(val, maks):
    """0-100 normalize (radar chart için)."""
    return round(val / maks * 100, 1) if maks else 0


# ── Ana lig (TR Süper Lig) kariyer verisi ──
@st.cache_data(ttl=3600)
def analig_leistung_yukle() -> dict:
    yol = pathlib.Path(__file__).parent / "analig_leistungsdaten.json"
    if not yol.exists():
        return {}
    import json
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


# ── Kariyer trend yardımcıları ──
def _kariyer_sezon_topla(sezonlar):
    """Kulüp ligleri (milli hariç) sezon bazlı gol/asist/dakika/maç toplamı."""
    agg = {}
    for s in sezonlar:
        if s.get("milli"):
            continue
        d = agg.setdefault(s["sezon"], {"gol": 0, "asist": 0, "dakika": 0, "mac": 0})
        d["gol"]    += s.get("gol", 0)
        d["asist"]  += s.get("asist", 0)
        d["dakika"] += s.get("dakika", 0)
        d["mac"]    += s.get("mac", 0)
    return dict(sorted(agg.items()))


def _kariyer_trend_figuru(sezonlar):
    """Sezon-sezon gol/asist (bar) + dakika (çizgi) Plotly figürü."""
    agg = _kariyer_sezon_topla(sezonlar)
    if not agg:
        return None
    sz    = list(agg.keys())
    gol   = [agg[x]["gol"] for x in sz]
    asist = [agg[x]["asist"] for x in sz]
    dk    = [agg[x]["dakika"] for x in sz]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sz, y=gol, name=t("Gol", "Goals"), marker_color="#22c55e"))
    fig.add_trace(go.Bar(x=sz, y=asist, name=t("Asist", "Assists"), marker_color="#3b82f6"))
    # Dakika verisi varsa (>0) çizgi göster; yoksa ekseni yine de koy ama gizli tut
    dk_var = any(d > 0 for d in dk)
    if dk_var:
        fig.add_trace(go.Scatter(x=sz, y=[d if d > 0 else None for d in dk],
                                 name=t("Dakika", "Minutes"), yaxis="y2",
                                 mode="lines+markers", line=dict(color="#f59e0b", width=3),
                                 connectgaps=False))
    fig.update_layout(
        barmode="group", height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=12),
        margin=dict(l=10, r=10, t=28, b=10),
        legend=dict(orientation="h", y=1.18, x=0),
        yaxis=dict(title=t("Gol / Asist", "Goals / Assists"), gridcolor="#1e293b"),
        yaxis2=dict(title=t("Dakika", "Minutes"), overlaying="y", side="right",
                    showgrid=False, visible=dk_var),
        xaxis=dict(gridcolor="#1e293b"),
    )
    return fig


def _form_rozeti(sezonlar):
    """Son 2 sezon gol+asist trendine göre form etiketi (HTML)."""
    agg = _kariyer_sezon_topla(sezonlar)
    sz  = list(agg.keys())
    if len(sz) < 2:
        return ""
    son    = agg[sz[-1]]["gol"] + agg[sz[-1]]["asist"]
    onceki = agg[sz[-2]]["gol"] + agg[sz[-2]]["asist"]
    if son > onceki:
        return f"<span style='color:#22c55e;'>📈 {t('Yükselişte', 'Rising')}</span>"
    if son < onceki:
        return f"<span style='color:#ef4444;'>📉 {t('Düşüşte', 'Declining')}</span>"
    return f"<span style='color:#94a3b8;'>➡️ {t('Stabil', 'Stable')}</span>"


def kariyer_trend_goster(sezonlar):
    """Trend grafiği + form rozetini bir profil sayfasında render eder."""
    fig = _kariyer_trend_figuru(sezonlar)
    if fig is None:
        return
    rozet = _form_rozeti(sezonlar)
    st.markdown(f"#### 📈 {t('Kariyer Trendi', 'Career Trend')} &nbsp; {rozet}", unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", key=_pk("plt_1815"))


# ── Benzer oyuncu motoru ──
def _yas_hesapla(dob):
    import re
    from datetime import date
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", dob or "")
    if not m:
        return 0.0
    g, a, y = map(int, m.groups())
    try:
        return round((date.today() - date(y, a, g)).days / 365.25, 1)
    except Exception:
        return 0.0


def _boy_cm(boy):
    import re
    m = re.search(r"(\d)[,.](\d{2})", boy or "")
    return int(m.group(1)) * 100 + int(m.group(2)) if m else 0


def _poz_kategori(poz):
    p = (poz or "").lower()
    if "goalkeeper" in p or "kaleci" in p:
        return "Kaleci"
    if "defen" in p or "back" in p:
        return "Defans"
    if "midfield" in p:
        return "Orta Saha"
    if "strik" in p or "forward" in p or "wing" in p:
        return "Forvet"
    return "?"


def _deger_num(s) -> int:
    """'€80.000' → 80000 (Avrupa biçimi: noktalar binlik). Sayı yoksa 0."""
    d = _re.sub(r"[^\d]", "", str(s or ""))
    return int(d) if d else 0


@st.cache_data(ttl=3600)
def _benzer_havuz(kaynak):
    """kaynak: 'analig' | 'scouting' → feature listesi (pozisyon, yaş, fizik, kariyer +
    scouting'de scout_kadro: mevki kodu, rol, piyasa değeri)."""
    if kaynak == "analig":
        profiller = sd_profiller
        leistung  = analig_leistung_yukle()
        kadro     = {}
    else:
        profiller = scouting_sd_yukle()
        leistung  = scouting_leistung_yukle()
        kadro     = scout_kadro_yukle()
    havuz = []
    for isim, p in profiller.items():
        if not isinstance(p, dict) or p.get("bulunamadi"):
            continue
        sez = [s for s in leistung.get(isim, {}).get("sezonlar", []) if not s.get("milli")]
        mac = sum(s.get("mac", 0) for s in sez)
        if mac < 5:
            continue
        _kd = kadro.get(isim, {})
        _kl = _kd.get("kulup", "") or (sez[0].get("kulup", "") if sez else "")
        havuz.append({
            "isim":      isim,
            "kat":       _poz_kategori(p.get("Position", "")),
            "yas":       _yas_hesapla(p.get("Date of birth", "")),
            "boy":       _boy_cm(p.get("Height", "")),
            "ulke":      p.get("Nationality", ""),
            "kulup":     _kl,
            "mac":       mac,
            "gol":       sum(s.get("gol", 0) for s in sez),
            "asist":     sum(s.get("asist", 0) for s in sez),
            "gol_mac":   sum(s.get("gol", 0) for s in sez) / mac,
            "asist_mac": sum(s.get("asist", 0) for s in sez) / mac,
            "dk_mac":    sum(s.get("dakika", 0) for s in sez) / mac,
            # scout_kadro zenginleştirmesi (scouting; analig'de boş)
            "mevki_kod": ((_kd.get("mevki") or [""])[0] or "").upper(),
            "rol":       _kd.get("rol", ""),
            "deger":     _deger_num(_kd.get("deger", "")),
        })
    return havuz


def _benzer_oyuncular(hedef_isim, kaynak, k=5):
    havuz = _benzer_havuz(kaynak)
    q = next((o for o in havuz if o["isim"] == hedef_isim), None)
    if not q or q["kat"] == "?":
        return []
    grup  = [o for o in havuz if o["kat"] == q["kat"]]
    feats = ["yas", "boy", "mac", "gol_mac", "asist_mac", "dk_mac"]
    # Piyasa değeri verisi varsa benzer bütçe de bir sinyal (scouting)
    if any((o.get("deger") or 0) > 0 for o in grup):
        feats = feats + ["deger"]
    rng = {}
    for fe in feats:
        vals = [(o.get(fe) or 0) for o in grup if (o.get(fe) or 0) > 0]
        rng[fe] = (min(vals), max(vals)) if len(vals) >= 2 else None

    def skor(o):
        fark, n = 0.0, 0
        for fe in feats:
            if not rng[fe]:
                continue
            lo, hi = rng[fe]
            if hi == lo:
                continue
            fark += (((q.get(fe) or 0) - lo) / (hi - lo) - ((o.get(fe) or 0) - lo) / (hi - lo)) ** 2
            n += 1
        base = (1 - (fark / n) ** 0.5) * 100 if n else 0.0
        # Kategorik yakınlık: aynı detay mevki kodu + aynı rol (scout_kadro)
        bonus = 0
        if q.get("mevki_kod") and q["mevki_kod"] == o.get("mevki_kod"):
            bonus += 10
        if q.get("rol") and q["rol"] == o.get("rol"):
            bonus += 8
        return round(min(99.5, base + bonus), 1)

    adaylar = sorted(((skor(o), o) for o in grup if o["isim"] != hedef_isim),
                     reverse=True, key=lambda x: x[0])

    def _lbl(o):
        parc = [(f"{o['yas']:.0f} {t('yaş','yrs')}" if o.get("yas") else ""),
                _takim_kisa(o.get("kulup", "")),
                ulke_goster(_uyruk_goster(o.get("ulke", "")))]   # yaş · takım · memleket
        return " · ".join(x for x in parc if x)

    return [(o["isim"], s, _lbl(o)) for s, o in adaylar[:k]]


def _benzer_kutu_grid(items):
    """items: [(isim, skor, bilgi), …] → İLK öneri büyük (öne çıkan) kart, kalan 4'ü
    2x2 grid (mobilde) / yan yana (masaüstü). Benzer Oyuncular + Transfer Hedefleri ortak."""
    if not items:
        return
    _dil_q = st.session_state.get("dil", "TR")
    def _renk(s):
        return ("#34d399" if s >= 90 else "#facc15" if s >= 80
                else "#fb923c" if s >= 70 else "#a78bfa")
    def _esc(x):
        return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    def _kart(isim, skor, bilgi, buyuk=False):
        href = f"?oyuncu={_urlquote(isim)}&dil={_dil_q}"
        wrap = "display:block;" if buyuk else "flex:1 1 0;min-width:140px;"
        kls  = "benzer-kutu benzer-buyuk" if buyuk else "benzer-kutu"
        return (
            f"<a href='{href}' style='text-decoration:none;{wrap}'>"
            f"<div class='{kls}'>"
            f"<div class='bk-skor' style='color:{_renk(skor)};'>%{skor}</div>"
            f"<div class='bk-ad'>{_esc(isim)}</div>"
            f"<div class='bk-alt'>{_esc(bilgi)}</div>"
            f"</div></a>"
        )
    html = _kart(*items[0], buyuk=True)
    if items[1:]:
        kalan = "".join(_kart(*it) for it in items[1:])
        html += f"<div class='benzer-grid' style='margin-top:8px;'>{kalan}</div>"
    st.markdown(html, unsafe_allow_html=True)


def benzer_oyuncular_goster(hedef_isim, kaynak):
    sonuc = _benzer_oyuncular(hedef_isim, kaynak)
    if not sonuc:
        return
    st.markdown(f"#### 🔎 {t('Benzer Oyuncular', 'Similar Players')}")
    st.caption(t("Aynı mevki · yaş, boy, deneyim ve gol/asist oranlarına göre",
                 "Same position · based on age, height, experience and goal/assist ratios"))
    _benzer_kutu_grid(sonuc)


# ── Radar grafiği (mevki içi yüzdelik profil) ──
def radar_goster(isim, kaynak):
    havuz = _benzer_havuz(kaynak)
    q = next((o for o in havuz if o["isim"] == isim), None)
    if not q or q["kat"] == "?":
        return
    grup = [o for o in havuz if o["kat"] == q["kat"]]
    if len(grup) < 3:
        return
    eksenler = [(t("Gol/Maç","Goals/Match"), "gol_mac"), (t("Asist/Maç","Assists/Match"), "asist_mac"),
                (t("Dakika/Maç","Minutes/Match"), "dk_mac"), (t("Deneyim","Experience"), "mac")]
    r, theta = [], []
    for ad, fe in eksenler:
        # dk_mac için: sadece veri olan (>0) oyuncuları kullan; veri yoksa 0 percentile
        if fe == "dk_mac":
            vals = [o[fe] for o in grup if o[fe] > 0]
            if not vals or q[fe] == 0:
                r.append(0)
                theta.append(ad)
                continue
        else:
            vals = [o[fe] for o in grup]
        rank = sum(1 for v in vals if v <= q[fe])
        r.append(round(rank / len(vals) * 100) if vals else 0)
        theta.append(ad)
    fig = go.Figure(go.Scatterpolar(
        r=r + [r[0]], theta=theta + [theta[0]], fill="toself",
        line=dict(color="#6366f1"), fillcolor="rgba(99,102,241,0.30)"))
    fig.update_layout(
        height=320, paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=11), margin=dict(l=50, r=50, t=30, b=30),
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(range=[0, 100], gridcolor="#1e293b", tickfont=dict(size=9)),
                   angularaxis=dict(gridcolor="#334155")),
        showlegend=False)
    st.markdown(f"#### 🕸️ {q['kat']} {t('Profili', 'Profile')}")
    st.caption(t("Aynı mevkideki oyunculara göre yüzdelik dilim (100 = en iyi)",
                 "Percentile vs players in the same position (100 = best)"))
    st.plotly_chart(fig, width="stretch", key=_pk("plt_1966"))


# ── Çapraz transfer hedefi (ana lig oyuncusuna benzeyen scouting adayları) ──
def _benzer_skor(q, o, rng, feats):
    fark, n = 0.0, 0
    for fe in feats:
        if not rng[fe]:
            continue
        lo, hi = rng[fe]
        if hi == lo:
            continue
        fark += ((q[fe] - lo) / (hi - lo) - (o[fe] - lo) / (hi - lo)) ** 2
        n += 1
    return round((1 - (fark / n) ** 0.5) * 100, 1) if n else 0.0


def capraz_transfer_goster(hedef_isim, hedef_kaynak="analig", aday_kaynak="scouting"):
    h = _benzer_havuz(hedef_kaynak)
    a = _benzer_havuz(aday_kaynak)
    q = next((o for o in h if o["isim"] == hedef_isim), None)
    if not q or q["kat"] == "?":
        return
    grup = [o for o in a if o["kat"] == q["kat"]]
    if not grup:
        return
    feats = ["yas", "boy", "mac", "gol_mac", "asist_mac", "dk_mac"]
    rng = {}
    for fe in feats:
        vals = [o[fe] for o in grup if o[fe] > 0]
        if q[fe] > 0:
            vals = vals + [q[fe]]
        rng[fe] = (min(vals), max(vals)) if len(vals) >= 2 else None
    ad = sorted(((_benzer_skor(q, o, rng, feats), o) for o in grup),
                reverse=True, key=lambda x: x[0])
    if not ad:
        return
    st.markdown(f"#### 🌍 {t('Benzer Transfer Hedefleri', 'Similar Transfer Targets')}")
    st.caption(t("Scouting havuzundan bu oyuncuya en yakın yabancı adaylar",
                 "Closest foreign candidates to this player from the scouting pool"))
    def _lbl(o):
        parc = [(f"{o['yas']:.0f} {t('yaş','yrs')}" if o.get("yas") else ""),
                _takim_kisa(o.get("kulup", "")),
                ulke_goster(_uyruk_goster(o.get("ulke", "")))]   # yaş · takım · memleket
        return " · ".join(x for x in parc if x)
    _benzer_kutu_grid([(o["isim"], s, _lbl(o)) for s, o in ad[:5]])


# ── Shortlist Karşılaştırma (favori oyuncuları yan yana kıyasla) ──
def shortlist_karsilastirma_goster(isimler, sd_data, leistung_data):
    isimler = [i for i in isimler if i]
    if len(isimler) < 2:
        st.info(t("⚖️ Karşılaştırma için shortlist'inde en az 2 oyuncu olmalı.",
                  "⚖️ You need at least 2 players in your shortlist to compare."))
        return
    veri = []
    for isim in isimler:
        sd  = sd_data.get(isim, {})
        sez = [s for s in leistung_data.get(isim, {}).get("sezonlar", []) if not s.get("milli")]
        mac = sum(s.get("mac", 0) for s in sez)
        veri.append({
            "isim": isim, "sd": sd, "mac": mac,
            "gol":   sum(s.get("gol", 0) for s in sez),
            "asist": sum(s.get("asist", 0) for s in sez),
            "dakika":sum(s.get("dakika", 0) for s in sez),
            "gol_mac":   sum(s.get("gol", 0) for s in sez) / mac if mac else 0,
            "asist_mac": sum(s.get("asist", 0) for s in sez) / mac if mac else 0,
            "dk_mac":    sum(s.get("dakika", 0) for s in sez) / mac if mac else 0,
        })
    # Özet tablo
    rows = "".join(
        f"<tr>"
        f"<td style='padding:5px 8px;font-weight:600;color:#f1f5f9'>{v['isim']}</td>"
        f"<td style='padding:5px 8px'>{v['sd'].get('Position','—')}</td>"
        f"<td style='padding:5px 8px'>{ulke_goster(_uyruk_goster(v['sd'].get('Nationality',''))) or '—'}</td>"
        f"<td style='padding:5px 8px'>{v['sd'].get('Age','?')}</td>"
        f"<td style='padding:5px 8px;text-align:right'>{v['mac']}</td>"
        f"<td style='padding:5px 8px;text-align:right'>{v['gol']}</td>"
        f"<td style='padding:5px 8px;text-align:right'>{v['asist']}</td>"
        f"<td style='padding:5px 8px;text-align:right'>{v['dakika']}</td></tr>"
        for v in veri)
    st.markdown(f"""
<table style="width:100%;border-collapse:collapse;font-size:0.82rem;margin-bottom:14px;">
  <thead><tr style="color:#94a3b8;border-bottom:1px solid #334155;">
    <th style="text-align:left;padding:6px 8px;">{t("Oyuncu","Player")}</th>
    <th style="text-align:left;padding:6px 8px;">{t("Mevki","Position")}</th>
    <th style="text-align:left;padding:6px 8px;">{t("Ülke","Country")}</th>
    <th style="text-align:left;padding:6px 8px;">{t("Yaş","Age")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("Maç","M")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("Gol","G")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("Asist","A")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("Dk","Min")}</th>
  </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)
    # Radar overlay (shortlist içi göreceli normalize)
    eksenler = [(t("Gol/Maç","Goals/Match"), "gol_mac"), (t("Asist/Maç","Assists/Match"), "asist_mac"),
                (t("Dakika/Maç","Minutes/Match"), "dk_mac"), (t("Deneyim","Experience"), "mac")]
    maxv = {fe: (max((v[fe] for v in veri), default=1) or 1) for _, fe in eksenler}
    fig = go.Figure()
    renkler = ["#22c55e", "#3b82f6", "#f59e0b", "#e040fb", "#06b6d4", "#ef4444"]
    for idx, v in enumerate(veri):
        r = [round(v[fe] / maxv[fe] * 100) for _, fe in eksenler]
        theta = [ad for ad, _ in eksenler]
        fig.add_trace(go.Scatterpolar(
            r=r + [r[0]], theta=theta + [theta[0]], fill="toself", name=v["isim"],
            line=dict(color=renkler[idx % len(renkler)]), opacity=0.55))
    fig.update_layout(
        height=400, paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=11),
        margin=dict(l=50, r=50, t=20, b=40),
        legend=dict(orientation="h", y=-0.12),
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(range=[0, 100], gridcolor="#1e293b", tickfont=dict(size=9)),
                   angularaxis=dict(gridcolor="#334155")))
    st.caption(t("Radar: shortlist içindeki en yüksek değere göre oranlanmıştır (göreceli kıyas)",
                 "Radar: scaled to the highest value within the shortlist (relative comparison)"))
    st.plotly_chart(fig, width="stretch", key=_pk("capraz_radar"))


# ── Veri Kapsama Paneli (admin: eksik veri özeti) ──
def veri_kapsama_goster(sc_df, isim_col, sd_data, leistung_data):
    isimler = sc_df[isim_col].dropna().astype(str).tolist()
    toplam = len(isimler)
    if toplam == 0:
        st.info(t("Veri yok.", "No data."))
        return
    mevki_yok, dob_yok, kariyer_yok, sd_yok = [], [], [], []
    for isim in isimler:
        sd = sd_data.get(isim, {})
        if not sd or sd.get("bulunamadi"):
            sd_yok.append(isim)
            continue
        if not sd.get("Position"):
            mevki_yok.append(isim)
        if not sd.get("Date of birth"):
            dob_yok.append(isim)
        if not leistung_data.get(isim, {}).get("sezonlar"):
            kariyer_yok.append(isim)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(t("Toplam", "Total"), toplam)
    c2.metric(t("SD profili yok", "No SD profile"), len(sd_yok))
    c3.metric(t("Mevki eksik", "Missing position"), len(mevki_yok))
    c4.metric(t("Doğum tarihi eksik", "Missing birth date"), len(dob_yok))
    c5.metric(t("Kariyer eksik", "Missing career"), len(kariyer_yok))

    def _liste(baslik, lst):
        if lst:
            ozet = ", ".join(lst[:40]) + (f" … (+{len(lst)-40})" if len(lst) > 40 else "")
            st.markdown(f"**{baslik} ({len(lst)}):** <span style='color:#94a3b8;font-size:0.85rem;'>{ozet}</span>",
                        unsafe_allow_html=True)

    _liste(t("🔴 SD profili bulunamayan", "🔴 No SD profile found"), sd_yok)
    _liste(t("📌 Mevkii eksik", "📌 Missing position"), mevki_yok)
    _liste(t("🎂 Doğum tarihi eksik", "🎂 Missing birth date"), dob_yok)
    _liste(t("⚽ Kariyer verisi eksik", "⚽ Missing career data"), kariyer_yok)
    if not (sd_yok or mevki_yok or dob_yok or kariyer_yok):
        st.success(t("Tüm oyuncularda mevki, doğum tarihi ve kariyer verisi tam ✅",
                     "All players have complete position, birth date and career data ✅"))


# ── ORTAK PROFİL BİLEŞENLERİ (scouting + ana lig aynı görünsün diye) ──────────
# ── Mevki haritası: mini futbol sahası (Transfermarkt tarzı) ──────────────────
# Dikey saha (GK altta, ST üstte) viewBox 0 0 100 132.
_SAHA_KONUM = {
    "GK": (50, 120),
    "LB": (17, 101), "RB": (83, 101), "CB": (50, 104), "LCB": (37, 104), "RCB": (63, 104),
    "LWB": (14, 89), "RWB": (86, 89),
    "DM": (50, 87), "DMF": (50, 87),
    "LM": (18, 69), "RM": (82, 69), "CM": (50, 69),
    "LMF": (18, 69), "RMF": (82, 69), "CMF": (50, 69),
    "AM": (50, 52), "AMF": (50, 52),
    "LW": (19, 40), "RW": (81, 40), "LWF": (19, 40), "RWF": (81, 40),
    "SS": (50, 35), "2ST": (50, 35),
    "ST": (50, 18), "CF": (50, 18),
}
# Normalize TR mevki → standart kod (ana lig için)
_MEVKI_SAHA_KOD = {
    "Kaleci": "GK", "Sağ Bek": "RB", "Sol Bek": "LB", "Stoper": "CB", "Defans": "CB",
    "Savunmacı Orta Saha": "DM", "Merkez Orta Saha": "CM", "Orta Saha": "CM",
    "Hücumcu Orta Saha": "AM", "Sol Kanat": "LW", "Sağ Kanat": "RW",
    "Sol Kanat Forvet": "LW", "Sağ Kanat Forvet": "RW",
    "Santrafor": "ST", "İkinci Santrafor": "SS", "Forvet": "ST",
}

def _pozisyon_saha(kodlar) -> str:
    """Verilen mevki kodları için mini saha SVG'si (ilk kod = birincil, parlak)."""
    seen = []
    for k in (kodlar or []):
        k = (k or "").upper().strip()
        if k in _SAHA_KONUM and k not in seen:
            seen.append(k)
    if not seen:
        return ""
    nokta = ""
    for i, k in enumerate(seen):
        x, y = _SAHA_KONUM[k]
        if i == 0:
            fill, r, tcol = "#22c55e", 9, "#06281a"
        else:
            fill, r, tcol = "#15803d", 8, "#bbf7d0"
        nokta += (f"<circle cx='{x}' cy='{y}' r='{r}' fill='{fill}' stroke='#0a3d1f' stroke-width='0.8'/>"
                  f"<text x='{x}' y='{y+2.3}' text-anchor='middle' font-size='6.2' font-weight='800' "
                  f"fill='{tcol}' font-family='Sora,monospace'>{k}</text>")
    return (
        "<svg viewBox='0 0 100 132' width='100%' style='max-width:188px;display:block;margin:0 auto;'>"
        "<rect x='2' y='2' width='96' height='128' rx='5' fill='#0e2117' stroke='#2f6b4a' stroke-width='1'/>"
        "<line x1='2' y1='66' x2='98' y2='66' stroke='#2f6b4a' stroke-width='0.7'/>"
        "<circle cx='50' cy='66' r='11' fill='none' stroke='#2f6b4a' stroke-width='0.7'/>"
        "<circle cx='50' cy='66' r='1.2' fill='#2f6b4a'/>"
        "<rect x='28' y='2' width='44' height='15' fill='none' stroke='#2f6b4a' stroke-width='0.7'/>"
        "<rect x='40' y='2' width='20' height='6' fill='none' stroke='#2f6b4a' stroke-width='0.7'/>"
        "<rect x='28' y='115' width='44' height='15' fill='none' stroke='#2f6b4a' stroke-width='0.7'/>"
        "<rect x='40' y='124' width='20' height='6' fill='none' stroke='#2f6b4a' stroke-width='0.7'/>"
        f"{nokta}</svg>")


def _profil_baslik(isim, sd_url=""):
    """Büyük isim başlığı + sağda SoccerDonna linki."""
    _badge = (f'<a href="{sd_url}" target="_blank" style="font-size:0.78rem;'
              f'color:#60a5fa;text-decoration:none;">🔗 SoccerDonna</a>') if sd_url else ""
    st.markdown(
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        'gap:16px;flex-wrap:wrap;margin:2px 0 4px;">'
        f'<div class="sc-isim">{isim}</div>'
        f'<div style="padding-top:8px;">{_badge}</div></div>',
        unsafe_allow_html=True)


def _profil_kutulari(gruplar):
    """Gruplu bilgi kutuları (Kişisel · Futbolcu · Diğer …) yan yana, mobilde dikey.
    gruplar: [(başlık, [(etiket, değer), …]), …]. Boş değer/kutu gizlenir."""
    def _bk(baslik, satirlar):
        ic = "".join(
            f"<div class='bk-satir'><span>{_e}</span><b>{_v}</b></div>"
            for _e, _v in satirlar if str(_v).strip() not in ("", "—", "None"))
        return (f"<div class='bilgi-kutu'><div class='bk-baslik'>{baslik}</div>{ic}</div>"
                if ic else "")
    _html = "".join(_bk(b, s) for b, s in gruplar)
    st.markdown(f"<div class='bilgi-grid'>{_html}</div>", unsafe_allow_html=True)


def _kariyer_kulup_milli(isim, sezonlar, kaynak, milli_ad="", guncelleme=""):
    """Trend + Radar yan yana + Kulüp/Milli ayrı tablolar (iki profilde ortak)."""
    if not sezonlar:
        return
    _ct1, _ct2 = st.columns([1.3, 1], gap="medium")
    with _ct1:
        kariyer_trend_goster(sezonlar)
    with _ct2:
        radar_goster(isim, kaynak)
    _kulup_sez = [s for s in sezonlar if not s.get("milli")]
    _milli_sez = [s for s in sezonlar if s.get("milli")]
    if not milli_ad and _milli_sez:
        milli_ad = _ilk_uyruk(_milli_sez[0].get("kulup", ""))

    def _tbl(baslik, rows, takim_basligi, takim_deger):
        if not rows:
            return
        import collections as _col
        # Sezona göre grupla (ilk görülme sırası korunur)
        _gr = _col.OrderedDict()
        for _s in rows:
            _gr.setdefault(_s.get("sezon", ""), []).append(_s)
        _sh = ""
        for _sez, _grp in _gr.items():
            _tm = sum(x.get("mac", 0) for x in _grp);   _tg = sum(x.get("gol", 0) for x in _grp)
            _ta = sum(x.get("asist", 0) for x in _grp); _ts = sum(x.get("sari", 0) for x in _grp)
            _td = sum(x.get("dakika", 0) for x in _grp)
            _coklu = len(_grp) > 1
            _ana = max(_grp, key=lambda x: x.get("mac", 0))
            _yari = f"{len(_grp)} {t('yarışma','comp.')}" if _coklu else _grp[0].get("lig", "")
            # TOPLAM satırı — BEYAZ, kalın
            _sh += (
                "<tr style='color:#f8fafc;font-weight:700;border-top:1px solid #2c3550;'>"
                f"<td style='padding:6px 8px;'>{_sez}</td>"
                f"<td style='padding:6px 8px;'>{takim_deger(_ana)}</td>"
                f"<td style='padding:6px 8px;color:#93a4bd;font-weight:600;font-size:0.76rem;'>{_yari}</td>"
                f"<td style='padding:6px 8px;text-align:right;'>{_tm}</td>"
                f"<td style='padding:6px 8px;text-align:right;'>{_tg}</td>"
                f"<td style='padding:6px 8px;text-align:right;'>{_ta}</td>"
                f"<td style='padding:6px 8px;text-align:right;'>{_ts}</td>"
                f"<td style='padding:6px 8px;text-align:right;'>{_td}</td></tr>")
            # Kırılım satırları — GRİ (yalnız çoklu yarışmada)
            if _coklu:
                for x in _grp:
                    _sh += (
                        "<tr style='color:#64748b;font-size:0.79rem;'>"
                        "<td style='padding:2px 8px;'></td><td style='padding:2px 8px;'></td>"
                        f"<td style='padding:2px 8px 2px 18px;'>↳ {x.get('lig','')}</td>"
                        f"<td style='padding:2px 8px;text-align:right;'>{x.get('mac',0)}</td>"
                        f"<td style='padding:2px 8px;text-align:right;'>{x.get('gol',0)}</td>"
                        f"<td style='padding:2px 8px;text-align:right;'>{x.get('asist',0)}</td>"
                        f"<td style='padding:2px 8px;text-align:right;'>{x.get('sari',0)}</td>"
                        f"<td style='padding:2px 8px;text-align:right;'>{x.get('dakika',0)}</td></tr>")
        st.markdown(f"##### {baslik}")
        st.markdown(
            '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;margin-bottom:6px;">'
            '<thead><tr style="color:#94a3b8;border-bottom:1px solid #334155;">'
            f'<th style="text-align:left;padding:6px 8px;">{t("Sezon","Season")}</th>'
            f'<th style="text-align:left;padding:6px 8px;">{takim_basligi}</th>'
            f'<th style="text-align:left;padding:6px 8px;">{t("Lig","League")}</th>'
            f'<th style="text-align:right;padding:6px 8px;">{t("M","M")}</th>'
            f'<th style="text-align:right;padding:6px 8px;">{t("G","G")}</th>'
            f'<th style="text-align:right;padding:6px 8px;">{t("A","A")}</th>'
            '<th style="text-align:right;padding:6px 8px;">🟨</th>'
            f'<th style="text-align:right;padding:6px 8px;">{t("Dk","Min")}</th>'
            f'</tr></thead><tbody>{_sh}</tbody></table>',
            unsafe_allow_html=True)

    st.markdown(f"#### ⚽ {t('Kariyer Performansı', 'Career Performance')}")
    _tbl(f"🏟️ {t('Kulüp Kariyeri','Club Career')}", _kulup_sez,
         t("Kulüp", "Club"), lambda s: s.get("kulup", ""))
    _tbl(f"🏳️ {t('Milli Takım','National Team')}" + (f" — {milli_ad}" if milli_ad else ""),
         _milli_sez, t("Takım", "Team"),
         lambda s: milli_ad or _uyruk_goster(s.get("kulup", "")))
    if guncelleme:
        st.caption(f"📡 SoccerDonna · {guncelleme}")


def _kontrat_renk_g(sz):
    """'DD.MM.YYYY' → kalan aya göre renk (kırmızı<6ay / amber<12ay / yeşil)."""
    import datetime as _dt
    try:
        _g, _a, _y = (int(x) for x in str(sz).split(".")[:3])
        _ay = (_dt.date(_y, _a, _g) - _dt.date.today()).days / 30.0
        return "#f87171" if _ay < 6 else "#fbbf24" if _ay < 12 else "#34d399"
    except Exception:
        return "#cbd5e1"


def render_shortlist_kartlari(isimler, kullanici):
    """Shortlist oyuncularını W-Scope 'Favoriler' tarzı kartlarla göster + scout notu /
    durum / öncelik düzenleme (yorumlama + işlem)."""
    if not isimler:
        st.info(t("Shortlist'in boş. Oyuncu tablosundan aşağıdaki ⭐ ile ekleyebilirsin.",
                  "Your shortlist is empty. Add players with ⭐ below the table."))
        return
    sd_data = scouting_sd_yukle()
    _notlar = scoutnot_kullanici(kullanici)
    st.markdown(f"<div style='color:#71717a;font-size:0.8rem;margin:2px 0 10px;'>"
                f"⭐ {len(isimler)} {t('oyuncu takipte','players tracked')}</div>",
                unsafe_allow_html=True)

    def _kutu(lbl, val, clr="#e8eef7"):
        return (f"<div style='flex:1;background:#0f1626;border:1px solid #233149;border-radius:8px;"
                f"padding:8px 6px;text-align:center;'>"
                f"<div style='font-size:0.56rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;'>{lbl}</div>"
                f"<div style='font-size:0.95rem;font-weight:800;color:{clr};margin-top:2px;'>{val}</div></div>")

    for isim in isimler:
        _kd = scout_kadro_yukle().get(isim, {})
        sd  = sd_data.get(isim, {})
        _yas = _kd.get("yas") or sd.get("Age", "") or "—"
        _pos = (_kd.get("mevki") or [""])[0] or "—"
        _kl  = _kd.get("kulup", "") or ""
        _lg  = _kd.get("lig", "") or ""
        _dg  = _kd.get("deger", "") or "—"
        _sz  = _kd.get("sozlesme", "") or sd.get("Contract until", "") or "—"
        _nh  = _kd.get("nihai", "")
        _uy  = ulke_goster(_uyruk_goster(sd.get("Nationality", "") or _kd.get("vatandaslik", "")))
        _m   = _notlar.get(isim, {})
        _durum, _oncelik, _notu, _tarih = (_m.get("durum",""), _m.get("oncelik",""),
                                           _m.get("not",""), _m.get("tarih",""))
        _skor = (f"<span class='ws-ring' style='border-color:{_scotr_renk(_scotr_puan(_nh))};"
                 f"color:{_scotr_renk(_scotr_puan(_nh))};'>{_nh}</span>") if _nh else ""
        _dr = _DURUM_RENK.get(_durum, "#475569")
        _durum_b = (f"<span style='background:{_dr}22;border:1px solid {_dr};color:{_dr};"
                    f"border-radius:6px;padding:2px 9px;font-size:0.68rem;font-weight:700;'>"
                    f"{_DURUM_EN.get(_durum,_durum) if EN else _durum}</span>") if _durum else ""
        _onc_b = (f"<span style='color:#94a3b8;font-size:0.72rem;'>"
                  f"{_ONCELIK_EN.get(_oncelik,_oncelik) if EN else _oncelik}</span>") if _oncelik else ""
        _statlar = (_kutu(t("YAŞ","AGE"), _yas) + _kutu("POS", _pos) +
                    _kutu(t("DEĞER","VALUE"), _dg) + _kutu(t("KONTR.","CONTR."), _sz, _kontrat_renk_g(_sz)))
        _not_html = (f"<div style='margin-top:11px;border-left:3px solid #7c3aed;padding:2px 0 2px 11px;"
                     f"color:#aab4c4;font-size:0.84rem;line-height:1.55;'>📝 {_notu}</div>") if _notu else ""
        _alt = " · ".join(x for x in [_onc_b, _tarih] if x)
        st.markdown(
            f"<div style='background:#0d0d16;border:1px solid #2a2a38;border-radius:12px;padding:14px 16px;margin-bottom:10px;'>"
            f"<div style='display:flex;align-items:center;gap:12px;'>"
            f"<span class='ws-ava' style='width:38px;height:38px;font-size:1rem;'>{(isim[:1] or '?').upper()}</span>"
            f"<div style='flex:1;min-width:0;'><div style='font-size:1.05rem;font-weight:800;color:#f4f4f5;'>{isim}</div>"
            f"<div class='ws-sub' style='font-size:0.72rem;'>{' · '.join(x for x in [_uy,_kl,_lg] if x)}</div></div>"
            f"<div style='display:flex;align-items:center;gap:10px;'>{_durum_b}{_skor}</div></div>"
            f"<div style='display:flex;gap:6px;margin-top:12px;'>{_statlar}</div>"
            f"{_not_html}"
            + (f"<div style='margin-top:7px;font-size:0.66rem;color:#52525b;'>{_alt}</div>" if _alt else "")
            + "</div>", unsafe_allow_html=True)
        with st.expander(f"✏️ {t('Durum · Öncelik · Not','Status · Priority · Note')} — {isim}"):
            _e1, _e2 = st.columns(2)
            with _e1:
                _yd = st.selectbox(t("Durum","Status"), DURUM_OPSIYON,
                    index=DURUM_OPSIYON.index(_durum) if _durum in DURUM_OPSIYON else 0,
                    format_func=lambda x: _DURUM_EN.get(x,x) if EN else x, key=_pk(f"sl_d_{isim}"))
            with _e2:
                _yo = st.selectbox(t("Öncelik","Priority"), ONCELIK_OPSIYON,
                    index=ONCELIK_OPSIYON.index(_oncelik) if _oncelik in ONCELIK_OPSIYON else 0,
                    format_func=lambda x: _ONCELIK_EN.get(x,x) if EN else x, key=_pk(f"sl_o_{isim}"))
            _yn = st.text_area(t("Scout Notu","Scout Note"), value=_notu,
                               key=_pk(f"sl_n_{isim}"), height=80)
            _b1, _b2 = st.columns(2)
            with _b1:
                if st.button(f"💾 {t('Kaydet','Save')}", key=_pk(f"sl_sv_{isim}"), width="stretch"):
                    scoutnot_ayarla(kullanici, isim, _yd, _yo, _yn); st.rerun()
            with _b2:
                if st.button(f"★ {t('Shortlist’ten Çıkar','Remove')}", key=_pk(f"sl_rm_{isim}"), width="stretch"):
                    shortlist_toggle(kullanici, isim); st.rerun()


# -- Odakli scouting oyuncu profili: kart + tum kariyer performansi --
def render_scouting_detay(tam_isim):
    _PROFIL_CTX["n"] += 1   # her render benzersiz key bağlamı
    # Deneme modunda yalnızca vitrin oyuncuları açık
    if deneme_modunda() and tam_isim not in DENEME_SCOUT_OYUNCULAR:
        deneme_kilit(t("Bu oyuncunun scout profili", "This player's scout profile"), "scout")
        return
    sd_data = scouting_sd_yukle()
    leistung_data = scouting_leistung_yukle()
    detay_data = scouting_detay_yukle()
    sd = sd_data.get(tam_isim, {})
    dob      = sd.get("Date of birth", "—")
    yas      = sd.get("Age", "?")
    boy      = sd.get("Height", "—")
    mevki    = sd.get("Position", "—")
    ayak     = sd.get("Foot", "—")
    sozlesme = sd.get("Contract until", "—")
    vatandas = sd.get("Nationality", "—")
    sd_url   = sd.get("profil_url", "")
    sd_badge = (f'<a href="{sd_url}" target="_blank" style="font-size:0.78rem;'
                f'color:#60a5fa;text-decoration:none;">🔗 SoccerDonna</a>') if sd_url else ""

    # scout_kadro'dan ek bilgiler (piyasa değeri, milli takım)
    _kadro  = scout_kadro_yukle().get(tam_isim, {})
    _deger  = _kadro.get("deger", "")
    # Milli takım = "Vatandaşlık (Millî)" (vatandaslik). NOT: milli_takim alanı aslında
    # "2. Vatandaşlık" (ikinci pasaport) → milli takım için YANLIŞ (örn. Miray Cin Türkiye
    # oynar ama 2. vatandaşlığı Almanya). Çift uyruklularda doğru NT = Millî vatandaşlık.
    _milli  = _kadro.get("vatandaslik", "") or _ilk_uyruk(vatandas)
    _yas_g  = f"{yas}" if str(yas) not in ("", "?", "—") else ""

    # Büyük isim başlığı + gruplu bilgi kutuları (ana lig ile ORTAK bileşen)
    _profil_baslik(tam_isim, sd_url)
    # Tek tıkla shortlist'e al/çıkar (profili açınca anında, ismin hemen altında)
    _sl_kul = st.session_state.get("kulup_kullanici", "admin")
    _in_sl = tam_isim in shortlist_kullanici(_sl_kul)
    if st.button(
            ("⭐ " + t("Shortlist'te ✓ (çıkarmak için tıkla)", "In Shortlist ✓ (click to remove)"))
            if _in_sl else ("☆ " + t("Shortlist'e Ekle", "Add to Shortlist")),
            key=_pk(f"sc_sl_top_{tam_isim}"), width="stretch",
            type="secondary" if _in_sl else "primary"):
        shortlist_toggle(_sl_kul, tam_isim)
        st.rerun()
    # Mevki kodları: scout_kadro mevki[] (DMF/CMF…) ya da SD mevkisinden türet
    _saha_kod = list(_kadro.get("mevki") or [])
    if not _saha_kod:
        _trm = mevki_normalize(mevki) if mevki else ""
        if _trm in _MEVKI_SAHA_KOD:
            _saha_kod = [_MEVKI_SAHA_KOD[_trm]]
    _saha_svg = _pozisyon_saha(_saha_kod)
    _kutu_grp = [
        (f"👤 {t('Kişisel','Personal')}", [
            (f"🌍 {t('Uyruk','Nationality')}", ulke_goster(_uyruk_goster(vatandas))),
            (f"📅 {t('Doğum','Born')}", dob),
            (f"🎂 {t('Yaş','Age')}", _yas_g)]),
        (f"⚽ {t('Futbolcu','Player')}", [
            (f"📌 {t('Mevki','Position')}", mevki_disp(mevki)),
            (f"📏 {t('Boy','Height')}", boy),
            (f"🦶 {t('Ayak','Foot')}", ayak)]),
        (f"📋 {t('Diğer','Other')}", [
            (f"📄 {t('Sözleşme','Contract')}", sozlesme),
            (f"💰 {t('Piyasa Değeri','Market Value')}", _deger),
            (f"🏳️ {t('Milli Takım','National Team')}", ulke_goster(_milli))]),
    ]
    if _saha_svg:
        _bk_col, _sh_col = st.columns([2.6, 1], gap="medium")
        with _bk_col: _profil_kutulari(_kutu_grp)
        with _sh_col:
            st.markdown(f"<div style='text-align:center;font-size:0.6rem;color:#64748b;"
                        f"text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;'>"
                        f"📍 {t('Mevki Haritası','Position Map')}</div>{_saha_svg}",
                        unsafe_allow_html=True)
    else:
        _profil_kutulari(_kutu_grp)

    # Mr Daniş scouting değerlendirmesi (detay verisi varsa)
    _dty = detay_data.get(tam_isim, {})
    if _dty:
        _rol = _dty.get("rol", "")
        _mrd = _dty.get("mr_danis", "")
        _mrc = _MR_DANIS_RENK.get(_mrd, "#475569")
        _mevk = " · ".join(_dty.get("mevki_kod", []))
        _satirlar = ""
        for _et, _vl in [(f"🎭 {t('Rol','Role')}", rol_goster(_rol)),
                         (f"🧬 {t('Vücut Tipi','Body Type')}", vucut_goster(_dty.get("vucut_tipi", ""))),
                         (f"🗺️ {t('Bölge','Region')}", bolge_goster(_dty.get("bolge", ""))),
                         (f"📍 {t('Mevki Kodları','Position Codes')}", _mevk),
                         (f"🏳️ {t('Milli Takım','National Team')}", ulke_goster(_milli))]:
            if _vl:
                _satirlar += (f"<div><div style='color:#64748b;font-size:0.74rem;'>{_et}</div>"
                              f"<div style='color:#f1f5f9;font-weight:600;'>{_vl}</div></div>")
        _mrd_badge = (f"<span style='background:{_mrc}22;border:1px solid {_mrc};color:{_mrc};"
                      f"border-radius:6px;padding:3px 12px;font-weight:700;font-size:0.85rem;'>"
                      f"★ {danis_goster(_mrd)}</span>") if _mrd else ""
        st.markdown(f"""
<div style="border:1px solid #6366f1;border-radius:12px;padding:16px 20px;margin-bottom:16px;background:#0f172a;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
    <div style="color:#a5b4fc;font-weight:700;font-size:1.0rem;">🎯 {t("Scouting Değerlendirmesi","Scouting Assessment")}</div>
    {_mrd_badge}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px 18px;font-size:0.88rem;">{_satirlar}</div>
</div>""", unsafe_allow_html=True)

    _sezonlar = leistung_data.get(tam_isim, {}).get("sezonlar", [])
    if _sezonlar:
        _milli_ad = ulke_goster((_kadro.get("vatandaslik") or _ilk_uyruk(vatandas) or "").strip())
        _kariyer_kulup_milli(tam_isim, _sezonlar, "scouting", _milli_ad,
                             leistung_data.get(tam_isim, {}).get("guncelleme", ""))
    else:
        st.info(t("Bu oyuncu için detaylı kariyer verisi bulunamadı.", "No detailed career data found for this player."))

    # Zengin scout raporu (varsa — nitelik panelleri + PDF indir)
    render_scout_kadro_raporu(tam_isim)

    st.markdown("---")
    benzer_oyuncular_goster(tam_isim, "scouting")


# -- Odakli profil yonlendirici: ?oyuncu=X (ana lig veya scouting) --
def render_odakli_profil(isim):
    # Kaynak: scouting oyuncusu mu (ana lig kadrosunda değil ama SD havuzunda var)?
    _scout_oyuncu = (isim not in df_tam["Oyuncu"].values) and (isim in scouting_sd_yukle())
    _geri_lbl = (t("← Scouting'e Dön", "← Back to Scouting") if _scout_oyuncu
                 else t("← Listeye Dön", "← Back to List"))
    if st.button(_geri_lbl, key="odakli_geri", type="primary"):
        _dil_koru = st.query_params.get("dil", "")
        st.query_params.clear()
        if _dil_koru:
            st.query_params["dil"] = _dil_koru   # dil tercihini koru
        st.session_state["girildi"] = True       # karşılama ekranını atla
        if _scout_oyuncu:
            st.session_state["sayfa"] = "scouting"
        else:
            st.session_state["sayfa"] = "ana"
            # Ana akışa dönünce sol menüde Oyuncu Listesi sekmesi seçili gelsin
            st.session_state["tr_sekme"] = t("📋 Oyuncu Listesi", "📋 Player List")
        st.rerun()
    st.markdown("---")
    # Ana lig oyuncusu mu?
    if isim in df_tam["Oyuncu"].values:
        if not st.session_state.get("kulup_giris"):
            giris_gerekli_ekrani()
            return
        render_ana_lig_profil(isim)
        return
    # Scouting oyuncusu mu? (Premium kademe gerekir)
    if isim in scouting_sd_yukle():
        if not tier_yeterli("premium"):
            pro_paywall_goster(t("Scouting oyuncu profili", "Scouting player profile"),
                               tier="premium")
            return
        render_scouting_detay(isim)
        return
    st.warning(t(f"Oyuncu bulunamadı: {isim}", f"Player not found: {isim}"))


# ─── SCO TR SCOUT RAPORU (1207 Antalyaspor — FM tarzı nitelik paneli) ─────────
_SCOTR_HARF = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}

def _scotr_puan(nt: str) -> float:
    """'CD' → 2.5 (harf çifti ortalaması, A=5 … F=0)."""
    if not nt:
        return 0.0
    vals = [_SCOTR_HARF.get(c, 0) for c in nt.strip().upper() if c in _SCOTR_HARF]
    return sum(vals) / len(vals) if vals else 0.0

def _scotr_renk(puan: float) -> str:
    if puan >= 4.5: return "#10b981"   # A   — zümrüt
    if puan >= 3.5: return "#4ade80"   # B   — yeşil
    if puan >= 2.75: return "#fbbf24"  # C   — amber
    if puan >= 1.75: return "#fb923c"  # D   — turuncu
    if puan >= 0.75: return "#f87171"  # E   — kırmızı
    return "#6b7280"                   # F   — gri (veri yok)

_SCOTR_POT = {
    "⬆︎": ("⬆",  "#10b981", "Güçlü Yükseliş",  "Strong Rise"),
    "⬆":  ("⬆",  "#10b981", "Güçlü Yükseliş",  "Strong Rise"),
    "⇧":  ("⇧",  "#10b981", "Güçlü Yükseliş",  "Strong Rise"),
    "⬈":  ("⬈",  "#4ade80", "Yükselişte",       "Rising"),
    "⬌":  ("⬌",  "#fbbf24", "Stabil",           "Stable"),
    "⬋":  ("⬋",  "#fb923c", "Hafif Düşüş",      "Slight Decline"),
    "⬇︎": ("⬇",  "#f87171", "Düşüşte",          "Declining"),
    "⬇":  ("⬇",  "#f87171", "Düşüşte",          "Declining"),
}

# 10 kademeli skala: EE(1) → A+(10). FF = 0 dolu kutucuk.
_SCOTR_SIRA = ["EE", "DE", "DD", "CD", "CC", "BC", "BB", "AB", "AA", "A+"]

def _scotr_segman(nt: str) -> int:
    """Notu 0-10 arası dolu kutucuk sayısına çevirir (FF/boş → 0)."""
    nt = (nt or "").strip().upper()
    if nt in _SCOTR_SIRA:
        return _SCOTR_SIRA.index(nt) + 1
    # Ters yazım (ör. 'DC' → 'CD') veya bilinmeyen: puana göre yaklaşık
    p = _scotr_puan(nt)
    return max(0, min(10, round(p * 2 - 1))) if p > 0 else 0

# ─── Scout raporu TR→EN çevirileri (sabit kümeler; scout notu/isim orijinal) ──
_NITELIK_EN = {
    "Bitiricilik":"Finishing","Top Tekniği":"Technique","Penaltı Vuruşu":"Penalty Taking",
    "Markaj":"Marking","Top Kapma":"Tackling","Uzun Taç":"Long Throws","Duran Top":"Set Pieces",
    "İlk Kontrol":"First Touch","Kafa Vuruşu":"Heading","Orta Yapma":"Crossing","Kısa Pas":"Short Passing",
    "Uzun Pas":"Long Passing","Top Sürme":"Dribbling","Uzaktan Şut":"Long Shots",
    "Agresiflik":"Aggression","Cesaret":"Bravery","Karar Alma":"Decisions","Kararlılık":"Determination",
    "Konsantrasyon":"Concentration","Liderlik":"Leadership","Önsezi":"Anticipation","Konumlanma":"Positioning",
    "Soğukkanlılık":"Composure","Takım Oyunu":"Teamwork","Topsuz Alan":"Off the Ball","Görüş":"Vision",
    "Çeviklik":"Agility","Dayanıklılık":"Stamina","Denge":"Balance","Güç":"Strength","Sürat":"Pace",
    "Hızlanma":"Acceleration","Koordinasyon":"Coordination","Zindelik":"Fitness","Zıplama":"Jumping",
    "Zayıf Ayak":"Weak Foot","Sakatlanma Direnci":"Injury Resistance","Sportmenlik":"Sportsmanship",
    "Profesyonellik":"Professionalism","Sadakat":"Loyalty","Baskıya Dayanıklılık":"Pressure Handling",
    "Uyumluluk":"Adaptability","Süreklilik":"Consistency","Çalışkanlık":"Work Rate",
}
_ROL_EN = {
    "*Mezzala":"*Mezzala","*Raumdeuter":"*Raumdeuter","*Versatile":"*Versatile","*Volante":"*Volante",
    "Dengeli BK":"Balanced FB","Derinden Oyun Kurucu OS":"Deep-Lying Playmaker MF","Dinamo OS":"Box-to-Box MF",
    "Hedef KT":"Target Winger","Hedef ST":"Target Man","Hücumcu BK":"Attacking FB",
    "Hücumcu Oyun Kurucu":"Attacking Playmaker","Limitli SV":"Limited DF","Oyun Kurucu BK":"Playmaking FB",
    "Oyun Kurucu KT":"Playmaking Winger","Oyun Kurucu SV":"Ball-Playing DF","Pozisyoncu SV":"Positional DF",
    "Sahte #9 ST":"False 9","Savaşçı OS":"Ball-Winning MF","Savunmacı BK":"Defensive FB","Tilki ST":"Poacher",
    "Çakılı SV":"No-Nonsense CB","Çalışkan Hücum BK":"Hard-Working Att. FB","Çalışkan ST":"Pressing Forward",
    "Çapa OS":"Anchor MF","Çizgi KT":"Touchline Winger","İçe Kat Eden KT":"Inverted Winger",
}
_TARZ_EN = {
    "Alanına Hakimdir":"Commands the area","Ayakta Mücadele Eder":"Stays on feet in duels",
    "Aşırtma/Akıllı Vuruşlar Yapar":"Tries chips / clever finishes","Başarılıı Plase Şut/Orta Dener":"Tries placed shots / crosses",
    "Bireysel Oynamayı Sever":"Likes to dribble / go solo","Duran Toplarda Topun Başına Geçer":"Takes set pieces",
    "Fırsat Buldukça Hücuma Katılır":"Joins the attack when possible","Hücum Koşuları Yapar":"Makes attacking runs",
    "Kaleye Sırtı Dönük Oynayabilir":"Can play back to goal","Kaleyi Uzaktan Yoklar":"Tries long-range shots",
    "Kanattan Bindirme Yapar":"Overlaps on the wing","Karta Meyilli Hamle Yapmaz":"Avoids rash challenges",
    "Merkezden Bindirme Yapar":"Bursts through the middle","Rakip Oyunculara Sataşmaz":"Doesn't provoke opponents",
    "Sert Şutlar/Ortalar Dener":"Tries powerful shots / crosses","Sık Sık Ara/Kilit Pas Dener":"Often tries through / key passes",
    "Tekniği İle Top Saklamayı Sever":"Shields the ball with technique","Topla Oyalanmayı Sevmez":"Doesn't dwell on the ball",
    "Topu Almak İçin Gerilere Kadar Gelir":"Drops deep to get the ball","Tribüne Oynar, Abartılı Sevinir":"Plays to the crowd",
    "Yerden Uzak Köşeye Vuruş Yapar":"Aims for the far corner","Zayıf Ayağını Kullanabilir":"Can use weak foot",
    "İç Koridoru Kullanır":"Uses the inside channel",
}
_YETENEK_EN_DEG = {"Elit":"Elite","Yetenekli":"Talented","Potansiyelli":"High Potential",
                   "Gelişime Açık":"Developing","Sınırlı":"Limited"}
_IKTISADI_EN = {"Yüksek":"High","Orta":"Medium","Orta-Düşük":"Mid-Low","Düşük":"Low"}
_TR_GORUS_EN = {"İstekli":"Willing","Nötr":"Neutral","İsteksiz":"Reluctant"}

def _scout_ceviri(metin, sozluk):
    if not EN or not metin:
        return metin
    return sozluk.get(metin, metin)

def nitelik_goster(ad):     return _scout_ceviri(ad, _NITELIK_EN)
def scout_rol_goster(r):    return _scout_ceviri(r, _ROL_EN)
def tarz_goster(x):         return _scout_ceviri(_tarz_temiz(x), _TARZ_EN)
def yetenek_kume_goster(x): return _scout_ceviri(x, _YETENEK_EN_DEG)
def iktisadi_goster(x):     return _scout_ceviri(x, _IKTISADI_EN)
def tr_gorus_goster(x):
    if not EN or not x:
        return x
    base = x.replace(" (Şartlar?)", "").strip()
    return _TR_GORUS_EN.get(base, base) + (" (terms?)" if "(Şartlar?)" in x else "")


def _scotr_nitelik_paneli(baslik, ikon, nitelikler, makro_not):
    """Tek nitelik grubu paneli — kompakt: ad + 10 kutucuklu segment çizgisi."""
    m_puan = _scotr_puan(makro_not)
    m_renk = _scotr_renk(m_puan)
    makro_html = (f"<span style='background:{m_renk}22;color:{m_renk};"
                  f"border:1px solid {m_renk};border-radius:5px;padding:0 7px;"
                  f"font-size:0.64rem;font-weight:800;'>{makro_not}</span>") if makro_not else ""
    satirlar = ""
    for ad, nt in nitelikler.items():
        ad_g = nitelik_goster(ad)
        dolu = _scotr_segman(nt)
        renk = _scotr_renk(_scotr_puan(nt))
        kutular = ""
        for i in range(10):
            kc = renk if i < dolu else "#1a2035"
            kutular += (f"<span style='width:5px;height:9px;background:{kc};"
                        f"border-radius:1px;'></span>")
        satirlar += (
            f"<div style='display:flex;align-items:center;gap:6px;margin:3px 0;' "
            f"title='{ad_g}: {nt}'>"
            f"<span style='flex:1;min-width:0;font-size:0.63rem;color:#aab4c4;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{ad_g}</span>"
            f"<span style='display:inline-flex;gap:1.5px;flex:0 0 auto;'>{kutular}</span>"
            f"<span style='flex:0 0 20px;text-align:right;font-size:0.58rem;"
            f"font-weight:800;color:{renk};font-family:monospace;'>{nt}</span>"
            f"</div>"
        )
    return (
        f"<div style='background:#11162a;border:1px solid #232b47;border-radius:10px;"
        f"padding:10px 12px;height:100%;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"margin-bottom:7px;'>"
        f"<span style='font-size:0.68rem;font-weight:800;color:#e2e8f0;"
        f"letter-spacing:0.04em;white-space:nowrap;'>{ikon} {baslik}</span>{makro_html}</div>"
        f"{satirlar}</div>"
    )

def render_scout_raporu(isim: str):
    """Sco Tr scout raporunu (varsa) FM tarzı görsel panelle çizer."""
    rapor = scotr_yukle().get(isim)
    if not rapor:
        return

    st.markdown("---")

    # ── Başlık bandı: rol + nihai + ivme ────────────────────────────────
    nihai   = rapor.get("nihai", "")
    n_puan  = _scotr_puan(nihai)
    n_renk  = _scotr_renk(n_puan)
    pot     = (rapor.get("ivme") or rapor.get("potansiyel") or "").strip()
    pot_ok, pot_renk, pot_tr, pot_en = "", "#8899aa", "", ""
    for anahtar, (ok, renk, tr_ad, en_ad) in _SCOTR_POT.items():
        if pot == anahtar or (pot and pot.startswith(anahtar[0])):
            pot_ok, pot_renk, pot_tr, pot_en = ok, renk, tr_ad, en_ad
            break

    mevki_kod = " / ".join(x for x in [rapor.get("mevki1"), rapor.get("mevki2")] if x)
    alt_satir = " · ".join(x for x in [
        scout_rol_goster(rapor.get("rol", "")), mevki_kod, rapor.get("bolge", ""),
        rapor.get("uyruk", "")] if x)

    nihai_rozet = (
        f"<div style='text-align:center;'>"
        f"<div style='width:54px;height:54px;border-radius:50%;border:3px solid {n_renk};"
        f"display:flex;align-items:center;justify-content:center;font-size:1.05rem;"
        f"font-weight:900;color:{n_renk};background:{n_renk}15;font-family:monospace;'>"
        f"{nihai or '—'}</div>"
        f"<div style='font-size:0.56rem;color:#64748b;margin-top:3px;letter-spacing:0.1em;'>"
        f"{t('NİHAİ','RATING')}</div></div>"
    )
    pot_rozet = (
        f"<div style='text-align:center;'>"
        f"<div style='width:54px;height:54px;border-radius:50%;border:3px solid {pot_renk};"
        f"display:flex;align-items:center;justify-content:center;font-size:1.45rem;"
        f"font-weight:900;color:{pot_renk};background:{pot_renk}15;'>{pot_ok or '—'}</div>"
        f"<div style='font-size:0.56rem;color:#64748b;margin-top:3px;letter-spacing:0.1em;'>"
        f"{t('İVME','MOMENTUM')}</div></div>"
    ) if pot_ok else ""

    pot_satir = (
        f"<div style='font-size:0.70rem;color:{pot_renk};margin-top:5px;"
        f"font-weight:700;'>{pot_ok} {t(pot_tr, pot_en)}</div>"
    ) if pot_ok else ""

    # Tek parça (girintisiz, boş satırsız) — Streamlit markdown'ın HTML bloğunu
    # boşluk satırında kesip ham metne çevirmesini önler.
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#151a33,#1d1438);"
        f"border:1px solid #3b2d6e;border-radius:14px;padding:18px 22px;"
        f"margin-bottom:12px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"gap:14px;flex-wrap:wrap;'>"
        f"<div>"
        f"<div style='font-size:0.66rem;font-weight:800;color:#a78bfa;"
        f"letter-spacing:0.18em;margin-bottom:5px;'>🔬 "
        f"{t('SCOUT RAPORU','SCOUT REPORT')} · SCO TR</div>"
        f"<div style='font-size:1.05rem;font-weight:800;color:#f1f5f9;'>{isim}</div>"
        f"<div style='font-size:0.76rem;color:#8899bb;margin-top:3px;'>{alt_satir}</div>"
        f"{pot_satir}"
        f"</div>"
        f"<div style='display:flex;gap:14px;'>{nihai_rozet}{pot_rozet}</div>"
        f"</div></div>",
        unsafe_allow_html=True)

    if not rapor.get("degerlendirildi"):
        st.info(t("Bu oyuncu için detaylı nitelik değerlendirmesi henüz tamamlanmadı.",
                  "Detailed attribute assessment for this player is not yet complete."))
        return

    # ── 4 nitelik paneli (yan yana, kompakt) ────────────────────────────
    makro = rapor.get("makro", {})
    paneller = [
        (t("BECERİ", "TECHNICAL"), "⚽", rapor.get("beceri", {}), makro.get("beceri", "")),
        (t("BEŞERİ", "MENTAL"),    "🧠", rapor.get("beseri", {}), makro.get("beseri", "")),
        (t("FİZİKİ", "PHYSICAL"),  "💪", rapor.get("fiziki", {}), makro.get("fiziki", "")),
        (t("ŞAHSİ",  "PERSONAL"),  "🎖️", rapor.get("sahsi",  {}), makro.get("sahsi", "")),
    ]
    if rapor.get("kaleci"):   # KALECİ YETKİNLİKLERİ — yalnızca kaleciler
        paneller.append((t("KALECİ", "GOALKEEPING"), "🧤",
                         rapor.get("kaleci", {}), makro.get("kaleci", "")))
    kolonlar = st.columns(len(paneller), gap="small")
    for kol, (baslik, ikon, nit, mk) in zip(kolonlar, paneller):
        if nit:
            kol.markdown(_scotr_nitelik_paneli(baslik, ikon, nit, mk),
                         unsafe_allow_html=True)

    # ── Oyun tarzı çipleri (yalnızca işaretli özellikler) ───────────────
    tarz = rapor.get("tarz", [])
    if tarz:
        cipler = ""
        for oz in tarz:
            if isinstance(oz, dict):  # eski format uyumluluğu
                oz = oz.get("ozellik", "")
            cipler += (
                f"<span style='display:inline-block;background:#1e1b38;"
                f"border:1px solid #4c3d8f;color:#c4b5fd;border-radius:99px;"
                f"padding:4px 12px;margin:3px 4px 3px 0;font-size:0.70rem;'>"
                f"{tarz_goster(oz)}</span>"
            )
        st.markdown(
            f"<div style='margin-top:6px;'>"
            f"<div style='font-size:0.70rem;font-weight:800;color:#a78bfa;"
            f"letter-spacing:0.12em;margin-bottom:6px;'>🎭 {t('OYUN TARZI','PLAY STYLE')}</div>"
            f"{cipler}</div>", unsafe_allow_html=True)

    if rapor.get("scout_notu"):
        st.markdown(
            f"<div style='margin-top:10px;font-size:0.78rem;color:#94a3b8;"
            f"font-style:italic;border-left:3px solid #7c3aed;padding-left:10px;'>"
            f"📝 {rapor['scout_notu']}</div>", unsafe_allow_html=True)

    st.caption("📡 Mr Daniş · Sco Tr")


# ─── ZENGİN SCOUT KADRO RAPORU (scouting tarafı + PDF) ───────────────────────
def _tarz_temiz(oz: str) -> str:
    """Tarz etiketini saha oyuncusu için sadeleştirir ('A / B (Kaleci)' → 'A')."""
    return oz.split(" / ")[0].strip()

_YETENEK_RENK = {
    "Elit": "#10b981", "Yetenekli": "#4ade80", "Potansiyelli": "#fbbf24",
    "Gelişime Açık": "#fb923c", "Sınırlı": "#f87171",
}

@st.cache_data(show_spinner=False, max_entries=64)
def _scout_pdf_uret(isim: str, rapor: dict) -> bytes:
    """Scout raporunu tek sayfalık PDF olarak üretir (DejaVu — Türkçe destekli)."""
    from fpdf import FPDF
    _f = pathlib.Path(__file__).parent / "fonts"

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=14)
    pdf.add_font("DV", "", str(_f / "DejaVuSans.ttf"))
    pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    W = 210 - 24  # içerik genişliği (12mm kenar)

    MOR = (124, 58, 237); KOYU = (30, 27, 56); GRI = (110, 120, 140)
    BG = (17, 22, 42)

    def harf_puan(nt):
        h = {"A":5,"B":4,"C":3,"D":2,"E":1,"F":0}
        v = [h.get(c,0) for c in (nt or "").upper() if c in h]
        return sum(v)/len(v) if v else 0
    def renk(nt):
        p = harf_puan(nt)
        if p>=4.5: return (16,185,129)
        if p>=3.5: return (74,222,128)
        if p>=2.75: return (245,158,11)
        if p>=1.75: return (251,146,60)
        if p>=0.75: return (248,113,113)
        return (130,130,130)

    # ── Başlık bandı ──
    pdf.set_fill_color(*MOR); pdf.rect(0, 0, 210, 30, "F")
    pdf.set_xy(12, 6); pdf.set_text_color(255,255,255); pdf.set_font("DV","B",17)
    pdf.cell(0, 8, isim, ln=1)
    pdf.set_x(12); pdf.set_font("DV","",9)
    mevki = " / ".join(rapor.get("mevki", []))
    alt = " · ".join(x for x in [scout_rol_goster(rapor.get("rol","")), mevki, rapor.get("kulup","")] if x)
    pdf.cell(0, 6, alt, ln=1)
    pdf.set_xy(150, 7); pdf.set_font("DV","",7)
    pdf.cell(48, 4, t("SCOUT RAPORU","SCOUT REPORT"), ln=2, align="R")
    pdf.set_font("DV","B",9); pdf.cell(48, 5, "Mr Daniş · WFS", align="R")

    pdf.set_y(36); pdf.set_text_color(40,40,40)

    # ── Künye satırı ──
    pdf.set_font("DV","",9)
    kunye = [
        (t("Uyruk","Nationality"), rapor.get("vatandaslik","—")),
        (t("Doğum","Born"), f"{rapor.get('dogum','—')} ({rapor.get('yas','?')})"),
        (t("Boy/Ayak","Height/Foot"), f"{rapor.get('boy','—')} · {rapor.get('ayak','—')}"),
        (t("Lig","League"), rapor.get("lig","—")),
        (t("Sözleşme","Contract"), rapor.get("sozlesme","—")),
    ]
    for et, dg in kunye:
        pdf.set_text_color(*GRI); pdf.set_font("DV","",7.5)
        pdf.cell(W/5, 4, et.upper(), align="C")
    pdf.ln(4)
    for et, dg in kunye:
        pdf.set_text_color(30,30,30); pdf.set_font("DV","B",8.5)
        pdf.cell(W/5, 5, str(dg)[:22], align="C")
    pdf.ln(9)

    # ── NİHAİ / İVME / Yetenek / İktisadi / TR ──
    ozet = [
        (t("NİHAİ","RATING"), rapor.get("nihai") or "—", renk(rapor.get("nihai",""))),
        (t("İVME","MOMENTUM"), rapor.get("ivme") or "—", (124,58,237)),
        (t("YETENEK","TALENT"), yetenek_kume_goster(rapor.get("yetenek_kumesi")) or "—", (124,58,237)),
        (t("İKTİSADİ","ECONOMY"), iktisadi_goster(rapor.get("iktisadi_durum")) or "—", (110,120,140)),
        (t("TR GÖRÜŞÜ","TR VIEW"), tr_gorus_goster(rapor.get("tr_gorusu")) or "—", (110,120,140)),
    ]
    y_box = pdf.get_y(); bw = W/5
    for k, (et, dg, rk) in enumerate(ozet):
        x = 12 + k*bw
        pdf.set_fill_color(245,243,252); pdf.set_draw_color(220,214,235)
        pdf.rect(x, y_box, bw-2.5, 14, "DF")
        pdf.set_xy(x, y_box+2); pdf.set_text_color(*GRI); pdf.set_font("DV","",6)
        pdf.cell(bw-2.5, 3, et, align="C")
        dgs = str(dg)
        pdf.set_xy(x, y_box+6.5); pdf.set_text_color(*rk)
        pdf.set_font("DV","B", 10 if len(dgs) <= 8 else (8 if len(dgs) <= 12 else 6.5))
        pdf.cell(bw-2.5, 5, dgs[:18], align="C")
    pdf.set_y(y_box + 19)

    # ── Nitelik panelleri (2 kolon × 2 satır) ──
    kol_w = W/2 - 2
    SEG = {"EE":1,"DE":2,"DD":3,"CD":4,"CC":5,"BC":6,"BB":7,"AB":8,"AA":9,"A+":10}

    def panel_ciz(x, y, gbas, nit, mk):
        pdf.set_xy(x, y); pdf.set_text_color(*MOR); pdf.set_font("DV","B",8.5)
        pdf.cell(kol_w-12, 5, gbas)
        if mk:
            pdf.set_text_color(*renk(mk)); pdf.cell(12, 5, mk, align="R")
        yy = y + 6
        for ad, nt in nit.items():
            pdf.set_xy(x, yy); pdf.set_text_color(70,80,95); pdf.set_font("DV","",7)
            pdf.cell(kol_w*0.52, 3.6, nitelik_goster(ad)[:22])
            seg = SEG.get(nt, 0); bx = x + kol_w*0.55
            for i in range(10):
                pdf.set_fill_color(*(renk(nt) if i < seg else (225,228,235)))
                pdf.rect(bx + i*2.3, yy+0.6, 1.9, 2.6, "F")
            pdf.set_xy(x + kol_w - 8, yy); pdf.set_text_color(*renk(nt)); pdf.set_font("DV","B",6.5)
            pdf.cell(8, 3.6, nt, align="R")
            yy += 4.2
        return yy

    g = lambda k: (rapor.get(k, {}), rapor.get("makro", {}).get(k, ""))
    y_row = pdf.get_y()
    e1 = panel_ciz(12,        y_row, t("BECERİ","TECHNICAL"), *g("beceri"))
    e2 = panel_ciz(12+kol_w+4, y_row, t("BEŞERİ","MENTAL"), *g("beseri"))
    y_row = max(e1, e2) + 4
    e3 = panel_ciz(12,        y_row, t("FİZİKİ","PHYSICAL"), *g("fiziki"))
    e4 = panel_ciz(12+kol_w+4, y_row, t("ŞAHSİ","PERSONAL"),  *g("sahsi"))
    pdf.set_y(max(e3, e4) + 4)

    # ── Oyun tarzı ──
    tarz = [tarz_goster(o) for o in rapor.get("tarz", [])]
    if tarz:
        pdf.set_text_color(*MOR); pdf.set_font("DV","B",8.5); pdf.set_x(12)
        pdf.cell(0, 6, t("OYUN TARZI","PLAY STYLE"), ln=1)
        pdf.set_text_color(60,60,70); pdf.set_font("DV","",7.5); pdf.set_x(12)
        pdf.multi_cell(W, 4.2, "  •  ".join(tarz))
        pdf.ln(1)

    # ── Scout notu ──
    if rapor.get("scout_notu"):
        pdf.set_text_color(*MOR); pdf.set_font("DV","B",8.5); pdf.set_x(12)
        pdf.cell(0, 6, t("SCOUT DEĞERLENDİRMESİ","SCOUT ASSESSMENT"), ln=1)
        pdf.set_text_color(50,55,65); pdf.set_font("DV","",8); pdf.set_x(12)
        pdf.multi_cell(W, 4.6, rapor["scout_notu"])

    out = pdf.output()
    return bytes(out)


def render_scout_kadro_raporu(isim: str):
    """Zengin scout kadro raporunu (scouting tarafı) görsel panelle çizer + PDF."""
    rapor = scout_kadro_yukle().get(isim)
    if not rapor:
        return

    st.markdown("---")

    # Başlık bandı
    nihai = rapor.get("nihai",""); n_renk = _scotr_renk(_scotr_puan(nihai))
    pot = (rapor.get("ivme") or "").strip()
    pot_ok, pot_renk, pot_tr, pot_en = "", "#8899aa", "", ""
    for anahtar, (ok, renk, tr_ad, en_ad) in _SCOTR_POT.items():
        if pot == anahtar or (pot and pot.startswith(anahtar[0])):
            pot_ok, pot_renk, pot_tr, pot_en = ok, renk, tr_ad, en_ad
            break
    mevki_kod = " / ".join(rapor.get("mevki", []))
    alt_satir = " · ".join(x for x in [scout_rol_goster(rapor.get("rol","")), mevki_kod,
                f"{rapor.get('boy','')} · {rapor.get('ayak','')}".strip(" ·"),
                rapor.get("vatandaslik","")] if x)
    kulup_satir = " · ".join(x for x in [rapor.get("kulup",""), rapor.get("lig",""),
                  (f"💰 {rapor.get('deger')}" if rapor.get("deger") else ""),
                  (f"🗓 {rapor.get('sozlesme')}" if rapor.get("sozlesme") else "")] if x)

    nihai_rozet = (
        f"<div style='text-align:center;'>"
        f"<div style='width:54px;height:54px;border-radius:50%;border:3px solid {n_renk};"
        f"display:flex;align-items:center;justify-content:center;font-size:1.05rem;"
        f"font-weight:900;color:{n_renk};background:{n_renk}15;font-family:monospace;'>"
        f"{nihai or '—'}</div>"
        f"<div style='font-size:0.56rem;color:#64748b;margin-top:3px;letter-spacing:0.1em;'>"
        f"{t('NİHAİ','RATING')}</div></div>"
    )
    pot_rozet = (
        f"<div style='text-align:center;'>"
        f"<div style='width:54px;height:54px;border-radius:50%;border:3px solid {pot_renk};"
        f"display:flex;align-items:center;justify-content:center;font-size:1.45rem;"
        f"font-weight:900;color:{pot_renk};background:{pot_renk}15;'>{pot_ok or '—'}</div>"
        f"<div style='font-size:0.56rem;color:#64748b;margin-top:3px;letter-spacing:0.1em;'>"
        f"{t('İVME','MOMENTUM')}</div></div>"
    ) if pot_ok else ""

    st.markdown(
        f"<div style='background:linear-gradient(135deg,#151a33,#1d1438);"
        f"border:1px solid #3b2d6e;border-radius:14px;padding:18px 22px;margin-bottom:12px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"gap:14px;flex-wrap:wrap;'>"
        f"<div>"
        f"<div style='font-size:0.66rem;font-weight:800;color:#a78bfa;"
        f"letter-spacing:0.18em;margin-bottom:5px;'>🔬 {t('SCOUT RAPORU','SCOUT REPORT')}</div>"
        f"<div style='font-size:1.05rem;font-weight:800;color:#f1f5f9;'>{isim}</div>"
        f"<div style='font-size:0.76rem;color:#8899bb;margin-top:3px;'>{alt_satir}</div>"
        f"<div style='font-size:0.72rem;color:#6b7a99;margin-top:2px;'>{kulup_satir}</div>"
        f"</div>"
        f"<div style='display:flex;gap:14px;'>{nihai_rozet}{pot_rozet}</div>"
        f"</div></div>",
        unsafe_allow_html=True)

    # Etiket rozetleri: Yetenek Kümesi / İktisadi / TR Görüşü
    rozet = []
    if rapor.get("yetenek_kumesi"):
        rk = _YETENEK_RENK.get(rapor["yetenek_kumesi"], "#a78bfa")
        rozet.append((f"💎 {yetenek_kume_goster(rapor['yetenek_kumesi'])}", rk))
    if rapor.get("iktisadi_durum"):
        rozet.append((f"💰 {iktisadi_goster(rapor['iktisadi_durum'])}", "#64748b"))
    if rapor.get("tr_gorusu"):
        rozet.append((f"🇹🇷 {tr_gorus_goster(rapor['tr_gorusu'])}", "#64748b"))
    if rozet:
        cip = "".join(
            f"<span style='display:inline-block;background:{c}1f;border:1px solid {c}55;"
            f"color:{c};border-radius:6px;padding:3px 11px;margin:0 6px 6px 0;"
            f"font-size:0.74rem;font-weight:700;'>{m}</span>" for m, c in rozet)
        st.markdown(f"<div style='margin-bottom:8px;'>{cip}</div>", unsafe_allow_html=True)

    # 4 nitelik paneli (yan yana)
    makro = rapor.get("makro", {})
    paneller = [
        (t("BECERİ","TECHNICAL"), "⚽", rapor.get("beceri",{}), makro.get("beceri","")),
        (t("BEŞERİ","MENTAL"),    "🧠", rapor.get("beseri",{}), makro.get("beseri","")),
        (t("FİZİKİ","PHYSICAL"),  "💪", rapor.get("fiziki",{}), makro.get("fiziki","")),
        (t("ŞAHSİ","PERSONAL"),   "🎖️", rapor.get("sahsi",{}),  makro.get("sahsi","")),
    ]
    if rapor.get("kaleci"):   # KALECİ YETKİNLİKLERİ — yalnızca kaleciler
        paneller.append((t("KALECİ","GOALKEEPING"), "🧤",
                         rapor.get("kaleci",{}), makro.get("kaleci","")))
    for kol, (b, ik, nit, mk) in zip(st.columns(len(paneller), gap="small"), paneller):
        if nit:
            kol.markdown(_scotr_nitelik_paneli(b, ik, nit, mk), unsafe_allow_html=True)

    # Oyun tarzı (sadeleştirilmiş, ✔ işaretliler)
    tarz = [tarz_goster(o) for o in rapor.get("tarz", [])]
    if tarz:
        cipler = "".join(
            f"<span style='display:inline-block;background:#1e1b38;border:1px solid #4c3d8f;"
            f"color:#c4b5fd;border-radius:99px;padding:4px 12px;margin:3px 4px 3px 0;"
            f"font-size:0.70rem;'>{oz}</span>" for oz in tarz)
        st.markdown(
            f"<div style='margin-top:10px;'>"
            f"<div style='font-size:0.70rem;font-weight:800;color:#a78bfa;"
            f"letter-spacing:0.12em;margin-bottom:6px;'>🎭 {t('OYUN TARZI','PLAY STYLE')}</div>"
            f"{cipler}</div>", unsafe_allow_html=True)

    # Scout değerlendirmesi
    if rapor.get("scout_notu"):
        st.markdown(
            f"<div style='margin-top:12px;font-size:0.82rem;color:#aab4c4;line-height:1.6;"
            f"border-left:3px solid #7c3aed;padding:4px 0 4px 12px;'>"
            f"📝 {rapor['scout_notu']}</div>", unsafe_allow_html=True)

    # PDF indirme
    try:
        pdf_bytes = _scout_pdf_uret(isim, rapor)
        st.download_button(
            f"📄 {t('Scout Raporunu PDF indir','Download Scout Report PDF')}",
            data=pdf_bytes, file_name=f"scout_raporu_{isim.replace(' ','_')}.pdf",
            mime="application/pdf", width="stretch")
    except Exception as e:
        st.caption(f"⚠️ PDF oluşturulamadı: {e}")

    # Paylaşılabilir PUBLIC rapor linki (kulübe gönder — giriş gerektirmez)
    _purl = f"https://womenfootballscouting.com/?paylas={_urlquote(isim)}"
    with st.expander(f"🔗 {t('Paylaşılabilir Rapor Linki','Shareable Report Link')}"):
        st.caption(t("Bu linki kulübe gönder — alıcı GİRİŞ YAPMADAN markalı raporu görür (yalnız bu oyuncu).",
                     "Send this link to a club — they see the branded report WITHOUT login (this player only)."))
        st.code(_purl, language=None)
        _wa = "https://wa.me/?text=" + _urlquote(
            t(f"{isim} — scout raporu: ", f"{isim} — scout report: ") + _purl)
        st.markdown(
            f"<a href='{_wa}' target='_blank' style='display:inline-flex;align-items:center;gap:7px;"
            f"background:#25D366;color:#0b141a;font-weight:700;padding:8px 16px;border-radius:8px;"
            f"text-decoration:none;font-size:0.85rem;'>💬 {t('WhatsApp ile paylaş','Share on WhatsApp')}</a>",
            unsafe_allow_html=True)

    st.caption("📡 Mr Daniş · Women's Football Scouting")


# -- Ana lig oyuncu profili: tab2 ve odakli profil sayfasi kullanir --
_GRUP_EN = {"Kaleci": "Goalkeepers", "Defans": "Defenders",
            "Orta Saha": "Midfielders", "Forvet": "Forwards"}

def _pct_renk(p: int) -> str:
    """Percentile değerine göre bar rengi (üst dilim yeşil → alt dilim kırmızı)."""
    if p >= 75: return "#1db954"
    if p >= 50: return "#84cc16"
    if p >= 30: return "#f59e0b"
    return "#ef4444"

def _percentil_hesapla(secili: str):
    """Oyuncunun mevki grubu içindeki yüzdelik (percentile) sıralaması.
    Akran havuzu: aynı geniş mevki + anlamlı süre (kademeli eşik)."""
    if df_tam.empty or "Mevki" not in df_tam.columns:
        return None
    alt = df_tam[df_tam["Oyuncu"] == secili]
    if alt.empty:
        return None
    grup = _MEVKI_GRUP_MAP.get(alt.iloc[0].get("Mevki", ""))
    if not grup:
        return None
    d = df_tam.copy()
    d["_g"] = d["Mevki"].map(lambda m: _MEVKI_GRUP_MAP.get(m))
    grup_df = d[d["_g"] == grup]
    peers = grup_df[grup_df["Dakika"] >= 450]
    if len(peers) < 8:
        peers = grup_df[grup_df["Dakika"] >= 180]
    if len(peers) < 8:
        peers = grup_df
    if secili not in set(peers["Oyuncu"]):
        peers = pd.concat([peers, grup_df[grup_df["Oyuncu"] == secili]])
    peers = peers.drop_duplicates(subset=["Oyuncu"]).copy()
    peers["Gol/90"]  = peers.apply(lambda r: r["Gol"]/r["Dakika"]*90 if r["Dakika"] > 0 else 0, axis=1)
    peers["Sarı/90"] = peers.apply(lambda r: r["Sarı"]/r["Dakika"]*90 if r["Dakika"] > 0 else 0, axis=1)
    peers["İlk11%"]  = peers.apply(lambda r: r["İlk11"]/r["Maç"]*100 if r["Maç"] > 0 else 0, axis=1)
    if grup == "Kaleci":
        setler = [("Maç",    t("Maç", "Matches"),    0, False),
                  ("Dakika", t("Süre (dk)", "Minutes"), 0, False),
                  ("İlk11%", t("İlk 11 %", "Start %"),  0, False)]
    else:
        setler = [("Gol/90", t("Gol / 90 dk", "Goals / 90"), 2, False),
                  ("Gol",    t("Toplam Gol", "Total Goals"), 0, False),
                  ("Dakika", t("Süre (dk)", "Minutes"),      0, False),
                  ("İlk11%", t("İlk 11 %", "Start %"),       0, False),
                  ("Sarı/90", t("Sarı / 90 dk", "Yellow / 90"), 2, True)]
    out = []
    for col, etiket, ond, ters in setler:
        seri  = peers[col].astype(float)
        deger = float(peers[peers["Oyuncu"] == secili][col].iloc[0])
        pct   = round(((seri >= deger).mean() if ters else (seri <= deger).mean()) * 100)
        if ond == 2:            ds = f"{deger:.2f}"
        elif col == "İlk11%":   ds = f"{deger:.0f}%"
        else:                   ds = f"{int(round(deger))}"
        out.append((etiket, ds, int(pct)))
    return {"grup": grup, "n": len(peers), "metrikler": out}

def render_percentil_panel(secili: str):
    """Profilde mevki-içi percentile barlarını çizer."""
    veri = _percentil_hesapla(secili)
    if not veri:
        return
    grup = veri["grup"]
    grup_ad = grup if not EN else _GRUP_EN.get(grup, grup)
    basl = t(f"🎯 Mevki İçi Sıralama — {grup_ad}", f"🎯 Within-Position Ranking — {grup_ad}")
    alt  = t(f"{veri['n']} {grup_ad} oyuncu arasında yüzdelik (percentile) sıralama · 100% = en iyi",
             f"Percentile rank among {veri['n']} {grup_ad} · 100% = best")
    satirlar = ""
    for etiket, ds, pct in veri["metrikler"]:
        renk = _pct_renk(pct)
        satirlar += (
            "<div style='display:flex;align-items:center;gap:10px;margin:7px 0;'>"
            f"<span style='width:118px;font-size:0.78rem;color:#aeb8cc;flex:none;'>{etiket}</span>"
            f"<span style='width:48px;text-align:right;font-size:0.82rem;color:#e2e8f0;font-weight:700;flex:none;'>{ds}</span>"
            "<div style='flex:1;height:9px;background:#1a1f36;border-radius:5px;overflow:hidden;'>"
            f"<div style='width:{pct}%;height:100%;background:{renk};border-radius:5px;'></div></div>"
            f"<span style='width:40px;text-align:right;font-size:0.8rem;font-weight:800;color:{renk};flex:none;'>{pct}%</span>"
            "</div>")
    st.markdown(
        "<div style='background:#11162a;border:1px solid #232a40;border-radius:12px;"
        "padding:14px 18px;margin:6px 0 4px;'>"
        f"<div style='font-size:0.95rem;font-weight:700;color:#f1f5f9;'>{basl}</div>"
        f"<div style='font-size:0.72rem;color:#64748b;margin:2px 0 10px;'>{alt}</div>"
        f"{satirlar}</div>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, max_entries=64)
def _ana_lig_pdf_uret(secili: str, _en: bool = False) -> bytes:
    """TR lig oyuncusu için tek sayfalık markalı PDF (DejaVu — Türkçe destekli).
    Sezon istatistikleri + mevki-içi percentile barları.
    PERF: cache'li — aynı oyuncu için her rerun'da yeniden üretilmez."""
    from fpdf import FPDF
    _f = pathlib.Path(__file__).parent / "fonts"
    row = df_tam[df_tam["Oyuncu"] == secili].iloc[0]
    sd  = sd_profiller.get(secili, {})
    mac = int(row.get("Maç", 0)); gol = int(row.get("Gol", 0)); dk = int(row.get("Dakika", 0))
    ilk11 = int(row.get("İlk11", 0)); sari = int(row.get("Sarı", 0)); kir = int(row.get("Kırmızı", 0))
    gol_f = int(row.get("GolF", 0)); gol_h = int(row.get("GolH", 0)); pen = int(row.get("GolP", 0))
    ort = round(gol / mac, 2) if mac else 0
    ilk11_oran = round(ilk11 / mac * 100) if mac else 0
    yas = _MANUEL_YAS.get(secili)
    yas_s = (f"{yas:.0f}" if isinstance(yas, (int, float)) else
             (str(sd.get("Age", "")).split()[0] if sd.get("Age") else "—"))
    uyruk = _MANUEL_UYRUK.get(secili) or row.get("Uyruk", "—") or "—"
    mevki = row.get("Mevki", "—"); takim = row.get("Takım", "—")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=14)
    pdf.add_font("DV", "",  str(_f / "DejaVuSans.ttf"))
    pdf.add_font("DV", "B", str(_f / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    W = 210 - 24
    MOR = (124, 58, 237); GRI = (110, 120, 140)

    # Başlık bandı
    pdf.set_fill_color(*MOR); pdf.rect(0, 0, 210, 30, "F")
    pdf.set_xy(12, 6); pdf.set_text_color(255, 255, 255); pdf.set_font("DV", "B", 17)
    pdf.cell(0, 8, secili, ln=1)
    pdf.set_x(12); pdf.set_font("DV", "", 9)
    pdf.cell(0, 6, " · ".join(x for x in [mevki, takim] if x and x != "—"), ln=1)
    pdf.set_xy(150, 7); pdf.set_font("DV", "", 7)
    pdf.cell(48, 4, t("OYUNCU RAPORU", "PLAYER REPORT"), ln=2, align="R")
    pdf.set_font("DV", "B", 9); pdf.cell(48, 5, "WFS", align="R")
    pdf.set_y(37)

    # Künye
    kunye = [(t("Yaş", "Age"), yas_s), (t("Uyruk", "Nation"), uyruk),
             (t("Boy", "Height"), str(sd.get("Height", "—") or "—")),
             (t("Ayak", "Foot"), str((sd.get("Foot", "") or "—")).capitalize()),
             (t("Doğum", "Born"), str(sd.get("Date of birth", "—") or "—"))]
    for et, _ in kunye:
        pdf.set_text_color(*GRI); pdf.set_font("DV", "", 7.5); pdf.cell(W / 5, 4, et.upper(), align="C")
    pdf.ln(4)
    for _, dg in kunye:
        pdf.set_text_color(30, 30, 30); pdf.set_font("DV", "B", 8.5); pdf.cell(W / 5, 5, str(dg)[:22], align="C")
    pdf.ln(11)

    # Sezon istatistik kutuları (6'lı)
    pdf.set_text_color(*MOR); pdf.set_font("DV", "B", 10)
    pdf.cell(0, 6, t("2025-26 SEZON İSTATİSTİKLERİ", "2025-26 SEASON STATS"), ln=1)
    statlar = [(t("Maç", "Matches"), str(mac)), (t("İlk 11", "Starts"), f"{ilk11} (%{ilk11_oran})"),
               (t("Dakika", "Minutes"), str(dk)), (t("Gol", "Goals"), str(gol)),
               (t("Gol/Maç", "G/Match"), str(ort)),
               (t("Sarı/Kırmızı", "Yel/Red"), f"{sari} / {kir}")]
    y_box = pdf.get_y() + 1; bw = W / 6
    for k, (et, dg) in enumerate(statlar):
        x = 12 + k * bw
        pdf.set_fill_color(245, 243, 252); pdf.set_draw_color(220, 214, 235)
        pdf.rect(x, y_box, bw - 2, 15, "DF")
        pdf.set_xy(x, y_box + 2.5); pdf.set_text_color(*GRI); pdf.set_font("DV", "", 6)
        pdf.cell(bw - 2, 3, et, align="C")
        pdf.set_xy(x, y_box + 7); pdf.set_text_color(30, 30, 30)
        pdf.set_font("DV", "B", 11 if len(dg) <= 6 else 8)
        pdf.cell(bw - 2, 5, dg, align="C")
    pdf.set_y(y_box + 21)

    # Mevki içi percentile barları
    veri = _percentil_hesapla(secili)
    if veri:
        grup_ad = veri["grup"] if not EN else _GRUP_EN.get(veri["grup"], veri["grup"])
        pdf.set_text_color(*MOR); pdf.set_font("DV", "B", 10)
        pdf.cell(0, 6, t(f"MEVKİ İÇİ SIRALAMA — {grup_ad}", f"WITHIN-POSITION RANKING — {grup_ad}"), ln=1)
        pdf.set_text_color(*GRI); pdf.set_font("DV", "", 7)
        pdf.cell(0, 4, t(f"{veri['n']} {grup_ad} oyuncu arasında yüzdelik · 100% = en iyi",
                         f"Percentile among {veri['n']} {grup_ad} · 100% = best"), ln=1)
        pdf.ln(1)
        bar_x = 74; bar_w = 198 - bar_x - 16
        for etiket, ds, pct in veri["metrikler"]:
            y = pdf.get_y()
            pdf.set_xy(12, y); pdf.set_text_color(60, 70, 85); pdf.set_font("DV", "", 8)
            pdf.cell(46, 5, etiket[:24])
            pdf.set_text_color(30, 30, 30); pdf.set_font("DV", "B", 8); pdf.cell(14, 5, str(ds))
            p = int(pct)
            col = (16, 185, 129) if p >= 75 else (132, 197, 24) if p >= 50 else (245, 158, 11) if p >= 30 else (239, 68, 68)
            pdf.set_fill_color(232, 230, 240); pdf.rect(bar_x, y + 1, bar_w, 3.4, "F")
            pdf.set_fill_color(*col); pdf.rect(bar_x, y + 1, max(0.5, bar_w * p / 100), 3.4, "F")
            pdf.set_xy(bar_x + bar_w + 1, y); pdf.set_text_color(*col); pdf.set_font("DV", "B", 8)
            pdf.cell(14, 5, f"%{p}", align="R")
            pdf.ln(6)

    # Footer
    pdf.set_y(-16); pdf.set_text_color(*GRI); pdf.set_font("DV", "", 7)
    pdf.cell(0, 5, "Women's Football Scouting · " + t("Kaynak: TFF & SoccerDonna · Bilgi amaçlıdır",
                                    "Source: TFF & SoccerDonna · For information only"), align="C")
    out = pdf.output()
    return bytes(out)


def render_ana_lig_profil(secili):
    _PROFIL_CTX["n"] += 1   # her render benzersiz key bağlamı
    # Deneme modunda yalnızca vitrin oyuncuları açık
    if deneme_modunda() and secili not in DENEME_TR_OYUNCULAR:
        deneme_kilit(t("Bu oyuncunun detaylı profili", "This player's detailed profile"), "tr")
        return
    if secili and secili in oyuncu_detay:
        row    = df_tam[df_tam["Oyuncu"] == secili].iloc[0]
        detay  = oyuncu_detay[secili]
        mac    = int(row["Maç"])
        gol    = int(row["Gol"])
        gol_f  = int(row.get("GolF", 0))
        gol_h  = int(row.get("GolH", 0))
        pen    = int(row.get("GolP", 0))
        sari   = int(row["Sarı"])
        kir    = int(row["Kırmızı"])
        dk     = int(row["Dakika"])
        ilk11  = int(row["İlk11"])
        yedek  = int(row["Yedek"])
        ort    = round(gol/mac, 2) if mac else 0
        dk_mac = round(dk/mac)     if mac else 0
        ilk11_oran = round(ilk11/mac*100) if mac else 0
        transfer = bool(row.get("Transfer", False))
        # Gol tipi özeti metni
        gol_detay_parcalar = []
        if gol_f: gol_detay_parcalar.append(f"{gol_f}F")
        if gol_h: gol_detay_parcalar.append(f"{gol_h}H")
        if pen:   gol_detay_parcalar.append(f"{pen}P")
        gol_detay = f" ({' · '.join(gol_detay_parcalar)})" if gol_detay_parcalar else ""

        # Paylaşılabilir link — gerçek tam URL'yi panoya kopyalar (clipboard + fallback)
        import streamlit.components.v1 as _comp
        import json as _json_lnk
        _isim_js = _json_lnk.dumps(secili)
        _lbl_kop = t("Kopyala", "Copy"); _lbl_ok = t("Kopyalandı ✓", "Copied ✓")
        _lbl_bas = t("🔗 Paylaşılabilir link", "🔗 Share link")
        _kopya_html = (
            '<div style="font-family:Inter,sans-serif;">'
            '<div style="font-size:12px;color:#9aa6ba;font-weight:700;margin-bottom:5px;">' + _lbl_bas + '</div>'
            '<div style="display:flex;gap:6px;">'
            '<input id="lnk" readonly style="flex:1;min-width:0;background:#0f1117;color:#cbd5e1;'
            'border:1px solid #2a3146;border-radius:6px;padding:7px 10px;font-size:12px;"/>'
            '<button id="cpy" style="background:linear-gradient(135deg,#7c3aed,#db2777);color:#fff;'
            'border:none;border-radius:6px;padding:7px 16px;font-size:12px;font-weight:700;'
            'cursor:pointer;white-space:nowrap;">📋 ' + _lbl_kop + '</button></div></div>'
            '<script>'
            'var loc=window.parent.location;'
            'var url=loc.origin+loc.pathname+"?oyuncu="+encodeURIComponent(' + _isim_js + ');'
            'var inp=document.getElementById("lnk");inp.value=url;'
            'var btn=document.getElementById("cpy");'
            'btn.onclick=function(){inp.focus();inp.select();inp.setSelectionRange(0,99999);'
            'var ok=function(){btn.textContent="' + _lbl_ok + '";'
            'setTimeout(function(){btn.textContent="📋 ' + _lbl_kop + '";},1800);};'
            'if(navigator.clipboard&&window.isSecureContext){'
            'navigator.clipboard.writeText(url).then(ok).catch(function(){'
            'try{document.execCommand("copy");}catch(e){}ok();});}'
            'else{try{document.execCommand("copy");}catch(e){}ok();}};'
            '</script>'
        )
        _comp.html(_kopya_html, height=74)

        takim_html = (
            f'<span style="color:#a0aab4">{row["TümTakımlar"]}</span>'
            f'<span class="transfer-badge">🔄 Transfer</span>'
            if transfer else
            f'<span style="color:#1db954">{row["Takım"]}</span>'
        )

        # SoccerDonna profil verisi
        sd = sd_profiller.get(secili, {})

        # Mevki emoji
        MEVKİ_İKON = {
            "Goalkeeper": "🧤", "Defender": "🛡️", "Midfield": "⚙️",
            "Striker": "⚽", "Forward": "⚽", "Back": "🛡️",
        }
        sd_mevki = sd.get("Position", "")
        mevki_ikon = next((v for k, v in MEVKİ_İKON.items() if k in sd_mevki), "")

        # SoccerDonna bilgi satırı
        sd_parcalar = []
        if sd.get("Date of birth"): sd_parcalar.append(f"🎂 {sd['Date of birth']}")
        if sd.get("Place of birth"): sd_parcalar.append(f"📍 {sd['Place of birth']}")
        if sd.get("Nationality"):   sd_parcalar.append(f"🏳️ {sd['Nationality']}")
        if sd.get("Height"):        sd_parcalar.append(f"📏 {sd['Height']} m")
        if sd.get("Foot"):          sd_parcalar.append(f"👟 {sd['Foot'].capitalize()}")
        if sd.get("Market value") and sd["Market value"] not in ("unknown","?",""):
            sd_parcalar.append(f"💰 {sd['Market value']}")
        sd_bilgi_html = ""
        if sd_parcalar:
            sd_bilgi_html = (
                '<div style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 14px 0">'
                + "".join(
                    f'<span style="background:#0f1117;border-radius:6px;padding:4px 10px;'
                    f'font-size:0.8rem;color:#c0ccd8">{p}</span>'
                    for p in sd_parcalar
                )
                + "</div>"
            )

        mevki_html = ""
        if sd_mevki:
            mevki_html = (
                f'<div style="margin:6px 0 12px 0">'
                f'<span style="background:#0d3b2e;color:#1db954;border-radius:6px;'
                f'padding:4px 12px;font-size:0.82rem;font-weight:600">'
                f'{mevki_ikon} {sd_mevki}</span></div>'
            )

        # Başlık + gruplu bilgi kutuları (Scouting profili ile ORTAK görünüm)
        _profil_baslik(secili, sd.get("profil_url", ""))
        _mv = sd.get("Market value", "")
        _kutu_grp = [
            (f"👤 {t('Kişisel','Personal')}", [
                (f"🌍 {t('Uyruk','Nationality')}", ulke_goster(_uyruk_goster(sd.get("Nationality","")))),
                (f"📅 {t('Doğum','Born')}", sd.get("Date of birth","")),
                (f"🎂 {t('Yaş','Age')}", (_yas_hesapla(sd.get("Date of birth","")) or sd.get("Age","")))]),
            (f"⚽ {t('Futbolcu','Player')}", [
                (f"📌 {t('Mevki','Position')}", mevki_disp(sd.get("Position",""))),
                (f"📏 {t('Boy','Height')}", sd.get("Height","")),
                (f"🦶 {t('Ayak','Foot')}", (sd.get("Foot","") or "").capitalize())]),
            (f"📋 {t('Diğer','Other')}", [
                (f"🏟️ {t('Takım','Club')}", _takim_kisa(row["TümTakımlar"] if transfer else row["Takım"])),
                (f"💰 {t('Piyasa Değeri','Market Value')}", _mv if _mv not in ("unknown","?","") else ""),
                (f"📍 {t('Doğum Yeri','Birthplace')}", sd.get("Place of birth",""))]),
        ]
        _ana_kod = _MEVKI_SAHA_KOD.get(row.get("Mevki", ""))
        _saha_svg = _pozisyon_saha([_ana_kod] if _ana_kod else [])
        if _saha_svg:
            _bk_col, _sh_col = st.columns([2.6, 1], gap="medium")
            with _bk_col: _profil_kutulari(_kutu_grp)
            with _sh_col:
                st.markdown(f"<div style='text-align:center;font-size:0.6rem;color:#64748b;"
                            f"text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;'>"
                            f"📍 {t('Mevki Haritası','Position Map')}</div>{_saha_svg}",
                            unsafe_allow_html=True)
        else:
            _profil_kutulari(_kutu_grp)
        # Sezon İstatistikleri + Mevki İçi Sıralama (percentile) — YAN YANA (kompakt)
        _stat_html = f"""
        <div class="profil-kart" style="padding:14px 16px;">
          <div style="font-size:0.95rem;font-weight:700;color:#f1f5f9;">📊 {t('Sezon İstatistikleri','Season Stats')}</div>
          <div class="profil-stat" style="margin-top:8px;">
            <div class="profil-stat-item"><div class="deger">{mac}</div><div class="ad">{t("Maç","Matches")}</div></div>
            <div class="profil-stat-item"><div class="deger">{ilk11}</div><div class="ad">▶ {t("İlk 11","Starting 11")}</div></div>
            <div class="profil-stat-item"><div class="deger">{ilk11_oran}%</div><div class="ad">Starter %</div></div>
            <div class="profil-stat-item"><div class="deger">{dk}</div><div class="ad">{t("Top. Dakika","Tot. Minutes")}</div></div>
            <div class="profil-stat-item"><div class="deger">{int(dk_mac)}</div><div class="ad">{t("Dk/Maç","Min/Match")}</div></div>
            <div class="profil-stat-item"><div class="deger">{gol}</div><div class="ad">{t("Gol","Goals")}{gol_detay}</div></div>
            <div class="profil-stat-item"><div class="deger">{gol_f}</div><div class="ad">⚽ {t("Ayak (F)","Foot (F)")}</div></div>
            <div class="profil-stat-item"><div class="deger">{gol_h}</div><div class="ad">🆕 {t("Kafa (H)","Header (H)")}</div></div>
            <div class="profil-stat-item"><div class="deger">{pen}</div><div class="ad">{t("Penaltı (P)","Penalty (P)")}</div></div>
            <div class="profil-stat-item"><div class="deger">{ort}</div><div class="ad">{t("Gol/Maç","Goals/Match")}</div></div>
            <div class="profil-stat-item"><div class="deger" style="color:#f5c518">{sari}</div><div class="ad">🟨 {t("Sarı","Yellow")}</div></div>
            <div class="profil-stat-item"><div class="deger" style="color:#e53935">{kir}</div><div class="ad">🟥 {t("Kırmızı","Red")}</div></div>
          </div>
        </div>"""
        if _percentil_hesapla(secili):
            _c1, _c2 = st.columns(2, gap="medium")
            with _c1:
                st.markdown(_stat_html, unsafe_allow_html=True)
            with _c2:
                render_percentil_panel(secili)
        else:
            st.markdown(_stat_html, unsafe_allow_html=True)

        # ── Markalı PDF rapor indir ──────────────────────────────────────────
        try:
            _pdf = _ana_lig_pdf_uret(secili, EN)
            st.download_button(
                f"📄 {t('Oyuncu Raporunu PDF indir', 'Download Player Report PDF')}",
                data=_pdf, file_name=f"oyuncu_raporu_{secili.replace(' ', '_')}.pdf",
                mime="application/pdf", width="stretch", key=_pk("pdf_indir"))
        except Exception as _e:
            st.caption(f"⚠️ PDF oluşturulamadı: {_e}")

        st.markdown("<br>", unsafe_allow_html=True)
        p1, p2 = st.columns(2)

        # ── Son 5 maç formu (her maçta Süre · Gol · CleanSheet · Kart) ────────
        with p1:
            st.markdown(f"##### {t('Son 5 Maç Formu', 'Last 5 Matches Form')}")
            _mg = {m["hafta"]: m for m in detay.get("mac_gecmisi", [])}
            _htk = _oyuncu_hafta_takim(detay)   # transfer: o hafta hangi kulüpte
            _son_kulup = _htk[max(_htk)] if _htk else row["Takım"]  # sezon-sonu = son kulüp
            _son_h = _son_lig_haftasi() or (max(_mg) if _mg else 0)
            _haftalar = [h for h in range(max(1, _son_h - 4), _son_h + 1)]
            if not _haftalar:
                st.caption(t("Maç verisi yok.", "No match data."))
            else:
                _kartlar = ""
                for _h in _haftalar:
                    m = _mg.get(_h, {})
                    _dk = int(m.get("dakika", 0) or 0)
                    _gl = int(m.get("gol", 0) or 0)
                    _sa = int(m.get("sari", 0) or 0)
                    _kr = int(m.get("kirmizi", 0) or 0)
                    _sure_renk = "#4ade80" if _dk > 0 else "#475569"
                    # Clean sheet: oyuncunun O HAFTAKİ takımı (transferse doğru kulüp) gol yedi mi?
                    _yen = _hafta_yenilen(_htk.get(_h) or _son_kulup, _h)
                    if _yen is None:
                        _cs = "<span style='color:#475569;'>🛡️ —</span>"
                    elif _yen == 0:
                        _cs = "<span style='color:#34d399;'>🛡️ ✓</span>"
                    else:
                        _cs = f"<span style='color:#fb7185;'>🥅 {_yen}</span>"
                    _gl_html = (f"<span style='color:#86efac;'>⚽ {_gl}</span>" if _gl
                                else "<span style='color:#64748b;'>⚽ 0</span>")
                    _kart_html = (f"🟨{_sa}" + (f" 🟥{_kr}" if _kr else ""))
                    _kart_renk = "#fbbf24" if (_sa or _kr) else "#64748b"
                    _kartlar += (
                        "<div style='flex:1;min-width:90px;background:#0f1117;border:1px solid #232842;"
                        "border-radius:9px;padding:8px 6px;text-align:center;'>"
                        f"<div style='font-size:0.6rem;color:#64748b;font-weight:700;letter-spacing:0.03em;'>{_h}. {t('Hafta','Wk')}</div>"
                        f"<div style='font-size:1.05rem;font-weight:800;color:{_sure_renk};line-height:1.2;'>{_dk}′</div>"
                        f"<div style='font-size:0.7rem;margin-top:4px;'>{_gl_html}</div>"
                        f"<div style='font-size:0.7rem;margin-top:2px;'>{_cs}</div>"
                        f"<div style='font-size:0.7rem;margin-top:2px;color:{_kart_renk};'>{_kart_html}</div>"
                        "</div>")
                st.markdown(f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>{_kartlar}</div>",
                            unsafe_allow_html=True)
                # Açıklama metni kutuların ALTINA (kutular Lig Sıralaması ile aynı hizada başlasın)
                st.caption(t("Her maç: Süre · Gol · Clean Sheet · Kart (oynamadıysa 0′)",
                             "Each match: Minutes · Goals · Clean Sheet · Cards (0′ if didn't play)"))

        # ── Lig sıralamaları ─────────────────────────────────────────────────
        with p2:
            st.markdown(f"##### {t('Lig Sıralaması', 'League Ranking')}")
            r1, r2 = st.columns(2)
            for kol, metrik, etiket in [
                (r1, "Gol",    t("Gol","Goals")),
                (r2, "Dakika", t("Dakika","Minutes")),
            ]:
                s_df = df_tam.sort_values(metrik, ascending=False).reset_index(drop=True)
                s_df.index += 1
                idx = s_df[s_df["Oyuncu"] == secili].index
                sira = int(idx[0]) if len(idx) else "—"
                kol.metric(etiket, f"{sira}. / {len(df_tam)}")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Haftalık performans + gol zamanı ─────────────────────────────────
        gecmis_tam = sorted(detay.get("mac_gecmisi",[]), key=lambda x: x["hafta"])

        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f"##### {t('Haftalık Performans', 'Weekly Performance')}")
            if gecmis_tam:
                haftalar  = [m["hafta"]  for m in gecmis_tam]
                dakikalar = [m["dakika"] for m in gecmis_tam]
                goller    = [m["gol"]    for m in gecmis_tam]
                fig = go.Figure()
                fig.add_trace(go.Bar(x=haftalar, y=dakikalar, name=t("Dakika", "Minutes"),
                    marker_color="#2979ff", opacity=0.70,
                    hovertemplate=f"{t('Hafta','Week')} %{{x}}<br>%{{y}} {t('dk','min')}<extra></extra>"))
                # Goller: İKİNCİL eksende (gerçek sayı 0,1,2,3…) yıldız + üstünde RAKAM —
                # böylece kaç gol atıldığı net görünür. Sadece gol olan haftalarda işaret.
                _gh = [h for h, g in zip(haftalar, goller) if g > 0]
                _gg = [g for g in goller if g > 0]
                if _gh:
                    fig.add_trace(go.Scatter(x=_gh, y=_gg, name=t("Gol", "Goals"),
                        mode="markers+text", yaxis="y2",
                        marker=dict(color="#22c55e", size=18, symbol="star",
                                    line=dict(color="#0a3d1f", width=1)),
                        text=[str(g) for g in _gg], textposition="top center",
                        textfont=dict(color="#4ade80", size=13, family="Sora"),
                        hovertemplate=f"{t('Hafta','Week')} %{{x}}<br>%{{y}} {t('gol','goals')}<extra></extra>"))
                _gmax = max(goller) if goller else 0
                fig.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=260,
                    legend=dict(orientation="h", y=1.15),
                    xaxis=dict(title=t("Hafta", "Week"), gridcolor="#2d3561"),
                    yaxis=dict(title=t("Dakika", "Minutes"), gridcolor="#2d3561"),
                    yaxis2=dict(title=t("Gol", "Goals"), overlaying="y", side="right",
                                range=[0, max(_gmax, 1) + 0.6], dtick=1, showgrid=False,
                                tickfont=dict(color="#4ade80"), title_font=dict(color="#4ade80")),
                    margin=dict(l=40, r=40, t=24, b=40))
                st.plotly_chart(fig, width="stretch", key=_pk("plt_2957"))

        with g2:
            st.markdown(f"##### {t('Gol Zamanı Dağılımı', 'Goal Timing Distribution')}")
            tum_dakikalar = []
            for m in gecmis_tam:
                tum_dakikalar.extend(m.get("gol_dakikalari", []))
            if tum_dakikalar:
                # 15 dakikalık dilimlere böl
                dilimler  = ["1-15","16-30","31-45","46-60","61-75","76-90"]
                sinirlar  = [(1,15),(16,30),(31,45),(46,60),(61,75),(76,100)]
                sayilar   = [sum(1 for d in tum_dakikalar if s<=d<=e) for s,e in sinirlar]
                fig2 = go.Figure(go.Bar(
                    x=dilimler, y=sayilar,
                    marker_color=["#1565c0","#1976d2","#1e88e5","#ff8f00","#f57c00","#e65100"],
                    text=sayilar, textposition="outside",
                    hovertemplate="%{x}. dk — %{y} gol<extra></extra>",
                ))
                fig2.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=260,
                    xaxis=dict(title=t("Dakika Aralığı","Minutes Range"), gridcolor="#2d3561"),
                    yaxis=dict(title="Gol", gridcolor="#2d3561", dtick=1),
                    margin=dict(l=30,r=10,t=10,b=40), showlegend=False)
                st.plotly_chart(fig2, width="stretch", key=_pk("plt_2980"))
            elif gol > 0:
                st.caption(t("Gol dakikası verisi bu sezonda mevcut değil.", "Goal minute data not available for this season."))
            else:
                st.caption(t("Bu oyuncu gol atmadı.", "This player has not scored."))

        # ── Gol Yenmeme (clean sheet) verisi: oynadığı haftalarda takım gol yedi mi? ──
        _cs_flags, _cs_rakip = [], {}
        _ff_set = _forfeit_hafta_takim()
        _htk_cs = _oyuncu_hafta_takim(detay)        # transfer: o hafta hangi kulüpte
        for _m in gecmis_tam:                       # hafta artan sırada
            if _m.get("dakika", 0) > 0:
                _tk_h = _htk_cs.get(_m["hafta"]) or row["Takım"]
                # Hükmen/çekilme haftası → gerçek maç yok, clean sheet sayma
                if (_m["hafta"], _kanon(_tk_h)) in _ff_set:
                    continue
                _rk_tam = _hafta_rakip(_tk_h, _m["hafta"])
                _yen = _hafta_yenilen(_tk_h, _m["hafta"])
                if _yen is None:
                    continue
                _cs_flags.append(1 if _yen == 0 else 0)
                if _yen == 0:
                    _rk = _takim_kisa(_rk_tam or "—")
                    _cs_rakip[_rk] = _cs_rakip.get(_rk, 0) + 1
        en_uzun_cs = max_seri(_cs_flags)
        toplam_cs  = sum(_cs_flags)

        # ── Seriler ──────────────────────────────────────────────────────────
        if gecmis_tam:
            st.markdown(f"##### 🔥 {t('Seri Rekorları', 'Streak Records')}")
            en_uzun_mac = max_seri([1 for _ in gecmis_tam])
            gol_var = [1 if m["gol"]>0 else 0 for m in gecmis_tam]
            en_uzun_gol = max_seri(gol_var)
            temiz = [1 if m["sari"]==0 and m["kirmizi"]==0 else 0 for m in gecmis_tam]
            en_uzun_temiz = max_seri(temiz)

            s1,s2,s3,s4 = st.columns(4)
            s1.metric(f"🏃 {t('En Uzun Maç Serisi', 'Longest Match Streak')}", f"{en_uzun_mac} {t('maç','matches')}")
            s2.metric(f"⚽ {t('En Uzun Gol Serisi', 'Longest Goal Streak')}", f"{en_uzun_gol} {t('maç','matches')}")
            s3.metric(f"🧤 {t('En Uzun Gol Yenmeyen Seri', 'Longest Clean-Sheet Streak')}", f"{en_uzun_cs} {t('maç','matches')}")
            s4.metric(f"🟨 {t('En Uzun Kartsız Seri', 'Longest Card-Free Streak')}", f"{en_uzun_temiz} {t('maç','matches')}")

        # ── Rakip dağılımları: Yenen goller (sol) · Gol yenmeyen maçlar (sağ) ──
        _has_gol = gol > 0 and bool(_gol_rakip_dagil(detay))
        _has_cs  = bool(_cs_rakip)
        if _has_gol and _has_cs:
            _rd1, _rd2 = st.columns(2, gap="medium")
            with _rd1: _gol_rakip_grafik(detay, gol)
            with _rd2: _clean_sheet_grafik(_cs_rakip, toplam_cs)
        elif _has_gol:
            _gol_rakip_grafik(detay, gol)
        elif _has_cs:
            _clean_sheet_grafik(_cs_rakip, toplam_cs)

        # ── Transfer kırılımı ─────────────────────────────────────────────────
        if transfer:
            st.markdown(f"##### {t('Takım Bazlı İstatistikler', 'Stats by Club')}")
            satirlar = ""
            for d in detay.get("takim_detay", []):
                satirlar += f"""
                <div class="takim-detay-satir">
                  <span class="td-adi">🏟 {_takim_kisa(d['takim'])}</span>
                  <span class="td-stats">
                    {d['mac']} {t('maç','matches')} · {d['gol']} {t('gol','goals')} · {d['dakika']} {t('dk','min')} ·
                    🟨{d['sari']} 🟥{d['kirmizi']}
                  </span>
                </div>"""
            st.markdown(satirlar, unsafe_allow_html=True)

        # ── Sco Tr Scout Raporu (1207 Antalyaspor — varsa) ────────────────────
        render_scout_raporu(secili)

        # ── Oyuncu Kartı ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(f"##### 🃏 {t('Oyuncu Kartı', 'Player Card')}")
        st.markdown(f"""
        <div style="max-width:320px;margin:0 auto;
             background:linear-gradient(145deg,#1a1f36,#0d3b2e);
             border-radius:18px;padding:26px 28px;text-align:center;
             box-shadow:0 8px 32px rgba(0,0,0,0.6);
             border:1px solid #1db95444;">
          <div style="font-size:0.68rem;letter-spacing:3px;color:#1db954aa;margin-bottom:4px">
            {t("KADIN FUTBOL · 2025-2026","WOMEN'S FOOTBALL · 2025-2026")}
          </div>
          <div style="font-size:1.2rem;font-weight:800;color:#fff;margin-bottom:2px">{secili}</div>
          <div style="color:#8899aa;font-size:0.78rem;margin-bottom:20px">{_takim_kisa(row['Takım'])}</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">
            <div style="background:rgba(0,200,83,0.08);border:1px solid #1db95433;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#1db954">{gol}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">{t("GOL","GOALS")}</div>
            </div>
            <div style="background:rgba(41,121,255,0.08);border:1px solid #2979ff33;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#2979ff">{mac}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">{t("MAÇ","MATCHES")}</div>
            </div>
            <div style="background:rgba(255,109,0,0.08);border:1px solid #ff6d0033;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#ff6d00">{ort}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">{t("G/MAÇ","G/MATCH")}</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid #ffffff11;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#e0e0e0">{ilk11_oran}%</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">STARTER</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid #ffffff11;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#e0e0e0">{int(dk_mac)}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">{t("DK/MAÇ","MIN/MATCH")}</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid #ffffff11;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#f5c518">{sari}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">🟨 {t("KART","CARD")}</div>
            </div>
          </div>
        </div>
        <div style="text-align:center;color:#505870;font-size:0.7rem;margin-top:8px">
          {t("Ekran görüntüsü alarak paylaşabilirsiniz","You can share by taking a screenshot")}
        </div>
        """, unsafe_allow_html=True)

        # Ana lig kariyer (Scouting ile ORTAK: Trend+Radar yan yana + Kulüp/Milli)
        _al = analig_leistung_yukle().get(secili, {})
        _al_sezon = _al.get("sezonlar", [])
        if _al_sezon:
            st.markdown("---")
            # Milli takım: SD uyruk sırasında İLK ülke (= NT; çift-uyruklularda doğru takım)
            _al_milli = ulke_goster(_ilk_uyruk(sd_profiller.get(secili, {}).get("Nationality", "")))
            _kariyer_kulup_milli(secili, _al_sezon, "analig", _al_milli, _al.get("guncelleme", ""))

        # Benzer oyuncular (ana lig havuzu)
        st.markdown("---")
        benzer_oyuncular_goster(secili, "analig")

        # Benzer transfer hedefleri (scouting havuzundan — çapraz)
        st.markdown("---")
        capraz_transfer_goster(secili)


# ─── PAYLAŞILABILIR LİNK: URL parametresi varsa otomatik profil aç ──────────
params = st.query_params
url_oyuncu = params.get("oyuncu", "")

# ─── SAYFA DURUMU ─────────────────────────────────────────────────────────────
if "sayfa" not in st.session_state:
    st.session_state["sayfa"] = "ana"

# Kalıcı oturum: cookie geçerliyse sayfa yenilense de girişi geri yükle
_oturum_geri_yukle()

# Karşılama ekranı: ana içeriğe geçmeden önce herkese gösterilir (giriş gerekmez)
if "girildi" not in st.session_state:
    # Doğrudan oyuncu profil linki (?oyuncu=...) veya geçerli oturum varsa karşılamayı atla
    st.session_state["girildi"] = bool(url_oyuncu) or st.session_state.get("kulup_giris", False)

# ─── BAŞLIK & NAVİGASYON ──────────────────────────────────────────────────────
_nav_is_admin = st.session_state.get("kulup_kullanici") == "admin"
def _nav_git(yeni_sayfa: str):
    """Nav geçişi: ?oyuncu profil parametresini temizle, dili koru, sayfayı değiştir."""
    _dil = st.query_params.get("dil", "")
    st.query_params.clear()
    if _dil:
        st.query_params["dil"] = _dil
    st.session_state["sayfa"] = yeni_sayfa
    st.session_state["girildi"] = True   # sol panele tıklayan zaten içeri giriyor
    st.rerun()

def _tr_veri_git():
    """Ana TR veri ekranına dön (oyuncu profil/geçici state temizlenir)."""
    _dil_koru = st.query_params.get("dil", "")
    st.query_params.clear()
    if _dil_koru:
        st.query_params["dil"] = _dil_koru
    for k in list(st.session_state.keys()):
        if k not in ("sayfa","kulup_giris","kulup_kullanici","kulup_takim","kulup_ad",
                     "kulup_rol","kulup_tier","kulup_pro","dil","girildi"):
            del st.session_state[k]
    st.session_state["sayfa"] = "ana"
    st.session_state["girildi"] = True
    st.rerun()

# ─── SOL NAVİGASYON — SİTE AĞACI (üst menü + sekmeler tek dikey panelde) ──────
def _tr_sekme_etiketleri(giris: bool) -> list:
    """TR Veri sekme etiketleri — st.tabs ile birebir aynı sırada (login-gated)."""
    ust = []
    if giris:
        ust = [t("🏟️ Benim Kadrom", "🏟️ My Squad"),
               t("📝 Internal Scout", "📝 Internal Scout")]
    return ust + [
        t("📋 Oyuncu Listesi", "📋 Player List"),
        t("🔄 Transfer Öner", "🔄 Transfer Suggest"),
        t("🌱 Genç Yetenekler", "🌱 Young Talents"),
        t("👤 Oyuncu Profili", "👤 Player Profile"),
        t("⚡ Karşılaştırma", "⚡ Comparison"),
        t("🏟️ Takımlar", "🏟️ Teams"),
        t("🏆 Lig Tablosu", "🏆 League Table"),
        t("🌟 En İyiler", "🌟 Top Performers"),
        t("⚽ Fantasy Kadro", "⚽ Fantasy Squad"),
        t("🔍 Gelişmiş Arama", "🔍 Advanced Search"),
        t("🎂 Yaş Analizi", "🎂 Age Analysis"),
        t("🧤 Kaleciler", "🧤 Goalkeepers"),
    ]

_aktif_sayfa   = st.session_state.get("sayfa", "ana")
_nav_giris_var = st.session_state.get("kulup_giris", False)

with st.sidebar:
    # ── Marka (logo görseli — static/logo.png, şeffaf arka plan) ──
    st.markdown(
        "<div class='nav-marka-logo'>"
        "<img src='app/static/logo.png' alt=\"Women's Football Scouting\" "
        "title=\"Women's Football Scouting\"/>"
        "</div>",
        unsafe_allow_html=True)

    # ── Üyelik rozeti ──
    if _nav_giris_var:
        _tier = kullanici_tier()
        _t_ad, _t_renk, _t_ikon = _TIER_GORUNUM.get(_tier, _TIER_GORUNUM["basic"])
        _dn = aktif_deneme(st.session_state.get("kulup_kullanici", "")) if _tier != "admin" else None
        _uye_kelime = "" if _tier == "admin" else t("Üye", "Member")
        _deneme_kel = t("DENEME", "TRIAL")
        _dn_etk = (f"<span style='font-size:0.58rem;color:#e9d5ff;margin-left:5px;'>🎁 {_deneme_kel}</span>") if _dn else ""
        st.markdown(
            f"<div style='background:{_t_renk}1a;border:1px solid {_t_renk};"
            f"border-radius:7px;padding:6px 10px;text-align:center;margin:8px 2px 2px;'>"
            f"<span style='color:{_t_renk};font-size:0.72rem;font-weight:700;'>"
            f"{_t_ikon} {_t_ad} {_uye_kelime}</span>{_dn_etk}</div>",
            unsafe_allow_html=True)

    # ── Giriş / Çıkış + Dil (en üstte, her zaman görünür) ──
    _ac1, _ac2 = st.columns([1.5, 1])
    with _ac1:
        if _nav_giris_var:
            if st.button(t("🚪 Çıkış", "🚪 Logout"), key="nav_cikis", width="stretch"):
                for k in ["kulup_giris","kulup_kullanici","kulup_takim","kulup_ad","kulup_rol","kulup_tier","kulup_pro"]:
                    st.session_state.pop(k, None)
                _oturum_cikis()
                _nav_git("ana")
        else:
            if st.button(t("🔐 Giriş Yap", "🔐 Log In"), key="nav_login",
                         width="stretch", type="primary"):
                st.session_state["login_ac"] = True
                st.session_state["girildi"] = True
                st.rerun()
    with _ac2:
        if st.button("🌐 EN" if not EN else "🌐 TR", key="nav_dil", width="stretch"):
            _yeni_dil = "EN" if not EN else "TR"
            st.session_state["dil"] = _yeni_dil
            st.query_params["dil"] = _yeni_dil
            st.rerun()
    st.markdown("<div style='border-bottom:1px solid #1c2238;margin:8px 2px 0;'></div>",
                unsafe_allow_html=True)

    # ── PLATFORM grubu ──
    st.markdown(f"<div class='nav-grup'>{t('PLATFORM', 'PLATFORM')}</div>", unsafe_allow_html=True)
    if st.button(t("📊 TR Veri", "📊 TR Data"), key="nav_veri", width="stretch",
                 type="primary" if _aktif_sayfa == "ana" else "secondary"):
        _tr_veri_git()
    if st.button(t("🔎 Scouting", "🔎 Scouting"), key="nav_scout", width="stretch",
                 type="primary" if _aktif_sayfa == "scouting" else "secondary"):
        _nav_git("scouting")
    if st.button(t("👤 Profilim", "👤 My Profile"), key="nav_profil", width="stretch",
                 type="primary" if _aktif_sayfa == "profil" else "secondary"):
        _nav_git("profil")
    if st.button(t("📩 Talep / Danışmanlık", "📩 Request / Consult"), key="nav_talep", width="stretch",
                 type="primary" if _aktif_sayfa == "talep" else "secondary"):
        _nav_git("talep")
    if st.button(t("📬 İletişim", "📬 Contact"), key="nav_iletisim", width="stretch",
                 type="primary" if _aktif_sayfa == "iletisim" else "secondary"):
        _nav_git("iletisim")
    if st.button(t("🎗️ Saygı Kuşağı", "🎗️ Hall of Respect"), key="nav_saygi", width="stretch",
                 type="primary" if _aktif_sayfa == "saygi" else "secondary"):
        _nav_git("saygi")

    # ── TR VERİ SEKMELERİ grubu (tüm sayfalarda görünür) ──
    st.markdown(f"<div class='nav-grup'>{t('TR VERİ SEKMELERİ', 'TR DATA TABS')}</div>",
                unsafe_allow_html=True)
    _sk_etiketler = _tr_sekme_etiketleri(_nav_giris_var)
    _aktif_sekme = st.session_state.get("tr_sekme")
    if _aktif_sekme not in _sk_etiketler:
        _aktif_sekme = _sk_etiketler[0]
        st.session_state["tr_sekme"] = _aktif_sekme
    for _i, _et in enumerate(_sk_etiketler):
        # Aktif vurgu yalnız TR Veri sayfasındayken; başka sayfadayken
        # tıklanınca TR Veri'ye geçip o sekme açılır.
        _akt = (_aktif_sayfa == "ana" and _et == _aktif_sekme)
        if st.button(_et, key=f"navsek_{_i}", width="stretch",
                     type="primary" if _akt else "secondary"):
            st.session_state["tr_sekme"] = _et
            st.session_state["girildi"] = True   # sekmeye tıklayan içeri girer
            if _aktif_sayfa != "ana":
                _dil_k = st.query_params.get("dil", "")
                st.query_params.clear()
                if _dil_k:
                    st.query_params["dil"] = _dil_k
                st.session_state["sayfa"] = "ana"
            st.rerun()

    # ── Alt kategoriler (TR Veri'nin altında, ücretsiz) ──
    st.markdown(f"<div class='nav-grup'>{t('ALT KATEGORİLER', 'LOWER CATEGORIES')}</div>",
                unsafe_allow_html=True)
    if st.button(t("🥈 Alt Ligler", "🥈 Lower Leagues"), key="nav_altlig", width="stretch",
                 type="primary" if _aktif_sayfa == "altlig" else "secondary"):
        _nav_git("altlig")
    if st.button(t("🌱 Alt Yaşlar", "🌱 Youth Leagues"), key="nav_altyas", width="stretch",
                 type="primary" if _aktif_sayfa == "altyas" else "secondary"):
        _nav_git("altyas")

# ─── HERO (tam genişlik — sağda boşluk kalmaz) ────────────────────────────────
_hero_oyuncu = len(df_tam) if not df_tam.empty else 0
_hero_takim  = _kanon_takim_sayisi(df_tam["Takım"]) if not df_tam.empty else 0
_hero_gol    = int(df_tam["Gol"].sum()) if not df_tam.empty else 0
try:    _hero_scout = len(scout_kadro_yukle())
except Exception: _hero_scout = 0
# Hero + danışmanlık bandı YALNIZ ana ekranın İLK sekmesinde (Oyuncu Listesi)
# gösterilir; diğer TR Veri alt sekmelerinde (Profil, Karşılaştırma vb.) üstte yer
# kaplamasın diye gizlenir (kullanıcı geri bildirimi: "sadece ilk sekmede göster").
_ana_ekran = (not url_oyuncu) and st.session_state.get("sayfa", "ana") == "ana"
_tr_sekmeler_h = _tr_sekme_etiketleri(st.session_state.get("kulup_giris", False))
_ilk_tr_sekme  = _tr_sekmeler_h[0] if _tr_sekmeler_h else None
_tr_sekme_sec  = st.session_state.get("tr_sekme", _ilk_tr_sekme)
_ilk_sekmede   = (_tr_sekme_sec == _ilk_tr_sekme) or (_tr_sekme_sec not in _tr_sekmeler_h)
_ust_blok_goster = _ana_ekran and _ilk_sekmede and not params.get("paylas", "").strip()
if _ust_blok_goster:
  st.markdown(f"""
<div class="baslik-kutu">
  <div class="ust-bant">⚡ {t("KADIN FUTBOLU PLATFORMU", "WOMEN'S FOOTBALL PLATFORM")}</div>
  <h1>{t('Veri · Scouting · <span class="vurgu">Kadro Danışmanlığı</span>',
         'Data · Scouting · <span class="vurgu">Squad Consultancy</span>')}</h1>
  <p>{t("Türkiye Kadınlar Süper Ligi istatistikleri · uluslararası oyuncu havuzu · kariyer ve benzerlik analizi · kulüplere özel kadro danışmanlığı",
        "Turkish Women's Super League stats · international player pool · career &amp; similarity analysis · club-tailored squad consultancy")}</p>
  <div class="hero-chips">
    <span class="hero-chip">{t("SEZON","SEASON")} <b>2025-26</b></span>
    <span class="hero-chip"><b>{_hero_takim}</b> {t("TAKIM","TEAMS")}</span>
    <span class="hero-chip"><b>{_hero_oyuncu}</b> {t("OYUNCU","PLAYERS")}</span>
    <span class="hero-chip"><b>{_hero_gol}</b> {t("GOL","GOALS")}</span>
    <span class="hero-chip">🔬 <b>{_hero_scout}</b> {t("SCOUT RAPORU","SCOUT REPORTS")}</span>
  </div>
</div>""", unsafe_allow_html=True)

# "🔐 Giriş" butonuna basılınca ana alanda açılan giriş kartı
# (üyelik rozeti + giriş/çıkış artık sol navigasyon panelinde)
giris_formu_ana()


# ─── Oyuncu profili MODALI (alta kaydırmak yerine üstte açılır) ───────────────
# Liste/filtre sayfasından ayrılmadan profil açar → geri dönünce hiçbir şey
# sıfırlanmaz. Tanım her run'da yenilenir → başlık dile göre doğru gelir.
def profil_ac(isim: str, kaynak: str = "tr"):
    st.session_state["_profil_dlg"] = (isim, kaynak)
    st.rerun()

@st.dialog(t("📋 Oyuncu Profili", "📋 Player Profile"), width="large")
def _profil_dialog(isim, kaynak):
    if kaynak == "scout":
        render_scouting_detay(isim)
    else:
        render_ana_lig_profil(isim)


def render_paylasim_raporu(isim: str):
    """PUBLIC (giriş gerektirmez) tek-oyuncu paylaşılabilir scout raporu (?paylas=X).
    Kulübe link gönderilir; alıcı giriş yapmadan markalı raporu görür. Tek oyuncu →
    tüm havuz açılmaz. Altta 'üye ol' CTA'sı (dönüşüm)."""
    isim = (isim or "").strip()
    # Temiz public sayfa: sol nav + chrome gizle, dar kolon
    st.markdown(
        "<style>section[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none!important;}"
        ".block-container{max-width:820px!important;padding-top:1rem!important;}</style>",
        unsafe_allow_html=True)
    kadro = scout_kadro_yukle().get(isim, {})
    sd    = scouting_sd_yukle().get(isim) or sd_profiller.get(isim) or {}
    leist = (scouting_leistung_yukle().get(isim) or {}).get("sezonlar", [])
    if not (kadro or sd):
        st.markdown(f"<div style='text-align:center;padding:70px 20px;color:#8899aa;'>"
                    f"⚠️ {t('Rapor bulunamadı.','Report not found.')}</div>", unsafe_allow_html=True)
        st.stop()

    _mv = kadro.get("mevki", "")
    mevki = " · ".join(_mv) if isinstance(_mv, list) else str(_mv or "")
    rol   = kadro.get("rol", "") or ""
    yas   = kadro.get("yas", "") or str(sd.get("Age", "") or "").split()[0] if (kadro.get("yas") or sd.get("Age")) else "—"
    boy   = kadro.get("boy", "") or sd.get("Height", "") or "—"
    ayak  = kadro.get("ayak", "") or sd.get("Foot", "") or "—"
    try:    uyruk = ulke_goster(kadro.get("vatandaslik", "")) or sd.get("Nationality", "") or "—"
    except Exception: uyruk = kadro.get("vatandaslik", "") or "—"
    try:    milli = ulke_goster(kadro.get("milli_takim", "")) if kadro.get("milli_takim") else ""
    except Exception: milli = kadro.get("milli_takim", "")
    kulup = _takim_kisa(kadro.get("kulup", "") or "") or "—"
    lig   = kadro.get("lig", "") or "—"
    deger = kadro.get("deger", "") or sd.get("Market value", "") or "—"
    sozl  = kadro.get("sozlesme", "") or sd.get("Contract until", "") or "—"
    nihai = (kadro.get("nihai", "") or "").strip()
    tarz  = kadro.get("tarz", "") or ""
    notu  = kadro.get("scout_notu", "") or kadro.get("tr_gorusu", "") or ""
    kmac = kgol = kasist = 0
    for s in leist:
        if not s.get("milli"):
            kmac += int(s.get("mac", 0) or 0); kgol += int(s.get("gol", 0) or 0); kasist += int(s.get("asist", 0) or 0)
    try:    _ngr = _scotr_renk(nihai) if nihai else "#1db954"
    except Exception: _ngr = "#1db954"

    def _e(x): return _html.escape(str(x))
    _grade = (f"<div style='flex:none;text-align:center;'>"
              f"<div style='width:74px;height:74px;border-radius:50%;border:3px solid {_ngr};"
              f"display:flex;align-items:center;justify-content:center;font-family:Sora,monospace;"
              f"font-size:1.5rem;font-weight:900;color:{_ngr};'>{_e(nihai)}</div>"
              f"<div style='font-size:0.58rem;color:#8899aa;letter-spacing:0.1em;margin-top:4px;'>NİHAİ</div></div>") if nihai else ""
    _bilgiler = [(t("Yaş","Age"), yas), (t("Uyruk","Nat."), uyruk), (t("Milli Tk.","NT"), milli or "—"),
                 (t("Kulüp","Club"), kulup), (t("Lig","League"), lig), (t("Boy","Height"), boy),
                 (t("Ayak","Foot"), ayak), (t("Değer","Value"), deger), (t("Sözleşme","Contract"), sozl)]
    _bg = "".join(
        f"<div style='background:#0e1326;border:1px solid #232a40;border-radius:9px;padding:9px 11px;'>"
        f"<div style='font-size:0.58rem;color:#8899aa;text-transform:uppercase;letter-spacing:0.06em;'>{_e(l)}</div>"
        f"<div style='font-size:0.9rem;color:#e8eef7;font-weight:600;margin-top:2px;'>{_e(v)}</div></div>"
        for l, v in _bilgiler)
    _kariyer = (f"<div style='display:flex;gap:10px;margin-top:14px;'>" + "".join(
        f"<div style='flex:1;background:#0e1326;border:1px solid #232a40;border-radius:10px;padding:12px;text-align:center;'>"
        f"<div style='font-family:Sora,monospace;font-size:1.5rem;font-weight:800;color:#1db954;'>{val}</div>"
        f"<div style='font-size:0.62rem;color:#8899aa;text-transform:uppercase;letter-spacing:0.05em;'>{lbl}</div></div>"
        for val, lbl in [(kmac, t("Maç","Matches")), (kgol, t("Gol","Goals")), (kasist, t("Asist","Assists"))])
        + "</div>") if (kmac or kgol or kasist) else ""
    _notu_html = (f"<div style='background:#0e1326;border-left:3px solid #a855f7;border-radius:8px;"
                  f"padding:12px 16px;margin-top:14px;color:#cbd5e1;font-size:0.88rem;line-height:1.6;'>"
                  f"📋 {_e(notu)}</div>") if notu else ""

    st.markdown(
        f"""
        <div style="background:linear-gradient(120deg,#0a0e1bf2 0%,#140c26ea 55%,#1d0d29c0 100%),
             url('app/static/b2.jpg') center 25%/cover no-repeat;border:1px solid #2c2350;
             border-radius:16px;padding:26px 30px;overflow:hidden;box-shadow:0 14px 44px -14px #000000aa;">
          <div style='display:flex;align-items:center;gap:13px;'>
            <img src='app/static/logo.png' alt="Women's Football Scouting"
                 style='height:46px;width:auto;filter:drop-shadow(0 3px 12px rgba(168,85,247,0.55));'/>
            <div style='font-size:0.62rem;font-weight:800;color:#c084fc;letter-spacing:0.22em;
                 padding-left:13px;border-left:1px solid #ffffff22;'>
              {t('SCOUT RAPORU','SCOUT REPORT')}</div>
          </div>
          <div style='display:flex;align-items:center;gap:18px;margin-top:10px;flex-wrap:wrap;'>
            <div style='flex:1;min-width:200px;'>
              <div style='font-family:Oswald,Sora,sans-serif;font-size:2.1rem;font-weight:700;color:#fff;line-height:1.05;'>{_e(isim)}</div>
              <div style='color:#9fb0c6;font-size:0.92rem;margin-top:3px;'>{_e(mevki)}{(' · ' + _e(rol)) if rol else ''}</div>
            </div>
            {_grade}
          </div>
        </div>
        <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-top:14px;'>{_bg}</div>
        {(f"<div style='color:#aebbd0;font-size:0.86rem;margin-top:12px;'>🎬 <b style='color:#e0e0e0;'>{t('Oyun Tarzı','Play Style')}:</b> {_e(tarz)}</div>") if tarz else ""}
        {_kariyer}
        {_notu_html}
        <div style='margin-top:22px;padding:18px;background:linear-gradient(135deg,#151a33,#1d1438);
             border:1px solid #3b2d6e;border-radius:14px;text-align:center;'>
          <div style='font-family:Oswald,Sora,sans-serif;font-size:1.15rem;font-weight:700;color:#fff;'>
            {t('Tüm scouting havuzu için','For the full scouting pool')}</div>
          <div style='color:#a78bfa;font-size:0.85rem;margin:4px 0 12px;'>
            {t('780+ oyuncu · kariyer & benzerlik analizi · kadro danışmanlığı','780+ players · career & similarity analysis · squad consultancy')}</div>
          <a href='/' style='display:inline-block;background:linear-gradient(135deg,#7c3aed,#db2777);
             color:#fff;font-weight:700;text-decoration:none;border-radius:9px;padding:10px 26px;'>
            🚀 {t('Üye Ol / Giriş','Join / Log In')}</a>
        </div>
        <div style='text-align:center;color:#566179;font-size:0.72rem;margin-top:14px;'>
          womenfootballscouting.com · {t('Veri: TFF & SoccerDonna','Data: TFF & SoccerDonna')}</div>
        """,
        unsafe_allow_html=True)
    st.stop()


# ─── HAKKINDA SAYFASI ─────────────────────────────────────────────────────────
# ─── PAYLAŞIM RAPORU (?paylas=X) — public, giriş gerektirmez ──────────────────
if params.get("paylas", "").strip():
    render_paylasim_raporu(params.get("paylas", ""))

# ─── ODAKLI PROFİL SAYFASI (?oyuncu=X) — sekmeler yerine tek oyuncu ───────────
if url_oyuncu:
    # Yeni sekmede çerez/oturum geri yüklenirken İLK run'da kullanıcı "giriş yapmamış"
    # görünür → gate (paywall) bir an flaş eder. Çereze bir rerun şansı vermek için ilk
    # run'da "Yükleniyor" göster + dur (cookie controller mount olunca rerun tetikler).
    # _ck_grace_oyuncu tek seferlik → sonsuz döngü yok; cookie yoksa (None) atlanır.
    if (_cookie_ctrl() is not None and not st.session_state.get("kulup_giris")
            and not st.session_state.get("_ck_grace_oyuncu")):
        st.session_state["_ck_grace_oyuncu"] = True
        st.markdown(
            "<style>section[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']"
            "{display:none!important;}</style>"
            "<div style='text-align:center;padding:100px 20px;color:#8899aa;'>"
            "<div style='font-size:1.8rem;'>⏳</div>"
            f"<div style='margin-top:10px;font-size:0.95rem;'>{t('Profil yükleniyor…','Loading profile…')}</div></div>",
            unsafe_allow_html=True)
        st.stop()
    render_odakli_profil(url_oyuncu)
    st.stop()

def render_hakkinda_icerik():
    """Hakkında metnini render eder (Hakkında sayfası + GİRİŞ sekmesi ortak kullanır)."""
    st.markdown(f"""
    <div style='max-width:760px;margin:0 auto;padding:10px 0 40px;'>

    <h2 style='color:#1db954;margin-bottom:6px;'>{t("Biz Kimiz?", "Who Are We?")}</h2>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Türkiye'de kadın futbol liglerini takip eden bir grup futbol delisiyiz. Yıllardır tribünlerde, ekranların başında ve saha kenarlarında bu ligin büyümesine tanıklık ettik. Ama bir şeyin hep eksik kaldığını fark ettik: <b style='color:#fff;'>veri.</b>",
       "We are a group of football fanatics following women's football leagues in Türkiye. For years we've witnessed this league grow from the stands, the screens and the touchlines. But we noticed one thing was always missing: <b style='color:#fff;'>data.</b>")}
    </p>

    <h2 style='color:#1db954;margin-top:32px;margin-bottom:6px;'>{t("Neden Bu Siteyi Kurduk?", "Why Did We Build This?")}</h2>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Bir oyuncuyu bir maçta izlemek, o oyuncu hakkında tam bir fikir vermez. Gözlem yanılabilir — kötü bir gün, yorgunluk, takımın taktik yapısı ya da sadece o günkü rakip; bunların hepsi algıyı bozar. Kulüplerin çoğu hâlâ transferlerde \"rakibe karşı oynadığı o maçtaki izlenim\" ya da duyuma dayalı kararlar alıyor.",
       "Watching a player in a single match doesn't give a full picture. Observation can mislead — a bad day, fatigue, the team's tactical setup or just that day's opponent all distort perception. Most clubs still make transfer decisions based on \"the impression from that one match against us\" or on hearsay.")}
    </p>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Biz buna karşı <b style='color:#fff;'>ölçme ve değerlendirme metotları</b> geliştirmeye çalışıyoruz. Henüz değerini bulamamış ya da bulma aşamasındaki oyuncuları verilerle desteklemeyi, onların ligdeki gerçek katkılarını görünür kılmayı hedefliyoruz. Böylece takımlar; sadece rakipleri olduğu maçlardaki gözleme ya da kulaktan dolma bilgilere değil, <b style='color:#fff;'>sezon boyu biriken somut istatistiklere</b> dayanarak daha nitelikli kadrolar oluşturabilsin.",
       "Against this, we try to develop <b style='color:#fff;'>measurement and evaluation methods</b>. We aim to back undervalued or rising players with data and make their real contribution to the league visible. So that teams can build better squads based on <b style='color:#fff;'>concrete stats accumulated across the season</b> — not just observation from matches against them or word of mouth.")}
    </p>

    <h2 style='color:#1db954;margin-top:32px;margin-bottom:6px;'>{t("Bu Sitede Ne Var?", "What's on This Site?")}</h2>
    <div style='color:#c9d1d9;font-size:14px;line-height:2;'>
    {t('''📋 <b style='color:#fff;'>Oyuncu Listesi</b> — Ligdeki tüm oyuncuların sezon istatistikleri<br>
    👤 <b style='color:#fff;'>Oyuncu Profili</b> — Her oyuncu için detaylı performans kartı, kariyer ve benzerlik<br>
    🔎 <b style='color:#fff;'>Scouting</b> — Uluslararası oyuncu havuzu, shortlist ve etiketler<br>
    📩 <b style='color:#fff;'>Danışmanlık</b> — Kulübüne özel oyuncu raporu ve kadro planlama<br>
    🧤 <b style='color:#fff;'>Kaleciler</b> — Yenilen gol ve maç başına performans analizi<br>
    🏟️ <b style='color:#fff;'>Takımlar</b> — Takım bazında istatistikler ve kadro analizi<br>
    🏆 <b style='color:#fff;'>Lig Tablosu</b> — Güncel puan durumu<br>
    🔍 <b style='color:#fff;'>Gelişmiş Arama</b> — Uyruk, mevki, yaş ve maç sayısına göre filtrele''',
       '''📋 <b style='color:#fff;'>Player List</b> — Season stats of every player in the league<br>
    👤 <b style='color:#fff;'>Player Profile</b> — Detailed performance card, career & similarity per player<br>
    🔎 <b style='color:#fff;'>Scouting</b> — International player pool, shortlist and tags<br>
    📩 <b style='color:#fff;'>Consultancy</b> — Club-tailored player reports and squad planning<br>
    🧤 <b style='color:#fff;'>Goalkeepers</b> — Goals conceded and per-match performance<br>
    🏟️ <b style='color:#fff;'>Teams</b> — Team-level stats and squad analysis<br>
    🏆 <b style='color:#fff;'>League Table</b> — Current standings<br>
    🔍 <b style='color:#fff;'>Advanced Search</b> — Filter by nationality, position, age and matches''')}
    </div>

    <p style='color:#505870;font-size:12px;margin-top:36px;border-top:1px solid #21262d;padding-top:16px;'>
    {t("⚠️ Veriler TFF ve SoccerDonna kaynaklarından derlenmektedir. İstatistikler bilgi amaçlıdır; hata veya eksiklik içerebilir. Gözlemlerimiz ve değerlendirmelerimiz kişisel yoruma dayanır, yanılabiliriz — bu yüzden her zaman veriyi ön plana çıkarmaya çalışırız.",
       "⚠️ Data is compiled from TFF and SoccerDonna sources. Stats are for informational purposes and may contain errors or gaps. Our observations and evaluations rely on personal judgement and can be wrong — that's why we always try to put the data first.")}
    </p>
    </div>
    """, unsafe_allow_html=True)


def _profil_kart(deger, etiket, renk="#58a6ff"):
    return (f'<div class="stat-kart" style="border-radius:14px;">'
            f'<div class="sayi" style="color:{renk};font-size:1.25rem;">{deger}</div>'
            f'<div class="etiket">{etiket}</div></div>')


def render_profil():
    """Profilim sayfası: üyelik + giriş bilgileri + favoriler + etiketler + veri + iletişim."""
    st.markdown(f"## 👤 {t('Profilim', 'My Profile')}")
    if not st.session_state.get("kulup_giris"):
        st.info(t("Profilini görüntülemek için soldaki menüden 🔐 Giriş yap.",
                  "Log in via 🔐 in the left sidebar to view your profile."))
        return

    ku    = st.session_state.get("kulup_kullanici", "")
    ad    = st.session_state.get("kulup_ad", ku)
    rol   = st.session_state.get("kulup_rol", "kulup")
    takim = st.session_state.get("kulup_takim", "")
    _t_ad, tier_renk, _t_ik = _TIER_GORUNUM.get(kullanici_tier(), _TIER_GORUNUM["basic"])
    tier  = _t_ad

    # ── Üyelik Bilgileri ──
    st.markdown(f"#### 🪪 {t('Üyelik Bilgileri', 'Membership')}")
    c = st.columns(4)
    for kol, (v, l, r) in zip(c, [
        (ad or "—",        t("Ad", "Name"),       "#58a6ff"),
        (ku or "—",        t("Kullanıcı", "Username"), "#58a6ff"),
        (takim or "—",     t("Takım", "Team"),     "#1db954"),
        (tier,             t("Üyelik", "Tier"),    tier_renk),
    ]):
        kol.markdown(_profil_kart(v, l, r), unsafe_allow_html=True)

    # ── Aktif deneme bildirimi (kullanıcının kendisi) ──
    _kendi_dn = aktif_deneme(ku)
    if _kendi_dn:
        import time as _t
        _kalan = _deneme_ts(_kendi_dn.get("bitis","")) - _t.time()
        _saat = max(0, int(_kalan // 3600)); _dk = max(0, int((_kalan % 3600) // 60))
        _d_ad = _TIER_GORUNUM.get((_kendi_dn.get("tier") or "premium").lower(), _TIER_GORUNUM["premium"])[0]
        st.markdown(
            f"<div style='background:#e040fb1a;border:1px solid #e040fb;border-radius:10px;"
            f"padding:10px 16px;margin-top:6px;color:#e9d5ff;font-size:0.86rem;font-weight:600;'>"
            f"🎁 {t(f'{_d_ad} deneme aktif', f'{_d_ad} trial active')} · "
            f"<b>{_saat}s {_dk}dk</b> {t('kaldı','left')}</div>",
            unsafe_allow_html=True)

    # ── Admin: Deneme Yönetimi ──
    if ku == "admin":
        with st.expander(f"🎁 {t('Deneme Yönetimi (Admin)','Trial Management (Admin)')}", expanded=False):
            _creds = kulup_credentials_yukle()
            _kuluplar = [k for k in _creds if _creds[k].get("rol") != "admin"]
            _dv1, _dv2, _dv3, _dv4 = st.columns([2, 1.2, 1, 1])
            with _dv1:
                _dn_kul = st.selectbox(t("Kulüp","Club"), _kuluplar,
                    format_func=lambda k: _creds[k].get("ad", k), key="dn_kul")
            with _dv2:
                _dn_tier = st.selectbox(t("Kademe","Tier"), ["premium","pro"],
                    format_func=lambda x: _TIER_GORUNUM[x][0], key="dn_tier")
            with _dv3:
                _dn_gun = st.number_input(t("Gün","Days"), 1, 30, 2, key="dn_gun")
            with _dv4:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button(t("🎁 Ver","🎁 Grant"), width="stretch", type="primary", key="dn_ver"):
                    deneme_ver(_dn_kul, _dn_tier, int(_dn_gun), "admin")
                    st.success(t(f"{_creds[_dn_kul].get('ad',_dn_kul)} için {int(_dn_gun)} günlük {_TIER_GORUNUM[_dn_tier][0]} denemesi verildi.",
                                 f"Granted {int(_dn_gun)}-day {_TIER_GORUNUM[_dn_tier][0]} trial to {_creds[_dn_kul].get('ad',_dn_kul)}."))
                    st.rerun()
            # Aktif denemeler listesi
            import time as _t
            _aktifler = [d for d in denemeler_yukle()
                         if _deneme_ts(d.get("bitis","")) > _t.time()]
            if _aktifler:
                st.markdown(f"**{t('Aktif Denemeler','Active Trials')} ({len(_aktifler)})**")
                for _d in _aktifler:
                    _kalan = _deneme_ts(_d.get("bitis","")) - _t.time()
                    _sa = max(0, int(_kalan // 3600))
                    _kc1, _kc2 = st.columns([4, 1])
                    _kc1.markdown(
                        f"<div style='font-size:0.82rem;color:#cbd5e1;padding:4px 0;'>"
                        f"🎁 <b>{_creds.get(_d.get('kullanici',''),{}).get('ad', _d.get('kullanici',''))}</b> · "
                        f"{_TIER_GORUNUM.get((_d.get('tier') or 'premium').lower(),('?',))[0]} · "
                        f"{_sa}s {t('kaldı','left')} <span style='color:#64748b;'>"
                        f"({_d.get('bitis','')})</span></div>", unsafe_allow_html=True)
                    if _kc2.button(t("İptal","Cancel"), key=f"dn_ipt_{_d.get('kullanici','')}",
                                   width="stretch"):
                        deneme_iptal(_d.get("kullanici",""))
                        st.rerun()
            else:
                st.caption(t("Aktif deneme yok.","No active trials."))

        # ── Admin: Üye Yönetimi (kayıtlı üyeleri kademe/süre yönet) ──
        with st.expander(f"👥 {t('Üye Yönetimi (Admin)','Member Management (Admin)')}", expanded=False):
            _uyeler = uyeler_yukle()
            _uy1, _uy2 = st.columns([3, 1])
            _uy1.caption(t(f"{len(_uyeler)} kayıtlı üye · havale ile ödeyeni seç → kademe + süre ver.",
                           f"{len(_uyeler)} registered members · pick a payer → grant tier + duration."))
            if _uy2.button(t("🔄 Yenile", "🔄 Refresh"), key="uye_yenile", width="stretch"):
                uyeler_yukle.clear(); st.rerun()
            if not _uyeler:
                st.caption(t("Henüz kayıtlı üye yok.", "No registered members yet."))
            else:
                _TIERS = ["free", "basic", "pro", "premium"]
                # süre seçenekleri: (anahtar, etiket_tr, etiket_en, gün)
                _SURE = [("1ay","1 ay","1 month",30), ("3ay","3 ay","3 months",90),
                         ("6ay","6 ay","6 months",180), ("1yil","1 yıl","1 year",365),
                         ("suresiz","Süresiz","Unlimited",0)]
                _epostalar = sorted(_uyeler.keys())
                _c1, _c2, _c3 = st.columns([2.4, 1.3, 1.3])
                with _c1:
                    _sec = st.selectbox(t("Üye", "Member"), _epostalar,
                        format_func=lambda e: f"{_uyeler[e].get('ad', e)} · {e}", key="uye_sec")
                _mevcut_tier = (_uyeler[_sec].get("tier") or "free").lower()
                with _c2:
                    _tier_sec = st.selectbox(t("Kademe", "Tier"), _TIERS,
                        index=_TIERS.index(_mevcut_tier) if _mevcut_tier in _TIERS else 0,
                        format_func=lambda x: _TIER_GORUNUM[x][0], key="uye_tier")
                with _c3:
                    _sure_sec = st.selectbox(t("Süre", "Duration"), _SURE,
                        format_func=lambda s: s[1] if not EN else s[2], key="uye_sure")
                _cur_bt = _uyeler[_sec].get("bitis_tarihi", "")
                st.caption(t(f"Şu an: {_TIER_GORUNUM.get(_mevcut_tier,('?',))[0]}"
                             + (f" · bitiş {_cur_bt}" if _cur_bt else " · süresiz/yok"),
                             f"Now: {_TIER_GORUNUM.get(_mevcut_tier,('?',))[0]}"
                             + (f" · ends {_cur_bt}" if _cur_bt else " · none")))
                if st.button(t("💾 Güncelle", "💾 Update"), type="primary", key="uye_guncelle_btn"):
                    from datetime import date, timedelta
                    _gun = _sure_sec[3]
                    _bt = "" if (_gun == 0 or _tier_sec == "free") \
                        else (date.today() + timedelta(days=_gun)).isoformat()
                    if uye_guncelle(_sec, tier=_tier_sec, bitis_tarihi=_bt):
                        st.success(t(f"{_uyeler[_sec].get('ad', _sec)} → {_TIER_GORUNUM[_tier_sec][0]}"
                                     + (f" ({_bt} tarihine kadar)" if _bt else ""),
                                     f"{_uyeler[_sec].get('ad', _sec)} → {_TIER_GORUNUM[_tier_sec][0]}"
                                     + (f" (until {_bt})" if _bt else "")))
                        st.rerun()
                    else:
                        st.error(t("Güncellenemedi (GSheets erişimi?).", "Update failed (GSheets access?)."))
                # Üye listesi tablosu (mobil-dostu kart)
                _satirlar = [{
                    "ad": _uyeler[e].get("ad", e), "eposta": e,
                    "kulup": _uyeler[e].get("takim", ""),
                    "kademe": _TIER_GORUNUM.get((_uyeler[e].get("tier") or "free").lower(), ("?",))[0],
                    "bitis": _uyeler[e].get("bitis_tarihi", "") or "—",
                    "durum": _uyeler[e].get("durum", "aktif"),
                } for e in _epostalar]
                df_tablo(pd.DataFrame(_satirlar),
                    basliklar={"ad": t("Ad","Name"), "eposta": "E-posta", "kulup": t("Kulüp","Club"),
                               "kademe": t("Kademe","Tier"), "bitis": t("Bitiş","Ends"),
                               "durum": t("Durum","Status")})

        # ── Admin: Ödeme Bildirimleri (havale yapanlar → tek tık onay) ──
        with st.expander(f"💸 {t('Ödeme Bildirimleri (Admin)','Payment Notifications (Admin)')}", expanded=False):
            _odm = odemeler_yukle()
            _bekleyen = [o for o in _odm if str(o.get("durum", "")).lower() == "beklemede"]
            _o1, _o2 = st.columns([3, 1])
            _o1.caption(t(f"{len(_bekleyen)} bekleyen · {len(_odm)} toplam bildirim.",
                          f"{len(_bekleyen)} pending · {len(_odm)} total."))
            if _o2.button(t("🔄 Yenile", "🔄 Refresh"), key="odm_yenile", width="stretch"):
                odemeler_yukle.clear(); st.rerun()
            if not _bekleyen:
                st.caption(t("Bekleyen ödeme bildirimi yok.", "No pending payment notifications."))
            for _o in _bekleyen:
                _oku = str(_o.get("kullanici", "")); _opl = str(_o.get("plan", "")); _otr = str(_o.get("tarih", ""))
                _pad = _PLAN_FIYAT.get(_opl, (_opl, ""))[0]
                _r1, _r2, _r3 = st.columns([3, 1, 1])
                _r1.markdown(
                    f"<div style='font-size:0.85rem;color:#cbd5e1;padding:6px 0;'>"
                    f"💸 <b>{_oku}</b> → {_pad} · {_o.get('tutar','')} "
                    f"<span style='color:#64748b;'>({_otr})</span>"
                    + (f"<br><span style='color:#8899aa;font-size:0.78rem;'>📝 {_o.get('not','')}</span>"
                       if _o.get("not") else "") + "</div>", unsafe_allow_html=True)
                if _r2.button(t("✅ Onayla", "✅ Approve"), key=f"odm_ok_{_oku}_{_otr}",
                              type="primary", width="stretch"):
                    from datetime import date, timedelta
                    _bt = (date.today() + timedelta(days=365)).isoformat()
                    if uye_guncelle(_oku, tier=_opl, bitis_tarihi=_bt):
                        odeme_durum_guncelle(_oku, _opl, _otr, "onaylandi")
                        st.success(t(f"{_oku} → {_pad} (1 yıl) aktive edildi.",
                                     f"{_oku} → {_pad} (1 yr) activated."))
                    else:
                        st.error(t("Üye bulunamadı (kayıtlı mı?) — manuel kontrol et.",
                                   "Member not found (registered?) — check manually."))
                    st.rerun()
                if _r3.button(t("✖ Reddet", "✖ Reject"), key=f"odm_no_{_oku}_{_otr}", width="stretch"):
                    odeme_durum_guncelle(_oku, _opl, _otr, "reddedildi")
                    st.rerun()

    # ── Giriş Bilgileri ──
    from datetime import datetime, date
    log = giris_log_oku(ku)
    def _gunsay(s):
        try: return (date.today() - datetime.strptime(str(s)[:10], "%Y-%m-%d").date()).days
        except Exception: return None
    ilk    = log.get("ilk_giris", "")
    son     = log.get("son_giris", "")
    sayi    = log.get("giris_sayisi", "")
    hatali  = log.get("son_hatali_giris", "")
    aktif_g = _gunsay(ilk)

    st.markdown(f"#### 🔑 {t('Giriş Bilgileri', 'Login Info')}")
    c = st.columns(4)
    for kol, (v, l, r) in zip(c, [
        (f"{aktif_g} {t('gün','d')}" if aktif_g is not None else "—", t("Kaç gündür aktif", "Active for"), "#1db954"),
        (son or "—",                                                   t("Son giriş", "Last login"),       "#58a6ff"),
        (str(sayi) if str(sayi) != "" else "—",                        t("Toplam giriş", "Total logins"),  "#58a6ff"),
        (hatali or "—",                                                t("Son hatalı giriş", "Last failed"), "#ff6b6b"),
    ]):
        kol.markdown(_profil_kart(v, l, r), unsafe_allow_html=True)
    if not log:
        st.caption(t("ℹ️ Giriş geçmişi canlı sitede kaydedilir (ilk girişinden itibaren). Lokal testte görünmez.",
                     "ℹ️ Login history is recorded on the live site (from your first login). Not shown in local test."))

    # ── Favori Listem ──
    fav = shortlist_kullanici(ku)
    st.markdown(f"#### ⭐ {t('Favori Listem', 'My Favorites')} ({len(fav)})")
    if fav:
        fcols = st.columns(3)
        for i, isim in enumerate(sorted(fav)):
            if fcols[i % 3].button(f"👤 {isim}", key=f"pf_fav_{i}", width="stretch"):
                st.query_params["oyuncu"] = isim
                st.rerun()
    else:
        st.caption(t("Henüz favori eklemedin. Scouting'te ☆ ile ekleyebilirsin.",
                     "No favorites yet. Add players with ☆ in Scouting."))

    # ── Çektiğim Scouting Raporları (etiketlenen oyuncular) ──
    etk = etiket_kullanici(ku)
    etk_dolu = {k: v for k, v in etk.items() if v and v != "—"}
    st.markdown(f"#### 🗂️ {t('Çektiğim Scouting Raporları', 'My Scouting Reports')} ({len(etk_dolu)})")
    if etk_dolu:
        for isim, e in etk_dolu.items():
            st.markdown(f"- {etiket_badge_goster(e)} &nbsp; **{isim}**", unsafe_allow_html=True)
    else:
        st.caption(t("Üzerinde çalıştığın (etiketlediğin) oyuncular burada listelenir.",
                     "Players you've worked on (tagged) are listed here."))

    # ── Verilerim (CSV dışa aktarma) ──
    st.markdown(f"#### 💾 {t('Eski Verilerim', 'My Data')}")
    veri_rows = ([{"tip": "favori", "oyuncu": x, "etiket": ""} for x in fav]
                 + [{"tip": "etiket", "oyuncu": k, "etiket": v} for k, v in etk_dolu.items()])
    if veri_rows:
        csv = pd.DataFrame(veri_rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(t("⬇️ Verilerimi indir (CSV)", "⬇️ Download my data (CSV)"),
                           csv, f"{ku}_verilerim.csv", width="content")
    else:
        st.caption(t("Dışa aktarılacak veri yok.", "No data to export yet."))

    # ── İletişim ──
    st.markdown("---")
    if st.button(t("📬 İletişim / Destek", "📬 Contact / Support"), type="primary"):
        st.session_state["sayfa"] = "iletisim"
        st.rerun()


# ─── Tutarlı "← Ana Sayfa" geri butonu (tüm tam-sayfa görünümlerde) ───────────
def geri_ana_butonu(key: str):
    _gc = st.columns([1.3, 4, 1.3])
    with _gc[0]:
        if st.button(t("← Ana Sayfa", "← Home"), key=key, width="stretch"):
            _dil_koru = st.query_params.get("dil", "")
            st.query_params.clear()
            if _dil_koru:
                st.query_params["dil"] = _dil_koru
            st.session_state["sayfa"] = "ana"
            st.rerun()


# ─── ÖDEME / YÜKSELTME (manuel havale akışı) ──────────────────────────────────
# Havale bilgileri secrets.toml > [odeme]'den okunur (IBAN repoda DEĞİL). Yoksa placeholder.
_PLAN_FIYAT = {"basic": ("Basic", "499 €"), "pro": ("Pro", "999 €"), "premium": ("Premium", "1.999 €")}


def _odemeler_ws():
    try:
        import gspread
        from google.oauth2.service_account import Credentials as GCredentials
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = dict(st.secrets["gcp_service_account"]); creds_info["type"] = "service_account"
        creds = GCredentials.from_service_account_info(creds_info, scopes=scopes)
        gc = gspread.authorize(creds); sh = gc.open_by_key(GSHEET_ID)
        try:
            return sh.worksheet("Odemeler")
        except Exception:
            ws = sh.add_worksheet(title="Odemeler", rows=5000, cols=6)
            ws.update([["kullanici", "plan", "tutar", "tarih", "durum", "not"]])
            return ws
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def odemeler_yukle() -> list:
    """Ödeme bildirimleri (admin için). 2 dk cache; bildirim/onay sonrası .clear()."""
    ws = _odemeler_ws()
    if ws is None:
        return []
    try:
        return [dict(r) for r in ws.get_all_records()]
    except Exception:
        return []


def odeme_bildir(kullanici: str, plan: str, not_: str = "") -> bool:
    ws = _odemeler_ws()
    if ws is None:
        return False
    try:
        from datetime import datetime
        _ad, fiyat = _PLAN_FIYAT.get(plan, (plan, ""))
        ws.append_row([(kullanici or "").strip().lower(), plan, fiyat,
                        datetime.now().strftime("%Y-%m-%d %H:%M"), "beklemede", (not_ or "").strip()])
        odemeler_yukle.clear()
        return True
    except Exception:
        return False


def odeme_durum_guncelle(kullanici: str, plan: str, tarih: str, durum: str) -> bool:
    """Bir ödeme bildirimini (kullanici+plan+tarih) bulup durum kolonunu günceller."""
    ws = _odemeler_ws()
    if ws is None:
        return False
    try:
        ku = (kullanici or "").strip().lower()
        for i, r in enumerate(ws.get_all_records(), start=2):
            if (str(r.get("kullanici", "")).strip().lower() == ku
                    and str(r.get("plan", "")) == plan and str(r.get("tarih", "")) == tarih):
                ws.update_cell(i, 5, durum)   # durum = E kolonu
                odemeler_yukle.clear()
                return True
    except Exception:
        pass
    return False


def render_yukselt():
    """Üyelik yükseltme (manuel havale) sayfası — plan + havale bilgileri + 'ödedim' bildirimi."""
    _PLANLAR = ["basic", "pro", "premium"]
    _plan = st.session_state.get("yukselt_plan", "pro")
    if _plan not in _PLANLAR:
        _plan = "pro"
    _ad, _fiyat = _PLAN_FIYAT[_plan]
    st.markdown(f"## 💳 {t('Üyelik Yükselt', 'Upgrade Membership')}")

    _sec = st.radio(t("Plan seç", "Choose plan"), _PLANLAR,
                    index=_PLANLAR.index(_plan), horizontal=True,
                    format_func=lambda p: f"{_PLAN_FIYAT[p][0]} · {_PLAN_FIYAT[p][1]}",
                    key="yukselt_plan_sec")
    if _sec != _plan:
        st.session_state["yukselt_plan"] = _sec
        st.rerun()
    _ad, _fiyat = _PLAN_FIYAT[_sec]

    st.markdown(
        f"<div style='background:linear-gradient(135deg,#0d2b1e,#1a1f36);border:2px solid #1db954;"
        f"border-radius:14px;padding:18px 22px;margin:6px 0 14px;'>"
        f"<div style='color:#1db954;font-weight:800;font-size:0.8rem;letter-spacing:1px;'>"
        f"{_ad.upper()} {t('PAKET','PLAN')}</div>"
        f"<div style='color:#fff;font-size:2rem;font-weight:900;'>{_fiyat}"
        f"<span style='font-size:1rem;color:#8899aa;'> / {t('yıl','yr')}</span></div></div>",
        unsafe_allow_html=True)

    _ku = st.session_state.get("kulup_kullanici", "")
    _ob = _odeme_bilgi()

    # WhatsApp ile hızlı iletişim (numara secrets'ta tanımlıysa) — plan + e-posta önceden dolu
    _wa_mesaj = t(f"Merhaba, {_ad} ({_fiyat}) üyeliği almak istiyorum.",
                  f"Hi, I'd like to get the {_ad} ({_fiyat}) membership.") + (f" {t('E-posta','Email')}: {_ku}" if _ku else "")
    _whatsapp_butonu(_wa_mesaj, "WhatsApp'tan yaz / ödeme bilgisi al", "Message us on WhatsApp")

    # Havale bilgileri
    st.markdown(f"#### 🏦 {t('Havale / EFT Bilgileri', 'Bank Transfer Details')}")
    if _ob["aktif"]:
        _aciklama = _ku or t("e-posta adresin", "your email")
        st.markdown(
            f"<div style='background:#0e1326;border:1px solid #232a40;border-radius:10px;padding:14px 18px;'>"
            f"<div style='color:#cbd5e1;font-size:0.9rem;line-height:1.9;'>"
            f"<b>{t('Hesap adı','Account name')}:</b> {_ob['hesap_adi']}<br>"
            f"<b>{t('Banka','Bank')}:</b> {_ob['banka']}<br>"
            f"<b>IBAN:</b> <code style='color:#1db954;'>{_ob['iban']}</code><br>"
            f"<b>{t('Tutar','Amount')}:</b> {_fiyat}<br>"
            f"<b>{t('Açıklama','Reference')}:</b> <code>{_aciklama}</code> "
            f"<span style='color:#8899aa;font-size:0.78rem;'>"
            f"({t('mutlaka yaz — ödemeni eşleştirmek için','required — to match your payment')})</span>"
            f"</div></div>", unsafe_allow_html=True)
    else:
        st.info(t("Havale bilgileri yakında eklenecek. Şimdilik 📬 İletişim'den ulaşabilir ya da "
                  "aşağıdan ilgini bildirebilirsin; sana ödeme bilgilerini ulaştıralım.",
                  "Bank details coming soon. For now use 📬 Contact, or register your interest below "
                  "and we'll send you payment details."))

    # Ödedim bildirimi (giriş gerekli)
    st.markdown(f"#### ✅ {t('Ödemeni Bildir', 'Report Your Payment')}")
    if not st.session_state.get("kulup_giris"):
        st.warning(t("Ödemeni bildirmek için önce giriş yap veya kayıt ol (sağ üst 🔐).",
                     "Log in or sign up to report your payment (🔐 top right)."))
        return
    with st.form("odeme_bildir_form", clear_on_submit=True):
        _not = st.text_input(t("Not / referans (opsiyonel)", "Note / reference (optional)"),
                             placeholder=t("ör. havale referans no, gönderen ad", "e.g. transfer ref, sender name"))
        _gonder = st.form_submit_button(
            t("✅ Havale/EFT yaptım — bildir", "✅ I made the transfer — notify"),
            type="primary", width="stretch")
    if _gonder:
        if odeme_bildir(_ku, _sec, _not):
            st.success(t("Bildirimin alındı! Ödemeni kontrol edip kademeni en kısa sürede aktive edeceğiz. "
                         "Aktifleşince Profilim'de görürsün.",
                         "Got it! We'll verify your payment and activate your tier shortly. "
                         "You'll see it in My Profile."))
            st.balloons()
        else:
            st.error(t("Bildirim kaydedilemedi, lütfen sonra tekrar dene ya da 📬 İletişim.",
                       "Could not save the notification, please try again later or 📬 Contact."))


if st.session_state["sayfa"] == "yukselt":
    geri_ana_butonu("geri_yukselt")
    render_yukselt()
    st.stop()

if st.session_state["sayfa"] == "profil":
    geri_ana_butonu("geri_profil")
    render_profil()
    st.stop()

if st.session_state["sayfa"] == "hakkinda":
    geri_ana_butonu("geri_hakkinda")
    render_hakkinda_icerik()
    st.stop()

# ─── İLETİŞİM SAYFASI ─────────────────────────────────────────────────────────
if st.session_state["sayfa"] == "iletisim":
    geri_ana_butonu("geri_iletisim")
    st.markdown(f"""
    <div style='max-width:600px;margin:0 auto;padding:10px 0 40px;'>
    <h2 style='color:#1db954;margin-bottom:6px;'>{t("İletişim", "Contact")}</h2>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Öneri, hata bildirimi veya iş birliği için bize ulaşabilirsiniz.",
       "Reach us for suggestions, bug reports or collaboration.")}
    </p>
    <div style='background:#1a1f36;border-radius:12px;padding:24px;border-left:4px solid #1db954;margin-top:16px;'>
      <div style='color:#8899aa;font-size:13px;margin-bottom:8px;'>{t("📧 E-posta", "📧 E-mail")}</div>
      <div style='color:#fff;font-size:15px;font-weight:600;'>mehmetbarandanis@gmail.com</div>
      <div style='color:#8899aa;font-size:13px;margin-top:20px;margin-bottom:8px;'>{t("🌐 Sosyal Medya", "🌐 Social Media")}</div>
      <div style='display:flex;gap:10px;flex-wrap:wrap;'>
        <a href='https://www.instagram.com/celebiyigit/' target='_blank'
           style='display:inline-flex;align-items:center;gap:7px;text-decoration:none;
           background:#0f1117;border:1px solid #2a3146;border-radius:8px;
           padding:8px 14px;color:#e9d5ff;font-size:14px;font-weight:600;
           transition:border-color .15s;'>
          📸 Instagram <span style='color:#8899aa;font-weight:400;'>@celebiyigit</span>
        </a>
        <a href='https://x.com/yiitche' target='_blank'
           style='display:inline-flex;align-items:center;gap:7px;text-decoration:none;
           background:#0f1117;border:1px solid #2a3146;border-radius:8px;
           padding:8px 14px;color:#e2e8f0;font-size:14px;font-weight:600;
           transition:border-color .15s;'>
          𝕏 <span style='color:#8899aa;font-weight:400;'>@yiitche</span>
        </a>
      </div>
    </div>
    <p style='color:#505870;font-size:12px;margin-top:28px;'>
    {t("Veri hatası veya eksik oyuncu bildirimleri için lütfen oyuncu adı ve doğru bilgiyi içeren bir mesaj gönderin. En kısa sürede güncelliyoruz.",
       "For data errors or missing players, please send a message with the player name and correct info. We update as soon as possible.")}
    </p>
    </div>
    """, unsafe_allow_html=True)
    _wa_orta = st.columns([1, 2, 1])[1]
    with _wa_orta:
        _whatsapp_butonu(t("Merhaba, Women's Football Scouting hakkında bilgi almak istiyorum.",
                           "Hi, I'd like to get info about Women's Football Scouting."),
                         "WhatsApp'tan yaz", "Message us on WhatsApp")
    st.stop()

# ─── TALEP / DANIŞMANLIK SAYFASI ─────────────────────────────────────────────
if st.session_state["sayfa"] == "talep":
    geri_ana_butonu("geri_talep")
    # Hero
    st.markdown(f"""
    <div style="background:linear-gradient(100deg,#08160ff5 0%,#0f3d2ee0 44%,#1a5c4399 100%),
        url('app/static/b1.jpg') center 30%/cover no-repeat;border-radius:16px;
        padding:24px 30px;border-left:5px solid #1db954;margin-bottom:22px;overflow:hidden;">
      <div style='display:inline-block;background:#29b6f622;border:1px solid #29b6f6;
           color:#29b6f6;border-radius:6px;padding:2px 10px;font-size:0.66rem;
           font-weight:800;letter-spacing:0.1em;margin-bottom:8px;'>
        🔹 {t("BASIC ÜYELİK KAPSAMINDA","INCLUDED IN BASIC")}</div>
      <h1 style='font-size:1.5rem;margin:0 0 6px;color:#fff;'>{t("⚽ Kadronu birlikte kuralım", "⚽ Let's build your squad together")}</h1>
      <p style='color:#a7f3d0;font-size:0.95rem;line-height:1.6;margin:0;'>
      {t("Talep gönderme ve danışmanlık Basic üyeliğe dahildir. Scouting ve kadro planlamada veri + saha gözü birleşiyor — kulübüne özel danışmanlık.",
         "Sending requests and consultancy are included in Basic. Data and on-field insight combine in scouting and squad planning — consultancy tailored to your club.")}</p>
    </div>
    """, unsafe_allow_html=True)

    # Hizmet paketleri
    st.markdown(t("##### Hizmetler", "##### Services"))
    _paketler = [
        ("📋", t("Oyuncu Raporu", "Player Report"), t("Tek oyuncu", "Single player"),
         t("Hedeflediğin oyuncu için derinlemesine analiz: kariyer, güçlü/zayıf yönler, uygunluk ve fiyat öngörüsü.",
           "In-depth analysis of your target player: career, strengths/weaknesses, fit and price estimate.")),
        ("🎯", t("Mevki Tarama", "Position Scan"), t("Mevki bazlı", "By position"),
         t("Belirli bir mevkiye bütçene ve oyun stiline uygun en iyi adayların kısa listesi + kıyas.",
           "Shortlist of the best candidates for a position matching your budget and play style, plus comparison.")),
        ("⚖️", t("Oyuncu Kıyası", "Player Comparison"), t("2-5 oyuncu", "2-5 players"),
         t("Aklındaki birkaç oyuncu arasında veri + scouting gözüyle hangisini almalısın kararı.",
           "Which of the players on your mind to sign, decided with data and scouting insight.")),
        ("🏟️", t("Kadro Kurulumu", "Squad Building"), t("Tam kadro", "Full squad"),
         t("Takımı baştan kurma / yeniden yapılandırma danışmanlığı: mevki mevki hedef havuzu.",
           "Building or rebuilding your team: a target pool position by position.")),
    ]
    _pc = st.columns(2)
    for _i, (_ik, _ad, _et, _ac) in enumerate(_paketler):
        with _pc[_i % 2]:
            st.markdown(f"""
            <div class='hizmet-kart' style='border:1px solid #232a45;border-top:2px solid #1db954;
                border-radius:14px;padding:18px;background:linear-gradient(160deg,#141a2e,#0f1322);
                margin-bottom:14px;min-height:158px;'>
              <div style='font-size:1.6rem;'>{_ik}</div>
              <div style='font-family:Oswald,Sora,sans-serif;font-size:1.1rem;font-weight:700;color:#f1f5f9;margin:6px 0 2px;'>{_ad}</div>
              <div style='color:#1db954;font-size:0.64rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:9px;'>{_et}</div>
              <div style='color:#9fb0c6;font-size:0.84rem;line-height:1.55;'>{_ac}</div>
            </div>""", unsafe_allow_html=True)

    # Akıllı ön-öneri
    st.markdown(t("##### 🔎 Hızlı Ön-Öneri — talep etmeden dene",
                  "##### 🔎 Quick Pre-Suggestion — try before you request"))
    st.caption(t("Kriterini seç, sistem havuzdan anında aday önersin. Detaylı rapor için aşağıdan talep et.",
                 "Pick your criteria and the system suggests candidates instantly. Request a detailed report below."))
    _kat_en = {"Forvet": "Forward", "Orta Saha": "Midfield", "Defans": "Defense", "Kaleci": "Goalkeeper"}
    _yas_en = {"Fark etmez": "Any", "≤21": "≤21", "≤24": "≤24", "≤27": "≤27"}
    _onc_en = {"Gol oranı": "Goal rate", "Asist oranı": "Assist rate",
               "Deneyim (maç)": "Experience (matches)", "Oynama süresi": "Minutes played"}
    _oc1, _oc2, _oc3 = st.columns(3)
    _kat   = _oc1.selectbox(t("Mevki", "Position"), ["Forvet", "Orta Saha", "Defans", "Kaleci"],
                            format_func=lambda x: _kat_en[x] if EN else x, key="on_kat")
    _yas_s = _oc2.selectbox(t("Yaş", "Age"), ["Fark etmez", "≤21", "≤24", "≤27"],
                            format_func=lambda x: _yas_en[x] if EN else x, key="on_yas")
    _onc   = _oc3.selectbox(t("Öncelik", "Priority"), ["Gol oranı", "Asist oranı", "Deneyim (maç)", "Oynama süresi"],
                            format_func=lambda x: _onc_en[x] if EN else x, key="on_onc")
    _yas_max = {"Fark etmez": 0, "≤21": 21, "≤24": 24, "≤27": 27}[_yas_s]
    _oneriler = akilli_oneri(_kat, _yas_max, _onc)
    _oneri_metni = ""
    if _oneriler:
        _oneri_metni = (f"Kriter: {_kat} · {_yas_s} · öncelik {_onc}. Öneriler: "
                        + "; ".join(f"{o['isim']} ({o['yas']}y, {o['gol']}g/{o['mac']}m)" for o in _oneriler))
        for _idx, o in enumerate(_oneriler, 1):
            _uyg = min(99, 75 + int(o["gol_mac"] * 12) + (8 if o["yas"] and o["yas"] <= 21 else 0))
            st.markdown(f"""
            <div style='border:1px solid #1e3a5f;border-radius:10px;padding:12px 16px;
                background:#0f172a;margin-bottom:8px;'>
              <div style='display:flex;justify-content:space-between;align-items:center;'>
                <div style='font-size:1.0rem;font-weight:700;color:#f1f5f9;'>🔒 {t("Aday","Candidate")} #{_idx}</div>
                <div style='background:linear-gradient(90deg,#6366f1,#22c55e);color:#fff;
                    border-radius:20px;padding:2px 10px;font-size:0.72rem;font-weight:700;'>%{_uyg} {t("uygun","fit")}</div>
              </div>
              <div style='color:#94a3b8;font-size:0.78rem;margin:3px 0 6px;'>{o['yas']} {t("yaş","y/o")}
                &nbsp;·&nbsp; <span style='color:#475569;'>{t("isim & kulüp talepte paylaşılır","name & club shared on request")}</span></div>
              <div style='font-size:0.82rem;color:#cbd5e1;'>
                ⚽ <b style='color:#22c55e;'>{o['gol']}</b> {t("gol","goals")} &nbsp;·&nbsp;
                📊 <b>{round(o['gol_mac'],2)}</b> {t("gol/maç","goals/match")} &nbsp;·&nbsp; 🎮 {o['mac']} {t("maç","matches")}</div>
            </div>""", unsafe_allow_html=True)
        st.info(t("💡 Bu otomatik ön-öneri. Oyun stili, fiyat öngörüsü, video analiz ve alternatifler "
                  "için aşağıdan **detaylı talep** oluştur — seçtiğin kriter ve öneriler talebe eklenir.",
                  "💡 This is an automated pre-suggestion. For play style, price estimate, video analysis and "
                  "alternatives, create a **detailed request** below — your criteria and suggestions are attached."))
    else:
        st.warning(t("Bu kritere uygun aday bulunamadı, filtreyi gevşetmeyi dene.",
                     "No candidate matched this criteria, try loosening the filter."))

    # Talep formu
    st.markdown(t("##### 📨 Detaylı Talep", "##### 📨 Detailed Request"))
    _DENEME_TIP = "🎁 2 günlük ücretsiz deneme"
    _tip_opts = [
        _DENEME_TIP,
        "Belirli bir oyuncu için detaylı rapor",
        "Belirli bir mevkiye oyuncu önerisi",
        "Birkaç oyuncu arasında tercih / kıyas",
        "Takımı baştan kurma danışmanlığı",
    ]
    _tip_en = dict(zip(_tip_opts, [
        "🎁 2-day free trial",
        "Detailed report on a specific player",
        "Player suggestion for a position",
        "Choice / comparison among a few players",
        "Full squad building consultancy",
    ]))
    # Paket sayfasındaki "Deneme Talep Et" butonu deneme tipini ön-seçer
    _tip_idx = 0 if st.session_state.pop("talep_tip_on", None) == "deneme" else 1
    with st.form("talep_form", clear_on_submit=False):
        tip = st.selectbox(t("Talep türü", "Request type"), _tip_opts, index=_tip_idx,
                           format_func=lambda x: _tip_en[x] if EN else x)
        detay = st.text_area(
            t("Detay / açıklama *", "Details / description *"), height=120,
            placeholder=t("Örn: 23 yaş altı sol bek arıyoruz, fiziksel güçlü, bütçe sınırlı...",
                          "e.g. Looking for a left-back under 23, physically strong, limited budget..."))
        _c1, _c2 = st.columns(2)
        isim  = _c1.text_input(t("Ad Soyad *", "Full Name *"))
        kulup = _c2.text_input(t("Kulüp", "Club"))
        email = st.text_input(t("E-posta / İletişim bilgisi *", "E-mail / Contact info *"))
        gonder = st.form_submit_button(t("📨 Talebi Gönder", "📨 Send Request"),
                                       width="stretch", type="primary")
    if gonder:
        _deneme_talebi = (tip == _DENEME_TIP)
        _detay_son = detay.strip() or (t("2 günlük ücretsiz Premium deneme talebi.",
                                         "Request for a 2-day free Premium trial.") if _deneme_talebi else "")
        # Deneme talebinde Detay zorunlu değil
        if not (isim.strip() and email.strip() and (_detay_son if not _deneme_talebi else True)):
            st.error(t("Lütfen Ad Soyad, E-posta ve Detay alanlarını doldurun.",
                       "Please fill in Full Name, E-mail and Details."))
        else:
            with st.spinner(t("Talebiniz gönderiliyor...", "Sending your request...")):
                _k, _m = talep_gonder(tip, isim.strip(), kulup.strip(),
                                      email.strip(), _detay_son, oneri=_oneri_metni)
            if _k or _m:
                st.success(t("✅ Talebiniz alındı! En kısa sürede iletişime geçeceğiz.",
                             "✅ Your request has been received! We'll get back to you shortly."))
                st.balloons()
            else:
                st.warning(t("Talep şu an kaydedilemedi. Lütfen İletişim sayfasındaki e-posta adresinden bize ulaşın.",
                             "Request could not be saved right now. Please reach us via the e-mail on the Contact page."))
    st.caption(t(f"Talepler doğrudan {TALEP_EMAIL} adresine iletilir.",
                 f"Requests are sent directly to {TALEP_EMAIL}."))
    st.stop()

# ─── ALT LİGLER SAYFASI (Süper Lig verisinden TAMAMEN izole) ─────────────────
_ALTLIG_DOSYALAR = {"Kadınlar 1. Ligi": "altlig_1lig.json",
                    "Kadınlar 2. Ligi": "altlig_2lig.json"}

@st.cache_data(ttl=600)
def altlig_yukle(dosya: str):
    yol = _DIZIN / dosya
    if not yol.exists():
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _altlig_puan_df(puan):
    df = pd.DataFrame(puan)
    if df.empty:
        return df
    kolon = ["sira", "takim", "O", "G", "B", "M", "A", "Y", "AV", "P"]
    df = df[[c for c in kolon if c in df.columns]]
    if "sira" in df.columns and "takim" in df.columns:   # sırayı takım adına göm → kart başlığı temiz
        df["takim"] = df["sira"].astype(str) + ". " + df["takim"].astype(str)
        df = df.drop(columns="sira")
    return df.rename(columns={"sira": "#", "takim": t("Takım", "Team")})


# ─── Alt lig/yaş ortak görünümleri (TR Veri'deki gibi, istatistik tabanlı) ───
def _altlig_en_iyiler(oyuncular):
    """En İyiler — birden çok lider tablosu (golcü, dakika, gol/90, ilk11)."""
    if not oyuncular:
        st.caption(t("Veri yok.", "No data."))
        return
    df = pd.DataFrame(oyuncular)
    # Lig maç süresini VERİDEN otomatik tespit et (tam oynayanların dk/maç maksimumu):
    # U17≈90, U15=70, U13=60 → Gol/süre metriği o lige göre doğru olur.
    _dm = [o["toplam_dakika"] / o["mac_sayisi"]
           for o in oyuncular if o.get("mac_sayisi", 0) >= 3 and o.get("toplam_dakika", 0) > 0]
    mac_sure = min(90, int(round(max(_dm)))) if _dm else 90
    _mindk = 5 * mac_sure   # ~5 maç eşiği (gürültüyü ele)
    df["grate"] = df.apply(lambda r: round(r["gol_sayisi"] / r["toplam_dakika"] * mac_sure, 2)
                           if r.get("toplam_dakika", 0) > 0 else 0.0, axis=1)
    st.markdown(f"#### 🌟 {t('En İyiler', 'Top Performers')}")
    kategoriler = [
        ("⚽ " + t("En Golcü", "Top Scorers"),      "gol_sayisi",    lambda v: f"{int(v)}",  0),
        ("⏱️ " + t("En Çok Oynayan", "Most Minutes"), "toplam_dakika", lambda v: f"{int(v)}'", 0),
        (f"🎯 {t('Gol', 'Goals')} / {mac_sure} {t('dk','min')}", "grate", lambda v: f"{v:.2f}", _mindk),
        ("▶️ " + t("En Çok İlk 11", "Most Starts"),   "ilk11_mac",     lambda v: f"{int(v)}",  0),
    ]
    cols = st.columns(2)
    for i, (baslik, kol, fmt, mindk) in enumerate(kategoriler):
        d = df[df["toplam_dakika"] >= mindk] if mindk else df
        top = d.sort_values(kol, ascending=False).head(8)
        satir = ""
        for j, (_, r) in enumerate(top.iterrows(), 1):
            satir += (
                "<div style='display:flex;justify-content:space-between;gap:8px;"
                "padding:4px 0;border-bottom:1px solid #1a1f36;font-size:0.8rem;'>"
                f"<span style='color:#cbd5e1;'><b style='color:#64748b;'>{j}.</b> {r['oyuncu']} "
                f"<span style='color:#64748b;font-size:0.72rem;'>{str(r['takim'])[:16]}</span></span>"
                f"<b style='color:#1db954;white-space:nowrap;'>{fmt(r[kol])}</b></div>")
        cols[i % 2].markdown(
            "<div style='background:#0e1326;border:1px solid #232a40;border-top:3px solid #a855f7;"
            "border-radius:10px;padding:12px 14px;margin-bottom:12px;'>"
            f"<div style='font-weight:700;color:#f1f5f9;margin-bottom:6px;'>{baslik}</div>{satir}</div>",
            unsafe_allow_html=True)
    st.caption(t(f"Gol/{mac_sure}: en az {_mindk} dk ({mac_sure} dk'lık lig) oynayanlar arasında.",
                 f"Goals/{mac_sure}: among players with ≥{_mindk} min (this league plays {mac_sure}-min matches)."))


def _altlig_takim_analizi(oyuncular):
    """Takım Analizi — takım bazında kadro/gol/en golcü/kart agregasyonu."""
    if not oyuncular:
        st.caption(t("Veri yok.", "No data."))
        return
    df = pd.DataFrame(oyuncular)
    st.markdown(f"#### 🏟️ {t('Takım Analizi', 'Team Analysis')}")
    agg = df.groupby("takim").agg(kadro=("oyuncu", "count"), gol=("gol_sayisi", "sum"),
                                  sari=("sari_kart", "sum"), kirmizi=("kirmizi_kart", "sum")).reset_index()
    eng = df.loc[df.groupby("takim")["gol_sayisi"].idxmax(), ["takim", "oyuncu", "gol_sayisi"]]
    eng_map = {r["takim"]: f"{r['oyuncu']} ({int(r['gol_sayisi'])})" for _, r in eng.iterrows()}
    grup_map = dict(zip(df["takim"], df["grup"]))
    agg["en_golcu"] = agg["takim"].map(eng_map)
    agg["grup"] = agg["takim"].map(grup_map)
    agg = agg.sort_values("gol", ascending=False)
    show = agg[["takim", "grup", "kadro", "gol", "en_golcu", "sari", "kirmizi"]].rename(columns={
        "takim": t("Takım", "Team"), "grup": t("Grup", "Grp"), "kadro": t("Kadro", "Squad"),
        "gol": t("Toplam Gol", "Goals"), "en_golcu": t("En Golcü", "Top Scorer"),
        "sari": "🟨", "kirmizi": "🟥"})
    df_tablo(show)
    st.caption(t(f"{len(show)} takım · toplam gola göre sıralı.", f"{len(show)} teams · sorted by total goals."))


def render_altlig():
    st.markdown(f"## 🥈 {t('Alt Ligler', 'Lower Leagues')}")
    st.caption(t("TFF Kadınlar alt ligleri · gruplar, puan durumu ve oyuncu istatistikleri — Süper Lig verisinden tamamen ayrı.",
                 "TFF Women's lower leagues · groups, standings & player stats — fully separate from the Super League."))
    _ligler = list(_ALTLIG_DOSYALAR.keys())
    _lig = (st.selectbox(t("Lig", "League"), _ligler, key="altlig_lig")
            if len(_ligler) > 1 else _ligler[0])
    data = altlig_yukle(_ALTLIG_DOSYALAR[_lig])
    if not data:
        st.info(t("Veri henüz hazır değil — yakında eklenecek.", "Data not ready yet — coming soon."))
        return

    gruplar = data.get("gruplar", {})
    _oyuncular = data.get("oyuncular", [])
    _ad = _lig.replace("Kadınlar ", "").upper()
    _oy_lbl = t("👤 Oyuncular", "👤 Players")
    _pd_lbl = t("🏆 Puan Durumu", "🏆 Standings")
    _ei_lbl = t("🌟 En İyiler", "🌟 Top Performers")
    _ta_lbl = t("🏟️ Takımlar", "🏟️ Teams")
    _kr_lbl = t("👑 Gol Kraliçesi", "👑 Top Scorers")
    secenekler = []
    if _oyuncular:
        secenekler += [_oy_lbl, _ei_lbl, _ta_lbl]
    if gruplar:
        secenekler.append(_pd_lbl)
    if data.get("gol_kralicesi"):
        secenekler.append(_kr_lbl)
    secim = st.radio("g", secenekler, horizontal=True,
                     label_visibility="collapsed", key="altlig_gorunum")

    # Lig geneli görünümler
    if secim == _ei_lbl:
        _altlig_en_iyiler(_oyuncular)
        return
    if secim == _ta_lbl:
        _altlig_takim_analizi(_oyuncular)
        return
    if secim == _kr_lbl:
        st.markdown(f"#### 👑 {t('Gol Kraliçesi — Resmi TFF Tablosu', 'Top Scorers — Official TFF')}")
        kr = data["gol_kralicesi"]
        krdf = pd.DataFrame([{t("Oyuncu", "Player"): f"{i + 1}. {r['oyuncu']}",
                              t("Takım", "Team"): r["takim"], t("Gol", "Goals"): r["gol"]}
                             for i, r in enumerate(kr)])
        df_tablo(krdf)
        st.caption(t(f"Toplam {len(kr)} golcü · kaynak: tff.org (resmi normal sezon). Oyuncu gol sayıları bu tabloyla + playoff golleriyle uzlaştırılmıştır.",
                     f"{len(kr)} scorers · source: tff.org (official regular season). Player goals reconciled with this table + playoff goals."))
        return

    # Puan Durumu — gruplar yapısal olarak ayrı oynar; her grubun tablosu alt alta.
    if secim == _pd_lbl:
        st.markdown(f"#### 🏆 {t('Puan Durumu', 'Standings')}")
        for g in gruplar:
            puan_df = _altlig_puan_df(gruplar[g].get("puan_durumu", []))
            if not puan_df.empty:
                st.markdown(f"##### {_ad} · {t(f'{g} Grubu', f'Group {g}')}")
                df_tablo(puan_df)
        return

    # 👤 Oyuncular — TÜM oyuncular (A/B grup ayrımı YOK), arama + profil (detay kartı)
    st.markdown(
        f"<div style='display:inline-block;background:#1b1540;border:1px solid #4c3a8f;"
        f"border-left:3px solid #a855f7;border-radius:6px;padding:4px 12px;margin:4px 0 10px;"
        f"font-weight:700;color:#e9d5ff;font-size:0.8rem;letter-spacing:0.04em;'>"
        f"{_ad} · {t('TÜM OYUNCULAR','ALL PLAYERS')}</div>", unsafe_allow_html=True)
    _ara = st.text_input(f"🔎 {t('Oyuncu / takım ara', 'Search player / team')}",
                         key="altlig_ara", placeholder=t("İsim veya takım…", "Name or team…"))
    oyuncular = list(_oyuncular)
    if _ara.strip():
        _q = _ara.strip().lower()
        oyuncular = [o for o in oyuncular
                     if _q in o.get("oyuncu","").lower() or _q in o.get("tum_takimlar","").lower()]
    st.markdown(f"##### 👤 {t('Oyuncular', 'Players')} ({len(oyuncular)})")
    if not oyuncular:
        st.caption(t("Eşleşen oyuncu yok.", "No matching players."))
        return
    _oy_sirali = sorted(oyuncular, key=lambda x: (-x.get("gol_sayisi", 0), -x.get("mac_sayisi", 0)))
    odf = pd.DataFrame([{
        "Oyuncu": o["oyuncu"], "Takım": _takim_kisa(o["takim"]), "Maç": o["mac_sayisi"],
        "Gol": o["gol_sayisi"], "G/Maç": o["gol_ort"], "Dakika": o["toplam_dakika"],
        "Sarı": o["sari_kart"], "Kırmızı": o["kirmizi_kart"],
    } for o in _oy_sirali])

    col_l, col_r = st.columns([5, 4], gap="medium")
    with col_l:
        secim_df = st.dataframe(
            odf, width="stretch", hide_index=True, height=520,
            on_select="rerun", selection_mode="single-row", key="altlig_oyuncu_liste",
            column_config={
                "Oyuncu":  st.column_config.TextColumn(t("Oyuncu", "Player"), width="medium"),
                "Takım":   st.column_config.TextColumn(t("Takım", "Team"), width="small"),
                "Maç":     st.column_config.NumberColumn(t("Maç", "M"), format="%d", width="small"),
                "Gol":     st.column_config.NumberColumn(t("Gol", "G"), format="%d", width="small"),
                "G/Maç":   st.column_config.NumberColumn("G/M", format="%.2f", width="small"),
                "Dakika":  st.column_config.NumberColumn(t("Dk", "Min"), format="%d", width="small"),
                "Sarı":    st.column_config.NumberColumn("🟨", format="%d", width="small"),
                "Kırmızı": st.column_config.NumberColumn("🟥", format="%d", width="small"),
            })
    with col_r:
        _sel = secim_df.selection.rows if hasattr(secim_df, "selection") else []
        if not _sel:
            st.markdown(
                f"<div style='color:#64748b;padding:34px 10px;text-align:center;font-size:0.9rem;'>"
                f"👈 {t('Bir oyuncuya tıkla — detayları burada açılır', 'Click a player — details open here')}</div>",
                unsafe_allow_html=True)
        else:
            o = _oy_sirali[_sel[0]] if _sel[0] < len(_oy_sirali) else None
            if o:
                gf, gh, gp = o.get("gol_ayak", 0), o.get("gol_kafa", 0), o.get("penalti_gol", 0)
                ilk11, yedek = o.get("ilk11_mac", 0), o.get("yedek_mac", 0)
                _pl = o.get("playoff_gol", 0)
                _pl_not = (f" · 🏅 {_pl} {t('playoff golü','playoff goal' + ('s' if _pl != 1 else ''))}") if _pl else ""
                _kut = "".join(
                    f"<div style='flex:1;min-width:58px;background:#11162a;border-radius:6px;padding:8px;text-align:center;'>"
                    f"<div style='font-size:1.05rem;font-weight:800;color:#1db954;'>{v}</div>"
                    f"<div style='font-size:0.58rem;color:#64748b;'>{lbl}</div></div>"
                    for v, lbl in [(o['mac_sayisi'], t('MAÇ', 'M')), (o['gol_sayisi'], t('GOL', 'G')),
                                   (o['toplam_dakika'], t('DAKİKA', 'MIN')), (f"{ilk11}/{yedek}", t('İLK11/YDK', 'ST/SUB'))])
                st.markdown(
                    f"<div style='background:#0e1326;border:1px solid #232a40;border-top:3px solid #a855f7;"
                    f"border-radius:10px;padding:14px 16px;'>"
                    f"<div style='font-size:1.05rem;font-weight:800;color:#fff;'>{o['oyuncu']}</div>"
                    f"<div style='color:#8899aa;font-size:0.8rem;margin:3px 0 10px;'>🏟 {_takim_kisa(o['tum_takimlar'])}</div>"
                    f"<div style='display:flex;gap:8px;flex-wrap:wrap;'>{_kut}</div>"
                    f"<div style='margin-top:10px;font-size:0.76rem;color:#9aa6ba;'>"
                    f"⚽ {t('Gol kırılımı', 'Goal breakdown')}: {gf} {t('ayak', 'foot')} · {gh} {t('kafa', 'head')} · "
                    f"{gp} {t('penaltı', 'pen')}{_pl_not} · 🟨 {o['sari_kart']} · 🟥 {o['kirmizi_kart']}</div></div>",
                    unsafe_allow_html=True)
    st.caption(t("⚠️ Alt lig verisi TFF maç detaylarından derlenir; eksik olabilir. Süper Lig oyuncularıyla karışmaz.",
                 "⚠️ Lower-league data compiled from TFF match details; may be incomplete. Never mixed with Super League players."))


if st.session_state.get("sayfa") == "altlig":
    geri_ana_butonu("geri_altlig")
    render_altlig()
    st.stop()


# ─── ALT YAŞLAR (gelişim ligleri — toplu liste, puan durumu YOK) ─────────────
_ALTYAS_DOSYALAR = {  # kategori → veri dosyası (sırayla sekme/seçici olur)
    "U17 Kızlar": "altlig_u17.json",   # kaynak: TFF U17 Gelişim Ligi
    "U15 Kızlar": "altlig_u15.json",   # kaynak: tffistanbul.org (İstanbul U15 Genç Kızlar A/B/C)
    "U13 Kızlar": "altlig_u13.json",   # kaynak: tffistanbul.org (İstanbul U13 Minik Kızlar 1/2/3)
}

def render_altyas():
    st.markdown(f"## 🌱 {t('Alt Yaşlar', 'Youth Leagues')}")
    st.caption(t("Gelişim ligleri · toplu oyuncu listesi ve istatistikleri — üst seviye verisinden tamamen ayrı.",
                 "Development leagues · consolidated player list & stats — fully separate from senior data."))
    _ligler = list(_ALTYAS_DOSYALAR.keys())
    # Kategori seçimi GÖRÜNÜR kutucuklarla (yatay radio) — kullanıcı U13/U15'in
    # varlığını dropdown'a tıklamadan görsün.
    _lig = (st.radio(t("Kategori", "Category"), _ligler, horizontal=True, key="altyas_lig")
            if len(_ligler) > 1 else _ligler[0])
    data = altlig_yukle(_ALTYAS_DOSYALAR[_lig])
    if not data:
        st.info(t("Veri henüz hazır değil — lokalde scraper_u17_selenium.py çalıştırılıp eklenecek.",
                  "Data not ready yet — to be generated locally via scraper_u17_selenium.py."))
        return

    _kr_lbl = t("👑 Gol Kraliçesi", "👑 Top Scorers")
    _oy_lbl = t("👤 Oyuncular", "👤 Players")
    _ei_lbl = t("🌟 En İyiler", "🌟 Top Performers")
    _ta_lbl = t("🏟️ Takımlar", "🏟️ Teams")
    secenekler = [_oy_lbl, _ei_lbl, _ta_lbl] + ([_kr_lbl] if data.get("gol_kralicesi") else [])
    secim = st.radio("ay", secenekler, horizontal=True, label_visibility="collapsed", key="altyas_mod")

    if secim == _ei_lbl:
        _altlig_en_iyiler(data.get("oyuncular", []))
        return
    if secim == _ta_lbl:
        _altlig_takim_analizi(data.get("oyuncular", []))
        return

    if secim == _kr_lbl:
        _kr_baslik = (t("Gol Kraliçesi (Resmi TFF Top-10)", "Top Scorers (Official TFF Top-10)")
                      if "U17" in _lig else t("Gol Kraliçesi (İlk 10)", "Top Scorers (Top 10)"))
        st.markdown(f"#### 👑 {_kr_baslik}")
        kr = data["gol_kralicesi"]
        # U17: {oyuncu,takim,gol}; U15/U13: tam oyuncu dict ({...,gol_sayisi}) → ikisini de destekle
        krdf = pd.DataFrame([{t("Oyuncu", "Player"): f"{i + 1}. {r['oyuncu']}",
                              t("Takım", "Team"): r.get("takim", ""),
                              t("Gol", "Goals"): r.get("gol", r.get("gol_sayisi", 0))}
                             for i, r in enumerate(kr)])
        df_tablo(krdf)
        if "U17" in _lig:
            st.caption(t("TFF U17 gelişim ligi yalnızca top-10 golcüyü yayınlıyor.",
                         "TFF U17 development league publishes only the top-10 scorers."))
        else:
            st.caption(t("Lig genelinde ilk 10 golcü.", "Top 10 scorers across the league."))
        return

    oyuncular = data.get("oyuncular", [])
    st.markdown(f"##### 👤 {t('Tüm Oyuncular', 'All Players')} ({len(oyuncular)})")
    _c1, _c2 = st.columns([2, 1])
    _ara = _c1.text_input(t("Ara (oyuncu / takım)", "Search (player / team)"),
                          key="altyas_ara", label_visibility="collapsed",
                          placeholder=t("Oyuncu veya takım ara…", "Search player or team…"))
    _gruplar = sorted({o.get("grup") for o in oyuncular if o.get("grup")})
    _grup_sec = _c2.selectbox(t("Grup", "Group"), [t("Tüm gruplar", "All groups")] + [str(g) for g in _gruplar],
                              key="altyas_grup", label_visibility="collapsed")
    _arl = (_ara or "").lower().strip()
    flt = [o for o in oyuncular
           if (not _arl or _arl in o["oyuncu"].lower() or _arl in o.get("takim", "").lower())
           and (_grup_sec in (t("Tüm gruplar", "All groups"),) or str(o.get("grup")) == _grup_sec)]
    if not flt:
        st.caption(t("Eşleşen oyuncu yok.", "No matching players."))
        return
    odf = pd.DataFrame([{
        "Oyuncu": o["oyuncu"], "Takım": o.get("takim", ""), "Grup": o.get("grup", ""),
        "Maç": o["mac_sayisi"], "Gol": o["gol_sayisi"], "G/Maç": o["gol_ort"],
        "Dakika": o["toplam_dakika"], "Sarı": o["sari_kart"], "Kırmızı": o["kirmizi_kart"],
    } for o in flt]).sort_values(["Gol", "Maç"], ascending=False).reset_index(drop=True)

    col_l, col_r = st.columns([5, 4], gap="medium")
    with col_l:
        _secdf = st.dataframe(
            odf, width="stretch", hide_index=True, height=540,
            on_select="rerun", selection_mode="single-row", key="altyas_liste",
            column_config={
                "Oyuncu":  st.column_config.TextColumn(t("Oyuncu", "Player"), width="medium"),
                "Takım":   st.column_config.TextColumn(t("Takım", "Team"), width="small"),
                "Grup":    st.column_config.NumberColumn(t("Grup", "Grp"), format="%d", width="small"),
                "Maç":     st.column_config.NumberColumn(t("Maç", "M"), format="%d", width="small"),
                "Gol":     st.column_config.NumberColumn(t("Gol", "G"), format="%d", width="small"),
                "G/Maç":   st.column_config.NumberColumn("G/M", format="%.2f", width="small"),
                "Dakika":  st.column_config.NumberColumn(t("Dk", "Min"), format="%d", width="small"),
                "Sarı":    st.column_config.NumberColumn("🟨", format="%d", width="small"),
                "Kırmızı": st.column_config.NumberColumn("🟥", format="%d", width="small"),
            })
    with col_r:
        _sel = _secdf.selection.rows if hasattr(_secdf, "selection") else []
        if not _sel:
            st.markdown(
                f"<div style='color:#64748b;padding:34px 10px;text-align:center;font-size:0.9rem;'>"
                f"👈 {t('Bir oyuncuya tıkla — detayları açılır', 'Click a player — details open')}</div>",
                unsafe_allow_html=True)
        else:
            r = odf.iloc[_sel[0]]
            o = next((x for x in flt if x["oyuncu"] == r["Oyuncu"] and x.get("takim", "") == r["Takım"]), None)
            if o:
                gf, gh, gp = o.get("gol_ayak", 0), o.get("gol_kafa", 0), o.get("penalti_gol", 0)
                ilk11, yedek = o.get("ilk11_mac", 0), o.get("yedek_mac", 0)
                _kut = "".join(
                    f"<div style='flex:1;min-width:58px;background:#11162a;border-radius:6px;padding:8px;text-align:center;'>"
                    f"<div style='font-size:1.05rem;font-weight:800;color:#1db954;'>{v}</div>"
                    f"<div style='font-size:0.58rem;color:#64748b;'>{lbl}</div></div>"
                    for v, lbl in [(o['mac_sayisi'], t('MAÇ', 'M')), (o['gol_sayisi'], t('GOL', 'G')),
                                   (o['toplam_dakika'], t('DAKİKA', 'MIN')), (f"{ilk11}/{yedek}", t('İLK11/YDK', 'ST/SUB'))])
                st.markdown(
                    f"<div style='background:#0e1326;border:1px solid #232a40;border-top:3px solid #4ade80;"
                    f"border-radius:10px;padding:14px 16px;'>"
                    f"<div style='font-size:1.05rem;font-weight:800;color:#fff;'>{o['oyuncu']}</div>"
                    f"<div style='color:#8899aa;font-size:0.8rem;margin:3px 0 10px;'>🏟 {o.get('tum_takimlar', o.get('takim',''))}"
                    f" · {t('Grup','Group')} {o.get('grup','—')}</div>"
                    f"<div style='display:flex;gap:8px;flex-wrap:wrap;'>{_kut}</div>"
                    f"<div style='margin-top:10px;font-size:0.76rem;color:#9aa6ba;'>"
                    f"⚽ {t('Gol kırılımı', 'Goal breakdown')}: {gf} {t('ayak', 'foot')} · {gh} {t('kafa', 'head')} · "
                    f"{gp} {t('penaltı', 'pen')} · 🟨 {o['sari_kart']} · 🟥 {o['kirmizi_kart']}</div></div>",
                    unsafe_allow_html=True)
    st.caption(t("⚠️ Gelişim ligi verisi TFF maç detaylarından derlenir; eksik olabilir. Üst seviye oyuncularıyla karışmaz.",
                 "⚠️ Development-league data compiled from TFF match details; may be incomplete. Never mixed with senior players."))


if st.session_state.get("sayfa") == "altyas":
    geri_ana_butonu("geri_altyas")
    render_altyas()
    st.stop()


# ─── SAYGI KUŞAĞI (görsel + saygı metni — içerik JSON'dan) ───────────────────
def saygi_yukle():  # minik dosya — cache yok ki güncelleme anında yansısın
    yol = _DIZIN / "saygi_kusagi.json"
    if not yol.exists():
        return []
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def render_saygi():
    st.markdown(f"## 🎗️ {t('Saygı Kuşağı', 'Hall of Respect')}")
    st.caption(t("Kadın futboluna emek verenlere, hak edenlere saygı.",
                 "A tribute to those who give to — and earn respect in — women's football."))
    girisler = saygi_yukle()
    if not girisler:
        st.info(t("İçerik yakında eklenecek — görseller ve metinler hazırlanıyor.",
                  "Content coming soon — images and texts are being prepared."))
        return
    for e in girisler:
        with st.container(border=True):
            _g = e.get("gorsel", "")
            if _g and not _g.lower().startswith("http"):
                _yerel = _DIZIN / _g
                _g = str(_yerel) if _yerel.exists() else ""
            if _g:
                c1, c2 = st.columns([1, 3], gap="medium")
                with c1:
                    try:
                        st.image(_g, width="stretch")
                    except Exception:
                        st.caption("🖼️")
                _hedef = c2
            else:
                _hedef = st.container()
            with _hedef:
                st.markdown(f"<div style='font-size:1.12rem;font-weight:800;color:#f1f5f9;"
                            f"margin:2px 0 2px;'>{e.get('baslik', '')}</div>", unsafe_allow_html=True)
                if e.get("alt_baslik"):
                    st.markdown(f"<div style='color:#a855f7;font-weight:600;font-size:0.85rem;"
                                f"margin:-6px 0 8px;'>{e['alt_baslik']}</div>", unsafe_allow_html=True)
                if e.get("metin"):
                    st.markdown(
                        f"<div style='color:#cbd5e1;font-size:0.92rem;line-height:1.7;'>{e['metin']}</div>",
                        unsafe_allow_html=True)
    st.caption(t("📨 Saygı Kuşağı'na öneri için İletişim'den ulaşabilirsiniz.",
                 "📨 Suggest an entry via the Contact page."))


if st.session_state.get("sayfa") == "saygi":
    geri_ana_butonu("geri_saygi")
    render_saygi()
    st.stop()

# ─── SCOUTİNG SAYFASI (Premium kademe) ───────────────────────────────────────
if st.session_state.get("sayfa") == "scouting":
    geri_ana_butonu("geri_scouting")
    if tier_yeterli("premium"):
        _sayfa_banner("b2.jpg", f"🔎 {t('Scouting Havuzu','Scouting Pool')}",
            t("Yabancı oyuncu kurasyonu · 2026-27 kadro planlama · SoccerDonna verileri ile zenginleştirilmiş",
              "Foreign player curation · 2026-27 squad planning · enriched with SoccerDonna data"))

        # Roster kaynağı: Sco 🌍 sekmesi (scout_kadro_raporlar.json — commit'li snapshot).
        # Eşleşme anahtarı "Tam İsmi" = Sco 🌍'daki "Oyuncu Adı"; SD + scout raporu isimle eşleşir.
        _kadro_roster = scout_kadro_yukle()
        sc_df = pd.DataFrame(
            [{"Tam İsmi": _isim, "Vatandaşlık": _v.get("vatandaslik", "")}
             for _isim, _v in _kadro_roster.items()]
        )
        sd_data = scouting_sd_yukle()
        leistung_data = scouting_leistung_yukle()
        detay_data = scouting_detay_yukle()
        _sl_kullanici = st.session_state.get("kulup_kullanici", "admin")
        _sl_liste     = shortlist_kullanici(_sl_kullanici)
        _etiket_liste = etiket_kullanici(_sl_kullanici)

        if sc_df.empty:
            st.warning(t("Google Sheets'e bağlanılamadı veya liste boş.", "Could not connect to Google Sheets or the list is empty."))
        else:
            # ── SCOUT PRO REDESIGN ────────────────────────────────────────────
            isim_col = "Tam İsmi" if "Tam İsmi" in sc_df.columns else sc_df.columns[0]
            vat_col  = "Vatandaşlık" if "Vatandaşlık" in sc_df.columns else None

            # SD'den mevki → normalize eşleme
            _SD_MEVKI_NORM = {
                "Goalkeeper":                    "Kaleci",
                "Defence - Fullback, right":     "Sağ Bek",
                "Defender - Right Back":         "Sağ Bek",
                "Defence - Fullback, left":      "Sol Bek",
                "Defender - Left Back":          "Sol Bek",
                "Defence - Centre Back":         "Stoper",
                "Defender - Centre Back":        "Stoper",
                "Defence":                       "Defans",
                "Defender":                      "Defans",
                "Midfield - Defensive Midfield": "Savunmacı Orta Saha",
                "Midfield - Central Midfield":   "Merkez Orta Saha",
                "Midfield - Midfield, left":     "Sol Kanat",
                "Midfield - Midfield, right":    "Sağ Kanat",
                "Midfield - Attacking Midfield": "Hücumcu Orta Saha",
                "Midfield - Left Wing":          "Sol Kanat",
                "Midfield - Right Wing":         "Sağ Kanat",
                "Midfield":                      "Orta Saha",
                "Striker - Centre Forward":      "Santrafor",
                "Striker - Second Striker":      "İkinci Santrafor",
                "Striker - Left Wing":           "Sol Kanat Forvet",
                "Striker - Right Wing":          "Sağ Kanat Forvet",
                "Striker - Attacking Midfield":  "Hücumcu Orta Saha",
                "Striker":                       "Forvet",
            }

            # SD doğum yılı aralığı
            yillar = []
            for v in sd_data.values():
                dob = v.get("Date of birth", "")
                if dob and len(dob) >= 4:
                    try: yillar.append(int(dob[-4:]))
                    except: pass
            yil_min = min(yillar) if yillar else 1990
            yil_max = max(yillar) if yillar else 2008

            _sc_tumu    = t("Tümü", "All")
            _sc_ayak_en = {"Tümü": "All", "right": "Right", "left": "Left", "both": "Both"}

            # ── Scout Pro: Başlık ─────────────────────────────────────────────
            st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
     margin:12px 0 14px;padding:10px 18px;background:#111118;
     border:1px solid #2a2a38;border-radius:10px;">
  <div style="display:flex;align-items:center;gap:10px;">
    <span style="color:#7c3aed;font-size:1.05rem;">⚡</span>
    <span style="font-size:0.85rem;font-weight:700;color:#e2e8f0;">
      {t("Scout Havuzu","Scout Pool")}
    </span>
    <span style="font-size:0.70rem;background:#7c3aed22;color:#a78bfa;
         border:1px solid #7c3aed44;border-radius:99px;padding:2px 9px;font-weight:700;">
      {len(sc_df)} {t("oyuncu","players")}
    </span>
  </div>
  <div style="font-size:0.74rem;color:#64748b;">
    ⭐ <b style="color:#fbbf24;">{len(_sl_liste)}</b> shortlist
  </div>
</div>""", unsafe_allow_html=True)

            # ── Scout Pro: Sekme seçimi ───────────────────────────────────────
            _ONERI_TAB  = t("📥 Öneri Merkezi", "📥 Recommendations")
            _TAB_OPTS   = [t("Tüm Oyuncular", "All Players"), t("Shortlist", "Shortlist"), _ONERI_TAB]
            _sc_tab_sel = st.radio(t("Görünüm", "View"), _TAB_OPTS, horizontal=True,
                                   key="sc_tab_radio", label_visibility="collapsed")
            sadece_sl   = (_sc_tab_sel == t("Shortlist", "Shortlist"))

            # ── Öneri Merkezi sekmesi: tam genişlik panosu + erken çıkış ──────
            # (Scouting sayfası zaten aşağıda st.stop() ile bitiyor; burada da
            #  render edip durmak filtre/tablo bloğunu temiz şekilde atlar.)
            if _sc_tab_sel == _ONERI_TAB:
                render_oneri_merkezi(_sl_kullanici)
                st.stop()

            # ── Scout Pro: İki sütun düzeni (sidebar + ana alan) ─────────────
            sc_sb, sc_main_col = st.columns([1, 4.6], gap="medium")

            # ── Sol Kenar: Filtreler ──────────────────────────────────────────
            with sc_sb:
                st.markdown(
                    f"<div style='font-size:0.68rem;font-weight:700;color:#7c3aed;"
                    f"text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;'>"
                    f"🔧 {t('Filtreler','Filters')}</div>",
                    unsafe_allow_html=True)

                isim_q = st.text_input(
                    f"👤 {t('Oyuncu Ara', 'Search Player')}",
                    placeholder=t("İsim yaz…", "Type a name…"), key="sc_isim")

                if vat_col:
                    vat_opts = sorted(sc_df[vat_col].dropna().replace("", "").unique().tolist())
                    vat_sec  = st.selectbox(
                        f"🌍 {t('Ülke', 'Country')}",
                        [_sc_tumu] + [v for v in vat_opts if v],
                        format_func=lambda x: x if x == _sc_tumu else ulke_goster(x),
                        key="sc_vat")
                else:
                    vat_sec = _sc_tumu

                sc_kategori = st.selectbox(
                    f"📌 {t('Mevki', 'Position')}",
                    [_sc_tumu] + list(_MEVKI_DETAY.keys()),
                    format_func=mevki_goster, key="sc_kat")

                sc_detay_opts = ([_sc_tumu] +
                    (_MEVKI_DETAY.get(sc_kategori, []) if sc_kategori != _sc_tumu else []))
                sc_detay = st.selectbox(
                    f"↳ {t('Alt Mevki', 'Sub-Position')}", sc_detay_opts,
                    format_func=mevki_goster, key="sc_detay",
                    disabled=(sc_kategori == _sc_tumu))

                # Rol filtresi (scout_kadro verisi — ~267 oyuncuda dolu)
                _rol_opts = sorted({_v.get("rol", "") for _v in _kadro_roster.values()
                                    if _v.get("rol")})
                sc_rol = st.selectbox(
                    f"🎭 {t('Rol', 'Role')}", [_sc_tumu] + _rol_opts,
                    format_func=lambda x: x if x == _sc_tumu else scout_rol_goster(x),
                    key="sc_rol")

                yil_range = st.slider(
                    f"📅 {t('Doğum Yılı', 'Birth Year')}",
                    yil_min, yil_max, (yil_min, yil_max), key="sc_yil")

                ayak_sec = st.selectbox(
                    f"🦶 {t('Ayak', 'Foot')}",
                    [_sc_tumu, "right", "left", "both"], key="sc_ayak",
                    format_func=lambda x: (
                        (_sc_ayak_en.get(x, x) if x != _sc_tumu else _sc_tumu) if EN else x))

                # ── 📡 Transfer Radar: sözleşme bitiş yakınlığı ──────────────────
                # Sözleşmesi yakında biten = düşük bonservis / bedava fırsat.
                _transfer_etiket = {
                    _sc_tumu: t("Fark etmez", "Any"),
                    "exp6":  t("🔴 ≤ 6 ay (bedavaya çok yakın)", "🔴 ≤ 6 mo (near free)"),
                    "exp12": t("🟡 ≤ 12 ay", "🟡 ≤ 12 mo"),
                    "exp18": t("🟢 ≤ 18 ay", "🟢 ≤ 18 mo"),
                }
                transfer_sec = st.selectbox(
                    f"📡 {t('Transfer Radar', 'Transfer Radar')}",
                    [_sc_tumu, "exp6", "exp12", "exp18"],
                    format_func=lambda x: _transfer_etiket.get(x, x), key="sc_transfer",
                    help=t("Sözleşmesi bitmeye yakın oyuncular — düşük bonservis veya bedava transfer fırsatları.",
                           "Players whose contracts end soon — low-fee or free transfer opportunities."))

                # ── 🇹🇷 TR Görüşü: oyuncunun Türkiye'ye gelme isteği ─────────────
                _TR_SIRA = ["Çok İstekli", "İstekli (Şartlar?)", "İstekli",
                            "Nötr (Şartlar?)", "İsteksiz (Şartlar?)", "İsteksiz", "Çok İsteksiz"]
                _mevcut_tr = {(_v.get("tr_gorusu") or "").strip()
                              for _v in _kadro_roster.values() if (_v.get("tr_gorusu") or "").strip()}
                _tr_opts = ([x for x in _TR_SIRA if x in _mevcut_tr]
                            + sorted(_mevcut_tr - set(_TR_SIRA)))
                tr_sec = st.selectbox(
                    f"🇹🇷 {t('TR Görüşü', 'TR Stance')}", [_sc_tumu] + _tr_opts,
                    format_func=lambda x: x if x == _sc_tumu else tr_gorus_goster(x),
                    key="sc_trgorus",
                    help=t("Oyuncunun Türkiye'ye gelme isteği (scout görüşü).",
                           "Player's willingness to move to Turkey (scout assessment)."))

                st.markdown("<hr style='border-color:#2a2a38;margin:12px 0;'>",
                            unsafe_allow_html=True)

                with st.expander(f"📊 {t('Veri Kapsama', 'Data Coverage')}"):
                    veri_kapsama_goster(sc_df, isim_col, sd_data, leistung_data)

            # ── Sağ Alan: Tablo + İşlemler ────────────────────────────────────
            with sc_main_col:

                def sd_filtre(tam_isim):
                    v = sd_data.get(tam_isim, {})
                    if v.get("bulunamadi"): return True
                    sd_pos   = v.get("Position", "")
                    tr_mevki = _SD_MEVKI_NORM.get(sd_pos, mevki_normalize(sd_pos))
                    if sc_kategori != _sc_tumu:
                        if sc_detay != _sc_tumu:
                            if tr_mevki != sc_detay: return False
                        else:
                            if tr_mevki not in _MEVKI_DETAY.get(sc_kategori, []): return False
                    if ayak_sec != _sc_tumu and v.get("Foot", "") != ayak_sec:
                        return False
                    dob = v.get("Date of birth", "")
                    if dob and len(dob) >= 4:
                        try:
                            y = int(dob[-4:])
                            if not (yil_range[0] <= y <= yil_range[1]): return False
                        except: pass
                    return True

                filtered = sc_df.copy()
                if isim_q.strip():
                    filtered = filtered[
                        filtered[isim_col].str.contains(isim_q.strip(), case=False, na=False)]
                if vat_col and vat_sec != _sc_tumu:
                    filtered = filtered[filtered[vat_col] == vat_sec]
                if sc_rol != _sc_tumu:
                    _rol_isimler = {_i for _i, _v in _kadro_roster.items()
                                    if _v.get("rol") == sc_rol}
                    filtered = filtered[filtered[isim_col].isin(_rol_isimler)]
                if transfer_sec != _sc_tumu:
                    import datetime as _dtt, re as _ret
                    _esik = {"exp6": 6, "exp12": 12, "exp18": 18}[transfer_sec]

                    def _sozlesme_ay_kalan(_nm):
                        """Sözleşme bitişine kalan ay (negatif=bitmiş). Bilinmiyorsa None."""
                        _rec = _kadro_roster.get(_nm, {})
                        _s = (_rec.get("sozlesme") or "").strip()
                        if not _s:
                            _s = (sd_data.get(_nm, {}).get("Contract until") or "").strip()
                        if not _s or _s in ("—", "-"):
                            return None
                        _m = _ret.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/]((?:19|20)\d{2})", _s)
                        if _m:
                            try:
                                _d = _dtt.date(int(_m.group(3)), int(_m.group(2)), int(_m.group(1)))
                                return (_d - _dtt.date.today()).days / 30.0
                            except Exception:
                                pass
                        _my = _ret.search(r"(19|20)\d{2}", _s)
                        if _my:
                            try:
                                return (_dtt.date(int(_my.group()), 6, 30) - _dtt.date.today()).days / 30.0
                            except Exception:
                                pass
                        return None

                    _radar = set()
                    for _nm in filtered[isim_col]:
                        _ak = _sozlesme_ay_kalan(_nm)
                        if _ak is not None and _ak <= _esik:
                            _radar.add(_nm)
                    filtered = filtered[filtered[isim_col].isin(_radar)]
                if tr_sec != _sc_tumu:
                    _tr_isimler = {_i for _i, _v in _kadro_roster.items()
                                   if (_v.get("tr_gorusu") or "").strip() == tr_sec}
                    filtered = filtered[filtered[isim_col].isin(_tr_isimler)]
                filtered = filtered[filtered[isim_col].apply(sd_filtre)]
                if sadece_sl:
                    filtered = filtered[filtered[isim_col].isin(_sl_liste)]

                # Deneme modu: yalnızca vitrin oyuncuları göster (isimce de gizli)
                _deneme_scout = deneme_modunda()
                if _deneme_scout:
                    _toplam_havuz = len(sc_df)
                    filtered = filtered[filtered[isim_col].isin(DENEME_SCOUT_OYUNCULAR)]
                    st.markdown(
                        f"<div style='background:#e040fb1a;border:1px solid #e040fb;"
                        f"border-radius:10px;padding:10px 16px;margin-bottom:10px;"
                        f"color:#e9d5ff;font-size:0.84rem;'>"
                        f"🎁 <b>{t('Deneme modu','Trial mode')}</b> — "
                        f"{t('havuzdan','from a pool of')} <b>{_toplam_havuz}</b> "
                        f"{t('oyuncudan','players')} <b>{len(filtered)}</b> "
                        f"{t('örnek gösteriliyor. Tam havuz Premium üyelikte açılır.','samples shown. Full pool unlocks with Premium.')}"
                        f"</div>", unsafe_allow_html=True)

                if sadece_sl and len(filtered) >= 2:
                    with st.expander(
                            t("⚖️ Shortlist Karşılaştırma", "⚖️ Shortlist Comparison"),
                            expanded=True):
                        shortlist_karsilastirma_goster(
                            filtered[isim_col].tolist(), sd_data, leistung_data)

                if sadece_sl:
                    # Shortlist sekmesi: W-Scope 'Favoriler' tarzı kartlar + scout notu/durum
                    render_shortlist_kartlari(_sl_liste, _sl_kullanici)
                elif filtered.empty:
                    st.info(t("Filtrelerle eşleşen oyuncu yok.",
                              "No players match the filters."))
                else:
                    # Sayı badge
                    st.markdown(
                        f"<div style='font-size:0.73rem;color:#64748b;margin-bottom:8px;'>"
                        f"<span style='background:#7c3aed22;color:#a78bfa;"
                        f"border:1px solid #7c3aed44;border-radius:99px;"
                        f"padding:2px 10px;font-weight:700;font-size:0.70rem;'>"
                        f"{len(filtered)} {t('oyuncu bulundu', 'players found')}"
                        f"</span></div>",
                        unsafe_allow_html=True)

                    # ── W-Scope tarzı profesyonel tablo (isme tıkla → profil yeni sekme) ──
                    st.caption(t("👉 Bir isme tıkla → profil yeni sekmede açılır",
                                 "👉 Click a name → profile opens in a new tab"))
                    _dil_q = st.session_state.get("dil", "TR")
                    import datetime as _dt

                    def _kontrat_renk(_sz):
                        try:
                            _g, _a, _y = (int(x) for x in _sz.split(".")[:3])
                            _ay = (_dt.date(_y, _a, _g) - _dt.date.today()).days / 30.0
                            return "#f87171" if _ay < 6 else "#fbbf24" if _ay < 12 else "#34d399"
                        except Exception:
                            return "#a1a1aa"

                    def _esc(s):
                        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

                    _isim_sira, _sat = [], ""
                    for _, row in filtered.iterrows():
                        tam_isim = str(row.get(isim_col, ""))
                        vatandas = str(row.get(vat_col, "")) if vat_col else ""
                        _isim_sira.append(tam_isim)
                        sd  = sd_data.get(tam_isim, {})
                        _kd = _kadro_roster.get(tam_isim, {})
                        _yas = _kd.get("yas") or sd.get("Age", "") or ""
                        _poz = (_kd.get("mevki") or [""])[0]
                        if not _poz:
                            _trm = _SD_MEVKI_NORM.get(sd.get("Position", ""), "")
                            _poz = mevki_goster(_trm) if _trm else ""
                        _kl = _kd.get("kulup", "") or ""
                        _lg = _kd.get("lig", "") or ""
                        _sezk = [s for s in leistung_data.get(tam_isim, {}).get("sezonlar", [])
                                 if not s.get("milli")]
                        if not _kl and _sezk:
                            _kl = _sezk[0].get("kulup", "")
                        _sz = _kd.get("sozlesme", "") or sd.get("Contract until", "") or ""
                        _dg = _kd.get("deger", "") or ""
                        _mac = sum(s.get("mac", 0) for s in _sezk)
                        _gol = sum(s.get("gol", 0) for s in _sezk)
                        _ast = sum(s.get("asist", 0) for s in _sezk)
                        _nh  = _kd.get("nihai", "")
                        if _nh:
                            _rc = _scotr_renk(_scotr_puan(_nh))
                            _skor = f"<span class='ws-ring' style='border-color:{_rc};color:{_rc};'>{_nh}</span>"
                        else:
                            _skor = "<span style='color:#52525b;'>—</span>"
                        _poz_html = f"<span class='ws-pos'>{_esc(_poz)}</span>" if _poz else ""
                        _yildiz = "<span style='color:#fbbf24;'>★</span> " if tam_isim in _sl_liste else ""
                        _bayrak = _esc(ulke_goster(_uyruk_goster(vatandas))) if vatandas else ""
                        _href = f"?oyuncu={_urlquote(tam_isim)}&dil={_dil_q}"
                        _harf = (tam_isim[:1] or "?").upper()
                        _sat += (
                            "<tr>"
                            "<td><div style='display:flex;align-items:center;gap:10px;'>"
                            f"<span class='ws-ava'>{_esc(_harf)}</span><div>"
                            f"<a class='ws-name' href='{_href}' target='_blank'>{_yildiz}{_esc(tam_isim)}</a>"
                            f"<div class='ws-sub'>{_bayrak}</div></div></div></td>"
                            f"<td data-label='{t('Pozisyon','Pos')}'>{_poz_html}</td>"
                            f"<td data-label='{t('Kulüp','Club')}'>{_esc(_kl)}<div class='ws-sub'>{_esc(_lg)}</div></td>"
                            f"<td class='num ws-mono' data-label='{t('Yaş','Age')}'>{_yas or '—'}</td>"
                            f"<td class='ws-mono' data-label='{t('Kontrat','Contract')}' style='color:{_kontrat_renk(_sz)};'>{_esc(_sz) or '—'}</td>"
                            f"<td class='ws-mono' data-label='{t('Değer','Value')}'>{_esc(_dg) or '—'}</td>"
                            f"<td class='num ws-mono' data-label='{t('Maç','M')}'>{_mac or '—'}</td>"
                            f"<td class='num ws-mono' data-label='{t('Gol','G')}'>{_gol or '—'}</td>"
                            f"<td class='num ws-mono' data-label='{t('Asist','A')}'>{_ast or '—'}</td>"
                            f"<td data-label='{t('Skor','Score')}'>{_skor}</td></tr>"
                        )

                    _thead = (
                        "<tr>"
                        f"<th>{t('Oyuncu','Player')}</th><th>{t('Pozisyon','Position')}</th>"
                        f"<th>{t('Kulüp / Lig','Club / League')}</th><th class='num'>{t('Yaş','Age')}</th>"
                        f"<th>{t('Kontrat','Contract')}</th><th>{t('Değer','Value')}</th>"
                        f"<th class='num'>{t('Maç','M')}</th><th class='num'>{t('Gol','G')}</th>"
                        f"<th class='num'>{t('Asist','A')}</th><th>{t('Skor','Score')}</th></tr>"
                    )
                    st.markdown(
                        f"<div class='ws-wrap'><table class='ws-table'><thead>{_thead}</thead>"
                        f"<tbody>{_sat}</tbody></table></div>",
                        unsafe_allow_html=True)
                    # (Liste-sayfası Shortlist/Etiket bloğu kaldırıldı — oyuncu profilindeki
                    #  "⭐ Shortliste ekle" yeterli ve daha kullanışlı.)
    else:
        st.markdown(f"""
        <div style="max-width:560px;margin:60px auto;text-align:center;
             background:linear-gradient(135deg,#1a0f2e,#1e1338);
             border:1px solid #e040fb55;border-radius:16px;padding:48px 36px;">
          <div style="font-size:3rem;margin-bottom:16px;">👑</div>
          <h2 style="color:#f1f5f9;margin-bottom:12px;">{t("Scouting Havuzu","Scouting Pool")}</h2>
          <p style="color:#94a3b8;font-size:0.95rem;line-height:1.7;margin-bottom:20px;">
            {t("Uluslararası oyuncu kurasyonu, 2026-27 kadro planlama önerileri ve detaylı scout raporları",
               "International player curation, 2026-27 squad planning suggestions and detailed scout reports")}
            <b style="color:#e040fb;">{t("Premium üyelik","Premium membership")}</b> {t("gerektirir.","required.")}
          </p>
          <div style="background:linear-gradient(135deg,#2a1145,#1a1f36);
               border:2px solid #e040fb;border-radius:14px;padding:18px;margin-bottom:24px;">
            <div style="color:#e040fb;font-size:0.72rem;letter-spacing:2px;font-weight:800;
                 text-transform:uppercase;">👑 {t("Premium Paket","Premium Package")}</div>
            <div style="color:#fff;font-size:2.2rem;font-weight:900;line-height:1.1;margin-top:4px;">1.999 €</div>
            <div style="color:#8899aa;font-size:0.78rem;">{t("yıllık · KDV dahil","yearly · VAT incl.")}</div>
          </div>
          <div style="background:#1e1338;border:1px solid #3b2d6e;border-radius:10px;
               padding:20px;margin-bottom:24px;text-align:left;">
            <p style="color:#cbd5e1;font-size:0.85rem;margin:0 0 10px;font-weight:600;">{t("Premium ile neler var?","What's in Premium?")}</p>
            <p style="color:#94a3b8;font-size:0.82rem;line-height:1.8;margin:0;">
              🌍 {t("Uluslararası oyuncu havuzu","International player pool")}<br>
              🎯 {t("Mevki bazlı scout profilleri","Position-based scout profiles")}<br>
              📊 {t("Detaylı oyuncu değerlendirmeleri + PDF rapor","Detailed assessments + PDF reports")}<br>
              📋 {t("Kadro planlama danışmanlığı","Squad planning consultancy")}<br>
              🤝 {t("Öncelikli destek","Priority support")}
            </p>
          </div>
          <p style="color:#6b7a99;font-size:0.80rem;">
            {t("Premium üyelik için 📬 İletişim sayfasından bize ulaşın.","For Premium membership, reach us via the 📬 Contact page.")}
          </p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# ─── GENEL ÖZET (GİRİŞ ekranı için) ───────────────────────────────────────────
def genel_ozet_hesapla() -> dict:
    """GİRİŞ karşılama ekranı için kısa sayısal özet üretir (df_tam + yardımcı kaynaklar)."""
    if df_tam.empty:
        return {}
    uyr = df_tam["Uyruk"] if "Uyruk" in df_tam.columns else pd.Series([""] * len(df_tam))
    yerli   = int((uyr == "Turkey").sum())
    yabanci = int(((uyr != "Turkey") & (uyr.fillna("") != "")).sum())
    yas = df_tam["Yaş"].dropna() if "Yaş" in df_tam.columns else pd.Series(dtype=float)
    # Scouting sayısı: Sco 🌍 havuzu (scout_kadro), yoksa yerel SD profilleri
    try:
        scouting_n = len(scout_kadro_yukle()) or len(scouting_sd_yukle())
    except Exception:
        try: scouting_n = len(scouting_sd_yukle())
        except Exception: scouting_n = 0
    try: mac_n = len(mac_sonuclari_yukle())
    except Exception: mac_n = 0
    return {
        "oyuncu":   len(df_tam),
        "takim":    _kanon_takim_sayisi(df_tam["Takım"]),
        "scouting": scouting_n,
        "mac":      mac_n,
        "gol":      int(df_tam["Gol"].sum()),
        "yerli":    yerli,
        "yabanci":  yabanci,
        "ort_yas":  round(float(yas.mean()), 1) if not yas.empty else 0,
        "u23":      int((yas < 23).sum()) if not yas.empty else 0,
    }


def _ozet_kart(deger, etiket, alt="", renk="#58a6ff"):
    return (f'<div class="stat-kart" style="border-radius:14px;border-top:2px solid {renk};">'
            f'<div class="sayi" style="color:{renk}">{deger}</div>'
            f'<div class="etiket">{etiket}</div>'
            + (f'<div style="font-size:10px;color:#6e7681;margin-top:3px;">{alt}</div>' if alt else "")
            + '</div>')


def _paket_kart_html(ikon, isim, renk, fiyat, fiyat_alt, ozellikler, populer=False,
                     deneme=False, eski_fiyat="", indirim=""):
    """Tek üyelik paketi kartı (HTML)."""
    glow = f"box-shadow:0 0 0 2px {renk}, 0 8px 28px {renk}55;" if populer else f"border:1px solid {renk}44;"
    rozet = (f"<div style='position:absolute;top:-11px;left:50%;transform:translateX(-50%);"
             f"background:{renk};color:#06210f;font-size:10px;font-weight:800;letter-spacing:1px;"
             f"border-radius:20px;padding:3px 14px;white-space:nowrap;'>★ {t('EN POPÜLER','MOST POPULAR')}</div>") if populer else ""
    # İndirim rozeti (sağ üst köşe)
    indirim_rozet = (f"<div style='position:absolute;top:10px;right:10px;background:#ef4444;"
                     f"color:#fff;font-size:10px;font-weight:800;border-radius:6px;"
                     f"padding:2px 8px;'>{indirim}</div>") if indirim else ""
    # Üstü çizili eski fiyat
    eski_html = (f"<div style='font-size:0.95rem;color:#6e7681;text-decoration:line-through;"
                 f"line-height:1;margin-bottom:2px;'>{eski_fiyat}</div>") if eski_fiyat else ""
    deneme_rozet = (f"<div style='margin-top:8px;background:#e040fb1a;border:1px solid #e040fb66;"
                    f"color:#e9d5ff;border-radius:6px;padding:4px 0;font-size:10.5px;font-weight:800;"
                    f"letter-spacing:0.5px;'>🎁 {t('2 GÜN ÜCRETSİZ DENE','2-DAY FREE TRIAL')}</div>") if deneme else ""
    satirlar = ""
    for metin, var in ozellikler:
        if var:
            satirlar += (f"<div style='font-size:12.5px;color:#c9d1d9;padding:5px 0;border-bottom:1px solid #1a2027;'>"
                         f"<span style='color:{renk};font-weight:700;'>✓</span> &nbsp;{metin}</div>")
        else:
            satirlar += (f"<div style='font-size:12.5px;color:#5b6470;padding:5px 0;border-bottom:1px solid #1a2027;'>"
                         f"<span style='color:#475569;'>✕</span> &nbsp;{metin}</div>")
    return (
        f"<div class='paket-kart' style='position:relative;background:linear-gradient(160deg,#1a2030,#0f141c);"
        f"border:1px solid #232a45;border-radius:16px;padding:24px 20px 18px;{glow}height:100%;'>"
        f"{rozet}{indirim_rozet}"
        f"<div style='text-align:center;margin-bottom:6px;'>"
        f"<div style='font-size:30px;'>{ikon}</div>"
        f"<div style='font-size:1.25rem;font-weight:800;color:{renk};margin-top:2px;'>{isim}</div></div>"
        f"<div style='text-align:center;margin:8px 0 16px;'>"
        f"{eski_html}"
        f"<div style='font-size:2rem;font-weight:900;color:#fff;line-height:1;font-family:Sora,sans-serif;'>{fiyat}</div>"
        f"<div style='font-size:11px;color:#8b949e;margin-top:3px;'>{fiyat_alt}</div>"
        f"{deneme_rozet}</div>"
        f"{satirlar}</div>"
    )


def render_paketler():
    """Basic / Pro / Premium üyelik paketleri karşılaştırma görseli."""
    st.markdown(
        f"<div style='font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#1db954;"
        f"font-weight:700;margin:6px 0 12px;'>💎 {t('Üyelik Paketleri','Membership Plans')}</div>",
        unsafe_allow_html=True)

    free_pkg = [
        (t("Oyuncu listesi & temel istatistikler","Player list & basic stats"), True),
        (t("Lig tablosu · Takımlar · Kaleciler","Standings · Teams · Goalkeepers"), True),
        (t("Yaş analizi","Age analysis"), True),
        (t("İletişim & talep gönderme","Contact & request"), False),
        (t("PRO veri araçları","PRO data tools"), False),
        (t("Scouting havuzu","Scouting pool"), False),
    ]
    basic = [
        (t("Free'nin tüm özellikleri","Everything in Free"), True),
        (t("İletişim & talep gönderme","Contact & request"), True),
        (t("PRO veri araçları","PRO data tools"), False),
        (t("Scouting havuzu","Scouting pool"), False),
    ]
    pro = [
        (t("Basic'in tüm özellikleri","Everything in Basic"), True),
        (t("Detaylı oyuncu profili","Detailed player profile"), True),
        (t("Transfer Öner","Transfer Suggest"), True),
        (t("Karşılaştırma (4 oyuncu)","Comparison (4 players)"), True),
        (t("Gelişmiş arama · En İyiler","Advanced search · Top performers"), True),
        (t("Favori listesi","Favorites list"), True),
        (t("Scouting havuzu","Scouting pool"), False),
    ]
    premium = [
        (t("Pro'nun tüm özellikleri","Everything in Pro"), True),
        (t("Uluslararası scouting havuzu","International scouting pool"), True),
        (t("Scouting raporları & etiketleme","Scouting reports & tagging"), True),
        (t("Kadro planlama danışmanlığı","Squad planning consultancy"), True),
        (t("Öncelikli destek","Priority support"), True),
    ]

    def _al_butonu(plan, key):
        if st.button(t("Bu planı al", "Get this plan"), key=key, width="stretch"):
            st.session_state["yukselt_plan"] = plan
            st.session_state["sayfa"] = "yukselt"
            st.session_state["girildi"] = True
            st.rerun()

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        st.markdown(_paket_kart_html("🆓", "Free", "#58a6ff",
            t("Ücretsiz","Free"), t("temel erişim","basic access"), free_pkg), unsafe_allow_html=True)
    _yillik = t("yıllık · KDV dahil", "yearly · VAT incl.")
    _ind = t("%50", "-50%")
    with c2:
        st.markdown(_paket_kart_html("🔹", "Basic", "#29b6f6",
            "499 €", _yillik, basic, deneme=True, eski_fiyat="999 €", indirim=_ind), unsafe_allow_html=True)
        _al_butonu("basic", "al_basic")
    with c3:
        st.markdown(_paket_kart_html("⚡", "Pro", "#1db954",
            "999 €", _yillik, pro, populer=True, deneme=True, eski_fiyat="1.999 €", indirim=_ind), unsafe_allow_html=True)
        _al_butonu("pro", "al_pro")
    with c4:
        st.markdown(_paket_kart_html("👑", "Premium", "#e040fb",
            "1.999 €", _yillik, premium, deneme=True, eski_fiyat="2.999 €",
            indirim=t("%33","-33%")), unsafe_allow_html=True)
        _al_butonu("premium", "al_premium")

    # Lansman indirimi şeridi
    st.markdown(
        f"<div style='text-align:center;margin-top:10px;'>"
        f"<span style='background:#ef444422;border:1px solid #ef4444;color:#fca5a5;"
        f"border-radius:99px;padding:4px 16px;font-size:0.78rem;font-weight:700;'>"
        f"🔥 {t('LANSMAN İNDİRİMİ — sınırlı süre','LAUNCH DISCOUNT — limited time')}</span></div>",
        unsafe_allow_html=True)

    # Ücretsiz deneme talep CTA'sı — belirgin kutu (giriş gerekmez)
    _dnc = st.columns([1, 2, 1])[1]
    with _dnc:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#1a0f2e,#2a1145);"
            f"border:1px solid #e040fb;border-radius:12px;padding:14px 18px 6px;"
            f"text-align:center;margin-top:16px;'>"
            f"<div style='color:#e9d5ff;font-size:0.9rem;font-weight:700;'>"
            f"🎁 {t('Önce denemek ister misin?','Want to try first?')}</div>"
            f"<div style='color:#a78bfa;font-size:0.78rem;margin-top:2px;'>"
            f"{t('2 gün boyunca Premium — kart bilgisi yok, taahhüt yok.','2 days of Premium — no card, no commitment.')}</div>"
            f"</div>", unsafe_allow_html=True)
        if st.button(t("🎁 2 Günlük Ücretsiz Deneme Talep Et", "🎁 Request a 2-Day Free Trial"),
                     width="stretch", type="primary", key="deneme_talep_cta"):
            st.session_state["sayfa"]      = "talep"
            st.session_state["talep_tip_on"] = "deneme"
            st.session_state["girildi"]    = True
            st.rerun()

    _pk_not = t("Deneme talebini değerlendirip kademeni elle aktifleştiririz. Kurumsal teklifler için 📬 İletişim.",
                "We review your trial request and activate your tier manually. For corporate offers see 📬 Contact.")
    st.markdown(
        f"<div style='text-align:center;color:#6e7681;font-size:11px;margin-top:12px;'>{_pk_not}</div>",
        unsafe_allow_html=True)


def render_giris_ekrani():
    """GİRİŞ sekmesi: kısa sayısal özet + Hakkında içeriği."""
    o = genel_ozet_hesapla()
    ad = st.session_state.get("kulup_ad", "")
    selam = f"{t('Hoş geldin','Welcome')}{(' ' + ad) if ad else ''} 👋"
    st.markdown(f"### {selam}")
    st.caption(t("Türkiye Kadınlar Süper Ligi · 2025-2026 Sezonu · 30 hafta verisi",
                 "Turkish Women's Super League · 2025-2026 Season · 30 weeks of data"))

    if o:
        st.markdown(
            f"<div style='font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#1db954;"
            f"font-weight:700;margin:10px 0 10px;'>📊 {t('Kısa Sayısal Özet','Quick Summary')}</div>",
            unsafe_allow_html=True)
        # Disiplinli palet: veri=yeşil (#1db954), platform/scouting=mor vurgu (#a855f7).
        satir1 = [
            (o["oyuncu"], t("Toplam Oyuncu","Total Players"),
             f"{o['yerli']} {t('yerli','dom.')} · {o['yabanci']} {t('yabancı','for.')}", "#1db954"),
            (o["takim"], t("Toplam Takım","Total Teams"), t("Süper Lig","Super League"), "#1db954"),
            (o["scouting"], t("Scouting Raporu","Scouting Reports"), t("uluslararası havuz","intl. pool"), "#a855f7"),
            (o["mac"], t("Toplam Maç","Total Matches"), t("sezon geneli","full season"), "#1db954"),
        ]
        satir2 = [
            (o["gol"], t("Toplam Gol","Total Goals"), t("tüm lig","whole league"), "#1db954"),
            (o["yerli"], t("Yerli Oyuncu","Domestic Players"),
             (f"%{round(o['yerli']/o['oyuncu']*100)} " + t("yerli oran","domestic")) if o["oyuncu"] else "", "#1db954"),
            (o["ort_yas"], t("Ortalama Yaş","Average Age"), t("lig geneli","league-wide"), "#1db954"),
            (o["u23"], t("U-23 Yetenek","U-23 Talents"), t("geleceğin yıldızları","future stars"), "#a855f7"),
        ]
        for satir in (satir1, satir2):
            cols = st.columns(4)
            for kol, (d, e, a, r) in zip(cols, satir):
                kol.markdown(_ozet_kart(d, e, a, r), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # Üyelik paketleri
    render_paketler()
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#1db954;"
        f"font-weight:700;margin:6px 0 4px;'>ℹ️ {t('Hakkında','About')}</div>",
        unsafe_allow_html=True)
    render_hakkinda_icerik()


# ─── KARŞILAMA EKRANI (ana içeriğe geçmeden önce — herkese açık) ───────────────
if not st.session_state.get("girildi", False):
    _kc = st.columns([1, 2, 1])[1]
    with _kc:
        if st.button(t("🚀 Ana Sayfaya Geç", "🚀 Enter the App"),
                     type="primary", width="stretch", key="karsilama_gec_ust"):
            st.session_state["girildi"] = True
            st.rerun()
    render_giris_ekrani()
    st.markdown("<br>", unsafe_allow_html=True)
    _kc2 = st.columns([1, 2, 1])[1]
    with _kc2:
        if st.button(t("🚀 Ana Sayfaya Geç", "🚀 Enter the App"),
                     type="primary", width="stretch", key="karsilama_gec_alt"):
            st.session_state["girildi"] = True
            st.rerun()
    st.stop()


# ─── DANIŞMANLIK TALEP BANNER — yalnız ilk sekmede (Oyuncu Listesi) ───────────
if _ust_blok_goster:
    st.markdown("<br>", unsafe_allow_html=True)
    _bc1, _bc2 = st.columns([3, 1])
    with _bc1:
        st.markdown(f"""
    <div style='background:linear-gradient(135deg,#0f3d2e,#1a5c43);border-radius:12px;
        padding:13px 20px;border-left:4px solid #1db954;'>
      <div style='color:#fff;font-size:1.05rem;font-weight:700;'>{t("📩 Kadronu birlikte kuralım", "📩 Let's build your squad together")}</div>
      <div style='color:#a7f3d0;font-size:0.85rem;margin-top:2px;'>
      {t("Oyuncu raporu · mevki önerisi · oyuncu kıyası · tam kadro danışmanlığı — talebini ilet.",
         "Player report · position suggestion · player comparison · full squad consultancy — send your request.")}</div>
    </div>""", unsafe_allow_html=True)
    with _bc2:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        if st.button(t("📩 Talep / Danışmanlık", "📩 Request / Consult"), width="stretch", type="primary"):
            st.session_state["sayfa"] = "talep"
            st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)

# ─── SEKMELER (KOŞULLU RENDER — perf) ─────────────────────────────────────────
# st.tabs yerine: SADECE sol menüden seçili sekmenin kodu çalışır (14 sekme
# yerine 1 → her etkileşim ~14 kat daha hafif). Native sekme barı + JS hilesi
# kaldırıldı. Sekme değişkenleri artık BOOLEAN (aktif mi); "with tabX:" → "if tabX:".
_giris_var = st.session_state.get("kulup_giris", False)
_sekmeler  = _tr_sekme_etiketleri(_giris_var)
_is_admin  = st.session_state.get("kulup_kullanici") == "admin"
_aktif = st.session_state.get("tr_sekme", _sekmeler[0])
if _aktif not in _sekmeler:
    _aktif = _sekmeler[0]
    st.session_state["tr_sekme"] = _aktif

# "Tam Profili Aç" modal tetikleyicisi
_dlg = st.session_state.pop("_profil_dlg", None)
if _dlg:
    _profil_dialog(_dlg[0], _dlg[1])

tab_benim    = _giris_var and _aktif == t("🏟️ Benim Kadrom", "🏟️ My Squad")
tab_internal = _giris_var and _aktif == t("📝 Internal Scout", "📝 Internal Scout")
tab1         = _aktif == t("📋 Oyuncu Listesi", "📋 Player List")
tab_transfer = _aktif == t("🔄 Transfer Öner", "🔄 Transfer Suggest")
tab_genç     = _aktif == t("🌱 Genç Yetenekler", "🌱 Young Talents")
tab2         = _aktif == t("👤 Oyuncu Profili", "👤 Player Profile")
tab3         = _aktif == t("⚡ Karşılaştırma", "⚡ Comparison")
tab4         = _aktif == t("🏟️ Takımlar", "🏟️ Teams")
tab5         = _aktif == t("🏆 Lig Tablosu", "🏆 League Table")
tab6         = _aktif == t("🌟 En İyiler", "🌟 Top Performers")
tab7         = _aktif == t("⚽ Fantasy Kadro", "⚽ Fantasy Squad")
tab9         = _aktif == t("🔍 Gelişmiş Arama", "🔍 Advanced Search")
tab10        = _aktif == t("🎂 Yaş Analizi", "🎂 Age Analysis")
tab11        = _aktif == t("🧤 Kaleciler", "🧤 Goalkeepers")

# ══════════════════════════════════════════════════════════════════════════════
# SEKME — INTERNAL SCOUT (kişiye özel maç raporları: SWOT + serbest not)
# ══════════════════════════════════════════════════════════════════════════════
if tab_internal:
    if True:
        import datetime as _dt
        _kull = st.session_state.get("kulup_kullanici", "")
        st.markdown(f"### 📝 {t('Internal Scout — Maç Raporların', 'Internal Scout — Your Match Reports')}")
        st.caption(t("İzlediğin maçlara özel SWOT + serbest not. Yalnızca sen görürsün.",
                     "Private SWOT + free notes for matches you watched. Only you can see them."))

        _int_mod = st.radio("mod", [t("➕ Yeni Rapor", "➕ New Report"),
                                    t("📋 Raporlarım", "📋 My Reports")],
                            horizontal=True, label_visibility="collapsed", key="int_mod")

        if _int_mod == t("➕ Yeni Rapor", "➕ New Report"):
            ic1, ic2, ic3, ic4 = st.columns([1.2, 1.4, 1.4, 0.9])
            with ic1: _i_tarih = st.date_input(t("Maç Tarihi", "Match Date"), key="int_tarih")
            with ic2: _i_ev    = st.text_input(t("Ev Sahibi", "Home"), key="int_ev", placeholder="Türkiye U19")
            with ic3: _i_dep   = st.text_input(t("Deplasman", "Away"), key="int_dep", placeholder="Karadağ U19")
            with ic4: _i_skor  = st.text_input(t("Skor", "Score"), key="int_skor", placeholder="5-0")
            _i_genel = st.text_area(t("Genel Not / Maç Özeti", "General Note / Match Summary"),
                                    key="int_genel", height=110,
                                    placeholder=t("Maçın genel görünümü, taktik gözlemler…",
                                                  "Overall view, tactical observations…"))
            st.markdown(f"**{t('Oyuncu SWOT — alttan satır ekleyebilirsin', 'Player SWOT — add rows below')}**")
            _bos = pd.DataFrame([{"Oyuncu": "", "Mevki": "", "Takım": "",
                                  "S": "", "W": "", "O": "", "T": ""} for _ in range(3)])
            _i_swot = st.data_editor(
                _bos, num_rows="dynamic", width="stretch", key="int_swot",
                column_config={
                    "Oyuncu": st.column_config.TextColumn(t("Oyuncu", "Player"), width="medium"),
                    "Mevki":  st.column_config.TextColumn(t("Mevki", "Pos"), width="small"),
                    "Takım":  st.column_config.TextColumn(t("Takım", "Team"), width="small"),
                    "S": st.column_config.TextColumn("💪 S", help=t("Güçlü yönler", "Strengths"), width="large"),
                    "W": st.column_config.TextColumn("⚠️ W", help=t("Zayıf yönler", "Weaknesses"), width="large"),
                    "O": st.column_config.TextColumn("📈 O", help=t("Fırsatlar", "Opportunities"), width="large"),
                    "T": st.column_config.TextColumn("🛑 T", help=t("Tehditler", "Threats"), width="large"),
                })
            if st.button(t("💾 Raporu Kaydet", "💾 Save Report"), type="primary", key="int_kaydet"):
                if not (_i_ev.strip() or _i_dep.strip()):
                    st.error(t("En az takım adlarını gir.", "Enter at least the team names."))
                else:
                    _oyuncular = [row for row in _i_swot.to_dict("records")
                                  if str(row.get("Oyuncu", "")).strip()]
                    internal_ekle({
                        "id": int(_dt.datetime.now().timestamp()),
                        "kullanici": _kull, "tarih": str(_i_tarih),
                        "ev": _i_ev.strip(), "dep": _i_dep.strip(), "skor": _i_skor.strip(),
                        "genel_not": _i_genel.strip(), "oyuncular": _oyuncular,
                        "olusturma": _dt.datetime.now().isoformat(timespec="seconds"),
                    })
                    st.success(t(f"✅ Rapor kaydedildi — {len(_oyuncular)} oyuncu.",
                                 f"✅ Report saved — {len(_oyuncular)} players."))
                    st.balloons()

        else:  # 📋 Raporlarım
            _raporlar = internal_yukle(_kull)
            if not _raporlar:
                st.info(t("Henüz rapor yok. '➕ Yeni Rapor' ile başla.",
                          "No reports yet. Start with '➕ New Report'."))
            for _r in _raporlar:
                _b = " ".join(x for x in [_r.get("ev",""), _r.get("skor",""), _r.get("dep","")] if x)
                _b = f"⚪ {_b}  ·  {_r.get('tarih','')}" if _b else _r.get("tarih","")
                _oys = _r.get("oyuncular", [])
                with st.expander(f"{_b}   ({len(_oys)} {t('oyuncu','players')})"):
                    if _r.get("genel_not"):
                        st.markdown(
                            f"<div style='background:#11162a;border-left:3px solid #7c3aed;"
                            f"padding:8px 12px;border-radius:6px;font-size:0.86rem;color:#cbd5e1;"
                            f"margin-bottom:10px;'>📝 {_r['genel_not']}</div>", unsafe_allow_html=True)
                    for _o in _oys:
                        _mvk = _o.get("Mevki", ""); _tkm = _o.get("Takım", "")
                        st.markdown(
                            f"<div style='font-weight:700;color:#e2e8f0;margin-top:6px;'>{_o.get('Oyuncu','')}"
                            f" <span style='color:#8899aa;font-weight:400;font-size:0.78rem;'>"
                            f"{_mvk}{' · ' + _tkm if _tkm else ''}</span></div>", unsafe_allow_html=True)
                        for _ik, _hf, _ak, _clr in [("💪","S","S","#4ade80"),("⚠️","W","W","#fbbf24"),
                                                    ("📈","O","O","#60a5fa"),("🛑","T","T","#f87171")]:
                            if str(_o.get(_ak,"")).strip():
                                st.markdown(
                                    f"<div style='font-size:0.82rem;margin-left:10px;color:#cbd5e1;'>"
                                    f"{_ik} <b style='color:{_clr};'>{_hf}</b>: {_o[_ak]}</div>",
                                    unsafe_allow_html=True)
                    if st.button(t("🗑️ Sil", "🗑️ Delete"), key=f"int_sil_{_r.get('id')}"):
                        internal_sil(_r.get("id")); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 1 — OYUNCU LİSTESİ
# ══════════════════════════════════════════════════════════════════════════════
if tab1:
    if df_tam.empty:
        st.info(t("Veri yok.", "No data."))

    _TUM_OYUNCU   = t("— Tüm oyuncular —", "— All players —")
    _TUM_TAKIM    = t("Tüm Takımlar", "All Teams")
    _TUM_MEVKI    = t("Tüm Mevkiler", "All Positions")
    _TUM          = t("Tümü", "All")
    _SIRALAMA_OPT = ["Maç ↓","Gol ↓","Dakika ↓","Sarı ↓","Gol/Maç ↓"]
    _SIRALAMA_EN  = {"Maç ↓":"Matches ↓","Gol ↓":"Goals ↓","Dakika ↓":"Minutes ↓","Sarı ↓":"Yellow ↓","Gol/Maç ↓":"Goals/Match ↓"}

    f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
    with f1:
        secenekler = [_TUM_OYUNCU] + sorted(df_tam["Oyuncu"].tolist())
        secili_oyuncu = st.selectbox(t("Oyuncu Ara", "Search Player"), secenekler,
            index=secenekler.index(url_oyuncu) if url_oyuncu in secenekler else 0)
    with f2:
        takimlar = [_TUM_TAKIM] + sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_takim = st.selectbox(t("Takım", "Team"), takimlar,
                                    format_func=lambda x: x if x == _TUM_TAKIM else _takim_kisa(x))
    with f3:
        secili_kategori = st.selectbox(t("Mevki", "Position"), [_TUM_MEVKI] + list(_MEVKI_DETAY.keys()),
            format_func=mevki_goster, key="ol_kategori")
    with f4:
        siralama = st.selectbox(t("Sırala", "Sort"), _SIRALAMA_OPT,
            format_func=lambda x: _SIRALAMA_EN[x] if EN else x)

    # Detay filtresi — sadece kategori seçiliyse göster
    secili_detay = _TUM
    if secili_kategori != _TUM_MEVKI:
        detay_secenekler = [_TUM] + _MEVKI_DETAY[secili_kategori]
        secili_detay = st.selectbox(
            f"↳ {mevki_goster(secili_kategori)} {t('detayı', 'detail')}",
            detay_secenekler,
            format_func=mevki_goster,
            key="ol_detay"
        )

    df = df_tam.copy()
    if secili_oyuncu != _TUM_OYUNCU:
        df = df[df["Oyuncu"] == secili_oyuncu]
    if secili_takim != _TUM_TAKIM:
        df = df[df["TümTakımlar"].str.contains(secili_takim, na=False)]
    if secili_kategori != _TUM_MEVKI and "Mevki" in df.columns:
        if secili_detay != _TUM:
            df = df[df["Mevki"] == secili_detay]
        else:
            df = df[df["Mevki"].isin(_MEVKI_DETAY[secili_kategori])]

    siralama_map = {"Maç ↓":"Maç","Gol ↓":"Gol","Dakika ↓":"Dakika","Sarı ↓":"Sarı","Gol/Maç ↓":"Gol/Maç"}
    df = df.sort_values(siralama_map[siralama], ascending=False).reset_index(drop=True)
    df.index += 1

    df = df.copy()
    df["Takım (Gösterim)"] = df.apply(
        lambda r: _takim_kisa(r["TümTakımlar"] if r["Transfer"] else r["Takım"]), axis=1)

    # Free kademe (girişsiz VEYA ücretsiz üye) kısa liste; Basic+ (kulüp/ödeyen üye/admin) tam liste.
    # NOT: Eskiden "giriş var mı" idi → self-servis free üyeler tam listeyi görüyordu (bug). Artık tier kapısı.
    _tam_yetki  = tier_yeterli("basic")
    _giris_var2 = st.session_state.get("kulup_giris", False)
    _toplam_oy  = len(df)
    if not _tam_yetki:
        df = df.head(40)

    bas, ind = st.columns([3, 1])
    with bas:
        if _tam_yetki or _toplam_oy <= len(df):
            st.markdown(f"#### {len(df)} {t('oyuncu', 'players')}")
        else:
            st.markdown(f"#### {len(df)} / {_toplam_oy} {t('oyuncu', 'players')}")
    with ind:
        csv_b = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ CSV", csv_b, "oyuncular.csv", width="stretch")
    if not _tam_yetki and _toplam_oy > len(df):
        if _giris_var2:   # giriş yapmış ama free kademe → yükseltmeye yönlendir
            st.caption(t(f"İlk {len(df)} oyuncu gösteriliyor — tüm {_toplam_oy} oyuncu + tıklanabilir detaylı profiller için 💎 üyeliğini yükselt.",
                         f"Showing first {len(df)} — upgrade your membership for all {_toplam_oy} players + clickable detailed profiles."))
        else:
            st.caption(t(f"İlk {len(df)} oyuncu gösteriliyor — tümü için 🔐 giriş yap / kayıt ol.",
                         f"Showing first {len(df)} — log in / sign up to see all {_toplam_oy}."))

    # ── Dar liste (Ad · Takım · Yaş) + sağda ücretsiz bilgi paneli ──
    def _yas_int(r):
        try: return int(r["Yaş"]) if "Yaş" in r and str(r["Yaş"]).strip() not in ("", "nan") else None
        except Exception: return None
    liste_df = df[["Oyuncu", "Takım (Gösterim)"]].reset_index(drop=True)
    liste_df["Yaş"] = [(_yas_int(df.iloc[i]) if "Yaş" in df.columns else None) for i in range(len(df))]

    if _tam_yetki:
        # Basic+ (kulüp/ödeyen üye/admin): Scouting ile AYNI W-Scope tablosu — isme tıkla → tam profil
        st.caption(t("👉 Bir isme tıkla → tam profil yeni sekmede açılır",
                     "👉 Click a name → full profile opens in a new tab"))
        _dil_q = st.session_state.get("dil", "TR")
        _sat = ""
        for _i in range(len(df)):
            _r = df.iloc[_i]
            _ad = str(_r["Oyuncu"])
            _sdp = sd_profiller.get(_ad, {})
            _nat = ulke_goster(_uyruk_goster(_sdp.get("Nationality", ""))) if _sdp.get("Nationality") else ""
            _mvk = _r.get("Mevki", "") or ""
            _mvk_g = mevki_goster(_mvk) if _mvk else ""
            _poz = f"<span class='ws-pos'>{_mvk_g}</span>" if _mvk_g else ""
            _tk = str(_r.get("Takım (Gösterim)", "") or "")
            try:
                _ya = int(_r["Yaş"]) if str(_r.get("Yaş", "")).strip() not in ("", "nan") else ""
            except Exception:
                _ya = ""
            _mac = int(_r.get("Maç", 0) or 0); _gol = int(_r.get("Gol", 0) or 0); _dk = int(_r.get("Dakika", 0) or 0)
            _gm = round(_gol / _mac, 2) if _mac else 0
            _href = f"?oyuncu={_urlquote(_ad)}&dil={_dil_q}"
            _harf = (_ad[:1] or "?").upper()
            _sat += (
                "<tr><td><div style='display:flex;align-items:center;gap:10px;'>"
                f"<span class='ws-ava'>{_harf}</span><div>"
                f"<a class='ws-name' href='{_href}' target='_blank'>{_ad}</a>"
                f"<div class='ws-sub'>{_nat}</div></div></div></td>"
                f"<td data-label='{t('Pozisyon','Pos')}'>{_poz}</td>"
                f"<td data-label='{t('Takım','Team')}'>{_tk}</td>"
                f"<td class='num ws-mono' data-label='{t('Yaş','Age')}'>{_ya or '—'}</td>"
                f"<td class='num ws-mono' data-label='{t('Maç','M')}'>{_mac or '—'}</td>"
                f"<td class='num ws-mono' data-label='{t('Gol','G')}'>{_gol or '—'}</td>"
                f"<td class='num ws-mono' data-label='{t('Gol/Maç','G/M')}'>{_gm or '—'}</td>"
                f"<td class='num ws-mono' data-label='{t('Dk','Min')}'>{_dk or '—'}</td></tr>"
            )
        _thead = ("<tr>"
                  f"<th>{t('Oyuncu','Player')}</th><th>{t('Pozisyon','Position')}</th>"
                  f"<th>{t('Takım','Team')}</th><th class='num'>{t('Yaş','Age')}</th>"
                  f"<th class='num'>{t('Maç','M')}</th><th class='num'>{t('Gol','G')}</th>"
                  f"<th class='num'>{t('Gol/Maç','G/M')}</th><th class='num'>{t('Dk','Min')}</th></tr>")
        st.markdown(
            f"<div class='ws-wrap'><table class='ws-table'><thead>{_thead}</thead>"
            f"<tbody>{_sat}</tbody></table></div>", unsafe_allow_html=True)
    else:
        # Girişsiz: kısa liste + ücretsiz önizleme kartı (freemium teaser korunur)
        col_liste, col_detay = st.columns([5, 4], gap="medium")
        with col_liste:
            secim = st.dataframe(
                liste_df, width="stretch", height=560,
                on_select="rerun", selection_mode="single-row", key="ol_liste",
                column_config={
                    "Oyuncu":           st.column_config.TextColumn(t("Oyuncu","Player"), width="large"),
                    "Takım (Gösterim)": st.column_config.TextColumn(t("Takım","Team"), width="medium"),
                    "Yaş":              st.column_config.NumberColumn(t("Yaş","Age"), format="%d", width="small"),
                })

        with col_detay:
            secili_satirlar = secim.selection.rows if secim and secim.selection else []
            if not secili_satirlar:
                st.markdown(
                    f"<div style='background:linear-gradient(180deg,#12182e,#0e1322);border:1px dashed #2d3561;"
                    f"border-radius:14px;padding:46px 24px;text-align:center;color:#7b86a0;'>"
                    f"<div style='font-size:2.2rem;margin-bottom:8px;opacity:0.65;'>⚽</div>"
                    f"<div style='font-weight:600;color:#aebbd0;font-size:0.95rem;'>{t('Listeden bir oyuncuya tıkla','Click a player in the list')}</div>"
                    f"<div style='font-size:0.82rem;margin-top:4px;'>{t('ücretsiz bilgileri burada görünür','free info appears here')}</div>"
                    f"</div>", unsafe_allow_html=True)
            else:
                tikli_oyuncu = liste_df.iloc[secili_satirlar[0]]["Oyuncu"]
                st.session_state["profil_sec"] = tikli_oyuncu
                p_row = df_tam[df_tam["Oyuncu"] == tikli_oyuncu]
                if not p_row.empty:
                    p   = p_row.iloc[0]
                    sd  = sd_profiller.get(tikli_oyuncu, {})
                    _mvk = p.get("Mevki", "")
                    _mrk = mevki_renk(_mvk)
                    transfer  = bool(p.get("Transfer", False))
                    takim_txt = _takim_kisa(p["TümTakımlar"] if transfer else p["Takım"])

                    CHIP = ("background:#0f1117;border:1px solid #2d3561;border-radius:6px;"
                            "padding:3px 9px;font-size:0.74rem;color:#c0ccd8;display:inline-block;margin:0 5px 5px 0")
                    chips = []
                    if sd.get("Date of birth"): chips.append(f'<span style="{CHIP}">🎂 {sd["Date of birth"]}</span>')
                    if sd.get("Nationality"):   chips.append(f'<span style="{CHIP}">🏳️ {ulke_goster(sd["Nationality"])}</span>')
                    if sd.get("Height"):        chips.append(f'<span style="{CHIP}">📏 {sd["Height"]} m</span>')
                    if sd.get("Foot"):          chips.append(f'<span style="{CHIP}">👟 {sd["Foot"].capitalize()}</span>')
                    chip_html = "".join(chips)

                    STAT = ("background:#0f1117;border-radius:8px;padding:8px 0;text-align:center;flex:1")
                    stat_html = ""
                    for sutun, etk, clr in [("Gol",t("GOL","GOALS"),"#4ade80"),
                                            ("Maç",t("MAÇ","MATCH"),"#60a5fa"),
                                            ("Dakika",t("DK","MIN"),"#f59e0b")]:
                        if sutun in p:
                            stat_html += (f'<div style="{STAT}">'
                                          f'<div style="font-size:1.3rem;font-weight:800;color:{clr}">{int(p[sutun])}</div>'
                                          f'<div style="font-size:0.6rem;color:#8899aa">{etk}</div></div>')
                    _mvk_g = mevki_goster(_mvk) if _mvk else ""
                    _transfer_b = (f' <span style="background:#1a3a2a;color:#1db954;border-radius:4px;'
                                   f'padding:1px 6px;font-size:0.66rem">🔄 Transfer</span>') if transfer else ""

                    st.markdown(
                        f'<div style="background:linear-gradient(160deg,#171c30,#12151f);'
                        f'border:1px solid #232842;border-top:3px solid {_mrk};border-radius:12px;padding:16px 18px;">'
                        f'<div style="font-size:1.15rem;font-weight:800;color:#fff;">{tikli_oyuncu}</div>'
                        f'<div style="margin:5px 0 10px;">'
                        f'<span style="color:{_mrk};font-weight:700;background:{_mrk}22;border:1px solid {_mrk}55;'
                        f'border-radius:5px;padding:1px 8px;font-size:0.74rem;">{_mvk_g or "—"}</span>'
                        f'<span style="color:#8899aa;font-size:0.8rem;"> · 🏟 {takim_txt}{_transfer_b}</span></div>'
                        f'<div style="margin-bottom:10px;">{chip_html}</div>'
                        f'<div style="display:flex;gap:8px;">{stat_html}</div>'
                        f'</div>', unsafe_allow_html=True)
                    st.caption(t("🔒 Kariyer · radar · scout raporu içeren tam profil üye girişiyle açılır.",
                                 "🔒 Full profile (career · radar · scout report) opens with login."))

# ==============================================================================
# SEKME 2 - OYUNCU PROFILI
# ==============================================================================
if tab2:
    if not st.session_state.get("kulup_giris"):
        giris_gerekli_ekrani()
    else:
        _tum_liste = sorted(df_tam["Oyuncu"].tolist())
        if deneme_modunda() or not tier_yeterli("basic"):
            # Free kademe / deneme: yalnızca vitrin oyuncuları (tam detaylı profil = basic+)
            oyuncu_listesi = [o for o in _tum_liste if o in DENEME_TR_OYUNCULAR]
            st.markdown(
                f"<div style='background:linear-gradient(135deg,#1a0f2e,#2a1145);"
                f"border:1px solid #e040fb;border-radius:12px;padding:13px 18px 6px;margin-bottom:8px;'>"
                f"<div style='color:#e9d5ff;font-size:0.9rem;font-weight:700;'>"
                f"🎁 {t('Açık örnek oyuncular','Sample players unlocked')}</div>"
                f"<div style='color:#a78bfa;font-size:0.78rem;margin-top:2px;'>"
                f"{t('Toplam','Total')} <b>{len(_tum_liste)}</b> {t('TR oyuncusundan','TR players —')} "
                f"<b style='color:#e040fb;'>{len(oyuncu_listesi)}</b> {t('örnek tam açık. Birine tıkla 👇','samples fully open. Tap one 👇')}"
                f"</div></div>", unsafe_allow_html=True)
            # Vitrin oyuncu butonları (tıkla → profil seçilir)
            _vbtn = st.columns(len(oyuncu_listesi)) if oyuncu_listesi else []
            for _bc, _oy in zip(_vbtn, oyuncu_listesi):
                _kisa = " ".join(_oy.title().split()[:2])
                if _bc.button(f"⭐ {_kisa}", key=f"vitrin_tr_{_oy}", width="stretch"):
                    st.session_state["profil_sec"] = _oy
                    st.rerun()
        else:
            oyuncu_listesi = _tum_liste
        # Varsayılan oyuncu: URL'den gelen > Ebru Topçu > listedeki ilk.
        # NOT: selectbox key="profil_sec" olduğundan, session'da geçerli bir değer
        # YOKSA varsayılanı açıkça session'a yazıyoruz (yoksa Streamlit alfabetik/
        # rastgele ilk oyuncuyu — örn. Jelena — sabitliyordu).
        if st.session_state.get("profil_sec") not in oyuncu_listesi:
            if url_oyuncu in oyuncu_listesi:
                _def = url_oyuncu
            else:
                _def = next((o for o in oyuncu_listesi if "EBRU TOP" in o.upper()), None)
                _def = _def or (oyuncu_listesi[0] if oyuncu_listesi else None)
            if _def:
                st.session_state["profil_sec"] = _def
        secili = st.selectbox(t("Oyuncu seç", "Select Player"), oyuncu_listesi,
                              key="profil_sec")
        render_ana_lig_profil(secili)

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 3 — KARŞILAŞTIRMA (2-4 oyuncu)
# ══════════════════════════════════════════════════════════════════════════════
if tab3:
    st.markdown(f"### ⚡ {t('Oyuncu Karşılaştırması', 'Player Comparison')}")
    st.caption(t("2 ile 4 oyuncu arasında seçim yapabilirsiniz.", "You can select between 2 and 4 players."))

    _tum_liste2 = sorted(df_tam["Oyuncu"].tolist())
    if deneme_modunda() or not tier_yeterli("basic"):
        oyuncu_listesi2 = [o for o in _tum_liste2 if o in DENEME_TR_OYUNCULAR]
        VARSAYILAN_OYUNCULAR = oyuncu_listesi2[:4]
        st.markdown(
            f"<div style='background:#e040fb1a;border:1px solid #e040fb;border-radius:10px;"
            f"padding:9px 15px;margin-bottom:8px;color:#e9d5ff;font-size:0.84rem;'>"
            f"🎁 <b>{t('Önizleme','Preview')}</b> — "
            f"{t('yalnızca','only the')} <b>{len(oyuncu_listesi2)}</b> "
            f"{t('örnek oyuncu karşılaştırılabilir (toplam','sample players are comparable (total')} "
            f"{len(_tum_liste2)}).</div>", unsafe_allow_html=True)
    else:
        oyuncu_listesi2 = _tum_liste2
        VARSAYILAN_OYUNCULAR = [
            "EBRU TOPÇU", "ECE TÜRKOĞLU", "DONJETA HALILAJ", "MILICA MIJATOVIC"
        ]
    # Listede bulunanları filtrele, eksikse ilk N oyuncuyla tamamla
    varsayilan = [o for o in VARSAYILAN_OYUNCULAR if o in oyuncu_listesi2]
    if len(varsayilan) < 2:
        varsayilan = oyuncu_listesi2[:4]

    secili_oyuncular = st.multiselect(
        t("Karşılaştırılacak oyuncuları seç (2-4)", "Select players to compare (2-4)"),
        oyuncu_listesi2,
        default=varsayilan,
        max_selections=4,
        key="karsilastirma_sec",
    )

    RENKLER = ["#1db954", "#2979ff", "#ff6d00", "#e040fb"]

    if len(secili_oyuncular) < 2:
        st.info(t("En az 2 oyuncu seçin.", "Select at least 2 players."))
    elif not df_tam.empty:

        # ── Radar chart ──────────────────────────────────────────────────────
        kategoriler = [t("Maç","Matches"), t("Gol","Goals"), t("Gol/Maç","Goals/Match"),
                       t("Dakika","Minutes"), "Starter %", t("Disiplin","Discipline")]

        def norm(oyuncu, metrik):
            r = df_tam[df_tam["Oyuncu"] == oyuncu]
            if r.empty: return 0
            val  = float(r.iloc[0].get(metrik, 0))
            maks = float(df_tam[metrik].max())
            return round(val / maks * 100, 1) if maks else 0

        def radar_degerleri(oyuncu):
            r   = df_tam[df_tam["Oyuncu"] == oyuncu].iloc[0]
            mac = int(r["Maç"])
            return [
                norm(oyuncu, "Maç"),
                norm(oyuncu, "Gol"),
                norm(oyuncu, "Gol/Maç"),
                norm(oyuncu, "Dakika"),
                round(int(r["İlk11"]) / mac * 100, 1) if mac else 0,
                round(100 - norm(oyuncu, "Sarı"), 1),   # az kart = yüksek puan
            ]

        fig = go.Figure()
        for oyuncu, renk in zip(secili_oyuncular, RENKLER):
            dg = radar_degerleri(oyuncu)
            fig.add_trace(go.Scatterpolar(
                r=dg + [dg[0]],
                theta=kategoriler + [kategoriler[0]],
                fill="toself",
                name=oyuncu,
                line=dict(color=renk, width=2.5),
                opacity=0.35,
            ))
        fig.update_layout(
            polar=dict(
                bgcolor="#1a1f36",
                radialaxis=dict(
                    visible=True, range=[0, 100],
                    gridcolor="#2d3561", tickfont=dict(color="#8899aa"),
                    tickvals=[25, 50, 75, 100], ticksuffix="%",
                ),
                angularaxis=dict(tickfont=dict(color="#e0e0e0", size=13), gridcolor="#2d3561"),
            ),
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            font=dict(color="#e0e0e0"),
            legend=dict(orientation="h", y=-0.12, font=dict(size=12)),
            height=480, margin=dict(l=70, r=70, t=30, b=60),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(t("Disiplin = 100 − (sarı kart oranı) · Starter % = ilk 11 oranı · Tüm değerler lig içinde normalize edilmiştir (100 = en iyi).",
                     "Discipline = 100 − (yellow card rate) · Starter % = starting 11 rate · All values normalized within the league (100 = best)."))

        # ── Sayısal karşılaştırma tablosu ────────────────────────────────────
        st.markdown(f"##### 📊 {t('İstatistik Karşılaştırması', 'Stats Comparison')}")

        METRIK_ETIKET = {
            "Maç":     t("Maç","Matches"),
            "İlk11":   f"▶ {t('İlk 11','Starting 11')}",
            "Yedek":   f"↗ {t('Yedek','Sub')}",
            "Gol":     t("Gol","Goals"),
            "GolF":    f"⚽ {t('Ayak (F)','Foot (F)')}",
            "GolH":    f"⚽ {t('Kafa (H)','Header (H)')}",
            "GolP":    f"⚽ {t('Penaltı (P)','Penalty (P)')}",
            "Gol/Maç": t("Gol/Maç","Goals/Match"),
            "Sarı":    f"🟨 {t('Sarı Kart','Yellow Card')}",
            "Kırmızı": f"🟥 {t('Kırmızı','Red Card')}",
            "Dakika":  t("Toplam Dakika","Total Minutes"),
        }
        # Kart sayısı düşük olan iyi → ters metrikler
        TERS = {"Sarı", "Kırmızı"}  # internal column names, stay TR

        _stat_col = t("İstatistik", "Stat")
        tablo_satirlar = []
        for metrik, etiket in METRIK_ETIKET.items():
            satir = {_stat_col: etiket}
            degerler_list = []
            for oy in secili_oyuncular:
                r = df_tam[df_tam["Oyuncu"] == oy]
                val = float(r.iloc[0].get(metrik, 0)) if not r.empty else 0
                degerler_list.append(val)

            # En iyi değeri belirle
            en_iyi = min(degerler_list) if metrik in TERS else max(degerler_list)

            for oy, val in zip(secili_oyuncular, degerler_list):
                # Formatla
                fmt = f"{val:.2f}" if metrik == "Gol/Maç" else f"{int(val)}"
                # En iyi değer vurgusu
                if val == en_iyi and degerler_list.count(en_iyi) < len(degerler_list):
                    fmt = f"★ {fmt}"
                satir[oy] = fmt
            tablo_satirlar.append(satir)

        df_karsilastirma = pd.DataFrame(tablo_satirlar)
        df_karsilastirma = df_karsilastirma.set_index(_stat_col)

        # Oyuncu adlarını renkli başlık olarak göster
        baslik_html = '<div style="display:flex;gap:12px;margin-bottom:8px;flex-wrap:wrap;">'
        for oy, renk in zip(secili_oyuncular, RENKLER):
            baslik_html += (
                f'<span style="background:{renk}22;color:{renk};border:1px solid {renk}44;'
                f'border-radius:6px;padding:4px 12px;font-weight:600;font-size:0.85rem">'
                f'{oy}</span>'
            )
        baslik_html += "</div>"
        st.markdown(baslik_html, unsafe_allow_html=True)
        st.caption(t("★ = o kategoride en iyi", "★ = best in that category"))

        st.dataframe(
            df_karsilastirma,
            width="stretch",
            height=430,
            column_config={
                col: st.column_config.TextColumn(col, width="medium")
                for col in df_karsilastirma.columns
            },
        )

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 4 — TAKIMLAR
# ══════════════════════════════════════════════════════════════════════════════
if tab4:
    st.markdown(f"### 🏟️ {t('Takım Analizi', 'Team Analysis')}")

    if not df_tam.empty:
        takim_listesi_tam = sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_t = st.selectbox(t("Takım seç", "Select Team"), takim_listesi_tam,
                                key="takim_sayfasi", format_func=_takim_kisa)
        df_t = df_tam[df_tam["Takım"] == secili_t].copy()

        st.markdown("---")

        # ── Takım özet istatistikleri ─────────────────────────────────────
        t1, t2, t3, t4, t5 = st.columns(5)
        for kol, sayi, etiket in [
            (t1, len(df_t),                  t("Oyuncu","Players")),
            (t2, int(df_t["Gol"].sum()),      t("Toplam Gol","Total Goals")),
            (t3, int(df_t["Maç"].sum()),      t("Toplam Maç","Total Matches")),
            (t4, int(df_t["Dakika"].sum()),   t("Toplam Dakika","Total Minutes")),
            (t5, int(df_t["Sarı"].sum()),     t("Sarı Kart","Yellow Cards")),
        ]:
            kol.markdown(
                f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                f'<div class="etiket">{etiket}</div></div>',
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        sol, sag = st.columns(2)

        # ── Kadro tablosu ─────────────────────────────────────────────────
        with sol:
            st.markdown(f"##### 👥 {t('Kadro', 'Squad')}")
            kadro = df_t.sort_values("Maç", ascending=False)[
                ["Oyuncu","Mevki","Maç","Gol","Dakika","Sarı"]
            ].reset_index(drop=True)
            if EN:
                kadro["Mevki"] = kadro["Mevki"].map(mevki_goster)
            kadro.index += 1
            df_tablo(kadro, basliklar={"Oyuncu": t("Oyuncu","Player"), "Mevki": t("Mevki","Position"),
                                       "Maç": t("Maç","Matches"), "Gol": t("Gol","Goals"),
                                       "Dakika": t("Dk","Min"), "Sarı": "🟨"})

        # ── Mevki dağılımı + uyruk ─────────────────────────────────────
        with sag:
            st.markdown(f"##### 📊 {t('Mevki Dağılımı', 'Position Distribution')}")
            if "Mevki" in df_t.columns:
                mevki_sayilari = df_t["Mevki"].value_counts()
                MEVKI_RENK = {"Kaleci":"#1db954","Defans":"#2979ff",
                              "Orta Saha":"#ff6d00","Forvet":"#e040fb","Bilinmiyor":"#555"}
                fig_mevki = go.Figure(go.Pie(
                    labels=[mevki_goster(m) for m in mevki_sayilari.index],
                    values=mevki_sayilari.values,
                    marker_colors=[mevki_renk(m) for m in mevki_sayilari.index],
                    textinfo="label+value", textposition="outside",
                    automargin=True, insidetextorientation="horizontal",
                    hole=0.4,
                ))
                fig_mevki.update_layout(
                    paper_bgcolor="#0f1117", font=dict(color="#e0e0e0", size=11),
                    height=240, margin=dict(l=30,r=30,t=24,b=24),
                    showlegend=False)
                st.plotly_chart(fig_mevki, width="stretch")

            st.markdown(f"##### 🌍 {t('Uyruk Dağılımı', 'Nationality Distribution')}")
            if "Uyruk" in df_t.columns:
                uyruk_sayilari = df_t[df_t["Uyruk"]!=""]["Uyruk"].value_counts().head(8)
                fig_uyruk = go.Figure(go.Bar(
                    x=uyruk_sayilari.values,
                    y=uyruk_sayilari.index,
                    orientation="h",
                    marker_color="#2979ff",
                    text=uyruk_sayilari.values,
                    textposition="outside",
                ))
                fig_uyruk.update_layout(
                    paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=250,
                    xaxis=dict(gridcolor="#2d3561"),
                    yaxis=dict(gridcolor="#2d3561"),
                    margin=dict(l=10,r=30,t=10,b=10))
                st.plotly_chart(fig_uyruk, width="stretch")

        # ── Scatter: verimlilik ────────────────────────────────────────
        st.markdown("---")
        st.markdown(f"##### ⚡ {t('Dakika-Gol Verimliliği', 'Minutes-Goals Efficiency')}")
        fig_s = go.Figure()
        _df_t_grup = (df_t["Mevki"].map(mevki_grup) if "Mevki" in df_t.columns
                      else pd.Series("Bilinmiyor", index=df_t.index))
        for mevki, renk in [("Kaleci","#1db954"),("Defans","#2979ff"),
                              ("Orta Saha","#ff6d00"),("Forvet","#e040fb"),("Bilinmiyor","#555")]:
            alt = df_t[_df_t_grup == mevki]
            if alt.empty: continue
            fig_s.add_trace(go.Scatter(
                x=alt["Dakika"], y=alt["Gol"],
                mode="markers+text", name=mevki_goster(mevki),
                marker=dict(color=renk, size=10),
                text=alt["Oyuncu"].str.split().str[-1],
                textposition="top center", textfont=dict(size=9),
                hovertemplate="%{text}<br>%{x} " + t("dk","min") + ", %{y} " + t("gol","goals") + "<extra></extra>",
            ))
        fig_s.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
            font=dict(color="#e0e0e0"), height=380,
            xaxis=dict(title="Toplam Dakika", gridcolor="#2d3561"),
            yaxis=dict(title="Toplam Gol", gridcolor="#2d3561"),
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=40,r=20,t=40,b=40))
        st.plotly_chart(fig_s, width="stretch")

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 5 — LİG TABLOSU
# ══════════════════════════════════════════════════════════════════════════════
if tab5:
    st.markdown(f"### {t('Puan Durumu', 'League Standings')}")

    # Oyuncu verisinden takım istatistikleri hesapla
    if not df_tam.empty:
        takim_ozet = df_tam.groupby("Takım").agg(
            Oyuncu=("Oyuncu", "count"),
            TopGol=("Gol", "sum"),
            TopDk=("Dakika", "sum"),
            TopSari=("Sarı", "sum"),
            TopKirmizi=("Kırmızı", "sum"),
        ).reset_index().sort_values("TopGol", ascending=False)

        # Kolon adları iç-anahtar olarak TR kalır; görünen etiketler column_config'te çevrilir
        takim_ozet.columns = ["Takım","Oyuncu Sayısı","Toplam Gol","Toplam Dakika","Sarı Kart","Kırmızı Kart"]
        takim_ozet["Takım"] = takim_ozet["Takım"].map(_takim_kisa)
        takim_ozet.index = range(1, len(takim_ozet)+1)

        st.markdown(f"#### {t('Takım Bazlı Sezon İstatistikleri', 'Season Stats by Team')}")
        df_tablo(takim_ozet, basliklar={"Takım": t("Takım","Team"), "Oyuncu Sayısı": t("Kadro","Squad"),
                                        "Toplam Gol": t("Toplam Gol","Total Goals"),
                                        "Toplam Dakika": t("Toplam Dk","Total Min"),
                                        "Sarı Kart": "🟨", "Kırmızı Kart": "🟥"})

        st.markdown("<br>", unsafe_allow_html=True)

        # TFF'den resmi puan cetveli
        st.markdown(f"#### 🏆 {t('TFF Resmi Puan Cetveli', 'TFF Official Standings')}")
        with st.spinner(t("TFF'den yükleniyor...", "Loading from TFF...")):
            df_puan = puan_durumu_cek()

        if not df_puan.empty:
            df_puan = df_puan.copy()
            if "" in df_puan.columns:
                df_puan[""] = df_puan[""].map(_takim_kisa)
            # Sütun adlarını düzelt — O G B M A Y AV P
            sutun_aciklama = {
                "O": t("O — Oynadı","P — Played"), "G": t("G — Galibiyet","W — Won"), "B": t("B — Beraberlik","D — Draw"),
                "M": t("M — Mağlubiyet","L — Lost"), "A": t("A — Atılan","GF — Goals For"), "Y": t("Y — Yenilen","GA — Goals Ag."),
                "AV": t("AV — Averaj","GD — Goal Diff"), "P": t("P — Puan","Pts — Points"),
            }
            df_puan.index = range(1, len(df_puan) + 1)
            df_tablo(df_puan, basliklar={col: sutun_aciklama.get(col, col) for col in df_puan.columns})
            st.caption(t("Kaynak: TFF — tff.org | O=Oynadı · G=Galibiyet · B=Beraberlik · M=Mağlubiyet · A=Atılan · Y=Yenilen · AV=Averaj · P=Puan",
                         "Source: TFF — tff.org | P=Played · W=Won · D=Draw · L=Lost · GF=Goals For · GA=Goals Ag. · GD=Goal Diff · Pts=Points"))
        else:
            st.caption(t("TFF puan cetveli yüklenemedi.", "Could not load TFF standings."))

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 6 — EN İYİLER
# ══════════════════════════════════════════════════════════════════════════════
if tab6:
    st.markdown(f"### 🌟 {t('2025-2026 Sezonu En İyileri', '2025-2026 Season Top Performers')}")
    if df_tam.empty:
        st.info(t("Veri yok.", "No data."))
    elif deneme_modunda() or not tier_yeterli("basic"):
        deneme_kilit(t("🌟 En İyiler", "🌟 Top Performers"), "tr")
    else:
        # ── Lig Geneli Verimlilik Scatter ──────────────────────────────
        st.markdown(f"#### ⚡ {t('Tüm Ligde Dakika-Gol Verimliliği', 'Minutes-Goals Efficiency Across the League')}")
        st.caption(t("Sağ üst = hem çok oynadı hem çok gol attı. Her renk bir mevki.",
                     "Top right = played a lot and scored a lot. Each color represents a position."))
        fig_lig = go.Figure()
        MEVKI_RENK = {"Kaleci":"#1db954","Defans":"#2979ff",
                      "Orta Saha":"#ff6d00","Forvet":"#e040fb","Bilinmiyor":"#555555"}
        _df_tam_grup = (df_tam["Mevki"].map(mevki_grup) if "Mevki" in df_tam.columns
                        else pd.Series("Bilinmiyor", index=df_tam.index))
        for mevki, renk in MEVKI_RENK.items():
            alt = df_tam[_df_tam_grup == mevki] if "Mevki" in df_tam.columns else pd.DataFrame()
            if alt.empty: continue
            fig_lig.add_trace(go.Scatter(
                x=alt["Dakika"], y=alt["Gol"],
                mode="markers", name=mevki_goster(mevki),
                marker=dict(color=renk, size=7, opacity=0.8),
                text=alt["Oyuncu"],
                hovertemplate="%{text}<br>%{x} " + t("dk","min") + " · %{y} " + t("gol","goals") + "<extra></extra>",
            ))
        # En golcülerin etiketini göster
        top10 = df_tam.nlargest(10, "Gol")
        fig_lig.add_trace(go.Scatter(
            x=top10["Dakika"], y=top10["Gol"],
            mode="text", showlegend=False,
            text=top10["Oyuncu"].str.split().str[-1],
            textposition="top center", textfont=dict(size=9, color="#e0e0e0"),
        ))
        fig_lig.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
            font=dict(color="#e0e0e0"), height=420,
            xaxis=dict(title="Toplam Dakika", gridcolor="#2d3561"),
            yaxis=dict(title="Toplam Gol",    gridcolor="#2d3561"),
            legend=dict(orientation="h", y=1.08),
            margin=dict(l=40,r=20,t=40,b=40))
        st.plotly_chart(fig_lig, width="stretch")

        # ── Uyruk Analizi ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown(f"#### 🌍 {t('Uyruk Dağılımı', 'Nationality Distribution')}")
        if "Uyruk" in df_tam.columns:
            ua, ub = st.columns(2)
            with ua:
                st.markdown(f"**{t('Oyuncu sayısına göre', 'By number of players')}**")
                uyruk_sayi = df_tam[df_tam["Uyruk"]!=""]["Uyruk"].value_counts().head(15)
                fig_u = go.Figure(go.Bar(
                    x=uyruk_sayi.values, y=uyruk_sayi.index,
                    orientation="h", marker_color="#2979ff",
                    text=uyruk_sayi.values, textposition="outside",
                ))
                fig_u.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=400,
                    xaxis=dict(gridcolor="#2d3561"), yaxis=dict(gridcolor="#2d3561"),
                    margin=dict(l=10,r=40,t=10,b=10))
                st.plotly_chart(fig_u, width="stretch")
            with ub:
                st.markdown(f"**{t('Gol sayısına göre', 'By number of goals')}**")
                uyruk_gol = df_tam[df_tam["Uyruk"]!=""].groupby("Uyruk")["Gol"].sum().sort_values(ascending=False).head(15)
                fig_ug = go.Figure(go.Bar(
                    x=uyruk_gol.values, y=uyruk_gol.index,
                    orientation="h", marker_color="#1db954",
                    text=uyruk_gol.values, textposition="outside",
                ))
                fig_ug.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=400,
                    xaxis=dict(gridcolor="#2d3561"), yaxis=dict(gridcolor="#2d3561"),
                    margin=dict(l=10,r=40,t=10,b=10))
                st.plotly_chart(fig_ug, width="stretch")

        st.markdown("---")
        # Yardımcı: top-N kart
        def en_iyi_kart(baslik, df_siralali, sutunlar, ikon="🥇"):
            st.markdown(f"#### {ikon} {baslik}")
            df_siralali = df_siralali.reset_index(drop=True)
            df_siralali.index += 1
            rozetler = ["🥇","🥈","🥉","4.","5."]
            for i, (_, row) in enumerate(df_siralali.iterrows()):
                degerler = " · ".join(f"**{row[s]}**" for s in sutunlar if s in row)
                st.markdown(
                    f'<div style="background:#1a1f36;border-radius:8px;padding:10px 14px;'
                    f'margin-bottom:6px;display:flex;justify-content:space-between;align-items:center">'
                    f'<span style="font-size:1.1rem">{rozetler[i]} {row["Oyuncu"]}'
                    f'<span style="color:#8899aa;font-size:0.78rem;margin-left:8px">{_takim_kisa(row["Takım"])}</span></span>'
                    f'<span style="color:#1db954;font-weight:600">{degerler}</span></div>',
                    unsafe_allow_html=True
                )

        # ── Satır 1 ──────────────────────────────────────────────────────────
        r1c1, r1c2, r1c3 = st.columns(3)

        with r1c1:
            # Yalnız golü olanlar — gol kraliçesinde 0-gollü asla çıkmasın (garantili)
            en_iyi_kart(t("Gol Kraliçesi","Top Scorer"),
                df_tam[df_tam["Gol"] > 0].nlargest(5,"Gol")[["Oyuncu","Takım","Gol","GolF","GolH","GolP"]],
                ["Gol"], "⚽")

        with r1c2:
            en_iyi_kart(t("En Çok Oynayan","Most Minutes"),
                df_tam.nlargest(5,"Dakika")[["Oyuncu","Takım","Dakika","Maç"]],
                ["Dakika","Maç"], "🏃")

        with r1c3:
            # Min 10 maç şartı
            df_ort = df_tam[df_tam["Maç"]>=10].nlargest(5,"Gol/Maç")[["Oyuncu","Takım","Gol/Maç","Gol","Maç"]]
            en_iyi_kart(t("En İyi Gol Ortalaması","Best Goals/Match"),
                df_ort, ["Gol/Maç"], "🎯")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Satır 2 ──────────────────────────────────────────────────────────
        r2c1, r2c2, r2c3 = st.columns(3)

        with r2c1:
            en_iyi_kart(t("Kafa Golü Uzmanı","Header Specialist"),
                df_tam[df_tam["GolH"]>0].nlargest(5,"GolH")[["Oyuncu","Takım","GolH","Gol"]],
                ["GolH"], "🆕")

        with r2c2:
            en_iyi_kart(t("Penaltı Uzmanı","Penalty Specialist"),
                df_tam[df_tam["GolP"]>0].nlargest(5,"GolP")[["Oyuncu","Takım","GolP","Gol"]],
                ["GolP"], "🥅")

        with r2c3:
            # En temiz oyuncu: sarı kart almadan en çok dakika
            df_temiz = df_tam[(df_tam["Sarı"]==0) & (df_tam["Kırmızı"]==0) & (df_tam["Maç"]>=10)]
            en_iyi_kart(t("Disiplin Şampiyonu","Discipline Champion"),
                df_temiz.nlargest(5,"Dakika")[["Oyuncu","Takım","Dakika","Maç"]],
                ["Dakika"], "🛡️")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Satır 3 ──────────────────────────────────────────────────────────
        r3c1, r3c2, r3c3 = st.columns(3)

        with r3c1:
            # Starter şampiyonu: en yüksek ilk 11 oranı (min 15 maç)
            df_s = df_tam[df_tam["Maç"]>=15].copy()
            df_s["Starter%"] = (df_s["İlk11"] / df_s["Maç"] * 100).round(1)
            en_iyi_kart(t("Starter Şampiyonu","Starter Champion"),
                df_s.nlargest(5,"Starter%")[["Oyuncu","Takım","Starter%","Maç"]],
                ["Starter%"], "▶️")

        with r3c2:
            # En çok ardışık gol serisi
            seri_data = []
            for o in ham_liste:
                gecmis = sorted(o.get("mac_gecmisi",[]), key=lambda x: x["hafta"])
                gol_seri = max_seri([1 if m["gol"]>0 else 0 for m in gecmis])
                if gol_seri >= 2:
                    seri_data.append({
                        "Oyuncu": o["oyuncu"],
                        "Takım":  _takim_kisa(o["takim"]),
                        "Gol Serisi": gol_seri,
                        "Toplam Gol": o["gol_sayisi"],
                    })
            if seri_data:
                df_seri = pd.DataFrame(seri_data).nlargest(5,"Gol Serisi")
                en_iyi_kart(t("En Uzun Gol Serisi","Longest Scoring Streak"),
                    df_seri[["Oyuncu","Takım","Gol Serisi","Toplam Gol"]],
                    ["Gol Serisi"], "🔥")

        with r3c3:
            # En çok temiz seri (kart almadan ardışık maç)
            temiz_seri_data = []
            for o in ham_liste:
                gecmis = sorted(o.get("mac_gecmisi",[]), key=lambda x: x["hafta"])
                temiz = [1 if m["sari"]==0 and m["kirmizi"]==0 else 0 for m in gecmis]
                en_uzun = max_seri(temiz)
                if en_uzun >= 5:
                    temiz_seri_data.append({
                        "Oyuncu": o["oyuncu"],
                        "Takım":  _takim_kisa(o["takim"]),
                        "Temiz Seri": en_uzun,
                        "Toplam Maç": o["mac_sayisi"],
                    })
            if temiz_seri_data:
                df_temiz_s = pd.DataFrame(temiz_seri_data).nlargest(5,"Temiz Seri")
                en_iyi_kart(t("En Uzun Kart Almama Serisi","Longest Card-Free Streak"),
                    df_temiz_s[["Oyuncu","Takım","Temiz Seri","Toplam Maç"]],
                    ["Temiz Seri"], "🧹")

        # ── Takım başına en golcü ─────────────────────────────────────────────
        st.markdown("<br>")
        st.markdown(f"#### 🏟️ {t('Her Takımın Gol Kraliçesi', 'Top Scorer per Team')}")
        takimlar_s = sorted(df_tam["Takım"].dropna().unique())
        # Golü olan takımlar (hiç gol atmayan takımda 0-gollü "kraliçe" çıkmasın)
        _golcu_takimlar = [tk for tk in takimlar_s
                           if not df_tam[df_tam["Takım"] == tk].empty
                           and int(df_tam[df_tam["Takım"] == tk]["Gol"].max()) > 0]
        cols = st.columns(min(4, len(_golcu_takimlar))) if _golcu_takimlar else [st]
        for idx, takim in enumerate(_golcu_takimlar):
            with cols[idx % 4]:
                df_t = df_tam[df_tam["Takım"]==takim].nlargest(1,"Gol")
                if not df_t.empty and int(df_t.iloc[0]["Gol"]) > 0:
                    r = df_t.iloc[0]
                    st.markdown(
                        f'<div style="background:#1a1f36;border-radius:8px;padding:10px;'
                        f'margin-bottom:8px;border-top:2px solid #1db954">'
                        f'<div style="color:#8899aa;font-size:0.68rem">{takim[:30]}</div>'
                        f'<div style="font-weight:600;font-size:0.9rem;margin:3px 0">{r["Oyuncu"]}</div>'
                        f'<div style="color:#1db954;font-size:0.82rem">⚽ {int(r["Gol"])} {t("gol","goals")}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 7 — FANTASY KADRO
# ══════════════════════════════════════════════════════════════════════════════
if tab7:
    st.markdown(f"### ⚽ {t('Fantasy Kadro Kur', 'Build Fantasy Squad')}")
    st.caption(t("Dizilişini seç, oyuncuları ata — saha gerçek zamanlı güncellenir.",
                 "Choose your formation, assign players — the pitch updates in real time."))

    if df_tam.empty:
        st.info(t("Veri yok.", "No data."))
    else:
        # ── Pitch koordinat sistemi: W=68m, H=105m ────────────────────
        W, H = 68, 105
        # Padding için görünüm aralığı
        XR = [-4, 72]; YR = [-8, 113]

        # Her slot: (etiket, filtre_mevki, x_pitch, y_pitch)
        FORMASYON = {
            "4-3-3": [
                ("Kaleci",    "Kaleci",    34, 8),
                ("Sol Bek",   "Defans",    10, 27), ("Sol-OB",   "Defans",  25, 27),
                ("Sağ-OB",    "Defans",    43, 27), ("Sağ Bek",  "Defans",  58, 27),
                ("Sol OM",    "Orta Saha", 16, 56), ("Merkez OM","Orta Saha",34,56),
                ("Sağ OM",    "Orta Saha", 52, 56),
                ("Sol Kanat", "Forvet",    12, 83), ("Santrafor","Forvet",   34,83),
                ("Sağ Kanat", "Forvet",    56, 83),
            ],
            "4-4-2": [
                ("Kaleci",    "Kaleci",    34, 8),
                ("Sol Bek",   "Defans",    10, 27), ("Sol-OB",   "Defans",  25, 27),
                ("Sağ-OB",    "Defans",    43, 27), ("Sağ Bek",  "Defans",  58, 27),
                ("Sol OM",    "Orta Saha", 10, 56), ("Sol-Merkez","Orta Saha",25,56),
                ("Sağ-Merkez","Orta Saha", 43, 56), ("Sağ OM",  "Orta Saha",58,56),
                ("Sol Santr", "Forvet",    24, 83), ("Sağ Santr","Forvet",   44,83),
            ],
            "3-5-2": [
                ("Kaleci",    "Kaleci",    34, 8),
                ("Sol-OB",    "Defans",    17, 27), ("Merkez-OB","Defans",   34,27),
                ("Sağ-OB",    "Defans",    51, 27),
                ("Sol K.",    "Orta Saha",  7, 56), ("Sol OM",  "Orta Saha", 21,56),
                ("Merkez OM", "Orta Saha", 34, 56), ("Sağ OM",  "Orta Saha",47,56),
                ("Sağ K.",    "Orta Saha", 61, 56),
                ("Sol Santr", "Forvet",    24, 83), ("Sağ Santr","Forvet",   44,83),
            ],
            "4-2-3-1": [
                ("Kaleci",    "Kaleci",    34, 8),
                ("Sol Bek",   "Defans",    10, 25), ("Sol-OB",   "Defans",  25, 25),
                ("Sağ-OB",    "Defans",    43, 25), ("Sağ Bek",  "Defans",  58, 25),
                ("Def OM-1",  "Orta Saha", 24, 48), ("Def OM-2","Orta Saha",44,48),
                ("Sol Kanat", "Forvet",    10, 68), ("Ofansif OM","Orta Saha",34,68),
                ("Sağ Kanat", "Forvet",    58, 68),
                ("Santrafor", "Forvet",    34, 88),
            ],
            "4-1-2-3": [
                ("Kaleci",    "Kaleci",    34,  8),
                ("Sol Bek",   "Defans",    10, 25), ("Sol-OB",   "Defans",   25, 25),
                ("Sağ-OB",    "Defans",    43, 25), ("Sağ Bek",  "Defans",   58, 25),
                ("Def OM",    "Orta Saha", 34, 43),
                ("Sol OM",    "Orta Saha", 19, 61), ("Sağ OM",   "Orta Saha",49, 61),
                ("Sol Kanat", "Forvet",    12, 82), ("Santrafor","Forvet",    34, 82),
                ("Sağ Kanat", "Forvet",    56, 82),
            ],
        }
        MEVKI_RENK_F = {
            "Kaleci":    "#ffd700",
            "Defans":    "#2979ff",
            "Orta Saha": "#ff6d00",
            "Forvet":    "#e040fb",
        }

        # ── Layout: Sol seçici, Sağ saha ───────────────────────────────
        col_sol, col_sag = st.columns([4, 6])

        with col_sol:
            formasyon_sec = st.selectbox(t("Diziliş","Formation"), list(FORMASYON.keys()), key="ff_formasyon")
            slotlar = FORMASYON[formasyon_sec]

            # Hoca seçimi
            hoca_listesi = tum_hocalar()
            if hoca_listesi:
                _hoca_sec_sentinel = t("— Hoca seç —", "— Select coach —")
                secili_hoca = st.selectbox(
                    f"🧑‍💼 {t('Teknik Direktör','Head Coach')}",
                    [_hoca_sec_sentinel] + hoca_listesi,
                    key="ff_hoca",
                )
            else:
                secili_hoca = st.text_input(f"🧑‍💼 {t('Teknik Direktör','Head Coach')}", key="ff_hoca_text",
                                            placeholder=t("Hoca adı girin...","Enter coach name..."))
            st.markdown("---")

            secimler   = {}
            zaten_sec  = set()
            GRUP_IKON  = {"Kaleci":"🧤","Defans":"🛡️","Orta Saha":"⚙️","Forvet":"⚽"}
            onceki_grp = None

            for etiket, mevki, px, py in slotlar:
                if mevki != onceki_grp:
                    st.markdown(f"**{GRUP_IKON.get(mevki,'')} {mevki_goster(mevki)}**")
                    onceki_grp = mevki
                if "Mevki" in df_tam.columns:
                    _grup_ser   = df_tam["Mevki"].map(mevki_grup)
                    _eslesen    = sorted(df_tam[_grup_ser == mevki]["Oyuncu"].tolist())
                    _bilinmeyen = sorted(df_tam[_grup_ser == "Bilinmiyor"]["Oyuncu"].tolist())
                    havuz = _eslesen + _bilinmeyen
                else:
                    havuz = sorted(df_tam["Oyuncu"].tolist())
                secenekler = ["—"] + [o for o in havuz if o not in zaten_sec]
                secim = st.selectbox(etiket, secenekler, key=f"ff_{etiket}",
                                     label_visibility="collapsed")
                secimler[etiket] = secim
                if secim != "—":
                    zaten_sec.add(secim)

        with col_sag:
            # ════════════════════════════════════════════════════════
            # SAHA ÇİZİMİ
            # ════════════════════════════════════════════════════════
            fig = go.Figure()

            # ── Çim şeritleri (dekoratif) ──────────────────────────
            serit_h = H / 7
            for i in range(8):
                renk = "#2a7a26" if i % 2 == 0 else "#238f1f"
                fig.add_shape(type="rect",
                    x0=0, y0=i*serit_h, x1=W, y1=min((i+1)*serit_h, H),
                    fillcolor=renk, line_width=0, layer="below")

            # ── Saha sınırı ────────────────────────────────────────
            CIZGI = dict(color="rgba(255,255,255,0.9)", width=2)
            fig.add_shape(type="rect", x0=0, y0=0, x1=W, y1=H,
                          fillcolor="rgba(0,0,0,0)", line=CIZGI)

            # ── Orta çizgi ─────────────────────────────────────────
            fig.add_shape(type="line", x0=0, y0=H/2, x1=W, y1=H/2, line=CIZGI)

            # ── Orta daire ─────────────────────────────────────────
            r = 9.15
            fig.add_shape(type="circle",
                x0=W/2-r, y0=H/2-r, x1=W/2+r, y1=H/2+r,
                fillcolor="rgba(0,0,0,0)", line=CIZGI)
            # Orta nokta
            fig.add_trace(go.Scatter(x=[W/2], y=[H/2], mode="markers",
                marker=dict(size=5, color="white"), showlegend=False,
                hoverinfo="skip"))

            # ── Ceza sahaları ──────────────────────────────────────
            for y0, y1 in [(0, 16.5), (H-16.5, H)]:
                fig.add_shape(type="rect",
                    x0=13.84, y0=y0, x1=54.16, y1=y1,
                    fillcolor="rgba(0,0,0,0)", line=CIZGI)
            # 6 yard kutuları
            for y0, y1 in [(0, 5.5), (H-5.5, H)]:
                fig.add_shape(type="rect",
                    x0=24.84, y0=y0, x1=43.16, y1=y1,
                    fillcolor="rgba(0,0,0,0)", line=CIZGI)

            # ── Kaleler ────────────────────────────────────────────
            KALE = dict(color="white", width=3)
            for y0, y1 in [(-2.44, 0), (H, H+2.44)]:
                fig.add_shape(type="rect",
                    x0=30.34, y0=y0, x1=37.66, y1=y1,
                    fillcolor="rgba(255,255,255,0.15)", line=KALE)

            # ── Penaltı noktaları ──────────────────────────────────
            for py in [11, H-11]:
                fig.add_trace(go.Scatter(x=[W/2], y=[py], mode="markers",
                    marker=dict(size=5, color="white"), showlegend=False, hoverinfo="skip"))

            # ── Köşe yayları ───────────────────────────────────────
            import math
            for cx, cy, a1, a2 in [(0,0,0,90),(W,0,90,180),(0,H,270,360),(W,H,180,270)]:
                thetas = [math.radians(a) for a in range(a1, a2+1, 5)]
                fig.add_trace(go.Scatter(
                    x=[cx + math.cos(t) for t in thetas],
                    y=[cy + math.sin(t) for t in thetas],
                    mode="lines", line=dict(color="white", width=1.5),
                    showlegend=False, hoverinfo="skip"))

            # ── Diziliş etiketi (üst) ─────────────────────────────
            fig.add_annotation(x=W/2, y=H+5, text=formasyon_sec,
                showarrow=False, font=dict(size=16, color="white", family="Arial Black"),
                bgcolor="rgba(0,0,0,0.4)", borderpad=4)

            # ── Hoca etiketi (alt) ─────────────────────────────────
            hoca_goster = ""
            if "ff_hoca" in st.session_state:
                h = st.session_state["ff_hoca"]
                if h and h not in ("— Hoca seç —", "— Select coach —"):
                    hoca_goster = h
            elif "ff_hoca_text" in st.session_state:
                hoca_goster = st.session_state.get("ff_hoca_text","")
            if hoca_goster:
                fig.add_annotation(
                    x=W/2, y=-5.5,
                    text=f"🧑‍💼 <b>{hoca_goster}</b>",
                    showarrow=False,
                    font=dict(size=13, color="white", family="Arial"),
                    bgcolor="rgba(0,0,0,0.5)", borderpad=5,
                )

            # ── Oyuncu daireleri ───────────────────────────────────
            for etiket, mevki, px, py in slotlar:
                oyuncu = secimler.get(etiket, "—")
                dolu   = oyuncu != "—"
                renk   = MEVKI_RENK_F.get(mevki, "#aaa")

                if dolu:
                    hover        = f"<b>{oyuncu}</b><br>{etiket}"
                    marker_renk  = renk
                    border_renk  = "white"
                    border_kalin = 2.5
                    opak         = 1.0
                    # Tam isim — iki satıra böl (ad / soyad)
                    parcalar = oyuncu.title().split()
                    if len(parcalar) >= 2:
                        # İlk kelime(ler) + son kelime ayrı satır
                        isim_ust = " ".join(parcalar[:-1])
                        isim_alt = parcalar[-1]
                    else:
                        isim_ust = parcalar[0]
                        isim_alt = ""
                else:
                    hover        = etiket
                    marker_renk  = "rgba(40,40,40,0.6)"
                    border_renk  = "rgba(255,255,255,0.35)"
                    border_kalin = 1.5
                    opak         = 0.7
                    isim_ust     = ""
                    isim_alt     = ""

                # Daire
                fig.add_trace(go.Scatter(
                    x=[px], y=[py], mode="markers",
                    marker=dict(
                        size=44,
                        color=marker_renk,
                        opacity=opak,
                        line=dict(color=border_renk, width=border_kalin),
                    ),
                    hovertext=hover, hoverinfo="text",
                    showlegend=False,
                ))

                # Tam isim — daire içinde iki satır
                if dolu:
                    # Üst satır (ad)
                    fig.add_annotation(
                        x=px, y=py + 1.8,
                        text=f"<b>{isim_ust}</b>",
                        showarrow=False,
                        font=dict(size=8.5, color="white", family="Arial"),
                        bgcolor="rgba(0,0,0,0)",
                    )
                    # Alt satır (soyad, daha büyük)
                    if isim_alt:
                        fig.add_annotation(
                            x=px, y=py - 1.8,
                            text=f"<b>{isim_alt}</b>",
                            showarrow=False,
                            font=dict(size=9.5, color="white", family="Arial Black"),
                            bgcolor="rgba(0,0,0,0)",
                        )

                # Mevki etiketi (daire altında)
                fig.add_annotation(
                    x=px, y=py - 7.5,
                    text=etiket,
                    showarrow=False,
                    font=dict(size=7.5,
                              color="rgba(255,255,255,0.85)" if dolu else "rgba(255,255,255,0.4)"),
                )

            # ── Lejant ────────────────────────────────────────────
            for i, (mevki, renk) in enumerate(MEVKI_RENK_F.items()):
                fig.add_trace(go.Scatter(
                    x=[None], y=[None], mode="markers",
                    marker=dict(size=10, color=renk),
                    name=mevki, showlegend=True,
                ))

            fig.update_layout(
                paper_bgcolor="#0f1117",
                plot_bgcolor="#238f1f",
                height=600,
                margin=dict(l=0, r=0, t=10, b=10),
                xaxis=dict(range=XR, showgrid=False, zeroline=False,
                           showticklabels=False, fixedrange=True),
                yaxis=dict(range=YR, showgrid=False, zeroline=False,
                           showticklabels=False, fixedrange=True,
                           scaleanchor="x", scaleratio=1),
                legend=dict(orientation="h", y=-0.02, font=dict(color="#e0e0e0"),
                            bgcolor="rgba(0,0,0,0.4)"),
                hoverlabel=dict(bgcolor="#1a1f36", font_color="white"),
            )
            st.plotly_chart(fig, width="stretch")

        # ── İstatistikler ──────────────────────────────────────────────
        secili_isimler = [v for v in secimler.values() if v != "—"]
        if secili_isimler:
            st.markdown("---")
            st.markdown(f"##### 📊 {t('Kadro İstatistikleri','Squad Stats')} — {len(secili_isimler)}/11 {t('oyuncu seçildi','players selected')}")
            df_kadro = df_tam[df_tam["Oyuncu"].isin(secili_isimler)].copy()

            k1, k2, k3, k4, k5 = st.columns(5)
            for kol, sayi, etiket in [
                (k1, int(df_kadro["Gol"].sum()),    t("Toplam Gol","Total Goals")),
                (k2, int(df_kadro["Maç"].sum()),    t("Toplam Maç","Total Matches")),
                (k3, int(df_kadro["Dakika"].sum()), t("Toplam Dakika","Total Minutes")),
                (k4, int(df_kadro["Sarı"].sum()),   t("Sarı Kart","Yellow Cards")),
                (k5, round(df_kadro["Gol/Maç"].mean(),2) if not df_kadro.empty else 0, t("Ort. Gol/Maç","Avg. Goals/Match")),
            ]:
                kol.markdown(
                    f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                    f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            goster = df_kadro[["Oyuncu","Takım","Mevki","Gol","Maç","Gol/Maç","Dakika","Sarı"]].copy()
            _grup_sira = {"Kaleci":0,"Defans":1,"Orta Saha":2,"Forvet":3,"Bilinmiyor":4}
            goster["_s"] = goster["Mevki"].map(lambda m: _grup_sira.get(mevki_grup(m), 4))
            goster = goster.sort_values("_s").drop(columns="_s").reset_index(drop=True)
            goster.index += 1
            df_tablo(goster, basliklar={"Oyuncu": t("Oyuncu","Player"), "Takım": t("Takım","Team"),
                                        "Mevki": t("Mevki","Position"), "Gol": t("Gol","Goals"),
                                        "Maç": t("Maç","Matches"), "Gol/Maç": "G/M",
                                        "Dakika": t("Dk","Min"), "Sarı": "🟨"},
                     formatlar={"Gol/Maç": lambda v: f"{v:.2f}"})
        else:
            st.info(t("Soldan oyuncu seçmeye başla — saha canlı güncellenecek.",
                      "Start picking players on the left — the pitch updates live."))


# ══════════════════════════════════════════════════════════════════════════════
# SEKME — BENİM KADROM (sadece giriş yapanlara)
# ══════════════════════════════════════════════════════════════════════════════
if tab_benim:
    if True:
        kulup_takim = st.session_state.get("kulup_takim","")
        kulup_ad    = st.session_state.get("kulup_ad","")
        _rol        = st.session_state.get("kulup_kullanici","")

        # ── ADMIN GÖRÜNÜMÜ ────────────────────────────────────────
        if _rol == "admin":
            st.markdown(f"##### 🛡️ {t('Admin Paneli — Tüm Lig Özeti', 'Admin Panel — Full League Overview')}")
            if not df_tam.empty:
                k1,k2,k3,k4 = st.columns(4)
                for kol,sayi,etiket in [
                    (k1, len(df_tam),              t("Toplam Oyuncu","Total Players")),
                    (k2, df_tam["Takım"].nunique(), t("Takım","Teams")),
                    (k3, int(df_tam["Gol"].sum()),  t("Toplam Gol","Total Goals")),
                    (k4, int(df_tam["Maç"].sum()),  t("Toplam Maç","Total Matches")),
                ]:
                    kol.markdown(
                        f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                        f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"**{t('Takım Bazlı Gol Sıralaması', 'Goals by Team')}**")
                takim_gol = (df_tam.groupby("Takım")["Gol"].sum()
                             .sort_values(ascending=False).reset_index())
                fig_admin = go.Figure(go.Bar(
                    x=takim_gol["Gol"], y=takim_gol["Takım"], orientation="h",
                    marker=dict(color="#1db954"),
                    text=takim_gol["Gol"], textposition="outside",
                    textfont=dict(color="#e0e0e0"),
                ))
                fig_admin.update_layout(
                    paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                    xaxis=dict(showgrid=False, color="#505870"),
                    yaxis=dict(color="#e0e0e0"),
                    margin=dict(l=10,r=40,t=5,b=5), height=420,
                    font=dict(color="#e0e0e0"),
                )
                st.plotly_chart(fig_admin, width="stretch")

        else:
            # ── KULÜP GÖRÜNÜMÜ ────────────────────────────────────────
            st.markdown(f"##### 🏟️ {kulup_ad} — {t('Kadro Paneli', 'Squad Panel')}")
            st.caption(f"2025-26 {t('sezonu','season')} · {kulup_takim}")

            _tk_kelime = (kulup_takim or "").split()
            kadro = df_tam[df_tam["Takım"].str.contains(
                _tk_kelime[0], case=False, na=False
            )].copy() if (not df_tam.empty and _tk_kelime) else pd.DataFrame()

            if kadro.empty:
                if not _tk_kelime:   # üye (kulüp değil) → tanımlı takım yok
                    st.info(t("Bu panel kulüp hesapları içindir — hesabında tanımlı takım yok. "
                              "Üyeliğin tüm veri ve scouting araçlarına erişim verir.",
                              "This panel is for club accounts — no team is set on your account. "
                              "Your membership gives access to all data and scouting tools."))
                else:
                    st.warning(t("Kadro verisi bulunamadı.", "Squad data not found."))
            else:
                k1,k2,k3,k4,k5 = st.columns(5)
                en_golcu = kadro.loc[kadro["Gol"].idxmax(),"Oyuncu"] if kadro["Gol"].max()>0 else "—"
                for kol,sayi,etiket in [
                    (k1, len(kadro),                t("Oyuncu","Players")),
                    (k2, int(kadro["Gol"].sum()),   t("Toplam Gol","Total Goals")),
                    (k3, int(kadro["Maç"].sum()),   t("Toplam Maç","Total Matches")),
                    (k4, int(kadro["Dakika"].sum()),t("Toplam Dakika","Total Minutes")),
                    (k5, en_golcu,                  t("En Golcü","Top Scorer")),
                ]:
                    kol.markdown(
                        f'<div class="stat-kart"><div class="sayi" style="font-size:1.2rem">{sayi}</div>'
                        f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                col_k, col_g = st.columns([3,2], gap="large")

                with col_k:
                    st.markdown(f"**📋 {t('Kadro İstatistikleri', 'Squad Stats')}**")
                    goster = kadro[["Oyuncu","Mevki","Maç","İlk11","Gol","Gol/Maç","Dakika","Sarı","Kırmızı"]].copy()
                    goster = goster.sort_values("Gol", ascending=False).reset_index(drop=True)
                    if EN:
                        goster["Mevki"] = goster["Mevki"].map(mevki_goster)
                    goster.index += 1
                    df_tablo(goster, basliklar={"Oyuncu": t("Oyuncu","Player"), "Mevki": t("Mevki","Position"),
                                                "Maç": t("Maç","Matches"), "İlk11": t("İlk11","Started"),
                                                "Gol": t("Gol","Goals"), "Gol/Maç": t("Gol/Maç","G/Match"),
                                                "Dakika": t("Dakika","Minutes"), "Sarı": "🟨", "Kırmızı": "🟥"},
                             formatlar={"Gol/Maç": lambda v: f"{v:.2f}"})

                with col_g:
                    st.markdown(f"**📊 {t('Mevki Dağılımı', 'Position Distribution')}**")
                    mev_dag = kadro["Mevki"].value_counts().reset_index()
                    mev_dag.columns = ["Mevki","Sayı"]
                    renk_map = {"Kaleci":"#2979ff","Defans":"#1db954",
                                "Orta Saha":"#ffab00","Forvet":"#ff6b6b","Bilinmiyor":"#8899aa"}
                    fig_pie = go.Figure(go.Pie(
                        labels=[mevki_goster(m) for m in mev_dag["Mevki"]], values=mev_dag["Sayı"],
                        marker_colors=[mevki_renk(m) for m in mev_dag["Mevki"]],
                        hole=0.45, textinfo="label+value", textposition="outside",
                        automargin=True, insidetextorientation="horizontal",
                        textfont=dict(color="#e0e0e0", size=11),
                    ))
                    fig_pie.update_layout(
                        paper_bgcolor="#0f1117", font=dict(color="#e0e0e0", size=11),
                        margin=dict(l=30,r=30,t=24,b=24), height=240,
                        showlegend=False,
                    )
                    st.plotly_chart(fig_pie, width="stretch")

                    st.markdown(f"**🌍 {t('Uyruk Dağılımı', 'Nationality Distribution')}**")
                    uyr_dag = kadro["Uyruk"].value_counts().head(8).reset_index()
                    uyr_dag.columns = ["Uyruk","Sayı"]
                    fig_uyr = go.Figure(go.Bar(
                        x=uyr_dag["Sayı"], y=uyr_dag["Uyruk"], orientation="h",
                        marker=dict(color="#1db954"),
                        text=uyr_dag["Sayı"], textposition="outside",
                        textfont=dict(color="#e0e0e0", size=11),
                    ))
                    fig_uyr.update_layout(
                        paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                        xaxis=dict(showgrid=False,color="#505870"),
                        yaxis=dict(color="#e0e0e0"),
                        margin=dict(l=5,r=30,t=5,b=5), height=240,
                        font=dict(color="#e0e0e0"),
                    )
                    st.plotly_chart(fig_uyr, width="stretch")

                st.markdown("---")
                st.markdown(f"**📊 {t('Takım vs Lig Ortalaması', 'Team vs League Average')}**")
                lig_ort   = df_tam.groupby("Takım").agg({"Gol":"sum","Maç":"sum","Dakika":"sum"}).mean()
                takim_ort = kadro.agg({"Gol":"sum","Maç":"sum","Dakika":"sum"})
                c1,c2,c3 = st.columns(3)
                for kol, metrik, birim, birim_en in [
                    (c1,"Gol","gol","goals"), (c2,"Maç","maç","matches"), (c3,"Dakika","dakika","min")
                ]:
                    takim_val = float(takim_ort[metrik])
                    lig_val   = float(lig_ort[metrik])
                    delta     = takim_val - lig_val
                    kol.metric(
                        label=f"{t('Toplam','Total')} {metrik}",
                        value=f"{int(takim_val)} {t(birim,birim_en)}",
                        delta=f"{delta:+.0f} {t('lig ort. farkı','vs league avg')}",
                    )


# ══════════════════════════════════════════════════════════════════════════════
# SEKME — GENÇ YETENEKLER
# ══════════════════════════════════════════════════════════════════════════════
if tab_genç:
    st.markdown(f"##### 🌱 {t('Genç Yetenekler', 'Young Talents')}")
    st.caption(t("23 yaş altı · En az 8 maç · Erken Olgunluk Skoru'na göre sıralı",
                 "Under 23 · At least 8 matches · Sorted by Early Maturity Score"))

    # Veri hazırla
    @st.cache_data(ttl=3600)
    def genc_yetenekler_hesapla():
        rows = []
        for o in ham_liste:
            isim = o["oyuncu"]
            yas  = _MANUEL_YAS.get(isim)
            if not yas:
                try: yas = float(str(sd_profiller.get(isim,{}).get("Age","")).split()[0])
                except: yas = None
            if not yas or yas >= 23: continue

            mac = int(o.get("mac_sayisi", 0))
            if mac < 8: continue
            gol   = int(o.get("gol_sayisi", 0))
            dk    = int(o.get("toplam_dakika", 0))
            gpm   = round(gol / mac, 2) if mac else 0
            dk_mac = round(dk / mac, 0) if mac else 0

            pos = _MANUEL_MEVKI.get(isim) or sd_profiller.get(isim,{}).get("Position","")
            mevki = mevki_normalize(pos)

            nat = _MANUEL_UYRUK.get(isim) or sd_profiller.get(isim,{}).get("Nationality","")
            nat = _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nat).split()[0] if nat else "—"

            # Erken Olgunluk Skoru
            skor = round((mac/30*40) + (gpm*10*40) + (dk_mac/90*20), 1)

            rows.append({
                "Oyuncu": isim, "Takım": _takim_kisa(o["takim"]), "Yaş": yas,
                "Mevki": mevki, "Maç": mac, "Gol": gol,
                "G/Maç": gpm, "Dk/Maç": int(dk_mac),
                "Uyruk": nat, "Skor": skor,
            })
        return pd.DataFrame(rows).sort_values("Skor", ascending=False).reset_index(drop=True)

    genc_df = genc_yetenekler_hesapla()

    if genc_df.empty:
        st.warning(t("Veri bulunamadı.", "No data found."))
    else:
        # ── Filtreler ─────────────────────────────────────────────────
        gf1, gf2, gf3 = st.columns([2, 2, 2])
        with gf1:
            yas_ust = st.select_slider(t("Maksimum Yaş","Maximum Age"), options=[15, 16, 17, 18, 19, 20, 21, 22, 23], value=23)
        with gf2:
            mevki_filtre = st.multiselect(t("Mevki","Position"), ["Kaleci","Defans","Orta Saha","Forvet"],
                                           format_func=mevki_goster,
                                           placeholder=t("Tümü","All"), key="gf_mevki")
        with gf3:
            _gf_nat_opts = ["Tümü","Yerli","Yabancı"]
            _gf_nat_en   = {"Tümü":"All","Yerli":"Domestic","Yabancı":"Foreign"}
            tercih_filtre = st.selectbox(t("Uyruk Tercihi","Nationality Filter"), _gf_nat_opts,
                format_func=lambda x: _gf_nat_en[x] if EN else x, key="gf_tercih")

        filtered = genc_df[genc_df["Yaş"] < yas_ust + 1].copy()
        if mevki_filtre:
            filtered = filtered[filtered["Mevki"].isin(mevki_filtre)]
        if tercih_filtre == "Yerli":
            filtered = filtered[filtered["Uyruk"] == "Turkey"]
        elif tercih_filtre == "Yabancı":
            filtered = filtered[filtered["Uyruk"] != "Turkey"]

        st.markdown(
            f"<div style='color:#1db954;font-size:13px;font-weight:700;margin:8px 0 16px;'>"
            f"🎯 {len(filtered)} {t('genç oyuncu','young players')}</div>", unsafe_allow_html=True)

        # ── En İlginç 5 ───────────────────────────────────────────────
        if len(filtered) >= 3:
            st.markdown(f"**⭐ {t('Öne Çıkan İsimler', 'Featured Names')}**")
            top5 = filtered.head(5)
            cols = st.columns(min(5, len(top5)))
            for idx, (_, r) in enumerate(top5.iterrows()):
                with cols[idx]:
                    _mrk = mevki_renk(r['Mevki'])
                    st.markdown(
                        f"<div style='background:#1a1f36;border-radius:10px;padding:12px;"
                        f"text-align:center;border-top:3px solid {_mrk};'>"
                        f"<div style='font-size:11px;font-weight:700;color:#fff;"
                        f"margin-bottom:4px;'>{r['Oyuncu'].split()[0]}<br>"
                        f"<span style='font-size:10px;'>{r['Oyuncu'].split()[-1]}</span></div>"
                        f"<div style='font-size:20px;font-weight:800;color:#1db954;'>{r['Yaş']:.0f}</div>"
                        f"<div style='display:inline-block;font-size:9px;font-weight:700;"
                        f"color:{_mrk};background:{_mrk}22;border:1px solid {_mrk}55;"
                        f"border-radius:5px;padding:1px 7px;margin-top:2px;'>{mevki_goster(r['Mevki'])}</div>"
                        f"<div style='font-size:16px;font-weight:700;color:#fff;margin-top:6px;'>{r['Gol']}</div>"
                        f"<div style='font-size:9px;color:#8899aa;'>{t('gol','goals')} · {r['Maç']} {t('maç','matches')}</div>"
                        f"</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Scatter: Yaş vs Gol/Maç ───────────────────────────────────
        col_scatter, col_tablo = st.columns([3, 2], gap="large")

        with col_scatter:
            st.markdown(f"**📊 {t('Yaş — Gol/Maç Dağılımı', 'Age — Goals/Match Distribution')}**")
            fig_sc = go.Figure()
            for mev, grp in filtered.groupby("Mevki"):
                fig_sc.add_trace(go.Scatter(
                    x=grp["Yaş"], y=grp["G/Maç"],
                    mode="markers+text",
                    name=mevki_goster(mev),
                    marker=dict(size=grp["Maç"].clip(8,30)/1.5,
                                color=mevki_renk(mev),
                                opacity=0.85,
                                line=dict(color="#0f1117", width=1)),
                    text=grp["Oyuncu"].str.split().str[0],
                    textposition="top center",
                    textfont=dict(size=9, color="#c9d1d9"),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Yaş: %{x}<br>G/Maç: %{y}<br>"
                        "Maç: %{customdata[1]}<extra></extra>"
                    ),
                    customdata=grp[["Oyuncu","Maç"]].values,
                ))
            fig_sc.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title=t("Yaş","Age"), color="#8899aa", gridcolor="#1e2340",
                           range=[14.5, 23.5]),
                yaxis=dict(title=t("Gol/Maç","Goals/Match"), color="#8899aa", gridcolor="#1e2340"),
                legend=dict(bgcolor="#1a1f36", bordercolor="#30363d",
                            font=dict(color="#e0e0e0")),
                margin=dict(l=10, r=10, t=10, b=10),
                height=420, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_sc, width="stretch")
            st.caption(t("💡 Nokta büyüklüğü = oynanan maç sayısı", "💡 Dot size = number of matches played"))

        with col_tablo:
            st.markdown(f"**📋 {t('Tam Liste', 'Full List')}**")
            goster = filtered[["Oyuncu","Yaş","Mevki","Takım","Maç","Gol","G/Maç","Skor"]].copy()
            if EN:
                goster["Mevki"] = goster["Mevki"].map(mevki_goster)
            goster.index = range(1, len(goster)+1)
            df_tablo(
                goster,
                basliklar={"Oyuncu": t("Oyuncu","Player"), "Yaş": t("Yaş","Age"),
                           "Mevki": t("Mevki","Position"), "Takım": t("Takım","Team"),
                           "Maç": t("Maç","Matches"), "Gol": t("Gol","Goals"),
                           "G/Maç": t("G/Maç","G/Match"), "Skor": t("Skor","Score")},
                formatlar={"Yaş": lambda v: f"{v:.0f}", "G/Maç": lambda v: f"{v:.2f}",
                           "Skor": lambda v: f"{v:.0f}"})


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 9 — GELİŞMİŞ OYUNCU ARAMA
# ══════════════════════════════════════════════════════════════════════════════
if tab9:
    if not st.session_state.get("kulup_giris"):
        giris_gerekli_ekrani()
    elif not pro_kontrol():
        pro_paywall_goster(t("🔍 Gelişmiş Arama", "🔍 Advanced Search"))
    elif deneme_modunda():
        deneme_kilit(t("🔍 Gelişmiş Arama", "🔍 Advanced Search"), "tr")
    else:
        st.markdown(f"##### 🔍 {t('Gelişmiş Oyuncu Arama', 'Advanced Player Search')}")
        st.caption(t("Uyruk, mevki, yaş ve maç sayısına göre filtrele",
                     "Filter by nationality, position, age and number of matches"))

        if df_tam.empty:
            st.warning(t("Veri yok.", "No data."))
        else:
            fa1, fa2, fa3, fa4 = st.columns([2, 1, 1, 2])
            fb1, fb2, fb3, fb4 = st.columns([2, 2, 2, 2])

            all_nats = sorted(df_tam["Uyruk"].dropna().replace("", pd.NA).dropna().unique())

            _as_tumu = t("Tümü", "All")
            with fa1:
                sel_nats = st.multiselect(f"🌍 {t('Uyruk','Nationality')}", all_nats, placeholder=t("Tümü","All"), key="as_nat")
            with fa2:
                as_kategori = st.selectbox(f"📋 {t('Mevki','Position')}", [_as_tumu] + list(_MEVKI_DETAY.keys()),
                    format_func=mevki_goster, key="as_kat")
            with fa3:
                as_detay_secenekler = [_as_tumu] + (_MEVKI_DETAY.get(as_kategori, []) if as_kategori != _as_tumu else [])
                as_detay = st.selectbox(f"↳ {t('Detay','Detail')}", as_detay_secenekler,
                    format_func=mevki_goster, key="as_detay", disabled=(as_kategori==_as_tumu))
            with fa4:
                isim_q = st.text_input(f"👤 {t('İsim','Name')}", placeholder=t("Ara…","Search…"), key="as_isim")

            yas_vals = df_tam["Yaş"].dropna() if "Yaş" in df_tam.columns else pd.Series(dtype=float)
            yas_min = int(yas_vals.min()) if not yas_vals.empty else 15
            yas_max = int(yas_vals.max()) if not yas_vals.empty else 40
            mac_max = int(df_tam["Maç"].max()) if not df_tam.empty else 30

            _as_sort_opts = ["Maç ↓", "Gol ↓", "Dakika ↓", "Yaş ↑", "Oyuncu ↑"]
            _as_sort_en   = {"Maç ↓":"Matches ↓","Gol ↓":"Goals ↓","Dakika ↓":"Minutes ↓","Yaş ↑":"Age ↑","Oyuncu ↑":"Player ↑"}
            with fb1:
                yas_range = st.slider(f"🎂 {t('Yaş','Age')}", yas_min, yas_max, (yas_min, yas_max), key="as_yas")
            with fb2:
                min_mac = st.slider(f"📅 {t('Min. Maç','Min. Matches')}", 0, mac_max, 0, key="as_mac")
            with fb3:
                min_gol = st.slider(f"⚽ {t('Min. Gol','Min. Goals')}", 0, int(df_tam["Gol"].max()), 0, key="as_gol")
            with fb4:
                sort_by = st.selectbox(t("Sırala","Sort"), _as_sort_opts,
                    format_func=lambda x: _as_sort_en[x] if EN else x, key="as_sort")

            mask = pd.Series(True, index=df_tam.index)
            if sel_nats:
                mask &= df_tam["Uyruk"].isin(sel_nats)
            if as_kategori != _as_tumu:
                if as_detay != _as_tumu:
                    mask &= df_tam["Mevki"] == as_detay
                else:
                    mask &= df_tam["Mevki"].isin(_MEVKI_DETAY.get(as_kategori, []))
            if isim_q.strip():
                mask &= df_tam["Oyuncu"].str.contains(isim_q.strip(), case=False, na=False)
            mask &= df_tam["Maç"] >= min_mac
            mask &= df_tam["Gol"] >= min_gol
            if "Yaş" in df_tam.columns and not yas_vals.empty:
                yas_mask = df_tam["Yaş"].isna() | df_tam["Yaş"].between(yas_range[0], yas_range[1])
                mask &= yas_mask

            filtered = df_tam[mask].copy()
            sort_map = {"Maç ↓": ("Maç", False), "Gol ↓": ("Gol", False),
                        "Dakika ↓": ("Dakika", False), "Yaş ↑": ("Yaş", True), "Oyuncu ↑": ("Oyuncu", True)}  # internal keys stay TR
            sc, sa = sort_map[sort_by]
            filtered = filtered.sort_values(sc, ascending=sa).reset_index(drop=True)

            st.markdown(
                f"<div style='color:#1db954;font-size:13px;font-weight:700;margin:8px 0;'>"
                f"🎯 {len(filtered)} {t('oyuncu bulundu','players found')}</div>", unsafe_allow_html=True)

            if filtered.empty:
                st.info(t("Filtrelerle eşleşen oyuncu yok.", "No players match the filters."))
            else:
                show = ["Oyuncu", "Takım", "Mevki", "Uyruk", "Yaş", "Maç", "İlk11", "Gol", "Dakika", "Sarı"]
                show = [c for c in show if c in filtered.columns]
                _goster_df = filtered[show].copy()
                if EN and "Mevki" in _goster_df.columns:
                    _goster_df["Mevki"] = _goster_df["Mevki"].map(mevki_goster)
                df_tablo(_goster_df,
                    basliklar={"Oyuncu": t("Oyuncu","Player"), "Takım": t("Takım","Team"),
                               "Mevki": t("Mevki","Position"), "Uyruk": t("Uyruk","Nationality"),
                               "Yaş": t("Yaş","Age"), "Maç": t("Maç","Matches"),
                               "İlk11": t("İlk11","Started"), "Gol": t("Gol","Goals"),
                               "Dakika": t("Dakika","Minutes"), "Sarı": "🟨"},
                    formatlar={"Yaş": lambda v: f"{v:.0f}"})


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 10 — YAŞ ANALİZİ
# ══════════════════════════════════════════════════════════════════════════════
def _yas_df():
    """soccerdonna_profiller.json'dan yaş verisi üretir."""
    rows = []
    # Manuel override'ları ekle
    for isim, age_num in _MANUEL_YAS.items():
        rows.append({
            "isim": isim,
            "born_dt": pd.NaT,
            "yas": age_num,
            "dogum_yili": None,
        })
    already = {r["isim"] for r in rows}

    for isim, profil in sd_profiller.items():
        if isim in already:
            continue
        dob = profil.get("Date of birth", "")
        age_str = profil.get("Age", "")
        try:
            born_dt = pd.to_datetime(dob, dayfirst=True, errors="coerce")
            age_num = float(str(age_str).split()[0]) if age_str else None
        except Exception:
            born_dt, age_num = pd.NaT, None
        # Mantıksız yaş değerlerini filtrele (15-40 dışı)
        if age_num is not None and not (15 <= age_num <= 40):
            continue
        rows.append({
            "isim": isim,
            "born_dt": born_dt,
            "yas": age_num,
            "dogum_yili": born_dt.year if not pd.isna(born_dt) else None,
        })
    df = pd.DataFrame(rows).dropna(subset=["yas"])
    # oyuncular.json'daki takım bilgisini birleştir
    takim_map = dict(zip(df_tam["Oyuncu"], df_tam["Takım"])) if not df_tam.empty else {}
    df["takim"] = df["isim"].map(takim_map).fillna("Bilinmiyor")
    return df

if tab10:
    st.markdown(f"##### 🎂 {t('Yaş Analizi', 'Age Analysis')}")
    st.caption(t("SoccerDonna verisi", "SoccerDonna data"))

    yas_df = _yas_df()

    if yas_df.empty:
        st.warning(t("Yaş verisi bulunamadı.", "Age data not found."))
    else:
        avg_age = yas_df["yas"].mean()
        youngest = yas_df.loc[yas_df["yas"].idxmin()]
        oldest   = yas_df.loc[yas_df["yas"].idxmax()]
        u23      = int((yas_df["yas"] < 23).sum())

        k1, k2, k3, k4 = st.columns(4)
        for kol, sayi, etiket in [
            (k1, f"{avg_age:.1f}", t("Lig Ort. Yaşı","League Avg. Age")),
            (k2, f"{youngest['yas']:.0f} — {youngest['isim']}", t("En Genç","Youngest")),
            (k3, f"{oldest['yas']:.0f} — {oldest['isim']}", t("En Yaşlı","Oldest")),
            (k4, u23, t("U-23 Oyuncu","U-23 Players")),
        ]:
            kol.markdown(
                f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_hist, col_takim = st.columns([3, 2], gap="large")

        with col_hist:
            st.markdown(f"**📊 {t('Yaş Dağılımı', 'Age Distribution')}**")
            fig_hist = go.Figure(go.Histogram(
                x=yas_df["yas"], nbinsx=20,
                marker=dict(color="#00a86b", line=dict(color="#1db954", width=0.8)),
                opacity=0.85,
                hovertemplate=t("Yaş","Age")+": %{x:.0f}<br>"+t("Oyuncu","Player")+": %{y}<extra></extra>",
            ))
            fig_hist.add_vline(x=avg_age, line_dash="dash", line_color="#ffab00",
                annotation_text=f"Ort: {avg_age:.1f}",
                annotation_position="top right",
                annotation_font=dict(color="#ffab00", size=11))
            fig_hist.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title=t("Yaş","Age"), color="#8899aa", gridcolor="#1e2340"),
                yaxis=dict(title=t("Oyuncu Sayısı","Player Count"), color="#8899aa", gridcolor="#1e2340"),
                bargap=0.08, margin=dict(l=10,r=10,t=10,b=10),
                height=320, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_hist, width="stretch")

            st.markdown(f"**📅 {t('Doğum Yılı Dağılımı', 'Birth Year Distribution')}**")
            by_year = (yas_df.dropna(subset=["dogum_yili"])
                       .groupby("dogum_yili").size()
                       .reset_index(name="sayi").sort_values("dogum_yili"))
            fig_year = go.Figure(go.Bar(
                x=by_year["dogum_yili"], y=by_year["sayi"],
                marker=dict(color=by_year["sayi"],
                            colorscale=[[0,"#0d3b2e"],[1,"#1db954"]], showscale=False),
                hovertemplate="%{x}: %{y} oyuncu<extra></extra>",
            ))
            fig_year.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title=t("Doğum Yılı","Birth Year"), color="#8899aa", gridcolor="#1e2340", dtick=2),
                yaxis=dict(title="Oyuncu", color="#8899aa", gridcolor="#1e2340"),
                bargap=0.1, margin=dict(l=10,r=10,t=10,b=10),
                height=260, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_year, width="stretch")

        with col_takim:
            st.markdown(f"**🏟 {t('Takım Yaş Ortalamaları', 'Team Age Averages')}**")
            takim_yas = (yas_df[yas_df["takim"] != "Bilinmiyor"]
                         .groupby("takim")["yas"]
                         .agg(["mean","min","max","count"]).round(1)
                         .reset_index()
                         .rename(columns={"takim":"Takım","mean":"Ort","min":"Min","max":"Max","count":"Oyuncu"})
                         .sort_values("Ort"))
            df_tablo(takim_yas,
                basliklar={"Takım": t("Takım","Team"), "Ort": t("Ort","Avg"),
                           "Min": "Min", "Max": "Max", "Oyuncu": t("Oyuncu","Players")},
                formatlar={"Ort": lambda v: f"{v:.1f}", "Min": lambda v: f"{v:.0f}",
                           "Max": lambda v: f"{v:.0f}"})
            if not takim_yas.empty:
                g = takim_yas.iloc[0]; y = takim_yas.iloc[-1]
                st.markdown(
                    f"<div style='font-size:12px;color:#8899aa;margin-top:8px;'>"
                    f"🟢 {t('En genç','Youngest')}: <b style='color:#1db954'>{g['Takım']}</b> ({g['Ort']} {t('yaş','yrs')})<br>"
                    f"🔴 {t('En yaşlı','Oldest')}: <b style='color:#ff6b6b'>{y['Takım']}</b> ({y['Ort']} {t('yaş','yrs')})</div>",
                    unsafe_allow_html=True)

            st.markdown(f"<br>**⚽ {t('Mevkiye Göre Ortalama Yaş', 'Average Age by Position')}**")
            pos_yas_map = dict(zip(df_tam["Oyuncu"], df_tam["Mevki"])) if not df_tam.empty else {}
            yas_df["mevki"] = yas_df["isim"].map(pos_yas_map).fillna("Bilinmiyor")
            mevki_yas = (yas_df[yas_df["mevki"] != "Bilinmiyor"]
                         .groupby("mevki")["yas"].mean().round(1)
                         .reset_index().rename(columns={"mevki":"Mevki","yas":"Ort. Yaş"})
                         .sort_values("Ort. Yaş", ascending=False))
            fig_pos = go.Figure(go.Bar(
                x=mevki_yas["Ort. Yaş"], y=[mevki_goster(m) for m in mevki_yas["Mevki"]], orientation="h",
                marker=dict(color=[mevki_renk(m) for m in mevki_yas["Mevki"]]),
                text=mevki_yas["Ort. Yaş"], textposition="outside",
                textfont=dict(color="#e0e0e0", size=12),
                hovertemplate="%{y}: %{x:.1f} " + t("yaş","yrs") + "<extra></extra>",
            ))
            fig_pos.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(range=[0,35], color="#505870", showgrid=False),
                yaxis=dict(color="#e0e0e0"),
                margin=dict(l=10,r=50,t=5,b=5), height=180,
                font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_pos, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 11 — KALECİLER
# ══════════════════════════════════════════════════════════════════════════════
if tab11:
    st.markdown(f"##### 🧤 {t('Kaleci İstatistikleri', 'Goalkeeper Statistics')}")
    st.caption(t("Yenilen gol ve maç başına yenilen gol — en az 5 maç oynayanlar",
                 "Goals conceded and goals conceded per match — min. 5 matches played"))

    kal_df = kaleci_istatistikleri_hesapla()

    if kal_df.empty:
        st.warning(t("Kaleci verisi bulunamadı.", "Goalkeeper data not found."))
    else:
        aktif = kal_df[kal_df["Maç"] >= 5].copy()

        # Üst kartlar
        if not aktif.empty:
            en_iyi = aktif.loc[aktif["G/Maç"].idxmin()]
            en_kotu = aktif.loc[aktif["G/Maç"].idxmax()]
            k1, k2, k3, k4 = st.columns(4)
            _ei_ad = en_iyi['Kaleci'].split()[0].title()
            _ek_ad = en_kotu['Kaleci'].split()[0].title()
            for kol, sayi, etiket in [
                (k1, len(aktif), t("Aktif Kaleci","Active GKs")),
                (k2, int(kal_df["YenilenGol"].sum()), t("Toplam Gol","Total Goals")),
                (k3, en_iyi['G/Maç'], t("En Az Yiyen","Fewest Conceded") + " · " + _ei_ad),
                (k4, en_kotu['G/Maç'], t("En Çok Yiyen","Most Conceded") + " · " + _ek_ad),
            ]:
                kol.markdown(
                    f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                    f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_tablo, col_grafik = st.columns([2, 3], gap="large")

        with col_tablo:
            st.markdown(f"**📋 {t('Tüm Kaleciler', 'All Goalkeepers')}**")
            goster = kal_df[kal_df["Maç"] > 0].copy()
            goster.index = range(1, len(goster) + 1)
            df_tablo(
                goster,
                basliklar={"Kaleci": t("Kaleci","Goalkeeper"), "Takım": t("Takım","Team"),
                           "Maç": t("Maç","Matches"), "YenilenGol": t("Y.Gol","GA"),
                           "G/Maç": t("G/Maç","G/Match")},
                formatlar={"G/Maç": lambda v: f"{v:.2f}"})

        with col_grafik:
            st.markdown(f"**📊 {t('Maç Başına Yenilen Gol (≥5 maç)', 'Goals Conceded per Match (≥5 matches)')}**")
            plot_df = aktif.sort_values("G/Maç")
            renkler = ["#1db954" if g <= 1.0 else "#ffab00" if g <= 2.0 else "#ff6b6b"
                       for g in plot_df["G/Maç"]]
            fig = go.Figure(go.Bar(
                x=plot_df["G/Maç"],
                y=plot_df["Kaleci"],
                orientation="h",
                marker=dict(color=renkler),
                text=[f"{g:.2f}" for g in plot_df["G/Maç"]],
                textposition="outside",
                textfont=dict(color="#e0e0e0", size=11),
                hovertemplate="%{y}<br>%{x:.2f} "+t("G/Maç","G/Match")+"<extra></extra>",
            ))
            fig.add_vline(x=1.0, line_dash="dash", line_color="#1db954",
                          annotation_text="1.0", annotation_font=dict(color="#1db954", size=10))
            fig.add_vline(x=2.0, line_dash="dash", line_color="#ffab00",
                          annotation_text="2.0", annotation_font=dict(color="#ffab00", size=10))
            fig.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title=t("Maç Başına Yenilen Gol","Goals Conceded per Match"), color="#8899aa",
                           gridcolor="#1e2340", range=[0, max(plot_df["G/Maç"]) * 1.15]),
                yaxis=dict(color="#e0e0e0"),
                margin=dict(l=10, r=60, t=10, b=10),
                height=500, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig, width="stretch")

            # Renk açıklaması
            st.markdown(
                "<div style='font-size:11px;color:#8899aa;'>"
                "🟢 ≤1.0 &nbsp; 🟡 1.0–2.0 &nbsp; 🔴 >2.0 &nbsp; G/Maç</div>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 12 — TRANSFER ÖNER
# ══════════════════════════════════════════════════════════════════════════════

# Öneri veri tabanı: (mevki, bütçe, tercih) → [oyuncu adları]
_TRANSFER_DB = {
    ("Kaleci", "Yuksek", "Yerli"):      ["SELDA AKGÖZ", "GAMZE NUR YAMAN", "GÖKNUR GÜLERYÜZ"],
    ("Kaleci", "Yuksek", "Yabancı"):    ["NATALIA MUNTEANU", "MARIA ASUNCION QUINONES GOICOE", "ROBERTA APRILE"],
    ("Kaleci", "Yuksek", "Farketmez"):  ["NATALIA MUNTEANU", "SELDA AKGÖZ", "GAMZE NUR YAMAN"],
    ("Kaleci", "Orta",   "Yerli"):      ["EZGİ ÇAĞLAR", "FATMA ŞAHİN", "İREM DAMLA ŞAHİN"],
    ("Kaleci", "Orta",   "Yabancı"):    ["AYTAJ SHARIFOVA", "FLORENTİNA KOLGECİ", "BEATRIZ BUENO NICOLETI"],
    ("Kaleci", "Orta",   "Farketmez"):  ["AYTAJ SHARIFOVA", "FLORENTİNA KOLGECİ", "EZGİ ÇAĞLAR"],
    ("Kaleci", "Dusuk",  "Yerli"):      ["DUYGU YILMAZ", "HİLAL SUBAY", "SUDE TOPÇU"],
    ("Kaleci", "Dusuk",  "Yabancı"):    ["NARGIZ ALIYEVA", "ROSE TEYE BAAH", "MEHRİBAN SHAHMAMMADOVA"],
    ("Kaleci", "Dusuk",  "Farketmez"):  ["DUYGU YILMAZ", "NARGIZ ALIYEVA", "HİLAL SUBAY"],

    # ── Sağ Bek - Sağ Kanat Bek ──────────────────────────────────────────
    ("Sağ Bek - Sağ Kanat Bek", "Yuksek", "Yerli"):      ["ELİF KESKİN", "ÜMRAN ÖZEV", "ECE TEKMEN"],
    ("Sağ Bek - Sağ Kanat Bek", "Yuksek", "Yabancı"):    ["MARIA APARECIDA SOUZA ALVES", "RAFAELA SUDRE DOS SANTOS", "TEODORA NICOARA"],
    ("Sağ Bek - Sağ Kanat Bek", "Yuksek", "Farketmez"):  ["MARIA APARECIDA SOUZA ALVES", "RAFAELA SUDRE DOS SANTOS", "ELİF KESKİN"],
    ("Sağ Bek - Sağ Kanat Bek", "Orta",   "Yerli"):      ["ECEM CUMERT", "RABİYA İSGİ", "MEDİNE ERKAN"],
    ("Sağ Bek - Sağ Kanat Bek", "Orta",   "Yabancı"):    ["JUSTİCE TWENEBOAA", "UGOCHI CYNTHIA EMENAYO", "JALE AĞAYAR QIZIZHALA MAHSIMOVA"],
    ("Sağ Bek - Sağ Kanat Bek", "Orta",   "Farketmez"):  ["ECEM CUMERT", "RABİYA İSGİ", "MEDİNE ERKAN"],
    ("Sağ Bek - Sağ Kanat Bek", "Dusuk",  "Yerli"):      ["NAZLI ÖRNEK", "HÜMEYRA ŞANVER", "MELİSA NİLGÜN KESER"],
    ("Sağ Bek - Sağ Kanat Bek", "Dusuk",  "Yabancı"):    ["RREZONA RAMADANI", "ELLEN COLEMAN", "DORİS AKAHEEH"],
    ("Sağ Bek - Sağ Kanat Bek", "Dusuk",  "Farketmez"):  ["NAZLI ÖRNEK", "RREZONA RAMADANI", "ELLEN COLEMAN"],

    # ── Sağ Stoper - Merkez Stoper ───────────────────────────────────────
    ("Sağ Stoper", "Yuksek", "Yerli"):      ["EDA KARATAŞ", "GÜLBİN HIZ", "KEZBAN TAĞ"],
    ("Sağ Stoper", "Yuksek", "Yabancı"):    ["KONYA TAJAE PLUMMER", "HEİDİ LYNNE RUTH", "BLERTA SMAILI"],
    ("Sağ Stoper", "Yuksek", "Farketmez"):  ["KONYA TAJAE PLUMMER", "HEİDİ LYNNE RUTH", "EDA KARATAŞ"],
    ("Sağ Stoper", "Orta",   "Yerli"):      ["MERYEM KÜÇÜKBİRİNCİ", "FATMA SARE ÖZTÜRK", "NARİN YAKUT"],
    ("Sağ Stoper", "Orta",   "Yabancı"):    ["MADİNATOU ROUAMBA", "MARİAM DİAKİTE", "ARMERA TUKAJ"],
    ("Sağ Stoper", "Orta",   "Farketmez"):  ["MADİNATOU ROUAMBA", "MERYEM KÜÇÜKBİRİNCİ", "FATMA SARE ÖZTÜRK"],
    ("Sağ Stoper", "Dusuk",  "Yerli"):      ["DAMLA BOZYEL", "SEVGİ SEVİN ERGEN", "SELİN SİVRİKAYA"],
    ("Sağ Stoper", "Dusuk",  "Yabancı"):    ["KARLA DANİELA ZEMPOALTECA HERNANDEZ", "AGNESA GASHI", "AYSHAN AHMADOVA"],
    ("Sağ Stoper", "Dusuk",  "Farketmez"):  ["DAMLA BOZYEL", "SEVGİ SEVİN ERGEN", "KARLA DANİELA ZEMPOALTECA HERNANDEZ"],

    # ── Sol Stoper ────────────────────────────────────────────────────────
    ("Sol Stoper", "Yuksek", "Yerli"):      ["İPEK KAYA", "YAŞAM GÖKSU"],
    ("Sol Stoper", "Yuksek", "Yabancı"):    ["LIUBOV SHMATKO", "BLERTA SMAILI", "OLUWATOSIN BLESSING DEMEHIN"],
    ("Sol Stoper", "Yuksek", "Farketmez"):  ["LIUBOV SHMATKO", "İPEK KAYA", "YAŞAM GÖKSU"],
    ("Sol Stoper", "Orta",   "Yerli"):      ["MERVE ODABAŞOĞLU", "NEHİR ZEYTÜNLÜ", "SÜHEYLA ÇALÇINAR"],
    ("Sol Stoper", "Orta",   "Yabancı"):    ["ELİZABETH OPPONG", "ZOTE NINA KPAHO", "MARIE LAURE KONG"],
    ("Sol Stoper", "Orta",   "Farketmez"):  ["MERVE ODABAŞOĞLU", "ELİZABETH OPPONG", "NEHİR ZEYTÜNLÜ"],
    ("Sol Stoper", "Dusuk",  "Yerli"):      ["SEVİLAY DUMAN", "ÖZGE ŞENGEL", "ESİN NİSA SİVASLI"],
    ("Sol Stoper", "Dusuk",  "Yabancı"):    ["VUSALA HACIYEVA", "SHKURTE MALIQI", "LUSHOMO MWEEMBA"],
    ("Sol Stoper", "Dusuk",  "Farketmez"):  ["SEVİLAY DUMAN", "VUSALA HACIYEVA", "SHKURTE MALIQI"],

    # ── Sol Bek - Sol Kanat Bek ───────────────────────────────────────────
    ("Sol Bek - Sol Kanat Bek", "Yuksek", "Yerli"):      ["İLAYDA CİVELEK", "RABİA NUR KÜÇÜK", "YELİZ AÇAR"],
    ("Sol Bek - Sol Kanat Bek", "Yuksek", "Yabancı"):    ["YANA DERKACH", "ZOE VAN EYNDE", "MERTHA TEMBO"],
    ("Sol Bek - Sol Kanat Bek", "Yuksek", "Farketmez"):  ["İLAYDA CİVELEK", "YANA DERKACH", "RABİA NUR KÜÇÜK"],
    ("Sol Bek - Sol Kanat Bek", "Orta",   "Yerli"):      ["BENAN ALTINTAŞ", "ÖZNUR TAŞ", "MESUDE ALAYONT"],
    ("Sol Bek - Sol Kanat Bek", "Orta",   "Yabancı"):    ["NİKOLİNA MİLOVİC", "MARY ATİNUKE SAİKİ"],
    ("Sol Bek - Sol Kanat Bek", "Orta",   "Farketmez"):  ["BENAN ALTINTAŞ", "ÖZNUR TAŞ", "NİKOLİNA MİLOVİC"],
    ("Sol Bek - Sol Kanat Bek", "Dusuk",  "Yerli"):      ["BEYZA KOCATÜRK", "ELİF KESGİN", "SILA BESRA TETİK"],
    ("Sol Bek - Sol Kanat Bek", "Dusuk",  "Yabancı"):    ["OUAFAA HAMRİ", "PRECİOUS ADJWOA HAİZEL"],
    ("Sol Bek - Sol Kanat Bek", "Dusuk",  "Farketmez"):  ["BEYZA KOCATÜRK", "ELİF KESGİN", "SILA BESRA TETİK"],

    # ── Hücumcu Orta Saha ─────────────────────────────────────────────────
    ("Hücumcu Orta Saha", "Yuksek", "Yerli"):      ["EBRU TOPÇU", "DİLAN BORA"],
    ("Hücumcu Orta Saha", "Yuksek", "Yabancı"):    ["MARTA ALEXANDRA COX VILLARREAL", "DONJETA HALILAJ", "MILICA MIJATOVIC"],
    ("Hücumcu Orta Saha", "Yuksek", "Farketmez"):  ["MARTA ALEXANDRA COX VILLARREAL", "DONJETA HALILAJ", "EBRU TOPÇU"],
    ("Hücumcu Orta Saha", "Orta",   "Yerli"):      ["MELİKE DİNÇEL"],
    ("Hücumcu Orta Saha", "Orta",   "Yabancı"):    ["SULIAT OLAJUMOKE ABIDEEN", "RASMATA SAWADOGO", "VANESA LEVENAJ"],
    ("Hücumcu Orta Saha", "Orta",   "Farketmez"):  ["SULIAT OLAJUMOKE ABIDEEN", "RASMATA SAWADOGO"],
    ("Hücumcu Orta Saha", "Dusuk",  "Yerli"):      ["AÇELYA NOMAK", "ALEYNA MERAL", "OLIVIA MATILDE JOHANSSON ALCAIDE"],
    ("Hücumcu Orta Saha", "Dusuk",  "Farketmez"):  ["AÇELYA NOMAK", "ALEYNA MERAL", "OLIVIA MATILDE JOHANSSON ALCAIDE"],

    # ── Savunmacı Orta Saha ───────────────────────────────────────────────────
    ("Savunmacı Orta Saha", "Yuksek", "Yerli"):     ["BAŞAK İÇİNÖZBEBEK", "MERYEM CENNET ÇAL", "FATMA KARA"],
    ("Savunmacı Orta Saha", "Yuksek", "Yabancı"):   ["REGINA IBIANG OTU", "LINA YANG", "DANA MARGARETHA WILHELMINA FOEDERER"],
    ("Savunmacı Orta Saha", "Yuksek", "Farketmez"): ["REGINA IBIANG OTU", "LINA YANG", "BAŞAK İÇİNÖZBEBEK"],
    ("Savunmacı Orta Saha", "Orta",   "Yerli"):     ["CANSU NUR KAYA", "KEVSER KARTAL", "NEVCAN KELEŞ"],
    ("Savunmacı Orta Saha", "Orta",   "Yabancı"):   ["PAULA RUESS", "CHIOMA OLISE", "AMIRA OULD BRAHAM"],
    ("Savunmacı Orta Saha", "Orta",   "Farketmez"): ["PAULA RUESS", "CHIOMA OLISE", "CANSU NUR KAYA"],
    ("Savunmacı Orta Saha", "Dusuk",  "Yerli"):     ["ZEYNEP ÜLKÜ KAHYA", "AYŞE DEMİRCİ", "İSMİGÜL YALÇINER"],
    ("Savunmacı Orta Saha", "Dusuk",  "Yabancı"):   ["EZMİRALDA FRANJA", "JALE AĞAYAR QIZIZHALA MAHSIMOVA", "KAFAYAT FOLAKEMI SHITTU"],
    ("Savunmacı Orta Saha", "Dusuk",  "Farketmez"): ["EZMİRALDA FRANJA", "JALE AĞAYAR QIZIZHALA MAHSIMOVA", "ZEYNEP ÜLKÜ KAHYA"],

    # ── Merkez Orta Saha ─────────────────────────────────────────────────────
    ("Merkez Orta Saha", "Yuksek", "Yerli"):     ["ECE TÜRKOĞLU", "PERİTAN BOZDAĞ", "EMİNE ECEM ESEN"],
    ("Merkez Orta Saha", "Yuksek", "Yabancı"):   ["SLAĐANA BULATOVIĆ", "CHANG JANG", "LYDIA NAYELI RANGEL HERNANDEZ"],
    ("Merkez Orta Saha", "Yuksek", "Farketmez"): ["SLAĐANA BULATOVIĆ", "CHANG JANG", "ECE TÜRKOĞLU"],
    ("Merkez Orta Saha", "Orta",   "Yerli"):     ["DERYA ARHAN", "SEDA NUR İNCİK", "NİHAL SARAÇ"],
    ("Merkez Orta Saha", "Orta",   "Yabancı"):   ["FADIMATOU ARETOUYAP KOME", "MARIJA ALEKSIC", "DIANA LUCAS MSEWA"],
    ("Merkez Orta Saha", "Orta",   "Farketmez"): ["FADIMATOU ARETOUYAP KOME", "MARIJA ALEKSIC", "DERYA ARHAN"],
    ("Merkez Orta Saha", "Dusuk",  "Yerli"):     ["MERYEM SEVENT", "MERVE NUR TAŞUCU", "BEYZA EMİNE SARUHAN"],
    ("Merkez Orta Saha", "Dusuk",  "Yabancı"):   ["ILARJA ZARKA", "JOY EBINEMIERE BOKIRI"],
    ("Merkez Orta Saha", "Dusuk",  "Farketmez"): ["MERYEM SEVENT", "ILARJA ZARKA", "MERVE NUR TAŞUCU"],

    # ── Sol Kanat ─────────────────────────────────────────────────────────
    ("Sol Kanat", "Yuksek", "Yerli"):      ["ARZU KARABULUT", "BİRGÜL SADIKOĞLU"],
    ("Sol Kanat", "Yuksek", "Yabancı"):    ["FLOURISH CHIOMA SABASTINE", "OLHA OVDIYCHUK", "MARTA NAIZIA DA SILVA CINTRA"],
    ("Sol Kanat", "Yuksek", "Farketmez"):  ["FLOURISH CHIOMA SABASTINE", "OLHA OVDIYCHUK", "MARTA NAIZIA DA SILVA CINTRA"],
    ("Sol Kanat", "Orta",   "Yerli"):      ["İNAYET FUNDA ALTINKAYA", "ŞEHRİBAN DÜLEK"],
    ("Sol Kanat", "Orta",   "Yabancı"):    ["SULIAT OLAJUMOKE ABIDEEN", "OLGA MASSOMBO", "KALTRINA BIQKAJ"],
    ("Sol Kanat", "Orta",   "Farketmez"):  ["SULIAT OLAJUMOKE ABIDEEN", "OLGA MASSOMBO", "İNAYET FUNDA ALTINKAYA"],
    ("Sol Kanat", "Dusuk",  "Yerli"):      ["CANSU İRİŞ", "AZRA TIRAŞ"],
    ("Sol Kanat", "Dusuk",  "Yabancı"):    ["LARA ANTUNES PINTASSILGO", "JELENA KARLİCİC", "MELISSA SANDRINE BEHINAN"],
    ("Sol Kanat", "Dusuk",  "Farketmez"):  ["LARA ANTUNES PINTASSILGO", "JELENA KARLİCİC", "İNAYET FUNDA ALTINKAYA"],

    # ── Sağ Kanat ─────────────────────────────────────────────────────────
    ("Sağ Kanat", "Yuksek", "Yerli"):      ["BUSEM ŞEKER", "MELİKE PEKEL"],
    ("Sağ Kanat", "Yuksek", "Yabancı"):    ["MARIA APARECIDA SOUZA ALVES", "NATALIA OLESZKIEWICZ", "ANA INES COSTA MENDES DIAS"],
    ("Sağ Kanat", "Yuksek", "Farketmez"):  ["MARIA APARECIDA SOUZA ALVES", "NATALIA OLESZKIEWICZ", "BUSEM ŞEKER"],
    ("Sağ Kanat", "Orta",   "Yerli"):      ["ZEYNEP KERİMOĞLU", "SEVGİ ÇINAR KARAOĞLU"],
    ("Sağ Kanat", "Orta",   "Yabancı"):    ["JULIA HICKELSBERGEN FULLER", "ELENA GRACINDA SANTOS", "KARYNA ALKHOVIK"],
    ("Sağ Kanat", "Orta",   "Farketmez"):  ["JULIA HICKELSBERGEN FULLER", "ELENA GRACINDA SANTOS", "ZEYNEP KERİMOĞLU"],
    ("Sağ Kanat", "Dusuk",  "Yerli"):      ["ECEMNUR ÖZTÜRK", "MELİKE DİNÇEL", "FATMA ATAŞ"],
    ("Sağ Kanat", "Dusuk",  "Yabancı"):    ["JULIETTE NANA", "SAMARIA SARAI GOMEZ MEJIA", "PRİNCELLA ADUBEA"],
    ("Sağ Kanat", "Dusuk",  "Farketmez"):  ["JULIETTE NANA", "SAMARIA SARAI GOMEZ MEJIA", "ECEMNUR ÖZTÜRK"],

    # ── Santrafor ─────────────────────────────────────────────────────────
    ("Santrafor", "Yuksek", "Yerli"):      ["YAĞMUR URAZ"],
    ("Santrafor", "Yuksek", "Yabancı"):    ["VALENTINA GIACINTI", "ANDREA STASKOVA", "ARMISA KUÇ"],
    ("Santrafor", "Yuksek", "Farketmez"):  ["VALENTINA GIACINTI", "ANDREA STASKOVA", "ARMISA KUÇ"],
    ("Santrafor", "Orta",   "Yerli"):      ["MELİKE ÖZTÜRK", "NESLİHAN DEMİRDÖĞEN", "ESRA MANYA"],
    ("Santrafor", "Orta",   "Yabancı"):    ["MARIE GISELE DIVINE NGAH MANGA", "MARIEM HOUIJ", "VALENTINA TROKA"],
    ("Santrafor", "Orta",   "Farketmez"):  ["MARIE GISELE DIVINE NGAH MANGA", "MARIEM HOUIJ", "MELİKE ÖZTÜRK"],
    ("Santrafor", "Dusuk",  "Yerli"):      ["ZEYNEP GAMZE KOÇER", "BUKET KARADAĞ", "ELİF CEREN MUTLU"],
    ("Santrafor", "Dusuk",  "Yabancı"):    ["ELIZABETH OWUSUAA", "NGO MBELECK GENEVIEVE EDITH", "KENNYA KINDA ESTHER CORDNER"],
    ("Santrafor", "Dusuk",  "Farketmez"):  ["ELIZABETH OWUSUAA", "NGO MBELECK GENEVIEVE EDITH", "ZEYNEP GAMZE KOÇER"],
}

if tab_transfer:
    if not st.session_state.get("kulup_giris"):
        giris_gerekli_ekrani()
    elif not pro_kontrol():
        pro_paywall_goster(t("Transfer Öner", "Transfer Suggest"))
    elif deneme_modunda():
        deneme_kilit(t("🔄 Transfer Öner", "🔄 Transfer Suggest"), "tr")
    else:
        st.markdown(f"##### 🔄 {t('Transfer Öner', 'Transfer Suggest')}")
        st.caption(t("Adım adım bütçe ve kriterlere göre lig içi transfer önerisi",
                     "Step-by-step in-league transfer suggestion based on budget and criteria"))

        if "tr_adim" not in st.session_state:
            st.session_state["tr_adim"] = 0

        adim = st.session_state["tr_adim"]

        # ── ADIM 0: Başlangıç ───────────────────────────────────────────
        if adim == 0:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "<div style='text-align:center;padding:40px 0 20px;'>"
                "<div style='font-size:40px;'>🔄</div>"
                f"<div style='font-size:20px;font-weight:700;color:#fff;margin-top:12px;'>{t('Transfer Asistanı','Transfer Assistant')}</div>"
                f"<div style='font-size:13px;color:#8899aa;margin-top:8px;'>"
                f"{t('Takımınızın ihtiyacına göre lig içi transfer önerisi alın.','Get in-league transfer suggestions tailored to your team needs.')}</div>"
                "</div>",
                unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            col_b = st.columns([1, 2, 1])[1]
            with col_b:
                if st.button(t("🚀 Başla","🚀 Start"), width="stretch", type="primary"):
                    st.session_state["tr_adim"] = 1
                    st.rerun()

        # ── ADIM 1: Bütçe seç ───────────────────────────────────────────
        elif adim == 1:
            st.markdown(f"### {t('Adım 1 / 3','Step 1 / 3')} &nbsp; 💰 {t('Bütçenizi seçin','Select your budget')}")
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(t("💎 Yüksek\n\nBüyük kulüp transferi","💎 High\n\nBig club transfer"), width="stretch"):
                    st.session_state["tr_butce"]      = "Yuksek"
                    st.session_state["tr_butce_label"] = t("Yüksek 💎","High 💎")
                    st.session_state["tr_adim"]        = 2
                    st.rerun()
            with c2:
                if st.button(t("🔵 Orta\n\nOrta ölçekli transfer","🔵 Medium\n\nMid-range transfer"), width="stretch"):
                    st.session_state["tr_butce"]      = "Orta"
                    st.session_state["tr_butce_label"] = t("Orta 🔵","Medium 🔵")
                    st.session_state["tr_adim"]        = 2
                    st.rerun()
            with c3:
                if st.button(t("🟡 Düşük\n\nBütçe dostu transfer","🟡 Low\n\nBudget-friendly transfer"), width="stretch"):
                    st.session_state["tr_butce"]      = "Dusuk"
                    st.session_state["tr_butce_label"] = t("Düşük 🟡","Low 🟡")
                    st.session_state["tr_adim"]        = 2
                    st.rerun()

        # ── ADIM 2: Mevki + tercih ──────────────────────────────────────
        elif adim == 2:
            butce       = st.session_state.get("tr_butce", "")
            butce_label = st.session_state.get("tr_butce_label", butce)
            st.markdown(f"### {t('Adım 2 / 3','Step 2 / 3')} &nbsp; 📋 {t('Mevki ve tercih','Position and preference')}")
            st.markdown(f"<div style='color:#8899aa;font-size:13px;'>{t('Bütçe','Budget')}: <b style='color:#1db954'>{butce_label}</b></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            col_m, col_t = st.columns(2)
            with col_m:
                st.markdown(f"**{t('Hangi mevkiye oyuncu arıyorsunuz?','Which position are you looking for?')}**")
                mevki_secenekler = [
                                    "Kaleci",
                                    "Sağ Bek - Sağ Kanat Bek", "Sağ Stoper", "Sol Stoper", "Sol Bek - Sol Kanat Bek",
                                    "Savunmacı Orta Saha", "Merkez Orta Saha", "Hücumcu Orta Saha",
                                    "Sol Kanat", "Sağ Kanat", "Santrafor",
                                ]
                mevki_sec = st.radio(t("Mevki", "Position"), mevki_secenekler, key="tr_mevki_radio",
                                     format_func=lambda x: _TR_MEVKI_EN.get(x, x) if EN else x,
                                     label_visibility="collapsed")

            with col_t:
                st.markdown(f"**{t('Oyuncu tercihiniz?','Player preference?')}**")
                _tr_tercih_opts = ["Farketmez", "Yerli", "Yabancı"]
                tercih = st.radio(t("Tercih", "Preference"), _tr_tercih_opts, key="tr_tercih_radio",
                    format_func=lambda x: _TR_TERCIH_EN[x] if EN else x,
                    label_visibility="collapsed")

            st.markdown("<br>", unsafe_allow_html=True)
            col_geri, col_ileri = st.columns([1, 3])
            with col_geri:
                if st.button(t("← Geri","← Back"), width="stretch"):
                    st.session_state["tr_adim"] = 1
                    st.rerun()
            with col_ileri:
                if st.button(t("Önerileri Gör →","See Suggestions →"), width="stretch", type="primary"):
                    st.session_state["tr_mevki"]  = mevki_sec
                    st.session_state["tr_tercih"] = tercih
                    st.session_state["tr_adim"]   = 3
                    st.rerun()

        # ── ADIM 3: Sonuçlar ────────────────────────────────────────────
        elif adim == 3:
            butce       = st.session_state.get("tr_butce", "")
            butce_label = st.session_state.get("tr_butce_label", butce)
            mevki_sec   = st.session_state.get("tr_mevki", "")
            tercih      = st.session_state.get("tr_tercih", "")

            _mevki_disp  = _TR_MEVKI_EN.get(mevki_sec, mevki_sec) if EN else mevki_sec
            _tercih_disp = _TR_TERCIH_EN.get(tercih, tercih) if EN else tercih
            st.markdown(
                f"<div style='color:#8899aa;font-size:13px;margin-bottom:16px;'>"
                f"💰 {butce_label} &nbsp;·&nbsp; 📋 {_mevki_disp} &nbsp;·&nbsp; 🌍 {_tercih_disp}</div>",
                unsafe_allow_html=True)

            anahtar  = (mevki_sec, butce, tercih)
            oneriler = _TRANSFER_DB.get(anahtar, [])

            if not oneriler:
                st.info(t("Bu kombinasyon için henüz öneri tanımlanmadı.", "No suggestions defined for this combination yet."))
            else:
                # Kaleci için özel istatistikler, diğer mevkiler için genel oyuncu verisi
                _kaleci_mevki = mevki_sec == "Kaleci"
                if _kaleci_mevki:
                    kal_df   = kaleci_istatistikleri_hesapla()
                    kal_dict = {r["Kaleci"]: r for _, r in kal_df.iterrows()}

                st.markdown(
                    f"<div style='color:#1db954;font-weight:700;font-size:16px;margin-bottom:20px;'>"
                    f"🏆 {t('Önerilen 3 Oyuncu','3 Recommended Players')}</div>",
                    unsafe_allow_html=True)

                for i, isim in enumerate(oneriler, 1):
                    profil = sd_profiller.get(isim, {})
                    yas_v  = profil.get("Age", "—")
                    boy_v  = profil.get("Height", "—")
                    nat_v  = profil.get("Nationality", "—")
                    if nat_v:
                        nat_v = _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nat_v).split()[0]

                    if _kaleci_mevki:
                        r     = kal_dict.get(isim, {})
                        mac   = r.get("Maç", "—")
                        gol   = r.get("YenilenGol", "—")
                        takim = r.get("Takım", "—")
                        s2    = "Y.Gol"
                        renk  = "#1db954" if isinstance(gol, (int,float)) and gol <= 1.0 else \
                                "#ffab00" if isinstance(gol, (int,float)) and gol <= 2.0 else "#ff6b6b"
                    else:
                        o     = oyuncu_detay.get(isim, {})
                        mac   = o.get("mac_sayisi", "—")
                        gol   = o.get("gol_sayisi", "—")
                        takim = o.get("takim", "—")
                        s2    = "Gol"
                        renk  = "#1db954"

                    istatlar = [(mac, t("Maç","Matches")), (gol, s2), (yas_v, t("Yaş","Age")), (boy_v, t("Boy","Height")), (nat_v, t("Uyruk","Nation"))]
                    stat_html = "".join(
                        f"<div style='background:#0f1117;border-radius:8px;padding:8px 14px;"
                        f"text-align:center;'>"
                        f"<div style='font-size:18px;font-weight:700;color:#e0e0e0;'>{val}</div>"
                        f"<div style='font-size:10px;color:#8899aa;'>{lbl}</div></div>"
                        for val, lbl in istatlar
                    )
                    st.markdown(
                        f"<div style='background:#1a1f36;border-radius:12px;padding:18px 22px;"
                        f"margin-bottom:14px;border-left:4px solid {renk};'>"
                        f"<div style='font-size:17px;font-weight:800;color:#fff;margin-bottom:4px;'>"
                        f"{i}. {isim}</div>"
                        f"<div style='font-size:12px;color:#8899aa;margin-bottom:12px;'>🏟 {takim}</div>"
                        f"<div style='display:flex;gap:12px;flex-wrap:wrap;'>{stat_html}</div>"
                        f"</div>",
                        unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(t("🔄 Yeniden Başla","🔄 Start Over"), width="content"):
                for k in ["tr_adim","tr_butce","tr_butce_label","tr_mevki","tr_tercih"]:
                    st.session_state.pop(k, None)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCOUTING SAYFASI (sadece admin — tam sayfa)
# ══════════════════════════════════════════════════════════════════════════════

# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="altbilgi">'
    f'<span style="background:linear-gradient(90deg,#a855f7,#ec4899);'
    f'-webkit-background-clip:text;background-clip:text;color:transparent;'
    f'font-weight:800;letter-spacing:0.12em;">'
    f'{t("KADIN FUTBOLU PLATFORMU","WOMEN\'S FOOTBALL PLATFORM")}</span><br>'
    f'{t("Veri kaynağı: TFF — tff.org &amp; SoccerDonna | 2025-2026 Kadınlar Süper Ligi",
         "Data sources: TFF — tff.org &amp; SoccerDonna | 2025-2026 Women\'s Super League")}'
    f'</div>',
    unsafe_allow_html=True)
