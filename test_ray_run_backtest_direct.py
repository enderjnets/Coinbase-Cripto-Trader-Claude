#!/usr/bin/env python3
"""
Test que llama a run_backtest_task directamente vía Ray
para verificar si hay problema de serialización
"""

import ray
import pandas as pd
from optimizer import run_backtest_task

# Inicializar Ray
if not ray.is_initialized():
    ray.init(address='auto')

print("=" * 80)
print("🧪 TEST: run_backtest_task directo vía Ray")
print("=" * 80)
print()

# Cargar datos
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"📊 Dataset: {len(df)} velas\n")

# Crear genome
genome = {
    "entry_rules": [
        {
            "left": {"field": "close"},
            "op": "<",
            "right": {"indicator": "SMA", "period": 200}
        }
    ],
    "params": {
        "sl_pct": 0.046,
        "tp_pct": 0.040
    }
}

print("📋 Genome:")
print(f"   Rules: {genome['entry_rules'][0]}")
print(f"   SL: {genome['params']['sl_pct']*100}%, TP: {genome['params']['tp_pct']*100}%\n")

# Convertir DF a payload compatible (usamos datos directos)
data_payload = df.copy()

print("🚀 Ejecutando run_backtest_task.remote()...\n")

# Llamar a run_backtest_task via Ray
result_ref = run_backtest_task.remote(
    data_payload=data_payload,
    risk_level="LOW",
    params=genome,
    strategy_code="DYNAMIC"
)

# Esperar resultado
result = ray.get(result_ref)

print("=" * 80)
print("📊 RESULTADO")
print("=" * 80)

if 'error' in result:
    print(f"❌ ERROR: {result['error']}")
else:
    metrics = result.get('metrics', {})
    trades = metrics.get('Total Trades', 0)
    pnl = metrics.get('Total PnL', 0)
    win_rate = metrics.get('Win Rate %', 0)

    print(f"✅ Backtest completado")
    print(f"   Trades: {trades}")
    print(f"   PnL: ${pnl:.2f}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print()

    if trades == 0:
        print("❌ PROBLEMA: 0 trades generados (igual que strategy_miner)")
        print("   Esto confirma que el problema está en run_backtest_task con Ray")
    else:
        print("✅ SUCCESS: Trades generados correctamente")
        print("   El problema entonces está en otro lado (strategy_miner?)")

print("\n" + "=" * 80)
