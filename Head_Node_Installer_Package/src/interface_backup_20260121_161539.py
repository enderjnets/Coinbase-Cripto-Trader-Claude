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


with tab_opt:
    st.header("Parameter Optimization (Grid Search)")
    st.markdown("Find the best strategy parameters by testing combinations.")
    
    col_o1, col_o2 = st.columns([1, 2])
    
    with col_o1:
        st.subheader("1. Ranges")
        
        # Resistance Period (Breakout Lookback)
        st.markdown("**Breakout Period (Candles)**")
        res_min = st.number_input("Min", 10, 100, 20, key="res_min")
        res_max = st.number_input("Max", 20, 200, 60, key="res_max")
        res_step = st.number_input("Step", 5, 50, 10, key="res_step")

        # RSI Period Range
        st.markdown("**RSI Period**")
        rsi_min = st.number_input("Min", 10, 20, 10, key="rsi_min")
        rsi_max = st.number_input("Max", 10, 30, 20, key="rsi_max")
        rsi_step = st.number_input("Step", 1, 5, 2, key="rsi_step")
        
        # SL Multiplier Range
        st.markdown("**SL Multiplier (ATR)**")
        sl_min = st.number_input("Min", 1.0, 3.0, 1.0, 0.1, key="sl_min")
        sl_max = st.number_input("Max", 1.0, 5.0, 2.0, 0.1, key="sl_max")
        sl_step = st.number_input("Step", 0.1, 1.0, 0.5, 0.1, key="sl_step")
        
        # TP Multiplier Range
        st.markdown("**TP Multiplier (ATR)**")
        tp_min = st.number_input("Min", 1.5, 5.0, 2.0, 0.1, key="tp_min")
        tp_max = st.number_input("Max", 2.0, 8.0, 4.0, 0.1, key="tp_max")
        tp_step = st.number_input("Step", 0.5, 2.0, 1.0, 0.1, key="tp_step")
        
        # Risk Level
        st.markdown("**Risk Levels to Test**")
        risk_options = st.multiselect("Select Levels", ["LOW", "MEDIUM", "HIGH"], default=["LOW", "HIGH"])
        
    with col_o2:
        st.subheader("2. Run Optimization")
        
        if 'bt_data' not in st.session_state:
            st.warning("Please download data in the **Backtester** tab first.")
        else:
            # Session State for Async Optimization
            import queue
            if 'opt_running' not in st.session_state:
                st.session_state.opt_running = False
            if 'opt_thread' not in st.session_state:
                st.session_state.opt_thread = None
            if 'opt_stop_event' not in st.session_state:
                st.session_state.opt_stop_event = threading.Event()
            if 'opt_progress_val' not in st.session_state:
                st.session_state.opt_progress_val = 0.0
            if 'opt_logs' not in st.session_state:
                st.session_state.opt_logs = []
            if 'opt_log_queue' not in st.session_state:
                st.session_state.opt_log_queue = queue.Queue()
            
            # Optimization Method Selection
            st.markdown("---")
            st.markdown("**Optimization Method**")
            opt_method = st.radio("Select Algorithm", ["Grid Search (Exhaustive)", "Genetic Algorithm (Evolutionary)"], label_visibility="collapsed")
            
            ga_gens, ga_pop, ga_mut = 10, 50, 0.1
            if opt_method == "Genetic Algorithm (Evolutionary)":
                st.info("🧬 **Genetic Algorithm**: Evolves parameters over generations. Faster for large search spaces.")
                col_ga1, col_ga2, col_ga3 = st.columns(3)
                ga_gens = col_ga1.number_input("Generations", min_value=1, max_value=200, value=10, help="Number of evolutionary cycles")
                ga_pop = col_ga2.number_input("Population", min_value=10, max_value=1000, value=50, help="Strategies per generation")
                ga_mut = col_ga3.number_input("Mutation Rate", min_value=0.01, max_value=0.5, value=0.1, step=0.01, help="Chance of random gene change")
            else:
                st.info("🔍 **Grid Search**: Tests EVERY combination. Precise but slow for large ranges.")

            # Start Button
            if not st.session_state.opt_running:
                if st.button("Start Optimization"):
                    st.session_state.opt_running = True
                    st.session_state.opt_stop_event.clear()
                    st.session_state.opt_progress_val = 0.0
                    st.session_state.opt_logs = [] # Clear previous logs
                    
                    # Drain queue just in case
                    while not st.session_state.opt_log_queue.empty():
                        st.session_state.opt_log_queue.get()
                    
                    if 'opt_results' in st.session_state:
                        del st.session_state['opt_results']

                    # Range Logic inside click
                    def float_range(start, stop, step):
                        r = []
                        c = start
                        while c <= stop:
                            r.append(round(c, 2))
                            c += step
                        return r

                    if not risk_options: risk_options = ["LOW"]
                    
                    param_ranges = {
                        'resistance_period': list(range(int(res_min), int(res_max) + 1, int(res_step))),
                        'rsi_period': list(range(int(rsi_min), int(rsi_max) + 1, int(rsi_step))),
                        'sl_multiplier': float_range(sl_min, sl_max, sl_step),
                        'tp_multiplier': float_range(tp_min, tp_max, tp_step),
                        'risk_level': risk_options
                    }
                    
                    st.write("Testing Grid:", param_ranges)
                    
                    # Thread Target
                    # We pass the queue explicitly to avoid closure issues if possible, 
                    # but closure is fine here.
                    log_q = st.session_state.opt_log_queue
                    stop_ev = st.session_state.opt_stop_event
                    
                    def run_opt_async(q, stop_event, data, params, risk, method, ga_params):
                        # print("DEBUG: Thread run_opt_async STARTED")

                        def progress_wrapper(p):
                            q.put(f"__PROGRESS__{p}")

                        def log_wrapper(msg):
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            q.put(f"[{timestamp}] {msg}")

                        log_wrapper("Thread started. Preparing optimizer...")

                        try:
                            # CREATE optimizer INSIDE thread to avoid threading issues
                            if method == "Genetic Algorithm (Evolutionary)":
                                from optimizer import GeneticOptimizer
                                optimizer = GeneticOptimizer(
                                    population_size=ga_params['pop'],
                                    generations=ga_params['gens'],
                                    mutation_rate=ga_params['mut']
                                )
                                log_wrapper(f"Using Genetic Algorithm (pop={ga_params['pop']}, gens={ga_params['gens']})")
                            else:
                                from optimizer import GridOptimizer
                                optimizer = GridOptimizer()
                                log_wrapper("Using Grid Search")

                            res = optimizer.optimize(
                                data,
                                params,
                                risk_level=risk,
                                progress_callback=progress_wrapper,
                                cancel_event=stop_event,
                                log_callback=log_wrapper
                            )
                            # Result needs to be stored. 
                            # We can't return it. We can't write to session state safely.
                            # We will store it in a global or file? 
                            # Or we push a "DONE" event with the result.
                            # Since dataframe is complex, let's try writing to session_state 
                            # (it's the completion that fails often).
                            # Better pattern: Use a mutable container passed in.
                            # Send result via queue safely
                            q.put(("__RESULT__", res))
                        except Exception as e:
                            log_wrapper(f"THREAD EXCEPTION: {e}")
                            print(f"Optimization Thread Error: {e}")
                        finally:
                            # We signal done via queue
                            q.put("__DONE__")

                    # Launch
                    t = threading.Thread(target=run_opt_async, args=(
                        log_q,
                        stop_ev,
                        st.session_state['bt_data'],
                        param_ranges,
                        bot_instance.risk_level,
                        opt_method,  # Pass method
                        {'pop': ga_pop, 'gens': ga_gens, 'mut': ga_mut}  # Pass GA params
                    ), daemon=True)  # Make it daemon so it dies when main thread exits
                    st.session_state.opt_thread = t
                    try:
                        t.start()
                        # Give thread a moment to start and potentially fail
                        time.sleep(0.5)
                        if not t.is_alive():
                            st.error("❌ Thread failed to start - check console for errors")
                            st.session_state.opt_running = False
                            st.stop()
                    except Exception as e:
                        st.error(f"❌ Failed to start optimization thread: {e}")
                        st.session_state.opt_running = False
                        st.stop()
                    st.rerun()

            else:
                # RUNNING STATE UI
                thread = st.session_state.get('opt_thread')

                # Poll Queue FIRST to capture any final logs
                try:
                    while True:
                        msg = st.session_state.opt_log_queue.get_nowait()
                        if isinstance(msg, tuple) and msg[0] == "__RESULT__":
                            # Capture result
                            st.session_state['opt_temp_result'] = msg[1]
                        elif isinstance(msg, str) and msg.startswith("__PROGRESS__"):
                            val = float(msg.replace("__PROGRESS__", ""))
                            st.session_state.opt_progress_val = val
                        elif msg == "__DONE__":
                            st.session_state.opt_running = False
                            # Move result
                            if 'opt_temp_result' in st.session_state:
                                st.session_state['opt_results'] = st.session_state['opt_temp_result']
                                del st.session_state['opt_temp_result']
                            # Don't rerun immediately - let it finish this render
                            break
                        else:
                            st.session_state.opt_logs.append(msg)
                except queue.Empty:
                    pass

                # UI RENDER - Create stable containers
                st.info("🚀 Optimization Running in Background...")

                # Progress Bar
                progress_container = st.container()
                with progress_container:
                    st.progress(st.session_state.opt_progress_val)
                    st.text(f"Progress: {int(st.session_state.opt_progress_val * 100)}%")

                # Stop Button
                if st.button("🛑 STOP OPTIMIZATION"):
                    st.session_state.opt_stop_event.set()
                    st.warning("Stopping... please wait.")

                # Live Logs Container - ALWAYS VISIBLE
                logs_container = st.container()
                with logs_container:
                    st.markdown("### 📝 Process Logs")

                    # Create a scrollable text area for logs
                    log_box = st.empty()

                    if st.session_state.opt_logs:
                        # Join all logs and display
                        log_text = "\n".join(st.session_state.opt_logs[-50:])  # Last 50 logs
                        log_box.text_area(
                            "Live Output",
                            value=log_text,
                            height=400,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    else:
                        log_box.info("⏳ Initializing optimizer... (logs will appear here)")

                # Check thread health AFTER rendering
                if thread and not thread.is_alive():
                    # Only show error if we didn't finish cleanly
                    if st.session_state.opt_running:
                        st.error("❌ Optimization thread died unexpectedly. Check logs above.")
                        st.session_state.opt_running = False

                # Only rerun if still running
                if st.session_state.opt_running:
                    # Slower refresh to give browser time to render
                    time.sleep(2.0)
                    st.rerun()

            # Completion Check (if just finished)
            if 'opt_results' in st.session_state and not st.session_state.opt_running:
                 st.success("✅ Optimization Complete!")

                 # Show full execution log
                 if st.session_state.opt_logs:
                     with st.expander("📜 View Full Execution Log", expanded=False):
                         log_text = "\n".join(st.session_state.opt_logs)
                         st.text_area(
                             "Complete Log",
                             value=log_text,
                             height=300,
                             disabled=True,
                             label_visibility="collapsed"
                         )
        
        # Display Results & Selection
        if 'opt_results' in st.session_state:
            df_res = st.session_state['opt_results']
            st.subheader("Top Results")
            st.dataframe(df_res.head(10))
            
            # Scatter Plot (Trades vs PnL)
            if not df_res.empty:
                st.scatter_chart(df_res, x='Total Trades', y='Total PnL', color='Win Rate %')
                
            st.markdown("---")
            st.subheader("🎯 Select & Apply Configuration")
            
            # Create a selection list from the dataframe
            # Format: "Rank #1 | PnL: $X | Params..."
            if not df_res.empty:
                # Add an index column for rank
                df_res = df_res.reset_index(drop=True)
                
                options = []
                for idx, row in df_res.iterrows():
                    # Create a readable label
                    label = f"Rank #{idx+1} | PnL: ${row['Total PnL']} | Trades: {row['Total Trades']} | WR: {row['Win Rate %']}%"
                    options.append(label)
                    
                selected_option = st.selectbox("Choose Configuration to Apply", options)
                
                if st.button("Apply to Backtester"):
                    # Parse selection
                    idx = options.index(selected_option)
                    selected_row = df_res.iloc[idx]
                    
                    # Extract params (exclude metrics)
                    # We know the metric keys (Total Trades, etc.)
                    metric_keys = ['Total Trades', 'Win Rate %', 'Total PnL', 'Final Balance']
                    best_params = {k: v for k, v in selected_row.to_dict().items() if k not in metric_keys}
                    
                    st.session_state['active_strategy_params'] = best_params
                    st.success(f"✅ Applied Configuration #{idx+1}! Go to **Backtester** tab to verify.")
                    
                # Save to JSON
                if st.button("💾 Save to JSON"):
                    idx = options.index(selected_option)
                    row_dict = df_res.iloc[idx].to_dict()
                    json_str = json.dumps(row_dict, indent=2)
                    st.download_button(
                        label="Download Config JSON", 
                        data=json_str,
                        file_name=f"opt_config_rank_{idx+1}.json",
                        mime="application/json"
                    )
