#!/usr/bin/env python3
"""
Test de carga pesada del Strategy Miner
Usa estrategias predefinidas que SÍ generan trades para verificar la estabilidad del cluster
"""

import pandas as pd
import ray
import time
import psutil
from datetime import datetime
from optimizer import run_backtest_task

print("\n" + "="*80)
print("STRATEGY MINER - TEST DE CARGA PESADA")
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

# Cargar dataset GRANDE
print("CARGANDO DATASET...")
df = pd.read_csv("data/BTC-USD_ONE_MINUTE.csv")
print(f"Dataset: {len(df):,} velas")
print(f"Rango: {df.iloc[0, 0]} a {df.iloc[-1, 0]}")
print(f"Memoria dataset: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")

# Crear archivo parquet para distribución HTTP
import os
PORT = 8765
STATIC_DIR = os.path.join(os.getcwd(), "static_payloads")
os.makedirs(STATIC_DIR, exist_ok=True)

filename = "payload_heavy_load.parquet"
file_path = os.path.join(STATIC_DIR, filename)
print(f"Guardando dataset como: {file_path}")
df.to_parquet(file_path)

# Iniciar servidor HTTP si no está corriendo
import threading
import http.server
import socketserver

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)
    def log_message(self, format, *args):
        pass

def start_server():
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"HTTP Data Server running on port {PORT}")
            httpd.serve_forever()
    except OSError:
        print(f"Port {PORT} already in use (server running)")

t = threading.Thread(target=start_server, daemon=True)
t.start()
time.sleep(1)

# Obtener IP alcanzable
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

# Definir estrategias de prueba que SÍ generan trades
test_strategies = [
    # RSI Oversold
    {
        "entry_rules": [{"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 30}}],
        "params": {"sl_pct": 0.02, "tp_pct": 0.04}
    },
    # RSI Overbought
    {
        "entry_rules": [{"left": {"indicator": "RSI", "period": 14}, "op": ">", "right": {"value": 70}}],
        "params": {"sl_pct": 0.015, "tp_pct": 0.03}
    },
    # Price above SMA
    {
        "entry_rules": [{"left": {"field": "close"}, "op": ">", "right": {"indicator": "SMA", "period": 20}}],
        "params": {"sl_pct": 0.025, "tp_pct": 0.05}
    },
    # Price below SMA
    {
        "entry_rules": [{"left": {"field": "close"}, "op": "<", "right": {"indicator": "SMA", "period": 20}}],
        "params": {"sl_pct": 0.02, "tp_pct": 0.04}
    },
    # SMA Crossover
    {
        "entry_rules": [{"left": {"indicator": "SMA", "period": 10}, "op": ">", "right": {"indicator": "SMA", "period": 50}}],
        "params": {"sl_pct": 0.03, "tp_pct": 0.06}
    },
    # RSI Moderate
    {
        "entry_rules": [{"left": {"indicator": "RSI", "period": 14}, "op": "<", "right": {"value": 40}}],
        "params": {"sl_pct": 0.02, "tp_pct": 0.05}
    },
    # Volume above average
    {
        "entry_rules": [{"left": {"field": "volume"}, "op": ">", "right": {"indicator": "VOLSMA", "period": 20}}],
        "params": {"sl_pct": 0.025, "tp_pct": 0.05}
    },
    # EMA
    {
        "entry_rules": [{"left": {"field": "close"}, "op": ">", "right": {"indicator": "EMA", "period": 20}}],
        "params": {"sl_pct": 0.02, "tp_pct": 0.04}
    },
]

# Configurar carga (ajustado para CPUs disponibles)
# Con 8 estrategias y 10 evaluaciones cada una = 80 tareas totales
EVALUATIONS_PER_STRATEGY = 10  # Evaluar cada estrategia 10 veces
total_tasks = len(test_strategies) * EVALUATIONS_PER_STRATEGY

print("CONFIGURACION DEL TEST:")
print(f"  Estrategias: {len(test_strategies)}")
print(f"  Evaluaciones por estrategia: {EVALUATIONS_PER_STRATEGY}")
print(f"  Total tareas: {total_tasks}")
print(f"  CPUs: {int(total_cpus)}")
print(f"  Velas por evaluacion: {len(df):,}\n")

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
    'task_times': []
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

    print(f"\r[{completed}/{total_tasks}] | CPU: {cpu_percent:5.1f}% | RAM: {mem.percent:5.1f}% | Rate: {rate:5.1f} task/s | ETA: {int(eta)}s     ", end='', flush=True)

print("Enviando tareas al cluster...")
futures = []

# Enviar todas las tareas de una vez con scheduling SPREAD
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
print("EJECUTANDO EVALUACIONES...")
print("="*80 + "\n")

# Procesar resultados
unfinished = futures
while unfinished:
    show_progress()

    # Esperar por tareas completadas
    done, unfinished = ray.wait(unfinished, num_returns=min(10, len(unfinished)), timeout=1.0)

    for ref in done:
        task_start = time.time()
        try:
            result = ray.get(ref)
            metrics['results'].append(result)

            # Verificar si hubo error
            if 'error' in result:
                metrics['errors'] += 1
        except Exception as e:
            metrics['errors'] += 1
            metrics['results'].append({'error': str(e)})

        metrics['completed'] += 1
        metrics['task_times'].append(time.time() - task_start)

show_progress()
print("\n")

# Calcular métricas finales
total_time = time.time() - metrics['start_time']

print("\n" + "="*80)
print("RESULTADOS FINALES")
print("="*80 + "\n")

print("RENDIMIENTO:")
print(f"  Tiempo total: {total_time:.2f}s ({total_time/60:.1f} min)")
print(f"  Tareas completadas: {metrics['completed']}/{total_tasks}")
print(f"  Tareas con error: {metrics['errors']}")
print(f"  Throughput: {metrics['completed']/total_time:.2f} tareas/segundo")
print(f"  Tiempo promedio por tarea: {sum(metrics['task_times'])/len(metrics['task_times']):.3f}s")
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
if metrics['errors'] == 0 and len(successful_results) == total_tasks:
    print("="*80)
    print("TEST EXITOSO")
    print("El cluster distribuido maneja la carga pesada correctamente")
    print("No se detectaron crashes, SIGSEGV ni problemas de estabilidad")
    print("="*80)
elif metrics['errors'] > 0:
    print("="*80)
    print("TEST COMPLETADO CON ERRORES")
    print(f"Se encontraron {metrics['errors']} errores")
    print("Revisar logs para detalles")
    print("="*80)
else:
    print("="*80)
    print("TEST COMPLETADO")
    print("="*80)

print("\n" + "="*80 + "\n")
