import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# =========================
# CONFIG SUPABASE
# =========================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Monitoring OD", layout="wide")

st.title("📊 Monitoring Overdue (OD)")

# AUTO REFRESH
st_autorefresh(interval=60000, key="refresh")

# =========================
# INPUT DATA
# =========================
st.subheader("➕ Input Invoice")

with st.form("input_form"):
    col1, col2 = st.columns(2)

    with col1:
        noreg = st.text_input("No Reg")

    with col2:
        invoice_date = st.date_input("Tanggal Invoice")

    submitted = st.form_submit_button("Submit")

    if submitted:
        if noreg:
            try:
                supabase.table("input_data").insert({
                    "noreg": noreg,
                    "invoice_date": str(invoice_date)
                }).execute()

                st.success("✅ Data berhasil ditambahkan!")
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("⚠️ No Reg harus diisi!")

# =========================
# LOAD DATA
# =========================
st.subheader("📋 Monitoring Table")

@st.cache_data(ttl=60)
def load_data():
    response = supabase.table("monitoring_od").select("*").execute()
    return pd.DataFrame(response.data)

df = load_data()

if not df.empty:

    df = df.sort_values(by=["is_paid", "aging_days"], ascending=[True, False])
    df = df.reset_index(drop=True)

    df["af"] = df["af"].fillna(0)
    df["af"] = df["af"].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

    if "id" in df.columns:
        df = df.drop(columns=["id"])

    def highlight_row(row):
        if row["is_paid"]:
            return ["background-color: #2e7d32; color: white"] * len(row)

        if row["od_status"] == "OD 3":
            return ["background-color: #ffccc7"] * len(row)
        elif row["od_status"] == "OD 2":
            return ["background-color: #ffe7ba"] * len(row)
        elif row["od_status"] == "OD 1":
            return ["background-color: #fff1b8"] * len(row)

        return [""] * len(row)

    st.dataframe(df.style.apply(highlight_row, axis=1), use_container_width=True)

    st.markdown("""
    **Keterangan Warna:**
    - 🟢 Hijau = Paid (OVOP)
    - 🟥 Merah = OD 3
    - 🟧 Orange = OD 2
    - 🟨 Kuning = OD 1
    """)

else:
    st.info("Belum ada data")

# =========================
# UPLOAD MASTER DATA (SUPER FIX)
# =========================
st.subheader("📤 Upload Master Data")

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])

if uploaded_file:

    df_excel = pd.read_excel(uploaded_file)

    # Rename kolom
    df_excel = df_excel.rename(columns={
        "NoReg": "noreg",
        "NamaCust": "nama_customer",
        "NamaDealer": "dealer",
        "SalesACC": "salesacc",
        "Merk": "brand",
        "State": "state",
        "State1": "state1",
        "AF": "af"
    })

    # Pastikan AF numeric
    df_excel["af"] = pd.to_numeric(df_excel["af"], errors="coerce").fillna(0)

    st.dataframe(df_excel.head())

    if st.button("Upload ke Database"):

        try:
            df_clean = df_excel.copy()

            # =========================
            # FIX TIMESTAMP
            # =========================
            for col in df_clean.columns:
                if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
                    df_clean[col] = df_clean[col].astype(str)

            # =========================
            # FIX NaN
            # =========================
            df_clean = df_clean.astype(object).where(pd.notnull(df_clean), None)

            # =========================
            # FILTER KOLOM SESUAI DB
            # =========================
            allowed_columns = [
                "noreg",
                "nama_customer",
                "dealer",
                "salesacc",
                "brand",
                "state",
                "state1",
                "af"
            ]

            # VALIDASI KOLOM
            missing_cols = [col for col in allowed_columns if col not in df_clean.columns]
            if missing_cols:
                st.error(f"❌ Kolom ini tidak ada di Excel: {missing_cols}")
                st.stop()

            df_clean = df_clean[allowed_columns]

            # =========================
            # CONVERT KE DICT
            # =========================
            data = df_clean.to_dict(orient="records")

            # =========================
            # UPLOAD BATCH
            # =========================
            batch_size = 500
            for i in range(0, len(data), batch_size):
                supabase.table("db_ascii").upsert(data[i:i+batch_size]).execute()

            st.success("✅ Upload berhasil!")

        except Exception as e:
            st.error(f"❌ Error upload: {e}")
