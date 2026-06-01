"""
Türkiye Kadınlar Süper Ligi 2025-2026 — Streamlit Web Arayüzü
"""
import json, os, pathlib, requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Türkiye Kadınlar Süper Ligi 2025-2026",
    page_icon="⚽", layout="wide",
)

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
        st.warning("oyuncular.json bulunamadı.")
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

@st.cache_data(ttl=3600)
def sd_profiller_yukle():
    yol = _DIZIN / "soccerdonna_profiller.json"
    if yol.exists():
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    return {}

sd_profiller = sd_profiller_yukle()

@st.cache_data(ttl=86400)
def manuel_yaslar_yukle() -> tuple:
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

_MANUEL_YAS, _MANUEL_MEVKI, _MANUEL_UYRUK = manuel_yaslar_yukle()


def mevki_normalize(pozisyon: str) -> str:
    if not pozisyon: return "Bilinmiyor"
    if "Goalkeeper" in pozisyon: return "Kaleci"
    if "Defend" in pozisyon or "Defence" in pozisyon or "Back" in pozisyon: return "Defans"
    if "Midfield" in pozisyon: return "Orta Saha"
    if "Striker" in pozisyon or "Forward" in pozisyon or "Wing" in pozisyon: return "Forvet"
    return "Bilinmiyor"


import re as _re

def _ilk_uyruk(nat_str: str) -> str:
    """'TurkeyGermany' → 'Turkey', 'France' → 'France'"""
    nat_str = (nat_str or "").strip()
    if not nat_str:
        return ""
    # CamelCase geçişine boşluk ekle, ilk kelimeyi al
    spaced = _re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nat_str)
    return spaced.split()[0]


def df_zenginlestir(df: "pd.DataFrame") -> "pd.DataFrame":
    """df_tam'a Mevki, Uyruk, Boy ve Yaş sütunlarını ekler."""
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
    df_tam = df_zenginlestir(df_tam)  # Mevki + Uyruk + Boy ekle


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

# ─── PAYLAŞILABILIR LİNK: URL parametresi varsa otomatik profil aç ──────────
params = st.query_params
url_oyuncu = params.get("oyuncu", "")

# ─── BAŞLIK ───────────────────────────────────────────────────────────────────
bas_sol, bas_sag = st.columns([5, 1])
with bas_sol:
    st.markdown("""
    <div class="baslik-kutu">
      <h1>⚽ Türkiye Kadınlar Süper Ligi 2025-2026</h1>
      <p>30 haftanın tüm oyuncu istatistikleri — maç, gol, kart, dakika, forma ve karşılaştırma</p>
    </div>""", unsafe_allow_html=True)
with bas_sag:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏠 Ana Sayfa", use_container_width=True):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

# ─── ÖZET KARTLAR ─────────────────────────────────────────────────────────────
if not df_tam.empty:
    k1, k2, k3 = st.columns(3)
    en_golcu = df_tam.loc[df_tam["Gol"].idxmax(), "Oyuncu"]
    for kol, sayi, etiket in [
        (k1, len(df_tam),              "Oyuncu"),
        (k2, df_tam["Takım"].nunique(), "Takım"),
        (k3, int(df_tam["Gol"].sum()),  "Toplam Gol"),
    ]:
        kol.markdown(
            f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
            f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── SEKMELER ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📋 Oyuncu Listesi", "👤 Oyuncu Profili", "⚡ Karşılaştırma",
    "🏟️ Takımlar", "🏆 Lig Tablosu", "🌟 En İyiler", "⚽ Fantasy Kadro",
    "🗺️ Dünya Haritası", "🔍 Gelişmiş Arama", "🎂 Yaş Analizi",
])

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 1 — OYUNCU LİSTESİ
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if df_tam.empty:
        st.info("Veri yok."); st.stop()

    f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
    with f1:
        secenekler = ["— Tüm oyuncular —"] + sorted(df_tam["Oyuncu"].tolist())
        secili_oyuncu = st.selectbox("Oyuncu Ara", secenekler,
            index=secenekler.index(url_oyuncu) if url_oyuncu in secenekler else 0)
    with f2:
        takimlar = ["Tüm Takımlar"] + sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_takim = st.selectbox("Takım", takimlar)
    with f3:
        mevki_secenekler = ["Tüm Mevkiler", "Kaleci", "Defans", "Orta Saha", "Forvet"]
        secili_mevki = st.selectbox("Mevki", mevki_secenekler)
    with f4:
        siralama = st.selectbox("Sırala", ["Maç ↓","Gol ↓","Dakika ↓","Sarı ↓","Gol/Maç ↓"])

    df = df_tam.copy()
    if secili_oyuncu != "— Tüm oyuncular —":
        df = df[df["Oyuncu"] == secili_oyuncu]
    if secili_takim != "Tüm Takımlar":
        df = df[df["TümTakımlar"].str.contains(secili_takim, na=False)]
    if secili_mevki != "Tüm Mevkiler" and "Mevki" in df.columns:
        df = df[df["Mevki"] == secili_mevki]

    siralama_map = {"Maç ↓":"Maç","Gol ↓":"Gol","Dakika ↓":"Dakika","Sarı ↓":"Sarı","Gol/Maç ↓":"Gol/Maç"}
    df = df.sort_values(siralama_map[siralama], ascending=False).reset_index(drop=True)
    df.index += 1

    df = df.copy()
    df["Takım (Gösterim)"] = df.apply(
        lambda r: r["TümTakımlar"] if r["Transfer"] else r["Takım"], axis=1)

    bas, ind = st.columns([3,1])
    with bas: st.markdown(f"#### {len(df)} oyuncu")
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
            "Oyuncu":           st.column_config.TextColumn("Oyuncu",       width="medium"),
            "Takım (Gösterim)": st.column_config.TextColumn("Takım",        width="medium"),
            "Maç":     st.column_config.NumberColumn("Maç",   format="%d"),
            "İlk11":   st.column_config.NumberColumn("▶11",   format="%d",  help="İlk 11'de başladığı maç sayısı"),
            "Yedek":   st.column_config.NumberColumn("↗Yed",  format="%d",  help="Yedek olarak girdiği maç sayısı"),
            "Gol":     st.column_config.ProgressColumn("Gol", min_value=0, max_value=max_gol, format="%d"),
            "GolF":    st.column_config.NumberColumn("⚽F",   format="%d",  help="Ayakla gol (F)"),
            "GolH":    st.column_config.NumberColumn("⚽H",   format="%d",  help="Kafa golü (H)"),
            "GolP":    st.column_config.NumberColumn("⚽P",   format="%d",  help="Penaltı golü (P)"),
            "Gol/Maç": st.column_config.NumberColumn("G/M",  format="%.2f", help="Maç başına gol ortalaması"),
            "Sarı":    st.column_config.NumberColumn("🟨",    format="%d"),
            "Kırmızı": st.column_config.NumberColumn("🟥",   format="%d"),
            "Dakika":  st.column_config.ProgressColumn("Dakika", min_value=0, max_value=max_dk, format="%d"),
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
            for sutun, etiket in [("Gol","GOL"),("Maç","MAÇ"),("Dakika","DK")]:
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
            st.caption("👆 Tam profil için 'Oyuncu Profili' sekmesine geç")
    st.caption("⚽F = Ayak golü · ⚽H = Kafa golü · ⚽P = Penaltı · ▶11 = İlk 11 · ↗Yed = Yedek giriş")

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 2 — OYUNCU PROFİLİ
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    oyuncu_listesi = sorted(df_tam["Oyuncu"].tolist())
    varsayilan_idx = oyuncu_listesi.index(url_oyuncu) if url_oyuncu in oyuncu_listesi else 0
    secili = st.selectbox("Oyuncu seç", oyuncu_listesi, index=varsayilan_idx, key="profil_sec")

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
        st.markdown(f"🔗 **Paylaşılabilir link:** `{share_url}`")
        if st.button("📋 Linki Kopyala (adres çubuğuna bakın)"):
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
            <div class="profil-stat-item"><div class="deger">{mac}</div><div class="ad">Maç</div></div>
            <div class="profil-stat-item"><div class="deger">{ilk11}</div><div class="ad">▶ İlk 11</div></div>
            <div class="profil-stat-item"><div class="deger">{yedek}</div><div class="ad">↗ Yedek</div></div>
            <div class="profil-stat-item"><div class="deger">{ilk11_oran}%</div><div class="ad">Starter %</div></div>
            <div class="profil-stat-item"><div class="deger">{dk}</div><div class="ad">Top. Dakika</div></div>
            <div class="profil-stat-item"><div class="deger">{int(dk_mac)}</div><div class="ad">Dk/Maç</div></div>
            <div class="profil-stat-item"><div class="deger">{gol}</div><div class="ad">Gol{gol_detay}</div></div>
            <div class="profil-stat-item"><div class="deger">{gol_f}</div><div class="ad">⚽ Ayak (F)</div></div>
            <div class="profil-stat-item"><div class="deger">{gol_h}</div><div class="ad">🆕 Kafa (H)</div></div>
            <div class="profil-stat-item"><div class="deger">{pen}</div><div class="ad">Penaltı (P)</div></div>
            <div class="profil-stat-item"><div class="deger">{ort}</div><div class="ad">Gol/Maç</div></div>
            <div class="profil-stat-item"><div class="deger" style="color:#f5c518">{sari}</div><div class="ad">🟨 Sarı</div></div>
            <div class="profil-stat-item"><div class="deger" style="color:#e53935">{kir}</div><div class="ad">🟥 Kırmızı</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        p1, p2 = st.columns(2)

        # ── Son 5 maç formu ──────────────────────────────────────────────────
        with p1:
            st.markdown("##### Son 5 Maç Formu")
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
                st.caption("Maç verisi yok.")

        # ── Lig sıralamaları ─────────────────────────────────────────────────
        with p2:
            st.markdown("##### Lig Sıralaması")
            r1, r2 = st.columns(2)
            for kol, metrik, etiket in [
                (r1, "Gol",    "Gol"),
                (r2, "Dakika", "Dakika"),
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
            st.markdown("##### Haftalık Performans")
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
            st.markdown("##### Gol Zamanı Dağılımı")
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
                st.caption("Gol dakikası verisi bu sezonda mevcut değil.")
            else:
                st.caption("Bu oyuncu gol atmadı.")

        # ── Seriler ──────────────────────────────────────────────────────────
        if gecmis_tam:
            st.markdown("##### 🔥 Seri Rekorları")
            # En uzun ardışık maç serisi
            en_uzun_mac = max_seri([1 for _ in gecmis_tam])
            # En uzun gol serisi (ardışık maçlarda gol)
            gol_var = [1 if m["gol"]>0 else 0 for m in gecmis_tam]
            en_uzun_gol = max_seri(gol_var)
            # En uzun kart almama serisi
            temiz = [1 if m["sari"]==0 and m["kirmizi"]==0 else 0 for m in gecmis_tam]
            en_uzun_temiz = max_seri(temiz)

            s1,s2,s3 = st.columns(3)
            s1.metric("🏃 En Uzun Maç Serisi", f"{en_uzun_mac} maç")
            s2.metric("⚽ En Uzun Gol Serisi", f"{en_uzun_gol} maç")
            s3.metric("🛡️ En Uzun Temiz Seri", f"{en_uzun_temiz} maç")

        # ── Transfer kırılımı ─────────────────────────────────────────────────
        if transfer:
            st.markdown("##### Takım Bazlı İstatistikler")
            satirlar = ""
            for d in detay.get("takim_detay", []):
                satirlar += f"""
                <div class="takim-detay-satir">
                  <span class="td-adi">🏟 {d['takim']}</span>
                  <span class="td-stats">
                    {d['mac']} maç · {d['gol']} gol · {d['dakika']} dk ·
                    🟨{d['sari']} 🟥{d['kirmizi']}
                  </span>
                </div>"""
            st.markdown(satirlar, unsafe_allow_html=True)

        # ── Oyuncu Kartı ─────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### 🃏 Oyuncu Kartı")
        st.markdown(f"""
        <div style="max-width:320px;margin:0 auto;
             background:linear-gradient(145deg,#1a1f36,#0d3b2e);
             border-radius:18px;padding:26px 28px;text-align:center;
             box-shadow:0 8px 32px rgba(0,0,0,0.6);
             border:1px solid #00c85344;">
          <div style="font-size:0.68rem;letter-spacing:3px;color:#00c853aa;margin-bottom:4px">
            KADIN FUTBOL · 2025-2026
          </div>
          <div style="font-size:1.2rem;font-weight:800;color:#fff;margin-bottom:2px">{secili}</div>
          <div style="color:#8899aa;font-size:0.78rem;margin-bottom:20px">{row['Takım'][:35]}</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px">
            <div style="background:rgba(0,200,83,0.08);border:1px solid #00c85333;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#00c853">{gol}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">GOL</div>
            </div>
            <div style="background:rgba(41,121,255,0.08);border:1px solid #2979ff33;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#2979ff">{mac}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">MAÇ</div>
            </div>
            <div style="background:rgba(255,109,0,0.08);border:1px solid #ff6d0033;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#ff6d00">{ort}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">G/MAÇ</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid #ffffff11;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#e0e0e0">{ilk11_oran}%</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">STARTER</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid #ffffff11;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#e0e0e0">{int(dk_mac)}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">DK/MAÇ</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid #ffffff11;
                 border-radius:8px;padding:10px 6px">
              <div style="font-size:1.5rem;font-weight:800;color:#f5c518">{sari}</div>
              <div style="font-size:0.62rem;color:#8899aa;margin-top:2px">🟨 KART</div>
            </div>
          </div>
        </div>
        <div style="text-align:center;color:#505870;font-size:0.7rem;margin-top:8px">
          Ekran görüntüsü alarak paylaşabilirsiniz
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 3 — KARŞILAŞTIRMA (2-4 oyuncu)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ⚡ Oyuncu Karşılaştırması")
    st.caption("2 ile 4 oyuncu arasında seçim yapabilirsiniz.")

    oyuncu_listesi2 = sorted(df_tam["Oyuncu"].tolist())

    VARSAYILAN_OYUNCULAR = [
        "EBRU TOPÇU", "ECE TÜRKOĞLU", "DONJETA HALILAJ", "MILICA MIJATOVIC"
    ]
    # Listede bulunanları filtrele, eksikse ilk N oyuncuyla tamamla
    varsayilan = [o for o in VARSAYILAN_OYUNCULAR if o in oyuncu_listesi2]
    if len(varsayilan) < 2:
        varsayilan = oyuncu_listesi2[:4]

    secili_oyuncular = st.multiselect(
        "Karşılaştırılacak oyuncuları seç (2-4)",
        oyuncu_listesi2,
        default=varsayilan,
        max_selections=4,
        key="karsilastirma_sec",
    )

    RENKLER = ["#00c853", "#2979ff", "#ff6d00", "#e040fb"]

    if len(secili_oyuncular) < 2:
        st.info("En az 2 oyuncu seçin.")
    elif not df_tam.empty:

        # ── Radar chart ──────────────────────────────────────────────────────
        kategoriler = ["Maç", "Gol", "Gol/Maç", "Dakika", "Starter %", "Disiplin"]

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
        st.caption("Disiplin = 100 − (sarı kart oranı) · Starter % = ilk 11 oranı · Tüm değerler lig içinde normalize edilmiştir (100 = en iyi).")

        # ── Sayısal karşılaştırma tablosu ────────────────────────────────────
        st.markdown("##### 📊 İstatistik Karşılaştırması")

        METRIK_ETIKET = {
            "Maç":     "Maç",
            "İlk11":   "▶ İlk 11",
            "Yedek":   "↗ Yedek",
            "Gol":     "Gol",
            "GolF":    "⚽ Ayak (F)",
            "GolH":    "⚽ Kafa (H)",
            "GolP":    "⚽ Penaltı (P)",
            "Gol/Maç": "Gol/Maç",
            "Sarı":    "🟨 Sarı Kart",
            "Kırmızı": "🟥 Kırmızı",
            "Dakika":  "Toplam Dakika",
        }
        # Kart sayısı düşük olan iyi → ters metrikler
        TERS = {"Sarı", "Kırmızı"}

        tablo_satirlar = []
        for metrik, etiket in METRIK_ETIKET.items():
            satir = {"İstatistik": etiket}
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
        df_karsilastirma = df_karsilastirma.set_index("İstatistik")

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
        st.caption("★ = o kategoride en iyi")

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
    st.markdown("### 🏟️ Takım Analizi")

    if not df_tam.empty:
        takim_listesi_tam = sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_t = st.selectbox("Takım seç", takim_listesi_tam, key="takim_sayfasi")
        df_t = df_tam[df_tam["Takım"] == secili_t].copy()

        st.markdown("---")

        # ── Takım özet istatistikleri ─────────────────────────────────────
        t1, t2, t3, t4, t5 = st.columns(5)
        for kol, sayi, etiket in [
            (t1, len(df_t),                  "Oyuncu"),
            (t2, int(df_t["Gol"].sum()),      "Toplam Gol"),
            (t3, int(df_t["Maç"].sum()),      "Toplam Maç"),
            (t4, int(df_t["Dakika"].sum()),   "Toplam Dakika"),
            (t5, int(df_t["Sarı"].sum()),     "Sarı Kart"),
        ]:
            kol.markdown(
                f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                f'<div class="etiket">{etiket}</div></div>',
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        sol, sag = st.columns(2)

        # ── Kadro tablosu ─────────────────────────────────────────────────
        with sol:
            st.markdown("##### 👥 Kadro")
            kadro = df_t.sort_values("Maç", ascending=False)[
                ["Oyuncu","Mevki","Maç","Gol","Dakika","Sarı"]
            ].reset_index(drop=True)
            kadro.index += 1
            st.dataframe(kadro, use_container_width=True, height=400,
                column_config={
                    "Oyuncu": st.column_config.TextColumn("Oyuncu", width="medium"),
                    "Mevki":  st.column_config.TextColumn("Mevki",  width="small"),
                    "Maç":    st.column_config.NumberColumn("Maç",   format="%d"),
                    "Gol":    st.column_config.NumberColumn("Gol",   format="%d"),
                    "Dakika": st.column_config.NumberColumn("Dk",    format="%d"),
                    "Sarı":   st.column_config.NumberColumn("🟨",    format="%d"),
                })

        # ── Mevki dağılımı + uyruk ─────────────────────────────────────
        with sag:
            st.markdown("##### 📊 Mevki Dağılımı")
            if "Mevki" in df_t.columns:
                mevki_sayilari = df_t["Mevki"].value_counts()
                MEVKI_RENK = {"Kaleci":"#00c853","Defans":"#2979ff",
                              "Orta Saha":"#ff6d00","Forvet":"#e040fb","Bilinmiyor":"#555"}
                fig_mevki = go.Figure(go.Pie(
                    labels=mevki_sayilari.index,
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

            st.markdown("##### 🌍 Uyruk Dağılımı")
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
        st.markdown("##### ⚡ Dakika-Gol Verimliliği")
        fig_s = go.Figure()
        for mevki, renk in [("Kaleci","#00c853"),("Defans","#2979ff"),
                              ("Orta Saha","#ff6d00"),("Forvet","#e040fb"),("Bilinmiyor","#555")]:
            alt = df_t[df_t.get("Mevki","") == mevki] if "Mevki" in df_t.columns else df_t
            if alt.empty: continue
            fig_s.add_trace(go.Scatter(
                x=alt["Dakika"], y=alt["Gol"],
                mode="markers+text", name=mevki,
                marker=dict(color=renk, size=10),
                text=alt["Oyuncu"].str.split().str[-1],
                textposition="top center", textfont=dict(size=9),
                hovertemplate="%{text}<br>%{x} dk, %{y} gol<extra></extra>",
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
    st.markdown("### Puan Durumu")

    # Oyuncu verisinden takım istatistikleri hesapla
    if not df_tam.empty:
        takim_ozet = df_tam.groupby("Takım").agg(
            Oyuncu=("Oyuncu", "count"),
            TopGol=("Gol", "sum"),
            TopDk=("Dakika", "sum"),
            TopSari=("Sarı", "sum"),
            TopKirmizi=("Kırmızı", "sum"),
        ).reset_index().sort_values("TopGol", ascending=False)

        takim_ozet.columns = ["Takım","Oyuncu Sayısı","Toplam Gol","Toplam Dakika","Sarı Kart","Kırmızı Kart"]
        takim_ozet.index = range(1, len(takim_ozet)+1)

        st.markdown("#### Takım Bazlı Sezon İstatistikleri")
        st.dataframe(takim_ozet, use_container_width=True, height=520,
            column_config={
                "Takım":          st.column_config.TextColumn("Takım", width="large"),
                "Oyuncu Sayısı":  st.column_config.NumberColumn("Kadro"),
                "Toplam Gol":     st.column_config.ProgressColumn("Toplam Gol",
                    min_value=0, max_value=int(takim_ozet["Toplam Gol"].max()), format="%d"),
                "Toplam Dakika":  st.column_config.NumberColumn("Toplam Dk"),
                "Sarı Kart":      st.column_config.NumberColumn("🟨"),
                "Kırmızı Kart":   st.column_config.NumberColumn("🟥"),
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # TFF'den resmi puan cetveli
        st.markdown("#### 🏆 TFF Resmi Puan Cetveli")
        with st.spinner("TFF'den yükleniyor..."):
            df_puan = puan_durumu_cek()

        if not df_puan.empty:
            # Sütun adlarını düzelt — O G B M A Y AV P
            sutun_aciklama = {
                "O": "O — Oynadı", "G": "G — Galibiyet", "B": "B — Beraberlik",
                "M": "M — Mağlubiyet", "A": "A — Atılan", "Y": "Y — Yenilen",
                "AV": "AV — Averaj", "P": "P — Puan",
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
            st.caption("Kaynak: TFF — tff.org | O=Oynadı · G=Galibiyet · B=Beraberlik · M=Mağlubiyet · A=Atılan · Y=Yenilen · AV=Averaj · P=Puan")
        else:
            st.caption("TFF puan cetveli yüklenemedi.")

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 6 — EN İYİLER
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### 🌟 2025-2026 Sezonu En İyileri")
    if df_tam.empty:
        st.info("Veri yok.")
    else:
        # ── Lig Geneli Verimlilik Scatter ──────────────────────────────
        st.markdown("#### ⚡ Tüm Ligde Dakika-Gol Verimliliği")
        st.caption("Sağ üst = hem çok oynadı hem çok gol attı. Her renk bir mevki.")
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
                mode="markers", name=mevki,
                marker=dict(color=renk, size=7, opacity=0.8),
                text=alt["Oyuncu"],
                hovertemplate="%{text}<br>%{x} dk · %{y} gol<extra></extra>",
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
        st.markdown("#### 🌍 Uyruk Dağılımı")
        if "Uyruk" in df_tam.columns:
            ua, ub = st.columns(2)
            with ua:
                st.markdown("**Oyuncu sayısına göre**")
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
                st.markdown("**Gol sayısına göre**")
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
            en_iyi_kart("Gol Kraliçesi",
                df_tam.nlargest(5,"Gol")[["Oyuncu","Takım","Gol","GolF","GolH","GolP"]],
                ["Gol"], "⚽")

        with r1c2:
            en_iyi_kart("En Çok Oynayan",
                df_tam.nlargest(5,"Dakika")[["Oyuncu","Takım","Dakika","Maç"]],
                ["Dakika","Maç"], "🏃")

        with r1c3:
            # Min 10 maç şartı
            df_ort = df_tam[df_tam["Maç"]>=10].nlargest(5,"Gol/Maç")[["Oyuncu","Takım","Gol/Maç","Gol","Maç"]]
            en_iyi_kart("En İyi Gol Ortalaması",
                df_ort, ["Gol/Maç"], "🎯")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Satır 2 ──────────────────────────────────────────────────────────
        r2c1, r2c2, r2c3 = st.columns(3)

        with r2c1:
            en_iyi_kart("Kafa Golü Uzmanı",
                df_tam[df_tam["GolH"]>0].nlargest(5,"GolH")[["Oyuncu","Takım","GolH","Gol"]],
                ["GolH"], "🆕")

        with r2c2:
            en_iyi_kart("Penaltı Uzmanı",
                df_tam[df_tam["GolP"]>0].nlargest(5,"GolP")[["Oyuncu","Takım","GolP","Gol"]],
                ["GolP"], "🥅")

        with r2c3:
            # En temiz oyuncu: sarı kart almadan en çok dakika
            df_temiz = df_tam[(df_tam["Sarı"]==0) & (df_tam["Kırmızı"]==0) & (df_tam["Maç"]>=10)]
            en_iyi_kart("Disiplin Şampiyonu",
                df_temiz.nlargest(5,"Dakika")[["Oyuncu","Takım","Dakika","Maç"]],
                ["Dakika"], "🛡️")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Satır 3 ──────────────────────────────────────────────────────────
        r3c1, r3c2, r3c3 = st.columns(3)

        with r3c1:
            # Starter şampiyonu: en yüksek ilk 11 oranı (min 15 maç)
            df_s = df_tam[df_tam["Maç"]>=15].copy()
            df_s["Starter%"] = (df_s["İlk11"] / df_s["Maç"] * 100).round(1)
            en_iyi_kart("Starter Şampiyonu",
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
                en_iyi_kart("En Uzun Gol Serisi",
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
                en_iyi_kart("En Uzun Kart Almama Serisi",
                    df_temiz_s[["Oyuncu","Takım","Temiz Seri","Toplam Maç"]],
                    ["Temiz Seri"], "🧹")

        # ── Takım başına en golcü ─────────────────────────────────────────────
        st.markdown("<br>")
        st.markdown("#### 🏟️ Her Takımın Gol Kraliçesi")
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
                        f'<div style="color:#00c853;font-size:0.82rem">⚽ {int(r["Gol"])} gol</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 7 — FANTASY KADRO
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown("### ⚽ Fantasy Kadro Kur")
    st.caption("Dizilişini seç, oyuncuları ata — saha gerçek zamanlı güncellenir.")

    if df_tam.empty:
        st.info("Veri yok.")
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
            formasyon_sec = st.selectbox("Diziliş", list(FORMASYON.keys()), key="ff_formasyon")
            slotlar = FORMASYON[formasyon_sec]

            # Hoca seçimi
            hoca_listesi = tum_hocalar()
            if hoca_listesi:
                secili_hoca = st.selectbox(
                    "🧑‍💼 Teknik Direktör",
                    ["— Hoca seç —"] + hoca_listesi,
                    key="ff_hoca",
                )
            else:
                secili_hoca = st.text_input("🧑‍💼 Teknik Direktör", key="ff_hoca_text",
                                            placeholder="Hoca adı girin...")
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
                if h and h != "— Hoca seç —":
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
            st.markdown(f"##### 📊 Kadro İstatistikleri — {len(secili_isimler)}/11 oyuncu seçildi")
            df_kadro = df_tam[df_tam["Oyuncu"].isin(secili_isimler)].copy()

            k1, k2, k3, k4, k5 = st.columns(5)
            for kol, sayi, etiket in [
                (k1, int(df_kadro["Gol"].sum()),    "Toplam Gol"),
                (k2, int(df_kadro["Maç"].sum()),    "Toplam Maç"),
                (k3, int(df_kadro["Dakika"].sum()), "Toplam Dakika"),
                (k4, int(df_kadro["Sarı"].sum()),   "Sarı Kart"),
                (k5, round(df_kadro["Gol/Maç"].mean(),2) if not df_kadro.empty else 0,"Ort. Gol/Maç"),
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
                    "Oyuncu": st.column_config.TextColumn("Oyuncu", width="medium"),
                    "Takım":  st.column_config.TextColumn("Takım",  width="medium"),
                    "Gol":    st.column_config.ProgressColumn("Gol",
                        min_value=0, max_value=int(df_tam["Gol"].max()), format="%d"),
                    "Gol/Maç": st.column_config.NumberColumn("G/M", format="%.2f"),
                })
        else:
            st.info("Soldan oyuncu seçmeye başla — saha canlı güncellenecek.")


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 8 — DÜNYA HARİTASI
# ══════════════════════════════════════════════════════════════════════════════
_NAT_FIX = {
    "United":            "United States",
    "Cote":              "Ivory Coast",
    "Congo":             "Republic of the Congo",
    "Bosnia-Herzegovina":"Bosnia and Herzegovina",
    "Korea,":            "South Korea",
    "Burkina":           "Burkina Faso",
    "El":                "El Salvador",
    "Costa":             "Costa Rica",
    "Puerto":            "Puerto Rico",
}

def _harita_verisi():
    """soccerdonna_profiller.json'dan uyruk bazlı oyuncu sayısını döndürür."""
    rows = []
    for isim, profil in sd_profiller.items():
        nat = _ilk_uyruk(profil.get("Nationality", "") or "")
        nat = _NAT_FIX.get(nat, nat)
        if len(nat) > 2:
            rows.append(nat)
    if not rows:
        return pd.DataFrame()
    s = pd.Series(rows).value_counts().reset_index()
    s.columns = ["Uyruk", "Oyuncu"]
    return s

with tab8:
    st.markdown("##### 🗺️ Oyuncuların Dünya Haritası")
    st.caption("SoccerDonna verisi · Kadın Futbol Süper Ligi oyuncularının uyruk dağılımı")

    cnt = _harita_verisi()

    if cnt.empty:
        st.warning("Uyruk verisi bulunamadı.")
    else:
        try:
            fig_map = px.choropleth(
                cnt,
                locations="Uyruk",
                locationmode="country names",
                color="Oyuncu",
                hover_name="Uyruk",
                hover_data={"Oyuncu": True, "Uyruk": False},
                color_continuous_scale=[
                    [0.0, "#1a3a2a"],
                    [0.2, "#0d5c3a"],
                    [0.5, "#00a86b"],
                    [1.0, "#00c853"],
                ],
                labels={"Oyuncu": "Oyuncu Sayısı"},
            )
            fig_map.update_geos(
                bgcolor="#0f1117",
                showcoastlines=True, coastlinecolor="#2a3a2a",
                showland=True, landcolor="#1a1f36",
                showocean=True, oceancolor="#0f1117",
                showframe=False,
                projection_type="natural earth",
            )
            fig_map.update_layout(
                paper_bgcolor="#0f1117",
                font=dict(color="#e0e0e0"),
                margin=dict(l=0, r=0, t=10, b=0),
                height=480,
                coloraxis_colorbar=dict(
                    title="Oyuncu",
                    tickfont=dict(color="#8899aa"),
                    titlefont=dict(color="#8899aa"),
                    bgcolor="#1a1f36",
                    bordercolor="#2a3a2a",
                ),
            )
            st.plotly_chart(fig_map, use_container_width=True)
        except Exception as e:
            st.warning(f"Harita oluşturulamadı: {e}")

        k1, k2, k3, k4 = st.columns(4)
        top = cnt.iloc[0]
        yabanci = cnt[cnt["Uyruk"] != "Turkey"]["Oyuncu"].sum()
        for kol, sayi, etiket in [
            (k1, len(sd_profiller),       "Toplam Oyuncu"),
            (k2, cnt["Uyruk"].nunique(),   "Farklı Uyruk"),
            (k3, f"{top['Oyuncu']} ({top['Uyruk']})", "En Çok"),
            (k4, int(yabanci),             "Yabancı Oyuncu"),
        ]:
            kol.markdown(
                f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 🏳️ Uyruk Sıralaması (İlk 20)")
        top20 = cnt.head(20).sort_values("Oyuncu")
        fig_bar = go.Figure(go.Bar(
            x=top20["Oyuncu"], y=top20["Uyruk"], orientation="h",
            marker=dict(color=top20["Oyuncu"],
                        colorscale=[[0,"#0d3b2e"],[1,"#00c853"]], showscale=False),
            text=top20["Oyuncu"], textposition="outside",
            textfont=dict(color="#e0e0e0", size=11),
            hovertemplate="%{y}: %{x} oyuncu<extra></extra>",
        ))
        fig_bar.update_layout(
            paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
            xaxis=dict(showgrid=False, color="#505870"),
            yaxis=dict(color="#e0e0e0"),
            margin=dict(l=10, r=40, t=5, b=5), height=520,
            font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SEKME 9 — GELİŞMİŞ OYUNCU ARAMA
# ══════════════════════════════════════════════════════════════════════════════
with tab9:
    st.markdown("##### 🔍 Gelişmiş Oyuncu Arama")
    st.caption("Uyruk, mevki, yaş ve maç sayısına göre filtrele")

    if df_tam.empty:
        st.warning("Veri yok.")
    else:
        fa1, fa2, fa3 = st.columns([2, 2, 2])
        fb1, fb2, fb3, fb4 = st.columns([2, 2, 2, 2])

        all_nats = sorted(df_tam["Uyruk"].dropna().replace("", pd.NA).dropna().unique())
        all_pos  = sorted(df_tam["Mevki"].dropna().replace("Bilinmiyor", pd.NA).dropna().unique())

        with fa1:
            sel_nats = st.multiselect("🌍 Uyruk", all_nats, placeholder="Tümü", key="as_nat")
        with fa2:
            sel_pos = st.multiselect("📋 Mevki", all_pos, placeholder="Tümü", key="as_pos")
        with fa3:
            isim_q = st.text_input("👤 İsim", placeholder="Ara…", key="as_isim")

        yas_vals = df_tam["Yaş"].dropna() if "Yaş" in df_tam.columns else pd.Series(dtype=float)
        yas_min = int(yas_vals.min()) if not yas_vals.empty else 15
        yas_max = int(yas_vals.max()) if not yas_vals.empty else 40
        mac_max = int(df_tam["Maç"].max()) if not df_tam.empty else 30

        with fb1:
            yas_range = st.slider("🎂 Yaş", yas_min, yas_max, (yas_min, yas_max), key="as_yas")
        with fb2:
            min_mac = st.slider("📅 Min. Maç", 0, mac_max, 0, key="as_mac")
        with fb3:
            min_gol = st.slider("⚽ Min. Gol", 0, int(df_tam["Gol"].max()), 0, key="as_gol")
        with fb4:
            sort_by = st.selectbox("Sırala", ["Maç ↓", "Gol ↓", "Dakika ↓", "Yaş ↑", "Oyuncu ↑"], key="as_sort")

        mask = pd.Series(True, index=df_tam.index)
        if sel_nats:
            mask &= df_tam["Uyruk"].isin(sel_nats)
        if sel_pos:
            mask &= df_tam["Mevki"].isin(sel_pos)
        if isim_q.strip():
            mask &= df_tam["Oyuncu"].str.contains(isim_q.strip(), case=False, na=False)
        mask &= df_tam["Maç"] >= min_mac
        mask &= df_tam["Gol"] >= min_gol
        if "Yaş" in df_tam.columns and not yas_vals.empty:
            yas_mask = df_tam["Yaş"].isna() | df_tam["Yaş"].between(yas_range[0], yas_range[1])
            mask &= yas_mask

        filtered = df_tam[mask].copy()
        sort_map = {"Maç ↓": ("Maç", False), "Gol ↓": ("Gol", False),
                    "Dakika ↓": ("Dakika", False), "Yaş ↑": ("Yaş", True), "Oyuncu ↑": ("Oyuncu", True)}
        sc, sa = sort_map[sort_by]
        filtered = filtered.sort_values(sc, ascending=sa).reset_index(drop=True)

        st.markdown(
            f"<div style='color:#00c853;font-size:13px;font-weight:700;margin:8px 0;'>"
            f"🎯 {len(filtered)} oyuncu bulundu</div>", unsafe_allow_html=True)

        if filtered.empty:
            st.info("Filtrelerle eşleşen oyuncu yok.")
        else:
            show = ["Oyuncu", "Takım", "Mevki", "Uyruk", "Yaş", "Maç", "İlk11", "Gol", "Dakika", "Sarı"]
            show = [c for c in show if c in filtered.columns]
            st.dataframe(filtered[show], hide_index=True, use_container_width=True,
                height=min(600, 45 + len(filtered) * 35),
                column_config={"Yaş": st.column_config.NumberColumn(format="%.0f")})


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
    st.markdown("##### 🎂 Yaş Analizi")
    st.caption("SoccerDonna verisi")

    yas_df = _yas_df()

    if yas_df.empty:
        st.warning("Yaş verisi bulunamadı.")
    else:
        avg_age = yas_df["yas"].mean()
        youngest = yas_df.loc[yas_df["yas"].idxmin()]
        oldest   = yas_df.loc[yas_df["yas"].idxmax()]
        u23      = int((yas_df["yas"] < 23).sum())

        k1, k2, k3, k4 = st.columns(4)
        for kol, sayi, etiket in [
            (k1, f"{avg_age:.1f}", "Lig Ort. Yaşı"),
            (k2, f"{youngest['yas']:.0f} — {youngest['isim']}", "En Genç"),
            (k3, f"{oldest['yas']:.0f} — {oldest['isim']}", "En Yaşlı"),
            (k4, u23, "U-23 Oyuncu"),
        ]:
            kol.markdown(
                f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
                f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_hist, col_takim = st.columns([3, 2], gap="large")

        with col_hist:
            st.markdown("**📊 Yaş Dağılımı**")
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

            st.markdown("**📅 Doğum Yılı Dağılımı**")
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
            st.markdown("**🏟 Takım Yaş Ortalamaları**")
            takim_yas = (yas_df[yas_df["takim"] != "Bilinmiyor"]
                         .groupby("takim")["yas"]
                         .agg(["mean","min","max","count"]).round(1)
                         .reset_index()
                         .rename(columns={"takim":"Takım","mean":"Ort","min":"Min","max":"Max","count":"Oyuncu"})
                         .sort_values("Ort"))
            st.dataframe(takim_yas, hide_index=True, use_container_width=True, height=400,
                column_config={
                    "Ort": st.column_config.NumberColumn(format="%.1f"),
                    "Min": st.column_config.NumberColumn(format="%.0f"),
                    "Max": st.column_config.NumberColumn(format="%.0f"),
                })
            if not takim_yas.empty:
                g = takim_yas.iloc[0]; y = takim_yas.iloc[-1]
                st.markdown(
                    f"<div style='font-size:12px;color:#8899aa;margin-top:8px;'>"
                    f"🟢 En genç: <b style='color:#00c853'>{g['Takım']}</b> ({g['Ort']} yaş)<br>"
                    f"🔴 En yaşlı: <b style='color:#ff6b6b'>{y['Takım']}</b> ({y['Ort']} yaş)</div>",
                    unsafe_allow_html=True)

            st.markdown("<br>**⚽ Mevkiye Göre Ortalama Yaş**")
            pos_yas_map = dict(zip(df_tam["Oyuncu"], df_tam["Mevki"])) if not df_tam.empty else {}
            yas_df["mevki"] = yas_df["isim"].map(pos_yas_map).fillna("Bilinmiyor")
            mevki_yas = (yas_df[yas_df["mevki"] != "Bilinmiyor"]
                         .groupby("mevki")["yas"].mean().round(1)
                         .reset_index().rename(columns={"mevki":"Mevki","yas":"Ort. Yaş"})
                         .sort_values("Ort. Yaş", ascending=False))
            fig_pos = go.Figure(go.Bar(
                x=mevki_yas["Ort. Yaş"], y=mevki_yas["Mevki"], orientation="h",
                marker=dict(color="#00a86b"),
                text=mevki_yas["Ort. Yaş"], textposition="outside",
                textfont=dict(color="#e0e0e0", size=12),
                hovertemplate="%{y}: %{x:.1f} yaş<extra></extra>",
            ))
            fig_pos.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                xaxis=dict(range=[0,35], color="#505870", showgrid=False),
                yaxis=dict(color="#e0e0e0"),
                margin=dict(l=10,r=50,t=5,b=5), height=180,
                font=dict(color="#e0e0e0"),
            )
            st.plotly_chart(fig_pos, use_container_width=True)


# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="altbilgi">Veri kaynağı: TFF — tff.org | 2025-2026 Kadınlar Süper Ligi</div>',
    unsafe_allow_html=True)
