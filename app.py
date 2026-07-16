import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="QC Dashboard", layout="wide")

@st.cache_data(ttl=60)
def fetch_and_clean_data():
    token = st.secrets.get("github", {}).get("token")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        
        # Error Detection Logic
        species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
        df['Error_Flag'] = 0
        for s in species_list:
            ready_col, seedling_col = f"{s} Count Ready", f"{s} Ready Seedling"
            if ready_col in df.columns and seedling_col in df.columns:
                df[ready_col] = pd.to_numeric(df[ready_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df[seedling_col] = pd.to_numeric(df[seedling_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                error_mask = (df[seedling_col] > df[ready_col]) | ((df[ready_col] - df[seedling_col]) > 200)
                df.loc[error_mask, 'Error_Flag'] += 1
        return df
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Nursery Quality Control Dashboard")
df = fetch_and_clean_data()

if not df.empty:
    # Hierarchical Filters
    st.sidebar.header("Navigation")
    
    # 1. Zone
    zone = st.sidebar.selectbox("Select Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    
    # 2. Cluster
    cluster = st.sidebar.selectbox("Select Cluster", ["All"] + sorted(df_f["Cluster"].unique().tolist()))
    df_f = df_f if cluster == "All" else df_f[df_f["Cluster"] == cluster]
    
    # 3. Woreda
    woreda = st.sidebar.selectbox("Select Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    
    # 4. Kebele
    kebele = st.sidebar.selectbox("Select Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]

    # Metrics
    st.metric("Total Flagged Records", int(df_f['Error_Flag'].sum()))
    
    # Dynamic Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Error Distribution (Bar)")
        # If a Kebele is selected, it shows the error status for that Kebele; 
        # otherwise, it groups by the next available hierarchy.
        group_by = "Kebele" if kebele == "All" else "Woreda"
        st.bar_chart(df_f.groupby(group_by)['Error_Flag'].sum())
        
    with col2:
        st.subheader("Error Trend (Line)")
        st.line_chart(df_f.groupby("Kebele")['Error_Flag'].sum())
        
    st.dataframe(df_f[df_f['Error_Flag'] > 0], use_container_width=True)
else:
    st.warning("Data not loaded.")
