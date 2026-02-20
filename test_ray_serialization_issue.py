#!/usr/bin/env python3
"""
Test para verificar si hay problema de serialización con self.df vs df.copy()
"""

import ray
import pandas as pd
from optimizer import run_backtest_task
from strategy_miner import StrategyMiner

# Inicializar Ray
if not ray.is_initialized():
    ray.init(address='auto')

print("=" * 80)
print("🧪 TEST: Serialización de DataFrame con Ray")
print("=" * 80)
print()

# Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df)} velas\n")

# Genome simple
genome = {
    "entry_rules": [
        {
            "left": {"field": "close"},
            "op": "<",
            "right": {"indicator": "SMA", "period": 200}
        }
    ],
    "params": {
        "sl_pct": 0.046,
        "tp_pct": 0.040
    }
}

print("=" * 80)
print("TEST 1: DataFrame directo (df.copy())")
print("=" * 80)
result_ref = run_backtest_task.remote(df.copy(), "LOW", genome, "DYNAMIC")
result = ray.get(result_ref)
print(f"Trades: {result['metrics']['Total Trades']}")
print(f"PnL: ${result['metrics']['Total PnL']:.2f}\n")

print("=" * 80)
print("TEST 2: DataFrame desde StrategyMiner.df (self.cached_payload)")
print("=" * 80)

# Crear StrategyMiner (forzar local para que no use HTTP, use self.df)
miner = StrategyMiner(
    df=df,
    population_size=1,
    generations=1,
    risk_level="LOW",
    force_local=False  # NO force local, para que use Ray
)

# Obtener cached_payload que strategy_miner usaría
print(f"Type of miner.cached_payload: {type(miner.cached_payload)}")
print(f"Shape: {miner.cached_payload.shape if hasattr(miner.cached_payload, 'shape') else 'N/A'}")
print()

# Probar con ese payload
result_ref2 = run_backtest_task.remote(miner.cached_payload, "LOW", genome, "DYNAMIC")
result2 = ray.get(result_ref2)
print(f"Trades: {result2['metrics']['Total Trades']}")
print(f"PnL: ${result2['metrics']['Total PnL']:.2f}\n")

print("=" * 80)
print("RESULTADO")
print("=" * 80)

if result['metrics']['Total Trades'] > 0 and result2['metrics']['Total Trades'] > 0:
    print("✅ AMBOS TESTS GENERARON TRADES")
    print("   El problema NO es la serialización del DataFrame")
elif result['metrics']['Total Trades'] > 0 and result2['metrics']['Total Trades'] == 0:
    print("❌ PROBLEMA ENCONTRADO:")
    print("   df.copy() funciona, pero miner.cached_payload NO")
    print("   Investigar diferencias entre ambos DataFrames")
else:
    print("⚠️  Resultado inesperado")

print()
