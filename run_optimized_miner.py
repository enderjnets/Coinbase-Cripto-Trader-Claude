#!/usr/bin/env python3
"""
🎯 STRATEGY MINER - CONFIGURACIÓN OPTIMIZADA PARA RENTABILIDAD
==============================================================

Dataset: BTC-USD 5 minutos (4.7 meses - Training Set)
Objetivo: Encontrar estrategias RENTABLES
CPUs: 22 (MacBook Pro 12 + MacBook Air 10)
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import os

print("\n" + "="*80)
print("🎯 STRATEGY MINER - BÚSQUEDA DE RENTABILIDAD")
print("="*80 + "\n")

# Configurar entorno
os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'

# Inicializar Ray
if not ray.is_initialized():
    ray.init(address='auto', ignore_reinit_error=True)
    print("✅ Ray inicializado\n")

# Verificar cluster
try:
    nodes = ray.nodes()
    alive_nodes = [n for n in nodes if n.get('Alive')]
    total_cpus = sum(n.get('Resources', {}).get('CPU', 0) for n in alive_nodes)
    print(f"🖥️  Cluster Ray:")
    print(f"   • Nodos: {len(alive_nodes)}")
    print(f"   • CPUs: {int(total_cpus)}")
    for i, n in enumerate(alive_nodes, 1):
        ip = n.get('NodeManagerAddress', 'Unknown')
        cpus = int(n.get('Resources', {}).get('CPU', 0))
        print(f"   • Nodo {i}: {ip} ({cpus} CPUs)")
except Exception as e:
    print(f"⚠️  Error verificando cluster: {e}")
    total_cpus = 22

# Cargar datos de TRAINING
print(f"\n📊 Cargando Training Set...")
df = pd.read_csv("data/BTC-USD_FIVE_MINUTE_TRAINING.csv")
print(f"   ✅ {len(df):,} velas cargadas")
print(f"   📅 Periodo: {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")

# Configuración OPTIMIZADA para RENTABILIDAD
POPULATION = 1000  # Más individuos = mejor exploración
GENERATIONS = 200   # Más generaciones = mejor convergencia

print(f"\n⚙️  Configuración de Optimización:")
print(f"   • Población: {POPULATION:,} individuos")
print(f"   • Generaciones: {GENERATIONS}")
print(f"   • Total evaluaciones: {POPULATION * GENERATIONS:,} backtests")
print(f"   • Risk Level: MEDIUM")
print(f"   • CPUs: {int(total_cpus)}")

# Estimación de tiempo
backtests_per_second = total_cpus * 0.8  # ~0.8 backtests/seg/CPU
total_backtests = POPULATION * GENERATIONS
estimated_seconds = total_backtests / backtests_per_second
estimated_minutes = estimated_seconds / 60

print(f"\n⏱️  Tiempo estimado: {estimated_minutes:.0f} minutos ({estimated_minutes/60:.1f} horas)")

# Crear miner
miner = StrategyMiner(
    df=df,
    population_size=POPULATION,
    generations=GENERATIONS,
    risk_level="MEDIUM",
    force_local=False
)

# Callback para mostrar progreso
best_pnl_ever = -999999
generation_start_time = None

def show_progress(msg_type, data):
    global best_pnl_ever, generation_start_time

    if msg_type == "START_GEN":
        generation_start_time = time.time()
        print(f"\n🧬 Generación {data}/{GENERATIONS}")

    elif msg_type == "BEST_GEN":
        gen_time = time.time() - generation_start_time if generation_start_time else 0

        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100

        # Actualizar mejor PnL histórico
        if pnl > best_pnl_ever:
            best_pnl_ever = pnl
            emoji = "🔥🔥🔥" if pnl > 5000 else ("🔥" if pnl > 1000 else "✅")
        else:
            emoji = "⏳"

        print(f"   {emoji} PnL: ${pnl:>10,.2f} | Trades: {trades:>4d} | Win: {win_rate:>5.1f}% | {gen_time:.1f}s")

        # Alertas de progreso
        if pnl > 0:
            print(f"   💰 ¡PRIMERA ESTRATEGIA RENTABLE! PnL: ${pnl:,.2f}")
        if pnl > 1000:
            print(f"   🎯 ¡OBJETIVO ALCANZADO! PnL > $1000")
        if pnl > 5000:
            print(f"   🚀 ¡ESTRATEGIA EXCEPCIONAL! PnL > $5000")

# Ejecutar
print("\n" + "="*80)
print("🚀 INICIANDO EVOLUCIÓN...")
print("="*80)

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# Resultados
print("\n" + "="*80)
print("🏆 RESULTADOS FINALES")
print("="*80 + "\n")

print(f"💰 Mejor PnL: ${best_pnl:,.2f}")
print(f"⏱️  Tiempo total: {int(total_time/60)} minutos ({total_time/60/60:.1f} horas)")
print(f"⚡ Velocidad: {(POPULATION * GENERATIONS) / total_time:.1f} backtests/segundo")

if best_pnl > 0:
    print(f"\n✅ ¡ÉXITO! Estrategia RENTABLE encontrada")
    print(f"\n📋 Mejor Genoma:")
    import json
    print(json.dumps(best_genome, indent=2))

    # Guardar resultado
    result_file = f"best_strategy_pnl_{best_pnl:.2f}.json"
    with open(result_file, 'w') as f:
        json.dump({
            'genome': best_genome,
            'pnl': best_pnl,
            'config': {
                'population': POPULATION,
                'generations': GENERATIONS,
                'dataset': 'BTC-USD_FIVE_MINUTE_TRAINING.csv',
                'period': f"{df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}"
            }
        }, f, indent=2)
    print(f"\n💾 Estrategia guardada en: {result_file}")

elif best_pnl > -500:
    print(f"\n⚠️  Pérdida moderada. Considera:")
    print(f"   • Aumentar generaciones a 300+")
    print(f"   • Probar con risk level HIGH")
    print(f"   • Usar dataset de timeframe diferente")
else:
    print(f"\n❌ No se encontró estrategia rentable")
    print(f"   Mejor resultado: ${best_pnl:,.2f}")

print("\n" + "="*80 + "\n")

# Shutdown Ray
ray.shutdown()
