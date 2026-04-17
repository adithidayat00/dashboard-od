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

    # SORTING
    df = df.sort_values(by=["is_paid", "aging_days"], ascending=[True, False])
    df = df.reset_index(drop=True)

    # FORMAT AF
    df["af"] = df["af"].fillna(0)
    df["af"] = df["af"].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

    # DROP ID
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # =========================
    # 🎨 STYLE FUNCTION
    # =========================
    def highlight_row(row):
        # PRIORITAS: PAID
        if row["is_paid"]:
            return ["background-color: #2e7d32; color: white"] * len(row)

        # OD COLOR
        if row["od_status"] == "OD 3":
            return ["background-color: #ffccc7"] * len(row)  # merah soft
        elif row["od_status"] == "OD 2":
            return ["background-color: #ffe7ba"] * len(row)  # orange soft
        elif row["od_status"] == "OD 1":
            return ["background-color: #fff1b8"] * len(row)  # kuning soft

        return [""] * len(row)

    # =========================
    # DISPLAY
    # =========================
    st.dataframe(
        df.style.apply(highlight_row, axis=1),
        use_container_width=True
    )

    # LEGEND
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
# DASHBOARD OD
# =========================
st.subheader("📈 Dashboard OD")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()

    if not df_unpaid.empty:

        df_unpaid["af"] = df_unpaid["af"].replace('[Rp .]', '', regex=True).astype(float)

        summary = df_unpaid.groupby("od_status").agg(
            total_account=("noreg", "count"),
            total_af=("af", "sum")
        ).reset_index()

        col1, col2, col3 = st.columns(3)

        for _, row in summary.iterrows():
            af_format = f"Rp {int(row['total_af']):,}".replace(",", ".")

            if row["od_status"] == "OD 1":
                col1.metric("🟨 OD 1", row["total_account"], f"AF: {af_format}")
            elif row["od_status"] == "OD 2":
                col2.metric("🟧 OD 2", row["total_account"], f"AF: {af_format}")
            elif row["od_status"] == "OD 3":
                col3.metric("🟥 OD 3", row["total_account"], f"AF: {af_format}")

    else:
        st.info("Semua data sudah paid 🎉")

# =========================
# SUMMARY DEALER
# =========================
st.subheader("🏢 Summary Dealer")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()

    if not df_unpaid.empty:

        df_unpaid["dealer_clean"] = (
            df_unpaid["dealer"]
            .fillna("")
            .str.upper()
            .str.replace(",PT", "", regex=False)
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

        pivot = pivot.fillna(0)

        pivot["TOTAL_ACC"] = pivot.filter(like="_ACC").sum(axis=1)
        pivot["TOTAL_AF"] = pivot.filter(like="_AF").sum(axis=1)

        for col in pivot.columns:
            if "_AF" in col:
                pivot[col] = pivot[col].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

        pivot = pivot.sort_values(by="TOTAL_ACC", ascending=False)

        st.dataframe(pivot, use_container_width=True)

# =========================
# SUMMARY SALES
# =========================
st.subheader("📊 Summary by Sales")

if not df.empty:

    df_unpaid = df[df["is_paid"] == False].copy()

    if not df_unpaid.empty:

        df_unpaid["af"] = df_unpaid["af"].replace('[Rp .]', '', regex=True).astype(float)

        pivot = df_unpaid.groupby("salesacc").agg(
            total_account=("noreg", "count"),
            total_af=("af", "sum")
        ).reset_index()

        pivot = pivot.sort_values(by="total_af", ascending=False)

        pivot["total_af"] = pivot["total_af"].apply(lambda x: f"Rp {int(x):,}".replace(",", "."))

        st.dataframe(pivot, use_container_width=True)

# =========================
# UPLOAD MASTER DATA
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
        data = df_excel.to_dict(orient="records")
        supabase.table("db_ascii").upsert(data).execute()
        st.success("✅ Upload berhasil!")
