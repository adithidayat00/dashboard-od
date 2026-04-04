import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard OD", layout="wide")

st.title("📊 Dashboard Monitoring OD")

col1, col2 = st.columns(2)

with col1:
    no_kontrak = st.text_input("Masukkan No Kontrak")

with col2:
    tgl_tagihan = st.date_input("Tanggal Terima Tagihan")

uploaded_file = st.file_uploader("Upload Data Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    df.rename(columns={
        "NoReg": "No_Kontrak",
        "Stat OV": "Stat_OV",
        "Tanggal Valid": "Tanggal_Valid"
    }, inplace=True)

    df["Tanggal_Valid"] = pd.to_datetime(df["Tanggal_Valid"], errors='coerce')

    if no_kontrak:
        data = df[df["No_Kontrak"].astype(str) == no_kontrak]

        if not data.empty:
            data = data.copy()

            data["Selisih_Hari"] = (
                data["Tanggal_Valid"] - pd.to_datetime(tgl_tagihan)
            ).dt.days

            def klasifikasi_od(x):
                if 15 <= x <= 45:
                    return "OD1"
                elif 46 <= x <= 75:
                    return "OD2"
                elif x > 75:
                    return "OD3"
                else:
                    return "Tidak Masuk OD"

            data["Kategori_OD"] = data["Selisih_Hari"].apply(klasifikasi_od)

            st.subheader("📌 Hasil Analisa")

            st.metric("Selisih Hari", int(data["Selisih_Hari"].values[0]))
            st.metric("Kategori OD", data["Kategori_OD"].values[0])
            st.metric("Stat OV", data["Stat_OV"].values[0])

            st.dataframe(data)

        else:
            st.warning("No Kontrak tidak ditemukan")