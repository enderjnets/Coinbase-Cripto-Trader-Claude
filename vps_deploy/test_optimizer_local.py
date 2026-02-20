#!/usr/bin/env python3
"""
Test simple del optimizer en modo LOCAL (sin cluster)
"""
import pandas as pd
import os
import sys

# Detener cualquier cluster Ray existente
import ray
if ray.is_initialized():
    ray.shutdown()

def test_local_optimizer():
    print("=" * 60)
    print("TEST OPTIMIZER LOCAL (sin cluster distribuido)")
    print("=" * 60)

    from optimizer import GridOptimizer

    # Cargar datos
    data_file = "data/BTC-USD_FIVE_MINUTE.csv"
    if not os.path.exists(data_file):
        print(f"❌ No se encontró {data_file}")
        print("Primero descarga datos usando el Backtester en la interfaz")
        return False

    print(f"✅ Cargando datos...")
    df = pd.read_csv(data_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Usar solo últimos 500 candles para prueba rápida
    df = df.tail(500).copy()
    print(f"✅ Datos cargados: {len(df)} candles")

    # Grid pequeño para prueba rápida
    param_ranges = {
        'resistance_period': [20, 30],  # 2 valores
        'rsi_period': [14],              # 1 valor
        'sl_multiplier': [1.5],          # 1 valor
        'tp_multiplier': [3.0],          # 1 valor
        'risk_level': ['LOW']            # 1 valor
    }

    print(f"\n📊 Grid: 2 × 1 × 1 × 1 × 1 = 2 combinaciones")
    print("\n" + "=" * 60)
    print("INICIANDO OPTIMIZACIÓN")
    print("=" * 60 + "\n")

    optimizer = GridOptimizer()

    try:
        results = optimizer.optimize(
            df,
            param_ranges,
            risk_level="LOW"
        )

        print("\n" + "=" * 60)
        print("RESULTADOS")
        print("=" * 60)

        if not results.empty:
            print(f"\n✅ {len(results)} configuraciones evaluadas")
            print("\nTop configuración:")
            print(results.head(1).to_string())
            return True
        else:
            print("⚠️  No se generaron resultados")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_local_optimizer()

    print("\n" + "=" * 60)
    if success:
        print("✅ TEST EXITOSO")
        sys.exit(0)
    else:
        print("❌ TEST FALLIDO")
        sys.exit(1)
