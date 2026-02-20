#!/usr/bin/env python3
"""
Test de carga EXTREMA del Strategy Miner
200+ tareas con dataset de 297k velas para verificar estabilidad bajo estrés máximo
"""

import pandas as pd
import ray
import time
import psutil
from datetime import datetime
from optimizer import run_backtest_task

print("\n" + "="*80)
print("STRATEGY MINER - TEST DE CARGA EXTREMA")
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
    total_cpus = 10

# Cargar dataset GRANDE
print("CARGANDO DATASET...")
df = pd.read_csv("data/BTC-USD_ONE_MINUTE.csv")
print(f"Dataset: {len(df):,} velas")
print(f"Rango: {df.iloc[0, 0]} a {df.iloc[-1, 0]}")
print(f"Memoria dataset: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")

# Usar archivo parquet existente
import os
PORT = 8765
STATIC_DIR = os.path.join(os.getcwd(), "static_payloads")
filename = "payload_heavy_load.parquet"

def get_reachable_ip():
    try:
        ray_ip = ray.util.get_node_ip_address()
        if ray_ip and ray_ip != '127.0.0.1' and ray_ip != '0.0.0.0':
            return ray_ip
    except: pass
    return '127.0.0.1'

head_ip = get_reachable_ip()
data_url = f"http://{head_ip}:{PORT}/{filename}"
print(f"Data URL: {data_url}\n")

# Estrategias de prueba
test_strategies = [
    {"entry_rules": [{"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}],
     "params": {"sl_pct": 0.02, "tp_pct": 0.04}},
    {"entry_rules": [{"left": {"indicator": "RSI", "period": 14}, "op": ">", "right": {"value": 70}}],
     "params": {"sl_pct": 0.015, "tp_pct": 0.03}},
    {"entry_rules": [{"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 20}}],
     "params": {"sl_pct": 0.025, "tp_pct": 0.05}},
    {"entry_rules": [{"left": {"field": "close"}, "op": "<", "right": {"indicator": "SMA", "period": 20}}],
     "params": {"sl_pct": 0.02, "tp_pct": 0.04}},
    {"entry_rules": [{"left": {"indicator": "SMA", "period": 10}, "op": ">", "right": {"indicator": "SMA", "period": 50}}],
     "params": {"sl_pct": 0.03, "tp_pct": 0.06}},
    {"entry_rules": [{"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 40}}],
     "params": {"sl_pct": 0.02, "tp_pct": 0.05}},
    {"entry_rules": [{"left": {"field": "volume"}, "op": ">", "right": {"indicator": "VOLSMA", "period": 20}}],
     "params": {"sl_pct": 0.025, "tp_pct": 0.05}},
    {"entry_rules": [{"left": {"field": "close"}, "op": ">", "right": {"indicator": "EMA", "period": 20}}],
     "params": {"sl_pct": 0.02, "tp_pct": 0.04}},
    {"entry_rules": [{"left": {"indicator": "RSI", "period": 7}, "op": "<", "right": {"value": 25}}],
     "params": {"sl_pct": 0.015, "tp_pct": 0.03}},
    {"entry_rules": [{"left": {"indicator": "RSI", "period": 21}, "op": "<", "right": {"value": 35}}],
     "params": {"sl_pct": 0.025, "tp_pct": 0.05}},
]

# CARGA EXTREMA: 25 evaluaciones por estrategia = 250 tareas totales
EVALUATIONS_PER_STRATEGY = 25
total_tasks = len(test_strategies) * EVALUATIONS_PER_STRATEGY

print("CONFIGURACION DEL TEST EXTREMO:")
print(f"  Estrategias: {len(test_strategies)}")
print(f"  Evaluaciones por estrategia: {EVALUATIONS_PER_STRATEGY}")
print(f"  Total tareas: {total_tasks}")
print(f"  CPUs: {int(total_cpus)}")
print(f"  Velas por evaluacion: {len(df):,}")
print(f"  Tiempo estimado: {total_tasks * 6 / int(total_cpus) / 60:.1f} minutos\n")

# Preparar tareas
print("="*80)
print("PREPARANDO TAREAS...")
print("="*80 + "\n")

all_tasks = []
for strategy in test_strategies:
    for i in range(EVALUATIONS_PER_STRATEGY):
        all_tasks.append(strategy)

# Métricas
metrics = {
    'start_time': time.time(),
    'completed': 0,
    'errors': 0,
    'results': [],
    'task_times': [],
    'checkpoint_times': []
}

# Monitor de progreso
def show_progress():
    elapsed = time.time() - metrics['start_time']
    completed = metrics['completed']
    remaining = total_tasks - completed
    rate = completed / elapsed if elapsed > 0 else 0

    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
    except:
        cpu_percent = 0
        mem = type('obj', (object,), {'percent': 0})()

    eta = remaining / rate if rate > 0 else 0

    print(f"\r[{completed}/{total_tasks}] | CPU: {cpu_percent:5.1f}% | RAM: {mem.percent:5.1f}% | Rate: {rate:5.2f} task/s | ETA: {int(eta/60)}m {int(eta%60)}s     ", end='', flush=True)

print("Enviando tareas al cluster...")
futures = []

submit_start = time.time()
for strategy in all_tasks:
    future = run_backtest_task.options(scheduling_strategy="SPREAD").remote(
        data_url,
        "LOW",
        strategy,
        "DYNAMIC"
    )
    futures.append(future)

submit_time = time.time() - submit_start
print(f"\nTareas enviadas en {submit_time:.2f}s\n")

print("="*80)
print(f"EJECUTANDO {total_tasks} EVALUACIONES...")
print("="*80 + "\n")

# Procesar resultados con checkpoint cada 50 tareas
unfinished = futures
checkpoint_interval = 50
last_checkpoint = 0

while unfinished:
    show_progress()

    # Checkpoint cada 50 tareas
    if metrics['completed'] - last_checkpoint >= checkpoint_interval:
        checkpoint_time = time.time()
        elapsed = checkpoint_time - metrics['start_time']
        print(f"\n\nCHECKPOINT {metrics['completed']}/{total_tasks}:")
        print(f"  Tiempo transcurrido: {int(elapsed/60)}m {int(elapsed%60)}s")
        print(f"  Errores hasta ahora: {metrics['errors']}")
        print(f"  Rate actual: {metrics['completed']/elapsed:.2f} task/s")
        print()
        metrics['checkpoint_times'].append((metrics['completed'], elapsed))
        last_checkpoint = metrics['completed']

    # Esperar por tareas completadas
    done, unfinished = ray.wait(unfinished, num_returns=min(10, len(unfinished)), timeout=1.0)

    for ref in done:
        task_start = time.time()
        try:
            result = ray.get(ref)
            metrics['results'].append(result)

            if 'error' in result:
                metrics['errors'] += 1
                print(f"\n  ERROR en tarea {metrics['completed']}: {result.get('error', 'Unknown')[:100]}")
        except Exception as e:
            metrics['errors'] += 1
            metrics['results'].append({'error': str(e)})
            print(f"\n  EXCEPTION en tarea {metrics['completed']}: {str(e)[:100]}")

        metrics['completed'] += 1
        metrics['task_times'].append(time.time() - task_start)

show_progress()
print("\n")

# Calcular métricas finales
total_time = time.time() - metrics['start_time']

print("\n" + "="*80)
print("RESULTADOS FINALES - TEST DE CARGA EXTREMA")
print("="*80 + "\n")

print("RENDIMIENTO:")
print(f"  Tiempo total: {int(total_time/60)}m {int(total_time%60)}s ({total_time:.2f}s)")
print(f"  Tareas completadas: {metrics['completed']}/{total_tasks}")
print(f"  Tareas con error: {metrics['errors']} ({metrics['errors']/total_tasks*100:.1f}%)")
print(f"  Throughput promedio: {metrics['completed']/total_time:.2f} tareas/segundo")
print(f"  Tiempo promedio por tarea (get): {sum(metrics['task_times'])/len(metrics['task_times']):.3f}s")
print()

# Analizar resultados
successful_results = [r for r in metrics['results'] if 'error' not in r and 'metrics' in r]

if successful_results:
    print("METRICAS DE BACKTESTS:")
    total_trades = sum(r['metrics']['Total Trades'] for r in successful_results)
    avg_trades = total_trades / len(successful_results)
    avg_pnl = sum(r['metrics']['Total PnL'] for r in successful_results) / len(successful_results)

    print(f"  Evaluaciones exitosas: {len(successful_results)}/{total_tasks}")
    print(f"  Total trades generados: {total_trades:,}")
    print(f"  Promedio trades por backtest: {avg_trades:.1f}")
    print(f"  PnL promedio: ${avg_pnl:.2f}")
    print()

    # Mejor estrategia
    best = max(successful_results, key=lambda x: x['metrics']['Total PnL'])
    print("MEJOR RESULTADO:")
    print(f"  PnL: ${best['metrics']['Total PnL']:.2f}")
    print(f"  Trades: {best['metrics']['Total Trades']}")
    print(f"  Win Rate: {best['metrics']['Win Rate %']:.2f}%")
    print()

# Checkpoints
if metrics['checkpoint_times']:
    print("CHECKPOINTS:")
    for completed, elapsed in metrics['checkpoint_times']:
        print(f"  {completed} tareas: {int(elapsed/60)}m {int(elapsed%60)}s ({completed/elapsed:.2f} task/s)")
    print()

# Estado del cluster
print("ESTADO DEL CLUSTER:")
try:
    nodes = ray.nodes()
    alive_nodes = [n for n in nodes if n.get('Alive', False)]
    print(f"  Nodos activos: {len(alive_nodes)}/{len(nodes)}")

    for i, node in enumerate(alive_nodes):
        node_ip = node.get('NodeManagerAddress', 'Unknown')
        print(f"  Node {i+1} ({node_ip}): OK")
except Exception as e:
    print(f"  Warning: Could not verify cluster: {e}")
print()

# Conclusión
success_rate = len(successful_results) / total_tasks * 100
if metrics['errors'] == 0:
    print("="*80)
    print("TEST EXTREMO COMPLETADO EXITOSAMENTE")
    print(f"{total_tasks} tareas ejecutadas sin errores")
    print("El cluster demuestra excelente estabilidad bajo carga extrema")
    print("="*80)
elif success_rate >= 95:
    print("="*80)
    print("TEST EXTREMO COMPLETADO CON EXITO")
    print(f"Tasa de exito: {success_rate:.1f}%")
    print(f"Solo {metrics['errors']} errores en {total_tasks} tareas")
    print("="*80)
else:
    print("="*80)
    print("TEST COMPLETADO CON PROBLEMAS")
    print(f"Tasa de exito: {success_rate:.1f}%")
    print(f"{metrics['errors']} errores encontrados")
    print("="*80)

print("\n" + "="*80 + "\n")
