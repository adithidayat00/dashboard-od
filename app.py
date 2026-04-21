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

st_autorefresh(interval=60000, key="refresh")

# =========================
# LOAD DATA
# =========================
@st.cache_data(ttl=60)
def load_data():
    response = supabase.table("monitoring_od").select("*").execute()
    return pd.DataFrame(response.data)

df = load_data()

# =========================
# MONITORING TABLE
# =========================
st.subheader("📋 Monitoring Table")

if not df.empty:

    df = df.sort_values(by=["is_paid", "aging_days"], ascending=[True, False])
    df = df.reset_index(drop=True)

    df["af"] = df["af"].fillna(0)
    df["af"] = df["af"].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

    def highlight_row(row):
        if row["is_paid"]:
            return ["background-color: #2e7d32; color: white"] * len(row)
        if row["od_status"] == "OD 3":
            return ["background-color: #ffccc7"] * len(row)
        elif row["od_status"] == "OD 2":
            return ["background-color: #ffe7ba"] * len(row)
        elif row["od_status"] == "OD 1":
            return ["background-color: #fff1b8"] * len(row)
        elif row["od_status"] == "CURRENT":
            return ["background-color: #e6f4ff"] * len(row)
        return [""] * len(row)

    st.dataframe(df.style.apply(highlight_row, axis=1), use_container_width=True)

# =========================
# DASHBOARD OD + CURRENT
# =========================
st.subheader("📈 Dashboard OD")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()
    df_unpaid["af"] = df_unpaid["af"].replace('[Rp .]', '', regex=True).astype(float)

    summary = df_unpaid.groupby("od_status").agg(
        total_account=("noreg", "count"),
        total_af=("af", "sum")
    ).reset_index()

    col1, col2, col3, col4 = st.columns(4)

    for _, row in summary.iterrows():
        af_format = f"Rp {int(row['total_af']):,}".replace(",", ".")

        if row["od_status"] == "CURRENT":
            col1.metric("🔵 CURRENT", row["total_account"], af_format)
        elif row["od_status"] == "OD 1":
            col2.metric("🟨 OD 1", row["total_account"], af_format)
        elif row["od_status"] == "OD 2":
            col3.metric("🟧 OD 2", row["total_account"], af_format)
        elif row["od_status"] == "OD 3":
            col4.metric("🟥 OD 3", row["total_account"], af_format)

# =========================
# SUMMARY DEALER (ADA CURRENT + AF)
# =========================
st.subheader("🏢 Summary Dealer")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()

    df_unpaid["dealer_clean"] = (
        df_unpaid["dealer"]
        .fillna("")
        .str.upper()
        .str.strip()
    )

    df_unpaid["af"] = df_unpaid["af"].replace('[Rp .]', '', regex=True).astype(float)

    grouped = df_unpaid.groupby(["dealer_clean", "od_status"]).agg(
        total_account=("noreg", "count"),
        total_af=("af", "sum")
    ).reset_index()

    pivot_acc = grouped.pivot(index="dealer_clean", columns="od_status", values="total_account").fillna(0)
    pivot_af = grouped.pivot(index="dealer_clean", columns="od_status", values="total_af").fillna(0)

    pivot_acc.columns = [f"{col}_ACC" for col in pivot_acc.columns]
    pivot_af.columns = [f"{col}_AF" for col in pivot_af.columns]

    pivot = pd.concat([pivot_acc, pivot_af], axis=1).reset_index()

    pivot["TOTAL_ACC"] = pivot.filter(like="_ACC").sum(axis=1)
    pivot["TOTAL_AF"] = pivot.filter(like="_AF").sum(axis=1)

    # format rupiah
    for col in pivot.columns:
        if "_AF" in col or col == "TOTAL_AF":
            pivot[col] = pivot[col].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

    pivot = pivot.sort_values(by="TOTAL_ACC", ascending=False)

    st.dataframe(pivot, use_container_width=True)

# =========================
# SUMMARY SALES
# =========================
st.subheader("📊 Summary by Sales")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()
    df_unpaid["af"] = df_unpaid["af"].replace('[Rp .]', '', regex=True).astype(float)

    pivot = df_unpaid.groupby("salesacc").agg(
        total_account=("noreg", "count"),
        total_af=("af", "sum")
    ).reset_index()

    pivot = pivot.sort_values(by="total_af", ascending=False)

    pivot["total_af"] = pivot["total_af"].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

    st.dataframe(pivot, use_container_width=True)

# =========================
# UPLOAD (FIXED)
# =========================
st.subheader("📤 Upload Master Data")

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])

if uploaded_file:

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

    df_excel["af"] = pd.to_numeric(df_excel["af"], errors="coerce").fillna(0)

    st.dataframe(df_excel.head())

    if st.button("Upload ke Database"):

        try:
            df_clean = df_excel.copy()

            # FIX TIMESTAMP
            for col in df_clean.columns:
                if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
                    df_clean[col] = df_clean[col].astype(str)

            # FIX NaN
            df_clean = df_clean.astype(object).where(pd.notnull(df_clean), None)

            # FILTER KOLOM
            allowed_columns = [
                "noreg", "nama_customer", "dealer",
                "salesacc", "brand", "state",
                "state1", "af"
            ]

            df_clean = df_clean[allowed_columns]

            data = df_clean.to_dict(orient="records")

            for i in range(0, len(data), 500):
                supabase.table("db_ascii").upsert(data[i:i+500]).execute()

            st.success("✅ Upload berhasil!")

        except Exception as e:
            st.error(f"❌ Error upload: {e}")
