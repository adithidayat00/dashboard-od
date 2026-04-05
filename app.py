import streamlit as st
import pandas as pd
from io import BytesIO
from supabase import create_client

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Monitoring OD", layout="wide")

st.title("📊 Sistem Monitoring OD")

# =========================
# SUPABASE
# =========================
SUPABASE_URL = "https://jrikxltaaxlipbgturju.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWt4bHRhYXhsaXBiZ3R1cmp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyODMxNzEsImV4cCI6MjA5MDg1OTE3MX0.gloC3nfdIx7q9rV8kEXcKsAaZpJB9nOeyvRRS4yY-6U"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# 🔒 ADMIN LOGIN (HIDDEN MODE)
# =========================
st.sidebar.title("🔐 Admin Access")

admin_mode = False
password = st.sidebar.text_input("Masukkan Password Admin", type="password")

if password == "banjarmasin002":
    admin_mode = True
    st.sidebar.success("Admin Mode Aktif")
elif password:
    st.sidebar.error("Password salah")

# =========================
# FUNCTION SUPABASE
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

def upload_db_to_supabase(df):
    supabase.table("db_ascii").delete().neq("no_kontrak", "").execute()
    data = df.to_dict(orient="records")
    supabase.table("db_ascii").insert(data).execute()

def load_db_ascii():
    res = supabase.table("db_ascii").select("*").execute()
    return pd.DataFrame(res.data)

# =========================
# ADMIN PANEL (HIDDEN)
# =========================
if admin_mode:
    st.markdown("### ⚙️ Admin Panel - Upload Database")

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

        upload_db_to_supabase(db)

        st.success("Database berhasil diupload ✅")

# =========================
# LOAD DATABASE
# =========================
db = load_db_ascii()

if db.empty:
    st.warning("⚠️ Database belum tersedia. Hubungi admin.")
    st.stop()

# =========================
# INPUT USER
# =========================
st.markdown("### 📥 Input Invoice")

col1, col2 = st.columns(2)

with col1:
    no_reg = st.text_input("NoReg")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

if st.button("➕ Tambah Data"):
    if not no_reg:
        st.warning("NoReg wajib diisi")
    elif len(no_reg) < 5:
        st.warning("NoReg tidak valid")
    else:
        insert_data(no_reg, tgl_invoice)
        st.success("Data berhasil disimpan ✅")

# =========================
# LOAD INPUT DATA
# =========================
df = load_data()

if not df.empty:

    df["no_kontrak"] = df["no_kontrak"].astype(str).str.strip()
    db["no_kontrak"] = db["no_kontrak"].astype(str).str.strip()

    df = df.merge(
        db[["no_kontrak", "nama_cust", "tanggal_valid", "status_bayar"]],
        on="no_kontrak",
        how="left"
    )

    # =========================
    # HITUNG OD
    # =========================
    df["selisih_hari"] = (df["tanggal_valid"] - df["tgl_invoice"]).dt.days

    def klasifikasi_od(x):
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

    df["kategori_od"] = df["selisih_hari"].apply(klasifikasi_od)

    # =========================
    # SORT PRIORITAS
    # =========================
    order_map = {"OD3": 1, "OD2": 2, "OD1": 3, "Tidak Masuk OD": 4, "Tidak Valid": 5}
    df["priority"] = df["kategori_od"].map(order_map)

    df["paid_flag"] = df["status_bayar"].astype(str).str.upper().str.contains("OV")

    df = df.sort_values(["paid_flag", "priority"])

    # =========================
    # SEARCH
    # =========================
    st.markdown("### 🔍 Pencarian")

    search = st.text_input("Cari NoReg / Nama Customer")

    if search:
        df = df[
            df["no_kontrak"].str.contains(search, case=False, na=False) |
            df["nama_cust"].str.contains(search, case=False, na=False)
        ]

    # =========================
    # STYLE WARNA
    # =========================
    def highlight(row):
        if row["paid_flag"]:
            return ["background-color: #ff4d4d"] * len(row)
        elif row["kategori_od"] == "OD3":
            return ["background-color: #ff9999"] * len(row)
        elif row["kategori_od"] == "OD2":
            return ["background-color: #ffe066"] * len(row)
        elif row["kategori_od"] == "OD1":
            return ["background-color: #b3ffb3"] * len(row)
        else:
            return [""] * len(row)

    styled_df = df.style.apply(highlight, axis=1)

    # =========================
    # TABEL
    # =========================
    st.markdown("### 📋 Data Monitoring")
    st.write(styled_df)

    # =========================
    # DOWNLOAD
    # =========================
    def to_excel(data):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            data.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button(
        "📥 Download Excel",
        to_excel(df),
        "monitoring_od.xlsx"
    )
