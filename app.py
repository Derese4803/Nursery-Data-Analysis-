import streamlit as st
import pandas as pd
import base64
import requests
import io

# ============================================================================
# CONFIGURATION
# ============================================================================
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "control-sample-collction"
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery-Data-Analysis", layout="wide")

# ============================================================================
# DATA FETCHING WITH DEBUGGING
# ============================================================================
@st.cache_data(ttl=60)
def fetch_data_from_github():
    token = st.secrets.get("github", {}).get("token")
    if not token:
        st.error("GitHub token not found in secrets!")
        return pd.DataFrame()
        
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code != 200:
        st.error(f"GitHub Error {response.status_code}: Please check your Token, Repo Name, or File Path.")
        return pd.DataFrame()
        
    try:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return pd.read_csv(io.StringIO(content))
    except Exception as e:
        st.error(f"Error parsing CSV: {e}")
        return pd.DataFrame()

# ============================================================================
# INTERFACE
# ============================================================================
st.title("🌱 Nursery-Data-Analysis")
df = fetch_data_from_github()

if not df.empty:
    st.sidebar.header("Filter Options")
    
    # Species Filter
    species_options = ["All"] + sorted(df["Species"].astype(str).unique().tolist())
    selected_species = st.sidebar.selectbox("Select Species", species_options)
    
    # Filter Data
    filtered_df = df if selected_species == "All" else df[df["Species"] == selected_species]
    
    # Location Filters
    woreda_options = ["All"] + sorted(filtered_df["Woreda"].astype(str).unique().tolist())
    selected_woreda = st.sidebar.selectbox("Select Woreda", woreda_options)
    filtered_df = filtered_df if selected_woreda == "All" else filtered_df[filtered_df["Woreda"] == selected_woreda]
    
    kebele_options = ["All"] + sorted(filtered_df["Kebele"].astype(str).unique().tolist())
    selected_kebele = st.sidebar.selectbox("Select Kebele", kebele_options)
    filtered_df = filtered_df if selected_kebele == "All" else filtered_df[filtered_df["Kebele"] == selected_kebele]

    # Metrics
    st.subheader(f"Analysis: {selected_species} | {selected_woreda} | {selected_kebele}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Count", int(pd.to_numeric(filtered_df.get("Total Count", 0)).sum()))
    m2.metric("MDB Plan", int(pd.to_numeric(filtered_df.get("MDB Plan", 0)).sum()))
    m3.metric("Healthy Seeding", int(pd.to_numeric(filtered_df.get("Healthy Seeding", 0)).sum()))
    m4.metric("Ready Seedling", int(pd.to_numeric(filtered_df.get("Ready Seedling", 0)).sum()))

    st.dataframe(filtered_df, use_container_width=True)
    
    st.download_button("📥 Download Filtered Data", filtered_df.to_csv(index=False).encode('utf-8-sig'), "Nursery_Export.csv", use_container_width=True)
else:
    st.info("Waiting for data... If this persists, verify your CSV file exists on GitHub and matches the required headers.")
