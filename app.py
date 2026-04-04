import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Dashboard OD", layout="wide")

st.title("📊 Dashboard Monitoring OD")

# =========================
# INPUT
# =========================
tgl_tagihan = st.date_input("Tanggal Terima Tagihan")

uploaded_file = st.file_uploader("Upload Data Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # =========================
    # RENAME KOLOM (SESUAIKAN JIKA PERLU)
    # =========================
    df.rename(columns={
        "NoReg": "No_Kontrak",
        "Stat OV": "Stat_OV",
        "Tanggal Valid": "Tanggal_Valid"
    }, inplace=True)

    # =========================
    # FORMAT TANGGAL
    # =========================
    df["Tanggal_Valid"] = pd.to_datetime(df["Tanggal_Valid"], errors='coerce')

    # =========================
    # HITUNG SELISIH HARI
    # =========================
    df["Selisih_Hari"] = (
        df["Tanggal_Valid"] - pd.to_datetime(tgl_tagihan)
    ).dt.days

    # =========================
    # KLASIFIKASI OD
    # =========================
    def klasifikasi_od(x):
        if 15 <= x <= 45:
            return "OD1"
        elif 46 <= x <= 75:
            return "OD2"
        elif x > 75:
            return "OD3"
        else:
            return "Tidak Masuk OD"

    df["Kategori_OD"] = df["Selisih_Hari"].apply(klasifikasi_od)

    # =========================
    # SUMMARY
    # =========================
    st.subheader("📊 Summary OD")

    col1, col2, col3 = st.columns(3)

    col1.metric("OD1", (df["Kategori_OD"] == "OD1").sum())
    col2.metric("OD2", (df["Kategori_OD"] == "OD2").sum())
    col3.metric("OD3", (df["Kategori_OD"] == "OD3").sum())

    # =========================
    # HIGHLIGHT WARNA
    # =========================
    def highlight_od(row):
        if row["Kategori_OD"] == "OD1":
            return ["background-color: #90EE90"] * len(row)  # hijau
        elif row["Kategori_OD"] == "OD2":
            return ["background-color: #FFD700"] * len(row)  # kuning
        elif row["Kategori_OD"] == "OD3":
            return ["background-color: #FF7F7F"] * len(row)  # merah
        else:
            return [""] * len(row)

    styled_df = df.style.apply(highlight_od, axis=1)

    # =========================
    # TABEL
    # =========================
    st.subheader("📋 Data Rekap")
    st.write(styled_df)

    # =========================
    # DOWNLOAD EXCEL
    # =========================
    def convert_to_excel(dataframe):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='Rekap OD')
        return output.getvalue()

    excel_data = convert_to_excel(df)

    st.download_button(
        label="📥 Download Rekap Excel",
        data=excel_data,
        file_name="rekap_od.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
