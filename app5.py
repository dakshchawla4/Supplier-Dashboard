import os
import io
import streamlit as st
import polars as pl
import pandas as pd

st.set_page_config(layout="wide")

# === Your Excel file (path + name) ===
EXCEL_FILE = "excel.xlsx"   # keep this file in the repo root

# ---------- Password gate ----------
password = st.text_input("Enter Password to access the dashboard", type="password")
if password != "Newjoiner@01":
    st.stop()

# ---------- Helpers ----------
def safe_get_options(df: pl.DataFrame, col: str):
    if col not in df.columns:
        return ["All"]
    ser = (
        df.select(pl.col(col).cast(pl.Utf8, strict=False))
          .drop_nulls()
          .select(pl.col(col).str.strip().str.to_lowercase())
          .to_series()
    )
    vals = sorted({v for v in ser.to_list() if v})
    return ["All"] + vals

def apply_eq_filter(frame: pl.DataFrame, col: str, val: str) -> pl.DataFrame:
    if val == "All" or col not in frame.columns:
        return frame
    return frame.filter(pl.col(col).str.to_lowercase() == val)

def _read_excel_from_path(path: str) -> pd.DataFrame:
    """Always read bytes so the engine never gets a bool/str."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 1024:
        st.warning(
            f"`{path}` looks very small ({len(data)} bytes). "
            "If the file on GitHub shows 'version https://git-lfs.github.com/spec/v1', "
            "you committed a Git LFS pointer instead of the real Excel."
        )
    return pd.read_excel(io.BytesIO(data), engine="openpyxl")

# ---------- Data load (cached) ----------
@st.cache_data(show_spinner=True, ttl=600)
def load_data(explicit_path: str) -> pl.DataFrame:
    try:
        df_pd = None
        if explicit_path and os.path.isfile(explicit_path):
            df_pd = _read_excel_from_path(explicit_path)
        else:
            st.warning(
                f"Could not find `{explicit_path}` in the app directory. "
                "Upload an Excel file below to proceed."
            )

        # Upload fallback if the file isn't present
        if df_pd is None:
            up = st.file_uploader("Upload an Excel file", type=["xlsx"])
            if up is None:
                return pl.DataFrame()
            df_pd = pd.read_excel(up, engine="openpyxl")

        # Convert to Polars
        df = pl.from_pandas(df_pd)

        # Normalize column names: spaces & slashes -> underscores (matches filter names)
        df = df.rename({c: c.strip().replace("/", "_").replace(" ", "_") for c in df.columns})

        # Cast to strings for consistent filtering/search
        df = df.with_columns([pl.col(c).cast(pl.Utf8, strict=False).alias(c) for c in df.columns])

        # Build searchable blob once
        if "Concat" not in df.columns:
            df = df.with_columns([
                pl.concat_str([pl.col(c).fill_null("") for c in df.columns], separator=" ").alias("Concat")
            ])

        return df

    except Exception as e:
        st.error(f"Failed to load Excel file: {e}")
        return pl.DataFrame()

st.caption(f"📄 Attempting to load: **{EXCEL_FILE}**")
df = load_data(EXCEL_FILE)

# ---------- Styles ----------
st.markdown("""
<style>
input, select, textarea, option { color:#1a1a1a !important; background-color:white !important; }
label, .stTextInput > label, .stSelectbox > label, .stMarkdown h3, .stMarkdown h4 { color:White!important; }
[data-testid="stAppViewContainer"] { background-color: #0F1C2E; }
.white-box { background-color: white; padding: 1.5rem; border-radius: 10px; display: flex; align-items: center; justify-content: space-between; }
.title-text { font-size:28px; font-weight:bold; color:#102A43; display:flex; align-items:center; }
.symbol { font-size:34px; margin-right:15px; color:#102A43; }
button[kind="download"] { background-color:#1E88E5 !important; color:white!important; border:none!important; padding: 10px 20px!important; border-radius: 5px!important; font-weight: bold!important; }
button .stButton button { color: Black!important; }
</style>
""", unsafe_allow_html=True)

# ---------- Header ----------
left_col, right_col = st.columns([6,1])
with left_col:
    st.markdown("""
        <div style="background-color: white; padding: 20px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center;">
            <span style="color: #0F1C2E; font-size: 26px; font-weight: bold;">Supplier Dashboard</span>
        </div>
    """, unsafe_allow_html=True)
with right_col:
    st.markdown('<div style="padding: 20px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center;"></div>',
                unsafe_allow_html=True)
    try:
        st.image("logo.jpg", width=100)
    except Exception:
        pass

# ---------- Filters ----------
search = st.text_input("Search", "")

SupplierName_options = safe_get_options(df, "Supplier_Name")
City_options        = safe_get_options(df, "City")
State_options       = safe_get_options(df, "State")
Location_options    = safe_get_options(df, "Location")
Category1_options   = safe_get_options(df, "Category_1")
Category2_options   = safe_get_options(df, "Category_2")
Category3_options   = safe_get_options(df, "Category_3")
Product_options     = safe_get_options(df, "Product_Service")

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
with col1: supplierName_filter = st.selectbox("Filter by Name", SupplierName_options)
with col2: City_filter         = st.selectbox("Filter by City", City_options)
with col3: State_filter        = st.selectbox("Filter by State", State_options)
with col4: Location_filter     = st.selectbox("Filter by Location", Location_options)
with col5: Category1_filter    = st.selectbox("Filter by Category 1", Category1_options)
with col6: Category2_filter    = st.selectbox("Filter by Category 2", Category2_options)
with col7: Category3_filter    = st.selectbox("Filter by Category 3", Category3_options)
with col8: Product_filter      = st.selectbox("Filter by Product", Product_options)

# ---------- Apply filters ----------
filtered_df = df
filtered_df = apply_eq_filter(filtered_df, "Supplier_Name",   supplierName_filter)
filtered_df = apply_eq_filter(filtered_df, "City",            City_filter)
filtered_df = apply_eq_filter(filtered_df, "State",           State_filter)
filtered_df = apply_eq_filter(filtered_df, "Location",        Location_filter)
filtered_df = apply_eq_filter(filtered_df, "Category_1",      Category1_filter)
filtered_df = apply_eq_filter(filtered_df, "Category_2",      Category2_filter)
filtered_df = apply_eq_filter(filtered_df, "Category_3",      Category3_filter)
filtered_df = apply_eq_filter(filtered_df, "Product_Service", Product_filter)

if search and "Concat" in filtered_df.columns:
    filtered_df = filtered_df.filter(
        pl.col("Concat").str.to_lowercase().str.contains(search.lower())
    )

filtered_df_no_concat = filtered_df.drop(["Concat"], strict=False)

# ---------- Table ----------
st.dataframe(
    filtered_df_no_concat.head(4000).to_pandas(),
    use_container_width=True
)

# ---------- Download ----------
if filtered_df_no_concat.height > 0:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        filtered_df_no_concat.to_pandas().to_excel(writer, index=False, sheet_name="Sheet")
        buffer.seek(0)
    st.download_button(
        label="Export Search Results",
        data=buffer.getvalue(),
        file_name="Supplier_Dashboard_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data to export. Please adjust your filters or search.")




















