import streamlit as st
import pandas as pd
import requests
import base64
import io

# --- CONFIGURATION ---
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "Nursery-Data-Analysis-" 
CSV_FILENAME = "amhara_me_2026.csv"
GITHUB_TOKEN = st.secrets["github"]["token"]

st.set_page_config(page_title="Nursery QC & Correction Dashboard", layout="wide")

@st.cache_data(ttl=60)
def fetch_data():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        df = pd.read_csv(io.StringIO(content))
        if 'Justification' not in df.columns:
            df['Justification'] = ""
        return df, response.json()['sha']
    return pd.DataFrame(), None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    csv_content = df.to_csv(index=False).encode('utf-8')
    data = {
        "message": "Update data and justifications",
        "content": base64.b64encode(csv_content).decode('utf-8'),
        "sha": sha
    }
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    return requests.put(url, json=data, headers=headers)

# --- APP LOGIC ---
df, file_sha = fetch_data()

if not df.empty:
    # 1. PRE-CALCULATE ERRORS (Excluded if Justification is provided)
    species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
    df['Total_Errors'] = 0
    for s in species_list:
        r, sc = f"{s} Count Ready", f"{s} Ready Seedling"
        if r in df.columns and sc in df.columns:
            df[r] = pd.to_numeric(df[r].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df[sc] = pd.to_numeric(df[sc].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            mask = ((df[sc] > df[r]) | ((df[r] - df[sc]) > 200)) & (df['Justification'].fillna("") == "")
            df.loc[mask, 'Total_Errors'] = 1

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

    # 3. Visual Analysis
    st.title("🌱 Nursery Quality Control & Correction Dashboard")
    st.metric("Total Active QC Errors", int(df_f['Total_Errors'].sum()))
    
    st.subheader("📊 Performance & Error Analytics")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("Error Distribution by Cluster (Bar)")
        st.bar_chart(df_f.groupby("Cluster")['Total_Errors'].sum())
    with c2:
        st.caption("Error Trend by Zone (Line)")
        st.line_chart(df_f.groupby("Zone")['Total_Errors'].sum())
    with c3:
        st.caption("Error Distribution by Woreda (Bar)")
        st.bar_chart(df_f.groupby("Woreda")['Total_Errors'].sum())

    # 4. Correction & Justification Center
    st.divider()
    st.subheader("🛠 Correction & Justification Center")
    error_df = df_f[df_f['Total_Errors'] > 0]
    
    if not error_df.empty:
        edited_df = st.data_editor(error_df, use_container_width=True)
        if st.button("Save Changes to GitHub"):
            df.update(edited_df)
            res = save_to_github(df, file_sha)
            if res.status_code == 200:
                st.success("Changes saved! Justified records are now excluded.")
                st.rerun()
    else:
        st.success("No active errors found in this selection.")

    # 5. Comparison Analysis (Priority Ranking)
    st.divider()
    st.subheader("📊 Comparison Analysis (Priority Ranking)")
    comp_type = st.radio("Compare by:", ["Zone", "Cluster", "Woreda"], horizontal=True)
    sel_items = st.multiselect(f"Select {comp_type}s to Compare", sorted(df[comp_type].unique().tolist()))
    
    if sel_items:
        df_comp = df[df[comp_type].isin(sel_items)]
        grouped = df_comp.groupby(comp_type)['Total_Errors'].agg(['sum', 'count'])
        summary = pd.DataFrame()
        summary['Total Errors'] = grouped['sum']
        summary['Total Records'] = grouped['count']
        summary['Error Rate %'] = ((summary['Total Errors'] / summary['Total Records']) * 100).round(2)
        summary = summary.sort_values(by='Error Rate %', ascending=False)
        st.dataframe(summary, use_container_width=True)

else:
    st.warning("Data not loaded.")
