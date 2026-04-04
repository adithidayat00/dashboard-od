import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Dashboard OD", layout="wide")

st.title("📊 Dashboard Monitoring OD")

# =========================
# INPUT
# =========================
tgl_tagihan = st.date_input("Tanggal Terima Tagihan")
uploaded_file = st.file_uploader("Upload Data Excel", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # =========================
    # BERSIHKAN NAMA KOLOM (ANTI ERROR TOTAL)
    # =========================
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "")
        .str.replace("'", "")
        .str.replace("-", "")
    )

    # DEBUG (optional, bisa dihapus nanti)
    st.write("Kolom terdeteksi:", df.columns)

    # =========================
    # RENAME OTOMATIS (FLEXIBLE)
    # =========================
    mapping = {
        "noreg": "no_kontrak",
        "tglin": "tgl_tagihan",
        "namacust": "nama_cust",
        "state": "stat_ov",
        "tglvld": "tanggal_valid",
        "tglvalid": "tanggal_valid"
    }

    df.rename(columns={k: v for k, v in mapping.items() if k in df.columns}, inplace=True)

    # =========================
    # VALIDASI KOLOM WAJIB
    # =========================
    required_cols = ["no_kontrak", "tanggal_valid"]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Kolom wajib tidak ditemukan: {missing}")
        st.stop()

    # =========================
    # FORMAT TANGGAL
    # =========================
    df["tanggal_valid"] = pd.to_datetime(df["tanggal_valid"], errors='coerce')

    # =========================
    # HITUNG SELISIH
    # =========================
    df["selisih_hari"] = (
        df["tanggal_valid"] - pd.to_datetime(tgl_tagihan)
    ).dt.days

    # =========================
    # KLASIFIKASI OD
    # =========================
    def klasifikasi_od(x):
        if pd.isna(x):
            return "Tidak Valid"
        elif 15 <= x <= 45:
            return "OD1"
        elif 46 <= x <= 75:
            return "OD2"
        elif x > 75:
            return "OD3"
        else:
            return "Tidak Masuk OD"

    df["kategori_od"] = df["selisih_hari"].apply(klasifikasi_od)

    # =========================
    # SUMMARY
    # =========================
    st.subheader("📊 Summary OD")

    col1, col2, col3 = st.columns(3)
    col1.metric("OD1", (df["kategori_od"] == "OD1").sum())
    col2.metric("OD2", (df["kategori_od"] == "OD2").sum())
    col3.metric("OD3", (df["kategori_od"] == "OD3").sum())

    # =========================
    # HIGHLIGHT WARNA
    # =========================
    def highlight_od(row):
        if row["kategori_od"] == "OD1":
            return ["background-color: #90EE90"] * len(row)
        elif row["kategori_od"] == "OD2":
            return ["background-color: #FFD700"] * len(row)
        elif row["kategori_od"] == "OD3":
            return ["background-color: #FF7F7F"] * len(row)
        else:
            return [""] * len(row)

    styled_df = df.style.apply(highlight_od, axis=1)

    # =========================
    # TABEL
    # =========================
    st.subheader("📋 Data Rekap")
    st.write(styled_df)

    # =========================
    # PILIH FORMAT DOWNLOAD
    # =========================
    format_file = st.selectbox(
        "Pilih Format Download",
        ["Excel (.xlsx)", "Excel 97-2003 (.xls)"]
    )

    # =========================
    # EXPORT EXCEL
    # =========================
    def convert_to_excel(dataframe, format_type):
        output = BytesIO()

        if format_type == "Excel (.xlsx)":
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='Rekap OD')
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = "rekap_od.xlsx"

        else:
            with pd.ExcelWriter(output, engine='xlwt') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='Rekap OD')
            mime = "application/vnd.ms-excel"
            filename = "rekap_od.xls"

        return output.getvalue(), filename, mime

    excel_data, file_name, mime_type = convert_to_excel(df, format_file)

    st.download_button(
        label="📥 Download Rekap",
        data=excel_data,
        file_name=file_name,
        mime=mime_type
    )
