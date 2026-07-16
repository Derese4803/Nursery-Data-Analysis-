import streamlit as st
import pandas as pd
import requests
import base64
import io
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery-Data-Analysis", layout="wide")

# --- DATA FETCHING & CLEANING ---
@st.cache_data(ttl=60)
def fetch_data():
    token = st.secrets.get("github", {}).get("token")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        # Clean numeric columns (remove commas)
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='ignore')
        return df
    return pd.DataFrame()

# --- INTERFACE ---
st.title("🌱 Nursery-Data-Analysis")
df = fetch_data()

if not df.empty:
    sel_species = st.sidebar.selectbox("Select Species", sorted(list(set([c.split(' ')[0] for c in df.columns if ' ' in c]))))
    
    # CALCULATE PERCENTAGE
    total_col = f"{sel_species} Total Count"
    ready_col = f"{sel_species} Ready Seedling"
    
    if total_col in df.columns and ready_col in df.columns:
        total = df[total_col].sum()
        ready = df[ready_col].sum()
        percentage = (ready / total * 100) if total > 0 else 0
        
        # Display Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Count", f"{int(total):,}")
        m2.metric("Ready Seedlings", f"{int(ready):,}")
        m3.metric("Readiness %", f"{percentage:.1f}%")
        
        # Visualization
        st.subheader(f"Readiness Breakdown: {sel_species}")
        fig, ax = plt.subplots()
        ax.pie([ready, max(0, total - ready)], labels=['Ready', 'Not Ready'], 
               autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c'], startangle=90)
        st.pyplot(fig)
    else:
        st.warning("Required columns not found for this species.")

    st.dataframe(df, use_container_width=True)
