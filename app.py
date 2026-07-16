import streamlit as st
import pandas as pd
import base64
import datetime
import io
import requests

# ============================================================================
# GITHUB ENVIRONMENT CONFIGURATION
# ============================================================================
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "control-sample-collction"
CSV_FILENAME = "amhara_me_2026.csv"

# ============================================================================
# CLOUD DATABASE STORAGE CORE LOGIC (GITHUB API)
# ============================================================================
def get_github_headers():
    token = st.secrets.get("github", {}).get("token")
    if not token:
        st.error("❌ GitHub token missing in .streamlit/secrets.toml!")
        return None
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def fetch_data_from_github() -> pd.DataFrame:
    headers = get_github_headers()
    if not headers: 
        return pd.DataFrame()
    
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            return pd.read_csv(io.StringIO(content))
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        
    return pd.DataFrame()

def save_data_to_github(updated_df: pd.DataFrame) -> bool:
    headers = get_github_headers()
    if not headers: 
        return False
    
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    
    response = requests.get(url, headers=headers)
    sha = response.json()['sha'] if response.status_code == 200 else None
    
    csv_data = updated_df.to_csv(index=False)
    encoded_data = base64.b64encode(csv_data.encode()).decode()
    
    payload = {
        "message": f"Nursery Sync - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": encoded_data,
        "branch": "main"  
    }
    if sha: 
        payload["sha"] = sha
        
    try:
        res = requests.put(url, headers=headers, json=payload, timeout=10)
        return res.status_code in [200, 201]
    except Exception as e:
        st.error(f"Network error during upload: {str(e)}")
        return False

# ============================================================================
# STATE ROUTING MANAGEMENT
# ============================================================================
if "page" not in st.session_state: st.session_state["page"] = "Home"
if "auth" not in st.session_state: st.session_state["auth"] = False

def nav(p):
    st.session_state["page"] = p
    st.rerun()

# ============================================================================
# INTERFACE CONFIGURATION
# ============================================================================
st.set_page_config(page_title="Nursery-Data-Analysis", layout="wide")

# ============================================================================
# INTERFACE: HOME SCREEN
# ============================================================================
if st.session_state["page"] == "Home":
    st.title("🌱 Nursery-Data-Analysis")
    st.divider()
    col1, col2 = st.columns(2)
    if col1.button("📝 NEW REGISTRATION", use_container_width=True, type="primary"): 
        nav("Reg")
    if col2.button("📊 ADMIN DASHBOARD", use_container_width=True): 
        nav("Data")

# ============================================================================
# INTERFACE: REGISTRATION FORM
# ============================================================================
elif st.session_state["page"] == "Reg":
    st.button("⬅️ Back to Home Layout", on_click=lambda: nav("Home"))
    
    st.header("📝 New Nursery Entry")
    with st.form("nursery_form", clear_on_submit=True):
        
        st.subheader("1. Location Details")
        col1, col2 = st.columns(2)
        zone = col1.text_input("Zone")
        woreda = col2.text_input("Woreda")
        kebele = col1.text_input("Kebele")
        cluster = col2.text_input("Cluster")
        
        st.subheader("2. Species & Metrics")
        species_list = [
            "Gesho", "Gaviliya", "Decurence", "Wanza", "Papaya", 
            "Lemon", "Guava", "Moringa", "Coffee", "Neem", "Arzelibanos"
        ]
        species = st.selectbox("Select Tree/Seed Species", species_list)
        
        m1, m2 = st.columns(2)
        ready = m1.number_input("Count Ready", min_value=0)
        non_ready = m2.number_input("Count Non Ready", min_value=0)
        total = m1.number_input("Total Count", min_value=0)
        mdb = m2.number_input("MDB Plan", min_value=0)
        healthy = m1.number_input("Healthy Seeding", min_value=0)
        ready_sd = m2.number_input("Ready Seedling", min_value=0)
        
        if st.form_submit_button("Submit Data Record"):
            if zone and woreda and kebele:
                with st.spinner("Syncing to GitHub Database..."):
                    df = fetch_data_from_github()
                    
                    new_entry = pd.DataFrame([{
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Species": species,
                        "Zone": zone,
                        "Woreda": woreda, 
                        "Kebele": kebele, 
                        "Cluster": cluster,
                        "Count Ready": ready, 
                        "Count Non Ready": non_ready, 
                        "Total Count": total,
                        "MDB Plan": mdb, 
                        "Healthy Seeding": healthy, 
                        "Ready Seedling": ready_sd
                    }])
                    
                    updated_df = pd.concat([df, new_entry], ignore_index=True)
                    if save_data_to_github(updated_df):
                        st.success(f"✅ Data for {species} in {kebele} synced successfully!")
                    else:
                        st.error("❌ Failed to save data. Check GitHub configurations.")
            else:
                st.error("Zone, Woreda, and Kebele are mandatory fields.")

# ============================================================================
# INTERFACE: ADMINISTRATIVE COMPLIANCE PANELS
# ============================================================================
elif st.session_state["page"] == "Data":
    st.button("⬅️ Back to Home Layout", on_click=lambda: nav("Home"))
    
    if not st.session_state["auth"]:
        st.header("🔒 Admin Access Verification")
        pass_input = st.text_input("Enter Passcode Token", type="password")
        if st.button("Validate"):
            if pass_input == "oaf2026": 
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Invalid passcode.")
    else:
        df = fetch_data_from_github()
        
        col_t, col_l = st.columns([8, 2])
        col_t.header("📊 Admin Management Station")
        if col_l.button("🔒 Lock Portal"):
            st.session_state["auth"] = False
            st.rerun()

        if not df.empty:
            st.subheader("Filter Data")
            
            # --- Dynamic Filtering ---
            f1, f2, f3 = st.columns(3)
            
            # 1. Species Filter
            species_options = ["All"] + sorted(df["Species"].astype(str).unique().tolist()) if "Species" in df.columns else ["All"]
            selected_species = f1.selectbox("Filter by Species", species_options)
            filtered_df = df if selected_species == "All" else df[df["Species"] == selected_species]
            
            # 2. Woreda Filter
            woreda_options = ["All"] + sorted(filtered_df["Woreda"].astype(str).unique().tolist()) if "Woreda" in filtered_df.columns else ["All"]
            selected_woreda = f2.selectbox("Select Woreda", woreda_options)
            filtered_df = filtered_df if selected_woreda == "All" else filtered_df[filtered_df["Woreda"] == selected_woreda]
            
            # 3. Kebele Filter
            kebele_options = ["All"] + sorted(filtered_df["Kebele"].astype(str).unique().tolist()) if "Kebele" in filtered_df.columns else ["All"]
            selected_kebele = f3.selectbox("Select Kebele", kebele_options)
            filtered_df = filtered_df if selected_kebele == "All" else filtered_df[filtered_df["Kebele"] == selected_kebele]

            # --- Metrics Display ---
            st.divider()
            st.subheader(f"Analysis Results: {selected_species} | {selected_woreda} | {selected_kebele}")
            
            # We use pd.to_numeric to ensure we are adding numbers safely
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Count", int(pd.to_numeric(filtered_df.get("Total Count", 0)).sum()))
            m2.metric("MDB Plan", int(pd.to_numeric(filtered_df.get("MDB Plan", 0)).sum()))
            m3.metric("Healthy Seeding", int(pd.to_numeric(filtered_df.get("Healthy Seeding", 0)).sum()))
            m4.metric("Ready Seedling", int(pd.to_numeric(filtered_df.get("Ready Seedling", 0)).sum()))

            st.divider()
            st.subheader("Raw Data Table")
            st.dataframe(filtered_df, use_container_width=True)
            
            st.download_button(
                label="📥 Extract Filtered Data (CSV)",
                data=filtered_df.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"Nursery_Data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                use_container_width=True
            )
        else:
            st.info("No records are currently stored inside your remote GitHub cloud database file.")
