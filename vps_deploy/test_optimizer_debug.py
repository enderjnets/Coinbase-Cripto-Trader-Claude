#!/usr/bin/env python3
"""
Test debug del optimizer - sin Streamlit
"""
import pandas as pd
import os
import sys

print("=" * 60)
print("TEST DEBUG - OPTIMIZER")
print("=" * 60)

# Shutdown any existing Ray
import ray
if ray.is_initialized():
    print("Cerrando Ray existente...")
    ray.shutdown()

# Cargar datos
data_file = "data/BTC-USD_FIVE_MINUTE.csv"
if not os.path.exists(data_file):
    print(f"❌ No se encontró {data_file}")
    sys.exit(1)

print(f"✅ Cargando datos desde {data_file}...")
df = pd.read_csv(data_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Usar SOLO 100 candles para test rápido
df = df.tail(100).copy()
print(f"✅ Datos cargados: {len(df)} candles (test pequeño)")

# Grid MUY pequeño - solo 2 combinaciones
param_ranges = {
    'resistance_period': [20, 30],  # 2 valores
    'rsi_period': [14],              # 1 valor
    'sl_multiplier': [1.5],          # 1 valor
    'tp_multiplier': [3.0],          # 1 valor
    'risk_level': ['LOW']            # 1 valor
}

print(f"\n📊 Grid: 2 combinaciones totales")
print(f"Parámetros: {param_ranges}")

# Test 1: Backtester directo (SIN Ray)
print("\n" + "=" * 60)
print("TEST 1: Backtester DIRECTO (sin Ray)")
print("=" * 60)

try:
    from backtester import Backtester
    bt = Backtester()

    test_params = {
        'resistance_period': 20,
        'rsi_period': 14,
        'sl_multiplier': 1.5,
        'tp_multiplier': 3.0
    }

    print(f"Ejecutando backtest con params: {test_params}")
    equity, trades = bt.run_backtest(df, risk_level='LOW', strategy_params=test_params)

    print(f"✅ Backtest completado")
    print(f"   - Trades: {len(trades)}")
    if len(trades) > 0:
        print(f"   - PnL: ${trades['pnl'].sum():.2f}")
        print(f"   - Balance final: ${trades['balance'].iloc[-1]:.2f}")
    else:
        print(f"   - No hubo trades")

    print("\n✅ TEST 1 EXITOSO - Backtester funciona directamente")
except Exception as e:
    print(f"\n❌ TEST 1 FALLÓ: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Optimizer con Ray (modo local)
print("\n" + "=" * 60)
print("TEST 2: GridOptimizer con Ray LOCAL")
print("=" * 60)

try:
    from optimizer import GridOptimizer

    optimizer = GridOptimizer()

    print("Iniciando optimización...")
    results = optimizer.optimize(
        df,
        param_ranges,
        risk_level="LOW"
    )

    print(f"\n✅ Optimización completada")
    print(f"   - Configuraciones evaluadas: {len(results)}")

    if not results.empty:
        print("\nMejor configuración:")
        print(results.head(1).to_string())
        print("\n✅ TEST 2 EXITOSO - Optimizer funciona")
    else:
        print("\n⚠️  TEST 2: No se generaron resultados")

except Exception as e:
    print(f"\n❌ TEST 2 FALLÓ: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TODOS LOS TESTS EXITOSOS")
print("=" * 60)
