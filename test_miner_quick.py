#!/usr/bin/env python3
"""
Test rápido del Strategy Miner corregido (10 población, 5 generaciones)
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray

print("\n" + "="*80)
print("🧬 STRATEGY MINER - TEST RÁPIDO CON BUG CORREGIDO")
print("="*80 + "\n")

# Inicializar Ray
if not ray.is_initialized():
    ray.init(address='auto')
    print("✅ Ray inicializado\n")

# 1. Cargar datos (usando dataset más grande para mejor testing)
df = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")
print(f"📊 Dataset: {len(df):,} velas\n")

# 2. Configurar miner (MUY PEQUEÑO para test rápido)
# Obtener CPUs de manera segura
try:
    nodes = ray.nodes()
    total_cpus = 0
    for node in nodes:
        if node.get('Alive', False) and 'Resources' in node:
            total_cpus += node['Resources'].get('CPU', 0)
    if total_cpus == 0:
        total_cpus = 22  # Fallback si no se puede detectar
except Exception:
    total_cpus = 22  # Fallback

print("⚙️  Configuración TEST:")
print(f"   • Población: 10")
print(f"   • Generaciones: 5")
print(f"   • CPUs: {int(total_cpus)}\n")

miner = StrategyMiner(
    df=df,
    population_size=10,
    generations=5,
    risk_level="LOW",
    force_local=False
)

# 3. Callback
def show_progress(msg_type, data):
    if msg_type == "START_GEN":
        print(f"\n🧬 Gen {data}/5")

    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100

        emoji = "🔥" if pnl > 1000 else ("✅" if pnl > 0 else "⏳")
        print(f"   {emoji} PnL: ${pnl:>8,.2f} | Trades: {trades:>3d} | Win: {win_rate:>5.1f}%")

# 4. Ejecutar
print("="*80)
print("⚡ INICIANDO...")
print("="*80)

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# 5. Resultados
print("\n" + "="*80)
print(f"🏆 RESULTADO")
print("="*80 + "\n")

print(f"💰 Mejor PnL: ${best_pnl:,.2f}")
print(f"⏱️  Tiempo: {int(total_time)} segundos")

if best_pnl > 0:
    print(f"\n✅ ¡FUNCIONA! El algoritmo encontró estrategia con PnL positivo")
else:
    print(f"\n⚠️  PnL negativo (normal en test pequeño)")

print("\n" + "="*80 + "\n")
