import streamlit as st
import asyncio
import pandas as pd
import threading
from trading_bot import bot_instance
import time
import json
from datetime import datetime

# Page Config
st.set_page_config(
    page_title="Coinbase Crypto Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Premium" look
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        color: #fafafa;
    }
    .stButton>button {
        color: white;
        background-color: #0052ff; /* Coinbase Blue */
        border-radius: 8px;
        height: 3em;
        width: 100%;
        border: none;
    }
    .metric-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Coinbase Pro Trading Bot")
st.markdown("### Algorithmic High-Frequency Trading System")

# Sidebar
st.sidebar.header("Control Panel")

# Bot Control Wrapper
# Streamlit runs in a separate thread/process model usually, 
# but for a local simpler app we can use threading to run the bot loop.

def run_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_instance.run_loop())

if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = None

# Mode Selection
mode = st.sidebar.radio("Trading Mode", ["Paper Trading (Simulated)", "Live Trading (Real $$$)"])
if "Paper" in mode:
    bot_instance.mode = "PAPER"
else:
    bot_instance.mode = "LIVE"

# Risk Level Details
risk_help = """
**🟢 Low Risk**: Breakout + 2 Confirmations (Strict/Sniper)
**🟡 Medium Risk**: Breakout + 1 Confirmation (Balanced)
**🔴 High Risk**: Immediate Breakout (Aggressive/Scalping)
"""
risk_selection = st.sidebar.select_slider(
    "Strategy Risk Level",
    options=["LOW", "MEDIUM", "HIGH"],
    value="LOW",
    help=risk_help
)
bot_instance.risk_level = risk_selection

status_placeholder = st.sidebar.empty()

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Data Management")

# Initialize session state for export if not present
if 'export_json' not in st.session_state:
    st.session_state['export_json'] = None
if 'export_filename' not in st.session_state:
    st.session_state['export_filename'] = None

if st.sidebar.button("Prepare Export File"):
    snapshot = bot_instance.get_system_snapshot()
    json_str = json.dumps(snapshot, indent=2, default=str)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Store in session state
    st.session_state['export_json'] = json_str
    st.session_state['export_filename'] = f"Coinbase_Export_{timestamp}.json"
    st.rerun()

# Display download button if data is ready
if st.session_state['export_json']:
    # debug: show the intended filename
    st.sidebar.caption(f"Ready: {st.session_state['export_filename']}")
    
    st.sidebar.download_button(
        label="📥 Download System Data (JSON)",
        data=st.session_state['export_json'], # Pass string directly
        file_name=st.session_state['export_filename'],
        mime="application/json",
        key="json_download_btn"
    )

if bot_instance.is_running:
    status_placeholder.success("Status: ● RUNNING")
    if st.sidebar.button("Stop Bot"):
        bot_instance.is_running = False
        st.rerun()
else:
    status_placeholder.error("Status: ● STOPPED")
    if st.sidebar.button("Start Bot"):
        # Start thread
        if st.session_state.bot_thread is None or not st.session_state.bot_thread.is_alive():
            t = threading.Thread(target=run_bot_thread, daemon=True)
            t.start()
            st.session_state.bot_thread = t
        st.rerun()

# Cache the product list to avoid API spam
@st.cache_data(ttl=3600)
def load_products():
    try:
        pairs = bot_instance.scanner.get_tradable_pairs()
        pairs.sort()
        return pairs
    except Exception as e:
        return ["BTC-USD", "ETH-USD"]

# Display Stored Data in Sidebar
st.sidebar.subheader("📂 Stored Market Data")
import os
data_dir = "data"
if os.path.exists(data_dir):
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    if files:
        # Show simplified view
        for f in files:
            # Format: BTC-USD_ONE_MINUTE.csv
            try:
                parts = f.replace(".csv", "").rsplit("_", 2) # BTC-USD, ONE, MINUTE ... tricky split
                # Smarter split: split by first "_" is dangerous because of product id.
                # Standardize filename in DataManager to be safe: product_granularity. 
                # Let's just show the filename for now or parse specifically.
                st.sidebar.caption(f"📄 {f}")
            except:
                st.sidebar.text(f)
    else:
        st.sidebar.caption("No data files found.")
else:
    st.sidebar.caption("No data directory.")


# Tabs
tab_live, tab_backtest, tab_opt = st.tabs(["🚀 Live Dashboard", "🧪 Backtester", "⚙️ Optimizer"])


with tab_live:
    # Dashboard Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Fetch fresh balance
        try:
            current_bal = bot_instance.get_balance()
            st.metric(f"Account Balance ({bot_instance.mode})", f"${current_bal:,.2f}")
        except:
            st.metric("Account Balance", "Error")
    with col2:
        st.metric("Active Trades", len(bot_instance.active_positions))
    with col3:
        wins = len([t for t in bot_instance.trade_history if t['pnl_usd'] > 0])
        total = len(bot_instance.trade_history)
        rate = (wins / total * 100) if total > 0 else 0
        st.metric("Win Rate", f"{int(rate)}%", delta=f"{total} trades")
    with col4:
        st.metric("Risk Level", bot_instance.risk_level, help="Current Strategy Aggressiveness")

    # Live Feed & Charts
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🔍 Candidates Watchlist (Scanner)")
        if bot_instance.candidates:
            df_cand = pd.DataFrame.from_dict(bot_instance.candidates, orient='index')
            st.dataframe(df_cand)
        else:
            st.info("Waiting for scanner results...")

        st.subheader("🟢 Active Positions")
        if bot_instance.active_positions:
            df_pos = pd.DataFrame(bot_instance.active_positions.values())
            st.dataframe(df_pos)
        else:
            st.info("No active positions.")

        st.subheader("📜 Trade History")
        if bot_instance.trade_history:
            df_hist = pd.DataFrame(bot_instance.trade_history)
            st.dataframe(df_hist)
        else:
            st.info("No closed trades yet.")

    with col_right:
        st.subheader("System Logs")
        log_container = st.container()
        with log_container:
            # Show last 50 logs
            for log in reversed(bot_instance.logs[-50:]):
                st.text(log)
                
        # Auto-refresh logic (basic)
        if bot_instance.is_running:
            time.sleep(1)
            st.rerun()

with tab_backtest:
    st.header("Strategy Backtester (MT5 Style)")
    st.markdown("Use this module to fetch historical data and simulate your strategy.")
    st.info("ℹ️ **Note**: Strategy uses **Multi-Timeframe Analysis**: Trend is calculated on **1H** (resampled) and Entries on **5M** (or selected timeframe).")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.subheader("1. Configuration")
        
        # Dropdown for Product ID
        available_products = load_products()
        default_idx = 0
        if "BTC-USD" in available_products:
            default_idx = available_products.index("BTC-USD")
            
        bt_product = st.selectbox("Product ID", available_products, index=default_idx)
        bt_granularity = st.selectbox("Timeframe", ["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"], index=1)
        
        # Date selection
        today = datetime.now()
        start_def = today - pd.Timedelta(days=30)
        bt_start_date = st.date_input("Start Date", value=start_def)
        bt_end_date = st.date_input("End Date", value=today)
        
        if st.button("Download Historical Data"):
            from backtester import Backtester
            bt = Backtester()
            with st.spinner("Downloading data... (Checking Pagination)"):
                # Convert date inputs to datetime
                s_dt = datetime.combine(bt_start_date, datetime.min.time())
                e_dt = datetime.combine(bt_end_date, datetime.max.time())
                
                # Progress Bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(pct):
                    progress_bar.progress(pct)
                    status_text.text(f"Downloading... {int(pct*100)}%")

                df_dl = bt.download_data(bt_product, s_dt, e_dt, bt_granularity, progress_callback=update_progress)
                
                # Clear progress when done
                progress_bar.empty()
                status_text.empty()
                
                if df_dl is not None:
                    st.success(f"Downloaded {len(df_dl)} candles!")
                    # Save to session or display
                    st.session_state['bt_data'] = df_dl
                    st.dataframe(df_dl.head())
                else:
                    st.error("Download failed or no data found.")

    with col_b2:
        st.subheader("2. Simulation")
        
        # Check if custom params are active
        active_params = None
        if 'active_strategy_params' in st.session_state:
            active_params = st.session_state['active_strategy_params']
            
            with st.expander("🔧 Active Strategy Parameters (Optimized)", expanded=True):
                st.json(active_params)
                if st.button("Reset to Defaults"):
                    del st.session_state['active_strategy_params']
                    st.rerun()
                    
        if 'bt_data' in st.session_state and st.button("Run Simulation"):
            from backtester import Backtester
            bt = Backtester()
            
            with st.spinner("Simulating Strategy..."):
                equity, trades = bt.run_backtest(
                    st.session_state['bt_data'], 
                    risk_level=bot_instance.risk_level,
                    strategy_params=active_params
                )
                
                # Metrics
                if not trades.empty:
                    total_pnl = trades['pnl'].sum()
                    win_rate = len(trades[trades['pnl'] > 0]) / len(trades) * 100
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total PnL", f"${total_pnl:,.2f}")
                    m2.metric("Total Trades", len(trades))
                    m3.metric("Win Rate", f"{win_rate:.1f}%")
                    
                    # Chart
                    st.subheader("Equity Curve")
                    st.line_chart(equity.set_index('timestamp')['equity'])
                    
                    st.subheader("Trade Log")
                    st.dataframe(trades)
                else:
                    st.warning("No trades generated during this period.")


