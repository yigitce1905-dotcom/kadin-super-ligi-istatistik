"""
Türkiye Kadınlar Süper Ligi 2025-2026 — Streamlit Web Arayüzü
"""
import json, os, requests
import pandas as pd
import plotly.graph_objects as go
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
    if not os.path.exists("oyuncular.json"):
        st.warning("oyuncular.json bulunamadı.")
        return pd.DataFrame(), []
    with open("oyuncular.json", encoding="utf-8") as f:
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
st.markdown("""
<div class="baslik-kutu">
  <h1>⚽ Türkiye Kadınlar Süper Ligi 2025-2026</h1>
  <p>30 haftanın tüm oyuncu istatistikleri — maç, gol, kart, dakika, forma ve karşılaştırma</p>
</div>""", unsafe_allow_html=True)

# ─── ÖZET KARTLAR ─────────────────────────────────────────────────────────────
if not df_tam.empty:
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    en_golcu = df_tam.loc[df_tam["Gol"].idxmax(),"Oyuncu"]
    transfer_say = int(df_tam["Transfer"].sum())
    for kol, sayi, etiket in [
        (k1, len(df_tam),             "Oyuncu"),
        (k2, df_tam["Takım"].nunique(),"Takım"),
        (k3, int(df_tam["Gol"].sum()), "Toplam Gol"),
        (k4, int(df_tam["GolP"].sum()),   "Penaltı Golü"),
        (k5, int(df_tam["Sarı"].sum()), "Sarı Kart"),
        (k6, transfer_say,             "Transfer"),
    ]:
        kol.markdown(
            f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
            f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── SEKMELER ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Oyuncu Listesi", "👤 Oyuncu Profili",
    "⚡ Karşılaştırma",  "🏆 Lig Tablosu", "🌟 En İyiler"
])

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 1 — OYUNCU LİSTESİ
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if df_tam.empty:
        st.info("Veri yok."); st.stop()

    f1, f2, f3 = st.columns([2, 2, 1])
    with f1:
        secenekler = ["— Tüm oyuncular —"] + sorted(df_tam["Oyuncu"].tolist())
        secili_oyuncu = st.selectbox("Oyuncu Ara", secenekler,
            index=secenekler.index(url_oyuncu) if url_oyuncu in secenekler else 0)
    with f2:
        takimlar = ["Tüm Takımlar"] + sorted(df_tam["Takım"].dropna().unique().tolist())
        secili_takim = st.selectbox("Takım", takimlar)
    with f3:
        siralama = st.selectbox("Sırala", ["Maç ↓","Gol ↓","Dakika ↓","Sarı ↓","Gol/Maç ↓"])

    df = df_tam.copy()
    if secili_oyuncu != "— Tüm oyuncular —":
        df = df[df["Oyuncu"] == secili_oyuncu]
    if secili_takim != "Tüm Takımlar":
        df = df[df["TümTakımlar"].str.contains(secili_takim, na=False)]

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

    st.dataframe(
        df[["Oyuncu","Takım (Gösterim)","Maç","İlk11","Yedek",
            "Gol","GolF","GolH","GolP","Gol/Maç","Sarı","Kırmızı","Dakika"]],
        use_container_width=True, height=520,
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

        st.markdown(f"""
        <div class="profil-kart">
          <h2>{secili}</h2>
          <div style="margin-bottom:14px">🏟 {takim_html}</div>
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
    secili_oyuncular = st.multiselect(
        "Karşılaştırılacak oyuncuları seç (2-4)",
        oyuncu_listesi2,
        default=oyuncu_listesi2[:2] if len(oyuncu_listesi2) >= 2 else oyuncu_listesi2,
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
# SEKME 4 — LİG TABLOSU
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
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
# SEKME 5 — EN İYİLER
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 🌟 2025-2026 Sezonu En İyileri")
    if df_tam.empty:
        st.info("Veri yok.")
    else:
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
            en_iyi_kart("Gol Krallığı",
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

# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="altbilgi">Veri kaynağı: TFF — tff.org | 2025-2026 Kadınlar Süper Ligi</div>',
    unsafe_allow_html=True)
