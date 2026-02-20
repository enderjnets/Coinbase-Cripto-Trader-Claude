#!/usr/bin/env python3
"""
Test para debugging: ejecutar strategy_miner con logging de payload
"""

import pandas as pd
from strategy_miner import StrategyMiner

# Patch strategy_miner temporarily to add logging
import strategy_miner as sm_module

# Save original evaluate_population
original_eval = sm_module.StrategyMiner.evaluate_population

def patched_eval(self, population, progress_cb=None, cancel_event=None):
    print(f"\n🔍 DEBUG: evaluate_population called")
    print(f"   Population size: {len(population)}")
    print(f"   force_local: {self.force_local}")

    # Call original, but intercept to see cached_payload
    result = original_eval(population, progress_cb, cancel_event)

    if hasattr(self, 'cached_payload'):
        print(f"   cached_payload type: {type(self.cached_payload)}")
        if isinstance(self.cached_payload, str):
            print(f"   cached_payload value: {self.cached_payload}")
        elif hasattr(self.cached_payload, 'shape'):
            print(f"   cached_payload shape: {self.cached_payload.shape}")
    else:
        print(f"   ⚠️  No cached_payload attribute")

    return result

# Apply patch
sm_module.StrategyMiner.evaluate_population = patched_eval

# NOW run the test
print("=" * 80)
print("🧬 STRATEGY MINER - DEBUG PAYLOAD")
print("=" * 80)
print()

df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df)} velas\n")

# Use 1 population, 1 generation for quick debug
miner = StrategyMiner(
    df=df,
    population_size=1,
    generations=1,
    risk_level="LOW",
    force_local=False  # Use Ray to test distributed path
)

def show_progress(msg_type, data):
    if msg_type == "BEST_GEN":
        trades = data.get('num_trades', 0)
        pnl = data.get('pnl', 0)
        print(f"\n📊 Gen {data['gen']}: PnL=${pnl:.2f}, Trades={trades}")

best_genome, best_pnl = miner.run(progress_callback=show_progress)

print("\n" + "=" * 80)
print("RESULTADO")
print("=" * 80)
print(f"Best PnL: ${best_pnl:.2f}")

if best_pnl == 0:
    print("❌ PnL = $0 (probablemente 0 trades)")
else:
    print("✅ PnL != $0 (estrategia generó trades)")

print("\n" + "=" * 80)
