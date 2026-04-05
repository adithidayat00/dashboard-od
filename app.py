import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from datetime import datetime
import os
import math

# =============================
# 🔑 CONFIG
# =============================
SUPABASE_URL = "https://jrikxltaaxlipbgturju.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWt4bHRhYXhsaXBiZ3R1cmp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyODMxNzEsImV4cCI6MjA5MDg1OTE3MX0.gloC3nfdIx7q9rV8kEXcKsAaZpJB9nOeyvRRS4yY-6U"

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
    try:
        supabase.table("input_data").insert({
            "No_Reg": str(noreg),
            "Tanggal_Invoice": pd.to_datetime(tgl_invoice).strftime("%Y-%m-%d")
        }).execute()
        st.success("✅ Data berhasil ditambahkan")
    except Exception as e:
        st.error(f"❌ Error Insert: {e}")

# =============================
# CLEAN COLUMN NAMES
# =============================
def clean_columns(df):
    df.columns = (
        df.columns.str.strip()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df

# =============================
# CLEAN VALUE
# =============================
def clean_value(val):
    # pd.NA, pd.NaT, None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass

    # numpy integer
    if isinstance(val, np.integer):
        return int(val)

    # numpy floating
    if isinstance(val, np.floating):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)

    # numpy bool
    if isinstance(val, np.bool_):
        return bool(val)

    # numpy array
    if isinstance(val, np.ndarray):
        return val.tolist()

    # native float (NaN / Inf)
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val

    return val

# =============================
# CLEAN FOR JSON
# =============================
def clean_for_json(df):
    df = df.copy()

    # Datetime → string
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")

    # Clean nilai per record
    records = df.to_dict(orient="records")
    cleaned = []
    for row in records:
        cleaned.append({k: clean_value(v) for k, v in row.items()})
    return cleaned

# =============================
# KATEGORI OD
# =============================
def get_kategori_od(h):
    if h < 15:
        return "Belum OD"
    elif h <= 45:      # 15–45 → OD 1
        return "OD 1"
    elif h <= 75:      # 46–75 → OD 2
        return "OD 2"
    elif h >= 76:      # >= 76 → OD 3
        return "OD 3"

# =============================
# 📂 UPLOAD EXCEL
# =============================
st.subheader("📂 Upload DB ASCII")

uploaded_file = st.file_uploader("Upload Excel (.xls/.xlsx)", type=["xls", "xlsx"])

if uploaded_file:
    try:
        ext = os.path.splitext(uploaded_file.name)[1]

        if ext == ".xls":
            df_upload = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df_upload = pd.read_excel(uploaded_file, engine="openpyxl")

        st.write("Preview Data:")
        st.dataframe(df_upload.head())

        if st.button("🚀 Upload ke DB"):
            df_upload = clean_columns(df_upload)   # ✅ bersihkan nama kolom
            data = clean_for_json(df_upload)        # ✅ bersihkan nilai

            for i in range(0, len(data), 500):
                supabase.table("db_ascii").upsert(
                    data[i:i+500],
                    on_conflict="No_Reg"
                ).execute()

            st.success("✅ Upload berhasil!")
            st.rerun()

    except Exception as e:
        st.error(f"❌ Error Upload: {e}")

# =============================
# 📝 INPUT INVOICE
# =============================
st.subheader("📝 Input Invoice")

col1, col2, col3 = st.columns(3)

with col1:
    noreg = st.text_input("No_Reg")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

with col3:
    if st.button("Tambah"):
        if not noreg:
            st.warning("No_Reg tidak boleh kosong!")
        else:
            insert_input(noreg, tgl_invoice)
            st.rerun()

# =============================
# LOAD DATA
# =============================
db = load_db()
df_input = load_input()

if not db.empty and not df_input.empty:

    # =============================
    # FORMAT DATA
    # =============================
    db["No_Reg"] = db["No_Reg"].astype(str)
    df_input["No_Reg"] = df_input["No_Reg"].astype(str)

    # =============================
    # STATUS
    # =============================
    db["status"] = db["State"].fillna("") + db["State1"].fillna("")

    # =============================
    # MERGE
    # =============================
    df = df_input.merge(db, on="No_Reg", how="left")

    # =============================
    # HITUNG OD
    # =============================
    df["Tanggal_Invoice"] = pd.to_datetime(df["Tanggal_Invoice"])
    today = pd.to_datetime(datetime.now().date())

    df["hari"] = (today - df["Tanggal_Invoice"]).dt.days
    df["kategori_od"] = df["hari"].apply(get_kategori_od)

    # =============================
    # STATUS LUNAS
    # =============================
    df["is_lunas"] = df["status"].str.contains("OVOP", na=False)
    df = df.sort_values(by=["is_lunas", "hari"], ascending=[True, False])

    # =============================
    # DISPLAY
    # =============================
    desired_cols = [
        "No_Reg", "kategori_od", "Nama_Cust", "Type",
        "Dealer", "Sales_ACC", "Brand", "status", "AF", "hari"
    ]
    cols_exist = [c for c in desired_cols if c in df.columns]
    df_display = df[cols_exist]

    # =============================
    # DASHBOARD
    # =============================
    st.subheader("📊 Dashboard")

    col1, col2, col3 = st.columns(3)

    for i, kategori_name in enumerate(["OD 1", "OD 2", "OD 3"]):
        data_od = df[df["kategori_od"] == kategori_name]
        total = len(data_od)

        if "AF" in df.columns:
            af_sum = pd.to_numeric(data_od["AF"], errors="coerce").sum()
            af_label = f"AF: {int(af_sum):,}"
        else:
            af_label = "AF: N/A"

        with [col1, col2, col3][i]:
            st.metric(kategori_name, f"{total} account", af_label)

    # =============================
    # TABLE
    # =============================
    def highlight(row):
        if "OVOP" in str(row.get("status", "")):
            return ["background-color: green"] * len(row)
        return [""] * len(row)

    st.subheader("📋 Data Monitoring")
    st.dataframe(df_display.style.apply(highlight, axis=1), use_container_width=True)

else:
    st.warning("⚠️ Upload DB ASCII dulu atau input data")
