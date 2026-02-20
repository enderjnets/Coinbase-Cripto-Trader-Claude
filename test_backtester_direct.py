#!/usr/bin/env python3
"""
Test directo del backtester con la estrategia generada
"""

import pandas as pd
from dynamic_strategy import DynamicStrategy
from backtester import Backtester

print("\n" + "="*80)
print("🎯 TEST DIRECTO: Backtester + DynamicStrategy")
print("="*80 + "\n")

# 1. Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df):,} velas\n")

# 2. Estrategia del miner
genome = {
    "entry_rules": [
        {
            "left": {"field": "close"},
            "op": "<",
            "right": {"indicator": "SMA", "period": 200}
        }
    ],
    "exit_rules": [],
    "params": {
        "sl_pct": 0.046,
        "tp_pct": 0.040
    }
}

print("📋 Estrategia:")
print("   Regla: close < SMA(200)")
print("   SL: 4.6%, TP: 4.0%\n")

strategy = DynamicStrategy(genome)

# 3. Ejecutar backtester
print("⚙️  Ejecutando backtester...\n")

bt = Backtester()

# Usar la interfaz correcta del backtester
_, trades_df = bt.run_backtest(
    df=df,
    risk_level="LOW",
    initial_balance=10000,
    strategy_params=genome,  # Pasar genome
    strategy_cls=DynamicStrategy  # Pasar clase
)

# Calcular resultado
result = {
    'pnl': trades_df['pnl'].sum() if len(trades_df) > 0 else 0.0,
    'num_trades': len(trades_df),
    'win_rate': (len(trades_df[trades_df['pnl'] > 0]) / len(trades_df)) if len(trades_df) > 0 else 0.0,
    'final_balance': trades_df['balance'].iloc[-1] if len(trades_df) > 0 else 10000,
    'return_pct': ((trades_df['balance'].iloc[-1] - 10000) / 10000 * 100) if len(trades_df) > 0 else 0.0,
    'trades': trades_df.to_dict('records') if len(trades_df) > 0 else []
}

# 4. Mostrar resultados
print("="*80)
print("📊 RESULTADOS")
print("="*80 + "\n")

print(f"💰 PnL: ${result['pnl']:.2f}")
print(f"📈 Return %: {result['return_pct']:.2f}%")
print(f"📊 Trades: {result['num_trades']}")
print(f"✅ Win Rate: {result['win_rate']*100:.1f}%")
print(f"💵 Balance Final: ${result['final_balance']:.2f}")

if result['num_trades'] == 0:
    print("\n❌ ERROR: Backtester NO generó trades!")
    print("\nPosibles causas:")
    print("  1. Backtester no está llamando a prepare_data()")
    print("  2. Backtester tiene un bug que impide generar trades")
    print("  3. Los parámetros del backtester son incorrectos")
else:
    print(f"\n✅ Backtester funcionó correctamente")

    print(f"\n📋 Detalles de trades:")
    if 'trades' in result and len(result['trades']) > 0:
        for i, trade in enumerate(result['trades'][:5], 1):
            print(f"   Trade {i}:")
            print(f"      Entry: ${trade.get('entry_price', 0):.2f} @ idx {trade.get('entry_idx', 0)}")
            print(f"      Exit: ${trade.get('exit_price', 0):.2f} @ idx {trade.get('exit_idx', 0)}")
            print(f"      PnL: ${trade.get('pnl', 0):.2f}")
            print(f"      Result: {trade.get('result', 'N/A')}")

print("\n" + "="*80 + "\n")
