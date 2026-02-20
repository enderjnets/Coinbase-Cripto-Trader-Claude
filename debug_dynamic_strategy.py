#!/usr/bin/env python3
"""
Debug detallado de por qué DynamicStrategy no genera trades
"""
import pandas as pd
from dynamic_strategy import DynamicStrategy
from backtester import Backtester

print("=" * 80)
print("🔍 DEBUG: ¿Por qué DynamicStrategy no genera trades?")
print("=" * 80)

# Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"\n📊 Dataset: {len(df)} velas")

# Crear un genoma simple que DEBERÍA generar trades
simple_genome = {
    "entry_rules": [
        # BUY cuando precio < SMA(50) - esto debería pasar varias veces
        {"left": {"field": "close"}, "op": "<", "right": {"indicator": "SMA", "period": 50}}
    ],
    "params": {
        "sl_pct": 0.02,  # 2% SL
        "tp_pct": 0.04   # 4% TP
    }
}

print("\n🧬 Genoma de prueba (super simple):")
print(f"   - Regla: Precio < SMA(50)")
print(f"   - SL: 2%")
print(f"   - TP: 4%")

# Crear estrategia
strat = DynamicStrategy(simple_genome)

# Test 1: ¿Se calculan los indicadores?
print("\n[TEST 1] Verificando cálculo de indicadores...")
df_prepared = strat.prepare_data(df.copy())

if 'SMA_50' in df_prepared.columns:
    print("   ✅ SMA_50 calculado")
    print(f"   - Valores NaN: {df_prepared['SMA_50'].isna().sum()}")
    print(f"   - Primer valor válido: {df_prepared['SMA_50'].dropna().iloc[0]:.2f}")
    print(f"   - Último valor: {df_prepared['SMA_50'].iloc[-1]:.2f}")
else:
    print("   ❌ SMA_50 NO calculado")
    print(f"   - Columnas disponibles: {df_prepared.columns.tolist()}")

# Test 2: ¿La regla se evalúa correctamente?
print("\n[TEST 2] Evaluando regla en varias velas...")

valid_df = df_prepared.dropna()  # Skip NaN rows
signals_generated = 0

for i in range(100, min(200, len(valid_df))):
    window = valid_df.iloc[i-100:i+1].reset_index(drop=True)
    result = strat.get_signal(window, len(window)-1, risk_level="LOW")

    if result and result.get('signal') == 'BUY':
        signals_generated += 1
        if signals_generated == 1:  # Print first signal details
            row = window.iloc[-1]
            print(f"\n   ✅ Primera señal encontrada en vela {i}:")
            print(f"      - Precio: ${row['close']:.2f}")
            print(f"      - SMA(50): ${row.get('SMA_50', 0):.2f}")
            print(f"      - Condición: {row['close']:.2f} < {row.get('SMA_50', 0):.2f} = {row['close'] < row.get('SMA_50', 0)}")

print(f"\n   📊 Señales generadas en 100 velas: {signals_generated}")

if signals_generated == 0:
    print("\n   ❌ PROBLEMA: No se generan señales")
    print("   Verificando por qué...")

    # Debug: ver qué está pasando con la comparación
    test_row = valid_df.iloc[150]
    print(f"\n   Ejemplo de vela (índice 150):")
    print(f"      - Precio: ${test_row['close']:.2f}")
    print(f"      - SMA(50): ${test_row.get('SMA_50', 'MISSING')}")

    # Intentar evaluar manualmente
    val_close = test_row['close']
    val_sma = test_row.get('SMA_50', 0)

    print(f"      - val_close < val_sma? {val_close} < {val_sma} = {val_close < val_sma}")

# Test 3: Backtest completo
print("\n[TEST 3] Ejecutando backtest completo...")

bt = Backtester()
bt.strategy = strat

# Normalizar columnas si es necesario
if 'timestamp' not in df.columns:
    if 'time' in df.columns:
        df = df.rename(columns={'time': 'timestamp'})
    df['timestamp'] = pd.to_datetime(df['timestamp'])

equity, trades = bt.run_backtest(df, risk_level="LOW", initial_balance=10000)

print(f"\n   📊 Resultados del Backtest:")
print(f"      - Total trades: {len(trades)}")

if len(trades) > 0:
    print(f"      - PnL total: ${trades['pnl'].sum():.2f}")
    print(f"      - Win rate: {len(trades[trades['pnl'] > 0]) / len(trades) * 100:.1f}%")
    print("\n   ✅ Trades generados exitosamente!")
    print("\n   Primeros 5 trades:")
    print(trades.head())
else:
    print("\n   ❌ NO SE GENERARON TRADES en el backtest")
    print("\n   Posibles causas:")
    print("      1. prepare_data() no se está llamando")
    print("      2. Los indicadores no están en el DataFrame pasado a get_signal()")
    print("      3. La integración Backtester <-> DynamicStrategy está rota")

print("\n" + "=" * 80)
print("✅ Debug completado")
print("=" * 80)
