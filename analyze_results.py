"""
Analizar resultados del backtest en detalle
"""

import pandas as pd
from backtester import Backtester

print("🔍 ANÁLISIS DETALLADO DE RESULTADOS\n")

# Cargar datos
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df_sample = df.tail(3000).reset_index(drop=True)

print(f"Período: {df_sample['timestamp'].iloc[0]} → {df_sample['timestamp'].iloc[-1]}")
print(f"Movimiento de precio: ${df_sample['close'].iloc[0]:.2f} → ${df_sample['close'].iloc[-1]:.2f}")
print(f"Cambio: {((df_sample['close'].iloc[-1] / df_sample['close'].iloc[0]) - 1) * 100:.2f}%\n")

# Backtest
backtester = Backtester()
equity, trades = backtester.run_backtest(df_sample, risk_level="LOW")

print("=" * 80)
print("📊 ANÁLISIS DE TRADES")
print("=" * 80 + "\n")

print(f"Total trades: {len(trades)}")
print(f"\nColumnas disponibles:")
for col in trades.columns:
    print(f"  - {col}")

print(f"\n📋 TODOS LOS TRADES:")
print(trades.to_string())

# Estadísticas
if not trades.empty:
    print(f"\n📈 ESTADÍSTICAS:")
    print(f"PnL Total: ${trades['pnl'].sum():.2f}")
    print(f"PnL Promedio: ${trades['pnl'].mean():.2f}")
    print(f"PnL Max: ${trades['pnl'].max():.2f}")
    print(f"PnL Min: ${trades['pnl'].min():.2f}")

    # Razones de salida
    print(f"\n🚪 RAZONES DE SALIDA:")
    print(trades['exit_reason'].value_counts())

    # Exportar para análisis
    trades.to_csv('trades_debug.csv', index=False)
    print(f"\n💾 Trades guardados en: trades_debug.csv")
