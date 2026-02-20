import pandas as pd
import time
from datetime import datetime, timedelta
from config import Config
from config import Config
from strategy import Strategy
# Scanner is no longer directly used, DataManager uses BrokerClient

class Backtester:
    def __init__(self, broker_client=None):
        self.strategy = Strategy()
        self.results = {}
        self.broker = broker_client
        
        # Lazy load broker only when needed to avoid overhead/hangs on Ray Workers
        # if not self.broker: ... removed from here
        
    def download_data(self, product_id, start_date, end_date, granularity_str, progress_callback=None):
        """
        Uses DataManager to smartly download only missing data and return the full range.
        Uses the internal self.broker to fetch data.
        """
        from data_manager import DataManager
        dm = DataManager()
        
        # LAZY INIT BROKER
        if not self.broker:
            try:
                from coinbase_client import CoinbaseClient
                self.broker = CoinbaseClient()
            except Exception as e:
                print(f"Failed to auto-init broker: {e}")
                
        print(f"Requesting data for {product_id} from {start_date} to {end_date}...")
        
        try:
            # Pass self.broker instead of scanner
            df = dm.smart_download(self.broker, product_id, start_date, end_date, granularity_str, progress_callback)
            if df is not None:
                print(f"Data ready. Total candles: {len(df)}")
            return df
        except Exception as e:
            print(f"Backtester Download Error: {e}")
            return None

    def run_backtest(self, df, risk_level="LOW", initial_balance=10000, strategy_params=None, progress_callback=None, strategy_cls=None):
        """
        Simulates the strategy on the historical DataFrame.
        Assume Spot Trading (Long Only) + Fees.
        strategy_params: dict of custom strategy parameters

        NEW: Supports cash_mode for exit-to-cash in bearish markets
        """
        # Create new strategy instance
        if strategy_cls:
             # If using a specific class (e.g. BitcoinSpotStrategy), instantiate it
             # It might require 'broker_client', pass None for backtest
             try:
                 self.strategy = strategy_cls(None)
             except TypeError:
                 self.strategy = strategy_cls() # Fallback
                 
             if strategy_params and hasattr(self.strategy, 'params'):
                 self.strategy.params.update(strategy_params)
        elif strategy_params:
            self.strategy = Strategy(strategy_params=strategy_params)
        else:
            self.strategy = Strategy()

        p = strategy_params if strategy_params else {}

        # Override risk_level if in params (for optimization)
        if p and 'risk_level' in p:
            risk_level = p['risk_level']

        balance = initial_balance
        equity_curve = []
        trades = []
        active_position = None # {entry_price, size, time, sl, tp}
        cash_mode = False  # Track if we're in "exit to cash" mode

        # Fee Config
        # CRITICAL: Use MAKER fees (0.40%), not TAKER (0.60%)
        # New strategies use limit orders with post_only=True
        fee_rate = getattr(Config, 'TRADING_FEE_MAKER', 0.4) / 100.0
        
        # --- DATA NORMALIZATION ---
        # Ensure 'timestamp' column exists and is datetime
        df = df.copy() # Avoid SettingWithCopy warning
        
        if 'timestamp' not in df.columns:
            # Try to restore from index if it's datetime
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.reset_index()
                # If unnamed, rename first col to timestamp
                if df.columns[0] == 'index':
                    df = df.rename(columns={'index': 'timestamp'})
            
            # Try mapping common names
            cols_map = {
                'time': 'timestamp',
                'Date': 'timestamp',
                'date': 'timestamp',
                'Time': 'timestamp'
            }
            df = df.rename(columns=cols_map)
            
        # Verify timestamp exists now
        if 'timestamp' not in df.columns:
            # Last resort: try checking if a column matches datetime format? 
            # Or assume first column? No, risky.
            # Just print warning and maybe fail later.
            print("⚠️ Warning: 'timestamp' column missing in Backtester data. Using default index if possible.")
            if not isinstance(df.index, pd.DatetimeIndex):
                 # Try to convert first column?
                 pass
        else:
             df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 1. Multi-Timeframe Trend Calculation (Resampling)
        
        # VECTORIZATION STEP
        # Check if strategy has prepare_data method
        if hasattr(self.strategy, 'prepare_data'):
            print("🚀 Vectorizing Indicators...")
            df = self.strategy.prepare_data(df)
            
        # Resample 5M to 1H to get EMA signals
        df_1h = df.set_index('timestamp').resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Calculate Trend Indicators on 1H
        # Calculate Trend Indicators on 1H using Params
        fast_span = p.get('ema_trend_fast', 50)
        slow_span = p.get('ema_trend_slow', 200)
        
        df_1h['ema50'] = df_1h['close'].ewm(span=fast_span, adjust=False).mean()
        df_1h['ema200'] = df_1h['close'].ewm(span=slow_span, adjust=False).mean()
        
        # Determine Trend per 1H candle
        # UP if EMA50 > EMA200
        df_1h['trend'] = df_1h.apply(lambda row: "UP" if row['ema50'] > row['ema200'] else "DOWN", axis=1)
        
        # Re-index back to 5M original dataframe (Forward Fill)
        # This ensures every 5M candle knows what the 1H trend was at that time.
        # merge_asof is perfect for "state as of this time"
        
        # Reset index to make timestamp a column again for merge
        df_1h = df_1h.reset_index()[['timestamp', 'trend']]
        
        # Ensure proper sorting
        df = df.sort_values('timestamp')
        df_1h = df_1h.sort_values('timestamp')
        
        # Merge: For each row in df, find the last row in df_1h where df_1h_ts <= df_ts
        df_merged = pd.merge_asof(
            df, 
            df_1h, 
            on='timestamp', 
            direction='backward'
        )
        
        # Iterate
        # Start from index 200 to have data
        total_steps = len(df_merged) - 200
        
        for i in range(200, len(df_merged)):
            # Progress Update (every 1% or 100 steps)
            if progress_callback and (i % 500 == 0):
                 progress = (i - 200) / total_steps
                 progress_callback(progress)

            # Slice window for analysis (last 100 candles)
            window = df_merged.iloc[i-100:i+1].copy() # includes current candle i
            current_candle = df_merged.iloc[i]
            timestamp = current_candle['timestamp']
            price = current_candle['close']
            
            # 1. Determine Trend (Already calculated)
            trend = current_candle['trend']
            if pd.isna(trend):
                trend = "NEUTRAL" # Should not happen if data is sufficient

            # 2. Get Signal using NEW interface
            # Reset index for get_signal compatibility
            window_reset = window.reset_index(drop=True)
            signal_result = self.strategy.get_signal(window_reset, len(window_reset) - 1, risk_level=risk_level)

            signal = signal_result.get('signal')
            reason = signal_result.get('reason', '')
            exit_type = signal_result.get('exit_type')
            signal_cash_mode = signal_result.get('cash_mode', False)
            
            # 3. Simulate Execution
            if active_position:
                # CHECK EXIT CONDITIONS (SL / TP / SELL)
                pos = active_position
                sl_hit = False
                tp_hit = False
                exit_price = price
                exit_reason = "SIGNAL"

                # --- NEW: TRAILING STOP LOGIC ---
                # Check if price moved in our favor to update SL
                if p.get('trailing_stop_enabled', True): # Enabled by default for v2.0
                    # Calculate Trail Distance (default 1.5x ATR if not specified)
                    # We reuse the ATR calculated at entry if possible, or recalculate
                    # For performance, we can estimate Trail Distance as % if ATR is heavy
                    trail_dist = pos.get('trail_dist')
                    if not trail_dist:
                         # 1.5% default trail if no ATR
                         trail_dist = price * 0.015
                    
                    new_sl = price - trail_dist
                    
                    # Only move SL up
                    if new_sl > pos['sl']:
                        pos['sl'] = new_sl
                        # Optional: Log trailing update? (Too verbose for backtest)

                # Check Stop Loss (Low <= SL)
                if current_candle['low'] <= pos['sl']:
                    sl_hit = True
                    exit_price = pos['sl']
                    exit_reason = "STOP_LOSS"

                # Check Take Profit (High >= TP)
                elif current_candle['high'] >= pos['tp']:
                    tp_hit = True
                    exit_price = pos['tp']
                    exit_reason = "TAKE_PROFIT"

                # Check Strategy Sell Signal
                elif signal == "SELL":
                    # Check if it's a FULL exit (exit to cash)
                    if exit_type == 'FULL':
                        exit_reason = "EXIT_TO_CASH"
                        cash_mode = True  # Enter cash mode
                    else:
                        exit_reason = "SIGNAL_SELL"

                # EXECUTE EXIT
                should_exit = sl_hit or tp_hit or (signal == "SELL")

                if should_exit:
                    # CLOSE POSITION
                    # Calc Proceeds
                    exit_val_gross = pos['size'] * exit_price
                    exit_fee = exit_val_gross * fee_rate
                    exit_val_net = exit_val_gross - exit_fee

                    balance += exit_val_net

                    # PnL
                    cost_total = pos['cost_basis'] + pos['entry_fee']
                    pnl = exit_val_net - cost_total
                    pnl_pct = (pnl / cost_total) * 100

                    trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': timestamp,
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'reason': exit_reason,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'balance': balance,
                        'cash_mode': cash_mode
                    })

                    active_position = None

            else:
                # No position - check if we should enter
                # If in cash_mode, only accept BUY signals to exit cash mode
                if cash_mode:
                    if signal == "BUY":
                        cash_mode = False  # Exit cash mode on strong BUY
                        # Continue to position opening below
                    else:
                        # Stay in cash, do nothing
                        pass

                # Open position on BUY (if not in cash_mode, or if exiting cash_mode)
                if signal == "BUY" and not cash_mode:
                    # Position Sizing: Use fixed $1000
                    size_usd = 1000

                    if balance > size_usd:
                        # Fee
                        entry_fee = size_usd * fee_rate
                        cost_deduct = size_usd + entry_fee

                        if balance >= cost_deduct:
                            balance -= cost_deduct

                            # Get SL/TP from signal result (already calculated by strategy)
                            sl_price = signal_result.get('sl')
                            tp_price = signal_result.get('tp')

                            # Fallback to ATR-based if not provided
                            if sl_price is None or tp_price is None:
                                atr = self.strategy.calculate_atr(window_reset, len(window_reset) - 1, period=14)
                                sl_mult = p.get('sl_multiplier', 2.5)
                                tp_mult = p.get('tp_multiplier', 6.0)

                                if atr == 0:
                                    atr = price * 0.01

                                sl_price = price - (sl_mult * atr)
                                tp_price = price + (tp_mult * atr)

                            active_position = {
                                'entry_price': price,
                                'size': size_usd / price,
                                'cost_basis': size_usd,
                                'entry_fee': entry_fee,
                                'entry_time': timestamp,
                                'sl': sl_price,
                                'tp': tp_price,
                                'trail_dist': (price - sl_price) * 0.8 # Trail is 80% of initial risk distance
                            }

            # Valid equity recording
            equity = balance
            if active_position:
                # Mark to market
                val_gross = active_position['size'] * price
                val_net = val_gross * (1 - fee_rate) # approx exit fee
                equity += val_net
            
            equity_curve.append({'timestamp': timestamp, 'equity': equity})
            
        return pd.DataFrame(equity_curve), pd.DataFrame(trades)

# Test execution
if __name__ == "__main__":
    bt = Backtester()
    # Simple test download
    end = datetime.now()
    start = end - timedelta(days=2) 
    # data = bt.download_data("BTC-USD", start, end, "FIVE_MINUTE")
    # if data is not None:
    #     eq, tr = bt.run_backtest(data)
    #     print(tr)
