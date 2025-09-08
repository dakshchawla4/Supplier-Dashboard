import io
import re
import streamlit as st
import polars as pl
import pandas as pd

st.set_page_config(layout="wide")

# ---------- Auth ----------
password = st.text_input("Enter Password to access the dashboard", type="password")
if password != "Newjoiner@01":
    st.stop()

# ---------- Config ----------
FILTER_COLS = [
    "Supplier_Name",
    "City",
    "State",
    "Location",
    "Category_1",
    "Category_2",
    "Category_3",
    "Product_Service",
]

def norm(s: str) -> str:
    return (s or "").strip().lower()

def clean_colname(c: str) -> str:
    # "Supplier Name" or "Category/1" -> "Supplier_Name", "Category_1"
    c2 = re.sub(r"[^0-9A-Za-z]+", "_", c.strip())
    return c2.strip("_")

def get_options(df: pl.DataFrame, col: str):
    if col not in df.columns:
        return ["All"]
    # keep first-seen display casing, match on lowercase
    values = df.select(pl.col(col).cast(pl.Utf8, strict=False)).to_series().to_list()
    uniq = {}
    for v in values:
        vv = (v or "").strip()
        if vv:
            uniq.setdefault(vv.lower(), vv)
    return ["All"] + sorted(uniq.values(), key=lambda x: x.lower())

# ---------- Data load (cached; runs once) ----------
@st.cache_data(show_spinner=True, ttl=3600)  # keeps the “app shows fast after first load”
def load_data():
    # 1) Read Excel as text to avoid ArrowTypeError & mixed types
    df_pd = pd.read_excel("excel.xlsx", engine="openpyxl", dtype=str).fillna("")
    # 2) Convert to Polars
    df = pl.from_pandas(df_pd, include_index=False)
    # 3) Standardize column names to expected ones
    df = df.rename({c: clean_colname(c) for c in df.columns})
    # 4) Ensure Utf8 for string ops
    df = df.with_columns([pl.col(c).cast(pl.Utf8, strict=False).fill_null("").alias(c) for c in df.columns])

    # Require your existing Concat
    if "Concat" not in df.columns:
        # App stays visible; user sees a clear error
        st.error("The uploaded Excel must contain a 'Concat' column. Add it and redeploy.")
        df = df.with_columns(pl.lit("").alias("Concat"))

    # Build only a quick normalized copy for searching
    df = df.with_columns(pl.col("Concat").str.to_lowercase().alias("Concat__norm"))

    # Precompute normalized columns for filters (cheap & done once)
    for c in FILTER_COLS:
        if c in df.columns:
            df = df.with_columns(
                pl.col(c).cast(pl.Utf8, strict=False).str.strip_chars().str.to_lowercase().alias(f"{c}__norm")
            )

    # Dropdown options (pretty values)
    options = {c: get_options(df, c) for c in FILTER_COLS}
    return df, options

df, options = load_data()

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
    try:
        st.image("logo.jpg", width=100)
    except Exception:
        pass

# ---------- Search & Filters ----------
search = st.text_input("Search (matches only the Concat column)", "")

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
with col1: supplierName_filter = st.selectbox("Filter by Name", options.get("Supplier_Name", ["All"]))
with col2: City_filter         = st.selectbox("Filter by City", options.get("City", ["All"]))
with col3: State_filter        = st.selectbox("Filter by State", options.get("State", ["All"]))
with col4: Location_filter     = st.selectbox("Filter by Location", options.get("Location", ["All"]))
with col5: Category1_filter    = st.selectbox("Filter by Category 1", options.get("Category_1", ["All"]))
with col6: Category2_filter    = st.selectbox("Filter by Category 2", options.get("Category_2", ["All"]))
with col7: Category3_filter    = st.selectbox("Filter by Category 3", options.get("Category_3", ["All"]))
with col8: Product_filter      = st.selectbox("Filter by Product", options.get("Product_Service", ["All"]))

# ---------- Fast filtering (uses precomputed __norm) ----------
filtered = df

def apply_eq(frame: pl.DataFrame, col: str, selected: str) -> pl.DataFrame:
    norm_col = f"{col}__norm"
    if selected == "All" or norm_col not in frame.columns:
        return frame
    return frame.filter(pl.col(norm_col) == norm(selected))

filtered = apply_eq(filtered, "Supplier_Name",   supplierName_filter)
filtered = apply_eq(filtered, "City",            City_filter)
filtered = apply_eq(filtered, "State",           State_filter)
filtered = apply_eq(filtered, "Location",        Location_filter)
filtered = apply_eq(filtered, "Category_1",      Category1_filter)
filtered = apply_eq(filtered, "Category_2",      Category2_filter)
filtered = apply_eq(filtered, "Category_3",      Category3_filter)
filtered = apply_eq(filtered, "Product_Service", Product_filter)

# Search ONLY your prebuilt Concat (normalized once)
if search.strip() and "Concat__norm" in filtered.columns:
    terms = [t.strip().lower() for t in search.split() if t.strip()]
    for t in terms:
        filtered = filtered.filter(pl.col("Concat__norm").str.contains(t, literal=True))

# Hide helper columns in the UI (keep Concat out of the table)
HIDDEN_COLS = ["Concat", "Concat__norm"] + [f"{c}__norm" for c in FILTER_COLS]
display_df = filtered.drop(HIDDEN_COLS, strict=False)

# ---------- Table (limit rows before converting to pandas) ----------
MAX_ROWS = 2000  # lower to 1000 if your browser feels sluggish
st.dataframe(display_df.head(MAX_ROWS).to_pandas(), use_container_width=True)

# ---------- Download (include Concat in export) ----------
if filtered.height > 0:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        filtered.to_pandas().to_excel(write)








