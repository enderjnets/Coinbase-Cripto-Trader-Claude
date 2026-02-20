#!/usr/bin/env python3
"""
Test para entender por qué 0 trades genera PnL positivo
"""

import pandas as pd
from dynamic_strategy import DynamicStrategy
from backtester import Backtester

print("\n" + "="*80)
print("🔬 TEST: ¿Por qué 0 trades genera PnL positivo?")
print("="*80 + "\n")

# 1. Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df):,} velas\n")

# 2. Crear estrategia imposible (nunca genera señales)
genome_impossible = {
    "entry_rules": [
        {
            "left": {"field": "close"},
            "op": ">",
            "right": {"value": 999999999}  # Imposible: close > 999M
        }
    ],
    "exit_rules": [],
    "params": {
        "sl_pct": 0.05,
        "tp_pct": 0.10
    }
}

print("📋 Estrategia IMPOSIBLE:")
print("   Regla: close > 999,999,999 (nunca se cumple)")
print("   Debería generar 0 trades y PnL = $0\n")

# 3. Ejecutar backtest
bt = Backtester()
_, trades_df = bt.run_backtest(
    df=df,
    risk_level="LOW",
    initial_balance=10000,
    strategy_params=genome_impossible,
    strategy_cls=DynamicStrategy
)

print("="*80)
print("📊 RESULTADOS")
print("="*80 + "\n")

total_trades = len(trades_df)
total_pnl = trades_df['pnl'].sum() if total_trades > 0 else 0.0
final_balance = trades_df['balance'].iloc[-1] if total_trades > 0 else 10000.0

print(f"📊 Trades: {total_trades}")
print(f"💰 Total PnL: ${total_pnl:.2f}")
print(f"💵 Final Balance: ${final_balance:.2f}")

if total_trades == 0 and total_pnl != 0:
    print(f"\n❌ BUG CONFIRMADO:")
    print(f"   Con 0 trades el PnL debería ser $0.00, pero es ${total_pnl:.2f}")
elif total_trades == 0 and total_pnl == 0:
    print(f"\n✅ CORRECTO: 0 trades = $0 PnL")
elif total_trades > 0:
    print(f"\n⚠️  La estrategia generó {total_trades} trades (debería ser 0)")

# 4. Mostrar trades_df
if len(trades_df) > 0:
    print(f"\n📋 Trades generados (primeros 5):")
    print(trades_df.head())
else:
    print(f"\n✅ trades_df está vacío (correcto)")

print("\n" + "="*80 + "\n")
