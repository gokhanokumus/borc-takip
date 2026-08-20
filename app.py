import sqlite3
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(page_title="BorçTakip", page_icon="💳", layout="centered")

# Veritabanı Bağlantısı
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

# Başlık
st.title("💳 BorçTakip")
st.caption("Borç, kredi kartı ve alacak ödeme takibi")

# Verileri Çekme
debts = c.execute(
    "SELECT * FROM debts WHERE status='Ödenmedi' ORDER BY due_date ASC"
).fetchall()
total_debt = sum([d[3] for d in debts]) if debts else 0.0
total_min = sum([d[4] for d in debts]) if debts else 0.0

urgent_count = 0
for d in debts:
    try:
        due_obj = datetime.strptime(d[6], "%Y-%m-%d").date()
        if 0 <= (due_obj - datetime.today().date()).days <= 7:
            urgent_count += 1
    except:
        pass

# 4 Özet Kartı
col1, col2 = st.columns(2)
with col1:
    st.metric(label="TOPLAM BORCUM", value=f"₺{total_debt:,.2f}")
    st.metric(label="BU DÖNEM ASGARİ", value=f"₺{total_min:,.2f}")

with col2:
    st.metric(label="TOPLAM ALACAĞIM", value="₺0,00")
    st.metric(label="7 GÜN İÇİNDE", value=f"{urgent_count} ödeme")

st.divider()

# Sekmeler
tab1, tab2, tab3, tab4 = st.tabs(
    ["🏠 Genel Bakış", "➕ Borç Ekle", "📜 Geçmiş", "📊 Grafik"]
)

with tab1:
    st.subheader("Yaklaşan Ödemeler")
    if debts:
        for d in debts:
            debt_id, bank, card, total, min_p, cutoff, due, status, debt_type = d

            try:
                days_left = (
                    datetime.strptime(due, "%Y-%m-%d").date()
                    - datetime.today().date()
                ).days
                kalan_txt = (
                    f"⏰ {days_left} gün kaldı"
                    if days_left >= 0
                    else f"🚨 {abs(days_left)} gün geçti"
                )
            except:
                kalan_txt = due

            with st.container(border=True):
                c_top1, c_top2 = st.columns([2, 1])
                c_top1.markdown(f"### {bank}")
                c_top1.caption(f"{debt_type} • {card}")
                c_top2.info(kalan_txt)

                st.markdown(f"## ₺{total:,.2f}")

                cd1, cd2 = st.columns(2)
                cd1.write(f"**Dönem borcu:** ₺{total:,.2f}\n\n**Kesim:** {cutoff}")
                cd2.write(f"**Asgari:** ₺{min_p:,.2f}\n\n**Son ödeme:** {due}")

                b1, b2 = st.columns(2)
                if b1.button("✅ Öde", key=f"pay_{debt_id}"):
                    c.execute(
                        "UPDATE debts SET status='Ödendi' WHERE id=?", (debt_id,)
                    )
                    conn.commit()
                    st.rerun()

                if b2.button("🗑️ Sil", key=f"del_{debt_id}"):
                    c.execute("DELETE FROM debts WHERE id=?", (debt_id,))
                    conn.commit()
                    st.rerun()
    else:
        st.info("Kayıtlı borç bulunmuyor.")

with tab2:
    st.subheader("Yeni Borç Ekle")
    with st.form("add_form"):
        bank_in = st.text_input("Banka / Kurum Adı")
        type_in = st.selectbox(
            "Borç Türü", ["Kredi Kartı", "Kira", "Kredi Taksidi", "Fatura"]
        )
        card_in = st.text_input("Kart / Detay Adı (Örn: Axess)")
        total_in = st.number_input("Toplam Borç (₺)", min_value=0.0, step=100.0)
        min_in = st.number_input("Asgari Ödeme (₺)", min_value=0.0, step=50.0)
        cutoff_in = st.date_input("Hesap Kesim Tarihi")
        due_in = st.date_input("Son Ödeme Tarihi")

        if st.form_submit_button("💾 Kaydet"):
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
            st.success("Borç eklendi!")
            st.rerun()

with tab3:
    st.subheader("Ödenen Borçlar")
    paid = c.execute("SELECT * FROM debts WHERE status='Ödendi'").fetchall()
    if paid:
        for p in paid:
            st.write(f"✔️ **{p[1]} ({p[2]})** - ₺{p[3]:,.2f} (Tarih: {p[6]})")
    else:
        st.info("Ödenmiş borç kaydı yok.")

with tab4:
    st.subheader("Borç Dağılımı")
    df = pd.read_sql_query(
        "SELECT bank_name, total_amount FROM debts WHERE status='Ödenmedi'",
        conn,
    )
    if not df.empty:
        fig = px.pie(
            df,
            values="total_amount",
            names="bank_name",
            hole=0.4,
            template="plotly_dark",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Grafik için veri bulunmuyor.")
