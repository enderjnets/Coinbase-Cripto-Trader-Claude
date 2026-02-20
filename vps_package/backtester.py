import pandas as pd
import time
from datetime import datetime, timedelta
from config import Config
from scanner import Scanner
from strategy import Strategy

class Backtester:
    def __init__(self):
        self.scanner = Scanner()
        self.strategy = Strategy()
        self.results = {}
        
    def download_data(self, product_id, start_date, end_date, granularity_str):
        """
        Downloads historical data with pagination to handle API limits.
        granularity_str: "FIVE_MINUTE", "ONE_HOUR", etc.
        """
        print(f"Downloading data for {product_id} from {start_date} to {end_date}...")
        
        # Map granularity string to seconds for stride calculation
        granularity_map = {
            "ONE_MINUTE": 60,
            "FIVE_MINUTE": 300,
            "FIFTEEN_MINUTE": 900,
            "ONE_HOUR": 3600,
            "SIX_HOUR": 21600,
            "ONE_DAY": 86400
        }
        
        gran_seconds = granularity_map.get(granularity_str, 300)
        
        # Coinbase limit is approx 300 candles per request. safe margin 250.
        chunk_size_seconds = gran_seconds * 250
        
        all_dfs = []
        current_end = end_date
        
        while current_end > start_date:
            current_start = max(start_date, current_end - timedelta(seconds=chunk_size_seconds))
            
            # Convert to unix timestamp for API
            ts_start = int(current_start.timestamp())
            ts_end = int(current_end.timestamp())
            
            # Fetch
            # print(f"Fetching chunk: {current_start} -> {current_end}")
            df_chunk = self.scanner.get_candles(product_id, ts_start, ts_end, granularity_str)
            
            if df_chunk is not None and not df_chunk.empty:
                all_dfs.append(df_chunk)
            
            # Move specific window back
            current_end = current_start
            
            # Rate limit
            time.sleep(0.15)
            
        if not all_dfs:
            return None
            
        # Concatenate and Sort
        full_df = pd.concat(all_dfs)
        full_df = full_df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        print(f"Download complete. Total candles: {len(full_df)}")
        return full_df

    def run_backtest(self, df, risk_level="LOW", initial_balance=10000):
        """
        Simulates the strategy on the historical DataFrame.
        Assume Spot Trading (Long Only) + Fees.
        """
        balance = initial_balance
        equity_curve = []
        trades = []
        active_position = None # {entry_price, size, time}
        
        # Fee Config
        fee_rate = getattr(Config, 'TRADING_FEE_PERCENT', 0.6) / 100.0
        
        # Pre-calculate indicators
        # We need a window for trend. 
        # Simulating "Trend" context is tricky if we only download 5m data.
        # Approximation: Use internal 200 EMA of the 5m data as 'Trend' proxy 
        # OR require user to provide separate Trend Dataframe.
        # For simplicity V1: Calculate Indicators on the provided DF.
        
        # We need 2 EMAs for trend check if we stick to strategy.py logic exactly?
        # Strategy.check_trend uses EMA50 vs EMA200.
        # Let's compute them on the 5m frame for this test, or ideally we'd need 1h data too.
        # To avoid complexity of downloading 2 datasets, we'll assume Trend is determined by 
        # the same timeframe's EMA200 for backtest V1 (or we fetch it, but that's slow).
        # Better: Let's use the provided DF.
        
        # Add basic indicators
        df['ema50'] = df['close'].ewm(span=50).mean()
        df['ema200'] = df['close'].ewm(span=200).mean()
        
        # Iterate
        # Start from index 200 to have data
        for i in range(200, len(df)):
            # Slice window for analysis (last 100 candles)
            window = df.iloc[i-100:i+1].copy() # includes current candle i
            current_candle = df.iloc[i]
            timestamp = current_candle['timestamp']
            price = current_candle['close']
            
            # 1. Determine Trend (Proxy using available EMA provided)
            # Strategy: if EMA50 > EMA200 -> UP
            trend = "UP" if current_candle['ema50'] > current_candle['ema200'] else "DOWN"
            
            # 2. Support/Resistance & Signal
            # Strategy expects df_5m (window)
            window = self.strategy.calculate_support_resistance(window)
            
            signal, reason = self.strategy.detect_signal(window, trend, risk_level)
            
            # 3. Simulate Execution
            if active_position:
                # Check for Exit Signal (SELL) or Stop Loss / Take Profit
                # Simple logic for Backtest: Exit if Signal is SELL
                
                # We could also impl SL/TP here if we passed params
                
                if signal == "SELL":
                    # CLOSE POSITION
                    pos = active_position
                    
                    # Calc Proceeds
                    exit_val_gross = pos['size'] * price
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
                        'exit_price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'balance': balance
                    })
                    
                    active_position = None
                    
            else:
                # No position, check BUY
                if signal == "BUY":
                    # OPEN POSITION
                    # Position Sizing: Use fixed $100 or Risk %?
                    # Let's use $1000 fixed for clear metrics or % of balance
                    size_usd = 1000 # Fixed size
                    
                    if balance > size_usd:
                        # Fee
                        entry_fee = size_usd * fee_rate
                        cost_deduct = size_usd + entry_fee
                        
                        if balance >= cost_deduct:
                            balance -= cost_deduct
                            active_position = {
                                'entry_price': price,
                                'size': size_usd / price,
                                'cost_basis': size_usd,
                                'entry_fee': entry_fee,
                                'entry_time': timestamp
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
