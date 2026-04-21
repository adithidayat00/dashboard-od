import numpy as np

# =========================
# UPLOAD MASTER DATA
# =========================
st.subheader("📤 Upload Master Data")

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])

if uploaded_file:

    df_excel = pd.read_excel(uploaded_file)

    # Rename kolom
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

    # Pastikan AF numeric
    df_excel["af"] = pd.to_numeric(df_excel["af"], errors="coerce").fillna(0)

    st.dataframe(df_excel.head())

    if st.button("Upload ke Database"):

        try:
            df_clean = df_excel.copy()

            # 1. Replace NaN → None
            df_clean = df_clean.replace({np.nan: None})

            # 2. Convert datetime → string
            for col in df_clean.columns:
                if str(df_clean[col].dtype).startswith("datetime"):
                    df_clean[col] = df_clean[col].astype(str)

            # 3. Convert numpy → python native
            df_clean = df_clean.applymap(
                lambda x: x.item() if hasattr(x, "item") else x
            )

            # 4. Convert ke dict
            data = df_clean.to_dict(orient="records")

            # 5. Upload ke Supabase
            supabase.table("db_ascii").upsert(data).execute()

            st.success("✅ Upload berhasil!")

        except Exception as e:
            st.error(f"❌ Error upload: {e}")
