#!/usr/bin/env python3
"""
Test exhaustivo del Strategy Miner con dataset grande (297k velas)
Objetivo: Verificar estabilidad del cluster bajo carga real
"""

import pandas as pd
from strategy_miner import StrategyMiner
import time
import ray
import os
import psutil
from datetime import datetime

print("\n" + "="*80)
print("STRATEGY MINER - TEST EXHAUSTIVO DE CARGA")
print("="*80 + "\n")

# Inicializar Ray
if not ray.is_initialized():
    ray.init(address='auto')
    print("Ray inicializado\n")

# Información del cluster
try:
    nodes = ray.nodes()
    print("CLUSTER INFORMATION:")
    print("-" * 80)
    total_cpus = 0
    for i, node in enumerate(nodes):
        if node.get('Alive', False):
            node_ip = node.get('NodeManagerAddress', 'Unknown')
            node_cpus = node.get('Resources', {}).get('CPU', 0)
            total_cpus += node_cpus
            print(f"  Node {i+1}: {node_ip} - {int(node_cpus)} CPUs")
    print(f"\n  Total CPUs disponibles: {int(total_cpus)}")
    print("-" * 80 + "\n")
except Exception as e:
    print(f"Warning: Could not get cluster info: {e}")
    total_cpus = 22

# 1. Cargar dataset GRANDE
print("CARGANDO DATASET...")
df = pd.read_csv("data/BTC-USD_ONE_MINUTE.csv")
print(f"Dataset: {len(df):,} velas")
print(f"Rango: {df.iloc[0, 0]} a {df.iloc[-1, 0]}")
print(f"Memoria dataset: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")

# 2. Configurar miner con parámetros EXIGENTES
POPULATION = 50
GENERATIONS = 20

print("CONFIGURACION DEL TEST:")
print(f"  Poblacion: {POPULATION}")
print(f"  Generaciones: {GENERATIONS}")
print(f"  Total evaluaciones: {POPULATION * GENERATIONS:,}")
print(f"  CPUs: {int(total_cpus)}")
print(f"  Velas por evaluacion: {len(df):,}")
print()

miner = StrategyMiner(
    df=df,
    population_size=POPULATION,
    generations=GENERATIONS,
    risk_level="LOW",
    force_local=False
)

# 3. Métricas de monitoreo
metrics = {
    'generation_times': [],
    'best_pnls': [],
    'cpu_usage': [],
    'memory_usage': [],
    'errors': []
}

# 4. Callback con monitoreo
def show_progress(msg_type, data):
    if msg_type == "START_GEN":
        gen = data
        print(f"\n{'='*80}")
        print(f"GENERACION {gen}/{GENERATIONS} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*80}")

        # Monitorear uso de recursos
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            metrics['cpu_usage'].append(cpu_percent)
            metrics['memory_usage'].append(mem.percent)
            print(f"  CPU: {cpu_percent:.1f}% | RAM: {mem.percent:.1f}% ({mem.used/1024**3:.1f}/{mem.total/1024**3:.1f} GB)")
        except:
            pass

    elif msg_type == "BEST_GEN":
        pnl = data.get('pnl', 0)
        trades = data.get('num_trades', 0)
        win_rate = data.get('win_rate', 0) * 100

        metrics['best_pnls'].append(pnl)

        emoji = "EXCELLENT" if pnl > 5000 else ("GOOD" if pnl > 1000 else ("OK" if pnl > 0 else "SEARCH"))
        print(f"  [{emoji}] PnL: ${pnl:>10,.2f} | Trades: {trades:>4d} | Win Rate: {win_rate:>5.1f}%")

    elif msg_type == "ERROR":
        metrics['errors'].append(data)
        print(f"  ERROR: {data}")

# 5. Ejecutar con manejo de errores
print("="*80)
print("INICIANDO TEST DE CARGA...")
print("="*80)

start_time = time.time()
best_genome = None
best_pnl = 0

try:
    best_genome, best_pnl = miner.run(progress_callback=show_progress)
    total_time = time.time() - start_time

    # 6. Resultados detallados
    print("\n" + "="*80)
    print("RESULTADOS FINALES")
    print("="*80 + "\n")

    print("METRICAS DE RENDIMIENTO:")
    print(f"  Tiempo total: {int(total_time)} segundos ({total_time/60:.1f} minutos)")
    print(f"  Tiempo promedio por generacion: {total_time/GENERATIONS:.1f} segundos")
    print(f"  Evaluaciones totales: {POPULATION * GENERATIONS:,}")
    print(f"  Evaluaciones por segundo: {(POPULATION * GENERATIONS)/total_time:.1f}")
    print()

    print("MEJOR ESTRATEGIA:")
    print(f"  PnL: ${best_pnl:,.2f}")
    if metrics['best_pnls']:
        print(f"  PnL maximo alcanzado: ${max(metrics['best_pnls']):,.2f}")
        print(f"  PnL minimo en generaciones: ${min(metrics['best_pnls']):,.2f}")
    print()

    if metrics['cpu_usage']:
        print("USO DE RECURSOS:")
        print(f"  CPU promedio: {sum(metrics['cpu_usage'])/len(metrics['cpu_usage']):.1f}%")
        print(f"  CPU maximo: {max(metrics['cpu_usage']):.1f}%")
        if metrics['memory_usage']:
            print(f"  RAM promedio: {sum(metrics['memory_usage'])/len(metrics['memory_usage']):.1f}%")
            print(f"  RAM maximo: {max(metrics['memory_usage']):.1f}%")
        print()

    if metrics['errors']:
        print(f"ERRORES ENCONTRADOS: {len(metrics['errors'])}")
        for err in metrics['errors'][:5]:
            print(f"  - {err}")
        print()
    else:
        print("ERRORES: Ninguno")
        print()

    # Verificar cluster
    print("ESTADO DEL CLUSTER:")
    try:
        nodes = ray.nodes()
        alive_nodes = sum(1 for n in nodes if n.get('Alive', False))
        print(f"  Nodos activos: {alive_nodes}/{len(nodes)}")

        for i, node in enumerate(nodes):
            if node.get('Alive', False):
                node_ip = node.get('NodeManagerAddress', 'Unknown')
                print(f"  Node {i+1} ({node_ip}): OK")
    except Exception as e:
        print(f"  Warning: Could not verify cluster: {e}")
    print()

    # Conclusión
    if best_pnl > 0 and not metrics['errors']:
        print("="*80)
        print("TEST EXITOSO")
        print("El cluster distribuido funciona correctamente bajo carga real")
        print("="*80)
    elif metrics['errors']:
        print("="*80)
        print("TEST COMPLETADO CON ERRORES")
        print(f"Se encontraron {len(metrics['errors'])} errores durante la ejecucion")
        print("="*80)
    else:
        print("="*80)
        print("TEST COMPLETADO")
        print("No se encontro estrategia con PnL positivo (puede ser normal)")
        print("="*80)

except KeyboardInterrupt:
    print("\n\nTest interrumpido por el usuario")
    total_time = time.time() - start_time
    print(f"Tiempo ejecutado: {int(total_time)} segundos")

except Exception as e:
    print(f"\n\nERROR FATAL: {e}")
    import traceback
    traceback.print_exc()
    total_time = time.time() - start_time
    print(f"\nTiempo antes del error: {int(total_time)} segundos")

print("\n" + "="*80 + "\n")
