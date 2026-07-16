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

# --- FUNCTIONS ---
@st.cache_data(ttl=300)
def fetch_data_from_github():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        sha = response.json()['sha']
        df = pd.read_csv(io.StringIO(content))
        if 'Justification' not in df.columns:
            df['Justification'] = ""
        return df, sha
    return None, None

def save_to_github(df, sha):
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    csv_content = df.to_csv(index=False).encode('utf-8')
    data = {
        "message": "Update nursery data and justifications",
        "content": base64.b64encode(csv_content).decode('utf-8'),
        "sha": sha
    }
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    return requests.put(url, json=data, headers=headers)

# --- SESSION STATE INITIALIZATION ---
if 'df' not in st.session_state:
    df_load, sha_load = fetch_data_from_github()
    if df_load is not None:
        st.session_state.df = df_load
        st.session_state.sha = sha_load
    else:
        st.error("Could not load data from GitHub.")
        st.stop()

# --- ERROR CALCULATION LOGIC ---
def refresh_errors(df):
    species_list = ['Gesho', 'Grevillea', 'Decurrens', 'Wanza', 'Papaya', 'Moringa', 'Coffee', 'Guava', 'Lemon', 'Arzelibano', 'Neem']
    df['Total_Errors'] = 0
    for s in species_list:
        r, sc = f"{s} Count Ready", f"{s} Ready Seedling"
        if r in df.columns and sc in df.columns:
            val_r = pd.to_numeric(df[r].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            val_sc = pd.to_numeric(df[sc].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            # Mask: Error exists AND no justification provided
            mask = ((val_sc > val_r) | ((val_r - val_sc) > 200)) & (df['Justification'].fillna("") == "")
            df.loc[mask, 'Total_Errors'] = 1
    return df

st.session_state.df = refresh_errors(st.session_state.df)
df = st.session_state.df

# --- UI ---
st.title("🌱 Nursery QC & Correction Dashboard")

# 1. METRICS
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Records", len(df))
col2.metric("Active Errors", int(df['Total_Errors'].sum()))
col3.metric("Justified", int(df['Justification'].replace("", None).count()))
col4.metric("Accuracy Rate", f"{((len(df)-df['Total_Errors'].sum())/len(df)*100):.2f}%")

# 2. FILTERS
st.sidebar.header("Filters")
zone = st.sidebar.selectbox("Zone", ["All"] + sorted(df["Zone"].unique().tolist()))
df_f = df if zone == "All" else df[df["Zone"] == zone]

# 3. VISUALS
c1, c2, c3 = st.columns(3)
c1.caption("Errors by Cluster")
c1.bar_chart(df_f.groupby("Cluster")['Total_Errors'].sum())
c2.caption("Errors by Zone Trend")
c2.line_chart(df_f.groupby("Zone")['Total_Errors'].sum())
c3.caption("Errors by Woreda")
c3.bar_chart(df_f.groupby("Woreda")['Total_Errors'].sum())

# 4. CORRECTION CENTER
st.subheader("🛠 Correction & Justification Center")
error_df = df_f[df_f['Total_Errors'] > 0]
if not error_df.empty:
    edited_df = st.data_editor(error_df, key="main_editor", use_container_width=True)
    if st.button("Save Changes to GitHub"):
        df.update(edited_df)
        res = save_to_github(df, st.session_state.sha)
        if res.status_code == 200:
            st.session_state.df = df
            st.success("Saved successfully! Reloading...")
            st.rerun()
        else:
            st.error("Failed to save to GitHub.")
else:
    st.info("No active errors to correct in this selection.")

st.divider()
st.subheader("📋 Full Dataset")
st.dataframe(df_f, use_container_width=True)
