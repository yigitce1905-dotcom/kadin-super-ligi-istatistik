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
    """TFF'den Kadınlar Süper Ligi puan durumunu çeker."""
    url = "https://www.tff.org/Default.aspx?pageID=1000&hafta=30"
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.content, "lxml")
        for tablo in soup.find_all("table"):
            txt = tablo.get_text()
            if "Puan" in txt and "O" in txt and "G" in txt:
                satirlar = []
                for tr in tablo.find_all("tr"):
                    hücreler = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
                    if hücreler: satirlar.append(hücreler)
                if len(satirlar) > 3:
                    return satirlar
    except Exception:
        pass
    return []


df_tam, ham_liste = veri_yukle()
oyuncu_detay = {o["oyuncu"]: o for o in ham_liste} if ham_liste else {}

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
        (k4, int(df_tam["Penaltı"].sum()),"Penaltı Golü"),
        (k5, int(df_tam["Sarı"].sum()), "Sarı Kart"),
        (k6, transfer_say,             "Transfer"),
    ]:
        kol.markdown(
            f'<div class="stat-kart"><div class="sayi">{sayi}</div>'
            f'<div class="etiket">{etiket}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── SEKMELER ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Oyuncu Listesi", "👤 Oyuncu Profili",
    "⚡ Karşılaştırma",  "🏆 Lig Tablosu"
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

        # ── Haftalık performans grafiği ───────────────────────────────────────
        st.markdown("##### Haftalık Performans")
        gecmis_tam = sorted(detay.get("mac_gecmisi",[]), key=lambda x: x["hafta"])
        if gecmis_tam:
            haftalar = [m["hafta"] for m in gecmis_tam]
            dakikalar = [m["dakika"] for m in gecmis_tam]
            goller    = [m["gol"]   for m in gecmis_tam]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=haftalar, y=dakikalar, name="Dakika",
                marker_color="#2979ff", opacity=0.7,
                hovertemplate="Hafta %{x}<br>%{y} dakika<extra></extra>"
            ))
            fig.add_trace(go.Scatter(
                x=haftalar, y=[g*20 for g in goller], name="Gol (×20)",
                mode="markers", marker=dict(color="#00c853", size=12, symbol="star"),
                hovertemplate="Hafta %{x}<br>Gol: %{customdata}<extra></extra>",
                customdata=goller
            ))
            fig.update_layout(
                paper_bgcolor="#0f1117", plot_bgcolor="#1a1f36",
                font=dict(color="#e0e0e0"), height=280,
                legend=dict(orientation="h", y=1.1),
                xaxis=dict(title="Hafta", gridcolor="#2d3561"),
                yaxis=dict(title="Dakika", gridcolor="#2d3561"),
                margin=dict(l=40,r=20,t=20,b=40)
            )
            st.plotly_chart(fig, use_container_width=True)

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

# ══════════════════════════════════════════════════════════════════════════════
# SEKME 3 — KARŞILAŞTIRMA
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Oyuncu Karşılaştırması")
    c1, c2 = st.columns(2)
    oyuncu_listesi2 = sorted(df_tam["Oyuncu"].tolist())
    with c1:
        oy1 = st.selectbox("1. Oyuncu", oyuncu_listesi2, key="k1")
    with c2:
        oy2 = st.selectbox("2. Oyuncu", oyuncu_listesi2,
                           index=min(1, len(oyuncu_listesi2)-1), key="k2")

    if oy1 and oy2 and not df_tam.empty:
        def radar_deger(oyuncu, metrik):
            r = df_tam[df_tam["Oyuncu"] == oyuncu]
            if r.empty: return 0
            val = float(r.iloc[0].get(metrik, 0))
            maks = float(df_tam[metrik].max())
            return round(val / maks * 100, 1) if maks else 0

        kategoriler = ["Maç", "Gol", "Gol/Maç", "Dakika", "İlk11 %", "Sarı (ters)"]

        def degerler(oyuncu):
            r = df_tam[df_tam["Oyuncu"] == oyuncu].iloc[0]
            mac   = int(r["Maç"])
            return [
                radar_deger(oyuncu, "Maç"),
                radar_deger(oyuncu, "Gol"),
                radar_deger(oyuncu, "Gol/Maç"),
                radar_deger(oyuncu, "Dakika"),
                round(int(r["İlk11"]) / mac * 100, 1) if mac else 0,
                round(100 - radar_deger(oyuncu, "Sarı"), 1),  # ters: az kart iyi
            ]

        d1 = degerler(oy1)
        d2 = degerler(oy2)

        fig = go.Figure()
        for oyuncu, dg, renk in [(oy1, d1, "#00c853"), (oy2, d2, "#2979ff")]:
            fig.add_trace(go.Scatterpolar(
                r=dg + [dg[0]], theta=kategoriler + [kategoriler[0]],
                fill="toself", name=oyuncu,
                line=dict(color=renk, width=2),
                fillcolor=renk.replace("#","") and renk,
                opacity=0.25 if oyuncu == oy2 else 0.3,
            ))
        fig.update_layout(
            polar=dict(
                bgcolor="#1a1f36",
                radialaxis=dict(visible=True, range=[0,100], gridcolor="#2d3561",
                                tickfont=dict(color="#8899aa"), tickvals=[25,50,75,100]),
                angularaxis=dict(tickfont=dict(color="#e0e0e0"), gridcolor="#2d3561")
            ),
            paper_bgcolor="#0f1117", font=dict(color="#e0e0e0"),
            legend=dict(orientation="h", y=-0.1),
            height=450, margin=dict(l=60,r=60,t=40,b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Sayısal karşılaştırma
        st.markdown("##### Sayısal Karşılaştırma")
        r1_row = df_tam[df_tam["Oyuncu"] == oy1].iloc[0]
        r2_row = df_tam[df_tam["Oyuncu"] == oy2].iloc[0]
        metrikler = ["Maç","İlk11","Yedek","Gol","GolF","GolH","GolP","Gol/Maç","Sarı","Kırmızı","Dakika"]

        sol, orta, sag = st.columns([5,1,5])
        with sol:
            st.markdown(f'<div style="text-align:center;font-weight:700;color:#00c853;padding:8px;background:#0d3b2e;border-radius:8px;margin-bottom:10px">{oy1}</div>', unsafe_allow_html=True)
            for m in metrikler:
                v1 = r1_row.get(m,0); v2 = r2_row.get(m,0)
                delta = float(v1) - float(v2) if m != "Sarı" else 0
                st.metric(m, v1, delta=round(delta,2) if delta else None,
                          delta_color="normal" if m not in ("Sarı","Kırmızı") else "inverse")
        with orta:
            st.markdown("<br><br>", unsafe_allow_html=True)
            for m in metrikler:
                v1 = float(r1_row.get(m,0)); v2 = float(r2_row.get(m,0))
                ikon = "🟢" if v1 > v2 else ("🟡" if v1 == v2 else "🔴")
                if m in ("Sarı","Kırmızı"): ikon = "🟢" if v1 <= v2 else "🔴"
                st.markdown(f'<div style="text-align:center;font-size:1.1rem;padding:18px 0">{ikon}</div>', unsafe_allow_html=True)
        with sag:
            st.markdown(f'<div style="text-align:center;font-weight:700;color:#2979ff;padding:8px;background:#0a1a3a;border-radius:8px;margin-bottom:10px">{oy2}</div>', unsafe_allow_html=True)
            for m in metrikler:
                st.metric(m, r2_row.get(m,0))

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

        # TFF'den puan durumu dene
        with st.spinner("TFF puan durumu yükleniyor..."):
            puan = puan_durumu_cek()
        if puan:
            st.markdown("#### TFF Puan Durumu")
            try:
                baslik = puan[0]
                satirlar = puan[1:]
                df_puan = pd.DataFrame(satirlar, columns=baslik[:len(satirlar[0])])
                st.dataframe(df_puan, use_container_width=True, hide_index=True)
            except Exception:
                st.caption("Puan durumu tablosu parse edilemedi.")
        else:
            st.caption("TFF puan durumu tablosu bu sayfada bulunamadı.")

# ─── ALTBİLGİ ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="altbilgi">Veri kaynağı: TFF — tff.org | 2025-2026 Kadınlar Süper Ligi</div>',
    unsafe_allow_html=True)
