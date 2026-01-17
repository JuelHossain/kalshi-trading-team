import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
import numpy as np

# Load environment variables
load_dotenv('.env') # Try root first
load_dotenv('backend/.env') # Try backend
load_dotenv('../backend/.env') # Try relative

# Initialize Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

st.set_page_config(
    page_title="Sentient Alpha Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "The Matrix/Hacker" Aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp {
        background-color: #050505;
        color: #00FF41; 
    }
    
    * {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .stMarkdown, .stText, h1, h2, h3, h4 {
        color: #E0E0E0 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #00FF41 !important;
        background: #111;
        padding: 5px 10px;
        border-radius: 5px;
        border: 1px solid #333;
    }

    /* GitHub Calendar Grid Style */
    .pnl-grid {
        display: grid;
        grid-template-columns: repeat(52, 1fr);
        gap: 2px;
        padding: 10px;
        background: #000;
        border: 1px solid #222;
    }
    .pnl-cell {
        aspect-ratio: 1/1;
        border-radius: 2px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Reasoning Trace Container */
    .log-container {
        height: 500px;
        overflow-y: auto;
        background-color: #000;
        border: 1px solid #00FF41;
        padding: 15px;
        font-size: 13px;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.1);
    }
    
    .log-entry {
        margin-bottom: 8px;
        line-height: 1.4;
        border-left: 2px solid #333;
        padding-left: 10px;
    }
    
    .log-ts { color: #666; font-size: 11px; }
    .log-ag { color: #00FF41; font-weight: bold; }
    .log-msg { color: #DDD; }
    .log-success { color: #00FF41 !important; }
    .log-error { color: #FF3131 !important; border-left-color: #FF3131; }
    .log-warn { color: #FFD700 !important; border-left-color: #FFD700; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except:
        return None

supabase = init_supabase()

# --- SIDEBAR: VAULT STATUS ---
st.sidebar.markdown("# 🔐 VAULT STATUS")

def get_latest_balance():
    if not supabase: return 30000
    try:
        res = supabase.table('balance_history').select('balance_cents').order('created_at', desc=True).limit(1).execute()
        return res.data[0]['balance_cents'] if res.data else 30000
    except:
        return 30000

bal_cents = get_latest_balance()
principal = 300.00
current = bal_cents / 100.0
profit = current - principal

# Gauge Figure
fig_gauge = go.Figure(go.Indicator(
    mode = "gauge+number+delta",
    value = current,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "Total Vault ($)", 'font': {'size': 20, 'color': "#00FF41"}},
    delta = {'reference': principal, 'increasing': {'color': "#00FF41"}},
    gauge = {
        'axis': {'range': [200, 500], 'tickwidth': 1, 'tickcolor': "darkblue"},
        'bar': {'color': "#00FF41"},
        'bgcolor': "black",
        'borderwidth': 2,
        'bordercolor': "#333",
        'steps': [
            {'range': [0, principal], 'color': '#300'},
            {'range': [principal, principal+50], 'color': '#030'},
            {'range': [principal+50, 500], 'color': '#003'}
        ],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': principal * 0.85 # Kill switch line
        }
    }
))
fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white", 'family': "Arial"}, height=250, margin=dict(l=20, r=20, t=50, b=20))
st.sidebar.plotly_chart(fig_gauge, use_container_width=True)

st.sidebar.metric("Principal Reserve", f"${principal:.2f}")
st.sidebar.metric("House Money", f"${max(0, profit):.2f}", delta=f"${profit:.2f}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 AGENT STATUS")

def get_agent_statuses():
    if not supabase: return []
    try:
        res = supabase.table('agent_heartbeats').select('*').order('agent_id').execute()
        return res.data or []
    except:
        return []

agent_data = get_agent_statuses()
for agent in agent_data:
    # Handle both Z and non-Z formats
    ts_str = agent['last_active'].replace('Z', '+00:00')
    last_seen = datetime.fromisoformat(ts_str)
    
    # Check if active in last 5 minutes
    is_live = (datetime.now(last_seen.tzinfo) - last_seen).total_seconds() < 300 
    
    color = "#00FF41" if is_live else "#FF3131"
    st.sidebar.markdown(f"<span style='color:{color}'>●</span> Agent {agent['agent_id']}: {agent['agent_name']}", unsafe_allow_html=True)

if not agent_data:
    st.sidebar.caption("No heartbeat data found.")

# --- MAIN DASHBOARD ---
st.title("⚡ SENTIENT ALPHA COMMAND")

# Row 1: PnL Heatmap (GitHub Style)
st.subheader("📅 PERFORMANCE CALENDAR (PnL HEATMAP)")

def get_pnl_data():
    if not supabase:
        # Mocking for visual if DB empty
        dates = pd.date_range(end=datetime.now(), periods=365)
        data = np.random.normal(0, 10, 365)
        data[data > 40] = 60 
        data[data < -30] = -40 
        return pd.DataFrame({'date': dates, 'pnl': data})
    
    try:
        # Query balance history for last 365 days
        res = supabase.table('balance_history').select('balance_cents, created_at').order('created_at').execute()
        if not res.data:
            return pd.DataFrame()
            
        df = pd.DataFrame(res.data)
        df['date'] = pd.to_datetime(df['created_at']).dt.date
        # Daily PnL = last balance of day - last balance of previous day
        daily = df.groupby('date')['balance_cents'].last().reset_index()
        daily['pnl'] = daily['balance_cents'].diff().fillna(0) / 100.0
        
        # Merge with full date range to show empty days
        all_dates = pd.date_range(end=datetime.now().date(), periods=365).date
        full_df = pd.DataFrame({'date': all_dates})
        df_pnl = pd.merge(full_df, daily, on='date', how='left').fillna(0)
        
        return df_pnl
    except Exception as e:
        st.error(f"PnL Data Error: {e}")
        return pd.DataFrame()

pnl_df = get_pnl_data()

# Logic for colors: Blue (>50), Green (>0), Red (<0), Yellow (0/Flat)
def color_map(val):
    if val >= 50: return "#0070FF" # House Money Blue
    if val > 0: return "#00D100"   # Profit Green
    if val < 0: return "#FF3131"   # Loss Red
    return "#333"                  # Flat/No Trade

# Creating the grid
cols = st.columns(1)
with cols[0]:
    # Streamlit doesn't have a native calendar grid, but we can uses plotly heatmap or HTML
    pnl_df['week'] = pnl_df['date'].dt.isocalendar().week
    pnl_df['day'] = pnl_df['date'].dt.dayofweek
    
    # Pivot for Heatmap
    pivot = pnl_df.pivot(index='day', columns='week', values='pnl').fillna(0)
    
    fig_heat = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        colorscale=[
            [0, "#FF3131"],     # Red
            [0.4, "#333"],       # Gray/Yellowish
            [0.5, "#333"],
            [0.6, "#00D100"],   # Green
            [1.0, "#0070FF"]    # Blue
        ],
        showscale=False,
        xgap=3, ygap=3
    ))
    fig_heat.update_layout(
        height=200, 
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# Row 2: REASONING TRACE (Terminal Style)
st.subheader("🧠 REAL-TIME REASONING TRACE")

log_box = st.empty()

def fetch_logs_from_db():
    if not supabase: return []
    try:
        # Fetch from trade_history and trade_errors, merge and sort
        res = supabase.table('trade_history').select('*').order('created_at', desc=True).limit(50).execute()
        return res.data or []
    except:
        return []

# Simulation of "Live" trace if DB is slow or empty
def get_mock_trace():
    return [
        {"ts": "14:20:01", "ag": "2", "msg": "Scout identified NBA-LAL-BOS | Liquidity OK ($85k)", "type": "success"},
        {"ts": "14:20:03", "ag": "3", "msg": "Interceptor: Vegas Prob 58% vs Kalshi 52% | GAP: +6%", "type": "info"},
        {"ts": "14:20:05", "ag": "4", "msg": "Analyst: Committee Debate Complete. Confidence: 72%. Verdict: BUY", "type": "success"},
        {"ts": "14:20:07", "ag": "5", "msg": "Scientist: Monte Carlo (10k runs) -> EV +0.12 | WinRate: 61%", "type": "info"},
        {"ts": "14:20:08", "ag": "6", "msg": "Auditor: Cynicism Check Passed. No hallucination detected.", "type": "info"},
        {"ts": "14:20:10", "ag": "8", "msg": "Executioner: Order 0x9f2a FILLED @ 51c (Ref: Bid+1)", "type": "success"},
    ]

# Display Logs
logs = fetch_logs_from_db()
if not logs:
    display_logs = get_mock_trace()
else:
    display_logs = []
    for l in logs:
        display_logs.append({
            "ts": l['created_at'][11:19],
            "ag": str(l['agent_id']),
            "msg": f"{l['market_ticker']} | {l['action']} @ {l['price_cents']}c | {l['details'].get('judgeVerdict', '')}",
            "type": "success" if l['status'] == 'FILLED' else 'info'
        })

with log_box.container():
    st.markdown('<div class="log-container">', unsafe_allow_html=True)
    for l in display_logs:
        style_class = f"log-{l['type']}" if l.get('type') else ""
        st.markdown(f"""
        <div class="log-entry {style_class}">
            <span class="log-ts">[{l['ts']}]</span>
            <span class="log-ag">AGENT-{l['ag']}:</span>
            <span class="log-msg">{l['msg']}</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns(3)
col_f1.caption("System: SENTIENT ALPHA v2.1")
col_f2.caption("Status: FULLY AUTONOMOUS")
col_f3.caption("Last Sync: " + datetime.now().strftime("%H:%M:%S"))

# Auto-refresh
if st.sidebar.checkbox("Live Update (Every 5s)", value=True):
    time.sleep(5)
    st.rerun()

