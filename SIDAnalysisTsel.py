import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# CONFIG
# ==============================
st.set_page_config(layout="wide", page_title="Dashboard Analisis Profile Sender ID (Telkomsel)")

st.title("📊 Dashboard Analisis Profile Sender ID (Telkomsel)")
st.markdown("Data otomatis diambil dari repository GitHub. Mohon tunggu beberapa saat untuk memuat data.")

# ==============================
# LOAD DATA FROM GITHUB (CACHED)
# ==============================
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/helmimauludii/SID-Profile-Analysis/main/Tsel%20SID%202025.xlsx"
    return pd.read_excel(url)

# ==============================
# DATA PROCESSING
# ==============================
try:
    df = load_data()

    # --- VALIDASI KOLOM ---
    required_cols = ['Time Stamp', 'Sender ID', 'Sent Messages', 'Delivered Messages']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Kolom berikut tidak ditemukan: {missing_cols}")
        st.stop()

    # --- CLEANING ---
    df['Time Stamp'] = pd.to_datetime(df['Time Stamp'], errors='coerce')
    df['Sender ID'] = df['Sender ID'].astype(str)

    df['Sent Messages'] = pd.to_numeric(df['Sent Messages'], errors='coerce')
    df['Delivered Messages'] = pd.to_numeric(df['Delivered Messages'], errors='coerce')

    df.dropna(subset=['Time Stamp', 'Sender ID', 'Sent Messages', 'Delivered Messages'], inplace=True)

    df['Sent Messages'] = df['Sent Messages'].fillna(0).astype(int)
    df['Delivered Messages'] = df['Delivered Messages'].fillna(0).astype(int)

    # ==============================
    # MONTH TRANSFORMATION
    # ==============================
    df['Month'] = df['Time Stamp'].dt.to_period('M')
    df['Month_str'] = df['Time Stamp'].dt.strftime('%B %Y')

except Exception as e:
    st.error(f"Terjadi kesalahan saat memproses data: {e}")
    st.stop()

# ==============================
# SIDEBAR FILTER
# ==============================
st.sidebar.header("⚙️ Filter Data")

sorted_months = sorted(df['Month'].unique())

# ✅ SIMPLIFIED MULTISELECT (tanpa checkbox)
selected_months = st.sidebar.multiselect(
    "Pilih Bulan:",
    options=sorted_months,
    default=sorted_months,
    format_func=lambda x: x.strftime('%B %Y'),
    placeholder="Pilih bulan..."
)

selected_metric = st.sidebar.radio(
    "Pilih Metrik:",
    options=['Delivered Messages', 'Sent Messages']
)

sender_id_mode = st.sidebar.radio(
    "Mode Pemilihan Sender ID:",
    options=["Pilih Manual", "Tampilkan Top N"]
)

if sender_id_mode == "Pilih Manual":
    all_sender_ids = sorted(df['Sender ID'].unique())
    selected_sender_ids = st.sidebar.multiselect(
        "Pilih Sender ID:",
        options=all_sender_ids,
        default=all_sender_ids[:5] if len(all_sender_ids) > 5 else all_sender_ids
    )
else:
    top_n = st.sidebar.number_input(
        "Jumlah Top Sender ID:",
        min_value=1,
        max_value=30,
        value=15,
        step=1
    )

# tombol trigger
st.sidebar.markdown("---")
show_button = st.sidebar.button("Tampilkan Visualisasi", type="primary")

# ==============================
# VISUALIZATION
# ==============================
st.header("📈 Hasil Visualisasi Data")

if show_button:

    if not selected_months:
        st.warning("Silakan pilih minimal satu bulan.")
        st.stop()

    # --- FILTER ---
    df_filtered = df[df['Month'].isin(selected_months)]

    # --- FILTER SENDER ---
    if sender_id_mode == "Tampilkan Top N":
        top_senders = (
            df_filtered.groupby('Sender ID')[selected_metric]
            .sum()
            .nlargest(top_n)
            .index.tolist()
        )
        final_sender_ids = top_senders
        st.info(f"Menampilkan Top {top_n} Sender ID berdasarkan {selected_metric}.")
    else:
        final_sender_ids = selected_sender_ids

    if final_sender_ids:
        df_final = df_filtered[df_filtered['Sender ID'].isin(final_sender_ids)]
    else:
        df_final = df_filtered.copy()

    if df_final.empty:
        st.warning("Tidak ada data yang cocok dengan filter yang Anda pilih.")
    else:
        df_final = df_final.sort_values('Month')

        # ==============================
        # BAR CHART
        # ==============================
        st.subheader(f"Volume {selected_metric} per Bulan")

        fig_bar = px.bar(
            df_final,
            x='Month_str',
            y=selected_metric,
            color='Sender ID',
            title=f'Total {selected_metric} per Bulan',
            text_auto=True
        )

        fig_bar.update_layout(
            xaxis_title="Bulan",
            yaxis_title="Jumlah Pesan",
            legend_title="Sender ID"
        )

        st.plotly_chart(fig_bar, use_container_width=True)

        # ==============================
        # ANALYSIS SECTION
        # ==============================
        st.header("💡 Analisis Tambahan")
        col1, col2 = st.columns(2)

        # --- PIE ---
        with col1:
            st.subheader(f"Komposisi {selected_metric}")
            fig_pie = px.pie(
                df_final,
                names='Sender ID',
                values=selected_metric,
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- LINE (DELIVERY RATE) ---
        with col2:
            st.subheader("Tren Tingkat Pengiriman (%)")

            df_trend = df_final.groupby('Month').agg(
                Total_Sent=('Sent Messages', 'sum'),
                Total_Delivered=('Delivered Messages', 'sum')
            ).reset_index()

            df_trend['Delivery Rate'] = df_trend.apply(
                lambda row: (row['Total_Delivered'] / row['Total_Sent']) * 100
                if row['Total_Sent'] > 0 else None,
                axis=1
            )

            df_trend['Delivery Rate'] = df_trend['Delivery Rate'].round(2)

            df_trend = df_trend.sort_values('Month')
            df_trend['Month_str'] = df_trend['Month'].astype(str)

            y_min = max(0, df_trend['Delivery Rate'].min() - 5) if not df_trend.empty else 80

            fig_line = px.line(
                df_trend,
                x='Month_str',
                y='Delivery Rate',
                markers=True,
                title='Tren Tingkat Keberhasilan Pengiriman per Bulan'
            )

            fig_line.update_yaxes(range=[y_min, 101])

            st.plotly_chart(fig_line, use_container_width=True)

        # ==============================
        # TABLE
        # ==============================
        st.subheader("Data Sesuai Filter")
        st.dataframe(df_final)

else:
    st.info("Silakan atur filter di samping dan klik **'Tampilkan Visualisasi'** untuk melihat hasilnya.")
