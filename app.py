import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery QC Comparison", layout="wide")

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
                error_mask = (df[seed_c] > df[ready_c]) | ((df[ready_c] - df[seed_c]) > 200)
                df.loc[error_mask, 'Total_Errors'] += 1
        return df
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Nursery QC: Comparison & Percentage Analysis")
df = fetch_and_clean_data()

if not df.empty:
    level = st.radio("Select Comparison Level:", ["Zone", "Cluster", "Woreda"], horizontal=True)
    selected_areas = st.multiselect(f"Select {level}s to Compare", sorted(df[level].unique().tolist()))
    
    if selected_areas:
        df_comp = df[df[level].isin(selected_areas)]
        
        # Aggregate Data
        summary = df_comp.groupby(level)['Total_Errors'].agg(['sum', 'count'])
        summary['Error %'] = (summary['sum'] / summary['count'] * 100).round(2)
        
        # Visual Comparison
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Total Errors by Area")
            st.bar_chart(summary['sum'])
        with col2:
            st.subheader("Error Rate (%)")
            st.bar_chart(summary['Error %'])
        
        # Detailed Table
        st.subheader("Comparison Statistics")
        st.dataframe(summary.rename(columns={'sum': 'Total Error Records', 'count': 'Total Records'}), use_container_width=True)
    else:
        st.info(f"👈 Select {level}s to view the comparison table and percentage charts.")
else:
    st.warning("Data not loaded.")
