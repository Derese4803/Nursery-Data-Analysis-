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
            st.error(f"GitHub Error {response.status_code}: Check repo name or file path.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Nursery-Data-Analysis")
df = fetch_data()

if not df.empty:
    st.sidebar.header("Hierarchical Filters")
    
    # 1. Zone
    zones = ["All"] + sorted(df["Zone"].unique().tolist())
    sel_zone = st.sidebar.selectbox("1. Select Zone", zones)
    df_f = df if sel_zone == "All" else df[df["Zone"] == sel_zone]
    
    # 2. Woreda
    woredas = ["All"] + sorted(df_f["Woreda"].unique().tolist())
    sel_woreda = st.sidebar.selectbox("2. Select Woreda", woredas)
    df_f = df_f if sel_woreda == "All" else df_f[df_f["Woreda"] == sel_woreda]
    
    # 3. Kebele
    kebeles = ["All"] + sorted(df_f["Kebele"].unique().tolist())
    sel_kebele = st.sidebar.selectbox("3. Select Kebele", kebeles)
    df_f = df_f if sel_kebele == "All" else df_f[df_f["Kebele"] == sel_kebele]
    
    st.divider()
    
    # 4. Species Analysis
    species_list = sorted(list(set([c.split(' ')[0] for c in df.columns if ' ' in c])))
    sel_species = st.selectbox("Select Species for Metric Analysis", species_list)
    
    st.subheader(f"Results: {sel_species} in {sel_kebele}, {sel_woreda}")
    
    # Dynamically find columns
    cols_to_sum = [c for c in df.columns if c.startswith(sel_species)]
    if cols_to_sum:
        metrics = df_f[cols_to_sum].sum()
        cols = st.columns(len(metrics))
        for i, (name, val) in enumerate(metrics.items()):
            cols[i].metric(name.replace(f"{sel_species} ", ""), int(val))
    
    st.dataframe(df_f, use_container_width=True)
else:
    st.warning("Data not found. Please verify the CSV path and your GitHub token permissions.")
