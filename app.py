"""
Türkiye Kadınlar Süper Ligi 2025-2026 — Streamlit Web Arayüzü
"""
import json, os, pathlib, requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
try:
    import bcrypt as _bcrypt
    _BCRYPT_OK = True
except ImportError:
    _BCRYPT_OK = False
try:
    from groq import Groq as _Groq
    _GROQ_OK = True
except ImportError:
    _GROQ_OK = False
from bs4 import BeautifulSoup

_page_title = ("Turkish Women's Super League 2025-2026"
               if st.session_state.get("dil") == "EN"
               else "Türkiye Kadınlar Süper Ligi 2025-2026")
st.set_page_config(
    page_title=_page_title,
    page_icon="⚽", layout="wide",
)

# ─── Dil (TR varsayılan / EN hedefli sayfalar) ───
if "dil" not in st.session_state:
    st.session_state["dil"] = "TR"

def t(tr, en):
    """Dile göre metin döndürür (EN seçiliyse İngilizce, değilse Türkçe)."""
    return en if st.session_state.get("dil") == "EN" else tr

EN = st.session_state.get("dil") == "EN"

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""<style>

/* ── Genel ── */
.stApp { background-color:#0f1117; color:#e0e0e0; }

/* ── Başlık ── */
.baslik-kutu {
    background:linear-gradient(135deg,#1a1f36 0%,#0d3b2e 100%);
    border-left:5px solid #00c853; border-radius:12px;
    padding:22px 30px; margin-bottom:22px;
}
.baslik-kutu h1 { color:#fff; font-size:1.8rem; margin:0 0 5px 0; }
.baslik-kutu p  { color:#a0aab4; margin:0; font-size:0.9rem; }

/* ── Özet kartlar ── */
.stat-kart { background:#1a1f36; border-radius:10px; padding:14px 18px;
    text-align:center; border-top:3px solid #00c853; margin-bottom:6px; }
.stat-kart .sayi   { font-size:1.9rem; font-weight:700; color:#00c853; }
.stat-kart .etiket { font-size:0.75rem; color:#8899aa; margin-top:3px; }

/* ── Profil kartı ── */
.profil-kart { background:#1a1f36; border-radius:14px; padding:22px 26px;
    border-left:4px solid #00c853; }
.profil-kart h2 { color:#fff; margin:0 0 4px 0; font-size:1.35rem; }
.profil-stat { display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
.profil-stat-item { background:#0f1117; border-radius:8px; padding:10px 14px;
    text-align:center; min-width:70px; flex:1 1 70px; }
.profil-stat-item .deger { font-size:1.4rem; font-weight:700; color:#00c853; }
.profil-stat-item .ad    { font-size:0.68rem; color:#8899aa; margin-top:2px; }

/* ── Diğer bileşenler ── */
.transfer-badge { display:inline-block; background:#1a3a2a; color:#00c853;
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

    /* Başlık küçült */
    .baslik-kutu { padding:14px 16px; margin-bottom:14px; }
    .baslik-kutu h1 { font-size:1.2rem; }
    .baslik-kutu p  { font-size:0.8rem; }

    /* Özet kartlar 2'li grid */
    .stat-kart { padding:10px 12px; margin-bottom:4px; }
    .stat-kart .sayi   { font-size:1.5rem; }
    .stat-kart .etiket { font-size:0.68rem; }

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

    /* Nav / aksiyon butonları mobilde kompakt */
    [data-testid="stButton"] button {
        font-size:0.8rem !important; padding:6px 8px !important; min-height:0 !important;
    }
    /* Banner + buton dikey yığılınca aralık */
    [data-testid="stHorizontalBlock"] [data-testid="column"] { margin-bottom:6px; }

    /* Genel padding azalt */
    .block-container { padding:1rem 0.75rem !important; }

    /* Plotly grafik yüksekliği azalt */
    .js-plotly-plot { max-height:300px; }
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
    """TFF'den Kadınlar Süper Ligi puan durumunu çeker (table.s-table)."""
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
@st.cache_data
def kulup_credentials_yukle() -> dict:
    yol = _DIZIN / "club_credentials.json"
    if yol.exists():
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    # Streamlit Secrets fallback
    try:
        return dict(st.secrets.get("clubs", {}))
    except Exception:
        return {}

def giris_dogrula(kullanici: str, sifre: str) -> dict | None:
    creds = kulup_credentials_yukle()
    bilgi = creds.get(kullanici)
    if not bilgi:
        return None
    try:
        if _BCRYPT_OK and _bcrypt.checkpw(sifre.encode(), bilgi["hash"].encode()):
            return bilgi
    except Exception:
        pass
    return None

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

    st.markdown(
        f"""
        <div style='max-width:580px;margin:0 auto;'>

          <!-- Giriş uyarısı -->
          <div style='background:#1a1f36;border:1px solid #00c85344;border-radius:14px;
               padding:28px;text-align:center;margin-bottom:24px;'>
            <div style='font-size:36px;margin-bottom:10px;'>🔐</div>
            <div style='font-size:17px;font-weight:700;color:#fff;margin-bottom:8px;'>
              {t("Bu özellik giriş gerektiriyor", "This feature requires login")}</div>
            <div style='font-size:13px;color:#8899aa;line-height:1.7;margin-bottom:16px;'>
              {t("Transfer Öner, Gelişmiş Arama ve Oyuncu Profili;", "Transfer Suggest, Advanced Search and Player Profile are")}<br>
              <b style='color:#e0e0e0;'>{t("kulüpler, menajerler ve scout profesyonellere", "exclusive content for clubs, agents and scouting professionals")}</b>{t(" özel içeriklerdir.", ".")}<br>
              {t("Sol üstteki", "Use the")} <b style='color:#00c853;'>🔐 {t("Giriş", "Login")}</b> {t("butonunu kullanarak devam edebilirsiniz.", "button at the top left to continue.")}
            </div>
            <div style='font-size:12px;color:#505870;'>
              {t("Hesabınız yoksa 📬 İletişim sayfasından bize ulaşın.", "If you don't have an account, reach us via the 📬 Contact page.")}
            </div>
          </div>

          <!-- PRO özellik listesi -->
          <div style='background:#12161f;border-radius:12px;padding:20px 24px;
               border:1px solid #1e2340;'>
            <div style='color:#00c853;font-weight:700;font-size:0.88rem;
                 letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>
              ⚡ {t("PRO Pakete Dahil Olanlar", "Included in the PRO Package")}
            </div>
            {ozellik_satiri}
          </div>

          <!-- Fiyat -->
          <div style='text-align:center;margin-top:20px;'>
            <span style='background:linear-gradient(135deg,#0d2b1e,#1a1f36);
                 border:2px solid #00c853;border-radius:12px;padding:14px 32px;
                 display:inline-block;'>
              <div style='color:#00c853;font-size:0.75rem;font-weight:700;
                   letter-spacing:2px;text-transform:uppercase;'>{t("PRO Paket", "PRO Package")}</div>
              <div style='color:#fff;font-size:2rem;font-weight:900;line-height:1.1;'>
                4.999 <span style='font-size:1rem;color:#8899aa;'>{t("TL/ay", "TL/mo")}</span>
              </div>
            </span>
          </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


def giris_formu():
    """Sidebar'da giriş formu gösterir."""
    if st.session_state.get("kulup_giris"):
        return
    with st.sidebar.expander(t("🔐 Giriş", "🔐 Login"), expanded=False):
        with st.form("giris_form", clear_on_submit=True):
            ku = st.text_input(t("Kullanıcı adı", "Username"), placeholder="fenerbahce")
            si = st.text_input(t("Şifre", "Password"), type="password", placeholder="••••")
            if st.form_submit_button(t("Giriş Yap", "Log In"), use_container_width=True):
                sonuc = giris_dogrula(ku.strip(), si.strip())
                if sonuc:
                    st.session_state["kulup_giris"]    = True
                    st.session_state["kulup_kullanici"] = ku.strip()
                    st.session_state["kulup_takim"]    = sonuc["takim"]
                    st.session_state["kulup_ad"]       = sonuc["ad"]
                    st.session_state["kulup_rol"]      = sonuc.get("rol", "kulup")
                    st.session_state["kulup_pro"]      = sonuc.get("pro", False)
                    st.rerun()
                else:
                    st.error(t("Kullanıcı adı veya şifre hatalı.", "Incorrect username or password."))


def pro_kontrol() -> bool:
    """Oturum açmış kullanıcının PRO yetkisi var mı?
    Admin her zaman PRO sayılır; diğerleri kulup_pro flag'ine göre."""
    if st.session_state.get("kulup_rol") == "admin":
        return True
    if st.session_state.get("kulup_kullanici") == "admin":
        return True
    return st.session_state.get("kulup_pro", False)


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


def pro_paywall_goster(ozellik_adi: str = None):
    """PRO üyelik satın alma sayfasını gösterir."""
    if ozellik_adi is None:
        ozellik_adi = t("Bu özellik", "This feature")
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

    st.markdown(
        f"""
        <div style='max-width:640px;margin:0 auto;'>

          <!-- Kilitli uyarısı -->
          <div style='background:#1a1f36;border:1px solid #f0a50044;border-radius:12px;
               padding:16px 22px;display:flex;align-items:center;gap:14px;margin-bottom:28px;'>
            <span style='font-size:1.6rem;'>🔒</span>
            <div>
              <div style='color:#f0c040;font-weight:700;font-size:0.95rem;'>{ozellik_adi} {t("PRO üyelik gerektirir", "requires PRO membership")}</div>
              <div style='color:#8899aa;font-size:0.8rem;margin-top:3px;'>
                {t("Aşağıdaki paketi aktifleştirerek tüm özelliklere anında erişebilirsiniz.", "Activate the package below to instantly access all features.")}
              </div>
            </div>
          </div>

          <!-- Fiyat kartı -->
          <div style='background:linear-gradient(135deg,#0d2b1e 0%,#1a1f36 100%);
               border:2px solid #00c853;border-radius:16px;padding:28px 32px;margin-bottom:28px;
               text-align:center;'>
            <div style='font-size:0.8rem;color:#00c853;letter-spacing:2px;font-weight:700;
                 text-transform:uppercase;margin-bottom:8px;'>⚡ {t("PRO Paket", "PRO Package")}</div>
            <div style='font-size:2.8rem;font-weight:900;color:#fff;line-height:1;'>
              4.999 <span style='font-size:1.4rem;color:#8899aa;'>TL</span>
            </div>
            <div style='color:#8899aa;font-size:0.82rem;margin-top:4px;'>{t("aylık · KDV dahil", "monthly · VAT included")}</div>
            <div style='margin-top:18px;'>
              <span style='background:#00c853;color:#000;font-weight:700;font-size:0.85rem;
                   border-radius:8px;padding:10px 28px;display:inline-block;'>
                {t("Satın Al — Hemen Başla", "Buy Now — Get Started")}
              </span>
            </div>
            <div style='color:#505870;font-size:0.75rem;margin-top:10px;'>
              {t("İptal prosedürü yok · İstediğin an durdur", "No cancellation hassle · Stop anytime")}
            </div>
          </div>

          <!-- Özellik listesi -->
          <div style='background:#12161f;border-radius:12px;padding:20px 24px;'>
            <div style='color:#fff;font-weight:700;font-size:0.9rem;margin-bottom:4px;'>
              {t("PRO pakete dahil olanlar:", "Included in the PRO package:")}
            </div>
            {ozellik_satiri}
          </div>

          <!-- Alt not -->
          <div style='text-align:center;margin-top:20px;color:#505870;font-size:0.78rem;'>
            {t("Kurumsal teklif veya demo için", "For a corporate offer or demo, write to")}
            <a href='mailto:info@heroyun.com' style='color:#00c853;text-decoration:none;'>
              info@heroyun.com
            </a>{t(" adresine yazın.", ".")}
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
            return
        except Exception:
            pass
    # Yerel JSON fallback
    import json
    with open(_SHORTLIST_YOL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
            return
        except Exception:
            pass
    import json
    with open(_ETIKET_YOL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    maclar = mac_sonuclari_yukle()

    # hafta + takım → yenilen gol lookup
    lookup = {}
    for m in maclar:
        lookup[(m["hafta"], m["ev"])]  = m["dep_gol"]
        lookup[(m["hafta"], m["dep"])] = m["ev_gol"]

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

        # Takım adından eşleştirme için anahtar kelimeler üret
        # Genel kelimeleri (SPOR, KADIN, FUTBOL vs.) dışla
        _genel = {"SPOR","KADIN","FUTBOL","TAKIMI","KULÜBÜ","A.Ş","ASK","SK","FK","SPORK"}
        takim_kelimeler = [w for w in takim.split() if len(w) > 4 and w not in _genel]

        yenilen = 0
        mac_say = 0
        for m in mac_gecmisi:
            if m.get("dakika", 0) < 45:
                continue
            hafta = m.get("hafta")
            gol = None
            for (h, t), g in lookup.items():
                if h != hafta:
                    continue
                # Tam eşleşme veya takım adından en az 1 anahtar kelime eşleşmesi
                if t == takim or takim in t or t in takim or \
                   any(kw in t for kw in takim_kelimeler):
                    gol = g
                    break
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

# Mevki kategorileri — geniş → detay (global, her yerde kullanılır)
_MEVKI_DETAY = {
    "Kaleci":    ["Kaleci"],
    "Defans":    ["Sağ Bek", "Sol Bek", "Stoper", "Defans"],
    "Orta Saha": ["Savunmacı Orta Saha", "Merkez Orta Saha", "Hücumcu Orta Saha",
                  "Sol Kanat", "Sağ Kanat", "Orta Saha"],
    "Forvet":    ["Santrafor", "İkinci Santrafor", "Sol Kanat Forvet", "Sağ Kanat Forvet", "Forvet"],
}

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
    "Türkiye": "Türkiye",
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
def ulke_goster(m):
    return _ULKE_EN.get((m or "").strip(), m) if EN else m

def _ilk_uyruk(nat_str: str) -> str:
    """'TurkeyGermany' → 'Turkey', 'France' → 'France'"""
    nat_str = (nat_str or "").strip()
    if not nat_str:
        return ""
    # CamelCase geçişine boşluk ekle, ilk kelimeyi al
    spaced = _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nat_str)
    return spaced.split()[0]


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
    fig.add_trace(go.Scatter(x=sz, y=dk, name=t("Dakika", "Minutes"), yaxis="y2",
                             mode="lines+markers", line=dict(color="#f59e0b", width=3)))
    fig.update_layout(
        barmode="group", height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=12),
        margin=dict(l=10, r=10, t=28, b=10),
        legend=dict(orientation="h", y=1.18, x=0),
        yaxis=dict(title=t("Gol / Asist", "Goals / Assists"), gridcolor="#1e293b"),
        yaxis2=dict(title=t("Dakika", "Minutes"), overlaying="y", side="right", showgrid=False),
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
    st.plotly_chart(fig, use_container_width=True)


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


@st.cache_data(ttl=3600)
def _benzer_havuz(kaynak):
    """kaynak: 'analig' | 'scouting' → feature listesi (pozisyon, yaş, fizik, kariyer)."""
    if kaynak == "analig":
        profiller = sd_profiller
        leistung  = analig_leistung_yukle()
    else:
        profiller = scouting_sd_yukle()
        leistung  = scouting_leistung_yukle()
    havuz = []
    for isim, p in profiller.items():
        if not isinstance(p, dict) or p.get("bulunamadi"):
            continue
        sez = [s for s in leistung.get(isim, {}).get("sezonlar", []) if not s.get("milli")]
        mac = sum(s.get("mac", 0) for s in sez)
        if mac < 5:
            continue
        havuz.append({
            "isim":      isim,
            "kat":       _poz_kategori(p.get("Position", "")),
            "yas":       _yas_hesapla(p.get("Date of birth", "")),
            "boy":       _boy_cm(p.get("Height", "")),
            "ulke":      p.get("Nationality", ""),
            "mac":       mac,
            "gol":       sum(s.get("gol", 0) for s in sez),
            "asist":     sum(s.get("asist", 0) for s in sez),
            "gol_mac":   sum(s.get("gol", 0) for s in sez) / mac,
            "asist_mac": sum(s.get("asist", 0) for s in sez) / mac,
            "dk_mac":    sum(s.get("dakika", 0) for s in sez) / mac,
        })
    return havuz


def _benzer_oyuncular(hedef_isim, kaynak, k=5):
    havuz = _benzer_havuz(kaynak)
    q = next((o for o in havuz if o["isim"] == hedef_isim), None)
    if not q or q["kat"] == "?":
        return []
    grup  = [o for o in havuz if o["kat"] == q["kat"]]
    feats = ["yas", "boy", "mac", "gol_mac", "asist_mac", "dk_mac"]
    rng = {}
    for fe in feats:
        vals = [o[fe] for o in grup if o[fe] > 0]
        rng[fe] = (min(vals), max(vals)) if len(vals) >= 2 else None

    def skor(o):
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

    adaylar = sorted(((skor(o), o) for o in grup if o["isim"] != hedef_isim),
                     reverse=True, key=lambda x: x[0])
    return [(o["isim"], s, f"{o['yas']:.0f} {t('yaş','yrs')} · {o['mac']} {t('maç','matches')} · {o['ulke']}")
            for s, o in adaylar[:k]]


def benzer_oyuncular_goster(hedef_isim, kaynak):
    sonuc = _benzer_oyuncular(hedef_isim, kaynak)
    if not sonuc:
        return
    st.markdown(f"#### 🔎 {t('Benzer Oyuncular', 'Similar Players')}")
    st.caption(t("Aynı mevki · yaş, boy, deneyim ve gol/asist oranlarına göre",
                 "Same position · based on age, height, experience and goal/assist ratios"))
    for isim, skor, bilgi in sonuc:
        if st.button(f"%{skor}  ·  {isim}  ·  {bilgi}",
                     key=f"benzer_{kaynak}_{isim}", use_container_width=True):
            st.query_params["oyuncu"] = isim
            st.rerun()


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
    st.plotly_chart(fig, use_container_width=True)


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
    for s, o in ad[:5]:
        if st.button(f"%{s}  ·  {o['isim']}  ·  {o['yas']:.0f} {t('yaş','yrs')} · {o['ulke']}",
                     key=f"capraz_{o['isim']}", use_container_width=True):
            st.query_params["oyuncu"] = o["isim"]
            st.rerun()


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
        f"<td style='padding:5px 8px'>{v['sd'].get('Nationality','—')}</td>"
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
    st.plotly_chart(fig, use_container_width=True)


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


# -- Odakli scouting oyuncu profili: kart + tum kariyer performansi --
def render_scouting_detay(tam_isim):
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

    st.markdown(f"""
<div style="border:1px solid #3b82f6;border-radius:14px;padding:22px 26px;margin-bottom:18px;
    background:linear-gradient(135deg,#0f172a,#1e293b);">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="font-size:1.5rem;font-weight:800;color:#f1f5f9;">{tam_isim}</div>
    <div>{sd_badge}</div>
  </div>
  <div style="color:#94a3b8;font-size:0.95rem;margin:6px 0 12px;">📌 {mevki}</div>
  <hr style="border-color:#334155;">
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px 18px;font-size:0.9rem;color:#cbd5e1;margin-top:10px;">
    <span>🌍 {ulke_goster(vatandas)}</span>
    <span>📅 {dob} ({yas} {t("yaş","yrs")})</span>
    <span>📏 {boy} · {ayak} {t("ayak","foot")}</span>
    <span>📄 {t("Sözleşme","Contract")}: {sozlesme}</span>
  </div>
</div>""", unsafe_allow_html=True)

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
                         (f"🏳️ {t('Milli Takım','National Team')}", ulke_goster(_dty.get("milli_takim", "")))]:
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
        kariyer_trend_goster(_sezonlar)
        radar_goster(tam_isim, "scouting")
        st.markdown(f"#### ⚽ {t('Tüm Kariyer Performansı', 'Full Career Performance')}")
        _satir_html = ""
        for _s in _sezonlar:
            _milli = _s.get("milli")
            _stil  = "color:#7c8aa0;" if _milli else "color:#cbd5e1;"
            _kulup_cell = _s.get("kulup", "")
            if _milli:
                _kulup_cell += f"<span style='color:#f59e0b;font-size:0.6rem;margin-left:4px;'>{t('MİLLİ','NT')}</span>"
            _satir_html += (
                f"<tr style='{_stil}'>"
                f"<td style='padding:4px 8px;'>{_s.get('sezon','')}</td>"
                f"<td style='padding:4px 8px;font-weight:600;'>{_kulup_cell}</td>"
                f"<td style='padding:4px 8px;'>{_s.get('lig','')}</td>"
                f"<td style='padding:4px 8px;text-align:right;'>{_s.get('mac',0)}</td>"
                f"<td style='padding:4px 8px;text-align:right;'>{_s.get('gol',0)}</td>"
                f"<td style='padding:4px 8px;text-align:right;'>{_s.get('asist',0)}</td>"
                f"<td style='padding:4px 8px;text-align:right;'>{_s.get('sari',0)}</td>"
                f"<td style='padding:4px 8px;text-align:right;'>{_s.get('dakika',0)}</td></tr>"
            )
        st.markdown(f"""
<table style="width:100%;border-collapse:collapse;font-size:0.82rem;">
  <thead><tr style="color:#94a3b8;border-bottom:1px solid #334155;">
    <th style="text-align:left;padding:6px 8px;">{t("Sezon","Season")}</th>
    <th style="text-align:left;padding:6px 8px;">{t("Kulüp","Club")}</th>
    <th style="text-align:left;padding:6px 8px;">{t("Lig","League")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("M","M")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("G","G")}</th>
    <th style="text-align:right;padding:6px 8px;">{t("A","A")}</th>
    <th style="text-align:right;padding:6px 8px;">🟨</th>
    <th style="text-align:right;padding:6px 8px;">{t("Dk","Min")}</th>
  </tr></thead><tbody>{_satir_html}</tbody>
</table>""", unsafe_allow_html=True)
        _g = leistung_data.get(tam_isim, {}).get("guncelleme", "")
        if _g:
            st.caption(f"📡 SoccerDonna · {_g}")
    else:
        st.info(t("Bu oyuncu için detaylı kariyer verisi bulunamadı.", "No detailed career data found for this player."))

    st.markdown("---")
    benzer_oyuncular_goster(tam_isim, "scouting")


# -- Odakli profil yonlendirici: ?oyuncu=X (ana lig veya scouting) --
def render_odakli_profil(isim):
    if st.button(t("← Listeye Dön", "← Back to List"), key="odakli_geri"):
        st.query_params.clear()
        st.rerun()
    st.markdown("---")
    # Ana lig oyuncusu mu?
    if isim in df_tam["Oyuncu"].values:
        if not st.session_state.get("kulup_giris"):
            giris_gerekli_ekrani()
            return
        render_ana_lig_profil(isim)
        return
    # Scouting oyuncusu mu?
    if isim in scouting_sd_yukle():
        _admin = st.session_state.get("kulup_kullanici") == "admin"
        if not (_admin or pro_kontrol()):
            pro_paywall_goster(t("Scouting oyuncu profili", "Scouting player profile"))
            return
        render_scouting_detay(isim)
        return
    st.warning(t(f"Oyuncu bulunamadı: {isim}", f"Player not found: {isim}"))


# -- Ana lig oyuncu profili: tab2 ve odakli profil sayfasi kullanir --
def render_ana_lig_profil(secili):
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

        # Paylaşılabilir link butonu
        share_url = f"?oyuncu={secili}"
        st.markdown(f"🔗 **{t('Paylaşılabilir link', 'Share link')}:** `{share_url}`")
        if st.button(t("📋 Linki Kopyala (adres çubuğuna bakın)", "📋 Copy Link (check address bar)")):
            st.query_params["oyuncu"] = secili

        takim_html = (
            f'<span style="color:#a0aab4">{row["TümTakımlar"]}</span>'
            f'<span class="transfer-badge">🔄 Transfer</span>'
            if transfer else
            f'<span style="color:#00c853">{row["Takım"]}</span>'
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
                f'<span style="background:#0d3b2e;color:#00c853;border-radius:6px;'
                f'padding:4px 12px;font-size:0.82rem;font-weight:600">'
                f'{mevki_ikon} {sd_mevki}</span></div>'
            )

        st.markdown(f"""
        <div class="profil-kart">
          <h2>{secili}</h2>
          {mevki_html}
          <div style="margin-bottom:6px">🏟 {takim_html}</div>
          {sd_bilgi_html}
          <div class="profil-stat">
            <div class="profil-stat-item"><div class="deger">{mac}</div><div class="ad">{t("Maç","Matches")}</div></div>
            <div class="profil-stat-item"><div class="deger">{ilk11}</div><div class="ad">▶ {t("İlk 11","Starting 11")}</div></div>
            <div class="profil-stat-item"><div class="deger">{yedek}</div><div class="ad">↗ {t("Yedek","Sub")}</div></div>
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
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        p1, p2 = st.columns(2)

        # ── Son 5 maç formu ──────────────────────────────────────────────────
        with p1:
            st.markdown(f"##### {t('Son 5 Maç Formu', 'Last 5 Matches Form')}")
            gecmis = sorted(detay.get("mac_gecmisi",[]), key=lambda x: x["hafta"], reverse=True)[:5]
            if gecmis:
                chipler = ""
                for m in gecmis:
                    if m["gol"] > 0:
                        renk, etiket = "#1b5e20", f"⚽ {m['gol']} Gol ({m['hafta']}.H)"
                    elif m["kirmizi"] > 0:
                        renk, etiket = "#b71c1c", f"🟥 ({m['hafta']}.H)"
                    elif m["sari"] > 0:
                        renk, etiket = "#f57f17", f"🟨 ({m['hafta']}.H)"
                    elif m["dakika"] >= 70:
                        renk, etiket = "#0d3b2e", f"✅ {m['dakika']}dk ({m['hafta']}.H)"
                    else:
                        renk, etiket = "#1a1f36", f"↗ {m['dakika']}dk ({m['hafta']}.H)"
                    chipler += f'<span class="form-chip" style="background:{renk}">{etiket}</span>'
                st.markdown(f'<div class="form-kutu">{chipler}</div>', unsafe_allow_html=True)
            else:
                st.caption(t("Maç verisi yok.", "No match data."))

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
                fig.add_trace(go.Bar(x=haftalar, y=dakikalar, name="Dakika",
                    marker_color="#2979ff", opacity=0.75,
                    hovertemplate="Hafta %{x}<br>%{y}dk<extra></extra>"))
                fig.add_trace(go.Scatter(x=haftalar, y=[g*18 for g in goller],
                    name="Gol", mode="markers",
                    marker=dict(color="#00c853", size=11, symbol="star"),
                    hovertemplate="Hafta %{x}<br>Gol:%{customdata}<extra></extra>",
                    customdata=goller))
                fig.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=260,
                    legend=dict(orientation="h", y=1.1),
                    xaxis=dict(title="Hafta", gridcolor="#2d3561"),
                    yaxis=dict(title="Dakika", gridcolor="#2d3561"),
                    margin=dict(l=40,r=10,t=10,b=40))
                st.plotly_chart(fig, use_container_width=True)

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
                    xaxis=dict(title="Dakika Aralığı", gridcolor="#2d3561"),
                    yaxis=dict(title="Gol", gridcolor="#2d3561", dtick=1),
                    margin=dict(l=30,r=10,t=10,b=40), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            elif gol > 0:
                st.caption(t("Gol dakikası verisi bu sezonda mevcut değil.", "Goal minute data not available for this season."))
            else:
                st.caption(t("Bu oyuncu gol atmadı.", "This player has not scored."))

        # ── Seriler ──────────────────────────────────────────────────────────
        if gecmis_tam:
            st.markdown(f"##### 🔥 {t('Seri Rekorları', 'Streak Records')}")
            # En uzun ardışık maç serisi
            en_uzun_mac = max_seri([1 for _ in gecmis_tam])
            # En uzun gol serisi (ardışık maçlarda gol)
            gol_var = [1 if m["gol"]>0 else 0 for m in gecmis_tam]
            en_uzun_gol = max_seri(gol_var)
            # En uzun kart almama serisi
            temiz = [1 if m["sari"]==0 and m["kirmizi"]==0 else 0 for m in gecmis_tam]
            en_uzun_temiz = max_seri(temiz)

            s1,s2,s3 = st.columns(3)
            s1.metric(f"🏃 {t('En Uzun Maç Serisi', 'Longest Match Streak')}", f"{en_uzun_mac} {t('maç','matches')}")
            s2.metric(f"⚽ {t('En Uzun Gol Serisi', 'Longest Goal Streak')}", f"{en_uzun_gol} {t('maç','matches')}")
            s3.metric(f"🛡️ {t('En Uzun Temiz Seri', 'Longest Clean Streak')}", f"{en_uzun_temiz} {t('maç','matches')}")

        # ── Transfer kırılımı ─────────────────────────────────────────────────
        if transfer:
            st.markdown(f"##### {t('Takım Bazlı İstatistikler', 'Stats by Club')}")
            satirlar = ""
            for d in detay.get("takim_detay", []):
                satirlar += f"""
                <div class="takim-detay-satir">
                  <span class="td-adi">🏟 {d['takim']}</span>
                  <span class="td-stats">
                    {d['mac']} {t('maç','matches')} · {d['gol']} {t('gol','goals')} · {d['dakika']} {t('dk','min')} ·
                    🟨{d['sari']} 🟥{d['kirmizi']}
                  </span>
                </div>"""
            st.markdown(satirlar, unsafe_allow_html=True)

        # ── Oyuncu Kartı ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(f"##### 🃏 {t('Oyuncu Kartı', 'Player Card')}")
        st.markdown(f"""
        <div style="max-width:320px;margin:0 auto;
             background:linear-gradient(145deg,#1a1f36,#0d3b2e);
             border-radius:18px;padding:26px 28px;text-align:center;
             box-shadow:0 8px 32px rgba(0,0,0,0.6);
             border:1px solid #00c85344;">
          <div style="font-size:0.68rem;letter-spacing:3px;color:#00c853aa;margin-bottom:4px">
            {t("KADIN FUTBOL · 2025-2026","WOMEN'S FOOTBALL · 2025-2026")}
          </div>
          <div style="font-size:1.2rem;font-weight:800;color:#fff;margin-bottom:2px">{secili}</div>
          <div style="color:#8899aa;font-size:0.78rem;margin-bottom:20px">{row['Takım'][:35]}</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">
            <div style="background:rgba(0,200,83,0.08);border:1px solid #00c85333;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#00c853">{gol}</div>
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

        # Ana lig kariyer trendi (analig_leistungsdaten.json hazır olunca)
        _al_sezon = analig_leistung_yukle().get(secili, {}).get("sezonlar", [])
        if _al_sezon:
            st.markdown("---")
            kariyer_trend_goster(_al_sezon)
            radar_goster(secili, "analig")

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
# Karşılama ekranı: ana içeriğe geçmeden önce herkese gösterilir (giriş gerekmez)
if "girildi" not in st.session_state:
    st.session_state["girildi"] = False

# ─── BAŞLIK & NAVİGASYON ──────────────────────────────────────────────────────
_nav_is_admin = st.session_state.get("kulup_kullanici") == "admin"
bas_sol, nav1, nav3, nav4, nav5, nav_dil = st.columns([3, 1, 1, 1, 1, 0.8])

with bas_sol:
    st.markdown(f"""
    <div class="baslik-kutu">
      <h1>{t("⚽ Kadın Futbolu Veri &amp; Scouting Platformu",
              "⚽ Women's Football Data &amp; Scouting Platform")}</h1>
      <p>{t("Türkiye Kadınlar Süper Ligi istatistikleri · uluslararası oyuncu havuzu · kariyer ve benzerlik analizi · kulüplere özel kadro danışmanlığı",
            "Turkish Women's Super League stats · international player pool · career &amp; similarity analysis · club-tailored squad consultancy")}</p>
    </div>""", unsafe_allow_html=True)
with nav1:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(t("🏠 Ana Sayfa", "🏠 Home"), use_container_width=True):
        st.query_params.clear()
        for k in list(st.session_state.keys()):
            if k not in ("sayfa","kulup_giris","kulup_kullanici","kulup_takim","kulup_ad","kulup_rol","kulup_pro","dil","girildi"):
                del st.session_state[k]
        st.session_state["sayfa"] = "ana"
        st.session_state["girildi"] = True  # Ana Sayfa = doğrudan içeriğe geç (karşılamayı atla)
        st.rerun()
with nav3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(t("📬 İletişim", "📬 Contact"), use_container_width=True):
        st.session_state["sayfa"] = "iletisim"
        st.rerun()
with nav4:
    st.markdown("<br>", unsafe_allow_html=True)
    _sc_active = st.session_state.get("sayfa") == "scouting"
    _sc_label  = "🔎 Scouting ◀" if _sc_active else "🔎 Scouting"
    if st.button(_sc_label, use_container_width=True, type="primary" if _sc_active else "secondary"):
        st.session_state["sayfa"] = "ana" if _sc_active else "scouting"
        st.rerun()

with nav5:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.get("kulup_giris"):
        kulup_ad = st.session_state.get("kulup_ad","")
        if st.button(f"🚪 {kulup_ad}", use_container_width=True):
            for k in ["kulup_giris","kulup_kullanici","kulup_takim","kulup_ad","kulup_rol","kulup_pro"]:
                st.session_state.pop(k, None)
            st.rerun()
    else:
        if st.button(t("🔐 Giriş", "🔐 Login"), use_container_width=True):
            st.session_state["sayfa"] = "giris"
            st.rerun()

with nav_dil:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🌐 EN" if not EN else "🌐 TR", use_container_width=True, help="Language / Dil"):
        st.session_state["dil"] = "EN" if not EN else "TR"
        st.rerun()

# Giriş formu sidebar'da her zaman
giris_formu()

# PRO / üye rozeti sidebar'da göster
if st.session_state.get("kulup_giris"):
    _is_pro = st.session_state.get("kulup_pro", False)
    _badge_bg  = "#0d3b2e" if _is_pro else "#1a1f36"
    _badge_bdr = "#00c853" if _is_pro else "#445566"
    _badge_lbl = t("⚡ PRO Üye", "⚡ PRO Member") if _is_pro else t("🔓 Üye", "🔓 Member")
    _badge_clr = "#00c853"  if _is_pro else "#8899aa"
    st.sidebar.markdown(
        f"<div style='background:{_badge_bg};border:1px solid {_badge_bdr};"
        f"border-radius:8px;padding:8px 14px;text-align:center;margin-top:4px;'>"
        f"<span style='color:{_badge_clr};font-size:0.8rem;font-weight:700;'>{_badge_lbl}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ─── HAKKINDA SAYFASI ─────────────────────────────────────────────────────────
# ─── ODAKLI PROFİL SAYFASI (?oyuncu=X) — sekmeler yerine tek oyuncu ───────────
if url_oyuncu:
    render_odakli_profil(url_oyuncu)
    st.stop()

def render_hakkinda_icerik():
    """Hakkında metnini render eder (Hakkında sayfası + GİRİŞ sekmesi ortak kullanır)."""
    st.markdown(f"""
    <div style='max-width:760px;margin:0 auto;padding:10px 0 40px;'>

    <h2 style='color:#00c853;margin-bottom:6px;'>{t("Biz Kimiz?", "Who Are We?")}</h2>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Türkiye'de kadın futbol liglerini takip eden bir grup futbol delisiyiz. Yıllardır tribünlerde, ekranların başında ve saha kenarlarında bu ligin büyümesine tanıklık ettik. Ama bir şeyin hep eksik kaldığını fark ettik: <b style='color:#fff;'>veri.</b>",
       "We are a group of football fanatics following women's football leagues in Türkiye. For years we've witnessed this league grow from the stands, the screens and the touchlines. But we noticed one thing was always missing: <b style='color:#fff;'>data.</b>")}
    </p>

    <h2 style='color:#00c853;margin-top:32px;margin-bottom:6px;'>{t("Neden Bu Siteyi Kurduk?", "Why Did We Build This?")}</h2>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Bir oyuncuyu bir maçta izlemek, o oyuncu hakkında tam bir fikir vermez. Gözlem yanılabilir — kötü bir gün, yorgunluk, takımın taktik yapısı ya da sadece o günkü rakip; bunların hepsi algıyı bozar. Kulüplerin çoğu hâlâ transferlerde \"rakibe karşı oynadığı o maçtaki izlenim\" ya da duyuma dayalı kararlar alıyor.",
       "Watching a player in a single match doesn't give a full picture. Observation can mislead — a bad day, fatigue, the team's tactical setup or just that day's opponent all distort perception. Most clubs still make transfer decisions based on \"the impression from that one match against us\" or on hearsay.")}
    </p>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Biz buna karşı <b style='color:#fff;'>ölçme ve değerlendirme metotları</b> geliştirmeye çalışıyoruz. Henüz değerini bulamamış ya da bulma aşamasındaki oyuncuları verilerle desteklemeyi, onların ligdeki gerçek katkılarını görünür kılmayı hedefliyoruz. Böylece takımlar; sadece rakipleri olduğu maçlardaki gözleme ya da kulaktan dolma bilgilere değil, <b style='color:#fff;'>sezon boyu biriken somut istatistiklere</b> dayanarak daha nitelikli kadrolar oluşturabilsin.",
       "Against this, we try to develop <b style='color:#fff;'>measurement and evaluation methods</b>. We aim to back undervalued or rising players with data and make their real contribution to the league visible. So that teams can build better squads based on <b style='color:#fff;'>concrete stats accumulated across the season</b> — not just observation from matches against them or word of mouth.")}
    </p>

    <h2 style='color:#00c853;margin-top:32px;margin-bottom:6px;'>{t("Bu Sitede Ne Var?", "What's on This Site?")}</h2>
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


if st.session_state["sayfa"] == "hakkinda":
    render_hakkinda_icerik()
    st.stop()

# ─── İLETİŞİM SAYFASI ─────────────────────────────────────────────────────────
if st.session_state["sayfa"] == "iletisim":
    st.markdown(f"""
    <div style='max-width:600px;margin:0 auto;padding:10px 0 40px;'>
    <h2 style='color:#00c853;margin-bottom:6px;'>{t("İletişim", "Contact")}</h2>
    <p style='color:#c9d1d9;font-size:15px;line-height:1.8;'>
    {t("Öneri, hata bildirimi veya iş birliği için bize ulaşabilirsiniz.",
       "Reach us for suggestions, bug reports or collaboration.")}
    </p>
    <div style='background:#1a1f36;border-radius:12px;padding:24px;border-left:4px solid #00c853;margin-top:16px;'>
      <div style='color:#8899aa;font-size:13px;margin-bottom:8px;'>{t("📧 E-posta", "📧 E-mail")}</div>
      <div style='color:#fff;font-size:15px;font-weight:600;'>mehmetbarandanis@gmail.com</div>
      <div style='color:#8899aa;font-size:13px;margin-top:20px;margin-bottom:8px;'>{t("🐦 Sosyal Medya", "🐦 Social Media")}</div>
      <div style='color:#fff;font-size:15px;'>{t("Yakında aktif olacak", "Coming soon")}</div>
    </div>
    <p style='color:#505870;font-size:12px;margin-top:28px;'>
    {t("Veri hatası veya eksik oyuncu bildirimleri için lütfen oyuncu adı ve doğru bilgiyi içeren bir mesaj gönderin. En kısa sürede güncelliyoruz.",
       "For data errors or missing players, please send a message with the player name and correct info. We update as soon as possible.")}
    </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── TALEP / DANIŞMANLIK SAYFASI ─────────────────────────────────────────────
if st.session_state["sayfa"] == "talep":
    # Hero
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#0f3d2e,#1a5c43);border-radius:16px;
        padding:24px 30px;border-left:5px solid #00c853;margin-bottom:22px;'>
      <h1 style='font-size:1.5rem;margin:0 0 6px;color:#fff;'>{t("⚽ Kadronu birlikte kuralım", "⚽ Let's build your squad together")}</h1>
      <p style='color:#a7f3d0;font-size:0.95rem;line-height:1.6;margin:0;'>
      {t("Doğru oyuncu, doğru veriyle bulunur. Scouting ve kadro planlamada veri + saha gözü birleşiyor — kulübüne özel danışmanlık.",
         "The right player is found with the right data. Data and on-field insight combine in scouting and squad planning — consultancy tailored to your club.")}</p>
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
            <div style='border:1px solid #334155;border-radius:12px;padding:16px;
                background:linear-gradient(135deg,#0f172a,#1a1f36);margin-bottom:14px;min-height:150px;'>
              <div style='font-size:1.5rem;'>{_ik}</div>
              <div style='font-size:1.0rem;font-weight:700;color:#f1f5f9;margin:4px 0 2px;'>{_ad}</div>
              <div style='color:#64748b;font-size:0.7rem;margin-bottom:8px;'>{_et}</div>
              <div style='color:#94a3b8;font-size:0.82rem;line-height:1.55;'>{_ac}</div>
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
    _tip_opts = [
        "Belirli bir oyuncu için detaylı rapor",
        "Belirli bir mevkiye oyuncu önerisi",
        "Birkaç oyuncu arasında tercih / kıyas",
        "Takımı baştan kurma danışmanlığı",
    ]
    _tip_en = dict(zip(_tip_opts, [
        "Detailed report on a specific player",
        "Player suggestion for a position",
        "Choice / comparison among a few players",
        "Full squad building consultancy",
    ]))
    with st.form("talep_form", clear_on_submit=False):
        tip = st.selectbox(t("Talep türü", "Request type"), _tip_opts,
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
                                       use_container_width=True, type="primary")
    if gonder:
        if not (isim.strip() and email.strip() and detay.strip()):
            st.error(t("Lütfen Ad Soyad, E-posta ve Detay alanlarını doldurun.",
                       "Please fill in Full Name, E-mail and Details."))
        else:
            with st.spinner(t("Talebiniz gönderiliyor...", "Sending your request...")):
                _k, _m = talep_gonder(tip, isim.strip(), kulup.strip(),
                                      email.strip(), detay.strip(), oneri=_oneri_metni)
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

# ─── SCOUTİNG SAYFASI ────────────────────────────────────────────────────────
if st.session_state.get("sayfa") == "scouting":
    if _nav_is_admin:
        st.markdown(f"""
        <div style='margin-bottom:4px;'>
          <h2 style='color:#f1f5f9;margin-bottom:4px;'>🔎 {t("Scouting Havuzu","Scouting Pool")}</h2>
          <p style='color:#64748b;font-size:0.85rem;'>
            {t("Yabancı oyuncu kurasyonu · 2026-27 kadro planlama · SoccerDonna verileri ile zenginleştirilmiş",
               "Foreign player curation · 2026-27 squad planning · enriched with SoccerDonna data")}
          </p>
        </div>
        """, unsafe_allow_html=True)

        sc_df = scouting_gsheet_yukle()
        sd_data = scouting_sd_yukle()
        leistung_data = scouting_leistung_yukle()
        detay_data = scouting_detay_yukle()
        _sl_kullanici = st.session_state.get("kulup_kullanici", "admin")
        _sl_liste     = shortlist_kullanici(_sl_kullanici)
        _etiket_liste = etiket_kullanici(_sl_kullanici)

        if sc_df.empty:
            st.warning(t("Google Sheets'e bağlanılamadı veya liste boş.", "Could not connect to Google Sheets or the list is empty."))
        else:
            # ── ARAMA & FİLTRELER ─────────────────────────────────
            st.markdown("---")
            isim_col = "Tam İsmi" if "Tam İsmi" in sc_df.columns else sc_df.columns[0]
            vat_col  = "Vatandaşlık" if "Vatandaşlık" in sc_df.columns else None

            with st.expander(t("📊 Veri Kapsama Paneli — eksik veri özeti", "📊 Data Coverage Panel — missing data summary")):
                veri_kapsama_goster(sc_df, isim_col, sd_data, leistung_data)

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
                dob = v.get("Date of birth","")
                if dob and len(dob) >= 4:
                    try: yillar.append(int(dob[-4:]))
                    except: pass
            yil_min = min(yillar) if yillar else 1990
            yil_max = max(yillar) if yillar else 2008

            _sc_tumu = t("Tümü", "All")
            _sc_ayak_en = {"Tümü":"All","right":"Right","left":"Left","both":"Both"}
            # Satır 1: İsim + Vatandaşlık + Mevki kategorisi + Detay
            sc_r1c1, sc_r1c2, sc_r1c3, sc_r1c4 = st.columns([2, 1, 1, 1])
            with sc_r1c1:
                isim_q = st.text_input(f"👤 {t('Oyuncu Ara','Search Player')}", placeholder=t("İsim yaz…","Type a name…"), key="sc_isim")
            with sc_r1c2:
                vat_opts = sorted(sc_df[vat_col].dropna().replace("","").unique().tolist()) if vat_col else []
                vat_sec = st.selectbox(f"🌍 {t('Vatandaşlık','Nationality')}", [_sc_tumu] + [v for v in vat_opts if v],
                    format_func=lambda x: x if x == _sc_tumu else ulke_goster(x), key="sc_vat")
            with sc_r1c3:
                sc_kategori = st.selectbox(f"📌 {t('Mevki','Position')}", [_sc_tumu] + list(_MEVKI_DETAY.keys()),
                    format_func=mevki_goster, key="sc_kat")
            with sc_r1c4:
                sc_detay_opts = [_sc_tumu] + (_MEVKI_DETAY.get(sc_kategori, []) if sc_kategori != _sc_tumu else [])
                sc_detay = st.selectbox(f"↳ {t('Detay','Detail')}", sc_detay_opts,
                    format_func=mevki_goster, key="sc_detay", disabled=(sc_kategori == _sc_tumu))

            # Satır 2: Doğum yılı + Ayak
            sc_r2c1, sc_r2c2, sc_r2c3 = st.columns([2, 1, 1])
            with sc_r2c1:
                yil_range = st.slider(f"📅 {t('Doğum Yılı','Birth Year')}", yil_min, yil_max, (yil_min, yil_max), key="sc_yil")
            with sc_r2c2:
                ayak_sec = st.selectbox(f"🦶 {t('Ayak','Foot')}", [_sc_tumu, "right", "left", "both"], key="sc_ayak",
                    format_func=lambda x: (_sc_ayak_en.get(x, x) if x != _sc_tumu else _sc_tumu) if EN else x)
            with sc_r2c3:
                st.markdown("<br>", unsafe_allow_html=True)
                sadece_sl = st.checkbox(f"⭐ {t('Shortlistim','My Shortlist')} ({len(_sl_liste)})", key="sc_sl")

            # Filtrele
            filtered = sc_df.copy()
            if isim_q.strip():
                filtered = filtered[filtered[isim_col].str.contains(isim_q.strip(), case=False, na=False)]
            if vat_col and vat_sec != _sc_tumu:
                filtered = filtered[filtered[vat_col] == vat_sec]

            def sd_filtre(tam_isim):
                v = sd_data.get(tam_isim, {})
                if v.get("bulunamadi"): return True
                # Mevki filtresi
                sd_pos  = v.get("Position","")
                tr_mevki = _SD_MEVKI_NORM.get(sd_pos, mevki_normalize(sd_pos))
                if sc_kategori != _sc_tumu:
                    if sc_detay != _sc_tumu:
                        if tr_mevki != sc_detay: return False
                    else:
                        if tr_mevki not in _MEVKI_DETAY.get(sc_kategori, []): return False
                # Ayak filtresi
                if ayak_sec != _sc_tumu and v.get("Foot","") != ayak_sec:
                    return False
                # Yıl filtresi
                dob = v.get("Date of birth","")
                if dob and len(dob) >= 4:
                    try:
                        y = int(dob[-4:])
                        if not (yil_range[0] <= y <= yil_range[1]): return False
                    except: pass
                return True

            filtered = filtered[filtered[isim_col].apply(sd_filtre)]

            if sadece_sl:
                filtered = filtered[filtered[isim_col].isin(_sl_liste)]

            _bulundu_txt = (f"⭐ {len(filtered)} {t('shortlistinde oyuncu','players in your shortlist')}" if sadece_sl
                            else f"🎯 {len(filtered)} {t('oyuncu bulundu','players found')}")
            st.markdown(
                f"<div style='color:#00c853;font-size:13px;font-weight:700;margin:6px 0 12px;'>"
                f"{_bulundu_txt}</div>", unsafe_allow_html=True)

            if sadece_sl and len(filtered) >= 2:
                with st.expander(t("⚖️ Shortlist Karşılaştırma", "⚖️ Shortlist Comparison"), expanded=True):
                    shortlist_karsilastirma_goster(
                        filtered[isim_col].tolist(), sd_data, leistung_data)

            if filtered.empty:
                st.info(t("Filtrelerle eşleşen oyuncu yok.", "No players match the filters."))
            else:
                for i in range(0, len(filtered), 2):
                    cols = st.columns(2)
                    for j, col in enumerate(cols):
                        if i + j >= len(filtered):
                            break
                        row      = filtered.iloc[i + j]
                        tam_isim = str(row.get(isim_col, ""))
                        vatandas = str(row.get(vat_col, "")) if vat_col else "—"
                        vatan2   = str(row.get("Vatandaşlık 2","")) if "Vatandaşlık 2" in sc_df.columns else ""

                        # SoccerDonna verisini birleştir
                        sd = sd_data.get(tam_isim, {})
                        dob      = sd.get("Date of birth","—")
                        yas      = sd.get("Age","?")
                        boy      = sd.get("Height","—")
                        mevki    = sd.get("Position","—")
                        ayak     = sd.get("Foot","—")
                        kulup    = sd.get("Name in native country","") or sd.get("© " + vatandas, "")
                        sozlesme = sd.get("Contract until","—")
                        sd_url   = sd.get("profil_url","")
                        sd_found = bool(sd) and not sd.get("bulunamadi")

                        sd_badge = (f'<a href="{sd_url}" target="_blank" style="font-size:0.72rem;'
                                    f'color:#60a5fa;text-decoration:none;">🔗 SoccerDonna</a>') if sd_url else ""
                        renk = "#3b82f6" if sd_found else "#6b7280"

                        with col:
                            _etk = _etiket_liste.get(tam_isim, "")
                            _etk_html = (f"<span style='font-size:0.62rem;background:#1e293b;"
                                         f"border:1px solid #475569;border-radius:4px;padding:1px 6px;"
                                         f"margin-left:6px;white-space:nowrap;'>{etiket_badge_goster(_etk)}</span>") if _etk else ""
                            _dty = detay_data.get(tam_isim, {})
                            _rol = _dty.get("rol", "")
                            _mrd = _dty.get("mr_danis", "")
                            _mrc = _MR_DANIS_RENK.get(_mrd, "#475569")
                            _mrd_html = (f"<span style='font-size:0.62rem;background:{_mrc}22;"
                                         f"border:1px solid {_mrc};color:{_mrc};border-radius:4px;"
                                         f"padding:1px 7px;margin-left:6px;white-space:nowrap;font-weight:700;'>"
                                         f"★ {danis_goster(_mrd)}</span>") if _mrd else ""
                            _rol_html = (f" &nbsp;·&nbsp; <span style='color:#a5b4fc;'>🎭 {rol_goster(_rol)}</span>") if _rol else ""
                            st.markdown(f"""
<div style="border:1px solid {renk};border-radius:12px;padding:16px 18px;margin-bottom:14px;
    background:linear-gradient(135deg,#0f172a,#1e293b);">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
    <div style="font-size:1.05rem;font-weight:700;color:#f1f5f9;">{tam_isim}{_mrd_html}{_etk_html}</div>
    <div style="font-size:0.72rem;color:#64748b;">{sd_badge}</div>
  </div>
  <div style="color:#94a3b8;font-size:0.82rem;margin-bottom:8px;">📌 {mevki}{_rol_html}</div>
  <hr style="border-color:#334155;margin:7px 0;">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px 12px;font-size:0.80rem;color:#cbd5e1;">
    <span>🌍 {ulke_goster(vatandas)}</span>
    <span>🏴 {ulke_goster(vatan2) if vatan2 and vatan2 != vatandas else "—"}</span>
    <span>📅 {dob} ({yas} {t("yaş","yrs")})</span>
    <span>📏 {boy} · {ayak} {t("ayak","foot")}</span>
  </div>
  <hr style="border-color:#334155;margin:7px 0;">
  <div style="font-size:0.80rem;color:#94a3b8;">
    📄 {t("Sözleşme","Contract")}: {sozlesme}
    {"" if sd_found else f"<br><span style='color:#475569;font-size:0.75rem;'>⚠️ {t('SoccerDonna verisi bulunamadı','SoccerDonna data not found')}</span>"}
  </div>
</div>""", unsafe_allow_html=True)

                            # Shortlist ⭐ toggle butonu
                            _fav = tam_isim in _sl_liste
                            _lbl = t("⭐ Shortlist'te","⭐ In Shortlist") if _fav else t("☆ Shortlist'e ekle","☆ Add to Shortlist")
                            if st.button(_lbl, key=f"sl_{i+j}", use_container_width=True):
                                shortlist_toggle(_sl_kullanici, tam_isim)
                                st.rerun()
                            if st.button(t("👤 Profili Aç","👤 Open Profile"), key=f"prof_{i+j}", use_container_width=True):
                                st.query_params["oyuncu"] = tam_isim
                                st.rerun()
                            _mev_etk = _etiket_liste.get(tam_isim, "—")
                            _ETIKET_EN = {"—":"—", "🔴 Öncelik":"🔴 Priority", "👀 İzle":"👀 Watch",
                                          "💰 Pahalı":"💰 Expensive", "✅ Görüşüldü":"✅ Contacted"}
                            _yeni_etk = st.selectbox(
                                t("Etiket","Tag"), _ETIKETLER,
                                index=_ETIKETLER.index(_mev_etk) if _mev_etk in _ETIKETLER else 0,
                                format_func=lambda x: _ETIKET_EN.get(x, x) if EN else x,
                                key=f"etk_{i+j}", label_visibility="collapsed")
                            if _yeni_etk != _mev_etk:
                                etiket_ayarla(_sl_kullanici, tam_isim, _yeni_etk)
                                st.rerun()

                            # Tüm kariyer performansı (leistungsdaten) expander
                            _kariyer  = leistung_data.get(tam_isim, {})
                            _sezonlar = _kariyer.get("sezonlar", [])
                            if _sezonlar:
                                with col.expander(t("⚽ Tüm Kariyer Performansı","⚽ Full Career Performance")):
                                    _satir_html = ""
                                    for _s in _sezonlar:
                                        _milli = _s.get("milli")
                                        _stil  = "color:#7c8aa0;" if _milli else "color:#cbd5e1;"
                                        _kulup_cell = _s.get("kulup", "")
                                        if _milli:
                                            _kulup_cell += (f"<span style='color:#f59e0b;font-size:0.6rem;"
                                                            f"margin-left:4px;'>{t('MİLLİ','NT')}</span>")
                                        _satir_html += (
                                            f"<tr style='{_stil}'>"
                                            f"<td style='padding:4px 6px;'>{_s.get('sezon','')}</td>"
                                            f"<td style='padding:4px 6px;font-weight:600;'>{_kulup_cell}</td>"
                                            f"<td style='padding:4px 6px;'>{_s.get('lig','')}</td>"
                                            f"<td style='padding:4px 6px;text-align:right;'>{_s.get('mac',0)}</td>"
                                            f"<td style='padding:4px 6px;text-align:right;'>{_s.get('gol',0)}</td>"
                                            f"<td style='padding:4px 6px;text-align:right;'>{_s.get('asist',0)}</td>"
                                            f"<td style='padding:4px 6px;text-align:right;'>{_s.get('sari',0)}</td>"
                                            f"<td style='padding:4px 6px;text-align:right;'>{_s.get('dakika',0)}</td>"
                                            f"</tr>"
                                        )
                                    st.markdown(f"""
<div style="max-height:380px;overflow-y:auto;">
<table style="width:100%;border-collapse:collapse;font-size:0.74rem;">
  <thead><tr style="color:#94a3b8;border-bottom:1px solid #334155;">
    <th style="text-align:left;padding:5px 6px;">{t("Sezon","Season")}</th>
    <th style="text-align:left;padding:5px 6px;">{t("Kulüp","Club")}</th>
    <th style="text-align:left;padding:5px 6px;">{t("Lig","League")}</th>
    <th style="text-align:right;padding:5px 6px;">M</th>
    <th style="text-align:right;padding:5px 6px;">G</th>
    <th style="text-align:right;padding:5px 6px;">A</th>
    <th style="text-align:right;padding:5px 6px;">🟨</th>
    <th style="text-align:right;padding:5px 6px;">{t("Dk","Min")}</th>
  </tr></thead>
  <tbody>{_satir_html}</tbody>
</table></div>""", unsafe_allow_html=True)
                                    _g = _kariyer.get("guncelleme", "")
                                    if _g:
                                        st.caption(f"📡 SoccerDonna · {_g}")

                            # Sezon istatistikleri expander (profil sayfası — kısmi)
                            elif sd_found and sd.get("sezon_istatistikleri"):
                                with col.expander(t("📊 Sezon İstatistikleri","📊 Season Statistics")):
                                    _rows = sd["sezon_istatistikleri"]
                                    if _rows:
                                        _df = pd.DataFrame(_rows)
                                        st.dataframe(_df, hide_index=True, use_container_width=True)
    else:
        st.markdown(f"""
        <div style="max-width:560px;margin:60px auto;text-align:center;
             background:linear-gradient(135deg,#0f172a,#1e293b);
             border:1px solid #f59e0b;border-radius:16px;padding:48px 36px;">
          <div style="font-size:3rem;margin-bottom:16px;">🔎</div>
          <h2 style="color:#f1f5f9;margin-bottom:12px;">{t("Scouting Havuzu","Scouting Pool")}</h2>
          <p style="color:#94a3b8;font-size:0.95rem;line-height:1.7;margin-bottom:24px;">
            {t("Yabancı ve yerli oyuncu kurasyonu, 2026-27 kadro planlama önerileri ve detaylı oyuncu profilleri",
               "Curation of foreign and domestic players, 2026-27 squad planning suggestions and detailed player profiles")}
            <b style="color:#f59e0b;">{t("PRO üyelik","PRO membership")}</b> {t("gerektirir.","required.")}
          </p>
          <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
               padding:20px;margin-bottom:28px;text-align:left;">
            <p style="color:#cbd5e1;font-size:0.85rem;margin:0 0 10px;font-weight:600;">{t("PRO ile neler var?","What's in PRO?")}</p>
            <p style="color:#64748b;font-size:0.82rem;line-height:1.8;margin:0;">
              🌍 {t("Türkiye dışı oyuncu havuzu","International player pool")}<br>
              🎯 {t("Mevki bazlı scouting profilleri","Position-based scouting profiles")}<br>
              📊 {t("Detaylı oyuncu değerlendirmeleri","Detailed player assessments")}<br>
              📋 {t("Kadro planlama önerileri","Squad planning suggestions")}<br>
              🤝 {t("Doğrudan danışmanlık erişimi","Direct consultancy access")}
            </p>
          </div>
          <p style="color:#475569;font-size:0.80rem;">
            {t("PRO üyelik için 📬 İletişim sayfasından bize ulaşın.","For PRO membership, reach us via the 📬 Contact page.")}
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
    # Scouting sayısı: önce GSheets, yoksa yerel SD profilleri
    try:
        _sc = scouting_gsheet_yukle()
        scouting_n = len(_sc) if _sc is not None and not _sc.empty else len(scouting_sd_yukle())
    except Exception:
        try: scouting_n = len(scouting_sd_yukle())
        except Exception: scouting_n = 0
    try: mac_n = len(mac_sonuclari_yukle())
    except Exception: mac_n = 0
    return {
        "oyuncu":   len(df_tam),
        "takim":    int(df_tam["Takım"].nunique()),
        "scouting": scouting_n,
        "mac":      mac_n,
        "gol":      int(df_tam["Gol"].sum()),
        "yerli":    yerli,
        "yabanci":  yabanci,
        "ort_yas":  round(float(yas.mean()), 1) if not yas.empty else 0,
        "u23":      int((yas < 23).sum()) if not yas.empty else 0,
    }


def _ozet_kart(deger, etiket, alt="", renk="#58a6ff"):
    return (f'<div class="stat-kart" style="border-radius:14px;">'
            f'<div class="sayi" style="color:{renk}">{deger}</div>'
            f'<div class="etiket">{etiket}</div>'
            + (f'<div style="font-size:10px;color:#6e7681;margin-top:3px;">{alt}</div>' if alt else "")
            + '</div>')


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
            f"<div style='font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#00c853;"
            f"font-weight:700;margin:10px 0 10px;'>📊 {t('Kısa Sayısal Özet','Quick Summary')}</div>",
            unsafe_allow_html=True)
        satir1 = [
            (o["oyuncu"], t("Toplam Oyuncu","Total Players"),
             f"{o['yerli']} {t('yerli','dom.')} · {o['yabanci']} {t('yabancı','for.')}", "#00c853"),
            (o["takim"], t("Toplam Takım","Total Teams"), t("Süper Lig","Super League"), "#58a6ff"),
            (o["scouting"], t("Scouting Raporu","Scouting Reports"), t("uluslararası havuz","intl. pool"), "#f0c040"),
            (o["mac"], t("Toplam Maç","Total Matches"), t("sezon geneli","full season"), "#58a6ff"),
        ]
        satir2 = [
            (o["gol"], t("Toplam Gol","Total Goals"), t("tüm lig","whole league"), "#e040fb"),
            (o["yerli"], t("Yerli Oyuncu","Domestic Players"),
             (f"%{round(o['yerli']/o['oyuncu']*100)} " + t("yerli oran","domestic")) if o["oyuncu"] else "", "#00c853"),
            (o["ort_yas"], t("Ortalama Yaş","Average Age"), t("lig geneli","league-wide"), "#58a6ff"),
            (o["u23"], t("U-23 Yetenek","U-23 Talents"), t("geleceğin yıldızları","future stars"), "#f0c040"),
        ]
        for satir in (satir1, satir2):
            cols = st.columns(4)
            for kol, (d, e, a, r) in zip(cols, satir):
                kol.markdown(_ozet_kart(d, e, a, r), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        f"<div style='font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#00c853;"
        f"font-weight:700;margin:6px 0 4px;'>ℹ️ {t('Hakkında','About')}</div>",
        unsafe_allow_html=True)
    render_hakkinda_icerik()


# ─── KARŞILAMA EKRANI (ana içeriğe geçmeden önce — herkese açık) ───────────────
if not st.session_state.get("girildi", False):
    _kc = st.columns([1, 2, 1])[1]
    with _kc:
        if st.button(t("🚀 Ana Sayfaya Geç", "🚀 Enter the App"),
                     type="primary", use_container_width=True, key="karsilama_gec_ust"):
            st.session_state["girildi"] = True
            st.rerun()
    render_giris_ekrani()
    st.markdown("<br>", unsafe_allow_html=True)
    _kc2 = st.columns([1, 2, 1])[1]
    with _kc2:
        if st.button(t("🚀 Ana Sayfaya Geç", "🚀 Enter the App"),
                     type="primary", use_container_width=True, key="karsilama_gec_alt"):
            st.session_state["girildi"] = True
            st.rerun()
    st.stop()


# ─── DANIŞMANLIK BANNER ÖNCESİ BOŞLUK ──────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

# ─── DANIŞMANLIK TALEP BANNER (ana sayfada görünür) ───────────────────────────
_bc1, _bc2 = st.columns([3, 1])
with _bc1:
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#0f3d2e,#1a5c43);border-radius:12px;
        padding:13px 20px;border-left:4px solid #00c853;'>
      <div style='color:#fff;font-size:1.05rem;font-weight:700;'>{t("📩 Kadronu birlikte kuralım", "📩 Let's build your squad together")}</div>
      <div style='color:#a7f3d0;font-size:0.85rem;margin-top:2px;'>
      {t("Oyuncu raporu · mevki önerisi · oyuncu kıyası · tam kadro danışmanlığı — talebini ilet.",
         "Player report · position suggestion · player comparison · full squad consultancy — send your request.")}</div>
    </div>""", unsafe_allow_html=True)
with _bc2:
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if st.button(t("📩 Talep / Danışmanlık", "📩 Request / Consult"), use_container_width=True, type="primary"):
        st.session_state["sayfa"] = "talep"
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ─── SEKMELER ─────────────────────────────────────────────────────────────────
_giris_var = st.session_state.get("kulup_giris", False)
_sekmeler = []
if _giris_var:
    _sekmeler.append(t("🏟️ Benim Kadrom", "🏟️ My Squad"))
_sekmeler += [
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
_is_admin = st.session_state.get("kulup_kullanici") == "admin"

_tabs = st.tabs(_sekmeler)
_ti = 0

if _giris_var:
    tab_benim = _tabs[_ti]; _ti += 1
else:
    tab_benim = None

tab1       = _tabs[_ti]; _ti += 1
tab_transfer = _tabs[_ti]; _ti += 1
tab_genç   = _tabs[_ti]; _ti += 1
tab2       = _tabs[_ti]; _ti += 1
tab3       = _tabs[_ti]; _ti += 1
tab4       = _tabs[_ti]; _ti += 1
tab5       = _tabs[_ti]; _ti += 1
tab6       = _tabs[_ti]; _ti += 1
tab7       = _tabs[_ti]; _ti += 1
tab9       = _tabs[_ti]; _ti += 1
tab10      = _tabs[_ti]; _ti += 1
tab11      = _tabs[_ti]; _ti += 1

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 1 — OYUNCU LİSTESİ
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
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
        secili_takim = st.selectbox(t("Takım", "Team"), takimlar)
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
        lambda r: r["TümTakımlar"] if r["Transfer"] else r["Takım"], axis=1)

    bas, ind = st.columns([3,1])
    with bas: st.markdown(f"#### {len(df)} {t('oyuncu', 'players')}")
    with ind:
        csv_b = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ CSV", csv_b, "oyuncular.csv", use_container_width=True)

    max_gol = int(df_tam["Gol"].max() or 1)
    max_mac = int(df_tam["Maç"].max() or 1)
    max_dk  = int(df_tam["Dakika"].max() or 1)

    tablo_df = df[["Oyuncu","Takım (Gösterim)","Maç","İlk11","Yedek",
                   "Gol","GolF","GolH","GolP","Gol/Maç","Sarı","Kırmızı","Dakika"]].reset_index(drop=True)

    secim = st.dataframe(
        tablo_df,
        use_container_width=True, height=520,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Oyuncu":           st.column_config.TextColumn(t("Oyuncu","Player"),       width="medium"),
            "Takım (Gösterim)": st.column_config.TextColumn(t("Takım","Team"),          width="medium"),
            "Maç":     st.column_config.NumberColumn(t("Maç","Matches"), format="%d"),
            "İlk11":   st.column_config.NumberColumn("▶11",   format="%d",  help=t("İlk 11'de başladığı maç sayısı","Started in first 11")),
            "Yedek":   st.column_config.NumberColumn("↗Yed",  format="%d",  help=t("Yedek olarak girdiği maç sayısı","Came on as substitute")),
            "Gol":     st.column_config.ProgressColumn(t("Gol","Goals"), min_value=0, max_value=max_gol, format="%d"),
            "GolF":    st.column_config.NumberColumn("⚽F",   format="%d",  help=t("Ayakla gol (F)","Foot goal (F)")),
            "GolH":    st.column_config.NumberColumn("⚽H",   format="%d",  help=t("Kafa golü (H)","Header goal (H)")),
            "GolP":    st.column_config.NumberColumn("⚽P",   format="%d",  help=t("Penaltı golü (P)","Penalty goal (P)")),
            "Gol/Maç": st.column_config.NumberColumn("G/M",  format="%.2f", help=t("Maç başına gol ortalaması","Goals per match average")),
            "Sarı":    st.column_config.NumberColumn("🟨",    format="%d"),
            "Kırmızı": st.column_config.NumberColumn("🟥",   format="%d"),
            "Dakika":  st.column_config.ProgressColumn(t("Dakika","Minutes"), min_value=0, max_value=max_dk, format="%d"),
        }
    )

    # Satıra tıklanınca mini profil kartı göster
    secili_satirlar = secim.selection.rows if secim and secim.selection else []
    if secili_satirlar:
        tikli_oyuncu = tablo_df.iloc[secili_satirlar[0]]["Oyuncu"]
        st.session_state["profil_sec"] = tikli_oyuncu
        st.markdown("---")

        p_row = df_tam[df_tam["Oyuncu"] == tikli_oyuncu]
        if not p_row.empty:
            p   = p_row.iloc[0]
            sd  = sd_profiller.get(tikli_oyuncu, {})
            MEVKİ_İKON = {"Goalkeeper":"🧤","Defender":"🛡️","Midfield":"⚙️",
                          "Striker":"⚽","Forward":"⚽","Back":"🛡️"}
            sd_mevki   = sd.get("Position","")
            mevki_ikon = next((v for k,v in MEVKİ_İKON.items() if k in sd_mevki),"")
            transfer   = bool(p.get("Transfer", False))
            takim_txt  = p["TümTakımlar"] if transfer else p["Takım"]

            # SD bilgi chip'leri — ayrı ayrı oluştur
            CHIP_STILI = ("background:#0f1117;border:1px solid #2d3561;border-radius:6px;"
                          "padding:3px 10px;font-size:0.78rem;color:#c0ccd8;margin-right:6px")
            chip_parcalar = []
            if sd.get("Date of birth"): chip_parcalar.append(f'<span style="{CHIP_STILI}">🎂 {sd["Date of birth"]}</span>')
            if sd.get("Nationality"):   chip_parcalar.append(f'<span style="{CHIP_STILI}">🏳️ {sd["Nationality"]}</span>')
            if sd.get("Height"):        chip_parcalar.append(f'<span style="{CHIP_STILI}">📏 {sd["Height"]} m</span>')
            if sd.get("Foot"):          chip_parcalar.append(f'<span style="{CHIP_STILI}">👟 {sd["Foot"].capitalize()}</span>')
            if sd.get("Market value","") not in ("","unknown","?"):
                chip_parcalar.append(f'<span style="{CHIP_STILI}">💰 {sd["Market value"]}</span>')
            chip_html = " ".join(chip_parcalar)

            # Stat kutuları
            STAT_STILI = ("background:#0f1117;border-radius:8px;padding:8px 16px;"
                          "text-align:center;min-width:60px")
            stat_html = ""
            for sutun, etiket in [("Gol",t("GOL","GOALS")),("Maç",t("MAÇ","MATCHES")),("Dakika",t("DK","MIN"))]:
                if sutun in p:
                    deger = int(p[sutun])
                    stat_html += (f'<div style="{STAT_STILI}">'
                                  f'<div style="font-size:1.4rem;font-weight:700;color:#00c853">{deger}</div>'
                                  f'<div style="font-size:0.62rem;color:#8899aa">{etiket}</div></div>')

            # Mevki ve transfer chip
            mevki_html = ""
            if sd_mevki:
                mevki_html = (f'<span style="color:#00c853;font-weight:600">'
                              f'{mevki_ikon} {sd_mevki}</span>  · ')
            transfer_html = ""
            if transfer:
                transfer_html = (' <span style="background:#1a3a2a;color:#00c853;border-radius:4px;'
                                 'padding:1px 6px;font-size:0.7rem">🔄 Transfer</span>')

            kart = (
                '<div style="background:#1a1f36;border-radius:12px;padding:18px 22px;'
                'border-left:4px solid #00c853;display:flex;'
                'justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px">'
                '<div>'
                f'<div style="font-size:1.15rem;font-weight:700;color:#fff;margin-bottom:4px">{tikli_oyuncu}</div>'
                f'<div style="color:#8899aa;font-size:0.82rem;margin-bottom:10px">'
                f'{mevki_html}🏟 {takim_txt}{transfer_html}</div>'
                f'<div>{chip_html}</div>'
                '</div>'
                f'<div style="display:flex;gap:10px;flex-wrap:wrap">{stat_html}</div>'
                '</div>'
            )
            st.markdown(kart, unsafe_allow_html=True)
            if st.button(t("👤 Tam Profili Aç", "👤 Full Profile"), key="ana_lig_profil_ac", use_container_width=True):
                st.query_params["oyuncu"] = tikli_oyuncu
                st.rerun()
    st.caption(t("⚽F = Ayak golü · ⚽H = Kafa golü · ⚽P = Penaltı · ▶11 = İlk 11 · ↗Yed = Yedek giriş",
                 "⚽F = Foot goal · ⚽H = Header goal · ⚽P = Penalty · ▶11 = Started · ↗Yed = Substitute"))

# ==============================================================================
# SEKME 2 - OYUNCU PROFILI
# ==============================================================================
with tab2:
    if not st.session_state.get("kulup_giris"):
        giris_gerekli_ekrani()
    else:
        oyuncu_listesi = sorted(df_tam["Oyuncu"].tolist())
        varsayilan_idx = oyuncu_listesi.index(url_oyuncu) if url_oyuncu in oyuncu_listesi else 0
        secili = st.selectbox(t("Oyuncu seç", "Select Player"), oyuncu_listesi, index=varsayilan_idx, key="profil_sec")
        render_ana_lig_profil(secili)

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 3 — KARŞILAŞTIRMA (2-4 oyuncu)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f"### ⚡ {t('Oyuncu Karşılaştırması', 'Player Comparison')}")
    st.caption(t("2 ile 4 oyuncu arasında seçim yapabilirsiniz.", "You can select between 2 and 4 players."))

    oyuncu_listesi2 = sorted(df_tam["Oyuncu"].tolist())

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

    RENKLER = ["#00c853", "#2979ff", "#ff6d00", "#e040fb"]

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
        st.plotly_chart(fig, use_container_width=True)
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
            use_container_width=True,
            height=430,
            column_config={
                col: st.column_config.TextColumn(col, width="medium")
                for col in df_karsilastirma.columns
            },
        )

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 4 — TAKIMLAR
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown(f"### 🏟️ {t('Takım Analizi', 'Team Analysis')}")

    if not df_tam.empty:
        takim_listesi_tam = sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_t = st.selectbox(t("Takım seç", "Select Team"), takim_listesi_tam, key="takim_sayfasi")
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
            st.dataframe(kadro, use_container_width=True, height=400,
                column_config={
                    "Oyuncu": st.column_config.TextColumn(t("Oyuncu","Player"), width="medium"),
                    "Mevki":  st.column_config.TextColumn(t("Mevki","Position"),  width="small"),
                    "Maç":    st.column_config.NumberColumn(t("Maç","Matches"),   format="%d"),
                    "Gol":    st.column_config.NumberColumn(t("Gol","Goals"),   format="%d"),
                    "Dakika": st.column_config.NumberColumn(t("Dk","Min"),    format="%d"),
                    "Sarı":   st.column_config.NumberColumn("🟨",    format="%d"),
                })

        # ── Mevki dağılımı + uyruk ─────────────────────────────────────
        with sag:
            st.markdown(f"##### 📊 {t('Mevki Dağılımı', 'Position Distribution')}")
            if "Mevki" in df_t.columns:
                mevki_sayilari = df_t["Mevki"].value_counts()
                MEVKI_RENK = {"Kaleci":"#00c853","Defans":"#2979ff",
                              "Orta Saha":"#ff6d00","Forvet":"#e040fb","Bilinmiyor":"#555"}
                fig_mevki = go.Figure(go.Pie(
                    labels=[mevki_goster(m) for m in mevki_sayilari.index],
                    values=mevki_sayilari.values,
                    marker_colors=[MEVKI_RENK.get(m,"#555") for m in mevki_sayilari.index],
                    textinfo="label+value",
                    hole=0.4,
                ))
                fig_mevki.update_layout(
                    paper_bgcolor="#0f1117", font=dict(color="#e0e0e0"),
                    height=200, margin=dict(l=0,r=0,t=10,b=0),
                    showlegend=False)
                st.plotly_chart(fig_mevki, use_container_width=True)

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
                st.plotly_chart(fig_uyruk, use_container_width=True)

        # ── Scatter: verimlilik ────────────────────────────────────────
        st.markdown("---")
        st.markdown(f"##### ⚡ {t('Dakika-Gol Verimliliği', 'Minutes-Goals Efficiency')}")
        fig_s = go.Figure()
        for mevki, renk in [("Kaleci","#00c853"),("Defans","#2979ff"),
                              ("Orta Saha","#ff6d00"),("Forvet","#e040fb"),("Bilinmiyor","#555")]:
            alt = df_t[df_t.get("Mevki","") == mevki] if "Mevki" in df_t.columns else df_t
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
        st.plotly_chart(fig_s, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 5 — LİG TABLOSU
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
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
        takim_ozet.index = range(1, len(takim_ozet)+1)

        st.markdown(f"#### {t('Takım Bazlı Sezon İstatistikleri', 'Season Stats by Team')}")
        st.dataframe(takim_ozet, use_container_width=True, height=520,
            column_config={
                "Takım":          st.column_config.TextColumn(t("Takım","Team"), width="large"),
                "Oyuncu Sayısı":  st.column_config.NumberColumn(t("Kadro","Squad")),
                "Toplam Gol":     st.column_config.ProgressColumn(t("Toplam Gol","Total Goals"),
                    min_value=0, max_value=int(takim_ozet["Toplam Gol"].max()), format="%d"),
                "Toplam Dakika":  st.column_config.NumberColumn(t("Toplam Dk","Total Min")),
                "Sarı Kart":      st.column_config.NumberColumn("🟨"),
                "Kırmızı Kart":   st.column_config.NumberColumn("🟥"),
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # TFF'den resmi puan cetveli
        st.markdown(f"#### 🏆 {t('TFF Resmi Puan Cetveli', 'TFF Official Standings')}")
        with st.spinner(t("TFF'den yükleniyor...", "Loading from TFF...")):
            df_puan = puan_durumu_cek()

        if not df_puan.empty:
            # Sütun adlarını düzelt — O G B M A Y AV P
            sutun_aciklama = {
                "O": t("O — Oynadı","P — Played"), "G": t("G — Galibiyet","W — Won"), "B": t("B — Beraberlik","D — Draw"),
                "M": t("M — Mağlubiyet","L — Lost"), "A": t("A — Atılan","GF — Goals For"), "Y": t("Y — Yenilen","GA — Goals Ag."),
                "AV": t("AV — Averaj","GD — Goal Diff"), "P": t("P — Puan","Pts — Points"),
            }
            df_puan.index = range(1, len(df_puan) + 1)
            st.dataframe(
                df_puan,
                use_container_width=True,
                height=600,
                column_config={
                    col: st.column_config.TextColumn(sutun_aciklama.get(col, col))
                    for col in df_puan.columns
                },
            )
            st.caption(t("Kaynak: TFF — tff.org | O=Oynadı · G=Galibiyet · B=Beraberlik · M=Mağlubiyet · A=Atılan · Y=Yenilen · AV=Averaj · P=Puan",
                         "Source: TFF — tff.org | P=Played · W=Won · D=Draw · L=Lost · GF=Goals For · GA=Goals Ag. · GD=Goal Diff · Pts=Points"))
        else:
            st.caption(t("TFF puan cetveli yüklenemedi.", "Could not load TFF standings."))

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 6 — EN İYİLER
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown(f"### 🌟 {t('2025-2026 Sezonu En İyileri', '2025-2026 Season Top Performers')}")
    if df_tam.empty:
        st.info(t("Veri yok.", "No data."))
    else:
        # ── Lig Geneli Verimlilik Scatter ──────────────────────────────
        st.markdown(f"#### ⚡ {t('Tüm Ligde Dakika-Gol Verimliliği', 'Minutes-Goals Efficiency Across the League')}")
        st.caption(t("Sağ üst = hem çok oynadı hem çok gol attı. Her renk bir mevki.",
                     "Top right = played a lot and scored a lot. Each color represents a position."))
        fig_lig = go.Figure()
        MEVKI_RENK = {"Kaleci":"#00c853","Defans":"#2979ff",
                      "Orta Saha":"#ff6d00","Forvet":"#e040fb","Bilinmiyor":"#555555"}
        for mevki, renk in MEVKI_RENK.items():
            alt = df_tam[df_tam.get("Mevki", pd.Series(dtype=str)) == mevki] if "Mevki" in df_tam.columns else pd.DataFrame()
            if "Mevki" in df_tam.columns:
                alt = df_tam[df_tam["Mevki"] == mevki]
            else:
                alt = pd.DataFrame()
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
        st.plotly_chart(fig_lig, use_container_width=True)

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
                st.plotly_chart(fig_u, use_container_width=True)
            with ub:
                st.markdown(f"**{t('Gol sayısına göre', 'By number of goals')}**")
                uyruk_gol = df_tam[df_tam["Uyruk"]!=""].groupby("Uyruk")["Gol"].sum().sort_values(ascending=False).head(15)
                fig_ug = go.Figure(go.Bar(
                    x=uyruk_gol.values, y=uyruk_gol.index,
                    orientation="h", marker_color="#00c853",
                    text=uyruk_gol.values, textposition="outside",
                ))
                fig_ug.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                    font=dict(color="#e0e0e0"), height=400,
                    xaxis=dict(gridcolor="#2d3561"), yaxis=dict(gridcolor="#2d3561"),
                    margin=dict(l=10,r=40,t=10,b=10))
                st.plotly_chart(fig_ug, use_container_width=True)

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
                    f'<span style="color:#8899aa;font-size:0.78rem;margin-left:8px">{row["Takım"][:25]}</span></span>'
                    f'<span style="color:#00c853;font-weight:600">{degerler}</span></div>',
                    unsafe_allow_html=True
                )

        # ── Satır 1 ──────────────────────────────────────────────────────────
        r1c1, r1c2, r1c3 = st.columns(3)

        with r1c1:
            en_iyi_kart(t("Gol Kraliçesi","Top Scorer"),
                df_tam.nlargest(5,"Gol")[["Oyuncu","Takım","Gol","GolF","GolH","GolP"]],
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
                        "Takım":  o["takim"],
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
                        "Takım":  o["takim"],
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
        cols = st.columns(min(4, len(takimlar_s)))
        for idx, takim in enumerate(takimlar_s):
            with cols[idx % 4]:
                df_t = df_tam[df_tam["Takım"]==takim].nlargest(1,"Gol")
                if not df_t.empty:
                    r = df_t.iloc[0]
                    st.markdown(
                        f'<div style="background:#1a1f36;border-radius:8px;padding:10px;'
                        f'margin-bottom:8px;border-top:2px solid #00c853">'
                        f'<div style="color:#8899aa;font-size:0.68rem">{takim[:30]}</div>'
                        f'<div style="font-weight:600;font-size:0.9rem;margin:3px 0">{r["Oyuncu"]}</div>'
                        f'<div style="color:#00c853;font-size:0.82rem">⚽ {int(r["Gol"])} {t("gol","goals")}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 7 — FANTASY KADRO
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
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
                    st.markdown(f"**{GRUP_IKON.get(mevki,'')} {mevki}**")
                    onceki_grp = mevki
                havuz = (df_tam[df_tam["Mevki"] == mevki]["Oyuncu"].tolist()
                         if "Mevki" in df_tam.columns else df_tam["Oyuncu"].tolist())
                secenekler = ["—"] + [o for o in sorted(havuz) if o not in zaten_sec]
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
            st.plotly_chart(fig, use_container_width=True)

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
            goster["_s"] = goster["Mevki"].map({"Kaleci":0,"Defans":1,"Orta Saha":2,"Forvet":3,"Bilinmiyor":4})
            goster = goster.sort_values("_s").drop(columns="_s").reset_index(drop=True)
            goster.index += 1
            st.dataframe(goster, use_container_width=True,
                column_config={
                    "Oyuncu": st.column_config.TextColumn(t("Oyuncu","Player"), width="medium"),
                    "Takım":  st.column_config.TextColumn(t("Takım","Team"),  width="medium"),
                    "Gol":    st.column_config.ProgressColumn(t("Gol","Goals"),
                        min_value=0, max_value=int(df_tam["Gol"].max()), format="%d"),
                    "Gol/Maç": st.column_config.NumberColumn("G/M", format="%.2f"),
                })
        else:
            st.info(t("Soldan oyuncu seçmeye başla — saha canlı güncellenecek.",
                      "Start picking players on the left — the pitch updates live."))


# ══════════════════════════════════════════════════════════════════════════════
# SEKME — BENİM KADROM (sadece giriş yapanlara)
# ══════════════════════════════════════════════════════════════════════════════
if tab_benim:
    with tab_benim:
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
                    marker=dict(color="#00c853"),
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
                st.plotly_chart(fig_admin, use_container_width=True)

        else:
            # ── KULÜP GÖRÜNÜMÜ ────────────────────────────────────────
            st.markdown(f"##### 🏟️ {kulup_ad} — {t('Kadro Paneli', 'Squad Panel')}")
            st.caption(f"2025-26 {t('sezonu','season')} · {kulup_takim}")

            kadro = df_tam[df_tam["Takım"].str.contains(
                kulup_takim.split()[0], case=False, na=False
            )].copy() if not df_tam.empty else pd.DataFrame()

            if kadro.empty:
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
                    st.dataframe(goster, use_container_width=True, height=460,
                        column_config={
                            "Oyuncu": st.column_config.TextColumn(t("Oyuncu","Player")),
                            "Mevki":  st.column_config.TextColumn(t("Mevki","Position")),
                            "Maç":    st.column_config.NumberColumn(t("Maç","Matches")),
                            "İlk11":  st.column_config.NumberColumn(t("İlk11","Started")),
                            "Gol": st.column_config.ProgressColumn(
                                t("Gol","Goals"), min_value=0, max_value=int(kadro["Gol"].max()+1), format="%d"),
                            "Gol/Maç": st.column_config.NumberColumn(format="%.2f"),
                            "Dakika": st.column_config.NumberColumn(t("Dakika","Minutes")),
                            "Sarı":   st.column_config.NumberColumn("🟨"),
                            "Kırmızı": st.column_config.NumberColumn("🟥"),
                        })

                with col_g:
                    st.markdown(f"**📊 {t('Mevki Dağılımı', 'Position Distribution')}**")
                    mev_dag = kadro["Mevki"].value_counts().reset_index()
                    mev_dag.columns = ["Mevki","Sayı"]
                    renk_map = {"Kaleci":"#2979ff","Defans":"#00c853",
                                "Orta Saha":"#ffab00","Forvet":"#ff6b6b","Bilinmiyor":"#8899aa"}
                    fig_pie = go.Figure(go.Pie(
                        labels=[mevki_goster(m) for m in mev_dag["Mevki"]], values=mev_dag["Sayı"],
                        marker_colors=[renk_map.get(m,"#8899aa") for m in mev_dag["Mevki"]],
                        hole=0.45, textinfo="label+value",
                        textfont=dict(color="#fff", size=12),
                    ))
                    fig_pie.update_layout(
                        paper_bgcolor="#0f1117", font=dict(color="#e0e0e0"),
                        margin=dict(l=10,r=10,t=10,b=10), height=220,
                        showlegend=False,
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                    st.markdown(f"**🌍 {t('Uyruk Dağılımı', 'Nationality Distribution')}**")
                    uyr_dag = kadro["Uyruk"].value_counts().head(8).reset_index()
                    uyr_dag.columns = ["Uyruk","Sayı"]
                    fig_uyr = go.Figure(go.Bar(
                        x=uyr_dag["Sayı"], y=uyr_dag["Uyruk"], orientation="h",
                        marker=dict(color="#00c853"),
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
                    st.plotly_chart(fig_uyr, use_container_width=True)

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
with tab_genç:
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
                "Oyuncu": isim, "Takım": o["takim"], "Yaş": yas,
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
            f"<div style='color:#00c853;font-size:13px;font-weight:700;margin:8px 0 16px;'>"
            f"🎯 {len(filtered)} {t('genç oyuncu','young players')}</div>", unsafe_allow_html=True)

        # ── En İlginç 5 ───────────────────────────────────────────────
        if len(filtered) >= 3:
            st.markdown(f"**⭐ {t('Öne Çıkan İsimler', 'Featured Names')}**")
            top5 = filtered.head(5)
            cols = st.columns(min(5, len(top5)))
            for idx, (_, r) in enumerate(top5.iterrows()):
                with cols[idx]:
                    st.markdown(
                        f"<div style='background:#1a1f36;border-radius:10px;padding:12px;"
                        f"text-align:center;border-top:3px solid #00c853;'>"
                        f"<div style='font-size:11px;font-weight:700;color:#fff;"
                        f"margin-bottom:4px;'>{r['Oyuncu'].split()[0]}<br>"
                        f"<span style='font-size:10px;'>{r['Oyuncu'].split()[-1]}</span></div>"
                        f"<div style='font-size:20px;font-weight:800;color:#00c853;'>{r['Yaş']:.0f}</div>"
                        f"<div style='font-size:9px;color:#8899aa;'>{mevki_goster(r['Mevki'])}</div>"
                        f"<div style='font-size:16px;font-weight:700;color:#fff;margin-top:6px;'>{r['Gol']}</div>"
                        f"<div style='font-size:9px;color:#8899aa;'>{t('gol','goals')} · {r['Maç']} {t('maç','matches')}</div>"
                        f"</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Scatter: Yaş vs Gol/Maç ───────────────────────────────────
        col_scatter, col_tablo = st.columns([3, 2], gap="large")

        with col_scatter:
            st.markdown(f"**📊 {t('Yaş — Gol/Maç Dağılımı', 'Age — Goals/Match Distribution')}**")
            renk_map = {"Kaleci":"#2979ff","Defans":"#00c853",
                        "Orta Saha":"#ffab00","Forvet":"#ff6b6b","Bilinmiyor":"#8899aa"}
            fig_sc = go.Figure()
            for mev, grp in filtered.groupby("Mevki"):
                fig_sc.add_trace(go.Scatter(
                    x=grp["Yaş"], y=grp["G/Maç"],
                    mode="markers+text",
                    name=mevki_goster(mev),
                    marker=dict(size=grp["Maç"].clip(8,30)/1.5,
                                color=renk_map.get(mev,"#8899aa"),
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
                xaxis=dict(title="Yaş", color="#8899aa", gridcolor="#1e2340",
                           range=[14.5, 23.5]),
                yaxis=dict(title="Gol/Maç", color="#8899aa", gridcolor="#1e2340"),
                legend=dict(bgcolor="#1a1f36", bordercolor="#30363d",
                            font=dict(color="#e0e0e0")),
                margin=dict(l=10, r=10, t=10, b=10),
                height=420, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_sc, use_container_width=True)
            st.caption(t("💡 Nokta büyüklüğü = oynanan maç sayısı", "💡 Dot size = number of matches played"))

        with col_tablo:
            st.markdown(f"**📋 {t('Tam Liste', 'Full List')}**")
            goster = filtered[["Oyuncu","Yaş","Mevki","Takım","Maç","Gol","G/Maç","Skor"]].copy()
            if EN:
                goster["Mevki"] = goster["Mevki"].map(mevki_goster)
            goster.index = range(1, len(goster)+1)
            st.dataframe(
                goster, use_container_width=True, height=420,
                column_config={
                    "Oyuncu": st.column_config.TextColumn(t("Oyuncu","Player")),
                    "Yaş":   st.column_config.NumberColumn(t("Yaş","Age"), format="%.0f"),
                    "Mevki": st.column_config.TextColumn(t("Mevki","Position")),
                    "Takım": st.column_config.TextColumn(t("Takım","Team")),
                    "Maç":   st.column_config.NumberColumn(t("Maç","Matches")),
                    "Gol":   st.column_config.NumberColumn(t("Gol","Goals")),
                    "G/Maç": st.column_config.NumberColumn(format="%.2f"),
                    "Skor":  st.column_config.ProgressColumn(
                        t("Skor","Score"), min_value=0, max_value=250, format="%.0f"),
                },
            )


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 9 — GELİŞMİŞ OYUNCU ARAMA
# ══════════════════════════════════════════════════════════════════════════════
with tab9:
    if not st.session_state.get("kulup_giris"):
        giris_gerekli_ekrani()
    elif not pro_kontrol():
        pro_paywall_goster(t("🔍 Gelişmiş Arama", "🔍 Advanced Search"))
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
                f"<div style='color:#00c853;font-size:13px;font-weight:700;margin:8px 0;'>"
                f"🎯 {len(filtered)} {t('oyuncu bulundu','players found')}</div>", unsafe_allow_html=True)

            if filtered.empty:
                st.info(t("Filtrelerle eşleşen oyuncu yok.", "No players match the filters."))
            else:
                show = ["Oyuncu", "Takım", "Mevki", "Uyruk", "Yaş", "Maç", "İlk11", "Gol", "Dakika", "Sarı"]
                show = [c for c in show if c in filtered.columns]
                _goster_df = filtered[show].copy()
                if EN and "Mevki" in _goster_df.columns:
                    _goster_df["Mevki"] = _goster_df["Mevki"].map(mevki_goster)
                st.dataframe(_goster_df, hide_index=True, use_container_width=True,
                    height=min(600, 45 + len(filtered) * 35),
                    column_config={
                        "Oyuncu": st.column_config.TextColumn(t("Oyuncu","Player")),
                        "Takım":  st.column_config.TextColumn(t("Takım","Team")),
                        "Mevki":  st.column_config.TextColumn(t("Mevki","Position")),
                        "Uyruk":  st.column_config.TextColumn(t("Uyruk","Nationality")),
                        "Yaş":    st.column_config.NumberColumn(t("Yaş","Age"), format="%.0f"),
                        "Maç":    st.column_config.NumberColumn(t("Maç","Matches")),
                        "İlk11":  st.column_config.NumberColumn(t("İlk11","Started")),
                        "Gol":    st.column_config.NumberColumn(t("Gol","Goals")),
                        "Dakika": st.column_config.NumberColumn(t("Dakika","Minutes")),
                        "Sarı":   st.column_config.NumberColumn("🟨"),
                    })


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

with tab10:
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
                marker=dict(color="#00a86b", line=dict(color="#00c853", width=0.8)),
                opacity=0.85,
                hovertemplate="Yaş: %{x:.0f}<br>Oyuncu: %{y}<extra></extra>",
            ))
            fig_hist.add_vline(x=avg_age, line_dash="dash", line_color="#ffab00",
                annotation_text=f"Ort: {avg_age:.1f}",
                annotation_position="top right",
                annotation_font=dict(color="#ffab00", size=11))
            fig_hist.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title="Yaş", color="#8899aa", gridcolor="#1e2340"),
                yaxis=dict(title="Oyuncu Sayısı", color="#8899aa", gridcolor="#1e2340"),
                bargap=0.08, margin=dict(l=10,r=10,t=10,b=10),
                height=320, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_hist, use_container_width=True)

            st.markdown(f"**📅 {t('Doğum Yılı Dağılımı', 'Birth Year Distribution')}**")
            by_year = (yas_df.dropna(subset=["dogum_yili"])
                       .groupby("dogum_yili").size()
                       .reset_index(name="sayi").sort_values("dogum_yili"))
            fig_year = go.Figure(go.Bar(
                x=by_year["dogum_yili"], y=by_year["sayi"],
                marker=dict(color=by_year["sayi"],
                            colorscale=[[0,"#0d3b2e"],[1,"#00c853"]], showscale=False),
                hovertemplate="%{x}: %{y} oyuncu<extra></extra>",
            ))
            fig_year.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title="Doğum Yılı", color="#8899aa", gridcolor="#1e2340", dtick=2),
                yaxis=dict(title="Oyuncu", color="#8899aa", gridcolor="#1e2340"),
                bargap=0.1, margin=dict(l=10,r=10,t=10,b=10),
                height=260, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_year, use_container_width=True)

        with col_takim:
            st.markdown(f"**🏟 {t('Takım Yaş Ortalamaları', 'Team Age Averages')}**")
            takim_yas = (yas_df[yas_df["takim"] != "Bilinmiyor"]
                         .groupby("takim")["yas"]
                         .agg(["mean","min","max","count"]).round(1)
                         .reset_index()
                         .rename(columns={"takim":"Takım","mean":"Ort","min":"Min","max":"Max","count":"Oyuncu"})
                         .sort_values("Ort"))
            st.dataframe(takim_yas, hide_index=True, use_container_width=True, height=400,
                column_config={
                    "Takım":  st.column_config.TextColumn(t("Takım","Team")),
                    "Ort": st.column_config.NumberColumn(t("Ort","Avg"), format="%.1f"),
                    "Min": st.column_config.NumberColumn(format="%.0f"),
                    "Max": st.column_config.NumberColumn(format="%.0f"),
                    "Oyuncu": st.column_config.NumberColumn(t("Oyuncu","Players")),
                })
            if not takim_yas.empty:
                g = takim_yas.iloc[0]; y = takim_yas.iloc[-1]
                st.markdown(
                    f"<div style='font-size:12px;color:#8899aa;margin-top:8px;'>"
                    f"🟢 {t('En genç','Youngest')}: <b style='color:#00c853'>{g['Takım']}</b> ({g['Ort']} {t('yaş','yrs')})<br>"
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
                marker=dict(color="#00a86b"),
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
            st.plotly_chart(fig_pos, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 11 — KALECİLER
# ══════════════════════════════════════════════════════════════════════════════
with tab11:
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
            for kol, sayi, etiket in [
                (k1, len(aktif), t("Aktif Kaleci","Active GKs")),
                (k2, int(kal_df["YenilenGol"].sum()), t("Toplam Gol","Total Goals")),
                (k3, f"{en_iyi['G/Maç']} — {en_iyi['Kaleci'].split()[0]}", t("En Az Yiyen","Fewest Conceded")),
                (k4, f"{en_kotu['G/Maç']} — {en_kotu['Kaleci'].split()[0]}", t("En Çok Yiyen","Most Conceded")),
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
            st.dataframe(
                goster,
                use_container_width=True,
                height=520,
                column_config={
                    "Kaleci": st.column_config.TextColumn(t("Kaleci","Goalkeeper")),
                    "Takım":  st.column_config.TextColumn(t("Takım","Team")),
                    "Maç":    st.column_config.NumberColumn(t("Maç","Matches")),
                    "G/Maç": st.column_config.NumberColumn(format="%.2f"),
                    "YenilenGol": st.column_config.NumberColumn(t("Y.Gol","GA")),
                },
            )

        with col_grafik:
            st.markdown(f"**📊 {t('Maç Başına Yenilen Gol (≥5 maç)', 'Goals Conceded per Match (≥5 matches)')}**")
            plot_df = aktif.sort_values("G/Maç")
            renkler = ["#00c853" if g <= 1.0 else "#ffab00" if g <= 2.0 else "#ff6b6b"
                       for g in plot_df["G/Maç"]]
            fig = go.Figure(go.Bar(
                x=plot_df["G/Maç"],
                y=plot_df["Kaleci"],
                orientation="h",
                marker=dict(color=renkler),
                text=[f"{g:.2f}" for g in plot_df["G/Maç"]],
                textposition="outside",
                textfont=dict(color="#e0e0e0", size=11),
                hovertemplate="%{y}<br>%{x:.2f} G/Maç<extra></extra>",
            ))
            fig.add_vline(x=1.0, line_dash="dash", line_color="#00c853",
                          annotation_text="1.0", annotation_font=dict(color="#00c853", size=10))
            fig.add_vline(x=2.0, line_dash="dash", line_color="#ffab00",
                          annotation_text="2.0", annotation_font=dict(color="#ffab00", size=10))
            fig.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(title="Maç Başına Yenilen Gol", color="#8899aa",
                           gridcolor="#1e2340", range=[0, max(plot_df["G/Maç"]) * 1.15]),
                yaxis=dict(color="#e0e0e0"),
                margin=dict(l=10, r=60, t=10, b=10),
                height=500, font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Renk açıklaması
            st.markdown(
                "<div style='font-size:11px;color:#8899aa;'>"
                "🟢 ≤1.0 &nbsp; 🟡 1.0–2.0 &nbsp; 🔴 >2.0 &nbsp; G/Maç</div>",
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 12 — TRANSFER ÖNER
# ══════════════════════════════════════════════════════════════════════════════

# Öneri veri tabanı: (mevki, bütçe, tercih) → [oyuncu adları]
def _groq_client():
    """Groq istemcisi oluşturur. Hem lokal .env hem Streamlit secrets destekler."""
    key = None
    env_yol = _DIZIN / ".env"
    if env_yol.exists():
        for line in env_yol.read_text(encoding="utf-8").strip().splitlines():
            if line.startswith("GROQ_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key:
        key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
    if not key or not _GROQ_OK:
        return None
    return _Groq(api_key=key)


def transfer_raporu_uret(oneriler: list, mevki: str, butce_label: str, tercih: str) -> str:
    """Verilen öneri listesi için Groq ile transfer raporu üretir."""
    client = _groq_client()
    if not client:
        return "⚠️ Rapor üretilemedi: API bağlantısı kurulamadı."

    # Kaleci mi değil mi — veri kaynağını buna göre seç
    if mevki == "Kaleci":
        kal_df   = kaleci_istatistikleri_hesapla()
        kal_dict = {r["Kaleci"]: r for _, r in kal_df.iterrows()}
        alan_df_dict = {}
    else:
        kal_dict = {}
        _alan_df, _ = veri_yukle()
        alan_df_dict = {r["Oyuncu"]: r for _, r in _alan_df.iterrows()} if not _alan_df.empty else {}

    oyuncu_verileri = []
    for isim in oneriler:
        profil = sd_profiller.get(isim, {})
        yas    = _MANUEL_YAS.get(isim)
        if not yas:
            try: yas = int(float(str(profil.get("Age","0")).split()[0]))
            except: yas = "?"
        nat = _MANUEL_UYRUK.get(isim) or profil.get("Nationality","")
        nat = _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nat).split()[0] if nat else "—"

        if mevki == "Kaleci":
            r = kal_dict.get(isim, {})
            oyuncu_verileri.append(
                f"- {isim} | Takım: {r.get('Takım','—')} | "
                f"{r.get('Maç','—')} maç, {r.get('YenilenGol','—')} yenilen gol, "
                f"{r.get('G/Maç','—')} G/Maç | Yaş: {yas} | Uyruk: {nat}"
            )
        else:
            r = alan_df_dict.get(isim, {})
            oyuncu_verileri.append(
                f"- {isim} | Takım: {r.get('Takım','—')} | "
                f"{r.get('Maç','—')} maç, {r.get('Gol','—')} gol, "
                f"{r.get('Gol/Maç','—')} Gol/Maç | Dakika: {r.get('Dakika','—')} | "
                f"Yaş: {yas} | Uyruk: {nat}"
            )

    veri_str = "\n".join(oyuncu_verileri)

    prompt = f"""Sen Türkiye Kadın Futbol Süper Ligi uzmanı bir futbol transfer danışmanısın.
Bütçe: {butce_label} | Mevki: {mevki} | Tercih: {tercih}

ÖNERILEN OYUNCULAR VE İSTATİSTİKLERİ (2025-26 sezonu):
{veri_str}

Bu üç oyuncu için kısa ve profesyonel bir transfer raporu yaz:

1. Her oyuncu için ayrı paragraf: performans değerlendirmesi (istatistiklere dayan), \
transferilebilirlik (mevcut takımındaki konumu), risk faktörü.
2. Sonda 2 cümlelik genel tavsiye: bu üçten hangisi en öncelikli seçenek ve neden?

Kurallar:
- Sadece Türkçe yaz
- Oyuncu isimlerini değiştirme
- Takım büyüklüğünden bahsederken "küçük takım" yerine "orta ölçekli takım" kullan
- Veri odaklı ol, klişeden kaçın
- Maksimum 300 kelime"""

    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sen bir futbol transfer danışmanısın. Sadece Türkçe yaz. İstatistikleri kullan. Küçük takım yerine orta ölçekli takım de."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"⚠️ Rapor üretilemedi: {e}"


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

with tab_transfer:
    if not st.session_state.get("kulup_giris"):
        giris_gerekli_ekrani()
    elif not pro_kontrol():
        pro_paywall_goster(t("Transfer Öner", "Transfer Suggest"))
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
                if st.button(t("🚀 Başla","🚀 Start"), use_container_width=True, type="primary"):
                    st.session_state["tr_adim"] = 1
                    st.rerun()

        # ── ADIM 1: Bütçe seç ───────────────────────────────────────────
        elif adim == 1:
            st.markdown(f"### {t('Adım 1 / 3','Step 1 / 3')} &nbsp; 💰 {t('Bütçenizi seçin','Select your budget')}")
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(t("💎 Yüksek\n\nBüyük kulüp transferi","💎 High\n\nBig club transfer"), use_container_width=True):
                    st.session_state["tr_butce"]      = "Yuksek"
                    st.session_state["tr_butce_label"] = t("Yüksek 💎","High 💎")
                    st.session_state["tr_adim"]        = 2
                    st.rerun()
            with c2:
                if st.button(t("🔵 Orta\n\nOrta ölçekli transfer","🔵 Medium\n\nMid-range transfer"), use_container_width=True):
                    st.session_state["tr_butce"]      = "Orta"
                    st.session_state["tr_butce_label"] = t("Orta 🔵","Medium 🔵")
                    st.session_state["tr_adim"]        = 2
                    st.rerun()
            with c3:
                if st.button(t("🟡 Düşük\n\nBütçe dostu transfer","🟡 Low\n\nBudget-friendly transfer"), use_container_width=True):
                    st.session_state["tr_butce"]      = "Dusuk"
                    st.session_state["tr_butce_label"] = t("Düşük 🟡","Low 🟡")
                    st.session_state["tr_adim"]        = 2
                    st.rerun()

        # ── ADIM 2: Mevki + tercih ──────────────────────────────────────
        elif adim == 2:
            butce       = st.session_state.get("tr_butce", "")
            butce_label = st.session_state.get("tr_butce_label", butce)
            st.markdown(f"### {t('Adım 2 / 3','Step 2 / 3')} &nbsp; 📋 {t('Mevki ve tercih','Position and preference')}")
            st.markdown(f"<div style='color:#8899aa;font-size:13px;'>{t('Bütçe','Budget')}: <b style='color:#00c853'>{butce_label}</b></div>", unsafe_allow_html=True)
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
                mevki_sec = st.radio("", mevki_secenekler, key="tr_mevki_radio",
                                     format_func=lambda x: _TR_MEVKI_EN.get(x, x) if EN else x,
                                     label_visibility="collapsed")

            with col_t:
                st.markdown(f"**{t('Oyuncu tercihiniz?','Player preference?')}**")
                _tr_tercih_opts = ["Farketmez", "Yerli", "Yabancı"]
                tercih = st.radio("", _tr_tercih_opts, key="tr_tercih_radio",
                    format_func=lambda x: _TR_TERCIH_EN[x] if EN else x,
                    label_visibility="collapsed")

            st.markdown("<br>", unsafe_allow_html=True)
            col_geri, col_ileri = st.columns([1, 3])
            with col_geri:
                if st.button(t("← Geri","← Back"), use_container_width=True):
                    st.session_state["tr_adim"] = 1
                    st.rerun()
            with col_ileri:
                if st.button(t("Önerileri Gör →","See Suggestions →"), use_container_width=True, type="primary"):
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
                    f"<div style='color:#00c853;font-weight:700;font-size:16px;margin-bottom:20px;'>"
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
                        renk  = "#00c853" if isinstance(gol, (int,float)) and gol <= 1.0 else \
                                "#ffab00" if isinstance(gol, (int,float)) and gol <= 2.0 else "#ff6b6b"
                    else:
                        o     = oyuncu_detay.get(isim, {})
                        mac   = o.get("mac_sayisi", "—")
                        gol   = o.get("gol_sayisi", "—")
                        takim = o.get("takim", "—")
                        s2    = "Gol"
                        renk  = "#00c853"

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
                st.markdown(
                    "<div style='background:#1a1f36;border:1px solid #00c853;border-radius:10px;"
                    "padding:18px;'>"
                    f"<div style='color:#00c853;font-weight:700;font-size:15px;margin-bottom:6px;'>"
                    f"📄 {t('Transfer Raporu','Transfer Report')}</div>"
                    f"<div style='color:#8899aa;font-size:12px;'>"
                    f"{t('Bu üç oyuncu için yapay zeka destekli detaylı analiz raporu üretin.','Generate an AI-powered detailed analysis report for these three players.')}</div>"
                    "</div>",
                    unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(t("📄 Raporu Oluştur","📄 Generate Report"), type="primary", use_container_width=False):
                    with st.spinner(t("Rapor hazırlanıyor…","Generating report…")):
                        rapor = transfer_raporu_uret(oneriler, mevki_sec, butce_label, tercih)
                    st.session_state["tr_rapor"] = rapor

                if st.session_state.get("tr_rapor"):
                    st.markdown(
                        f"<div style='background:#1a1f36;border-radius:10px;padding:20px;"
                        f"border-left:4px solid #00c853;margin-top:12px;'>"
                        f"<div style='color:#fff;font-size:13px;line-height:1.7;white-space:pre-wrap;'>"
                        f"{st.session_state['tr_rapor']}</div></div>",
                        unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(t("🔄 Yeniden Başla","🔄 Start Over"), use_container_width=False):
                for k in ["tr_adim","tr_butce","tr_butce_label","tr_mevki","tr_tercih","tr_rapor"]:
                    st.session_state.pop(k, None)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCOUTING SAYFASI (sadece admin — tam sayfa)
# ══════════════════════════════════════════════════════════════════════════════

# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="altbilgi">{t("Veri kaynağı: TFF — tff.org | 2025-2026 Kadınlar Süper Ligi","Data source: TFF — tff.org | 2025-2026 Women\'s Super League")}</div>',
    unsafe_allow_html=True)
