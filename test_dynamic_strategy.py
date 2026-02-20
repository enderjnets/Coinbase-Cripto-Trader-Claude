"""
Quick test to verify DynamicStrategy generates trades with a simple genome
"""
import pandas as pd
from backtester import Backtester
from dynamic_strategy import DynamicStrategy

# Load data (use existing test data)
df = pd.read_parquet("static_payloads/payload_v1.parquet")

print(f"📊 Data loaded: {len(df)} rows")
print(f"   Date range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

# Create a simple genome that should generate some trades
# RSI < 30 (oversold) - a condition that should trigger occasionally
simple_genome = {
    "entry_rules": [
        {
            "left": {"indicator": "RSI", "period": 14},
            "op": "<",
            "right": {"value": 35}  # RSI below 35 (oversold)
        }
    ],
    "params": {
        "sl_pct": 0.02,  # 2% stop loss
        "tp_pct": 0.04   # 4% take profit
    }
}

print(f"\n🧬 Testing genome:")
print(f"   Rules: {len(simple_genome['entry_rules'])}")
print(f"   Rule 1: RSI(14) < 35")
print(f"   SL: 2%, TP: 4%")

# Run backtest
bt = Backtester()
metrics, trades = bt.run_backtest(
    df,
    risk_level="LOW",
    strategy_params=simple_genome,
    strategy_cls=DynamicStrategy
)

print(f"\n📈 Results:")
print(f"   Total Trades: {len(trades)}")
if len(trades) > 0:
    total_pnl = trades['pnl'].sum()
    win_rate = (len(trades[trades['pnl'] > 0]) / len(trades)) * 100
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   ✅ DynamicStrategy WORKS!")
else:
    print(f"   ❌ NO TRADES - DynamicStrategy not working properly")
    print(f"\n🔍 Debugging info:")
    print(f"   DataFrame shape: {df.shape}")
    print(f"   Columns: {df.columns.tolist()}")
