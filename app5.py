import io
import re
import time
import pandas as pd
import polars as pl
import streamlit as st

st.set_page_config(layout="wide")

# -------------------- Auth --------------------
password = st.text_input("Enter Password to access the dashboard", type="password")
if password != "Newjoiner@01":
    st.stop()

# -------------------- Helpers --------------------
def _norm(s: str) -> str:
    # normalize a column label to compare across variants
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)  # spaces, slashes -> underscore
    s = re.sub(r"_+", "_", s).strip("_")
    return s

# Canonical targets you want to use in code
CANON = {
    "supplier_name": "Supplier_Name",
    "city": "City",
    "state": "State",
    "location": "Location",
    "category_1": "Category_1",
    "category_2": "Category_2",
    "category_3": "Category_3",
    "product_service": "Product_Service",
    "concat": "Concat",
}

# Common synonyms -> canonical key (left side uses our _norm form)
SYNONYMS = {
    # supplier
    "supplier_name": "supplier_name",
    "suppliername": "supplier_name",
    # city/state/location
    "city": "city",
    "state": "state",
    "location": "location",
    # product/service
    "product_service": "product_service",
    "productservice": "product_service",
    "product_services": "product_service",
    "product": "product_service",
    "service": "product_service",
    # categories
    "category_1": "category_1",
    "category1": "category_1",
    "category_2": "category_2",
    "category2": "category_2",
    "category_3": "category_3",
    "category3": "category_3",
    # search column
    "concat": "concat",
    "search_blob": "concat",
    "search": "concat",
}

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

# -------------------- Data load (cached) --------------------
@st.cache_data(show_spinner=True)
def load_data(excel_path: str = "excel.xlsx") -> pl.DataFrame:
    # Read ALL columns as strings (fast & consistent)
    df_pd = pd.read_excel(excel_path, engine="openpyxl", dtype=str)
    df_pd = df_pd.fillna("")  # ensure empty strings instead of NaN

    # Rename columns to canonical labels
    rename_map = {}
    for col in df_pd.columns:
        key = _norm(col)
        if key in SYNONYMS:
            canon_key = SYNONYMS[key]
            rename_map[col] = CANON[canon_key]
    if rename_map:
        df_pd = df_pd.rename(columns=rename_map)

    # Validate presence of required columns
    missing = [c for c in ["Concat"] if c not in df_pd.columns]
    if missing:
        raise ValueError(
            f"Missing column(s) {missing}. Your Excel must include a prebuilt 'Concat' column."
        )

    # Convert to Polars
    df = pl.from_pandas(df_pd)

    # Precompute LOWERCASE helper columns once (used for fast filtering/search)
    # Only for columns we actually need.
    lc_targets = [c for c in (FILTER_COLS + ["Concat"]) if c in df.columns]
    df = df.with_columns([
        pl.when(pl.col(c).is_null()).then("").otherwise(pl.col(c))
        .cast(pl.Utf8)
        .str.strip()
        .str.to_lowercase()
        .alias(f"{c}__lc")
        for c in lc_targets
    ])

    return df

# Load once from cache
t0 = time.perf_counter()
df = load_data()
load_ms = (time.perf_counter() - t0) * 1000

# -------------------- Options helpers --------------------
def get_options(df_pl: pl.DataFrame, col: str) -> list[str]:
    if col not in df_pl.columns:
        return ["All"]
    # Show tidy, unique (case-insensitive) values; we use lowercase helper for dedupe/sort
    lc = f"{col}__lc"
    if lc not in df_pl.columns:
        return ["All"]
    # Get unique lower values
    uniques = df_pl.select(pl.col(lc)).unique().to_series().to_list()
    uniques = [v for v in uniques if v]  # drop blanks
    uniques = sorted(uniques)
    # Display as Title Case for nicer UI (you can change to raw lower if you prefer)
    display = [u for u in uniques]
    # First item is "All"
    return ["All"] + display

SupplierName_options = get_options(df, "Supplier_Name")
City_options        = get_options(df, "City")
State_options       = get_options(df, "State")
Location_options    = get_options(df, "Location")
Category1_options   = get_options(df, "Category_1")
Category2_options   = get_options(df, "Category_2")
Category3_options   = get_options(df, "Category_3")
Product_options     = get_options(df, "Product_Service")

# -------------------- Styles / Header --------------------
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

left_col, right_col = st.columns([6, 1])
with left_col:
    st.markdown("""
        <div style="background-color: white; padding: 20px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center;">
            <span style='color: #0F1C2E; font-size: 26px; font-weight: bold;'> Supplier Dashboard </span>
        </div>
    """, unsafe_allow_html=True)
with right_col:
    st.markdown("""<div style="padding: 20px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center;"></div>""",
                unsafe_allow_html=True)
    st.image("logo.jpg", width=100)

# -------------------- Filters & Search (FORM -> submit once) --------------------
with st.form("filters_form", clear_on_submit=False):
    search = st.text_input("Search (uses only your prebuilt 'Concat' column)", "")

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col1:
        supplierName_filter = st.selectbox("Filter by Name", SupplierName_options, index=0)
    with col2:
        City_filter = st.selectbox("Filter by City", City_options, index=0)
    with col3:
        State_filter = st.selectbox("Filter by State", State_options, index=0)
    with col4:
        Location_filter = st.selectbox("Filter by Location", Location_options, index=0)
    with col5:
        Category1_filter = st.selectbox("Filter by Category 1", Category1_options, index=0)
    with col6:
        Category2_filter = st.selectbox("Filter by Category 2", Category2_options, index=0)
    with col7:
        Category3_filter = st.selectbox("Filter by Category 3", Category3_options, index=0)
    with col8:
        Product_filter = st.selectbox("Filter by Product", Product_options, index=0)

    apply_clicked = st.form_submit_button("Apply")

# -------------------- Filtering (fast; uses *_lc helper cols) --------------------
def _lc(s: str) -> str:
    return (s or "").strip().lower()

filtered_df = df

# Per-filter equality on lowercase helper columns
filters = [
    ("Supplier_Name", supplierName_filter),
    ("City", City_filter),
    ("State", State_filter),
    ("Location", Location_filter),
    ("Category_1", Category1_filter),
    ("Category_2", Category2_filter),
    ("Category_3", Category3_filter),
    ("Product_Service", Product_filter),
]
for base_col, val in filters:
    if val and val != "All" and (f"{base_col}__lc" in filtered_df.columns):
        filtered_df = filtered_df.filter(pl.col(f"{base_col}__lc") == _lc(val))

# Search ONLY on Concat (lowercase helper)
if search.strip():
    if "Concat__lc" in filtered_df.columns:
        # literal=True => no regex cost; case-insensitive via lower helper
        filtered_df = filtered_df.filter(
            pl.col("Concat__lc").str.contains(_lc(search), literal=True)
        )
    else:
        st.warning("Concat column not available for search.")

# Hide helper columns and hide Concat in the UI (but keep original Concat for export)
drop_cols = [c for c in filtered_df.columns if c.endswith("__lc")]
to_show = filtered_df.drop(drop_cols + (["Concat"] if "Concat" in filtered_df.columns else []))

# -------------------- Table --------------------
# Limit rows shown for UI perf. Adjust if you want.
MAX_SHOW = 2000
st.dataframe(to_show.head(MAX_SHOW).to_pandas(), use_container_width=True)

# -------------------- Export --------------------
# Export the FULL filtered result (includes 'Concat')
if filtered_df.height > 0:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        filtered_df.to_pandas().to_excel(writer, index=False, sheet_name="Sheet")
    buf.seek(0)
    st.download_button(
        label=f"Export Results ({filtered_df.height} rows)",
        data=buf.getvalue(),
        file_name="Supplier_Dashboard_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
else:
    st.info("No data to export. Please adjust your filters or search.")

# -------------------- Footnote --------------------
st.caption(f"Data loaded in ~{load_ms:.0f} ms • Using cached dataset • Searching only 'Concat'")
