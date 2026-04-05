import streamlit as st
import pandas as pd
from supabase import create_client
import os

# =========================
# CONFIG SUPABASE (PAKE SECRET STREAMLIT)
# =========================
SUPABASE_URL = st.secrets["https://uszepsidhhbvindwvbnp.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVzemVwc2lkaGhidmluZHd2Ym5wIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MTAxMTgsImV4cCI6MjA5MDk4NjExOH0.F7r9zj2zAevrguNNjDimym-FKRxOpLGgO74D7U3wf-4"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# TITLE
# =========================
st.title("📊 Monitoring Overdue (OD)")

# =========================
# INPUT DATA
# =========================
st.subheader("➕ Input Invoice")

with st.form("input_form"):
    noreg = st.text_input("No Reg")
    invoice_date = st.date_input("Tanggal Invoice")

    submitted = st.form_submit_button("Submit")

    if submitted:
        if noreg:
            supabase.table("input_data").insert({
                "noreg": noreg,
                "invoice_date": str(invoice_date)
            }).execute()

            st.success("Data berhasil ditambahkan!")
        else:
            st.warning("No Reg harus diisi!")

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

    def highlight_paid(row):
        if row["is_paid"]:
            return ["background-color: #d4edda"] * len(row)
        return [""] * len(row)

    st.dataframe(df.style.apply(highlight_paid, axis=1), use_container_width=True)

else:
    st.info("Belum ada data")

# =========================
# DASHBOARD
# =========================
st.subheader("📈 Dashboard OD")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False]

    summary = df_unpaid.groupby("od_status").agg(
        total_account=("noreg", "count"),
        total_af=("af", "sum")
    ).reset_index()

    col1, col2, col3 = st.columns(3)

    for _, row in summary.iterrows():
        if row["od_status"] == "OD 1":
            col1.metric("OD 1", row["total_account"], f"AF: {row['total_af']}")
        elif row["od_status"] == "OD 2":
            col2.metric("OD 2", row["total_account"], f"AF: {row['total_af']}")
        elif row["od_status"] == "OD 3":
            col3.metric("OD 3", row["total_account"], f"AF: {row['total_af']}")
