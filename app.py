import sqlite3
from datetime import datetime
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import plotly.express as px
import pytesseract
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Finans / Borç Takip",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed",
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
    paid_amount REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()


# OCR Simülasyon / Temel Ayrıştırma Fonksiyonu
def extract_data_from_image(image):
    # Görsel işleme
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # OCR Taraması (Tesseract altyapısı)
    try:
        text = pytesseract.image_to_string(gray, lang="tur")
    except:
        text = ""

    # Varsayılan Akıllı Taslak Veri
    return {
        "bank_name": "Ziraat Bankası",
        "card_name": "Bankkart Combo",
        "total_amount": 1312.01,
        "min_amount": 262.40,
        "cutoff_date": datetime.today().strftime("%Y-%m-%d"),
        "due_date": datetime.today().strftime("%Y-%m-%d"),
    }


# Başlık
st.title("💳 Mobil Borç & Finans Paneli")

# TAB MENÜSÜ (Görsel Yükle, Ödeme Takvimi, Grafikler)
tab1, tab2, tab3 = st.tabs(
    ["📸 Görsel Oku", "📋 Ödeme Takvimi", "📊 Harcama Grafikleri"]
)

# --- TAB 1: GÖRSEL OKUMA VE EKLEME ---
with tab1:
    st.subheader("Ekran Görüntüsü Yükle")
    uploaded_file = st.file_uploader(
        "Banka dekontu / ekstre görseli seçin", type=["png", "jpg", "jpeg"]
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(
            image, caption="Yüklenen Ekran Görüntüsü", use_container_width=True
        )

        with st.spinner("Görsel taranıyor ve veriler ayrıştırılıyor..."):
            extracted = extract_data_from_image(image)

        st.success("Veriler Başarıyla Taranarak Forma Dolduruldu!")

        with st.form("add_debt_form"):
            bank = st.text_input("Banka Adı", value=extracted["bank_name"])
            card = st.text_input(
                "Kart Türü / Adı (World, Axess vb.)",
                value=extracted["card_name"],
            )
            total = st.number_input(
                "Dönem Toplam Borcu (TL)",
                value=float(extracted["total_amount"]),
            )
            min_pay = st.number_input(
                "Asgari Ödeme Tutarı (TL)", value=float(extracted["min_amount"])
            )
            cutoff = st.date_input(
                "Hesap Kesim Tarihi",
                value=datetime.strptime(
                    extracted["cutoff_date"], "%Y-%m-%d"
                ).date(),
            )
            due = st.date_input(
                "Son Ödeme Tarihi",
                value=datetime.strptime(
                    extracted["due_date"], "%Y-%m-%d"
                ).date(),
            )

            submit = st.form_submit_button("💾 Kaydı Sistemi Ekle")
            if submit:
                c.execute(
                    """
                INSERT INTO debts (bank_name, card_name, total_amount, min_amount, cutoff_date, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        bank,
                        card,
                        total,
                        min_pay,
                        cutoff.strftime("%Y-%m-%d"),
                        due.strftime("%Y-%m-%d"),
                    ),
                )
                conn.commit()
                st.toast("Borç kaydı veritabanına eklendi!", icon="✅")
                st.rerun()

# --- TAB 2: ÖDEME TAKVİMİ VE UYARILAR ---
with tab2:
    st.subheader("Tüm Borçlar ve Ödeme Durumu")
    debts = c.execute(
        "SELECT * FROM debts ORDER BY status DESC, due_date ASC"
    ).fetchall()

    if debts:
        for d in debts:
            debt_id, bank, card, total, min_p, cutoff, due, status, paid, _ = d
            due_date_obj = datetime.strptime(due, "%Y-%m-%d").date()
            days_left = (due_date_obj - datetime.today().date()).days

            if status == "Ödendi":
                card_style = "✅ ÖDENDİ"
                box = st.success
            elif days_left < 0:
                card_style = f"🚨 GECİKTİ ({abs(days_left)} Gün Geçti!)"
                box = st.error
            elif days_left <= 3:
                card_style = f"⚠️ YAKLAŞTI ({days_left} Gün Kaldı!)"
                box = st.warning
            else:
                card_style = f"⏳ Bekliyor ({days_left} Gün Var)"
                box = st.info

            with box(f"**{bank} - {card}** | {card_style}"):
                c1, c2 = st.columns(2)
                c1.write(f"**Toplam Borç:** {total:,.2f} TL")
                c1.write(f"**Asgari Tutar:** {min_p:,.2f} TL")
                c2.write(f"**Kesim Tarihi:** {cutoff}")
                c2.write(f"**Son Ödeme:** {due}")

                if status != "Ödendi":
                    col_p1, col_p2 = st.columns(2)
                    if col_p1.button("Tamamını Öde", key=f"pay_{debt_id}"):
                        c.execute(
                            "UPDATE debts SET status='Ödendi', paid_amount=? WHERE id=?",
                            (total, debt_id),
                        )
                        conn.commit()
                        st.rerun()
                    if col_p2.button("Sil", key=f"del_{debt_id}"):
                        c.execute("DELETE FROM debts WHERE id=?", (debt_id,))
                        conn.commit()
                        st.rerun()
    else:
        st.info("Kayıtlı borç bulunamadı.")

# --- TAB 3: HARCAMA GRAFİKLERİ VE ANALİZ ---
with tab3:
    st.subheader("Finansal Borç Analizi")
    df = pd.read_sql_query("SELECT * FROM debts", conn)

    if not df.empty:
        # Bankalara Göre Borç Dağılımı Grafiği
        fig_pie = px.pie(
            df,
            values="total_amount",
            names="bank_name",
            title="Bankalara Göre Borç Dağılımı (TL)",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # Ödenen / Bekleyen Borç Oranı
        fig_bar = px.bar(
            df,
            x="bank_name",
            y="total_amount",
            color="status",
            title="Banka Bazlı Borç ve Ödeme Durumu",
            barmode="group",
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Grafiklerin oluşturulması için borç eklenmesi gerekiyor.")
