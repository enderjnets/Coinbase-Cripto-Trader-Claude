"""
Test what genomes the Strategy Miner is generating
"""
import pandas as pd
from strategy_miner import StrategyMiner
from backtester import Backtester
from dynamic_strategy import DynamicStrategy

# Load data
df = pd.read_parquet("static_payloads/payload_v1.parquet")

print(f"📊 Data loaded: {len(df)} rows\n")

# Create Strategy Miner
miner = StrategyMiner(df, population_size=5, generations=1, risk_level="LOW")

print("🧬 Generating 5 random genomes:\n")

for i in range(5):
    genome = miner.generate_random_genome()
    print(f"Genome {i+1}:")
    print(f"  Entry Rules ({len(genome['entry_rules'])}):")
    for j, rule in enumerate(genome['entry_rules']):
        print(f"    Rule {j+1}: {rule}")
    print(f"  Params: SL={genome['params']['sl_pct']:.3f}, TP={genome['params']['tp_pct']:.3f}")

    # Test this genome
    bt = Backtester()
    metrics, trades = bt.run_backtest(
        df,
        risk_level="LOW",
        strategy_params=genome,
        strategy_cls=DynamicStrategy
    )

    print(f"  Test Result: {len(trades)} trades, PnL: ${trades['pnl'].sum() if len(trades) > 0 else 0:.2f}\n")
