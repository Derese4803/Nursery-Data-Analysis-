import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "control-sample-collction"
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery-Data-Analysis", layout="wide")

# --- DATA FETCHING ---
@st.cache_data(ttl=300)
def fetch_data():
    token = st.secrets.get("github", {}).get("token")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return pd.read_csv(io.StringIO(content))
    except Exception as e:
        st.error(f"Could not load data: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Nursery-Data-Analysis")
df = fetch_data()

if not df.empty:
    # Sidebar Filters
    st.sidebar.header("Filter Options")
    
    # 1. Species Selection
    # Extract species names from columns (e.g., 'Gesho Count Ready' -> 'Gesho')
    species_list = sorted(list(set([col.split(' ')[0] for col in df.columns if ' ' in col])))
    selected_species = st.sidebar.selectbox("Select Species", species_list)
    
    # 2. Location Filters
    woreda = st.sidebar.selectbox("Select Woreda", ["All"] + sorted(df["Woreda"].unique().tolist()))
    kebele = st.sidebar.selectbox("Select Kebele", ["All"] + sorted(df[df["Woreda"] == woreda if woreda != "All" else True]["Kebele"].unique().tolist()))
    
    # Apply Filtering
    mask = True
    if woreda != "All": mask &= (df["Woreda"] == woreda)
    if kebele != "All": mask &= (df["Kebele"] == kebele)
    filtered_df = df[mask]
    
    # --- DYNAMIC METRICS ---
    st.subheader(f"Analysis: {selected_species} | Woreda: {woreda} | Kebele: {kebele}")
    
    # Match columns that start with our selected species
    col_map = {
        "Total": f"{selected_species} Total Count",
        "Healthy": f"{selected_species} Healthy Seeding",
        "Ready": f"{selected_species} Ready Seedling",
        "Plan": f"{selected_species} MDB Plan"
    }
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Count", int(filtered_df[col_map["Total"]].sum()) if col_map["Total"] in df.columns else 0)
    c2.metric("MDB Plan", int(filtered_df[col_map["Plan"]].sum()) if col_map["Plan"] in df.columns else 0)
    c3.metric("Healthy", int(filtered_df[col_map["Healthy"]].sum()) if col_map["Healthy"] in df.columns else 0)
    c4.metric("Ready", int(filtered_df[col_map["Ready"]].sum()) if col_map["Ready"] in df.columns else 0)

    st.dataframe(filtered_df, use_container_width=True)
    
    # Download Button
    st.download_button("📥 Download Filtered Data", filtered_df.to_csv(index=False).encode('utf-8-sig'), "Nursery_Export.csv")
else:
    st.warning("Data not found. Please ensure the CSV file is at the root of the GitHub repo.")
