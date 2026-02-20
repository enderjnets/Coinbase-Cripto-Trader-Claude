"""
Test rápido del optimizer con nuevos parámetros
"""

import pandas as pd
from optimizer import GridOptimizer
import sys

print("=" * 80)
print("🧪 TEST RÁPIDO DE OPTIMIZER")
print("=" * 80)

# Cargar datos
df = pd.read_csv('data/BTC-USD_FIVE_MINUTE.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Período alcista
df_test = df.iloc[16500:17500].reset_index(drop=True)

print(f"\n📊 Datos de prueba:")
print(f"   {df_test['timestamp'].iloc[0]} → {df_test['timestamp'].iloc[-1]}")
print(f"   {len(df_test)} velas")
change = ((df_test['close'].iloc[-1] / df_test['close'].iloc[0]) - 1) * 100
print(f"   Cambio: {change:+.2f}%")

# Rangos de parámetros reducidos para test rápido
param_ranges = {
    'grid_spacing_pct': [1.5, 2.0, 2.5],
    'min_move_pct': [2.0, 2.5, 3.0],
    'sl_multiplier': [2.0, 2.5, 3.0],
    'tp_multiplier': [5.0, 6.0, 7.0],
    'num_grids': [6, 8, 10],
}

print(f"\n🔧 Rangos de parámetros:")
for key, values in param_ranges.items():
    print(f"   {key}: {values}")

total_combinations = 1
for values in param_ranges.values():
    total_combinations *= len(values)
print(f"\n📊 Total combinaciones: {total_combinations}")

print("\n" + "=" * 80)
print("🚀 INICIANDO OPTIMIZACIÓN (Grid Search)")
print("=" * 80)

def progress_callback(progress_data):
    """Callback para mostrar progreso"""
    if isinstance(progress_data, float):
        # Nuevo formato: solo float
        pct = progress_data * 100
        print(f"   [...] {pct:.1f}%")
    elif isinstance(progress_data, dict):
        # Viejo formato (por si acaso)
        if progress_data['type'] == 'progress':
            current = progress_data['current']
            total = progress_data['total']
            pct = (current / total) * 100
            print(f"   [{current}/{total}] {pct:.1f}%")
        elif progress_data['type'] == 'best':
            print(f"   🏆 NUEVO MEJOR: ROI={progress_data['roi']:.2f}% Win={progress_data['win_rate']:.1f}%")

optimizer = GridOptimizer()

try:
    best_params, best_metrics = optimizer.optimize(
        df=df_test,
        param_ranges=param_ranges,
        risk_level='LOW',
        progress_callback=progress_callback
    )

    print("\n" + "=" * 80)
    print("✅ OPTIMIZACIÓN COMPLETADA")
    print("=" * 80)

    print(f"\n🏆 MEJORES PARÁMETROS:")
    for key, value in best_params.items():
        print(f"   {key}: {value}")

    print(f"\n📊 MÉTRICAS:")
    for key, value in best_metrics.items():
        if isinstance(value, (int, float)):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    print(f"\n✅ Optimizer funciona correctamente con cash_mode!")

except Exception as e:
    print(f"\n❌ Error en optimizer: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
