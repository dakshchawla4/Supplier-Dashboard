import io
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")

# ---------- Password gate ----------
password = st.text_input("Enter Password to access the dashboard", type="password")
if password != "Newjoiner@01":
    st.stop()

# ---------- Helpers ----------
EXPECTED_COLS = [
    "Supplier_Name", "City", "State", "Location",
    "Category_1", "Category_2", "Category_3", "Product_Service"
]

def _normalize_cols(cols):
    # strip spaces, turn spaces/slashes into underscores
    return [c.strip().replace("/", "_").replace(" ", "_") for c in cols]

@st.cache_data(show_spinner=True, ttl=600)
def load_data() -> pd.DataFrame:
    """
    Fast, safe Excel load:
    - read everything as string to avoid ArrowTypeError/bytes<->bool issues
    - normalize column names to your underscore style
    """
    try:
        df = pd.read_excel("excel.xlsx", dtype="string")  # engine auto-picks; openpyxl preferred
    except Exception as e:
        st.error(f"Failed to read excel.xlsx: {e}")
        return pd.DataFrame()

    # Normalize columns to the underscore form your UI expects
    df.columns = _normalize_cols(df.columns)

    # Ensure all columns are string & trimmed
    for c in df.columns:
        df[c] = df[c].astype("string").str.strip()

    return df

df = load_data()

def safe_options(frame: pd.DataFrame, col: str):
    if col not in frame.columns:
        return ["All"]
    vals = (
        frame[col]
        .dropna()
        .str.strip()
        .str.lower()
        .unique()
    )
    vals = sorted([v for v in vals if v])
    return ["All"] + vals

# ---------- Title / Header ----------
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
            <span style="color: #0F1C2E; font-size: 26px; font-weight: bold;">Supplier Dashboard</span>
        </div>
    """, unsafe_allow_html=True)
with right_col:
    st.markdown('<div style="padding: 20px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center;"></div>', unsafe_allow_html=True)
    try:
        st.image("logo.jpg", width=100)
    except Exception:
        pass

# ---------- Search & filters ----------
search = st.text_input("Search", "")

SupplierName_options = safe_options(df, "Supplier_Name")
City_options        = safe_options(df, "City")
State_options       = safe_options(df, "State")
Location_options    = safe_options(df, "Location")
Category1_options   = safe_options(df, "Category_1")
Category2_options   = safe_options(df, "Category_2")
Category3_options   = safe_options(df, "Category_3")
Product_options     = safe_options(df, "Product_Service")

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
with col1: supplierName_filter = st.selectbox("Filter by Name", SupplierName_options)
with col2: City_filter         = st.selectbox("Filter by City", City_options)
with col3: State_filter        = st.selectbox("Filter by State", State_options)
with col4: Location_filter     = st.selectbox("Filter by Location", Location_options)
with col5: Category1_filter    = st.selectbox("Filter by Category 1", Category1_options)
with col6: Category2_filter    = st.selectbox("Filter by Category 2", Category2_options)
with col7: Category3_filter    = st.selectbox("Filter by Category 3", Category3_options)
with col8: Product_filter      = st.selectbox("Filter by Product", Product_options)

def apply_eq(frame: pd.DataFrame, col: str, val: str) -> pd.DataFrame:
    if val == "All" or col not in frame.columns:
        return frame
    # robust string compare
    return frame[frame[col].fillna("").str.strip().str.lower() == val]

filtered = df.copy()
filtered = apply_eq(filtered, "Supplier_Name",   supplierName_filter)
filtered = apply_eq(filtered, "City",            City_filter)
filtered = apply_eq(filtered, "State",           State_filter)
filtered = apply_eq(filtered, "Location",        Location_filter)
filtered = apply_eq(filtered, "Category_1",      Category1_filter)
filtered = apply_eq(filtered, "Category_2",      Category2_filter)
filtered = apply_eq(filtered, "Category_3",      Category3_filter)
filtered = apply_eq(filtered, "Product_Service", Product_filter)

# Search across all (string) columns without building a huge Concat column
if search.strip():
    q = search.strip().lower()
    str_cols = [c for c in filtered.columns if pd.api.types.is_string_dtype(filtered[c])]
    if str_cols:
        mask = pd.Series(False, index=filtered.index)
        for c in str_cols:
            mask = mask | filtered[c].str.lower().str.contains(q, na=False)
        filtered = filtered[mask]

# ---------- Table ----------
st.dataframe(filtered.head(4000), use_container_width=True)

# ---------- Download ----------
if len(filtered) > 0:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        filtered.to_excel(writer, index=False, sheet_name="Sheet")
        buffer.seek(0)
    st.download_button(
        label="Export Search Results",
        data=buffer.getvalue(),
        file_name="Supplier_Dashboard_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:
    st.info("No data to export. Please adjust your filters or search.")









