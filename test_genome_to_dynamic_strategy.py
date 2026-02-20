#!/usr/bin/env python3
"""
Test que simula exactamente lo que hace strategy_miner -> run_backtest_task -> backtester
"""

import pandas as pd
from dynamic_strategy import DynamicStrategy
from backtester import Backtester

# 1. Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df)} velas\n")

# 2. Crear un genome simple (igual que strategy_miner)
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

print("📋 Genome:")
print(f"   Rules: {genome['entry_rules']}")
print(f"   SL: {genome['params']['sl_pct']*100}%, TP: {genome['params']['tp_pct']*100}%\n")

# 3. TEST 1: Crear DynamicStrategy pasando genome directamente
print("=" * 80)
print("TEST 1: DynamicStrategy(genome)")
print("=" * 80)
try:
    strategy = DynamicStrategy(genome)
    print(f"✅ Strategy created")
    print(f"   Has entry_rules: {hasattr(strategy, 'entry_rules')}")
    print(f"   Entry rules: {len(strategy.entry_rules) if hasattr(strategy, 'entry_rules') else 'N/A'}")

    # Test get_signal
    test_idx = 500
    signal = strategy.get_signal(df, test_idx)
    print(f"   Signal at idx {test_idx}: {signal}\n")
except Exception as e:
    print(f"❌ ERROR: {e}\n")

# 4. TEST 2: Crear backtester con genome (simulando run_backtest_task)
print("=" * 80)
print("TEST 2: Backtester con strategy_params=genome y strategy_cls=DynamicStrategy")
print("=" * 80)
try:
    bt = Backtester()
    _, trades_df = bt.run_backtest(
        df=df,
        risk_level="LOW",
        initial_balance=10000,
        strategy_params=genome,  # Pasar genome como strategy_params
        strategy_cls=DynamicStrategy  # Pasar DynamicStrategy como clase
    )

    print(f"✅ Backtest completed")
    print(f"   Trades: {len(trades_df)}")
    if len(trades_df) > 0:
        pnl = trades_df['pnl'].sum()
        win_rate = (len(trades_df[trades_df['pnl'] > 0]) / len(trades_df)) * 100
        print(f"   PnL: ${pnl:.2f}")
        print(f"   Win Rate: {win_rate:.1f}%")
    else:
        print(f"   ⚠️ NO TRADES GENERATED")
    print()
except Exception as e:
    print(f"❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()

# 5. TEST 3: Ver qué está pasando dentro de Backtester.__init__
print("=" * 80)
print("TEST 3: Debug de Backtester.__init__ con strategy_cls")
print("=" * 80)
print("Verificando el código de backtester.py líneas 54-72...\n")

# Simulamos lo que hace backtester.py
strategy_cls = DynamicStrategy
strategy_params = genome

print(f"strategy_cls = {strategy_cls}")
print(f"strategy_params = {strategy_params}\n")

print("Intentando: strategy_cls(strategy_params)")
try:
    test_strategy = strategy_cls(strategy_params)
    print(f"✅ SUCCESS: Strategy creado")
    print(f"   Has genome: {hasattr(test_strategy, 'genome')}")
    print(f"   Has entry_rules: {hasattr(test_strategy, 'entry_rules')}")
    if hasattr(test_strategy, 'entry_rules'):
        print(f"   Num entry_rules: {len(test_strategy.entry_rules)}")
except TypeError as e:
    print(f"❌ TypeError: {e}")
    print("   Cayendo en fallback: strategy_cls(None)")
    try:
        test_strategy = strategy_cls(None)
        print(f"✅ Fallback 1 SUCCESS")
        print(f"   Has genome: {hasattr(test_strategy, 'genome')}")
        print(f"   Has entry_rules: {hasattr(test_strategy, 'entry_rules')}")
    except TypeError as e2:
        print(f"❌ TypeError: {e2}")
        print("   Cayendo en fallback 2: strategy_cls()")
        test_strategy = strategy_cls()
        print(f"✅ Fallback 2 SUCCESS")
        print(f"   Has genome: {hasattr(test_strategy, 'genome')}")
        print(f"   Has entry_rules: {hasattr(test_strategy, 'entry_rules')}")

print("\n" + "=" * 80)
