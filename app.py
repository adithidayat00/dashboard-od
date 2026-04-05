import streamlit as st
import pandas as pd
from io import BytesIO
from supabase import create_client

st.set_page_config(page_title="Monitoring OD", layout="wide")

st.title("📊 Sistem Monitoring OD")

# =========================
# SUPABASE
# =========================
SUPABASE_URL = "https://jrikxltaaxlipbgturju.supabase.co"
SUPABASE_KEY = "ISI_ANON_KEY_LO"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# FUNCTION
# =========================
def insert_data(no_kontrak, tgl_invoice):
    supabase.table("input_data").insert({
        "no_kontrak": str(no_kontrak),
        "tgl_invoice": str(tgl_invoice)
    }).execute()

def load_data():
    res = supabase.table("input_data").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        df["tgl_invoice"] = pd.to_datetime(df["tgl_invoice"], errors="coerce")

    return df

# 🔥 TANPA DELETE (FIX ERROR)
def upload_db(df):
    df = df.drop_duplicates(subset=["no_kontrak"])
    supabase.table("db_ascii").insert(df.to_dict(orient="records")).execute()

def load_db():
    res = supabase.table("db_ascii").select("*").execute()
    return pd.DataFrame(res.data)

# =========================
# UPLOAD ASCII (SEKALI)
# =========================
st.subheader("📥 Upload Database (sekali saja)")

db_file = st.file_uploader("Upload Database ASCII", type=["xlsx", "xls"])

if db_file:
    db = pd.read_excel(db_file)

    db.columns = (
        db.columns.str.strip()
        .str.lower()
        .str.replace(" ", "")
        .str.replace("'", "")
    )

    mapping = {
        "noreg": "no_kontrak",
        "namacust": "nama_cust",
        "tglvld": "tanggal_valid",
        "tglvalid": "tanggal_valid",
        "state": "status_bayar"
    }

    db.rename(columns={k: v for k, v in mapping.items() if k in db.columns}, inplace=True)

    db["tanggal_valid"] = pd.to_datetime(db["tanggal_valid"], errors="coerce")

    upload_db(db)

    st.success("Database berhasil disimpan ✅")

# =========================
# LOAD DATABASE
# =========================
db = load_db()

if db.empty:
    st.warning("⚠️ Upload database dulu")
    st.stop()

# =========================
# INPUT USER
# =========================
st.subheader("📥 Input Data")

col1, col2 = st.columns(2)

with col1:
    no_reg = st.text_input("NoReg")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

if st.button("➕ Tambah"):
    if no_reg:
        insert_data(no_reg, tgl_invoice)
        st.success("Data masuk ✅")

# =========================
# LOAD INPUT
# =========================
df = load_data()

if not df.empty:

    df["no_kontrak"] = df["no_kontrak"].astype(str).str.strip()
    db["no_kontrak"] = db["no_kontrak"].astype(str).str.strip()

    # VLOOKUP
    df = df.merge(
        db[["no_kontrak", "nama_cust", "tanggal_valid", "status_bayar"]],
        on="no_kontrak",
        how="left"
    )

    # HITUNG OD
    df["selisih_hari"] = (df["tanggal_valid"] - df["tgl_invoice"]).dt.days

    def kategori(x):
        if pd.isna(x):
            return "Tidak Valid"
        elif 15 <= x <= 45:
            return "OD1"
        elif 46 <= x <= 75:
            return "OD2"
        elif x > 75:
            return "OD3"
        else:
            return "Tidak Masuk OD"

    df["kategori_od"] = df["selisih_hari"].apply(kategori)

    # SORT PRIORITAS
    order = {"OD3": 1, "OD2": 2, "OD1": 3, "Tidak Masuk OD": 4, "Tidak Valid": 5}
    df["priority"] = df["kategori_od"].map(order)

    df = df.sort_values("priority")

    # TAMPIL
    st.subheader("📋 Data Monitoring")
    st.dataframe(df, use_container_width=True)

    # DOWNLOAD
    def to_excel(data):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            data.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button("📥 Download Excel", to_excel(df), "monitoring.xlsx")
