#!/usr/bin/env python3
"""
Strategy Miner - EJECUTIÓN CON BUG CORREGIDO
Ahora debería encontrar estrategias rentables
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import sys

print("\n" + "="*80)
print("🧬 STRATEGY MINER - EJECUCIÓN CORREGIDA (22 CPUs)")
print("="*80 + "\n")

# 1. Cargar datos
print("📊 Cargando dataset...")
df = pd.read_csv("data/BTC-USD_ONE_HOUR_FULL.csv")
print(f"   ✅ Dataset: {len(df):,} velas\n")

# 2. Configurar miner con población reducida para test rápido
print("⚙️  Configuración:")
print(f"   • Población: 50 (reducida para test rápido)")
print(f"   • Generaciones: 30")
print(f"   • Risk Level: LOW")
print(f"   • CPUs: 22 (distribuidos)")
print(f"   • Tiempo estimado: ~15 minutos\n")

miner = StrategyMiner(
    df=df,
    population_size=50,   # Reducido para test
    generations=30,       # Reducido para test
    risk_level="LOW",
    force_local=False  # ¡USAR RAY CON 22 CPUs!
)

# 3. Callback de progreso
start_time = time.time()
generation_times = []
gen_start_time = time.time()
best_pnl_overall = float('-inf')

def show_progress(msg_type, data):
    global gen_start_time, generation_times, best_pnl_overall

    if msg_type == "START_GEN":
        gen = data
        elapsed = time.time() - start_time

        # Estimar tiempo restante
        if generation_times:
            avg_time = sum(generation_times) / len(generation_times)
            remaining_gens = 30 - gen
            eta = avg_time * remaining_gens
            eta_min = int(eta / 60)
            eta_sec = int(eta % 60)
            print(f"\n🧬 Gen {gen:2d}/30 | Transcurrido: {int(elapsed/60):2d}m {int(elapsed%60):2d}s | ETA: {eta_min:2d}m {eta_sec:2d}s", flush=True)
        else:
            print(f"\n🧬 Gen {gen:2d}/30 | Transcurrido: {int(elapsed/60):2d}m {int(elapsed%60):2d}s", flush=True)

        gen_start_time = time.time()

    elif msg_type == "BEST_GEN":
        gen_time = time.time() - gen_start_time
        generation_times.append(gen_time)

        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100

        # Actualizar mejor PnL
        if pnl > best_pnl_overall:
            best_pnl_overall = pnl

        # Indicador de progreso
        if pnl > 3000:
            emoji = "🔥"
        elif pnl > 1000:
            emoji = "💎"
        elif pnl > 0:
            emoji = "✅"
        else:
            emoji = "⏳"

        print(f"   {emoji} PnL: ${pnl:>8,.2f} | Trades: {trades:>3d} | Win: {win_rate:>5.1f}% | {gen_time:>4.1f}s | Mejor: ${best_pnl_overall:,.2f}", flush=True)

# 4. Ejecutar
print("="*80)
print("⚡ INICIANDO OPTIMIZACIÓN...")
print("="*80)
sys.stdout.flush()

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# 5. Resultados
print("\n" + "="*80)
print(f"🏆 RESULTADO FINAL")
print("="*80 + "\n")

print(f"💰 MEJOR PnL: ${best_pnl:,.2f}")
print(f"⏱️  Tiempo total: {int(total_time/60)} min {int(total_time%60)} seg\n")

if best_pnl > 3000:
    print("🔥 ¡ESTRATEGIA EXCELENTE! PnL > $3000")
elif best_pnl > 1000:
    print("💎 ¡ESTRATEGIA RENTABLE! PnL > $1000")
elif best_pnl > 0:
    print("✅ Ganancia positiva")
else:
    print("⚠️  PnL negativo - El algoritmo genético aún está evolucionando")
    print("     Considera ejecutar con más generaciones (50-100)")

print(f"\n📋 Genoma ganador:")
params = best_genome.get('params', {})
print(f"   • Stop Loss: {params.get('sl_pct', 0)*100:.1f}%")
print(f"   • Take Profit: {params.get('tp_pct', 0)*100:.1f}%")
print(f"   • Reglas de entrada: {len(best_genome.get('entry_rules', []))}")
print(f"   • Reglas de salida: {len(best_genome.get('exit_rules', []))}")

print(f"\n📜 Reglas de entrada:")
for i, rule in enumerate(best_genome.get('entry_rules', []), 1):
    print(f"   {i}. {rule}")

if best_genome.get('exit_rules'):
    print(f"\n📜 Reglas de salida:")
    for i, rule in enumerate(best_genome.get('exit_rules', []), 1):
        print(f"   {i}. {rule}")

# 6. Guardar resultado
print(f"\n💾 Guardando resultado...")
import json
result = {
    'pnl': best_pnl,
    'genome': best_genome,
    'total_time_seconds': total_time,
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'config': {
        'population_size': 50,
        'generations': 30,
        'cpus': 22
    }
}

with open('last_miner_result_fixed.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f"   ✅ Guardado en: last_miner_result_fixed.json")

print("\n" + "="*80 + "\n")
