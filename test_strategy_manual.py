#!/usr/bin/env python3
"""
Test manual de la estrategia generada para entender por qué da 0 trades
"""

import pandas as pd
from dynamic_strategy import DynamicStrategy
from backtester import Backtester

print("\n" + "="*80)
print("🔍 DIAGNÓSTICO: ¿Por qué 0 trades?")
print("="*80 + "\n")

# 1. Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df):,} velas\n")

# 2. Estrategia del miner
genome = {
    "entry_rules": [
        {
            "left": {"field": "close"},
            "op": "<",
            "right": {"indicator": "SMA", "period": 200}
        }
    ],
    "exit_rules": [],  # Sin reglas de salida
    "params": {
        "sl_pct": 0.046,
        "tp_pct": 0.040
    }
}

print("📋 Estrategia generada:")
print(f"   Regla: close < SMA(200)")
print(f"   SL: {genome['params']['sl_pct']*100:.1f}%")
print(f"   TP: {genome['params']['tp_pct']*100:.1f}%\n")

# 3. Crear estrategia
strategy = DynamicStrategy(genome)

# 4. Probar en primeras 500 velas
print("🧪 Test 1: Primeras 500 velas")
test_df = df.head(500).copy()

signals = []
for i in range(len(test_df)):
    row = test_df.iloc[i]
    signal = strategy.should_enter(test_df, i)
    if signal:
        signals.append((i, signal))

print(f"   Señales generadas: {len(signals)}")
if signals:
    print(f"   Primera señal en índice: {signals[0][0]}")
    print(f"   Señal: {signals[0][1]}")
else:
    print("   ❌ NO SE GENERÓ NINGUNA SEÑAL\n")

# 5. Verificar indicadores
print("\n🔬 Test 2: Verificar cálculo de indicadores")
strategy.prepare_indicators(test_df)

if 'SMA_200' in test_df.columns:
    print(f"   ✅ SMA_200 calculado")
    print(f"   Valores no-NaN: {test_df['SMA_200'].notna().sum()}/{len(test_df)}")

    # Contar cuántas velas cumplen la condición
    valid_rows = test_df['SMA_200'].notna()
    condition_met = (test_df['close'] < test_df['SMA_200']) & valid_rows

    print(f"   Velas que cumplen 'close < SMA(200)': {condition_met.sum()}")

    if condition_met.sum() > 0:
        print(f"   Primera vela que cumple: índice {condition_met.idxmax()}")
else:
    print("   ❌ SMA_200 NO fue calculado\n")

# 6. Test con backtester
print("\n🎯 Test 3: Ejecutar backtester completo")
bt = Backtester(
    df=test_df,
    strategy=strategy,
    initial_balance=10000,
    fee_pct=0.006
)

result = bt.run()

print(f"   Trades ejecutados: {result['num_trades']}")
print(f"   PnL: ${result['pnl']:.2f}")
print(f"   Señales BUY: {result.get('signals_generated', 'N/A')}")

if result['num_trades'] == 0:
    print("\n❌ PROBLEMA CONFIRMADO: Backtester no genera trades\n")

    # Verificar si hay señales en el log
    print("📋 Verificando método should_enter...")

    # Probar manualmente en índice 250 (después del warmup de SMA 200)
    test_idx = 250
    signal = strategy.should_enter(test_df, test_idx)

    print(f"   Índice {test_idx}:")
    print(f"   - close: {test_df.iloc[test_idx]['close']}")
    if 'SMA_200' in test_df.columns:
        print(f"   - SMA_200: {test_df.iloc[test_idx]['SMA_200']}")
        print(f"   - close < SMA_200: {test_df.iloc[test_idx]['close'] < test_df.iloc[test_idx]['SMA_200']}")
    print(f"   - Signal returned: {signal}")

print("\n" + "="*80 + "\n")
