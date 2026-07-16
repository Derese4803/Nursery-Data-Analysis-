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

# --- DATA FETCHING & CLEANING ---
@st.cache_data(ttl=60)
def fetch_and_clean_data():
    token = st.secrets.get("github", {}).get("token")
    if not token:
        st.error("GitHub token missing in Streamlit secrets.")
        return pd.DataFrame()
        
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            df = pd.read_csv(io.StringIO(content))
            
            # Species list defined by the columns of your CSV file
            species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
            
            # Strip commas and convert all numeric metric columns to integers
            for s in species_list:
                for metric in ['Count Ready', 'Count Non Ready', 'Total Count', 'MDB Plan', 'Healthy Seeding', 'Ready Seedling']:
                    col_name = f"{s} {metric}"
                    if col_name in df.columns:
                        df[col_name] = pd.to_numeric(
                            df[col_name].astype(str).str.replace(',', '').str.strip(), 
                            errors='coerce'
                        ).fillna(0).astype(int)
            return df
        else:
            st.error(f"GitHub Error {response.status_code}: Please verify that your CSV is on the main branch.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return pd.DataFrame()

# --- APP INTERFACE ---
st.title("🌱 Amhara Nursery Data Analysis Dashboard")
df = fetch_and_clean_data()

if not df.empty:
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Location Filters")
    
    # 1. Zone Filter
    zones = ["All"] + sorted(df["Zone"].unique().tolist())
    sel_zone = st.sidebar.selectbox("Select Zone", zones)
    df_f = df if sel_zone == "All" else df[df["Zone"] == sel_zone]
    
    # 2. Woreda Filter
    woredas = ["All"] + sorted(df_f["Woreda"].unique().tolist())
    sel_woreda = st.sidebar.selectbox("Select Woreda", woredas)
    df_f = df_f if sel_woreda == "All" else df_f[df_f["Woreda"] == sel_woreda]
    
    # 3. Kebele Filter
    kebeles = ["All"] + sorted(df_f["Kebele"].unique().tolist())
    sel_kebele = st.sidebar.selectbox("Select Kebele", kebeles)
    df_f = df_f if sel_kebele == "All" else df_f[df_f["Kebele"] == sel_kebele]
    
    # --- SPECIES SELECTOR ---
    species_options = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
    sel_species = st.selectbox("Choose Tree Species to Analyze", species_options)
    
    st.divider()
    
    # --- CALCULATE METRICS ---
    total_col = f"{sel_species} Total Count"
    ready_col = f"{sel_species} Ready Seedling"
    plan_col = f"{sel_species} MDB Plan"
    healthy_col = f"{sel_species} Healthy Seeding"
    
    if total_col in df.columns and ready_col in df.columns:
        total_val = df_f[total_col].sum()
        ready_val = df_f[ready_col].sum()
        plan_val = df_f[plan_col].sum() if plan_col in df.columns else 0
        healthy_val = df_f[healthy_col].sum() if healthy_col in df.columns else 0
        
        # Calculate Percentage safely
        percentage = (ready_val / total_val * 100) if total_val > 0 else 0.0
        
        # --- METRIC DISPLAY ---
        st.subheader(f"📊 Summary Statistics: {sel_species}")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        col1.metric("Total Count", f"{int(total_val):,}")
        col2.metric("Ready Seedlings", f"{int(ready_val):,}")
        col3.metric("Readiness %", f"{percentage:.1f}%")
        col4.metric("MDB Plan Target", f"{int(plan_val):,}")
        col5.metric("Healthy Seedlings", f"{int(healthy_val):,}")
        
        # Interactive Visual Progress Bar
        st.write("**Readiness Progress Bar:**")
        st.progress(min(percentage / 100.0, 1.0))
        
        st.divider()
        
        # --- INTERACTIVE NATIVE STREAMLIT CHART ---
        # Select chart grouping column dynamically based on chosen location filter
        if sel_woreda != "All":
            group_col = "Kebele"
        else:
            group_col = "Woreda"
            
        chart_data = df_f.groupby(group_col)[total_col].sum().reset_index()
        
        # Show native interactive bar chart
        st.subheader(f"📈 Total {sel_species} Count by {group_col}")
        st.bar_chart(data=chart_data, x=group_col, y=total_col, color="#2ecc71")
        
    else:
        st.warning(f"Required columns for '{sel_species}' not found in the CSV file.")

    # --- RAW DATA TABLE ---
    st.subheader("📋 Raw Data Records")
    st.dataframe(df_f, use_container_width=True)
    
    # Download Button
    csv_bytes = df_f.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Download Current View Data (CSV)", csv_bytes, "Nursery_Data_Export.csv", use_container_width=True)

else:
    st.warning("Data not loaded. Please verify your GitHub token and file path.")
