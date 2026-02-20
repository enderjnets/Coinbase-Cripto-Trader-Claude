import streamlit as st
import asyncio
import pandas as pd
import threading
from trading_bot import bot_instance
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
        
        if is_stocks:
            bt_product = st.text_input("Ticker Symbol", value="NVDA").upper()
        else:
            # Dropdown for Product ID (Crypto)
            available_products = load_products()
            default_idx = 0
            if "BTC-USD" in available_products:
                default_idx = available_products.index("BTC-USD")
            bt_product = st.selectbox("Product ID", available_products, index=default_idx)
            
        bt_granularity = st.selectbox("Timeframe", ["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"], index=3)
        
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


with tab_opt:
    st.header("Parameter Optimization")
    st.markdown("Find the best strategy parameters by testing combinations.")

    st.warning("⚠️ **IMPORTANT**: Optimization runs in BLOCKING mode. The browser will appear frozen during execution, but it IS working. Check your terminal/console for live logs.")

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
        st.subheader("1. Ranges")

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

        if 'bt_data' not in st.session_state:
            st.warning("Please download data in the **Backtester** tab first.")
        else:
            # Method Selection
            st.markdown("**Optimization Method**")
            opt_method = st.radio(
                "Select Algorithm",
                ["Grid Search (Exhaustive)", "Genetic Algorithm (Evolutionary)"],
                label_visibility="collapsed"
            )

            ga_gens, ga_pop, ga_mut = 5, 20, 0.1  # Defaults
            if opt_method == "Genetic Algorithm (Evolutionary)":
                st.info("🧬 **Genetic Algorithm**: Evolves parameters over generations. Faster for large search spaces.")
                col_ga1, col_ga2, col_ga3 = st.columns(3)
                ga_gens = col_ga1.number_input("Generations", 1, 200, 5, help="Number of evolutionary cycles")
                ga_pop = col_ga2.number_input("Population", 10, 1000, 20, help="Strategies per generation")
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

            if total_combinations > 100:
                st.warning(f"⚠️ {total_combinations} combinations may take several minutes. Consider using Genetic Algorithm or reducing the ranges.")

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
            col_start, col_stop = st.columns(2)

            with col_start:
                start_clicked = st.button("🚀 Start Optimization", type="primary", disabled=st.session_state['optimizer_running'])

            with col_stop:
                stop_clicked = st.button("🛑 Stop Optimization", disabled=not st.session_state['optimizer_running'])

            # Handle stop button
            if stop_clicked and st.session_state['optimizer_runner']:
                st.session_state['optimizer_runner'].stop()
                st.session_state['optimizer_running'] = False
                st.warning("⚠️ Stopping optimization...")
                st.rerun()

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
                else:
                    method = "grid"
                    ga_params_tuple = (10, 50, 0.1)  # Defaults (not used)

                # Start optimization in separate process
                try:
                    progress_queue, result_queue = runner.start(
                        st.session_state['bt_data'],
                        param_ranges,
                        risk_options[0] if risk_options else "LOW",
                        opt_method=method,
                        ga_params=ga_params_tuple
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

                # Scatter Plot (Disabled to prevent potential SIGSEGV on some systems)
                # if len(df_res) > 1:
                #     st.scatter_chart(df_res, x='Total Trades', y='Total PnL', color='Win Rate %')

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
                    label = f"Rank #{idx+1} | PnL: ${row['Total PnL']:.2f} | Trades: {int(row['Total Trades'])} | WR: {row['Win Rate %']:.1f}%"
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
