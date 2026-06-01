"""
Türkiye Kadınlar Süper Ligi 2025-2026 — Streamlit Web Arayüzü
"""
import json, os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Türkiye Kadınlar Süper Ligi 2025-2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background-color: #0f1117; color: #e0e0e0; }

.baslik-kutu {
    background: linear-gradient(135deg, #1a1f36 0%, #0d3b2e 100%);
    border-left: 5px solid #00c853;
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
}
.baslik-kutu h1 { color: #fff; font-size: 1.9rem; margin: 0 0 6px 0; }
.baslik-kutu p  { color: #a0aab4; margin: 0; font-size: 0.92rem; }

.stat-kart {
    background: #1a1f36;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
    border-top: 3px solid #00c853;
    margin-bottom: 8px;
}
.stat-kart .sayi   { font-size: 2rem; font-weight: 700; color: #00c853; }
.stat-kart .etiket { font-size: 0.78rem; color: #8899aa; margin-top: 4px; }

.profil-kart {
    background: #1a1f36;
    border-radius: 14px;
    padding: 24px 28px;
    border-left: 4px solid #00c853;
}
.profil-kart h2 { color: #fff; margin: 0 0 4px 0; font-size: 1.4rem; }
.profil-kart .takim-adi { color: #00c853; font-size: 0.9rem; margin-bottom: 16px; }
.profil-stat { display: flex; gap: 16px; flex-wrap: wrap; }
.profil-stat-item {
    background: #0f1117;
    border-radius: 8px;
    padding: 12px 18px;
    text-align: center;
    min-width: 80px;
}
.profil-stat-item .deger { font-size: 1.6rem; font-weight: 700; color: #00c853; }
.profil-stat-item .ad    { font-size: 0.72rem; color: #8899aa; margin-top: 2px; }

.karsilastirma-baslik {
    font-size: 1rem;
    font-weight: 600;
    color: #00c853;
    text-align: center;
    padding: 8px;
    background: #0d3b2e;
    border-radius: 8px;
    margin-bottom: 12px;
}
section[data-testid="stSidebar"] { background-color: #12161f; }
.altbilgi {
    text-align: center; color: #505870; font-size: 0.78rem;
    margin-top: 40px; padding-top: 16px;
    border-top: 1px solid #1e2340;
}
</style>
""", unsafe_allow_html=True)

# ─── VERİ ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def veri_yukle():
    if os.path.exists("oyuncular.json"):
        with open("oyuncular.json", encoding="utf-8") as f:
            liste = json.load(f)
        df = pd.DataFrame(liste)
    else:
        st.warning("oyuncular.json bulunamadı — demo veri kullanılıyor.")
        demo = [
            {"oyuncu":"Büşra Kılıç","takim":"Beşiktaş","mac_sayisi":28,"gol_sayisi":12,"gol_ort":0.43,"sari_kart":3,"kirmizi_kart":0,"toplam_dakika":2450},
            {"oyuncu":"Ezgi Koçak","takim":"Galatasaray","mac_sayisi":27,"gol_sayisi":9,"gol_ort":0.33,"sari_kart":1,"kirmizi_kart":0,"toplam_dakika":2200},
        ]
        df = pd.DataFrame(demo)

    # Sütun adlarını normalize et
    yeniden = {
        "oyuncu":"Oyuncu","takim":"Takım","mac_sayisi":"Maç",
        "gol_sayisi":"Gol","gol_ort":"Gol/Maç",
        "sari_kart":"Sarı","kirmizi_kart":"Kırmızı","toplam_dakika":"Dakika",
    }
    df.rename(columns=yeniden, inplace=True)
    for s in ["Maç","Gol","Sarı","Kırmızı","Dakika"]:
        if s not in df.columns: df[s] = 0
        df[s] = pd.to_numeric(df[s], errors="coerce").fillna(0).astype(int)
    if "Gol/Maç" not in df.columns:
        df["Gol/Maç"] = (df["Gol"] / df["Maç"].replace(0,1)).round(2)
    df["Gol/Maç"] = pd.to_numeric(df["Gol/Maç"], errors="coerce").fillna(0.0).round(2)
    return df

df_tam = veri_yukle()

# ─── BAŞLIK ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="baslik-kutu">
  <h1>⚽ Türkiye Kadınlar Süper Ligi 2025-2026</h1>
  <p>30 haftanın tüm oyuncu istatistikleri — maç, gol, kart ve dakika verileri</p>
</div>
""", unsafe_allow_html=True)

# ─── ÖZET KARTLAR ─────────────────────────────────────────────────────────────
k1,k2,k3,k4,k5 = st.columns(5)
en_golcu = df_tam.loc[df_tam["Gol"].idxmax(),"Oyuncu"] if not df_tam.empty else "—"
for kol, sayi, etiket in [
    (k1, len(df_tam),              "Toplam Oyuncu"),
    (k2, df_tam["Takım"].nunique(),"Takım"),
    (k3, df_tam["Gol"].sum(),      "Toplam Gol"),
    (k4, df_tam["Sarı"].sum(),     "Sarı Kart"),
    (k5, df_tam["Kırmızı"].sum(),  "Kırmızı Kart"),
]:
    kol.markdown(
        f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
        f'<div class="etiket">{etiket}</div></div>',
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─── SEKMELER ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Oyuncu Listesi", "👤 Oyuncu Profili", "🆚 Takım Karşılaştırması"])

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 1 — OYUNCU LİSTESİ
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    f1, f2, f3 = st.columns([2, 2, 1])

    with f1:
        # Autocomplete arama — selectbox + "Tümü" seçeneği
        secenekler = ["— Tüm oyuncular —"] + sorted(df_tam["Oyuncu"].tolist())
        secili_oyuncu = st.selectbox(
            "Oyuncu Ara",
            secenekler,
            help="Yazmaya başlayın — dropdown filtreler"
        )

    with f2:
        takimlar = ["Tüm Takımlar"] + sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_takim = st.selectbox("Takım", takimlar)

    with f3:
        siralama = st.selectbox("Sırala", ["Maç ↓", "Gol ↓", "Dakika ↓", "Sarı Kart ↓", "Gol/Maç ↓"])

    # Filtrele
    df = df_tam.copy()
    if secili_oyuncu != "— Tüm oyuncular —":
        df = df[df["Oyuncu"] == secili_oyuncu]
    if secili_takim != "Tüm Takımlar":
        df = df[df["Takım"] == secili_takim]

    # Sırala
    siralama_map = {
        "Maç ↓": "Maç", "Gol ↓": "Gol", "Dakika ↓": "Dakika",
        "Sarı Kart ↓": "Sarı", "Gol/Maç ↓": "Gol/Maç"
    }
    df = df.sort_values(siralama_map[siralama], ascending=False).reset_index(drop=True)
    df.index += 1

    bas, ind = st.columns([3,1])
    with bas:
        st.markdown(f"#### {len(df)} oyuncu listeleniyor")
    with ind:
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ CSV İndir", csv_bytes, "filtreli.csv", "text/csv", use_container_width=True)

    max_gol = int(df_tam["Gol"].max() or 1)
    max_mac = int(df_tam["Maç"].max() or 1)
    max_dk  = int(df_tam["Dakika"].max() or 1)

    st.dataframe(
        df[["Oyuncu","Takım","Maç","Gol","Gol/Maç","Sarı","Kırmızı","Dakika"]],
        use_container_width=True,
        height=540,
        column_config={
            "Oyuncu":   st.column_config.TextColumn("Oyuncu",  width="medium"),
            "Takım":    st.column_config.TextColumn("Takım",   width="medium"),
            "Maç":      st.column_config.ProgressColumn("Maç",     min_value=0, max_value=max_mac, format="%d"),
            "Gol":      st.column_config.ProgressColumn("Gol",     min_value=0, max_value=max_gol, format="%d"),
            "Gol/Maç":  st.column_config.NumberColumn("Gol/Maç", format="%.2f"),
            "Sarı":     st.column_config.NumberColumn("🟨 Sarı"),
            "Kırmızı":  st.column_config.NumberColumn("🟥 Kırmızı"),
            "Dakika":   st.column_config.ProgressColumn("Dakika", min_value=0, max_value=max_dk, format="%d dk"),
        }
    )

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 2 — OYUNCU PROFİLİ
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    oyuncu_listesi = sorted(df_tam["Oyuncu"].tolist())
    secili = st.selectbox("Oyuncu seç", oyuncu_listesi, key="profil_sec",
                          help="Yazmaya başlayın — isim filtrelenir")

    if secili:
        row = df_tam[df_tam["Oyuncu"] == secili].iloc[0]
        mac  = int(row["Maç"])
        gol  = int(row["Gol"])
        sari = int(row["Sarı"])
        kir  = int(row["Kırmızı"])
        dk   = int(row["Dakika"])
        ort  = round(gol / mac, 2) if mac else 0
        dk_mac = round(dk / mac, 0) if mac else 0

        st.markdown(f"""
        <div class="profil-kart">
          <h2>{secili}</h2>
          <div class="takim-adi">🏟 {row['Takım']}</div>
          <div class="profil-stat">
            <div class="profil-stat-item"><div class="deger">{mac}</div><div class="ad">Maç</div></div>
            <div class="profil-stat-item"><div class="deger">{gol}</div><div class="ad">Gol</div></div>
            <div class="profil-stat-item"><div class="deger">{ort}</div><div class="ad">Gol/Maç</div></div>
            <div class="profil-stat-item"><div class="deger">{dk}</div><div class="ad">Toplam Dk</div></div>
            <div class="profil-stat-item"><div class="deger">{int(dk_mac)}</div><div class="ad">Dk/Maç</div></div>
            <div class="profil-stat-item"><div class="deger" style="color:#f5c518">{sari}</div><div class="ad">Sarı Kart</div></div>
            <div class="profil-stat-item"><div class="deger" style="color:#e53935">{kir}</div><div class="ad">Kırmızı Kart</div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Listedeki sıralamalar
        st.markdown("#### Lig Sıralamaları")
        r1, r2, r3, r4 = st.columns(4)
        for kol, metrik, etiket in [
            (r1, "Gol",     "Gol sıralaması"),
            (r2, "Maç",     "Maç sıralaması"),
            (r3, "Dakika",  "Dakika sıralaması"),
            (r4, "Sarı",    "Sarı kart sıralaması"),
        ]:
            siralama_df = df_tam.sort_values(metrik, ascending=False).reset_index(drop=True)
            siralama_df.index += 1
            lig_sirasi = siralama_df[siralama_df["Oyuncu"] == secili].index
            sira = int(lig_sirasi[0]) if len(lig_sirasi) > 0 else "—"
            kol.metric(etiket, f"{sira}. / {len(df_tam)}")

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 3 — TAKIM KARŞILAŞTIRMASI
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    takimlar_liste = sorted(df_tam["Takım"].dropna().unique().tolist())

    c1, c2 = st.columns(2)
    with c1:
        takim1 = st.selectbox("1. Takım", takimlar_liste, key="t1")
    with c2:
        varsayilan2 = takimlar_liste[1] if len(takimlar_liste) > 1 else takimlar_liste[0]
        takim2 = st.selectbox("2. Takım", takimlar_liste,
                              index=takimlar_liste.index(varsayilan2), key="t2")

    df1 = df_tam[df_tam["Takım"] == takim1]
    df2 = df_tam[df_tam["Takım"] == takim2]

    st.markdown("<br>", unsafe_allow_html=True)

    # Takım özet istatistikleri
    def takim_ozet(df, takim_adi, renk):
        toplam_gol = int(df["Gol"].sum())
        toplam_mac = int(df["Maç"].sum())
        toplam_dk  = int(df["Dakika"].sum())
        toplam_sari= int(df["Sarı"].sum())
        oyuncu_say = len(df)
        ort_gol    = round(df["Gol"].sum() / max(df["Maç"].sum(),1), 2)
        return {
            "Toplam Gol": toplam_gol,
            "Toplam Maç (oyuncu×maç)": toplam_mac,
            "Toplam Dakika": toplam_dk,
            "Sarı Kart": toplam_sari,
            "Kadro Büyüklüğü": oyuncu_say,
            "Gol/Maç Ortalaması": ort_gol,
        }

    oz1 = takim_ozet(df1, takim1, "#00c853")
    oz2 = takim_ozet(df2, takim2, "#2979ff")

    sol, orta, sag = st.columns([5, 1, 5])

    with sol:
        st.markdown(f'<div class="karsilastirma-baslik">{takim1}</div>', unsafe_allow_html=True)
        for metrik, deger in oz1.items():
            st.metric(metrik, deger)

    with orta:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for metrik in oz1:
            v1 = oz1[metrik]
            v2 = oz2[metrik]
            if isinstance(v1, float):
                ikon = "🟢" if v1 >= v2 else "🔴"
            else:
                ikon = "🟢" if v1 >= v2 else "🔴"
            st.markdown(f"<div style='text-align:center;font-size:1.2rem;padding:14px 0'>{ikon}</div>",
                        unsafe_allow_html=True)

    with sag:
        st.markdown(f'<div class="karsilastirma-baslik">{takim2}</div>', unsafe_allow_html=True)
        for metrik, deger in oz2.items():
            st.metric(metrik, deger)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### En Çok Gol Atan Oyuncular")
    g1, g2 = st.columns(2)
    with g1:
        top1 = df1.nlargest(8,"Gol")[["Oyuncu","Gol","Maç","Dakika"]]
        st.dataframe(top1, use_container_width=True, hide_index=True)
    with g2:
        top2 = df2.nlargest(8,"Gol")[["Oyuncu","Gol","Maç","Dakika"]]
        st.dataframe(top2, use_container_width=True, hide_index=True)

# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="altbilgi">Veri kaynağı: TFF — tff.org | 2025-2026 Sezonu Kadınlar Süper Ligi</div>',
    unsafe_allow_html=True
)
