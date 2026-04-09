import streamlit as st
import pandas as pd
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

    # =========================
    # DETECT PAID (OV OP)
    # =========================
    df["state"] = df["state"].astype(str)
    df["state1"] = df["state1"].astype(str)

    df["is_paid"] = (
        df["state"].str.upper().str.strip() == "OV"
    ) & (
        df["state1"].str.upper().str.strip() == "OP"
    )

    # =========================
    # SPLIT DATA
    # =========================
    df_unpaid = df[df["is_paid"] == False].copy()
    df_paid = df[df["is_paid"] == True].copy()

    # =========================
    # FORMAT AF
    # =========================
    def format_rupiah(x):
        return f"Rp {int(x):,}".replace(",", ".")

    # =========================
    # UNPAID TABLE
    # =========================
    st.subheader("📋 Monitoring Table (Unpaid)")

    if not df_unpaid.empty:

        df_unpaid = df_unpaid.sort_values(by=["aging_days"], ascending=False)
        df_unpaid = df_unpaid.reset_index(drop=True)

        df_unpaid["af"] = df_unpaid["af"].fillna(0)
        df_unpaid["af"] = df_unpaid["af"].apply(format_rupiah)

        if "id" in df_unpaid.columns:
            df_unpaid = df_unpaid.drop(columns=["id"])

        st.dataframe(df_unpaid, use_container_width=True)

    else:
        st.info("Tidak ada data unpaid 🎉")

    # =========================
    # PAID TABLE (OV OP)
    # =========================
    st.subheader("✅ Paid Table (OV OP)")

    if not df_paid.empty:

        df_paid = df_paid.sort_values(by=["aging_days"], ascending=False)
        df_paid = df_paid.reset_index(drop=True)

        df_paid["af"] = df_paid["af"].fillna(0)
        df_paid["af"] = df_paid["af"].apply(format_rupiah)

        if "id" in df_paid.columns:
            df_paid = df_paid.drop(columns=["id"])

        st.dataframe(df_paid, use_container_width=True)

    else:
        st.info("Belum ada data yang sudah paid")

else:
    st.info("Belum ada data")

# =========================
# DASHBOARD OD
# =========================
st.subheader("📈 Dashboard OD")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()

    if not df_unpaid.empty:

        df_unpaid["af"] = df_unpaid["af"].fillna(0)

        summary = df_unpaid.groupby("od_status").agg(
            total_account=("noreg", "count"),
            total_af=("af", "sum")
        ).reset_index()

        col1, col2, col3 = st.columns(3)

        for _, row in summary.iterrows():
            af_format = f"Rp {int(row['total_af']):,}".replace(",", ".")

            if row["od_status"] == "OD 1":
                col1.metric("OD 1", row["total_account"], f"AF: {af_format}")
            elif row["od_status"] == "OD 2":
                col2.metric("OD 2", row["total_account"], f"AF: {af_format}")
            elif row["od_status"] == "OD 3":
                col3.metric("OD 3", row["total_account"], f"AF: {af_format}")

    else:
        st.info("Semua data sudah paid 🎉")

# =========================
# SUMMARY PER SALES
# =========================
st.subheader("📊 Summary by Sales (SO)")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()

    if not df_unpaid.empty:

        df_unpaid["af"] = df_unpaid["af"].fillna(0)

        pivot = df_unpaid.groupby("salesacc").agg(
            total_account=("noreg", "count"),
            total_af=("af", "sum")
        ).reset_index()

        pivot = pivot.sort_values(by="total_af", ascending=False)

        pivot["total_af"] = pivot["total_af"].apply(
            lambda x: f"Rp {int(x):,}".replace(",", ".")
        )

        pivot = pivot.reset_index(drop=True)

        st.dataframe(pivot, use_container_width=True)

# =========================
# UPLOAD MASTER DATA
# =========================
st.subheader("📤 Upload Master Data (db_ascii)")

uploaded_file = st.file_uploader(
    "Upload Excel (xlsx / xls)",
    type=["xlsx", "xls"]
)

if uploaded_file:

    try:
        df_excel = pd.read_excel(uploaded_file)

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

        df_excel = df_excel[
            ["noreg", "nama_customer", "type", "dealer", "salesacc", "brand", "state", "state1", "af"]
        ]

        df_excel["af"] = pd.to_numeric(df_excel["af"], errors="coerce").fillna(0)

        for col in df_excel.columns:
            if df_excel[col].dtype == "datetime64[ns]":
                df_excel[col] = df_excel[col].astype(str)

        df_excel = df_excel.fillna("")

        st.write("Preview Data:")
        st.dataframe(df_excel.head())

        if st.button("Upload ke Database"):

            data = df_excel.to_dict(orient="records")

            supabase.table("db_ascii").upsert(data).execute()

            st.success("✅ Master data berhasil diupload!")

    except Exception as e:
        st.error(f"❌ Error: {e}")
