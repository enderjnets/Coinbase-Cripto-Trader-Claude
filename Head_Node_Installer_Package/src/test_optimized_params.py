"""
Test con parámetros OPTIMIZADOS
Comparación: Viejos vs Nuevos parámetros
"""

import pandas as pd
from backtester import Backtester

print("=" * 80)
print("🚀 TEST CON PARÁMETROS OPTIMIZADOS")
print("=" * 80)

# Cargar período alcista
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df_bullish = df.iloc[16500:19500].reset_index(drop=True)

print(f"\n📊 Período ALCISTA:")
print(f"   {df_bullish['timestamp'].iloc[0]} → {df_bullish['timestamp'].iloc[-1]}")
print(f"   ${df_bullish['close'].iloc[0]:,.2f} → ${df_bullish['close'].iloc[-1]:,.2f}")
print(f"   Cambio: +{((df_bullish['close'].iloc[-1] / df_bullish['close'].iloc[0]) - 1) * 100:.2f}%")

# Parámetros NUEVOS (optimizados)
new_params = {
    'grid_spacing_pct': 2.0,      # Increased from 1.2%
    'min_move_pct': 2.5,          # Increased from 1.5%
    'sl_multiplier': 2.5,         # Increased from 1.5
    'tp_multiplier': 6.0,         # Increased from 3.0
    'num_grids': 8,
    'grid_range_pct': 12.0,
    'rebalance_threshold': 6.0
}

print("\n" + "=" * 80)
print("⚡ EJECUTANDO BACKTEST CON PARÁMETROS OPTIMIZADOS")
print("=" * 80)

print("\n🔧 NUEVOS PARÁMETROS:")
print(f"   Grid Spacing:   2.0% (was 1.2%)")
print(f"   Min Move:       2.5% (was 1.5%)")
print(f"   SL Multiplier:  2.5x (was 1.5x)")
print(f"   TP Multiplier:  6.0x (was 3.0x)")
print(f"   Num Grids:      8 (was 10)")

backtester = Backtester()

try:
    # Backtest con nuevos parámetros
    equity, trades = backtester.run_backtest(
        df_bullish,
        risk_level="LOW",
        strategy_params=new_params
    )

    print("\n" + "=" * 80)
    print("📈 RESULTADOS CON PARÁMETROS OPTIMIZADOS")
    print("=" * 80)

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

        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   Total trades:     {total_trades}")
        print(f"   Ganadores:        {winners} ({win_rate:.1f}%)")
        print(f"   Perdedores:       {losers}")

        if winners > 0:
            print(f"   Ganancia promedio: ${avg_win:.2f}")
        if losers > 0:
            print(f"   Pérdida promedio:  ${avg_loss:.2f}")

        if losers > 0 and avg_loss != 0 and winners > 0:
            profit_factor = abs((avg_win * winners) / (avg_loss * losers))
            risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            print(f"   Profit Factor:     {profit_factor:.2f}")
            print(f"   Risk/Reward Ratio: {risk_reward:.2f}")

        # Razones de salida
        print(f"\n🚪 RAZONES DE SALIDA:")
        print(trades['reason'].value_counts().to_string())

        # Mejores y peores
        print(f"\n🏆 MEJOR TRADE:  ${trades['pnl'].max():.2f}")
        print(f"📉 PEOR TRADE:   ${trades['pnl'].min():.2f}")

        # Análisis por tipo de salida
        tp_trades = trades[trades['reason'] == 'TAKE_PROFIT']
        sl_trades = trades[trades['reason'] == 'STOP_LOSS']

        if not tp_trades.empty:
            tp_pnl = tp_trades['pnl'].sum()
            tp_avg = tp_trades['pnl'].mean()
            tp_wins = len(tp_trades[tp_trades['pnl'] > 0])
            print(f"\n✅ TAKE PROFIT ({len(tp_trades)} trades):")
            print(f"   PnL total: ${tp_pnl:.2f}")
            print(f"   PnL promedio: ${tp_avg:.2f}")
            print(f"   Ganadores: {tp_wins}/{len(tp_trades)}")

        if not sl_trades.empty:
            sl_pnl = sl_trades['pnl'].sum()
            sl_avg = sl_trades['pnl'].mean()
            print(f"\n❌ STOP LOSS ({len(sl_trades)} trades):")
            print(f"   PnL total: ${sl_pnl:.2f}")
            print(f"   PnL promedio: ${sl_avg:.2f}")

        # Comparación con parámetros viejos
        print("\n" + "=" * 80)
        print("📊 COMPARACIÓN: NUEVOS vs VIEJOS PARÁMETROS")
        print("=" * 80)
        print(f"\n{'Métrica':<25} {'NUEVOS':<20} {'VIEJOS':<20} {'Mejora':<15}")
        print("-" * 80)
        print(f"{'PnL':<25} ${total_pnl:>18.2f} ${-98.44:>18.2f} {'+' if total_pnl > -98.44 else ''}{total_pnl + 98.44:>13.2f}")
        print(f"{'Win Rate':<25} {win_rate:>18.1f}% {0.0:>18.1f}% {'+' if win_rate > 0 else ''}{win_rate:>13.1f}%")
        print(f"{'ROI':<25} {roi:>18.2f}% {-0.98:>18.2f}% {'+' if roi > -0.98 else ''}{roi + 0.98:>13.2f}%")
        print(f"{'Total Trades':<25} {total_trades:>18} {13:>18} {total_trades - 13:>14}")

        if winners > 0:
            print(f"{'Trades Ganadores':<25} {winners:>18} {0:>18} {'+' + str(winners):>14}")

        # Primeros trades
        print(f"\n📋 PRIMEROS 5 TRADES:")
        print(trades[['entry_time', 'entry_price', 'exit_price', 'pnl', 'reason']].head().to_string(index=False))

        # Guardar resultados
        trades.to_csv('backtest_optimized_params.csv', index=False)
        print(f"\n💾 Resultados guardados: backtest_optimized_params.csv")

    else:
        print("\n⚠️  No se generaron trades")
        print("   Posibles razones:")
        print("   - Parámetros demasiado restrictivos")
        print("   - Movimientos no alcanzaron el min_move_pct de 2.5%")

    print("\n" + "=" * 80)

    if not trades.empty and total_pnl > 0:
        print("✅ ¡ESTRATEGIA RENTABLE CON NUEVOS PARÁMETROS!")
    elif not trades.empty and win_rate > 0:
        print("⚠️  Estrategia genera trades ganadores, pero necesita optimización")
    else:
        print("❌ Estrategia necesita más ajustes")

    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
