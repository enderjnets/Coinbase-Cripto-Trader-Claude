#!/usr/bin/env python3
"""
Test de distribución de carga con Population=100, Gen=10 (1000 backtests)
Verifica que ambos nodos procesan tareas equitativamente
"""
import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import os

print("\n" + "="*80)
print("📊 TEST DE DISTRIBUCIÓN DE CARGA - 1000 BACKTESTS")
print("="*80 + "\n")

# Configurar entorno
os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'

# Conectar al cluster
if not ray.is_initialized():
    ray.init(address='100.77.179.14:6379', ignore_reinit_error=True)

# Verificar cluster
nodes = ray.nodes()
alive_nodes = [n for n in nodes if n.get('Alive')]
total_cpus = sum(int(n.get('Resources', {}).get('CPU', 0)) for n in alive_nodes)

print(f"🖥️  Cluster:")
print(f"   • Nodos: {len(alive_nodes)}")
print(f"   • CPUs: {int(total_cpus)}")
for i, n in enumerate(alive_nodes, 1):
    ip = n.get('NodeManagerAddress', 'Unknown')
    cpus = int(n.get('Resources', {}).get('CPU', 0))
    print(f"   • Nodo {i}: {ip} ({cpus} CPUs)")

# Cargar datos (usar training set)
print(f"\n📊 Cargando datos...")
df = pd.read_csv("data/BTC-USD_FIVE_MINUTE_TRAINING.csv")
print(f"   ✅ {len(df):,} velas")

# Configuración de test
POPULATION = 100
GENERATIONS = 10

print(f"\n⚙️  Configuración:")
print(f"   • Población: {POPULATION}")
print(f"   • Generaciones: {GENERATIONS}")
print(f"   • Total backtests: {POPULATION * GENERATIONS:,}")

# Crear miner
miner = StrategyMiner(
    df=df,
    population_size=POPULATION,
    generations=GENERATIONS,
    risk_level="LOW",
    force_local=False
)

# Callback simple
generation_count = 0
def show_progress(msg_type, data):
    global generation_count
    if msg_type == "START_GEN":
        generation_count += 1
        print(f"\n🧬 Gen {generation_count}/{GENERATIONS}")
    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        print(f"   ⏳ Best: ${pnl:,.2f} | Trades: {trades}")

# Ejecutar
print("\n" + "="*80)
print("🚀 INICIANDO TEST...")
print("="*80)

start_time = time.time()
best_genome, best_pnl = miner.run(progress_callback=show_progress)
total_time = time.time() - start_time

# Resultados
print("\n" + "="*80)
print("📊 RESULTADOS")
print("="*80 + "\n")

print(f"💰 Mejor PnL: ${best_pnl:,.2f}")
print(f"⏱️  Tiempo: {int(total_time)} segundos ({total_time/60:.1f} minutos)")
print(f"⚡ Velocidad: {(POPULATION * GENERATIONS) / total_time:.1f} backtests/segundo")

print("\n💡 Para analizar distribución de tareas, revisar:")
print("   grep 'ip=100' /tmp/test_load_output.log | sort | uniq -c")

print("\n" + "="*80 + "\n")

ray.shutdown()
