#!/usr/bin/env python3
"""
Test simple para diagnosticar por qué no se generan trades
"""

import pandas as pd
from dynamic_strategy import DynamicStrategy

print("\n" + "="*80)
print("🔍 DIAGNÓSTICO SIMPLE: DynamicStrategy")
print("="*80 + "\n")

# 1. Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df):,} velas\n")

# 2. Crear estrategia
genome = {
    "entry_rules": [
        {
            "left": {"field": "close"},
            "op": "<",
            "right": {"indicator": "SMA", "period": 200}
        }
    ],
    "exit_rules": [],
    "params": {
        "sl_pct": 0.046,
        "tp_pct": 0.040
    }
}

print("📋 Estrategia:")
print("   Regla: close < SMA(200)")
print("   SL: 4.6%, TP: 4.0%\n")

strategy = DynamicStrategy(genome)

# 3. Preparar datos (calcular indicadores)
print("⚙️  Preparando indicadores...")
df_prepared = strategy.prepare_data(df)

# Verificar que SMA_200 fue calculado
if 'SMA_200' in df_prepared.columns:
    print(f"   ✅ SMA_200 calculado")
    valid_sma = df_prepared['SMA_200'].notna().sum()
    print(f"   Valores válidos: {valid_sma}/{len(df_prepared)}")
else:
    print("   ❌ SMA_200 NO fue calculado")
    print(f"   Columnas disponibles: {list(df_prepared.columns)}")
    exit(1)

# 4. Verificar condición
print("\n📊 Análisis de condición:")
condition = df_prepared['close'] < df_prepared['SMA_200']
condition_valid = condition & df_prepared['SMA_200'].notna()

print(f"   Velas que cumplen 'close < SMA(200)': {condition_valid.sum()}/{len(df_prepared)}")

if condition_valid.sum() == 0:
    print("   ❌ NINGUNA vela cumple la condición!")
    print("\n📈 Verificando precios vs SMA:")
    sample = df_prepared[df_prepared['SMA_200'].notna()].head(10)[['close', 'SMA_200']]
    print(sample)
else:
    first_match = condition_valid.idxmax()
    print(f"   ✅ Primera vela que cumple: índice {first_match}")

# 5. Probar get_signal en varias velas
print("\n🧪 Probando get_signal():")

test_indices = [250, 500, 1000, 2000, 4000]

signals_found = 0
for idx in test_indices:
    if idx >= len(df_prepared):
        continue

    # Crear window (backtester pasa una ventana)
    window = df_prepared.iloc[max(0, idx-100):idx+1].copy()
    window_reset = window.reset_index(drop=True)

    result = strategy.get_signal(window_reset, len(window_reset) - 1)

    signal = result.get('signal')
    if signal:
        signals_found += 1
        print(f"   Índice {idx}: {signal} ✅")
        print(f"      close: {df_prepared.iloc[idx]['close']:.2f}")
        print(f"      SMA_200: {df_prepared.iloc[idx]['SMA_200']:.2f}")
        print(f"      close < SMA: {df_prepared.iloc[idx]['close'] < df_prepared.iloc[idx]['SMA_200']}")
    else:
        # Mostrar por qué no generó señal
        close_val = df_prepared.iloc[idx]['close']
        sma_val = df_prepared.iloc[idx]['SMA_200']
        print(f"   Índice {idx}: NO SIGNAL ❌")
        print(f"      close: {close_val:.2f}, SMA_200: {sma_val:.2f}, close < SMA: {close_val < sma_val}")

print(f"\n📊 Resumen:")
print(f"   Señales encontradas: {signals_found}/{len(test_indices)}")

if signals_found == 0:
    print("\n❌ PROBLEMA CONFIRMADO: get_signal() NO genera señales")
    print("\n🔍 Debugging paso a paso en índice 250:")

    idx = 250
    window = df_prepared.iloc[max(0, idx-100):idx+1].copy()
    window_reset = window.reset_index(drop=True)

    row = window_reset.iloc[-1]
    print(f"\n   Row data:")
    print(f"   - close: {row['close']}")
    print(f"   - SMA_200: {row.get('SMA_200', 'MISSING')}")

    # Test manual de _get_value
    left_val = strategy._get_value(row, {"field": "close"})
    right_val = strategy._get_value(row, {"indicator": "SMA", "period": 200})

    print(f"\n   _get_value results:")
    print(f"   - left (close): {left_val}")
    print(f"   - right (SMA_200): {right_val}")

    comparison = strategy._compare(left_val, right_val, "<")
    print(f"\n   _compare({left_val}, {right_val}, '<'): {comparison}")

print("\n" + "="*80 + "\n")
