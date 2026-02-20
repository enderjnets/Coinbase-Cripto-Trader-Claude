#!/usr/bin/env python3
"""
Test para ver qué genomes exactos está generando strategy_miner
"""

import pandas as pd
from strategy_miner import StrategyMiner
import json

print("=" * 80)
print("🧬 TEST: Genomes generados por Strategy Miner")
print("=" * 80)
print()

# Cargar datos (pequeño para test rápido)
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df)} velas\n")

# Crear miner
miner = StrategyMiner(
    df=df,
    population_size=5,  # Solo 5 para test rápido
    generations=1,
    risk_level="LOW",
    force_local=True  # Force local para test rápido
)

# Generar población inicial
print("Generando 5 genomes random...\n")
population = [miner.generate_random_genome() for _ in range(5)]

# Mostrar cada genome
for i, genome in enumerate(population):
    print(f"Genome {i+1}:")
    print(f"  Entry Rules: {len(genome.get('entry_rules', []))}")
    for j, rule in enumerate(genome.get('entry_rules', [])):
        print(f"    Rule {j+1}: {json.dumps(rule, indent=6)}")
    print(f"  Params: SL={genome['params']['sl_pct']*100:.1f}%, TP={genome['params']['tp_pct']*100:.1f}%")
    print()

# Ahora probamos UNO de estos genomes con run_backtest_task
print("=" * 80)
print("🧪 TEST: Ejecutar Genome #1 con Backtester directo")
print("=" * 80)
print()

from backtester import Backtester
from dynamic_strategy import DynamicStrategy

genome = population[0]

bt = Backtester()
_, trades_df = bt.run_backtest(
    df=df,
    risk_level="LOW",
    initial_balance=10000,
    strategy_params=genome,
    strategy_cls=DynamicStrategy
)

print(f"✅ Backtest completado")
print(f"   Trades: {len(trades_df)}")
if len(trades_df) > 0:
    pnl = trades_df['pnl'].sum()
    win_rate = (len(trades_df[trades_df['pnl'] > 0]) / len(trades_df)) * 100
    print(f"   PnL: ${pnl:.2f}")
    print(f"   Win Rate: {win_rate:.1f}%")
else:
    print(f"   ⚠️ NO TRADES (genome puede ser demasiado restrictivo)")
    print(f"   Esto puede ser normal - algunos genomes no generan trades")

print("\n" + "=" * 80)
