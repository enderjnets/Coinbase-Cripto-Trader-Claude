#!/usr/bin/env python3
"""
Test simple: Ejecutar un backtest con el dataset grande para verificar que genera trades
"""

import pandas as pd
from backtester import Backtester
from dynamic_strategy import DynamicStrategy

print("\n" + "="*80)
print("TEST SIMPLE - BACKTEST CON DATASET GRANDE")
print("="*80 + "\n")

# Cargar dataset grande
df = pd.read_csv("data/BTC-USD_ONE_MINUTE.csv")
print(f"Dataset: {len(df):,} velas")
print(f"Rango: {df.iloc[0, 0]} a {df.iloc[-1, 0]}\n")

# Definir una estrategia simple que DEBERIA generar trades
test_genome = {
    "entry_rules": [
        {
            "left": {"indicator": "RSI", "period": 14},
            "op": "<",
            "right": {"value": 30}
        }
    ],
    "params": {
        "sl_pct": 0.02,
        "tp_pct": 0.04
    }
}

print("Estrategia de prueba:")
print(f"  RSI(14) < 30 (Buy Oversold)")
print(f"  SL: 2%, TP: 4%\n")

# Ejecutar backtest
bt = Backtester()
print("Ejecutando backtest...")

try:
    equity, trades = bt.run_backtest(
        df,
        risk_level="LOW",
        strategy_params=test_genome,
        strategy_cls=DynamicStrategy
    )

    print(f"\n{'='*80}")
    print("RESULTADOS:")
    print(f"{'='*80}")
    print(f"Total Trades: {len(trades)}")

    if len(trades) > 0:
        wins = trades[trades['pnl'] > 0]
        win_rate = (len(wins) / len(trades)) * 100
        total_pnl = trades['pnl'].sum()
        final_balance = trades['balance'].iloc[-1]

        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Total PnL: ${total_pnl:.2f}")
        print(f"Final Balance: ${final_balance:.2f}")
        print(f"\nPrimeros 5 trades:")
        print(trades.head())
        print(f"\nSUCCESS: El backtest genera trades correctamente")
    else:
        print("\nWARNING: No se generaron trades")
        print("Esto sugiere que las condiciones de entrada nunca se cumplen")

        # Vamos a verificar los valores de RSI
        print("\nAnalizando indicadores...")
        from strategy_logic import StrategyLogic
        logic = StrategyLogic(df)

        # Calcular RSI
        import pandas_ta as ta
        rsi = ta.rsi(df['close'], length=14)

        print(f"\nRSI(14) estadisticas:")
        print(f"  Min: {rsi.min():.2f}")
        print(f"  Max: {rsi.max():.2f}")
        print(f"  Mean: {rsi.mean():.2f}")
        print(f"  Veces que RSI < 30: {(rsi < 30).sum()}")
        print(f"  % del tiempo RSI < 30: {((rsi < 30).sum() / len(rsi)) * 100:.2f}%")

    print(f"{'='*80}\n")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
