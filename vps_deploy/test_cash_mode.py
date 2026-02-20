"""
Test Cash Mode Implementation
Verifica que la estrategia sale a cash en mercados bajistas y re-entra en alcistas
"""

import pandas as pd
from backtester import Backtester

print("=" * 80)
print("🧪 TEST DE CASH MODE (Exit to Cash)")
print("=" * 80)

# Cargar datos completos
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"\n📊 Datos cargados: {len(df)} velas")
print(f"   Período: {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")

# Parámetros optimizados
params = {
    'grid_spacing_pct': 2.0,
    'min_move_pct': 2.5,
    'sl_multiplier': 2.5,
    'tp_multiplier': 6.0,
    'num_grids': 8,
    'grid_range_pct': 12.0,
    'rebalance_threshold': 6.0
}

# Test 1: Período BAJISTA (debería activar cash_mode)
print("\n" + "=" * 80)
print("📉 TEST 1: PERÍODO BAJISTA SEVERO")
print("=" * 80)

# Usar período con caída máxima de -13.59%
# Índice 20000:20500 - caída total -7.85%, caída máxima -13.59%
df_bearish = df.iloc[20000:20500].reset_index(drop=True)

print(f"\n📊 Datos del período:")
print(f"   {df_bearish['timestamp'].iloc[0]} → {df_bearish['timestamp'].iloc[-1]}")
print(f"   ${df_bearish['close'].iloc[0]:,.2f} → ${df_bearish['close'].iloc[-1]:,.2f}")
change_pct = ((df_bearish['close'].iloc[-1] / df_bearish['close'].iloc[0]) - 1) * 100
print(f"   Cambio: {change_pct:+.2f}%")

backtester = Backtester()

try:
    equity, trades = backtester.run_backtest(
        df_bearish,
        risk_level="LOW",
        strategy_params=params
    )

    print(f"\n💰 RESULTADOS:")
    if not trades.empty:
        final_balance = equity.iloc[-1]['equity']
        total_pnl = trades['pnl'].sum()
        roi = ((final_balance - 10000) / 10000) * 100

        print(f"   Balance final: ${final_balance:,.2f}")
        print(f"   PnL total: ${total_pnl:,.2f}")
        print(f"   ROI: {roi:.2f}%")
        print(f"   Total trades: {len(trades)}")

        # Verificar si se activó cash_mode
        cash_mode_trades = trades[trades['cash_mode'] == True]
        exit_to_cash_trades = trades[trades['reason'] == 'EXIT_TO_CASH']

        print(f"\n🔍 VERIFICACIÓN CASH MODE:")
        print(f"   Trades EXIT_TO_CASH: {len(exit_to_cash_trades)}")
        if len(exit_to_cash_trades) > 0:
            print(f"   ✅ Cash mode ACTIVADO correctamente")
            print(f"\n   Primer EXIT_TO_CASH:")
            first_exit = exit_to_cash_trades.iloc[0]
            print(f"   - Tiempo: {first_exit['exit_time']}")
            print(f"   - Precio: ${first_exit['exit_price']:,.2f}")
            print(f"   - PnL: ${first_exit['pnl']:.2f}")
        else:
            print(f"   ⚠️  Cash mode NO se activó (puede ser normal si no hubo caídas >8%)")

        # Mostrar razones de salida
        print(f"\n🚪 RAZONES DE SALIDA:")
        print(trades['reason'].value_counts().to_string())

        # Primeros trades
        print(f"\n📋 PRIMEROS 5 TRADES:")
        cols = ['entry_time', 'exit_time', 'entry_price', 'exit_price', 'pnl', 'reason']
        if 'cash_mode' in trades.columns:
            cols.append('cash_mode')
        print(trades[cols].head().to_string(index=False))

    else:
        print("   ⚠️  No se generaron trades")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Período MIXTO (bajista → alcista) para verificar re-entrada
print("\n" + "=" * 80)
print("📊 TEST 2: PERÍODO MIXTO (Bajista → Alcista)")
print("=" * 80)

# Usar período que incluye caída fuerte y recuperación
# 20000:23000 incluye la caída -13.59% y recuperación posterior
df_mixed = df.iloc[20000:23000].reset_index(drop=True)

print(f"\n📊 Datos del período:")
print(f"   {df_mixed['timestamp'].iloc[0]} → {df_mixed['timestamp'].iloc[-1]}")
print(f"   ${df_mixed['close'].iloc[0]:,.2f} → ${df_mixed['close'].iloc[-1]:,.2f}")
change_pct = ((df_mixed['close'].iloc[-1] / df_mixed['close'].iloc[0]) - 1) * 100
print(f"   Cambio: {change_pct:+.2f}%")

backtester2 = Backtester()

try:
    equity, trades = backtester2.run_backtest(
        df_mixed,
        risk_level="LOW",
        strategy_params=params
    )

    print(f"\n💰 RESULTADOS:")
    if not trades.empty:
        final_balance = equity.iloc[-1]['equity']
        total_pnl = trades['pnl'].sum()
        roi = ((final_balance - 10000) / 10000) * 100

        print(f"   Balance final: ${final_balance:,.2f}")
        print(f"   PnL total: ${total_pnl:,.2f}")
        print(f"   ROI: {roi:.2f}%")
        print(f"   Total trades: {len(trades)}")

        # Verificar ciclos de cash_mode
        exit_to_cash_trades = trades[trades['reason'] == 'EXIT_TO_CASH']
        print(f"\n🔍 VERIFICACIÓN CASH MODE:")
        print(f"   Total EXIT_TO_CASH: {len(exit_to_cash_trades)}")

        if len(exit_to_cash_trades) > 0:
            print(f"   ✅ Cash mode detectó condiciones bajistas")

            # Verificar si hubo re-entradas después
            for idx, exit_trade in exit_to_cash_trades.iterrows():
                exit_time = exit_trade['exit_time']
                # Buscar siguiente trade después del exit
                next_trades = trades[trades['entry_time'] > exit_time]
                if len(next_trades) > 0:
                    next_entry = next_trades.iloc[0]
                    time_diff = (next_entry['entry_time'] - exit_time).total_seconds() / 60
                    print(f"\n   📈 RE-ENTRADA después de EXIT_TO_CASH:")
                    print(f"   - Salida: {exit_time} @ ${exit_trade['exit_price']:,.2f}")
                    print(f"   - Re-entrada: {next_entry['entry_time']} @ ${next_entry['entry_price']:,.2f}")
                    print(f"   - Tiempo en cash: {time_diff:.0f} minutos")
                    break

        # Mostrar razones de salida
        print(f"\n🚪 RAZONES DE SALIDA:")
        print(trades['reason'].value_counts().to_string())

        # Guardar resultados
        trades.to_csv('backtest_cash_mode.csv', index=False)
        print(f"\n💾 Resultados guardados: backtest_cash_mode.csv")

    else:
        print("   ⚠️  No se generaron trades")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ TEST DE CASH MODE COMPLETADO")
print("=" * 80)
