import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery QC Dashboard", layout="wide")

@st.cache_data(ttl=60)
def fetch_and_clean_data():
    token = st.secrets.get("github", {}).get("token")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        return df
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Nursery Quality Control Dashboard")
df = fetch_and_clean_data()

if not df.empty:
    # 1. Hierarchical Filters
    st.sidebar.header("Filter Data")
    zone = st.sidebar.selectbox("Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    
    cluster = st.sidebar.selectbox("Cluster", ["All"] + sorted(df_f["Cluster"].unique().tolist()))
    df_f = df_f if cluster == "All" else df_f[df_f["Cluster"] == cluster]
    
    woreda = st.sidebar.selectbox("Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    
    kebele = st.sidebar.selectbox("Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]

    # 2. Kebele-Specific Species Analysis
    if kebele != "All":
        st.subheader(f"📊 Species QC Analysis for: {kebele}")
        
        species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
        diff_data = []
        
        for s in species_list:
            ready_c = f"{s} Count Ready"
            seed_c = f"{s} Ready Seedling"
            if ready_c in df_f.columns and seed_c in df_f.columns:
                val_ready = pd.to_numeric(df_f[ready_c].astype(str).str.replace(',', ''), errors='coerce').sum()
                val_seed = pd.to_numeric(df_f[seed_c].astype(str).str.replace(',', ''), errors='coerce').sum()
                diff = val_ready - val_seed
                diff_data.append({"Species": s, "Difference (Ready - Seedling)": diff, "Status": "Error" if (val_seed > val_ready) or (diff > 200) else "OK"})
        
        st.table(pd.DataFrame(diff_data).set_index("Species"))
    else:
        st.info("👈 Select a Kebele from the sidebar to see detailed species differences and QC status.")

    # 3. Overview Charts
    st.divider()
    st.subheader("Global Error Overview")
    st.bar_chart(df_f.groupby("Woreda")['Zone'].count()) # Placeholder for aggregated view
else:
    st.warning("Data not loaded.")
