"""
Test en período ALCISTA (Sep 27 - Oct 7, 2025)
BTC subió +11.08% en 10 días
"""

import pandas as pd
from backtester import Backtester

print("=" * 70)
print("🚀 TEST EN PERÍODO ALCISTA (+11.08%)")
print("=" * 70)

# Cargar datos
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Período alcista: índice 16500 a 19500
df_bullish = df.iloc[16500:19500].reset_index(drop=True)

print(f"\n📊 Período ALCISTA:")
print(f"   Fecha: {df_bullish['timestamp'].iloc[0]} → {df_bullish['timestamp'].iloc[-1]}")
print(f"   Precio: ${df_bullish['close'].iloc[0]:,.2f} → ${df_bullish['close'].iloc[-1]:,.2f}")
print(f"   Cambio: +{((df_bullish['close'].iloc[-1] / df_bullish['close'].iloc[0]) - 1) * 100:.2f}%")
print(f"   Velas: {len(df_bullish)}")

# Backtest
print("\n⚡ Ejecutando backtest en período ALCISTA...")
backtester = Backtester()

try:
    equity, trades = backtester.run_backtest(df_bullish, risk_level="LOW")

    print("\n" + "=" * 70)
    print("📈 RESULTADOS - PERÍODO ALCISTA")
    print("=" * 70)

    if not trades.empty:
        total_trades = len(trades)
        winners = len(trades[trades['pnl'] > 0])
        losers = len(trades[trades['pnl'] < 0])
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades['pnl'].sum()
        avg_win = trades[trades['pnl'] > 0]['pnl'].mean() if winners > 0 else 0
        avg_loss = trades[trades['pnl'] < 0]['pnl'].mean() if losers > 0 else 0

        final_balance = equity.iloc[-1]['equity']
        roi = ((final_balance - 10000) / 10000) * 100

        print(f"\n💰 RENDIMIENTO:")
        print(f"   Balance inicial:  $10,000.00")
        print(f"   Balance final:    ${final_balance:,.2f}")
        print(f"   PnL total:        ${total_pnl:,.2f}")
        print(f"   ROI:              {roi:.2f}%")

        print(f"\n📊 ESTADÍSTICAS DE TRADES:")
        print(f"   Total trades:     {total_trades}")
        print(f"   Ganadores:        {winners} ({win_rate:.1f}%)")
        print(f"   Perdedores:       {losers}")
        print(f"   Ganancia promedio: ${avg_win:.2f}")
        print(f"   Pérdida promedio:  ${avg_loss:.2f}")

        if losers > 0 and avg_loss != 0:
            profit_factor = abs((avg_win * winners) / (avg_loss * losers))
            print(f"   Profit Factor:     {profit_factor:.2f}")

        # Razones de salida
        print(f"\n🚪 RAZONES DE SALIDA:")
        print(trades['reason'].value_counts().to_string())

        # Mejores y peores
        print(f"\n🏆 MEJOR TRADE:  ${trades['pnl'].max():.2f}")
        print(f"📉 PEOR TRADE:   ${trades['pnl'].min():.2f}")

        # Primeros trades
        print(f"\n📋 PRIMEROS 10 TRADES:")
        print(trades[['entry_time', 'entry_price', 'exit_price', 'pnl', 'reason']].head(10).to_string(index=False))

        # Comparación con período bajista
        print("\n" + "=" * 70)
        print("📊 COMPARACIÓN: PERÍODO ALCISTA vs BAJISTA")
        print("=" * 70)
        print(f"\n{'Métrica':<20} {'Alcista (+11%)':<20} {'Bajista (-1.5%)':<20}")
        print("-" * 70)
        print(f"{'PnL':<20} ${total_pnl:>18.2f} ${-166.54:>18.2f}")
        print(f"{'Win Rate':<20} {win_rate:>18.1f}% {19.0:>18.1f}%")
        print(f"{'ROI':<20} {roi:>18.2f}% {-1.67:>18.2f}%")
        print(f"{'Total Trades':<20} {total_trades:>18} {21:>18}")

        # Guardar resultados
        trades.to_csv('backtest_bullish_period.csv', index=False)
        equity.to_csv('equity_bullish_period.csv', index=False)
        print(f"\n💾 Resultados guardados:")
        print(f"   - backtest_bullish_period.csv")
        print(f"   - equity_bullish_period.csv")

    else:
        print("\n⚠️  No se generaron trades")

    print("\n✅ Test completado")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
