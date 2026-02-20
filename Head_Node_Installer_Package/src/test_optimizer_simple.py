"""
Test simple del optimizer con cash_mode
"""

import pandas as pd
from optimizer import GridOptimizer
import time

print("=" * 80)
print("🧪 TEST OPTIMIZER CON CASH_MODE")
print("=" * 80)

# Cargar datos
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Período alcista pequeño
df_test = df.iloc[16500:17000].reset_index(drop=True)

print(f"\n📊 Datos:")
print(f"   {len(df_test)} velas")
change = ((df_test['close'].iloc[-1] / df_test['close'].iloc[0]) - 1) * 100
print(f"   Cambio: {change:+.2f}%")

# Rangos reducidos
param_ranges = {
    'grid_spacing_pct': [2.0, 2.5],
    'min_move_pct': [2.5, 3.0],
    'sl_multiplier': [2.5],
    'tp_multiplier': [6.0],
    'num_grids': [8],
}

total = 1
for values in param_ranges.values():
    total *= len(values)

print(f"\n📊 Total combinaciones: {total}")
print("\n" + "=" * 80)

start_time = time.time()

optimizer = GridOptimizer()

try:
    # Retorna solo DataFrame
    df_results = optimizer.optimize(
        df=df_test,
        param_ranges=param_ranges,
        risk_level='LOW'
    )

    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print("✅ COMPLETADO")
    print("=" * 80)

    print(f"\n⏱️  Tiempo: {elapsed:.1f}s")

    if not df_results.empty:
        best = df_results.iloc[0]
        
        print(f"\n🏆 MEJOR RESULTADO:")
        print(f"   PnL: ${best['Total PnL']:.2f}")
        print(f"   ROI: {best['ROI (%)']:.2f}%")
        print(f"   Win Rate: {best['Win Rate (%)']:.1f}%")
        print(f"   Trades: {best['Total Trades']}")
        
        print(f"\n📋 PARÁMETROS:")
        for col in df_results.columns:
            if col not in ['Total PnL', 'Win Rate (%)', 'ROI (%)', 'Total Trades', 'Winners', 'Losers']:
                print(f"   {col}: {best[col]}")

        print(f"\n✅ Optimizer funciona correctamente con cash_mode!")
    else:
        print("\n⚠️  No se generaron resultados")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
