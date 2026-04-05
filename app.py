import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# =============================
# 🔑 SUPABASE CONFIG
# =============================
SUPABASE_URL = "https://jrikxltaaxlipbgturju.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpyaWt4bHRhYXhsaXBiZ3R1cmp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyODMxNzEsImV4cCI6MjA5MDg1OTE3MX0.gloC3nfdIx7q9rV8kEXcKsAaZpJB9nOeyvRRS4yY-6U"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Monitoring OD", layout="wide")

st.title("📊 Sistem Monitoring OD")

# =============================
# 📥 LOAD DATABASE ASCII (SUPABASE)
# =============================
def load_db():
    try:
        res = supabase.table("db_ascii").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# =============================
# 📥 LOAD INPUT USER
# =============================
def load_input():
    try:
        res = supabase.table("input_data").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# =============================
# 📤 UPLOAD DATABASE ASCII
# =============================
def upload_db(df):
    df = df.drop_duplicates(subset=["no_kontrak"])

    # 🔥 convert semua ke string
    df = df.astype(str)

    # 🔥 bersihin value rusak
    df = df.replace({
        "nan": None,
        "NaT": None,
        "None": None,
        "": None
    })

    # 🔥 fix tanggal
    if "tanggal_valid" in df.columns:
        df["tanggal_valid"] = pd.to_datetime(
            df["tanggal_valid"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    data = df.to_dict(orient="records")

    # 🔥 insert per row biar ga error massal
    for row in data:
        try:
            supabase.table("db_ascii").insert(row).execute()
        except:
            pass

# =============================
# 📤 INSERT INPUT USER
# =============================
def insert_input(no_kontrak, tgl_invoice):
    supabase.table("input_data").insert({
        "no_kontrak": str(no_kontrak),
        "tgl_invoice": str(tgl_invoice)
    }).execute()

# =============================
# 📤 DELETE INPUT
# =============================
def delete_input(id):
    supabase.table("input_data").delete().eq("id", id).execute()

# =============================
# 📂 UPLOAD ASCII (SEKALI SAJA)
# =============================
st.subheader("📤 Upload Database (sekali saja)")

db_file = st.file_uploader("Upload file ASCII", type=["xlsx", "xls"])

if db_file:
    db = pd.read_excel(db_file)

    # rename sesuai database
    db = db.rename(columns={
        "NoReg": "no_kontrak",
        "NamaCust": "nama_cust",
        "TglVld": "tanggal_valid",
        "State": "status_bayar"
    })

    upload_db(db)
    st.success("✅ Database berhasil disimpan ke Supabase!")

# =============================
# 📥 INPUT USER
# =============================
st.subheader("📝 Input Data Invoice")

col1, col2, col3 = st.columns(3)

with col1:
    no_kontrak = st.text_input("No Kontrak")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

with col3:
    if st.button("Tambah"):
        if no_kontrak:
            insert_input(no_kontrak, tgl_invoice)
            st.success("Data masuk!")
            st.rerun()

# =============================
# 📊 LOAD DATA
# =============================
db = load_db()
df_input = load_input()

if not df_input.empty and not db.empty:

    df_input["no_kontrak"] = df_input["no_kontrak"].astype(str)
    db["no_kontrak"] = db["no_kontrak"].astype(str)

    df = df_input.merge(
        db[["no_kontrak", "nama_cust", "tanggal_valid", "status_bayar"]],
        on="no_kontrak",
        how="left"
    )

    # =============================
    # 🧠 HITUNG OD
    # =============================
    df["tgl_invoice"] = pd.to_datetime(df["tgl_invoice"], errors="coerce")
    df["tanggal_valid"] = pd.to_datetime(df["tanggal_valid"], errors="coerce")

    df["selisih_hari"] = (df["tgl_invoice"] - df["tanggal_valid"]).dt.days

    def kategori(x):
        if pd.isna(x):
            return "Tidak Valid"
        elif x <= 0:
            return "Tidak Masuk OD"
        elif x <= 30:
            return "OD 1-30"
        elif x <= 60:
            return "OD 31-60"
        else:
            return "OD > 60"

    df["kategori_od"] = df["selisih_hari"].apply(kategori)

    # =============================
    # 🔥 SORT (BELUM BAYAR DI ATAS)
    # =============================
    df["status_sort"] = df["status_bayar"].apply(
        lambda x: 1 if x == "LUNAS" else 0
    )

    df = df.sort_values(by=["status_sort", "selisih_hari"], ascending=[True, False])

    # =============================
    # 🎨 HIGHLIGHT LUNAS
    # =============================
    def highlight(row):
        if row["status_bayar"] == "LUNAS":
            return ["background-color: red"] * len(row)
        return [""] * len(row)

    st.subheader("📋 Data Monitoring")
    st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True)

    # =============================
    # ❌ DELETE DATA
    # =============================
    st.subheader("🗑️ Hapus Data")

    for i, row in df.iterrows():
        if st.button(f"Hapus {row['no_kontrak']}", key=i):
            delete_input(row["id"])
            st.rerun()

else:
    st.warning("⚠️ Data belum lengkap (upload ASCII dulu atau input data)")
