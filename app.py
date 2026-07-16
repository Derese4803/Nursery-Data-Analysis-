import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery Master QC", layout="wide")

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
st.title("🌱 Master Nursery QC & Correction Dashboard")
df = fetch_and_clean_data()

if not df.empty:
    # 1. Navigation & Filters
    st.sidebar.header("Filter & Analyze")
    zone = st.sidebar.selectbox("Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    cluster = st.sidebar.selectbox("Cluster", ["All"] + sorted(df_f["Cluster"].unique().tolist()))
    df_f = df_f if cluster == "All" else df_f[df_f["Cluster"] == cluster]
    woreda = st.sidebar.selectbox("Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    kebele = st.sidebar.selectbox("Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]

    # --- QC CALCULATIONS ---
    species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
    df_f = df_f.copy()
    df_f['Total_Errors'] = 0
    for s in species_list:
        ready_c, seed_c = f"{s} Count Ready", f"{s} Ready Seedling"
        if ready_c in df_f.columns and seed_c in df_f.columns:
            df_f[ready_c] = pd.to_numeric(df_f[ready_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df_f[seed_c] = pd.to_numeric(df_f[seed_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            error_mask = (df_f[seed_c] > df_f[ready_c]) | ((df_f[ready_c] - df_f[seed_c]) > 200)
            df_f.loc[error_mask, 'Total_Errors'] += 1

    # 2. Global Metrics & Trends
    st.metric("Total Records with QC Errors", int(df_f['Total_Errors'].sum()))
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Error Distribution (Woreda)")
        st.bar_chart(df_f.groupby("Woreda")['Total_Errors'].sum())
    with c2:
        st.subheader("Error Trends (Kebele)")
        st.line_chart(df_f.groupby("Kebele")['Total_Errors'].sum())

    # 3. Comparison Analysis
    st.divider()
    st.subheader("📊 Comparison Analysis")
    comp_type = st.radio("Compare by:", ["Zone", "Cluster", "Woreda"], horizontal=True)
    sel_items = st.multiselect(f"Select {comp_type}s to Compare", sorted(df[comp_type].unique().tolist()))
    if sel_items:
        summary = df[df[comp_type].isin(sel_items)].groupby(comp_type)['Total_Errors'].agg(['sum', 'count'])
        summary['Error %'] = (summary['sum'] / summary['count'] * 100).round(2)
        st.dataframe(summary.rename(columns={'sum': 'Total Error Records'}), use_container_width=True)

    # 4. Correction Center (Woreda/Kebele Focus)
    st.divider()
    st.subheader("🛠 Correction Center: Woreda & Kebele Focus")
    corr_w = st.selectbox("Correction - Woreda:", ["All"] + sorted(df["Woreda"].unique().tolist()))
    corr_df = df if corr_w == "All" else df[df["Woreda"] == corr_w]
    
    st.info("Edit values below to correct errors:")
    corr_cols = ["Zone", "Cluster", "Woreda", "Kebele"] + [c for c in df.columns if "Count" in c or "Seedling" in c]
    edited_data = st.data_editor(corr_df[corr_cols], use_container_width=True)
    
    # 5. Species Analysis Table
    if kebele != "All":
        st.subheader(f"Detailed Species Breakdown: {kebele}")
        analysis_data = []
        for s in species_list:
            r, sc = f"{s} Count Ready", f"{s} Ready Seedling"
            if r in df_f.columns:
                val_r, val_sc = df_f[r].sum(), df_f[sc].sum()
                analysis_data.append({"Species": s, "Count Ready": int(val_r), "Ready Seedling": int(val_sc), "Diff": int(val_r - val_sc)})
        st.dataframe(pd.DataFrame(analysis_data).set_index("Species"), use_container_width=True)

else:
    st.warning("Data not loaded. Please check your connection.")
