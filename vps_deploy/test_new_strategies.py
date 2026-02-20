"""
Test de las nuevas estrategias híbridas
Ejecuta backtest completo y muestra resultados
"""

import pandas as pd
import sys
from datetime import datetime
from backtester import Backtester
from strategy import Strategy

print("=" * 80)
print("🚀 TESTING NUEVAS ESTRATEGIAS HÍBRIDAS (Grid Trading + Momentum Scalping)")
print("=" * 80)

# Cargar datos existentes
print("\n📊 Cargando datos de BTC-USD (5 minutos)...")
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')

# Convertir timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"✅ Datos cargados: {len(df)} velas")
print(f"   Período: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"   Precio inicial: ${df['close'].iloc[0]:.2f}")
print(f"   Precio final: ${df['close'].iloc[-1]:.2f}")

# Inicializar backtester
print("\n🔧 Inicializando backtester con estrategia híbrida...")
backtester = Backtester()

# Ejecutar backtest con las nuevas estrategias
print("\n⚡ Ejecutando simulación...")
print("   (Esto puede tomar 1-2 minutos...)\n")

try:
    equity, trades = backtester.run_backtest(
        df,
        risk_level="LOW",  # Usar nivel LOW (más conservador)
        strategy_params=None  # Usar parámetros default
    )

    print("\n" + "=" * 80)
    print("📈 RESULTADOS DEL BACKTEST")
    print("=" * 80)

    if not trades.empty:
        # Métricas generales
        total_trades = len(trades)
        winning_trades = len(trades[trades['pnl'] > 0])
        losing_trades = len(trades[trades['pnl'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        total_pnl = trades['pnl'].sum()
        avg_win = trades[trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades[trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0

        final_balance = equity.iloc[-1]['equity'] if not equity.empty else 10000
        roi = ((final_balance - 10000) / 10000) * 100

        print(f"\n💰 RENDIMIENTO:")
        print(f"   Balance inicial:  $10,000.00")
        print(f"   Balance final:    ${final_balance:,.2f}")
        print(f"   PnL total:        ${total_pnl:,.2f}")
        print(f"   ROI:              {roi:.2f}%")

        print(f"\n📊 ESTADÍSTICAS DE TRADES:")
        print(f"   Total trades:     {total_trades}")
        print(f"   Trades ganadores: {winning_trades} ({win_rate:.1f}%)")
        print(f"   Trades perdedores: {losing_trades}")
        print(f"   Ganancia promedio: ${avg_win:.2f}")
        print(f"   Pérdida promedio:  ${avg_loss:.2f}")

        if avg_loss != 0:
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 else 999
            print(f"   Profit Factor:     {profit_factor:.2f}")

        # Análisis de estrategias usadas
        print(f"\n🎯 ANÁLISIS DE ESTRATEGIAS:")

        # Contar trades por estrategia (si está en reason)
        grid_trades = trades[trades['entry_reason'].str.contains('GRID', na=False)]
        momentum_trades = trades[trades['entry_reason'].str.contains('MOMENTUM', na=False)]
        ranging_trades = trades[trades['entry_reason'].str.contains('RANGING', na=False)]
        trending_trades = trades[trades['entry_reason'].str.contains('TRENDING', na=False)]

        print(f"   RANGING (Grid):    {len(ranging_trades)} trades")
        print(f"   TRENDING (Momentum): {len(trending_trades)} trades")

        if len(ranging_trades) > 0:
            ranging_pnl = ranging_trades['pnl'].sum()
            ranging_wr = len(ranging_trades[ranging_trades['pnl'] > 0]) / len(ranging_trades) * 100
            print(f"      → PnL Grid: ${ranging_pnl:.2f} | WR: {ranging_wr:.1f}%")

        if len(trending_trades) > 0:
            trending_pnl = trending_trades['pnl'].sum()
            trending_wr = len(trending_trades[trending_trades['pnl'] > 0]) / len(trending_trades) * 100
            print(f"      → PnL Momentum: ${trending_pnl:.2f} | WR: {trending_wr:.1f}%")

        # Mejores y peores trades
        print(f"\n🏆 MEJOR TRADE:")
        best_trade = trades.loc[trades['pnl'].idxmax()]
        print(f"   PnL: ${best_trade['pnl']:.2f}")
        print(f"   Entry: ${best_trade['entry_price']:.2f}")
        print(f"   Exit: ${best_trade['exit_price']:.2f}")
        print(f"   Razón: {best_trade['entry_reason'][:60]}")

        print(f"\n📉 PEOR TRADE:")
        worst_trade = trades.loc[trades['pnl'].idxmin()]
        print(f"   PnL: ${worst_trade['pnl']:.2f}")
        print(f"   Entry: ${worst_trade['entry_price']:.2f}")
        print(f"   Exit: ${worst_trade['exit_price']:.2f}")
        print(f"   Razón salida: {worst_trade['exit_reason']}")

        # Tabla resumen
        print(f"\n📋 PRIMEROS 10 TRADES:")
        print(trades[['entry_time', 'entry_price', 'exit_price', 'pnl', 'exit_reason']].head(10).to_string(index=False))

        # Guardar resultados
        trades.to_csv('backtest_results_new_strategies.csv', index=False)
        equity.to_csv('backtest_equity_new_strategies.csv', index=False)
        print(f"\n💾 Resultados guardados en:")
        print(f"   - backtest_results_new_strategies.csv")
        print(f"   - backtest_equity_new_strategies.csv")

    else:
        print("\n⚠️  No se generaron trades durante el backtest")
        print("   Posibles razones:")
        print("   - Período de datos muy corto")
        print("   - Condiciones de mercado no cumplieron criterios")
        print("   - Parámetros demasiado restrictivos")

except Exception as e:
    print(f"\n❌ ERROR durante el backtest:")
    print(f"   {str(e)}")
    import traceback
    print("\n📋 Traceback completo:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ Test completado")
print("=" * 80)
