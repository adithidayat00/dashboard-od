import streamlit as st
import pandas as pd
from supabase import create_client

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

    # SORTING
    df = df.sort_values(by=["is_paid", "aging_days"], ascending=[True, False])

    # FORMAT AF BIAR RAPI
    if "af" in df.columns:
        df["af"] = df["af"].fillna(0)

    # HIGHLIGHT HIJAU YANG BAGUS
    def highlight_paid(row):
        if row["is_paid"]:
            return ["background-color: #2e7d32; color: white"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(highlight_paid, axis=1),
        use_container_width=True
    )

    st.caption("🟢 Hijau = Sudah Paid (OVOP)")

else:
    st.info("Belum ada data")

# =========================
# DASHBOARD
# =========================
st.subheader("📈 Dashboard OD")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False]

    if not df_unpaid.empty:

        summary = df_unpaid.groupby("od_status").agg(
            total_account=("noreg", "count"),
            total_af=("af", "sum")
        ).reset_index()

        col1, col2, col3 = st.columns(3)

        for _, row in summary.iterrows():
            if row["od_status"] == "OD 1":
                col1.metric("OD 1", row["total_account"], f"AF: {int(row['total_af']):,}")
            elif row["od_status"] == "OD 2":
                col2.metric("OD 2", row["total_account"], f"AF: {int(row['total_af']):,}")
            elif row["od_status"] == "OD 3":
                col3.metric("OD 3", row["total_account"], f"AF: {int(row['total_af']):,}")

    else:
        st.info("Semua data sudah paid 🎉")

# =========================
# UPLOAD EXCEL MASTER DATA
# =========================
st.subheader("📤 Upload Master Data (db_ascii)")

uploaded_file = st.file_uploader(
    "Upload Excel (xlsx / xls)",
    type=["xlsx", "xls"]
)

if uploaded_file:

    try:
        df_excel = pd.read_excel(uploaded_file)

        st.write("Preview Data:")
        st.dataframe(df_excel.head())

        st.info("Pastikan kolom sesuai: noreg, nama_customer, type, dealer, salesacc, brand, state, state1, af")

        if st.button("Upload ke Database"):

            data = df_excel.to_dict(orient="records")

            supabase.table("db_ascii").upsert(data).execute()

            st.success("✅ Master data berhasil diupload!")

    except Exception as e:
        st.error(f"❌ Error baca file: {e}")
