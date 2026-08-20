import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# Sayfa Yapılandırması (Mobil & Dark Mode)
st.set_page_config(
    page_title="BorçTakip",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Dark Theme & Mobil Arayüz CSS (Görsellerdeki Tasarım)
st.markdown(
    """
    <style>
    /* Arka Plan ve Koyu Tema */
    .stApp {
        background-color: #121824;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Üst Başlık */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0 20px 0;
    }
    .app-title {
        font-size: 24px;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .app-subtitle {
        font-size: 13px;
        color: #8a99ad;
        margin-top: 2px;
    }

    /* 4'lü Özet Metrik Kartları */
    .metrics-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 24px;
    }
    .metric-card {
        background-color: #1e2638;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #2a354d;
    }
    .metric-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        color: #8a99ad;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value-red {
        font-size: 20px;
        font-weight: 800;
        color: #ff5260;
    }
    .metric-value-green {
        font-size: 20px;
        font-weight: 800;
        color: #00e676;
    }
    .metric-value-orange {
        font-size: 20px;
        font-weight: 800;
        color: #ffb300;
    }
    .metric-value-blue {
        font-size: 20px;
        font-weight: 800;
        color: #00e5ff;
    }

    /* Yaklaşan Ödemeler Kartı */
    .debt-card {
        background-color: #1e2638;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 16px;
        border: 1px solid #2a354d;
        position: relative;
    }
    .bank-badge {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .bank-name {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
    }
    .tag-type {
        background-color: #2a354d;
        color: #8a99ad;
        font-size: 11px;
        padding: 3px 8px;
        border-radius: 6px;
        margin-left: 6px;
    }
    .days-badge {
        background-color: rgba(255, 179, 0, 0.15);
        color: #ffb300;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 12px;
    }
    .days-badge-urgent {
        background-color: rgba(255, 82, 96, 0.15);
        color: #ff5260;
        font-size: 12px;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 12px;
    }

    .amount-main {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        margin: 8px 0 16px 0;
    }
    .details-grid {
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        color: #8a99ad;
        border-top: 1px solid #2a354d;
        padding-top: 12px;
        margin-top: 12px;
    }

    /* Alt Tab Menüsü */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #1e2638;
        padding: 6px;
        border-radius: 16px;
        border: 1px solid #2a354d;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 12px;
        color: #8a99ad;
        font-weight: 600;
        font-size: 13px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2a3859 !important;
        color: #00e5ff !important;
    }

    /* Butonlar */
    .stButton > button {
        border-radius: 12px;
        background-color: #00e5ff15;
        color: #00e5ff;
        border: 1px solid #00e5ff40;
        font-weight: 600;
        height: 42px;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #00e5ff30;
        color: #ffffff;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Veritabanı Kurulumu
conn = sqlite3.connect("debts.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name TEXT,
    card_name TEXT,
    total_amount REAL,
    min_amount REAL,
    cutoff_date TEXT,
    due_date TEXT,
    status TEXT DEFAULT 'Ödenmedi',
    debt_type TEXT DEFAULT 'Kredi Kartı'
)
""")
conn.commit()

# --- ÜST BAŞLIK ---
st.markdown(
    """
<div class="app-header">
    <div>
        <div class="app-title">👛 BorçTakip</div>
        <div class="app-subtitle">Borç, kredi kartı ve alacak ödeme takibi</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# --- VERİ VE HESAPLAMALAR ---
debts = c.execute(
    "SELECT * FROM debts WHERE status='Ödenmedi' ORDER BY due_date ASC"
).fetchall()
all_debts = c.execute("SELECT * FROM debts").fetchall()

total_debt = sum([d[3] for d in debts])
total_min = sum([d[4] for d in debts])

# 7 Gün içinde ödenmesi gerekenler
urgent_count = 0
for d in debts:
    due_obj = datetime.strptime(d[6], "%Y-%m-%d").date()
    days = (due_obj - datetime.today().date()).days
    if 0 <= days <= 7:
        urgent_count += 1

# --- 4'LÜ ÖZET METRİK KARTLARI ---
st.markdown(
    f"""
<div class="metrics-grid">
    <div class="metric-card">
        <div class="metric-label">TOPLAM BORCUM</div>
        <div class="metric-value-red">₺{total_debt:,.2f}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">TOPLAM ALACAĞIM</div>
        <div class="metric-value-green">₺0,00</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">BU DÖNEM ASGARİ</div>
        <div class="metric-value-orange">₺{total_min:,.2f}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">7 GÜN İÇİNDE</div>
        <div class="metric-value-blue">{urgent_count} ödeme</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# TAB MENÜSÜ
tab1, tab2, tab3, tab4 = st.tabs(
    ["🏠 Genel Bakış", "➕ Borç Ekle", "📜 Geçmiş", "📊 Grafik"]
)

# --- TAB 1: YAKLAŞAN ÖDEMELER ---
with tab1:
    st.markdown(
        "<h4 style='color:#ffffff; margin-bottom:16px;'>YAKLAŞAN ÖDEMELER</h4>",
        unsafe_allow_html=True,
    )

    if debts:
        for d in debts:
            (
                debt_id,
                bank,
                card,
                total,
                min_p,
                cutoff,
                due,
                status,
                debt_type,
            ) = d
            due_date_obj = datetime.strptime(due, "%Y-%m-%d").date()
            days_left = (due_date_obj - datetime.today().date()).days

            badge_style = "days-badge"
            badge_text = f"⏰ {days_left} gün kaldı"
            if days_left < 0:
                badge_style = "days-badge-urgent"
                badge_text = f"🚨 {abs(days_left)} gün geçti"
            elif days_left == 0:
                badge_style = "days-badge-urgent"
                badge_text = "⚠️ Bugün son gün"

            st.markdown(
                f"""
            <div class="debt-card">
                <div class="bank-badge">
                    <div>
                        <span class="bank-name">{bank}</span>
                        <span class="tag-type">{debt_type}</span>
                        <span class="tag-type">{card}</span>
                    </div>
                    <div class="{badge_style}">{badge_text}</div>
                </div>
                <div style="font-size:12px; color:#8a99ad;">KALAN</div>
                <div class="amount-main">₺{total:,.2f}</div>
                <div class="details-grid">
                    <div>
                        <div>Dönem borcu: <b style="color:#fff;">₺{total:,.2f}</b></div>
                        <div>Hesap kesim: {cutoff}</div>
                    </div>
                    <div style="text-align:right;">
                        <div>Asgari: <b style="color:#fff;">₺{min_p:,.2f}</b></div>
                        <div>Son ödeme: {due}</div>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)
            if col1.button("✅ Ödeme Ekle", key=f"pay_{debt_id}"):
                c.execute(
                    "UPDATE debts SET status='Ödendi' WHERE id=?", (debt_id,)
                )
                conn.commit()
                st.rerun()
            if col2.button("🗑️ Sil", key=f"del_{debt_id}"):
                c.execute("DELETE FROM debts WHERE id=?", (debt_id,))
                conn.commit()
                st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Yaklaşan veya ödenmemiş borcunuz bulunmuyor.")

# --- TAB 2: YENİ BORÇ EKLEME ---
with tab2:
    st.markdown(
        "<h4 style='color:#ffffff; margin-bottom:16px;'>Yeni Borç Kaydı</h4>",
        unsafe_allow_html=True,
    )
    with st.form("add_debt"):
        bank_in = st.text_input("Banka / Kurum Adı", placeholder="Örn: Akbank")
        type_in = st.selectbox(
            "Borç Türü", ["Kredi Kartı", "Kira", "Kredi Taksidi", "Fatura"]
        )
        card_in = st.text_input(
            "Kart/Detay Adı", placeholder="Örn: Axess / World"
        )
        total_in = st.number_input(
            "Kalan / Dönem Borcu (₺)", min_value=0.0, step=100.0
        )
        min_in = st.number_input(
            "Asgari Ödeme Tutarı (₺)", min_value=0.0, step=50.0
        )
        cutoff_in = st.date_input("Hesap Kesim Tarihi")
        due_in = st.date_input("Son Ödeme Tarihi")

        if st.form_submit_button("💾 Borcu Kaydet"):
            c.execute(
                """
            INSERT INTO debts (bank_name, card_name, total_amount, min_amount, cutoff_date, due_date, debt_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    bank_in,
                    card_in,
                    total_in,
                    min_in,
                    cutoff_in.strftime("%Y-%m-%d"),
                    due_in.strftime("%Y-%m-%d"),
                    type_in,
                ),
            )
            conn.commit()
            st.toast("Borç başarıyla eklendi!", icon="✅")
            st.rerun()

# --- TAB 3: GEÇMİŞ / ÖDENENLER ---
with tab3:
    st.markdown(
        "<h4 style='color:#ffffff; margin-bottom:16px;'>Ödenen Borçlar</h4>",
        unsafe_allow_html=True,
    )
    paid_debts = c.execute(
        "SELECT * FROM debts WHERE status='Ödendi'"
    ).fetchall()
    if paid_debts:
        for p in paid_debts:
            st.markdown(
                f"""
            <div class="debt-card" style="opacity:0.7;">
                <div class="bank-badge">
                    <div>
                        <b style="color:#fff;">{p[1]}</b> - {p[2]}
                    </div>
                    <span style="color:#00e676; font-size:12px; font-weight:700;">● ÖDENDİ</span>
                </div>
                <div style="font-size:18px; font-weight:700; color:#fff;">₺{p[3]:,.2f}</div>
                <div style="font-size:12px; color:#8a99ad; margin-top:6px;">Son Ödeme: {p[6]}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Henüz ödenmiş borç geçmişi yok.")

# --- TAB 4: GRAFİK VE ANALİZ ---
with tab4:
    st.markdown(
        "<h4 style='color:#ffffff; margin-bottom:16px;'>Borç Dağılımı</h4>",
        unsafe_allow_html=True,
    )
    df = pd.read_sql_query(
        "SELECT bank_name, total_amount FROM debts WHERE status='Ödenmedi'",
        conn,
    )
    if not df.empty:
        fig = px.pie(
            df,
            values="total_amount",
            names="bank_name",
            hole=0.6,
            color_discrete_sequence=px.colors.qualitative.Dark24,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ffffff",
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Grafik için veri bekleniyor.")
