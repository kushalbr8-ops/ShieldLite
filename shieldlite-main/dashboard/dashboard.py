# shieldlite/dashboard/dashboard.py

import os
import sqlite3
from datetime import timedelta

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# -----------------------
# Env + config
# -----------------------
BASE_DIR = os.path.dirname(__file__)
BACKEND_ENV_PATH = os.path.join(BASE_DIR, "..", "backend", ".env")
load_dotenv(BACKEND_ENV_PATH)

ADMIN_PASS = os.getenv("DASH_PASS", "changeme")
SHIELD_API_KEY = os.getenv("SHIELD_API_KEY", "")
SHIELD_BACKEND_URL = os.getenv("SHIELD_BACKEND_URL", "http://127.0.0.1:8000")

DB_PATH = os.path.join(BASE_DIR, "..", "backend", "shieldlite.db")

st.set_page_config(page_title="ShieldLite Dashboard", layout="wide")
st.title("🛡️ ShieldLite – Real-Time Attack Monitoring")

# -----------------------
# Simple auth
# -----------------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.subheader("Admin Login")
    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("Enter dashboard password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if pwd == ADMIN_PASS:
                st.session_state.auth = True
                st.success("Login successful — dashboard will load on next refresh.")
            else:
                st.error("Invalid password")
    # block rest of page until authenticated
    st.stop()

# -----------------------
# Auto-refresh
# -----------------------
refresh_rate = st.sidebar.slider("Auto-refresh interval (seconds)", 2, 30, 5)
st_autorefresh(interval=refresh_rate * 1000, key="auto_refresh")

# -----------------------
# DB connection + data load
# -----------------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(ttl=3)
def load_attacks(limit=2000):
    df = pd.read_sql_query(
        f"SELECT * FROM attacks ORDER BY timestamp DESC LIMIT {limit}", conn
    )
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return df

df = load_attacks(1000)

# -----------------------
# Sidebar filters
# -----------------------
st.sidebar.header("Filters")

ip_filter = st.sidebar.text_input("Filter by IP (contains)")

if df.empty:
    attack_types = ["(any)"]
else:
    attack_types = ["(any)"] + sorted(df["attack_type"].dropna().unique().tolist())

attack_filter = st.sidebar.selectbox("Attack type", attack_types)
blocked_filter = st.sidebar.selectbox("Blocked", ["(any)", "Yes", "No"])
days = st.sidebar.slider("Show last N days", 1, 30, 7)

# Apply filters
if not df.empty:
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    df = df[df["timestamp"] >= cutoff]

    if ip_filter:
        df = df[df["ip"].astype(str).str.contains(ip_filter)]

    if attack_filter != "(any)":
        df = df[df["attack_type"] == attack_filter]

    if blocked_filter == "Yes":
        df = df[df["blocked"] == 1]
    elif blocked_filter == "No":
        df = df[df["blocked"] == 0]

# -----------------------
# Metrics
# -----------------------
col1, col2, col3 = st.columns(3)
col1.metric("Total Attacks (shown)", len(df))
col2.metric("Unique Attackers (IPs)", df["ip"].nunique() if not df.empty else 0)
col3.metric(
    "Blocked IPs (shown)",
    df[df["blocked"] == 1]["ip"].nunique() if not df.empty else 0,
)

# -----------------------
# Latest Attacks table
# -----------------------
st.markdown("### 📌 Latest Attacks")

if df.empty:
    st.info("No attack records in the selected range / filters.")
else:
    st.dataframe(
        df.reset_index(drop=True),
        use_container_width=True,
        height=360,
    )

    # CSV export
    csv = df.to_csv(index=False)
    st.download_button(
        "⬇️ Download CSV (filtered)",
        data=csv,
        file_name="shieldlite_attacks.csv",
        mime="text/csv",
    )

    # -----------------------
    # Attack distribution
    # -----------------------
    st.markdown("### 📊 Attack Type Distribution")
    attack_counts = df["attack_type"].fillna("unknown").value_counts()
    if not attack_counts.empty:
        st.bar_chart(attack_counts)

    # -----------------------
    # Time series: attacks per hour
    # -----------------------
    st.markdown("### ⏱ Attacks Over Time (Hourly)")
    ts = df.set_index("timestamp").resample("1H").size()
    if not ts.empty:
        st.line_chart(ts)

    # -----------------------
    # Blocked IPs + Unblock button
    # -----------------------
    st.markdown("### 🚫 Blocked IPs (recent)")

    blocked = (
        df[df["blocked"] == 1][["ip", "attack_type", "timestamp"]]
        .drop_duplicates("ip")
        .sort_values("timestamp", ascending=False)
    )

    if blocked.empty:
        st.info("No blocked IPs in the current view.")
    else:
        for _, row in blocked.head(50).iterrows():
            ip = row["ip"]
            atype = row["attack_type"]
            ts_val = row["timestamp"]

            cols = st.columns([2, 2, 2, 1])
            cols[0].write(ip)
            cols[1].write(str(atype))
            cols[2].write(str(ts_val))

            if cols[3].button("Unblock", key=f"unblock_{ip}"):
                # call backend /unblock
                try:
                    headers = {"Content-Type": "application/json"}
                    if SHIELD_API_KEY:
                        headers["X-API-KEY"] = SHIELD_API_KEY
                    resp = requests.post(
                        f"{SHIELD_BACKEND_URL}/unblock",
                        json={"ip": ip},
                        headers=headers,
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        st.success(f"Unblock request sent for {ip}")
                    else:
                        st.error(
                            f"Unblock failed for {ip}: {resp.status_code} {resp.text}"
                        )
                except Exception as e:
                    st.error(f"Error calling unblock for {ip}: {e}")

# -----------------------
# Footer
# -----------------------
st.markdown("---")
st.caption(
    "ShieldLite — local prototype. For production: run behind HTTPS (nginx), use strong secrets, and host backend + dashboard on secure infrastructure."
)