import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery-Data-Analysis", layout="wide")

# --- DATA FETCHING ---
@st.cache_data(ttl=60)
def fetch_data():
    token = st.secrets.get("github", {}).get("token")
    if not token:
        st.error("GitHub token missing in secrets.")
        return pd.DataFrame()
        
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            return pd.read_csv(io.StringIO(content))
        else:
            st.error(f"Error {response.status_code}: Check repo name or file path.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- APP INTERFACE ---
st.title("🌱 Nursery-Data-Analysis")
df = fetch_data()

if not df.empty:
    st.sidebar.header("Filter Data")
    
    # 1. Hierarchical Location Filtering
    zone = st.sidebar.selectbox("Select Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    
    woreda = st.sidebar.selectbox("Select Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    
    kebele = st.sidebar.selectbox("Select Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]
    
    # 2. Species Selector
    # Automatically extracts unique species (e.g., 'Gesho', 'Arzelibano') from column names
    all_columns = [c.split(' ')[0] for c in df.columns if ' ' in c]
    species_list = sorted(list(set(all_columns)))
    sel_species = st.selectbox("Select Species", species_list)
    
    st.divider()
    
    # 3. Dynamic Aggregation
    st.subheader(f"Results: {sel_species} in {kebele}, {woreda}")
    
    # Filter columns that belong to the selected species
    cols_to_sum = [c for c in df.columns if c.startswith(sel_species)]
    
    if cols_to_sum:
        # Calculate sums
        metrics = df_f[cols_to_sum].sum()
        
        # Display as metric cards
        cols = st.columns(len(metrics))
        for i, (name, val) in enumerate(metrics.items()):
            clean_name = name.replace(f"{sel_species} ", "")
            cols[i].metric(clean_name, f"{int(val):,}")
    else:
        st.info("No data columns found for this species.")
    
    st.dataframe(df_f, use_container_width=True)
else:
    st.warning("No data loaded. Check repository name and CSV path.")
