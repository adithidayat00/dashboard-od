import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

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
def insert_input(no_kontrak, tgl_invoice):
    supabase.table("input_data").insert({
        "no_kontrak": str(no_kontrak),
        "tgl_invoice": pd.to_datetime(tgl_invoice).strftime("%Y-%m-%d")
    }).execute()

# =============================
# UI INPUT
# =============================
st.subheader("📝 Input Invoice")

col1, col2, col3 = st.columns(3)

with col1:
    no_kontrak = st.text_input("NoReg")

with col2:
    tgl_invoice = st.date_input("Tanggal Invoice")

with col3:
    if st.button("Tambah"):
        insert_input(no_kontrak, tgl_invoice)
        st.rerun()

# =============================
# LOAD DATA
# =============================
db = load_db()
df_input = load_input()

if not db.empty and not df_input.empty:

    db["no_kontrak"] = db["no_kontrak"].astype(str)
    df_input["no_kontrak"] = df_input["no_kontrak"].astype(str)

    # 🔥 gabung state
    db["status"] = db["state"].fillna("") + db["state1"].fillna("")

    # 🔥 merge
    df = df_input.merge(db, on="no_kontrak", how="left")

    # =============================
    # HITUNG OD
    # =============================
    df["tgl_invoice"] = pd.to_datetime(df["tgl_invoice"])
    today = pd.to_datetime(datetime.today().date())

    df["hari"] = (today - df["tgl_invoice"]).dt.days

    def kategori(h):
        if h < 15:
            return "Belum OD"
        elif 15 <= h <= 45:
            return "OD 1"
        elif 46 <= h <= 75:
            return "OD 2"
        else:
            return "OD 3"

    df["kategori_od"] = df["hari"].apply(kategori)

    # =============================
    # STATUS LUNAS (OVOP)
    # =============================
    df["is_lunas"] = df["status"].str.contains("OVOP", na=False)

    # =============================
    # SORTING
    # =============================
    df = df.sort_values(by=["is_lunas", "hari"], ascending=[True, False])

    # =============================
    # KOLOM FINAL
    # =============================
    df_display = df[[
        "no_kontrak",
        "kategori_od",
        "nama_cust",
        "type",
        "dealer",
        "so",
        "brand",
        "status",
        "af",
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
        af_sum = pd.to_numeric(data["af"], errors="coerce").sum()

        with [col1, col2, col3][i]:
            st.metric(kategori_name, f"{total} account", f"AF: {int(af_sum):,}")

    # =============================
    # HIGHLIGHT
    # =============================
    def highlight(row):
        if row["status"] and "OVOP" in row["status"]:
            return ["background-color: green"] * len(row)
        return [""] * len(row)

    st.subheader("📋 Data Monitoring")
    st.dataframe(df_display.style.apply(highlight, axis=1), use_container_width=True)

else:
    st.warning("⚠️ Upload DB ASCII dulu atau input data")
