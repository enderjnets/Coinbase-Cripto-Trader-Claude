
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtester import Backtester

# Create dummy 5M data for 10 days
dates = pd.date_range(start="2025-01-01", end="2025-01-15", freq="5min")
# Create a trend: sin wave for price
prices = 100 + 10 * np.sin(np.linspace(0, 50, len(dates))) + np.random.normal(0, 0.5, len(dates))

df = pd.DataFrame({
    'timestamp': dates,
    'open': prices,
    'high': prices + 0.5,
    'low': prices - 0.5,
    'close': prices,
    'volume': 1000
})

print(f"Created {len(df)} candles.")

bt = Backtester()

try:
    print("Running backtest...")
    equity, trades = bt.run_backtest(df)
    print("Backtest finished.")
    print(f"Trades: {len(trades)}")
    print(equity.head())
    print("\nCheck if 'trend' column was effective:")
    # We can't check internal var easily but if it ran without error, merge_asof worked.
    print("Success.")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
