import io
import re
import streamlit as st

# Try Polars; fall back to Pandas if not installed
try:
    import polars as pl
    HAS_POLARS = True
except Exception:
    HAS_POLARS = False
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
    c2 = re.sub(r"[^0-9A-Za-z]+", "_", str(c).strip())
    return c2.strip("_")

def options_from_series(values):
    # keep first-seen display casing; match on lowercase
    uniq = {}
    for v in values:
        vv = (str(v) if v is not None else "").strip()
        if vv:
            uniq.setdefault(vv.lower(), vv)
    return ["All"] + sorted(uniq.values(), key=lambda x: x.lower())

# ---------- Data load (cached; runs once) ----------
@st.cache_data(show_spinner=True, ttl=3600)
def load_data():
    # Read Excel as strings to avoid ArrowTypeError & mixed types
    df_pd = pd.read_excel("excel.xlsx", engine="openpyxl", dtype=str).fillna("")
    # Standardize column names
    df_pd.columns = [clean_colname(c) for c in df_pd.columns]

    # Ensure Concat exists
    if "Concat" not in df_pd.columns:
        st.error("The uploaded Excel must contain a 'Concat' column. Add it and redeploy.")
        df_pd["Concat"] = ""

    # Precompute normalized columns for filtering/search (done once)
    df_pd["Concat__norm"] = df_pd["Concat"].astype(str).str.lower()
    for c in FILTER_COLS:
        if c in df_pd.columns:
            df_pd[f"{c}__norm"] = df_pd[c].astype(str).str.strip().str.lower()

    # Build dropdown options from original (pretty) values
    options = {}
    for c in FILTER_COLS:
        if c in df_pd.columns:
            options[c] = options_from_series(df_pd[c].tolist())
        else:
            options[c] = ["All"]

    # If Polars is available, convert for faster filtering; otherwise keep pandas
    if HAS_POLARS:
        df_pl = pl.from_pandas(df_pd, include_index=False)
        return ("polars", df_pl, options)
    else:
        return ("pandas", df_pd, options)

mode, data, options = load_data()

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

# ---------- Filtering helpers ----------
def selected_norm(s: str) -> str:
    return "" if s == "All" else norm(s)

# ---------- Apply filters & search ----------
if mode == "polars":
    df = data
    def apply_eq(frame, col, sel):
        if sel == "All" or f"{col}__norm" not in frame.columns:
            return frame
        return frame.filter(pl.col(f"{col}__norm") == norm(sel))

    df = apply_eq(df, "Supplier_Name",   supplierName_filter)
    df = apply_eq(df, "City",            City_filter)
    df = apply_eq(df, "State",           State_filter)
    df = apply_eq(df, "Location",        Location_filter)
    df = apply_eq(df, "Category_1",      Category1_filter)
    df = apply_eq(df, "Category_2",      Category2_filter)
    df = apply_eq(df, "Category_3",      Category3_filter)
    df = apply_eq(df, "Product_Service", Product_filter)

    if search.strip() and "Concat__norm" in df.columns:
        terms = [t.strip().lower() for t in search.split() if t.strip()]
        for t in terms:
            df = df.filter(pl.col("Concat__norm").str.contains(t, literal=True))

    # Hide helper cols in UI
    HIDDEN = ["Concat", "Concat__norm"] + [f"{c}__norm" for c in FILTER_COLS]
    display_df = df.drop(HIDDEN, strict=False)

    # Show limited rows for speed
    MAX_ROWS = 2000
    st.dataframe(display_df.head(MAX_ROWS).to_pandas(), use_container_width=True)

    # Download (include Concat & all data)
    if df.height > 0:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_pandas().to_excel(writer, index=False, sheet_name="Results")
            buffer.seek(0)
        st.download_button(
            label="Export Search Results",
            data=buffer.getvalue(),
            file_name="Supplier_Dashboard_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data to export. Please adjust your filters or search.")

else:
    df = data  # pandas
    def apply_eq(frame, col, sel):
        coln = f"{col}__norm"
        if sel == "All" or coln not in frame.columns:
            return frame
        return frame[frame[coln] == norm(sel)]

    df_f = df.copy()
    df_f = apply_eq(df_f, "Supplier_Name",   supplierName_filter)
    df_f = apply_eq(df_f, "City",            City_filter)
    df_f = apply_eq(df_f, "State",           State_filter)
    df_f = apply_eq(df_f, "Location",        Location_filter)
    df_f = apply_eq(df_f, "Category_1",      Category1_filter)
    df_f = apply_eq(df_f, "Category_2",      Category2_filter)
    df_f = apply_eq(df_f, "Category_3",      Category3_filter)
    df_f = apply_eq(df_f, "Product_Service", Product_filter)

    if search.strip() and "Concat__norm" in df_f.columns:
        terms = [t.strip().lower() for t in search.split() if t.strip()]
        for t in terms:
            df_f = df_f[df_f["Concat__norm"].str.contains(t, regex=False)]

    # Hide helper cols in UI
    HIDDEN = ["Concat", "Concat__norm"] + [f"{c}__norm" for c in FILTER_COLS]
    display_cols = [c for c in df_f.columns if c not in HIDDEN]
    MAX_ROWS = 2000
    st.dataframe(df_f.loc[:, display_cols].head(MAX_ROWS), use_container_width=True)

    # Download (include Concat & all columns)
    if len(df_f) > 0:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_f.to_excel(writer, index=False, sheet_name="Results")
            buffer.seek(0)
        st.download_button(
            label="Export Search Results",
            data=buffer.getvalue(),
            file_name="Supplier_Dashboard_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No data to export. Please adjust your filters or search.")







