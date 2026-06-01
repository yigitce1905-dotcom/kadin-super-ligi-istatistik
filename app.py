"""
Türkiye Kadınlar Süper Ligi 2025-2026 - Streamlit Web Arayüzü
Çalıştırmak için: streamlit run app.py
"""

import json
import os
import pandas as pd
import streamlit as st

# ─── SAYFA AYARLARI ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Türkiye Kadınlar Süper Ligi 2025-2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── ÖZEL CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Arka plan ve genel font */
    .stApp { background-color: #0f1117; color: #e0e0e0; }

    /* Başlık kutusu */
    .baslik-kutu {
        background: linear-gradient(135deg, #1a1f36 0%, #0d3b2e 100%);
        border-left: 5px solid #00c853;
        border-radius: 12px;
        padding: 24px 32px;
        margin-bottom: 28px;
    }
    .baslik-kutu h1 {
        color: #ffffff;
        font-size: 2rem;
        margin: 0 0 6px 0;
    }
    .baslik-kutu p {
        color: #a0aab4;
        margin: 0;
        font-size: 0.95rem;
    }

    /* İstatistik kartları */
    .stat-kart {
        background: #1a1f36;
        border-radius: 10px;
        padding: 18px 22px;
        text-align: center;
        border-top: 3px solid #00c853;
    }
    .stat-kart .sayi { font-size: 2.2rem; font-weight: 700; color: #00c853; }
    .stat-kart .etiket { font-size: 0.82rem; color: #8899aa; margin-top: 4px; }

    /* Filtre bölümü */
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background-color: #1a1f36 !important;
        color: #e0e0e0 !important;
        border-color: #2d3561 !important;
    }

    /* Tablo */
    .dataframe thead th {
        background-color: #0d3b2e !important;
        color: #00c853 !important;
        font-weight: 600 !important;
    }
    .dataframe tbody tr:hover { background-color: #1a2a40 !important; }

    /* Kenar çubuğu */
    section[data-testid="stSidebar"] {
        background-color: #12161f;
    }

    /* Altbilgi */
    .altbilgi {
        text-align: center;
        color: #505870;
        font-size: 0.8rem;
        margin-top: 40px;
        padding-top: 16px;
        border-top: 1px solid #1e2340;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── VERİ YÜKLEME ────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def veri_yukle():
    """JSON veya CSV dosyasından oyuncu verilerini yükler."""
    if os.path.exists("oyuncular.json"):
        with open("oyuncular.json", encoding="utf-8") as f:
            liste = json.load(f)
        df = pd.DataFrame(liste)
    elif os.path.exists("kadınlar_super_ligi_2026.csv"):
        df = pd.read_csv("kadınlar_super_ligi_2026.csv", encoding="utf-8-sig")
    else:
        # Veri dosyası yoksa demo verisi göster
        demo = [
            {"oyuncu": "Büşra Kılıç", "takim": "Beşiktaş", "mac_sayisi": 28, "gol_sayisi": 12},
            {"oyuncu": "Ezgi Koçak", "takim": "Galatasaray", "mac_sayisi": 27, "gol_sayisi": 9},
            {"oyuncu": "Melisa Öztürk", "takim": "Fenerbahçe", "mac_sayisi": 30, "gol_sayisi": 7},
            {"oyuncu": "Seray Demirci", "takim": "Kireçburnu", "mac_sayisi": 25, "gol_sayisi": 5},
            {"oyuncu": "Ayşe Yıldız", "takim": "Ankara BSB", "mac_sayisi": 22, "gol_sayisi": 4},
            {"oyuncu": "Ceren Aydın", "takim": "Blagovesta", "mac_sayisi": 29, "gol_sayisi": 3},
            {"oyuncu": "Nur Çelik", "takim": "Turkcell", "mac_sayisi": 20, "gol_sayisi": 11},
            {"oyuncu": "Zeynep Arslan", "takim": "Beşiktaş", "mac_sayisi": 26, "gol_sayisi": 6},
        ]
        df = pd.DataFrame(demo)
        st.warning(
            "⚠️ **Veri dosyası bulunamadı.** `scraper.py`'yi çalıştırarak gerçek veriyi toplayın. "
            "Şu an demo verisi gösterilmektedir.",
            icon="⚠️",
        )

    # Sütun adlarını standartlaştır
    sutun_map = {
        "oyuncu": "Oyuncu", "takim": "Takım",
        "mac_sayisi": "Maç Sayısı", "gol_sayisi": "Gol Sayısı",
    }
    df.rename(columns=sutun_map, inplace=True)

    # Eksik sütunları sıfırla doldur
    for s in ["Maç Sayısı", "Gol Sayısı"]:
        if s not in df.columns:
            df[s] = 0
    for s in ["Oyuncu", "Takım"]:
        if s not in df.columns:
            df[s] = ""

    df["Maç Sayısı"] = pd.to_numeric(df["Maç Sayısı"], errors="coerce").fillna(0).astype(int)
    df["Gol Sayısı"] = pd.to_numeric(df["Gol Sayısı"], errors="coerce").fillna(0).astype(int)
    return df


df_tam = veri_yukle()

# ─── KENAR ÇUBUĞU (FİLTRELER) ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Filtreler")
    st.markdown("---")

    arama = st.text_input(
        "Oyuncu Adı Ara",
        placeholder="Örn: Büşra, Ezgi...",
        help="Oyuncu adının bir kısmını yazın",
    )

    takimlar = ["Tüm Takımlar"] + sorted(df_tam["Takım"].dropna().unique().tolist())
    secili_takim = st.selectbox("Takım Seç", takimlar)

    st.markdown("---")
    st.markdown("### 📊 Sıralama Kriteri")
    siralama_kriteri = st.radio(
        "",
        ["Maç Sayısı (Azalan)", "Gol Sayısı (Azalan)", "Oyuncu Adı (A→Z)"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### 🎯 Minimum Değerler")
    min_mac = st.slider("Min. Maç Sayısı", 0, int(df_tam["Maç Sayısı"].max() or 30), 0)
    min_gol = st.slider("Min. Gol Sayısı", 0, int(df_tam["Gol Sayısı"].max() or 20), 0)

    st.markdown("---")
    if st.button("🔄 Filtreleri Sıfırla"):
        st.rerun()

# ─── BAŞLIK ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="baslik-kutu">
        <h1>⚽ Türkiye Kadınlar Süper Ligi 2025-2026</h1>
        <p>Sezon boyunca oynanan 30 haftanın oyuncu istatistikleri — maç katılımı ve gol verileri</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── İSTATİSTİK KARTLARI ─────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="stat-kart"><div class="sayi">{len(df_tam)}</div>'
        f'<div class="etiket">Toplam Oyuncu</div></div>',
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        f'<div class="stat-kart"><div class="sayi">{df_tam["Takım"].nunique()}</div>'
        f'<div class="etiket">Takım</div></div>',
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        f'<div class="stat-kart"><div class="sayi">{df_tam["Gol Sayısı"].sum()}</div>'
        f'<div class="etiket">Toplam Gol</div></div>',
        unsafe_allow_html=True,
    )
with k4:
    en_golcu = df_tam.loc[df_tam["Gol Sayısı"].idxmax(), "Oyuncu"] if not df_tam.empty else "—"
    st.markdown(
        f'<div class="stat-kart"><div class="sayi" style="font-size:1.1rem">{en_golcu}</div>'
        f'<div class="etiket">En Çok Gol Atan</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─── VERİ FİLTRELEME ─────────────────────────────────────────────────────────
df = df_tam.copy()

if arama:
    df = df[df["Oyuncu"].str.contains(arama, case=False, na=False)]

if secili_takim != "Tüm Takımlar":
    df = df[df["Takım"] == secili_takim]

df = df[df["Maç Sayısı"] >= min_mac]
df = df[df["Gol Sayısı"] >= min_gol]

# Sıralama
if siralama_kriteri == "Maç Sayısı (Azalan)":
    df = df.sort_values("Maç Sayısı", ascending=False)
elif siralama_kriteri == "Gol Sayısı (Azalan)":
    df = df.sort_values("Gol Sayısı", ascending=False)
else:
    df = df.sort_values("Oyuncu")

df = df.reset_index(drop=True)
df.index += 1  # 1'den başlat

# ─── SONUÇ BAŞLIĞI ───────────────────────────────────────────────────────────
t1, t2 = st.columns([3, 1])
with t1:
    st.markdown(f"### 📋 Oyuncu Listesi — {len(df)} Sonuç")
with t2:
    # CSV indirme butonu
    csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ CSV İndir",
        data=csv_bytes,
        file_name="filtreli_oyuncular.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ─── ANA TABLO ───────────────────────────────────────────────────────────────
if df.empty:
    st.info("🔎 Arama kriterlerinize uyan oyuncu bulunamadı.")
else:
    st.dataframe(
        df[["Oyuncu", "Takım", "Maç Sayısı", "Gol Sayısı"]],
        use_container_width=True,
        height=520,
        column_config={
            "Oyuncu": st.column_config.TextColumn("Oyuncu", width="medium"),
            "Takım": st.column_config.TextColumn("Takım", width="medium"),
            "Maç Sayısı": st.column_config.ProgressColumn(
                "Maç Sayısı",
                min_value=0,
                max_value=int(df_tam["Maç Sayısı"].max() or 30),
                format="%d",
            ),
            "Gol Sayısı": st.column_config.ProgressColumn(
                "Gol Sayısı",
                min_value=0,
                max_value=int(df_tam["Gol Sayısı"].max() or 20),
                format="%d",
            ),
        },
    )

# ─── GRAFİKLER ───────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
g1, g2 = st.columns(2)

with g1:
    st.markdown("#### 🥇 En Çok Gol Atan 10 Oyuncu")
    top_golcu = df_tam.nlargest(10, "Gol Sayısı")[["Oyuncu", "Takım", "Gol Sayısı"]]
    st.bar_chart(
        top_golcu.set_index("Oyuncu")["Gol Sayısı"],
        color="#00c853",
        height=300,
    )

with g2:
    st.markdown("#### 🏃 En Çok Maç Oynayan 10 Oyuncu")
    top_mac = df_tam.nlargest(10, "Maç Sayısı")[["Oyuncu", "Takım", "Maç Sayısı"]]
    st.bar_chart(
        top_mac.set_index("Oyuncu")["Maç Sayısı"],
        color="#2979ff",
        height=300,
    )

# ─── TAKIMA GÖRE GOL DAĞILIMI ────────────────────────────────────────────────
st.markdown("#### ⚽ Takım Bazlı Toplam Gol")
takim_gol = df_tam.groupby("Takım")["Gol Sayısı"].sum().sort_values(ascending=False)
st.bar_chart(takim_gol, color="#ff6d00", height=280)

# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="altbilgi">Veri kaynağı: TFF Resmi Web Sitesi — '
    'tff.org | 2025-2026 Sezonu Kadınlar Süper Ligi</div>',
    unsafe_allow_html=True,
)
