import streamlit as st
import polars as pl
import pandas as pd
import io

st.set_page_config(layout="wide")

passowrd = st.text_input("Enter Password to access the dashboard", type ="password")
if passowrd != "Newjoiner@01":
    st.stop()
    
def clean_string(s):
    if s is None:
        return ""
    return str(s).strip().lower()

@st.cache_data
def load_data():
    try:
        df = pl.read_excel("excel.xlsx")  # <-- Change to your file name
        # Clean column names
        df = df.rename({col: col.strip().replace("/", "_").replace(" ", "_") for col in df.columns})
        # Precompute a single search_blob column for fast searching (only ONCE!)
        df = df.with_columns([pl.col(col).cast(pl.Utf8).alias(col) for col in df.columns])
        return df
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return pl.DataFrame()

df = load_data()

def get_options(col):
    return ["All"] + sorted({clean_string(x) for x in df[col].unique() if clean_string(x)})

SupplierName_options = get_options("Supplier_Name")
City_options = get_options("City")
State_options = get_options("State")
Location_options = get_options("Location")
Category1_options = get_options("Category_1")
Category2_options = get_options("Category_2")
Category3_options = get_options("Category_3")
Product_options = get_options("Product_Service")


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

left_col, right_col = st.columns([6,1])

with left_col:
    st.markdown("""
                <div style = "background-color: white; padding: 20px; border-radius: 10px; margin-bottom: 10px;display: flex;align-items: center;">
        <span style ='color: #0F1C2E; font-size: 26px; font-weight: bold;'> Supplier Dashboard 
        </div>

    """, unsafe_allow_html=True)

with right_col:
    st.markdown("""
                <div style = padding: 20px; border-radius: 10px; margin-bottom: 10px;display: flex;align-items: center;"></div>""", unsafe_allow_html=True)
    st.image("logo.jpg",width=100)

# Search and Filters UI
search = st.text_input("Search", "")

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)

with col1:
    supplierName_filter = st.selectbox("Filter by Name", SupplierName_options)
with col2:
    City_filter = st.selectbox("Filter by City", City_options)
with col3:
    State_filter = st.selectbox("Filter by State", State_options)
with col4:
    Location_filter = st.selectbox("Filter by Location", Location_options)
with col5:
    Category1_filter = st.selectbox("Filter by Category 1", Category1_options)
with col6:
    Category2_filter = st.selectbox("Filter by Category 2", Category2_options)
with col7:
    Category3_filter = st.selectbox("Filter by Category 3", Category3_options)
with col8:
    Product_filter = st.selectbox("Filter by Product", Product_options)

# ---- FAST FILTERING ----

filtered_df = df
# Each filter: use .str.strip().to_lowercase() (and NEVER .stip or using .str twice)
if supplierName_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("Supplier_Name").str.to_lowercase() == supplierName_filter
    )
if City_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("City").str.to_lowercase() == City_filter
    )
if State_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("State").str.to_lowercase() == State_filter
    )
if Location_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("Location").str.to_lowercase() == Location_filter
    )
if Category1_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("Category_1").str.to_lowercase() == Category1_filter
    )
if Category2_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("Category_2").str.to_lowercase() == Category2_filter
    )
if Category3_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("Category_3").str.to_lowercase() == Category3_filter
    )
if Product_filter != "All":
    filtered_df = filtered_df.filter(
        pl.col("Product_Service").str.to_lowercase() == Product_filter
    )
# SEARCH: only on precomputed search_blob, only ONCE!
if search:
    filtered_df = filtered_df.filter(
        pl.col("Concat").str.to_lowercase().str.contains(search.lower())
    )
filtered_df_no_concat = filtered_df.drop("Concat")
# ---------- Show Table (now up to 2000 rows!) ----------
st.dataframe(filtered_df_no_concat.head(4000).to_pandas(), use_container_width=True)

# ---------- Download Button ----------
if filtered_df.shape[0] > 0:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        filtered_df.to_pandas().to_excel(writer, index=False, sheet_name="Sheet")
        buffer.seek(0)
    st.download_button(
        label="Export Search Results",
        data=buffer.getvalue(),
        file_name="Supplier_Dashboard_Results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data to export. Please adjust your filters or search.")



























