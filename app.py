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
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- APP INTERFACE ---
st.title("🌱 Nursery-Data-Analysis")
df = fetch_data()

if not df.empty:
    # 1. Hierarchical Filters
    st.sidebar.header("Filter Data")
    
    # Zone Filter
    zones = ["All"] + sorted(df["Zone"].unique().tolist())
    selected_zone = st.sidebar.selectbox("Select Zone", zones)
    df_filtered = df if selected_zone == "All" else df[df["Zone"] == selected_zone]
    
    # Woreda Filter
    woredas = ["All"] + sorted(df_filtered["Woreda"].unique().tolist())
    selected_woreda = st.sidebar.selectbox("Select Woreda", woredas)
    df_filtered = df_filtered if selected_woreda == "All" else df_filtered[df_filtered["Woreda"] == selected_woreda]
    
    # Kebele Filter
    kebeles = ["All"] + sorted(df_filtered["Kebele"].unique().tolist())
    selected_kebele = st.sidebar.selectbox("Select Kebele", kebeles)
    df_filtered = df_filtered if selected_kebele == "All" else df_filtered[df_filtered["Kebele"] == selected_kebele]
    
    # 2. Species Selector
    # Get unique species names (e.g., 'Gesho', 'Grevillea') from column headers
    species_options = sorted(list(set([c.split(' ')[0] for c in df.columns if ' ' in c])))
    selected_species = st.selectbox("Select Species to Analyze", species_options)
    
    # 3. Display Aggregated Metrics for selected species
    st.subheader(f"Analysis: {selected_species} in {selected_woreda} (Zone: {selected_zone})")
    
    # Dynamically find columns related to the selected species
    cols_to_sum = [c for c in df.columns if c.startswith(selected_species)]
    
    if cols_to_sum:
        metrics = df_filtered[cols_to_sum].sum()
        cols = st.columns(len(metrics))
        for i, (name, val) in enumerate(metrics.items()):
            cols[i].metric(name.replace(f"{selected_species} ", ""), int(val))
    
    st.dataframe(df_filtered, use_container_width=True)

else:
    st.warning("Data not found. Please check your GitHub repository.")
