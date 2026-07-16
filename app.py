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

# --- DATA FUNCTIONS ---
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

# --- SESSION STATE INITIALIZATION ---
if 'data' not in st.session_state:
    df_load, sha_load = fetch_data()
    st.session_state.data = df_load
    st.session_state.sha = sha_load

# Force Refresh Button
if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    df_load, sha_load = fetch_data()
    st.session_state.data = df_load
    st.session_state.sha = sha_load
    st.rerun()

df = st.session_state.data

if not df.empty:
    # 1. HARD RE-CALCULATE ERRORS (Ignore Justification)
    species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
    df['Total_Errors'] = 0 
    
    for s in species_list:
        r, sc = f"{s} Count Ready", f"{s} Ready Seedling"
        if r in df.columns and sc in df.columns:
            # Clean and convert to numeric to ensure accurate comparison
            df[r] = pd.to_numeric(df[r].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df[sc] = pd.to_numeric(df[sc].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            # Flag error if seedling count is greater than expected, or if gap > 100
            mask = (df[sc] > df[r]) | ((df[r] - df[sc]) > 100)
            df.loc[mask, 'Total_Errors'] = 1

    st.title("🌱 Nursery Quality Control & Correction Dashboard")

    # 2. OVERALL DATA ANALYSIS
    total_recs = len(df)
    active_errors = df['Total_Errors'].sum()
    accuracy_rate = ((total_recs - active_errors) / total_recs * 100) if total_recs > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", total_recs)
    col2.metric("Total Errors Found", int(active_errors))
    col3.metric("Records Justified", int(df['Justification'].replace("", None).count()))
    col4.metric("Data Accuracy Rate", f"{accuracy_rate:.2f}%")

    # 3. FILTERS
    st.divider()
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    zone = col_f1.selectbox("Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
    df_f = df if zone == "All" else df[df["Zone"] == zone]
    cluster = col_f2.selectbox("Cluster", ["All"] + sorted(df_f["Cluster"].unique().tolist()))
    df_f = df_f if cluster == "All" else df_f[df_f["Cluster"] == cluster]
    woreda = col_f3.selectbox("Woreda", ["All"] + sorted(df_f["Woreda"].unique().tolist()))
    df_f = df_f if woreda == "All" else df_f[df_f["Woreda"] == woreda]
    kebele = col_f4.selectbox("Kebele", ["All"] + sorted(df_f["Kebele"].unique().tolist()))
    df_f = df_f if kebele == "All" else df_f[df_f["Kebele"] == kebele]

    # 4. VISUAL ANALYSIS
    st.subheader("📊 Performance & Error Analytics")
    c1, c2, c3 = st.columns(3)
    c1.bar_chart(df_f.groupby("Cluster")['Total_Errors'].sum())
    c2.line_chart(df_f.groupby("Zone")['Total_Errors'].sum())
    c3.bar_chart(df_f.groupby("Woreda")['Total_Errors'].sum())

    # 5. CORRECTION & JUSTIFICATION CENTER
    st.divider()
    st.subheader("🛠 Correction & Justification Center")
    error_df = df_f[df_f['Total_Errors'] > 0]
    
    if not error_df.empty:
        edited_df = st.data_editor(error_df, key="editor", use_container_width=True)
        if st.button("Save Changes to GitHub"):
            df.update(edited_df)
            st.session_state.data = df
            res = save_to_github(df, st.session_state.sha)
            if res.status_code == 100:
                st.success("Changes saved! Refreshing...")
                st.rerun()
    else:
        st.success("No errors found in this selection.")

    # 6. COMPARISON ANALYSIS
    st.divider()
    st.subheader("📊 Comparison Analysis (Error Volume Contribution)")
    comp_type = st.radio("Compare by:", ["Zone", "Cluster", "Woreda"], horizontal=True)
    sel_items = st.multiselect(f"Select {comp_type}s to Compare", sorted(df[comp_type].unique().tolist()))
    
    if sel_items:
        df_comp = df[df[comp_type].isin(sel_items)]
        summary = df_comp.groupby(comp_type)['Total_Errors'].sum().reset_index()
        summary.columns = [comp_type, 'Total Errors']
        total_errors_selected = summary['Total Errors'].sum()
        
        if total_errors_selected > 0:
            summary['Error Contribution %'] = ((summary['Total Errors'] / total_errors_selected) * 100).round(2)
            st.bar_chart(summary.set_index(comp_type)['Error Contribution %'])
            st.dataframe(summary.sort_values(by='Error Contribution %', ascending=False), use_container_width=True)
        else:
            st.info("No errors in selection.")

else:
    st.warning("Data not loaded.")
