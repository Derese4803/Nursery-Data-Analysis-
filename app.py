import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"

st.set_page_config(page_title="Nursery QC & Correction Dashboard", layout="wide")

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
st.title("🌱 Nursery Quality Control & Correction Dashboard")
df = fetch_and_clean_data()

if not df.empty:
    # 1. PRE-CALCULATE ERRORS
    species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
    df['Total_Errors'] = 0
    for s in species_list:
        ready_c, seed_c = f"{s} Count Ready", f"{s} Ready Seedling"
        if ready_c in df.columns and seed_c in df.columns:
            df[ready_c] = pd.to_numeric(df[ready_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df[seed_c] = pd.to_numeric(df[seed_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            error_mask = (df[seed_c] > df[ready_c]) | ((df[ready_c] - df[seed_c]) > 200)
            df.loc[error_mask, 'Total_Errors'] += 1

    # 2. Hierarchical Filters
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    zone = col_f1.selectbox("Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    
    cluster = col_f2.selectbox("Cluster", ["All"] + sorted(df_f["Cluster"].unique().tolist()))
    df_f = df_f if cluster == "All" else df_f[df_f["Cluster"] == cluster]
    
    woreda = col_f3.selectbox("Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    
    kebele = col_f4.selectbox("Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]

    # 3. Global Metrics & Trends
    st.metric("Total Records with QC Errors", int(df_f['Total_Errors'].sum()))
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Error Distribution by Woreda")
        st.bar_chart(df_f.groupby("Woreda")['Total_Errors'].sum())
    with c2:
        st.subheader("Error Trend by Kebele")
        st.line_chart(df_f.groupby("Kebele")['Total_Errors'].sum())

    # 4. Species Analysis & Correction
    if kebele != "All":
        st.divider()
        st.subheader(f"Detailed Species QC: {kebele}")
        analysis_data = []
        for s in species_list:
            r, sc = f"{s} Count Ready", f"{s} Ready Seedling"
            if r in df_f.columns:
                val_r, val_sc = df_f[r].sum(), df_f[sc].sum()
                analysis_data.append({"Species": s, "Count Ready": int(val_r), "Ready Seedling": int(val_sc), "Diff": int(val_r - val_sc)})
        st.dataframe(pd.DataFrame(analysis_data).set_index("Species"), use_container_width=True)
        
        st.subheader(f"🛠 Correction Center: {kebele}")
        error_df = df_f[df_f['Total_Errors'] > 0]
        if not error_df.empty:
            st.warning("Edit the values below to fix flagged records:")
            edited_df = st.data_editor(error_df, use_container_width=True)
        else:
            st.success("No errors detected in this Kebele!")

    # 5. Comparison Analysis (Accurate Percentage Ranking)
    st.divider()
    st.subheader("📊 Comparison Analysis (Priority Ranking)")
    st.info("Areas are ranked by actual Error Rate (Total Errors / Total Records) %.")
    
    comp_type = st.radio("Compare by:", ["Zone", "Cluster", "Woreda"], horizontal=True)
    sel_items = st.multiselect(f"Select {comp_type}s to Compare", sorted(df[comp_type].unique().tolist()))
    
    if sel_items:
        df_comp = df[df[comp_type].isin(sel_items)]
        # Aggregation: sum errors and count records
        grouped = df_comp.groupby(comp_type)['Total_Errors'].agg(['sum', 'count'])
        
        summary = pd.DataFrame()
        summary['Total Errors'] = grouped['sum']
        summary['Total Records'] = grouped['count']
        # Calculate true Error Rate %
        summary['Error Rate %'] = ((summary['Total Errors'] / summary['Total Records']) * 100).round(2)
        
        # Sort by Error Rate % descending
        summary = summary.sort_values(by='Error Rate %', ascending=False)
        
        c_a, c_b = st.columns(2)
        c_a.bar_chart(summary[['Error Rate %']])
        c_b.bar_chart(summary[['Total Errors']])
        st.dataframe(summary, use_container_width=True)

    st.subheader("Full Flagged Records")
    st.dataframe(df_f[df_f['Total_Errors'] > 0], use_container_width=True)

else:
    st.warning("Data not loaded.")
