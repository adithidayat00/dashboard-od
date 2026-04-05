import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from datetime import datetime
import os
import re

# =============================
# 🔑 CONFIG
# =============================
SUPABASE_URL = "https://jrikxltaaxlipbgturju.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWt4bHRhYXhsaXBiZ3R1cmp1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTI4MzE3MSwiZXhwIjoyMDkwODU5MTcxfQ.08ArMKSDHRnQRy8lM3j7jKKG9IFrDBf6g0xeYxfyVgg"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(layout="wide")
st.title("📊 Sistem Monitoring OD")

# =============================
# NORMALIZE No_Reg
# =============================
def normalize_noreg(series):
    return (
        series.astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.replace(r"\s+", "", regex=True)
        .str.replace(r"[^\d]", "", regex=True)
        .str.strip()
    )

# =============================
# AUTO MAP KOLOM
# =============================
def auto_map_columns(df):
    mapping = {}

    for col in df.columns:
        c = col.lower().replace(" ", "").replace("_", "")

        if "noreg" in c:
            mapping[col] = "No_Reg"
        elif "nama" in c:
            mapping[col] = "Nama_Cust"
        elif "dealer" in c:
            mapping[col] = "Dealer"
        elif "sales" in c:
            mapping[col] = "Sales_ACC"
        elif "brand" in c or "merk" in c:
            mapping[col] = "Brand"
        elif "type" in c:
            mapping[col] = "Type"
        elif c == "state":
            mapping[col] = "State"
        elif c == "state1":
            mapping[col] = "State1"
        elif c == "af":
            mapping[col] = "AF"

    return df.rename(columns=mapping)

# =============================
# VALID COLUMNS
# =============================
VALID_COLUMNS = [
    "No_Reg", "Nama_Cust", "Dealer",
    "Sales_ACC", "Brand", "Type",
    "State", "State1", "AF"
]

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
            "No_Reg": str(noreg).strip(),
            "Tanggal_Invoice": pd.to_datetime(tgl_invoice).strftime("%Y-%m-%d")
        }).execute()
        st.success("✅ Data berhasil ditambahkan")
    except Exception as e:
        st.error(f"❌ Error Insert: {e}")

# =============================
# CLEAN JSON
# =============================
def clean_for_json(df):
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
    return df.replace({np.nan: None}).to_dict(orient="records")

# =============================
# 📂 UPLOAD EXCEL
# =============================
st.subheader("📂 Upload DB ASCII")

uploaded_file = st.file_uploader("Upload Excel", type=["xls", "xlsx"])

if uploaded_file:
    try:
        ext = os.path.splitext(uploaded_file.name)[1]

        if ext == ".xls":
            df_upload = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df_upload = pd.read_excel(uploaded_file, engine="openpyxl")

        st.write("Preview:")
        st.dataframe(df_upload.head())

        if st.button("🚀 Upload ke DB"):

            # AUTO MAP
            df_upload = auto_map_columns(df_upload)

            if "No_Reg" not in df_upload.columns:
                st.error("❌ Kolom No_Reg tidak ditemukan!")
                st.stop()

            # NORMALIZE
            df_upload["No_Reg"] = normalize_noreg(df_upload["No_Reg"])
            df_upload = df_upload[df_upload["No_Reg"] != ""]

            # FILTER KOLOM VALID
            df_upload = df_upload[[col for col in df_upload.columns if col in VALID_COLUMNS]]

            st.write("Kolom final:", df_upload.columns.tolist())

            data = clean_for_json(df_upload)

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
            st.warning("No_Reg kosong!")
        else:
            insert_input(noreg, tgl_invoice)
            st.rerun()

# =============================
# LOAD DATA
# =============================
db = load_db()
df_input = load_input()

if not db.empty and not df_input.empty:

    db["No_Reg"] = normalize_noreg(db["No_Reg"])
    df_input["No_Reg"] = normalize_noreg(df_input["No_Reg"])

    # 🔥 FIX STATUS (STATE + STATE1 TANPA SPASI)
    db["status"] = (
        db["State"].fillna("").str.strip() +
        db["State1"].fillna("").str.strip()
    )

    # MERGE
    df = df_input.merge(db, on="No_Reg", how="left")

    st.write("MATCH CHECK:", df_input["No_Reg"].isin(db["No_Reg"]))

    # =============================
    # HITUNG OD
    # =============================
    df["Tanggal_Invoice"] = pd.to_datetime(df["Tanggal_Invoice"])
    today = pd.to_datetime(datetime.now().date())

    df["hari"] = (today - df["Tanggal_Invoice"]).dt.days

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

    # DETEKSI LUNAS
    df["is_lunas"] = df["status"].str.contains("OV|OP", na=False)

    df = df.sort_values(by=["is_lunas", "hari"], ascending=[True, False])

    # =============================
    # DASHBOARD
    # =============================
    st.subheader("📊 Dashboard")

    col1, col2, col3 = st.columns(3)
    df_aktif = df[~df["is_lunas"]]

    for i, k in enumerate(["OD 1", "OD 2", "OD 3"]):
        d = df_aktif[df_aktif["kategori_od"] == k]
        total = len(d)
        af_sum = pd.to_numeric(d["AF"], errors="coerce").sum()

        with [col1, col2, col3][i]:
            st.metric(k, f"{total} account", f"AF: {int(af_sum):,}")

    # =============================
    # HIGHLIGHT
    # =============================
    def highlight(row):
        if re.search("OV|OP", str(row["status"])):
            return ["background-color: green"] * len(row)
        return [""] * len(row)

    cols = [
        "No_Reg", "kategori_od", "Nama_Cust", "Type",
        "Dealer", "Sales_ACC", "Brand", "status", "AF", "hari"
    ]

    # =============================
    # DATA AKTIF
    # =============================
    st.subheader("📋 Data Monitoring (Aktif)")
    st.dataframe(df_aktif[cols].style.apply(highlight, axis=1), use_container_width=True)

    # =============================
    # DATA LUNAS
    # =============================
    st.subheader("✅ Data Lunas (OV / OP)")
    df_lunas = df[df["is_lunas"]]

    st.dataframe(df_lunas[cols].style.apply(highlight, axis=1), use_container_width=True)

else:
    st.warning("⚠️ Upload DB ASCII dulu atau input data")
