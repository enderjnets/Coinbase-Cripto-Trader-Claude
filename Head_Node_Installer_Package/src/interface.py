import streamlit as st
import asyncio
import pandas as pd
import threading
import threading
from trading_bot import TradingBot
import time
import time
import json
from datetime import datetime

# --- BROKER & BOT SETUP ---
from backtester import Backtester
from coinbase_client import CoinbaseClient
from scanner import MarketScanner
from schwab_client import SchwabClient

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

def run_bot_thread(bot_ref):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_ref.run_loop())

if "bots" not in st.session_state:
    st.session_state['bots'] = {
        'Coinbase': TradingBot(broker_type="COINBASE"),
        'Schwab': TradingBot(broker_type="SCHWAB")
    }

if "bot_threads" not in st.session_state:
    st.session_state['bot_threads'] = {}

# Helper to get active bot based on section or selection
# Default to Coinbase for general views
if 'active_bot_key' not in st.session_state:
    st.session_state['active_bot_key'] = 'Coinbase'

bot_instance = st.session_state['bots'][st.session_state['active_bot_key']]


# Mode Selection
mode = st.sidebar.radio("Trading Mode", ["Paper Trading (Simulated)", "Live Trading (Real $$$)"])
if "Paper" in mode:
    bot_instance.mode = "PAPER"
else:
    bot_instance.mode = "LIVE"

st.sidebar.markdown("---")
# Broker Selection (New)
broker_selection = st.sidebar.radio("Connect via", ["Coinbase (Crypto)", "Charles Schwab (Stocks)"])

# Initialize Broker Client in Session State if changed
if 'active_broker_name' not in st.session_state:
    st.session_state['active_broker_name'] = "Coinbase (Crypto)"
    
if broker_selection != st.session_state['active_broker_name']:
    st.session_state['active_broker_name'] = broker_selection
    # Logic to switch broker client will be handled where it is needed (Backtester/Scanner)
    st.toast(f"Switched to {broker_selection}", icon="🔄")
    st.rerun()

is_crypto = "Coinbase" in broker_selection
is_stocks = "Schwab" in broker_selection

# Select Broker Client
if is_stocks:
    try:
        broker_client = SchwabClient()
        # st.toast("Schwab Client Active", icon="🏦")
    except Exception as e:
        st.error(f"Failed to initialize Schwab Client: {e}")
        broker_client = CoinbaseClient() # Fallback
else:
    broker_client = CoinbaseClient()

# Initialize Components with Broker
bt = Backtester(broker_client=broker_client)
scanner = MarketScanner(broker_client=broker_client)

st.title(f"⚡ {'Schwab Pro Trader' if is_stocks else 'Coinbase Crypto Bot'}")

# --- Navigation ---
nav_mode = st.sidebar.radio(
    "Navigation", 
    ["🤖 Live Dashboard", "⚡ Bitcoin Spot Pro", "🧪 Backtester", "⚙️ Optimizer", "⛏️ Strategy Miner (AI)"]
)


if nav_mode == "⚡ Bitcoin Spot Pro":
    st.subheader("Bitcoin Spot Pro 🚀 (BTC-USDC)")
    
    if is_stocks:
        st.warning("⚠️ You are in 'Charles Schwab' mode. Bitcoin Spot Pro requires Coinbase.")
        if st.button("Switch to Coinbase"):
            st.session_state.broker_choice = "Coinbase (Crypto)"
            st.rerun()
    else:
        tab_swing, tab_grid, tab_calc = st.tabs(["📉 Swing Trader", "🕸️ Grid Bot", "🧮 Position Calculator"])
        
        with tab_swing:
            st.markdown("### Intraday Swing (H1/H4)")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("BTC Price", "$95,432.10", "+1.2%") # Mock
            with col2:
                st.metric("Market Regime", "Lateral / Range", "Neutral")
                
            st.info("ℹ️ Strategy: Bollinger Bands (20,2) + RSI(<30) Reversion")
            if st.button("Analyze Swing Setup"):
                st.write("Fetching H1 data...")
                from btc_spot_strategy import BitcoinSpotStrategy
                strat = BitcoinSpotStrategy(None)
                st.success("Analysis Complete: No Signal (RSI=45)")
                
            # --- STRATEGY CONTROL ---
            st.divider()
            
            # Check if this specific strategy matches the active one
            from btc_spot_strategy import BitcoinSpotStrategy
            
            # Helper to check if current strategy is BTC Spot
            is_btc_strat_active = isinstance(bot_instance.strategy, BitcoinSpotStrategy)
            
            col_ctrl_1, col_ctrl_2 = st.columns([2, 1])
            with col_ctrl_1:
                st.markdown("### 🤖 Strategy Activation")
                if is_btc_strat_active and bot_instance.is_running:
                     st.success("✅ Bitcoin Spot Pro Strategy is RUNNING")
                     if st.button("Stop Strategy", key="stop_btc"):
                         bot_instance.is_running = False
                         st.rerun()
                else:
                     st.warning("Strategy is STOPPED or another strategy is active.")
                     if st.button("🚀 START Bitcoin Spot Strategy", key="start_btc"):
                         # Initialize and assign strategy
                         # Ensure we are using the Coinbase bot (active one in this view)
                         cb_bot = st.session_state['bots']['Coinbase']
                         cb_bot.strategy = BitcoinSpotStrategy(cb_bot.broker)
                         cb_bot.is_running = True
                         
                         # Ensure thread is running
                         if 'Coinbase' not in st.session_state['bot_threads'] or \
                            st.session_state['bot_threads']['Coinbase'] is None or \
                            not st.session_state['bot_threads']['Coinbase'].is_alive():
                                
                            t = threading.Thread(target=run_bot_thread, args=(cb_bot,), daemon=True)
                            t.start()
                            st.session_state['bot_threads']['Coinbase'] = t
                            
                         st.toast("Bitcoin Strategy Activated!", icon="🚀")
                         time.sleep(1)
                         st.rerun()


        with tab_grid:
            st.markdown("### Geometric Grid (Fee-Aware)")
            st.caption("Optimized for Coinbase Maker Fees (0.4%)")
            
            c1, c2, c3 = st.columns(3)
            lower = c1.number_input("Lower Range ($)", value=90000)
            upper = c2.number_input("Upper Range ($)", value=98000)
            grids = c3.number_input("Grid Levels", value=10, min_value=2)
            
            if st.button("Preview Grid"):
                from btc_spot_strategy import BitcoinSpotStrategy
                strat = BitcoinSpotStrategy(None)
                levels, gap = strat.generate_grid_levels(0, lower, upper, grids)
                
                st.write(f"**Grid Gap:** {gap:.2f}%")
                if gap < 1.2:
                    st.error(f"❌ Gap too small! Fees will eat profits. Aim for > 1.2%")
                else:
                    st.success("✅ Gap Healthy (Covers Fees + Profit)")
                    st.dataframe(pd.DataFrame(levels, columns=["Price Level"]))

        with tab_calc:
            st.markdown("### Risk & Position Sizing")
            cap = st.number_input("Account Balance ($)", value=10000.0)
            risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)
            
            c_ent, c_stop = st.columns(2)
            entry = c_ent.number_input("Entry Price ($)", value=50000.0)
            stop = c_stop.number_input("Stop Loss ($)", value=49000.0)
            
            if entry > stop:
                risk_usd = cap * (risk_pct/100)
                diff = entry - stop
                shares = risk_usd / diff
                pos_size = shares * entry
                
                st.divider()
                st.metric("Max Position Size", f"${pos_size:,.2f}", f"{shares:.4f} BTC")
                st.caption(f"Risking ${risk_usd:.2f} to lose 1% if stopped out.")
            else:
                st.error("Stop Loss must be lower than Entry.")
    
    # --- Strategy Monitor (Manual Refresh) ---
    st.markdown("---")
    st.subheader("📡 Strategy Monitor (Snapshot)")
    
    col_mon_1, col_mon_2 = st.columns([2, 1])
    
    # Use generic bot instance for this view (Coinbase usually)
    mon_bot = st.session_state['bots']['Coinbase']
    
    with col_mon_1:
         st.markdown("**Active Positions**")
         if mon_bot.active_positions:
             st.dataframe(pd.DataFrame(mon_bot.active_positions.values()))
         else:
             st.caption("No active positions.")
             
         st.markdown("**Scanner Candidates**")
         if mon_bot.candidates:
             st.dataframe(pd.DataFrame.from_dict(mon_bot.candidates, orient='index'))
         else:
             st.caption("No candidates.")

    # --- Live Charts ---
    st.markdown("### 📊 Contexto de Mercado (1H)")
    
    # Status Metrics
    m1, m2, m3 = st.columns(3)
    
    # helper for safe access
    l_trend = getattr(mon_bot, 'last_trend', 'WAITING')
    l_price = getattr(mon_bot, 'last_price', 0.0)
    l_time = getattr(mon_bot, 'last_analysis_time', '-')
    
    m1.metric("Tendencia Mercado", l_trend, delta=None, delta_color="off")
    m2.metric("Último Cierre", f"${l_price:,.2f}")
    m3.metric("Último Análisis", l_time)
    
    if st.button("📉 Cargar Gráficos", key="load_charts_btc"):
        with st.spinner("Fetching market data..."):
            # Fetch Data
            end_ts = int(time.time())
            start_ts = end_ts - (100 * 3600) # 100 hours
            
            # Use the bot's scanner/strategy to ensure consistency
            try:
                df_chart = mon_bot.scanner.get_candles("BTC-USD", start_ts, end_ts, "ONE_HOUR")
                if df_chart is not None and not df_chart.empty:
                    # Calculate Indicators
                    df_chart = mon_bot.strategy.calculate_indicators(df_chart)
                    
                    # Chart 1: Price vs BB
                    st.caption("Precio vs Bandas de Bollinger")
                    chart_data = df_chart[['close', 'BB_UPPER', 'BB_LOWER']].copy()
                    st.line_chart(chart_data, color=["#ffffff", "#00ff00", "#ff0000"]) # White Price, Green Upper, Red Lower
                    
                    # Chart 2: RSI
                    st.caption("RSI (Momento)")
                    rsi_data = df_chart[['RSI']].copy()
                    # Add threshold lines manually or just show the line
                    st.line_chart(rsi_data, color="#00aaff")
                    
                    curr_rsi = rsi_data.iloc[-1]['RSI']
                    st.metric("RSI Actual", f"{curr_rsi:.2f}", delta=None)
                    
                else:
                    st.error("No se recibieron datos de Coinbase.")
            except Exception as e:
                st.error(f"Chart Error: {e}")

    with col_mon_2:

        st.markdown("**System Logs**")
        if st.button("🔄 Refresh Monitor"):
            st.rerun()
            
        with st.container(height=300):
            for log in reversed(mon_bot.logs[-20:]):
                st.text(log)


elif nav_mode == "🤖 Live Dashboard":

    # --- Existing Main Dashboard Logic ---
    st.write("") # Spacer

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
# Update the ACTIVE bot's risk level directly
st.session_state['bots'][st.session_state['active_bot_key']].risk_level = risk_selection


status_placeholder = st.sidebar.empty()

st.sidebar.markdown("---")
with st.sidebar.expander("🔑 API Credentials"):
    if is_stocks:
        st.subheader("Charles Schwab")
        schwab_key = st.text_input("App Key", value="", type="password")
        schwab_secret = st.text_input("App Secret", value="", type="password")
        if st.button("Save Schwab Keys"):
            # Placeholder for saving mechanism
            st.toast("Keys Saved (Session Only)", icon="💾")
    else:
        st.subheader("Coinbase Advanced")
        cb_key = st.text_input("API Key Name", value="", type="password")
        cb_secret = st.text_input("Private Key", value="", type="password")
        if st.button("Save Coinbase Keys"):
            st.toast("Keys Saved (Session Only)", icon="💾")

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
    st.session_state['export_filename'] = f"{'Schwab' if is_stocks else 'Coinbase'}_Export_{timestamp}.json"
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

st.sidebar.subheader("🤖 Bot Manager")

# Iterate over all bots to show controls
for bot_name, bot_obj in st.session_state['bots'].items():
    with st.sidebar.expander(f"{bot_name} Bot", expanded=True):
        status_ph = st.empty()
        
        if bot_obj.is_running:
            status_ph.success("● RUNNING")
            if st.button(f"Stop {bot_name}", key=f"stop_{bot_name}"):
                bot_obj.is_running = False
                st.rerun()
        else:
            status_ph.error("● STOPPED")
            if st.button(f"Start {bot_name}", key=f"start_{bot_name}"):
                # Start thread
                if bot_name not in st.session_state['bot_threads'] or \
                   st.session_state['bot_threads'][bot_name] is None or \
                   not st.session_state['bot_threads'][bot_name].is_alive():
                       
                    t = threading.Thread(target=run_bot_thread, args=(bot_obj,), daemon=True)
                    t.start()
                    st.session_state['bot_threads'][bot_name] = t
                st.rerun()
                
# Sync active bot selection with sidebar if needed, or just let the tabs decide.
# For the main view, we might want to select which one to "monitor"
st.sidebar.markdown("---")
view_target = st.sidebar.selectbox("Dashboard View Source", list(st.session_state['bots'].keys()), index=0)
if view_target != st.session_state['active_bot_key']:
    st.session_state['active_bot_key'] = view_target
    st.rerun()

# Update global reference for the rest of the script (Dashboard, etc)
bot_instance = st.session_state['bots'][st.session_state['active_bot_key']]


# Cache the product list to avoid API spam
@st.cache_data(ttl=3600)
def load_products():
    try:
        # Use the global broker_client instance directly for reliability
        pairs = broker_client.get_tradable_symbols()
        if not pairs:
             pairs = ["BTC-USD", "ETH-USD"]
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


# --- DASHBOARD LOGIC ---
if nav_mode == "🤖 Live Dashboard":
    st.header("🚀 Live Trading Dashboard")

    # Top Metrics Row
    col_bal, col_pos, col_pnl, col_status = st.columns(4)
    
    curr_bal = bot_instance.get_balance() if hasattr(bot_instance, 'get_balance') else 0.0
    active_count = len(bot_instance.active_positions)
    
    session_pnl = sum(t['pnl_usd'] for t in bot_instance.trade_history) if bot_instance.trade_history else 0.0
    
    with col_bal:
        st.metric("Balance", f"${curr_bal:,.2f}", f"{'Paper' if bot_instance.mode=='PAPER' else 'Live'}")
        
    with col_pos:
        st.metric("Open Positions", active_count, delta_color="off")
        
    with col_pnl:
        st.metric("Session PnL", f"${session_pnl:,.2f}", delta_color="normal")
        
    with col_status:
        status_txt = "RUNNING" if bot_instance.is_running else "STOPPED"
        # Color code status
        st.markdown(f"**Status**: :{'green' if bot_instance.is_running else 'red'}[{status_txt}]")

    st.divider()

    # Main Content Area
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        st.subheader("📉 Active Positions")
        if bot_instance.active_positions:
            pos_data = []
            for pid, pdata in bot_instance.active_positions.items():
                row = pdata.copy()
                row['ticker'] = pid
                # Ensure JSON serializable columns mostly
                pos_data.append(row)
            
            df_pos = pd.DataFrame(pos_data)
            
            # Reorder if cols exist
            desired_order = ['ticker', 'side', 'entry_price', 'size', 'pnl', 'entry_time']
            final_cols = [c for c in desired_order if c in df_pos.columns]
            # Add others
            for c in df_pos.columns:
                if c not in final_cols:
                    final_cols.append(c)
            
            st.dataframe(df_pos[final_cols], use_container_width=True)
            
            if st.button("🚨 PANIC SELL ALL", type="primary", key="panic_btn"):
                if bot_instance.mode == "PAPER":
                     bot_instance.active_positions.clear()
                     bot_instance.log("🚨 PANIC SELL EXECUTED (Paper)")
                     st.warning("All positions closed (Paper mode)")
                     time.sleep(1)
                     st.rerun()
                else:
                    st.error("Panic Sell not implemented for Live mode yet (Safety).")
        else:
            st.info("No active positions. Waiting for signals...")
            
        st.subheader("📜 Recent Trade History")
        if bot_instance.trade_history:
            df_hist = pd.DataFrame(bot_instance.trade_history)
            st.dataframe(df_hist.iloc[::-1], use_container_width=True)
        else:
            st.caption("No trades executed yet in this session.")

    with col_side:
        st.subheader("📡 Live Feed")
        
        # Refresh Button
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.rerun()

        st.markdown("**System Logs**")
        log_txt = "\n".join(reversed(bot_instance.logs[-50:]))
        st.text_area("Logs", value=log_txt, height=400, disabled=True, label_visibility="collapsed")



# --- BACKTESTER LOGIC ---
elif nav_mode == "🧪 Backtester":
    st.header("Strategy Backtester (MT5 Style)")
    st.markdown("Use this module to fetch historical data and simulate your strategy.")
    st.info("ℹ️ **Note**: Strategy uses **Multi-Timeframe Analysis**: Trend is calculated on **1H** (resampled) and Entries on **5M** (or selected timeframe).")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.subheader("1. Configuration")
        
        if is_stocks:
            bt_product = st.text_input("Ticker Symbol", value="NVDA").upper()
        else:
            # Dropdown for Product ID (Crypto)
            available_products = load_products()
            default_idx = 0
            if "BTC-USD" in available_products:
                default_idx = available_products.index("BTC-USD")
            bt_product = st.selectbox("Product ID", available_products, index=default_idx)
            
        # Strategy Selector
        st.subheader("Strategy Selection")
        strategy_options = {
            "Bitcoin Spot Pro (BTC)": "BTC_SPOT",
            "Hybrid Strategy (Generic)": "HYBRID"
        }
        
        selected_strat_name = st.selectbox("Select Strategy", list(strategy_options.keys()))
        selected_strat_code = strategy_options[selected_strat_name]
        
        st.caption(f"Testing logic: **{selected_strat_name}**")

        bt_granularity = st.selectbox("Timeframe", ["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"], index=2 if selected_strat_code == "BTC_SPOT" else 3)
        if selected_strat_code == "BTC_SPOT":
             st.info("ℹ️ Bitcoin Spot Pro is designed for 5M entries with 1H Trend confirmation.")
            
        # Date selection
        
        # Date selection
        today = datetime.now()
        start_def = today - pd.Timedelta(days=30)
        bt_start_date = st.date_input("Start Date", value=start_def)
        bt_end_date = st.date_input("End Date", value=today)
        
        if st.button("Download Historical Data"):
            # Use global bt instance (already initialized with correct broker)
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
                    
        # Run Simulation Button & Logic
        if 'bt_data' in st.session_state and st.button("Run Simulation (Distributed)"):
             from backtest_runner import BacktestRunner
             
             # Initialize state
             st.session_state['sim_running'] = True
             st.session_state['sim_logs'] = []
             st.session_state['sim_progress'] = 0.0
             st.session_state['sim_results'] = None
             
             runner = BacktestRunner()
             prog_q, res_q = runner.start(
                 st.session_state['bt_data'],
                 bot_instance.risk_level,
                 active_params,
                 selected_strat_code
             )
             st.session_state['sim_runner'] = runner
             st.session_state['sim_prog_q'] = prog_q
             st.session_state['sim_res_q'] = res_q
             st.rerun()

        # Polling Loop for Simulation
        if st.session_state.get('sim_running', False):
             import queue
             
             # UI Containers
             st.caption("🚀 Running on Ray Cluster...")
             sim_progress_bar = st.progress(st.session_state.get('sim_progress', 0.0))
             sim_status_text = st.empty()
             sim_log_box = st.empty()
             
             # Read Queue (Batch)
             try:
                 for _ in range(20): # Read up to 20 msgs
                     try:
                         msg_type, msg_val = st.session_state['sim_prog_q'].get_nowait()
                         if msg_type == 'progress':
                             st.session_state['sim_progress'] = float(msg_val)
                             sim_progress_bar.progress(float(msg_val))
                         elif msg_type == 'log':
                             st.session_state['sim_logs'].append(msg_val)
                     except queue.Empty:
                         break
             except:
                 pass
                 
             # Update Log UI
             if st.session_state['sim_logs']:
                 sim_log_box.code("\n".join(st.session_state['sim_logs'][-15:]), language="text")
                 sim_status_text.text(f"Status: {st.session_state['sim_logs'][-1]}")
             
             # Check Result
             try:
                 status, data = st.session_state['sim_res_q'].get_nowait()
                 if status == 'success':
                     st.session_state['sim_running'] = False
                     st.session_state['sim_results'] = data
                     st.balloons()
                     st.success("Simulation Complete!")
                     st.rerun()
                 elif status == 'error':
                     st.session_state['sim_running'] = False
                     st.error(f"Error: {data}")
             except queue.Empty:
                 time.sleep(0.5)
                 st.rerun()

        # Results Display
        if st.session_state.get('sim_results'):
             res = st.session_state['sim_results']
             equity_df = pd.DataFrame(res['equity'])
             trades_df = pd.DataFrame(res['trades'])
             
             # Metrics
             if not trades_df.empty:
                    total_pnl = trades_df['pnl'].sum()
                    win_rate = len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total PnL", f"${total_pnl:,.2f}")
                    m2.metric("Total Trades", len(trades_df))
                    m3.metric("Win Rate", f"{win_rate:.1f}%")
                    
                    # Chart
                    st.subheader("Equity Curve")
                    st.line_chart(equity_df.set_index('timestamp')['equity'])
                    
                    # Trade List
                    with st.expander("Trade History"):
                        st.dataframe(trades_df)
             else:
                 st.info("No trades generated.")

# --- OPTIMIZER LOGIC ---
elif nav_mode == "⚙️ Optimizer":
    st.header("Parameter Optimization")
    st.markdown("Find the best strategy parameters by testing combinations.")

    st.warning("⚠️ **IMPORTANT**: Optimization runs in BLOCKING mode. The browser will appear frozen during execution, but it IS working. Check your terminal/console for live logs.")

    # --- DATA SOURCE SELECTOR ---
    import glob
    import pandas as pd
    
    col_head, col_refresh = st.columns([3, 1])
    with col_head:
        st.markdown("### 📊 Data Source")
    with col_refresh:
        if st.button("🔄 Refresh Files"):
            st.rerun()

    data_folder = "data"
    available_data_files = []
    
    # Gather candidates: data/*.csv AND *.csv (root)
    candidate_files = []
    if os.path.exists(data_folder):
        candidate_files.extend(glob.glob(os.path.join(data_folder, "*.csv")))
    
    # Also check root directory for misplaced files
    # (User might have pasted files in the project root)
    candidate_files.extend(glob.glob("*.csv"))
    
    # Deduplicate
    candidate_files = sorted(list(set(candidate_files)))

    for f in candidate_files:
            try:
                # Get file info without loading entire file
                fname = os.path.basename(f)
                fsize = os.path.getsize(f) / (1024 * 1024)  # MB
                
                # Count lines efficiently
                with open(f, 'rb') as fp:
                    line_count = sum(1 for _ in fp)
                candle_count = max(0, line_count - 1)  # Subtract header

                # Read first row for validation and start date
                df_head = pd.read_csv(f, nrows=1)
                
                # VALIDATION: If file is in root, be strict about columns to avoid reading results/junk
                is_in_data_dir = "data" in os.path.dirname(f)
                if not is_in_data_dir:
                    # Check for candle-like columns
                    cols_lower = [c.lower() for c in df_head.columns]
                    required = ['close'] # Minimal requirement
                    has_time = any(x in cols_lower for x in ['timestamp', 'time', 'date'])
                    
                    if not (has_time and 'close' in cols_lower):
                        # Skip this file, it's likely a report or config
                        continue

                # Read last row for end date using efficient skiprows
                # If file is small, just read it all. If large, skip to end.
                if candle_count > 0:
                    try:
                        # Skip all lines except header and last one
                        # But since we use header=None to read the specific line, we skip N lines
                        # where N = total_lines - 1 (skips everything before the last line)
                        rows_to_skip = line_count - 1
                        
                        df_tail = pd.read_csv(
                            f, 
                            skiprows=rows_to_skip, 
                            header=None, 
                            names=df_head.columns,
                            nrows=1
                        ) 
                        if df_tail.empty:
                             df_tail = df_head
                    except:
                        df_tail = df_head
                else:
                    df_tail = df_head

                # Try to extract date info
                col_candidates = ['timestamp', 'time', 'start', 'Date', 'date']
                date_col = None
                for col in col_candidates:
                    if col in df_head.columns:
                        date_col = col
                        break
                
                if date_col and not df_head.empty:
                    start_date = str(df_head[date_col].iloc[0])[:19]
                    end_date = str(df_tail[date_col].iloc[0])[:19] if not df_tail.empty and date_col in df_tail.columns else "Unknown"
                    date_info = f"{start_date} → {end_date}"
                else:
                    date_info = "Dates N/A"
                
                label = f"📁 {fname} | {candle_count:,} candles | {fsize:.1f}MB | {date_info}"
                available_data_files.append((label, f, fname, candle_count, date_info))
            except Exception as e:
                # print(f"Error reading {f}: {e}") # Debug
                # Only show errors for files in data dir, silence root file errors
                if "data" in f:
                     available_data_files.append((f"📁 {os.path.basename(f)} (Error reading)", f, os.path.basename(f), 0, "Error"))
    
    # Data source options
    data_source_options = ["🔴 Live Download (from Backtester)"]
    for item in available_data_files:
        data_source_options.append(item[0])
    
    selected_data_source = st.selectbox(
        "Select Historical Data",
        data_source_options,
        help="Choose between live downloaded data or saved historical files"
    )
    
    # Handle data source selection
    if selected_data_source == "🔴 Live Download (from Backtester)":
        if 'bt_data' in st.session_state and st.session_state['bt_data'] is not None:
            opt_data = st.session_state['bt_data']
            st.success(f"✅ Using live data: **{len(opt_data):,} candles** loaded from Backtester")
        else:
            opt_data = None
            st.info("💡 No live data available. Download data in the Backtester tab, or select a saved file above.")
    else:
        # Load from file
        selected_file_info = None
        for item in available_data_files:
            if item[0] == selected_data_source:
                selected_file_info = item
                break
        
        if selected_file_info:
            try:
                opt_data = pd.read_csv(selected_file_info[1])
                st.success(f"✅ Loaded: **{selected_file_info[2]}** | **{len(opt_data):,} candles** | {selected_file_info[4]}")
            except Exception as e:
                opt_data = None
                st.error(f"❌ Error loading file: {e}")
        else:
            opt_data = None
    
    st.divider()

    # --- CHECKPOINT RECOVERY SECTION ---
    st.markdown("### 📂 Checkpoints & Recovery")
    
    # Checkpoint helper functions (local scope or move to file level if needed)
    def decode_range_to_ui(r_list):
        """Convert a list range back to min, max, step."""
        if not r_list: return 0.0, 0.0, 0.0
        
        # Handle float/int differences
        is_float = isinstance(r_list[0], float)
        
        rmin = r_list[0]
        rmax = r_list[-1]
        
        if len(r_list) > 1:
            # Estimate step (round to avoid float errors)
            step = r_list[1] - r_list[0]
            if is_float:
                step = round(step, 2)
        else:
            step = 1.0 if is_float else 1
            
        return rmin, rmax, step

    import glob
    ckpt_files = glob.glob("optimization_checkpoints/checkpoint_*.json")
    
    if ckpt_files:
        # Sort by modification time (newest first)
        ckpt_files.sort(key=os.path.getmtime, reverse=True)
        
        ckpt_options = {}
        for f in ckpt_files:
            try:
                fname = os.path.basename(f)
                with open(f, 'r') as fp:
                    meta = json.load(fp)
                    
                ts = meta.get('last_updated', 'Unknown')
                otype = meta.get('optimizer_type', 'Unknown').upper()
                progress = ""
                if 'metadata' in meta:
                    if 'completed' in meta['metadata']:
                        progress = f"{meta['metadata']['completed']}/{meta['metadata']['total']} Tasks"
                    elif 'current_gen' in meta['metadata']:
                        progress = f"Gen {meta['metadata']['current_gen']}"
                
                label = f"[{ts}] {otype} | {progress} | {fname}"
                ckpt_options[label] = (f, meta)
            except:
                pass

        selected_ckpt_label = st.selectbox("Select Checkpoint", list(ckpt_options.keys()))
        
        if selected_ckpt_label:
            selected_path, selected_meta = ckpt_options[selected_ckpt_label]
            
            col_rec1, col_rec2, col_rec3 = st.columns(3)
            
            with col_rec1:
                if st.button("📥 Load Configuration", use_container_width=True):
                    # Restore parameters to session state keys
                    pr = selected_meta.get('param_ranges', {})
                    
                    # Resistance
                    if 'resistance_period' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['resistance_period'])
                       st.session_state['res_min'] = int(mi)
                       st.session_state['res_max'] = int(ma)
                       st.session_state['res_step'] = int(stp)
                    
                    # RSI
                    if 'rsi_period' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['rsi_period'])
                       st.session_state['rsi_min'] = int(mi)
                       st.session_state['rsi_max'] = int(ma)
                       st.session_state['rsi_step'] = int(stp)
                       
                    # SL
                    if 'sl_multiplier' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['sl_multiplier'])
                       st.session_state['sl_min'] = float(mi)
                       st.session_state['sl_max'] = float(ma)
                       st.session_state['sl_step'] = float(stp)
                       
                    # TP
                    if 'tp_multiplier' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['tp_multiplier'])
                       st.session_state['tp_min'] = float(mi)
                       st.session_state['tp_max'] = float(ma)
                       st.session_state['tp_step'] = float(stp)
                       
                    st.success("Configuration Loaded! Check ranges below.")
                    time.sleep(1)
                    st.rerun()

            with col_rec2:
                if st.button("🗑️ Delete Checkpoint", use_container_width=True):
                    try:
                        os.remove(selected_path)
                        st.success("Checkpoint Deleted!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col_rec3:
                st.info(f"File: {os.path.basename(selected_path)}")
            
            with st.expander("🔍 View Checkpoint Configuration Details"):
                st.json(selected_meta.get('param_ranges', {}))
        
        st.divider()

    else:
        st.info("No checkpoints found.")
        st.divider()

    col_o1, col_o2 = st.columns([1, 2])

    with col_o1:
        st.subheader("1. Strategy & Ranges") # Renamed

        # Strategy Selector
        strategy_options_opt = {
            "Bitcoin Spot Pro (BTC)": "BTC_SPOT",
            "Hybrid Strategy (Generic)": "HYBRID"
        }
        opt_strat_name = st.selectbox("Strategy to Optimize", list(strategy_options_opt.keys()), key="opt_strat_sel")
        opt_strat_code = strategy_options_opt[opt_strat_name]
        
        opt_product = st.text_input("Product ID", value="BTC-USD", key="opt_prod")
        st.divider()

        # Resistance Period

        # Resistance Period
        st.markdown("**Breakout Period (Candles)**")
        res_min = st.number_input("Min", 10, 100, 20, key="res_min")
        res_max = st.number_input("Max", 20, 200, 40, key="res_max")
        res_step = st.number_input("Step", 5, 50, 20, key="res_step")

        # RSI Period
        st.markdown("**RSI Period**")
        rsi_min = st.number_input("Min", 10, 20, 14, key="rsi_min")
        rsi_max = st.number_input("Max", 10, 30, 14, key="rsi_max")
        rsi_step = st.number_input("Step", 1, 5, 2, key="rsi_step")

        # SL Multiplier
        st.markdown("**SL Multiplier (ATR)**")
        sl_min = st.number_input("Min", 1.0, 3.0, 1.5, 0.1, key="sl_min")
        sl_max = st.number_input("Max", 1.0, 5.0, 1.5, 0.1, key="sl_max")
        sl_step = st.number_input("Step", 0.1, 1.0, 0.5, 0.1, key="sl_step")

        # TP Multiplier
        st.markdown("**TP Multiplier (ATR)**")
        tp_min = st.number_input("Min", 1.5, 5.0, 3.0, 0.1, key="tp_min")
        tp_max = st.number_input("Max", 2.0, 8.0, 3.0, 0.1, key="tp_max")
        tp_step = st.number_input("Step", 0.5, 2.0, 1.0, 0.1, key="tp_step")

        # Risk Level
        st.markdown("**Risk Levels to Test**")
        risk_options = st.multiselect("Select Levels", ["LOW", "MEDIUM", "HIGH"], default=["LOW"])

    with col_o2:
        st.subheader("2. Run Optimization")

        if opt_data is None:
            st.warning("⚠️ No data selected. Please select a data source above, or download data in the Backtester tab.")
        else:
            st.markdown("**Optimization Method**")
            opt_method = st.radio(
                "Select Algorithm",
                ["Grid Search (Exhaustive)", "Genetic Algorithm (Evolutionary)", "🧠 Bayesian (AI-Powered)"],
                label_visibility="collapsed"
            )
            
            # Execution Mode
            force_local = st.checkbox("💻 Force Local Mode (No Cluster)", value=True, help="Use only this computer's CPUs. Recommended if you are not connected to the Ray Cluster.")

            ga_gens, ga_pop, ga_mut = 5, 20, 0.1  # Defaults
            bayesian_trials = 50  # Default for Bayesian
            ga_auto_mode = False  # Initialize before conditional
            
            if opt_method == "🧠 Bayesian (AI-Powered)":
                st.info("🧠 **Bayesian Optimization (Optuna)**: Uses AI to learn from each evaluation and intelligently suggest better parameters. Most efficient for finding optimal settings.")
                
                # Bayesian specific settings
                col_bay1, col_bay2 = st.columns(2)
                bayesian_trials = col_bay1.number_input("Max Trials", 20, 500, 100, help="Number of parameter combinations to intelligently explore")
                bayesian_auto = col_bay2.checkbox("Auto-configure trials", value=True, help="Automatically set trials based on search space")
                
                if bayesian_auto:
                    # Will be calculated after param_ranges
                    ga_auto_mode = True
                    
            elif opt_method == "Genetic Algorithm (Evolutionary)":
                st.info("🧬 **Genetic Algorithm**: Evolves parameters over generations. Faster for large search spaces.")
                
                # Auto-calculate GA parameters based on search space (will be calculated after param_ranges)
                # Show toggle for auto vs manual
                auto_config = st.checkbox("🤖 Auto-configure GA (recommended)", value=True, help="Automatically set optimal Generations/Population based on search space size")
                
                if auto_config:
                    # Calculate later after param_ranges is built
                    ga_auto_mode = True
                else:
                    ga_auto_mode = False
                    col_ga1, col_ga2, col_ga3 = st.columns(3)
                    ga_gens = col_ga1.number_input("Generations", 1, 200, 10, help="Number of evolutionary cycles")
                    ga_pop = col_ga2.number_input("Population", 10, 1000, 30, help="Strategies per generation")
                    ga_mut = col_ga3.number_input("Mutation Rate", 0.01, 0.5, 0.1, 0.01, help="Chance of random gene change")
            else:
                st.info("🔍 **Grid Search**: Tests EVERY combination. Precise but slow for large ranges.")

            # Calculate total combinations
            def float_range(start, stop, step):
                r = []
                c = start
                while c <= stop:
                    r.append(round(c, 2))
                    c += step
                return r

            if not risk_options:
                risk_options = ["LOW"]

            param_ranges = {
                'resistance_period': list(range(int(res_min), int(res_max) + 1, int(res_step))),
                'rsi_period': list(range(int(rsi_min), int(rsi_max) + 1, int(rsi_step))),
                'sl_multiplier': float_range(sl_min, sl_max, sl_step),
                'tp_multiplier': float_range(tp_min, tp_max, tp_step),
                'risk_level': risk_options
            }

            # Use generic calculation to avoid strict dependency on structure
            import math
            total_combinations = (
                len(param_ranges['resistance_period']) *
                len(param_ranges['rsi_period']) *
                len(param_ranges['sl_multiplier']) *
                len(param_ranges['tp_multiplier']) *
                len(param_ranges['risk_level'])
            )

            st.info(f"📊 Total combinations to test: **{total_combinations}**")

            # Auto-configure GA parameters if enabled
            if opt_method == "Genetic Algorithm (Evolutionary)" and ga_auto_mode:
                # Formula: Population = min(100, max(20, sqrt(total_combinations)))
                # Generations = min(50, max(5, log2(total_combinations)))
                import math
                
                # Calculate raw values for transparency
                raw_pop = math.sqrt(total_combinations)
                raw_gens = math.log2(max(1, total_combinations))
                
                ga_pop = min(100, max(20, int(raw_pop)))
                ga_gens = min(50, max(5, int(raw_gens)))
                ga_mut = 0.1 if total_combinations < 1000 else 0.15  # Higher mutation for larger spaces
                
                st.success(f"🤖 Auto-configured: **{ga_gens} Generations** × **{ga_pop} Population** (Mutation: {ga_mut})")
                
                # Transparency expander
                with st.expander("📐 How was this calculated?"):
                    st.markdown(f"""
**Formulas Used:**
- **Population** = `min(100, max(20, √{total_combinations}))` = `min(100, max(20, {raw_pop:.2f}))` = **{ga_pop}**
- **Generations** = `min(50, max(5, log₂({total_combinations})))` = `min(50, max(5, {raw_gens:.2f}))` = **{ga_gens}**
- **Mutation Rate** = `{"0.10 (small search space < 1000)" if total_combinations < 1000 else "0.15 (large search space ≥ 1000)"}`

**Reasoning:**
- 📊 **Population size** scales with √N to sample the search space adequately
- 🔄 **Generations** scale with log₂(N) since evolutionary convergence is logarithmic
- 🎲 **Mutation rate** is higher for larger spaces to avoid local optima

**Data Source:**
- 📁 **File**: `{selected_data_source}`
- 📈 **Candles**: `{len(opt_data):,}` data points
""")
                    if hasattr(opt_data, 'columns'):
                        date_col = None
                        for col in ['timestamp', 'time', 'start', 'date']:
                            if col in opt_data.columns:
                                date_col = col
                                break
                        if date_col:
                            st.markdown(f"- 📅 **Range**: `{str(opt_data[date_col].iloc[0])[:19]}` → `{str(opt_data[date_col].iloc[-1])[:19]}`")

            # Auto-configure Bayesian trials if enabled
            if opt_method == "🧠 Bayesian (AI-Powered)" and ga_auto_mode:
                import math
                # Bayesian is more efficient, needs fewer trials than total combinations
                # Formula: sqrt(N) trials is enough for Bayesian to converge
                raw_trials = math.sqrt(total_combinations) * 2  # 2x sqrt for safety margin
                bayesian_trials = min(200, max(30, int(raw_trials)))
                
                st.success(f"🧠 Auto-configured: **{bayesian_trials} Trials** (Bayesian learns efficiently)")
                
                with st.expander("📐 How was this calculated?"):
                    st.markdown(f"""
**Formula Used:**
- **Trials** = `min(200, max(30, 2 × √{total_combinations}))` = `min(200, max(30, {raw_trials:.1f}))` = **{bayesian_trials}**

**Why fewer trials than GA/Grid?**
- 🧠 **Bayesian learns**: Each trial teaches the algorithm about the parameter space
- 📊 **TPE Sampler**: Uses probabilistic models to focus on promising regions
- ⚡ **Efficiency**: Typically finds optimal in √N trials vs N for Grid Search

**Data Source:**
- 📁 **File**: `{selected_data_source}`
- 📈 **Candles**: `{len(opt_data):,}` data points
""")

            if total_combinations > 100 and opt_method == "Grid Search (Exhaustive)":
                st.warning(f"⚠️ {total_combinations} combinations may take several minutes. Consider using Genetic Algorithm or Bayesian for faster results.")

            # Initialize session state for optimizer control
            if 'optimizer_runner' not in st.session_state:
                st.session_state['optimizer_runner'] = None
            if 'optimizer_running' not in st.session_state:
                st.session_state['optimizer_running'] = False
            if 'optimizer_logs' not in st.session_state:
                st.session_state['optimizer_logs'] = []
            if 'optimizer_progress' not in st.session_state:
                st.session_state['optimizer_progress'] = 0.0

            # Control buttons
            col_start, col_stop, col_kill = st.columns(3)

            with col_start:
                start_clicked = st.button("🚀 Start Optimization", type="primary", disabled=st.session_state['optimizer_running'])

            with col_stop:
                stop_clicked = st.button("🛑 Stop Optimization", disabled=not st.session_state['optimizer_running'])

            with col_kill:
                 kill_clicked = st.button("💀 Force Kill Ray (Panic)", help="Use ONLY if process is stuck. Kills all Ray processes.")

            # Handle stop button
            if stop_clicked and st.session_state['optimizer_runner']:
                st.session_state['optimizer_runner'].stop()
                st.session_state['optimizer_running'] = False
                st.warning("⚠️ Stopping optimization...")
                st.rerun()

            # Handle kill button
            if kill_clicked:
                 import subprocess
                 try:
                     st.warning("⚠️ Executing PURGE command...")
                     # Kill Raylet and Workers
                     subprocess.run(["pkill", "-f", "ray::"], check=False)
                     subprocess.run(["pkill", "-f", "raylet"], check=False)
                     
                     # Try ray stop
                     try:
                         # Try with venv ray first
                         subprocess.run([".venv/bin/ray", "stop", "--force"], check=False)
                     except:
                         pass
                         
                     subprocess.run(["ray", "stop", "--force"], check=False)
                     
                     if st.session_state['optimizer_runner']:
                         st.session_state['optimizer_runner'].cleanup()
                     st.session_state['optimizer_runner'] = None
                     st.session_state['optimizer_running'] = False
                     
                     st.success("✅ Ray Cluster has been PURGED. Wait 5s before restarting.")
                     time.sleep(2)
                     st.rerun()
                 except Exception as e:
                     st.error(f"Error purging: {e}")

            # Handle start button
            if start_clicked:
                from optimizer_runner import OptimizerRunner

                st.session_state['optimizer_logs'] = []
                st.session_state['optimizer_progress'] = 0.0
                st.session_state['optimizer_running'] = True

                # Create runner and start process
                runner = OptimizerRunner()

                # Determine method
                if opt_method == "Genetic Algorithm (Evolutionary)":
                    method = "genetic"
                    ga_params_tuple = (ga_gens, ga_pop, ga_mut)
                elif opt_method == "🧠 Bayesian (AI-Powered)":
                    method = "bayesian"
                    ga_params_tuple = (bayesian_trials, 0, 0)  # First param is n_trials
                else:
                    method = "grid"
                    ga_params_tuple = (10, 50, 0.1)  # Defaults (not used)

                # Start optimization in separate process
                try:
                    progress_queue, result_queue = runner.start(
                        opt_data,  # Use selected data source
                        param_ranges,
                        risk_options[0] if risk_options else "LOW",
                        opt_method=method,
                        ga_params=ga_params_tuple,
                        strategy_code=opt_strat_code,
                        force_local=force_local
                    )

                    st.session_state['optimizer_runner'] = runner
                    st.session_state['progress_queue'] = progress_queue
                    st.session_state['result_queue'] = result_queue

                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to start optimizer: {e}")
                    st.session_state['optimizer_running'] = False

            # Poll for updates if optimization is running
            if st.session_state['optimizer_running'] and st.session_state['optimizer_runner']:
                import queue

                # Create UI containers BEFORE the polling loop
                progress_container = st.empty()
                log_container = st.empty()
                status_container = st.empty()

                # Check if process is still alive
                if not st.session_state['optimizer_runner'].is_alive():
                    # Process died unexpectedly
                    try:
                        status, data = st.session_state['result_queue'].get_nowait()
                        # Handle result below
                    except queue.Empty:
                        st.error("❌ Optimizer process terminated unexpectedly")
                        st.session_state['optimizer_running'] = False
                        if st.session_state['optimizer_runner']:
                            st.session_state['optimizer_runner'].cleanup()
                        st.session_state['optimizer_runner'] = None

                # Read ALL available messages from progress queue (non-blocking)
                messages_read = 0
                max_reads_per_loop = 50  # Limit to prevent freezing UI thread

                try:
                    while messages_read < max_reads_per_loop:
                        try:
                            msg_type, msg_data = st.session_state['progress_queue'].get_nowait()
                            
                            if msg_type == "log":
                                st.session_state['optimizer_logs'].append(msg_data)
                            elif msg_type == "progress":
                                st.session_state['optimizer_progress'] = msg_data
                            
                            messages_read += 1
                        except queue.Empty:
                            break  # Queue is empty, exit inner loop
                    
                    # If we read many messages, sleep briefly to let the UI thread breathe
                    if messages_read > 20:
                        time.sleep(0.05)
                        
                except Exception as e:
                    pass

                # Check for final result
                try:
                    status, data = st.session_state['result_queue'].get_nowait()

                    if status == "success":
                        import pandas as pd
                        import os
                        # data is now a filepath
                        try:
                            results_df = pd.read_json(data, orient='records')
                            st.session_state['opt_results'] = results_df
                            
                            # Clean up temp file
                            try:
                                if os.path.exists(data):
                                    os.remove(data)
                            except:
                                pass
                                
                            st.session_state['optimizer_running'] = False
                            st.success("✅ Optimization Complete!")
                        except Exception as e:
                            # Fallback if it's a dict (legacy)
                            try:
                                results_df = pd.DataFrame(data)
                                st.session_state['opt_results'] = results_df
                                st.session_state['optimizer_running'] = False
                                st.success("✅ Optimization Complete!")
                            except:
                                st.error(f"Failed to load results: {e}")
                                st.session_state['optimizer_running'] = False
                    elif status == "error":
                        st.error(f"❌ Optimization failed: {data}")
                        st.session_state['optimizer_running'] = False
                    elif status == "stopped":
                        st.warning("⚠️ Optimization stopped by user")
                        st.session_state['optimizer_running'] = False

                    # Cleanup
                    if st.session_state['optimizer_runner']:
                        st.session_state['optimizer_runner'].cleanup()
                    st.session_state['optimizer_runner'] = None
                    st.rerun()

                except queue.Empty:
                    pass

                # Update UI with current state
                if st.session_state['optimizer_logs']:
                    # Show last 100 lines of logs
                    recent_logs = st.session_state['optimizer_logs'][-100:]
                    log_container.text_area(
                        "📋 Live Logs",
                        value="\n".join(recent_logs),
                        height=400,
                        disabled=True
                    )

                # Show progress bar
                if st.session_state['optimizer_progress'] > 0:
                    progress_container.progress(
                        st.session_state['optimizer_progress'],
                        text=f"Progress: {int(st.session_state['optimizer_progress'] * 100)}%"
                    )
                else:
                    progress_container.info("🔄 Initializing optimization...")

                # Show running status
                status_container.info(f"⚙️ Optimization running... (Read {messages_read} updates)")

                # Auto-refresh with delay to prevent UI freezing
                time.sleep(0.5)
                st.rerun()

        # Display Results (if they exist)
        if 'opt_results' in st.session_state:
            df_res = st.session_state['opt_results']

            if not df_res.empty:
                st.markdown("---")
                st.subheader("📊 Top Results")
                st.dataframe(df_res.head(10), use_container_width=True)

                # Show execution log in expander
                if 'opt_logs' in st.session_state:
                    with st.expander("📜 View Execution Log", expanded=False):
                        st.text_area(
                            "Complete Log",
                            value="\n".join(st.session_state['opt_logs']),
                            height=300,
                            disabled=True,
                            label_visibility="collapsed"
                        )

                st.markdown("---")
                st.subheader("🎯 Select & Apply Configuration")

                # Selection
                df_res = df_res.reset_index(drop=True)
                options = []
                for idx, row in df_res.iterrows():
                    pnl = row.get('Total PnL', 0.0)
                    trades = row.get('Total Trades', 0)
                    wr = row.get('Win Rate %', 0.0)
                    try:
                         trades = int(trades)
                    except:
                         trades = 0
                         
                    label = f"Rank #{idx+1} | PnL: ${pnl:.2f} | Trades: {trades} | WR: {wr:.1f}%"
                    options.append(label)

                selected_option = st.selectbox("Choose Configuration", options)

                col_apply, col_save, col_clear = st.columns(3)

                with col_apply:
                    if st.button("✅ Apply to Backtester", use_container_width=True):
                        idx = options.index(selected_option)
                        selected_row = df_res.iloc[idx]
                        metric_keys = ['Total Trades', 'Win Rate %', 'Total PnL', 'Final Balance']
                        best_params = {k: v for k, v in selected_row.to_dict().items() if k not in metric_keys}
                        st.session_state['active_strategy_params'] = best_params
                        st.success(f"✅ Applied Configuration #{idx+1}! Go to Backtester tab to verify.")

                with col_save:
                    idx = options.index(selected_option)
                    row_dict = df_res.iloc[idx].to_dict()
                    json_str = json.dumps(row_dict, indent=2)
                    st.download_button(
                        label="💾 Download JSON",
                        data=json_str,
                        file_name=f"opt_config_rank_{idx+1}.json",
                        mime="application/json",
                        use_container_width=True
                    )

                with col_clear:
                    if st.button("🗑️ Clear Results", use_container_width=True):
                        if 'opt_results' in st.session_state:
                            del st.session_state['opt_results']
                        if 'opt_logs' in st.session_state:
                            del st.session_state['opt_logs']
                        st.rerun()


# --- STRATEGY MINER LOGIC ---
elif nav_mode == "⛏️ Strategy Miner (AI)":
    st.header("⛏️ AI Strategy Miner (Genetic Programming)")
    st.markdown("Use **Genetic Algorithms** to automatically discover, evolve, and optimize profitable trading strategies from raw ingredients.")

    # --- DATA SELECTION ---
    import glob
    import pandas as pd
    
    # --- ENHANCED DATA SELECTOR (Replicated from Optimizer) ---
    col_head, col_refresh = st.columns([3, 1])
    with col_head:
        st.markdown("### 📊 Data Source")
    with col_refresh:
        if st.button("🔄 Refresh Files", key="miner_refresh"):
            st.rerun()

    data_folder = "data"
    available_data_files = []
    import glob
    import os
    
    # Gather candidates: data/*.csv AND *.csv (root)
    candidate_files = []
    if os.path.exists(data_folder):
        candidate_files.extend(glob.glob(os.path.join(data_folder, "*.csv")))
    candidate_files.extend(glob.glob("*.csv"))
    candidate_files = sorted(list(set(candidate_files)))

    for f in candidate_files:
            try:
                fname = os.path.basename(f)
                fsize = os.path.getsize(f) / (1024 * 1024) 
                
                with open(f, 'rb') as fp:
                    line_count = sum(1 for _ in fp)
                candle_count = max(0, line_count - 1)

                df_head = pd.read_csv(f, nrows=1)
                
                is_in_data_dir = "data" in os.path.dirname(f)
                if not is_in_data_dir:
                    cols_lower = [c.lower() for c in df_head.columns]
                    has_time = any(x in cols_lower for x in ['timestamp', 'time', 'date'])
                    if not (has_time and 'close' in cols_lower):
                        continue

                # Read last row
                if candle_count > 0:
                    try:
                        rows_to_skip = line_count - 1
                        df_tail = pd.read_csv(f, skiprows=rows_to_skip, header=None, names=df_head.columns, nrows=1) 
                        if df_tail.empty: df_tail = df_head
                    except:
                        df_tail = df_head
                else:
                    df_tail = df_head

                col_candidates = ['timestamp', 'time', 'start', 'Date', 'date']
                date_col = None
                for col in col_candidates:
                    if col in df_head.columns:
                        date_col = col
                        break
                
                if date_col and not df_head.empty:
                    start_date = str(df_head[date_col].iloc[0])[:19]
                    end_date = str(df_tail[date_col].iloc[0])[:19] if not df_tail.empty and date_col in df_tail.columns else "Unknown"
                    date_info = f"{start_date} → {end_date}"
                else:
                    date_info = "Dates N/A"
                
                label = f"📁 {fname} | {candle_count:,} candles | {fsize:.1f}MB | {date_info}"
                available_data_files.append((label, f, fname, candle_count, date_info))
            except Exception as e:
                # print(f"Error reading {f}: {e}")
                if "data" in f:
                     available_data_files.append((f"📁 {os.path.basename(f)} (Error reading)", f, os.path.basename(f), 0, "Error"))
    
    data_source_options = []
    # Priority for CSVs (Miner prefers data files)
    for item in available_data_files:
        data_source_options.append(item[0])
    
    live_option_label = "🔴 Live Download (From Coinbase)"
    data_source_options.append(live_option_label)
    
    selected_data_source = st.selectbox("Select Historical Data", data_source_options, key="miner_data_select")
    
    miner_data = None
    
    # Check if a file is selected
    selected_file_path = None
    for label, path, _, _, _ in available_data_files:
        if label == selected_data_source:
             selected_file_path = path
             break

    if selected_file_path:
        try:
            miner_data = pd.read_csv(selected_file_path)
            st.success(f"✅ Loaded {len(miner_data)} candles from **{os.path.basename(selected_file_path)}**")
        except Exception as e:
             st.error(f"Error loading CSV: {e}")
    
    elif selected_data_source == live_option_label:
        st.info("Fetching recent data from Coinbase...")
        try:
            import time
            end_ts = int(time.time())
            start_ts = end_ts - (1000 * 3600) # 1000 hours back
            miner_data = broker_client.get_historical_data("BTC-USD", granularity="ONE_HOUR", start_ts=start_ts, end_ts=end_ts) 
            
            if miner_data is not None and not miner_data.empty:
                st.success(f"Loaded {len(miner_data)} candles (Live).")
            else:
                 st.warning("No data returned. Check API Keys or connectivity.")
        except Exception as e:
            st.error(f"Error downloading data: {e}")

    st.divider()

    col_config, col_monitor = st.columns([1, 2])

    with col_config:
        st.subheader("🧬 Experiment Settings")
        
        pop_size = st.number_input("Population Size", min_value=10, max_value=500, value=100, step=10, help="Number of strategies in each generation.")
        generations = st.number_input("Generations", min_value=1, max_value=200, value=20, step=1, help="How many evolutionary cycles to run.")
        risk_level = st.selectbox("Risk Level", ["LOW", "MEDIUM", "HIGH"], index=0)
        
        force_local = st.checkbox("Force Local Mode (No Ray)", value=False, help="Run on this machine instead of cluster (Simpler debugging).")

        st.divider()
        
        # Initialize session state for miner
        if 'miner_runner' not in st.session_state:
            st.session_state['miner_runner'] = None
        if 'miner_running' not in st.session_state:
            st.session_state['miner_running'] = False
        if 'miner_logs' not in st.session_state:
            st.session_state['miner_logs'] = []
            
        start_miner = st.button("⛏️ Start Mining", type="primary", disabled=st.session_state['miner_running'])
        stop_miner = st.button("🛑 Stop Mining", disabled=not st.session_state['miner_running'])

        if stop_miner and st.session_state['miner_runner']:
            st.session_state['miner_runner'].stop()
            st.session_state['miner_running'] = False
            st.warning("Stopping miner...")
            st.rerun()

        if start_miner and miner_data is not None:
             from optimizer_runner import OptimizerRunner
             st.session_state['miner_logs'] = []
             st.session_state['miner_running'] = True
             
             runner = OptimizerRunner()
             
             # We piggyback on optimizer_runner with Type="miner"
             # ga_params = (Generations, Population, MutationRate)
             # But runner signature is fixed. We pass gens/pop via ga_params
             
             try:
                 progress_queue, result_queue = runner.start(
                     miner_data,
                     {}, # param_ranges (Empty for miner)
                     risk_level,
                     opt_method="miner",
                     ga_params=(generations, pop_size, 0.1),
                     strategy_code="DYNAMIC",
                     force_local=force_local
                 )
                 
                 st.session_state['miner_runner'] = runner
                 st.session_state['miner_queue'] = progress_queue
                 st.session_state['miner_res_queue'] = result_queue
                 st.rerun()
             except Exception as e:
                 st.error(f"Failed to start miner: {e}")
                 st.session_state['miner_running'] = False

    with col_monitor:
        st.subheader("🖥️ Live Evolution")
        
        log_area = st.empty()
        
        st.caption("Generation Progress")
        progress_bar = st.progress(0.0)
        
        chart_area = st.empty()
        
        # Monitor Loop
        if st.session_state['miner_running'] and st.session_state['miner_runner']:
            import queue
            
            # Read Logs
            try:
                while True:
                    msg_type, msg_data = st.session_state['miner_queue'].get_nowait()
                    if msg_type == "log":
                        st.session_state['miner_logs'].append(msg_data)
                    elif msg_type == "progress":
                        # Miner sends ("BEST_GEN", data) or ("START_GEN", n) via prog_cb wrapper
                        # optimizer_runner passes this tuple as 'msg_data'
                        if isinstance(msg_data, tuple) and len(msg_data) == 2:
                            subtype, subdata = msg_data
                            if subtype == "START_GEN":
                                st.session_state['miner_logs'].append(f"🧬 Starting Generation {subdata}...")
                            elif subtype == "BEST_GEN":
                                gen = subdata.get('gen')
                                pnl = subdata.get('pnl')
                                st.session_state['miner_logs'].append(f"🌟 Gen {gen} Best PnL: ${pnl:.2f}")
                                st.session_state['miner_logs'].append(f"🌟 Gen {gen} Best PnL: ${pnl:.2f}")
                                # Reset progress bar for next gen
                                progress_bar.progress(0.0)
                            elif subtype == "BATCH_PROGRESS":
                                # Update progress bar
                                progress_bar.progress(float(subdata))
                        else:
                             # Standard float progress (fallback)
                             pass
                        
            except queue.Empty:
                pass
            
            # Display Logs
            log_text = "\n".join(st.session_state['miner_logs'][-20:])
            log_area.code(log_text if log_text else "Waiting for logs...", language="text")
            
            # Check for Result
            try:
                status, payload = st.session_state['miner_res_queue'].get_nowait()
                if status == "success":
                    st.success("🎉 Mining Complete!")
                    st.session_state['miner_running'] = False
                    
                    # Load result file
                    res_df = pd.read_json(payload)
                    st.session_state['last_miner_result'] = res_df
                    st.rerun()
                    
                elif status == "error":
                    st.error(f"Mining Failed: {payload}")
                    st.session_state['miner_running'] = False
            except queue.Empty:
                pass
            
            time.sleep(1)
            st.rerun()

    # Display Results if available
    if 'last_miner_result' in st.session_state:
        res = st.session_state['last_miner_result']
        st.divider()
        st.subheader("🏆 Discovery Result")
        st.dataframe(res)
        
        # Extract Best Genome
        if not res.empty:
            params = res.iloc[0]['params']
            metrics = res.iloc[0]['metrics']
            
            st.markdown(f"**Best Metrics:** {metrics}")
            st.json(params)
            
            if st.button("💾 Apply this Strategy"):
                st.session_state['active_strategy_params'] = params 
                # Note: We need to tell Backtester to use DynamicStrategy + This Genome
                # This might require an extra flag in Backtester tab selectbox
                st.success("Strategy Saved to Session! (Go to Backtester -> Select 'Dynamic')")
