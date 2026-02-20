"""
Test rápido con subset de datos para validar estrategias
"""

import pandas as pd
from backtester import Backtester

print("=" * 60)
print("🚀 TEST RÁPIDO - Nuevas Estrategias Híbridas")
print("=" * 60)

# Cargar solo los últimos 3000 registros (suficiente para test)
print("\n📊 Cargando datos...")
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Tomar últimos 3000 registros (~ 10 días de datos de 5min)
df_sample = df.tail(3000).reset_index(drop=True)

print(f"✅ Datos: {len(df_sample)} velas")
print(f"   Período: {df_sample['timestamp'].min()} → {df_sample['timestamp'].max()}")
print(f"   Precio: ${df_sample['close'].iloc[0]:.2f} → ${df_sample['close'].iloc[-1]:.2f}")

# Backtest
print("\n⚡ Ejecutando backtest...")
backtester = Backtester()

try:
    equity, trades = backtester.run_backtest(df_sample, risk_level="LOW")

    print("\n" + "=" * 60)
    print("📈 RESULTADOS")
    print("=" * 60)

    if not trades.empty:
        total_trades = len(trades)
        winners = len(trades[trades['pnl'] > 0])
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
        total_pnl = trades['pnl'].sum()
        final_balance = equity.iloc[-1]['equity']
        roi = ((final_balance - 10000) / 10000) * 100

        print(f"\n💰 Balance final: ${final_balance:,.2f}")
        print(f"   PnL: ${total_pnl:,.2f} ({roi:.2f}%)")
        print(f"\n📊 Trades: {total_trades} | Win Rate: {win_rate:.1f}%")

        # Analizar razones de salida
        if 'reason' in trades.columns:
            print(f"\n🚪 Razones de salida:")
            print(trades['reason'].value_counts())

        print(f"\n📋 Primeros 5 trades:")
        print(trades[['entry_time', 'entry_price', 'exit_price', 'pnl', 'reason']].head().to_string(index=False))

        print(f"\n🏆 Mejor trade: ${trades['pnl'].max():.2f}")
        print(f"📉 Peor trade: ${trades['pnl'].min():.2f}")

    else:
        print("\n⚠️  Sin trades generados")

    print("\n✅ Test completado")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
