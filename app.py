import streamlit as st
import pandas as pd
import base64
import datetime
import io
import requests

# CONFIG
GITHUB_OWNER = "Derese4803"
GITHUB_REPO = "control-sample-collction"
CSV_FILENAME = "amhara_me_2026.csv"

# --- CORE LOGIC ---
def get_github_headers():
    token = st.secrets.get("github", {}).get("token")
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"} if token else None

def fetch_data_from_github() -> pd.DataFrame:
    headers = get_github_headers()
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            return pd.read_csv(io.StringIO(content))
    except: pass
    return pd.DataFrame()

def save_data_to_github(updated_df: pd.DataFrame) -> bool:
    headers = get_github_headers()
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{CSV_FILENAME}"
    res_get = requests.get(url, headers=headers)
    sha = res_get.json()['sha'] if res_get.status_code == 200 else None
    csv_data = updated_df.to_csv(index=False)
    payload = {"message": "Nursery Data Sync", "content": base64.b64encode(csv_data.encode()).decode(), "branch": "main"}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code in [200, 201]

# --- SESSION STATE ---
if "page" not in st.session_state: st.session_state["page"] = "Home"
if "editor" not in st.session_state: st.session_state["editor"] = None
if "auth" not in st.session_state: st.session_state["auth"] = False

def nav(p): st.session_state["page"] = p; st.rerun()

# --- UI ---
st.set_page_config(page_title="Nursery-Data-Analysis", layout="wide")

if st.session_state["page"] == "Home":
    st.title("🌱 Nursery-Data-Analysis")
    if st.session_state["editor"]: st.success(f"👤 Active Agent: {st.session_state['editor']}")
    c1, c2 = st.columns(2)
    if c1.button("📝 NEW REGISTRATION"): nav("Reg")
    if c2.button("📊 ADMIN DASHBOARD"): nav("Data")

elif st.session_state["page"] == "Reg":
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    if not st.session_state["editor"]:
        name_in = st.text_input("Enter your Full Name to begin:")
        if st.button("Initialize Session") and name_in: st.session_state["editor"] = name_in; st.rerun()
    else:
        with st.form("nursery_form"):
            f_name = st.text_input("Farmer Name")
            woreda = st.text_input("Woreda Zone")
            kebele = st.text_input("Kebele Locality")
            # Gesho Fields
            ready = st.number_input("Gesho Count Ready", 0)
            non_ready = st.number_input("Gesho Count Non Ready", 0)
            healthy = st.number_input("Gesho Healthy Seeding", 0)
            
            if st.form_submit_button("Submit Data"):
                df = fetch_data_from_github()
                new_entry = pd.DataFrame([{
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "user-name": st.session_state["editor"],
                    "Farmer Name": f_name, "Woreda Zone": woreda, "Kebele Locality": kebele,
                    "Gesho Count Ready": ready, "Gesho Count Non Ready": non_ready, "Gesho Healthy Seeding": healthy
                }])
                if save_data_to_github(pd.concat([df, new_entry], ignore_index=True)): st.success("Data Synced Successfully!")

elif st.session_state["page"] == "Data":
    st.button("⬅️ Back", on_click=lambda: nav("Home"))
    if not st.session_state["auth"]:
        if st.text_input("Admin Token", type="password") == "oaf2026": st.session_state["auth"] = True; st.rerun()
    else:
        df = fetch_data_from_github()
        if not df.empty:
            st.header("📊 Nursery Analysis Overview")
            w = st.selectbox("Filter by Woreda", ["All"] + df["Woreda Zone"].unique().tolist())
            filtered = df if w == "All" else df[df["Woreda Zone"] == w]
            k = st.selectbox("Filter by Kebele", ["All"] + filtered["Kebele Locality"].unique().tolist())
            final_df = filtered if k == "All" else filtered[filtered["Kebele Locality"] == k]
            
            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Gesho Ready", int(final_df["Gesho Count Ready"].sum()))
            m2.metric("Gesho Non-Ready", int(final_df["Gesho Count Non Ready"].sum()))
            m3.metric("Gesho Healthy", int(final_df["Gesho Healthy Seeding"].sum()))
            
            st.dataframe(final_df, use_container_width=True)
