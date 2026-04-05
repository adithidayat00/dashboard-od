import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import os

# =============================
# CONFIG
# =============================
SUPABASE_URL = st.secrets["https://jrikxltaaxlipbgturju.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWt4bHRhYXhsaXBiZ3R1cmp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyODMxNzEsImV4cCI6MjA5MDg1OTE3MX0.gloC3nfdIx7q9rV8kEXcKsAaZpJB9nOeyvRRS4yY-6U"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(layout="wide")
st.title("📊 Sistem Monitoring OD")

# =============================
# LOAD DATA
# =============================
def load_db():
    res = supabase.table("db_ascii").select("*").execute()
    return pd.DataFrame(res.data)

def load_input():
    res = supabase.table("input_data").select("*").execute()
    return pd.DataFrame(res.data)

# =============================
# INSERT INPUT
# =============================
def insert_input(noreg, tgl_invoice):
    supabase.table("input_data").insert({
        "NoReg": str(noreg),
        "Tanggal Invoice": pd.to_datetime(tgl_invoice).strftime("%Y-%m-%d")
    }).execute()

# =============================
# UPLOAD EXCEL
# =============================
st.subheader("📂 Upload DB ASCII")

uploaded_file = st.file_uploader("Upload Excel (.xls/.xlsx)", type=["xls","xlsx"])

if uploaded_file:
    try:
        ext = os.path.splitext(uploaded_file.name)[1]

        if ext == ".xls":
            df_upload = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df_upload = pd.read_excel(uploaded_file, engine="openpyxl")

        st.write("Preview:")
        st.dataframe(df_upload.head())

        if st.button("Upload ke DB"):
            data = df_upload.to_dict(orient="records")

            for i in range(0, len(data), 500):
                supabase.table("db_ascii").insert(data[i:i+500]).execute()

            st.success("✅ Upload berhasil")
            st.rerun()

    except Exception as e:
        st.error(e)

# =============================
# INPUT INVOICE
# =============================
st.subheader("📝 Input Invoice")

col1, col2, col3 = st.columns(3)

with col1:
    noreg = st.text_input("NoReg")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

with col3:
    if st.button("Tambah"):
        insert_input(noreg, tgl_invoice)
        st.success("Masuk!")
        st.rerun()

# =============================
# LOAD DATA
# =============================
db = load_db()
df_input = load_input()

if not db.empty and not df_input.empty:

    # 🔥 SAMAIN FORMAT
    db["NoReg"] = db["NoReg"].astype(str)
    df_input["NoReg"] = df_input["NoReg"].astype(str)

    # 🔥 STATUS
    db["status"] = db["State"].fillna("") + db["State1"].fillna("")

    # 🔥 MERGE
    df = df_input.merge(db, on="NoReg", how="left")

    # =============================
    # HITUNG OD
    # =============================
    df["Tanggal Invoice"] = pd.to_datetime(df["Tanggal Invoice"])
    today = pd.to_datetime(datetime.today().date())

    df["hari"] = (today - df["Tanggal Invoice"]).dt.days

    def kategori(h):
        if h < 15:
            return "Belum OD"
        elif h <= 45:
            return "OD 1"
        elif h <= 75:
            return "OD 2"
        else:
            return "OD 3"

    df["kategori_od"] = df["hari"].apply(kategori)

    # =============================
    # STATUS LUNAS
    # =============================
    df["is_lunas"] = df["status"].str.contains("OVOP", na=False)

    df = df.sort_values(by=["is_lunas", "hari"], ascending=[True, False])

    # =============================
    # DISPLAY
    # =============================
    df_display = df[[
        "NoReg",
        "kategori_od",
        "NamaCust",
        "Type",
        "Dealer",
        "SalesACC",
        "Brand",
        "status",
        "AF",
        "hari"
    ]]

    # =============================
    # DASHBOARD
    # =============================
    st.subheader("📊 Dashboard")

    col1, col2, col3 = st.columns(3)

    for i, kategori_name in enumerate(["OD 1", "OD 2", "OD 3"]):
        data = df[df["kategori_od"] == kategori_name]
        total = len(data)
        af_sum = pd.to_numeric(data["AF"], errors="coerce").sum()

        with [col1, col2, col3][i]:
            st.metric(kategori_name, f"{total} account", f"AF: {int(af_sum):,}")

    # =============================
    # TABLE
    # =============================
    def highlight(row):
        if "OVOP" in str(row["status"]):
            return ["background-color: green"] * len(row)
        return [""] * len(row)

    st.subheader("📋 Data Monitoring")
    st.dataframe(df_display.style.apply(highlight, axis=1), use_container_width=True)

else:
    st.warning("⚠️ Upload DB ASCII dulu atau input data")
