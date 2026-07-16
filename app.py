import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Complete Nursery QC Dashboard", layout="wide")

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
        df['Total_Errors'] = 0
        for s in species_list:
            ready_c, seed_c = f"{s} Count Ready", f"{s} Ready Seedling"
            if ready_c in df.columns and seed_c in df.columns:
                df[ready_c] = pd.to_numeric(df[ready_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df[seed_c] = pd.to_numeric(df[seed_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                # Rule: Error if Seedling > Ready OR (Ready - Seedling) > 200
                error_mask = (df[seed_c] > df[ready_c]) | ((df[ready_c] - df[seed_c]) > 200)
                df.loc[error_mask, 'Total_Errors'] += 1
        return df
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Master Nursery Quality Control Dashboard")
df = fetch_and_clean_data()

if not df.empty:
    # 1. Hierarchical Navigation
    st.sidebar.header("Filter & Navigate")
    zone = st.sidebar.selectbox("Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    
    cluster = st.sidebar.selectbox("Cluster", ["All"] + sorted(df_f["Cluster"].unique().tolist()))
    df_f = df_f if cluster == "All" else df_f[df_f["Cluster"] == cluster]
    
    woreda = st.sidebar.selectbox("Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    
    kebele = st.sidebar.selectbox("Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]

    # 2. Comparison Mode
    st.divider()
    st.subheader("Comparison & Percentage Analysis")
    comp_level = st.radio("Compare by:", ["Zone", "Cluster", "Woreda"], horizontal=True)
    sel_comps = st.multiselect(f"Select {comp_level}s to compare:", sorted(df[comp_level].unique().tolist()))
    
    if sel_comps:
        df_comp = df[df[comp_level].isin(sel_comps)]
        summary = df_comp.groupby(comp_level)['Total_Errors'].agg(['sum', 'count'])
        summary['Error %'] = (summary['sum'] / summary['count'] * 100).round(2)
        
        c1, c2 = st.columns(2)
        c1.bar_chart(summary['sum'])
        c2.bar_chart(summary['Error %'])

    # 3. Trends & QC Visuals
    st.divider()
    st.subheader("Error Trends & Distribution")
    c3, c4 = st.columns(2)
    c3.bar_chart(df_f.groupby("Woreda")['Total_Errors'].sum())
    c4.line_chart(df_f.groupby("Kebele")['Total_Errors'].sum())

    # 4. Detailed Species QC (When Kebele Selected)
    if kebele != "All":
        st.subheader(f"Detailed Species Breakdown: {kebele}")
        # (Table logic remains same as before)
    
    st.subheader("Flagged Data Records")
    st.dataframe(df_f[df_f['Total_Errors'] > 0], use_container_width=True)

else:
    st.warning("Data not loaded.")
