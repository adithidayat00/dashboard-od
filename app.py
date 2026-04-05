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
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWt4bHRhYXhsaXBiZ3R1cmp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyODMxNzEsImV4cCI6MjA5MDg1OTE3MX0.gloC3nfdIx7q9rV8kEXcKsAaZpJB9nOeyvRRS4yY-6U"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# FUNCTION
# =========================
def insert_data(no_kontrak, tgl_invoice):
    supabase.table("input_data").insert({
        "no_kontrak": str(no_kontrak),
        "tgl_invoice": str(tgl_invoice)
    }).execute()

def load_input():
    try:
        res = supabase.table("input_data").select("*").execute()
        df = pd.DataFrame(res.data)

        if not df.empty:
            df["tgl_invoice"] = pd.to_datetime(df["tgl_invoice"], errors="coerce")

        return df
    except:
        return pd.DataFrame()

def load_db():
    try:
        res = supabase.table("db_ascii").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# 🔥 FIX TOTAL UPLOAD (ANTI ERROR)
def upload_db(df):
    df = df.drop_duplicates(subset=["no_kontrak"])

    # bersihin data
    df = df.replace({pd.NA: None})
    df = df.replace({float("nan"): None})

    # fix tanggal
    if "tanggal_valid" in df.columns:
        df["tanggal_valid"] = pd.to_datetime(
            df["tanggal_valid"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    # convert semua ke string / None
    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x) if x not in [None, "None"] else None)

    data = df.to_dict(orient="records")

    # 🔥 batch biar aman
    batch_size = 500
    for i in range(0, len(data), batch_size):
        supabase.table("db_ascii").insert(data[i:i+batch_size]).execute()

# =========================
# LOAD DB
# =========================
db = load_db()

# =========================
# UPLOAD (CUMA SEKALI)
# =========================
if db.empty:
    st.subheader("📥 Upload Database (sekali saja)")

    file = st.file_uploader("Upload Database ASCII", type=["xlsx", "xls"])

    if file:
        db = pd.read_excel(file)

        # 🔥 bersihin kolom
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

        upload_db(db)

        st.success("Database berhasil disimpan ✅")
        st.rerun()

# =========================
# LOAD DB ULANG
# =========================
db = load_db()

if db.empty:
    st.warning("⚠️ Database belum tersedia")
    st.stop()

# =========================
# INPUT USER
# =========================
st.subheader("📥 Input Data Harian")

col1, col2 = st.columns(2)

with col1:
    no_reg = st.text_input("NoReg")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

if st.button("➕ Tambah Data"):
    if no_reg:
        insert_data(no_reg, tgl_invoice)
        st.success("Data berhasil ditambahkan ✅")
        st.rerun()

# =========================
# LOAD INPUT
# =========================
df = load_input()

if not df.empty:

    df["no_kontrak"] = df["no_kontrak"].astype(str).str.strip()
    db["no_kontrak"] = db["no_kontrak"].astype(str).str.strip()

    # =========================
    # VLOOKUP
    # =========================
    df = df.merge(
        db[["no_kontrak", "nama_cust", "tanggal_valid", "status_bayar"]],
        on="no_kontrak",
        how="left"
    )

    # =========================
    # HITUNG
    # =========================
    df["tanggal_valid"] = pd.to_datetime(df["tanggal_valid"], errors="coerce")
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

    # =========================
    # PRIORITAS + CA
    # =========================
    order = {"OD3": 1, "OD2": 2, "OD1": 3, "Tidak Masuk OD": 4, "Tidak Valid": 5}
    df["priority"] = df["kategori_od"].map(order)

    # 🔥 CA paling bawah
    df.loc[df["status_bayar"].str.upper() == "CA", "priority"] = 99

    df = df.sort_values("priority")

    # =========================
    # 🔴 HIGHLIGHT
    # =========================
    def highlight(row):
        if str(row["status_bayar"]).upper() == "CA":
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
    # TAMPIL
    # =========================
    st.subheader("📋 Data Monitoring")
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
        file_name="monitoring_od.xlsx"
    )
