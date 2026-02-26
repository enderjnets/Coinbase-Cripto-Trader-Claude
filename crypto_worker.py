#!/usr/bin/env python3
"""
CRYPTO WORKER - Cliente del Sistema Distribuido
Compatible con macOS, Windows y Linux

Este worker:
- Contacta al coordinator para obtener trabajo
- Ejecuta backtests de estrategias
- Envía resultados al coordinator
- Implementa checkpoints para recuperación
- Funciona completamente offline (excepto para sync con coordinator)

Autor: Strategy Miner Team
Fecha: 30 Enero 2026
"""

import requests
import time
import socket
import platform
import os
import sys
import json
from datetime import datetime
import pandas as pd
try:
    import ray
    HAS_RAY = True
except ImportError:
    HAS_RAY = False
from strategy_miner import StrategyMiner

# Detect market type from data file path
def detect_market_type(data_file):
    """Detect if this is futures data based on file path."""
    if not data_file:
        return "SPOT", False
    data_lower = data_file.lower()
    if "futures" in data_lower or "data_futures" in data_lower:
        # Check if it's a perpetual contract
        is_perpetual = "perp" in data_lower or "p-" in data_lower or data_lower.endswith("-p_") or \
                       any(x in data_lower for x in ["bip-", "etp-", "slp-", "xpp-", "adp-", "dop-", "lnp-", "avp-", "xlp-", "hep-", "lcp-"])
        return "FUTURES", is_perpetual
    return "SPOT", False

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# URL del coordinator (IP del Mac local por defecto)
COORDINATOR_URL = os.getenv('COORDINATOR_URL', "http://10.0.0.56:5001")

# Instancia del worker (para múltiples workers en la misma máquina)
WORKER_INSTANCE = os.getenv('WORKER_INSTANCE', '1')

# ID único de este worker (incluye instancia si hay múltiples)
WORKER_ID = f"{socket.gethostname()}_{platform.system()}_W{WORKER_INSTANCE}"

# Intervalo de polling (segundos)
POLL_INTERVAL = 30

# Archivo de checkpoint
CHECKPOINT_FILE = f"worker_checkpoint_{WORKER_ID}.json"

# Directorio de datos
DATA_FILE = "data/BTC-USD_ONE_MINUTE.csv"

# CPUs a reservar (ajustado para múltiples workers)
# Si hay N workers, cada uno usa total_cpus/N
RESERVED_CPUS = 1  # Se ajusta dinámicamente más abajo

# ============================================================================
# CHECKPOINT SYSTEM
# ============================================================================

def save_checkpoint(work_id, generation, best_genome, best_pnl, timeout=5):
    """Guarda checkpoint del trabajo actual con timeout"""
    import threading

    checkpoint = {
        'work_id': work_id,
        'generation': generation,
        'best_genome': best_genome,
        'best_pnl': best_pnl,
        'timestamp': time.time(),
        'worker_id': WORKER_ID
    }

    def _write():
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    # Ejecutar con timeout
    writer = threading.Thread(target=_write, daemon=True)
    writer.start()
    writer.join(timeout=timeout)

    if writer.is_alive():
        print(f"⚠️  Checkpoint timeout después de {timeout}s")

def load_checkpoint():
    """Carga checkpoint si existe"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(f, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def clear_checkpoint():
    """Elimina checkpoint después de completar trabajo"""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

# ============================================================================
# COORDINATOR COMMUNICATION
# ============================================================================

def get_work():
    """
    Solicita trabajo al coordinator

    Returns:
        Dict con work_id y strategy_params, o None si no hay trabajo
    """
    try:
        response = requests.get(
            f"{COORDINATOR_URL}/api/get_work",
            params={'worker_id': WORKER_ID},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('work_id'):
                return data

        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error contactando coordinator: {e}")
        return None

def submit_result(work_id, pnl, trades, win_rate, sharpe_ratio, max_drawdown, execution_time, strategy_genome=None):
    """
    Envía resultado al coordinator (incluye el genoma de la estrategia)

    Returns:
        True si se envió exitosamente, False en caso contrario
    """
    try:
        payload = {
            'work_id': work_id,
            'worker_id': WORKER_ID,
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'execution_time': execution_time
        }

        # Incluir genoma si está disponible
        if strategy_genome:
            payload['strategy_genome'] = json.dumps(strategy_genome)

        response = requests.post(
            f"{COORDINATOR_URL}/api/submit_result",
            json=payload,
            timeout=30
        )

        return response.status_code == 200

    except requests.exceptions.RequestException as e:
        print(f"❌ Error enviando resultado: {e}")
        return False

# ============================================================================
# BACKTEST EXECUTION
# ============================================================================

def execute_backtest(strategy_params, work_id=None):
    """
    Ejecuta backtest con los parámetros dados

    Args:
        strategy_params: Dict con population_size, generations, risk_level
        work_id: ID del trabajo actual (para checkpoints)

    Returns:
        Dict con pnl, trades, win_rate, sharpe_ratio, max_drawdown
    """
    print(f"🔬 Ejecutando backtest...")
    print(f"   Población: {strategy_params.get('population_size', 30)}")
    print(f"   Generaciones: {strategy_params.get('generations', 20)}")
    print(f"   Risk Level: {strategy_params.get('risk_level', 'MEDIUM')}")

    # Cargar datos - buscar en múltiples ubicaciones
    data_file_name = strategy_params.get('data_file', os.path.basename(DATA_FILE))

    # Intentar múltiples ubicaciones para encontrar el archivo
    possible_paths = []
    if strategy_params.get('data_dir'):
        possible_paths.append(os.path.join(strategy_params['data_dir'], data_file_name))
    possible_paths.extend([
        os.path.join("data", data_file_name),
        os.path.join("data_futures", data_file_name),
        os.path.join("data_coingecko", data_file_name),
        data_file_name,  # Ruta absoluta
    ])

    data_file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            data_file_path = path
            break

    if not data_file_path:
        print(f"❌ Error: Archivo de datos no encontrado: {data_file_name}")
        print(f"   Rutas buscadas: {possible_paths}")
        return None

    print(f"   Archivo de datos: {data_file_path}")

    # Read max_candles from strategy_params (0 = all candles)
    max_candles = strategy_params.get('max_candles', 0)
    df = pd.read_csv(data_file_path)
    if max_candles > 0 and len(df) > max_candles:
        df = df.tail(max_candles).copy()
    else:
        df = df.copy()
    df.reset_index(drop=True, inplace=True)
    total_available = len(df)
    print(f"   📊 Usando {total_available:,} velas" + (f" (cap: {max_candles:,})" if max_candles > 0 else " (todas)"))

    # Detect market type from data file
    market_type, is_perpetual = detect_market_type(data_file_path)
    if market_type == "FUTURES":
        print(f"   📈 FUTURES mode detected (perpetual: {is_perpetual})")

    # Crear miner con soporte para seed_genomes (élite global)
    # IMPORTANTE: force_local=False permite que Ray paralelice usando los 9 cores
    seed_genomes = strategy_params.get('seed_genomes', [])
    seed_ratio = strategy_params.get('seed_ratio', 0.5)

    if seed_genomes:
        print(f"   🌱 Usando {len(seed_genomes)} genomas élite como semilla ({seed_ratio*100:.0f}% de población)")

    miner = StrategyMiner(
        df=df,
        population_size=strategy_params.get('population_size', 30),
        generations=strategy_params.get('generations', 20),
        risk_level=strategy_params.get('risk_level', 'MEDIUM'),
        force_local=True,  # Procesamiento secuencial estable (Ray inestable en este sistema)
        seed_genomes=seed_genomes,
        seed_ratio=seed_ratio,
        market_type=market_type,
        max_leverage=strategy_params.get('max_leverage', 10),
        is_perpetual=is_perpetual
    )

    # Ejecutar búsqueda
    start_time = time.time()

    def progress_callback(msg_type, data):
        """Callback para monitorear progreso y crear checkpoints"""
        if msg_type == "START_GEN":
            gen = data
            print(f"   Gen {gen}/{strategy_params.get('generations', 20)}")

        elif msg_type == "BEST_GEN":
            gen = data.get('gen', 0)
            pnl = data.get('pnl', 0)
            print(f"   Gen {gen}: PnL=${pnl:,.2f}")

            # Guardar checkpoint cada 5 generaciones
            if gen % 5 == 0:
                save_checkpoint(
                    work_id=work_id,  # Usar ID real del trabajo
                    generation=gen,
                    best_genome=data.get('genome'),
                    best_pnl=pnl
                )

    best_genome, best_pnl, best_metrics = miner.run(
        progress_callback=progress_callback, return_metrics=True
    )

    execution_time = time.time() - start_time

    # Extract real metrics from miner
    trades = best_metrics.get('Total Trades', 0)
    win_rate_pct = best_metrics.get('Win Rate %', 0.0)
    win_rate = win_rate_pct / 100.0 if win_rate_pct > 1 else win_rate_pct
    sharpe_ratio = best_metrics.get('Sharpe Ratio', 0.0)
    max_drawdown = best_metrics.get('Max Drawdown', 0.0)
    liquidations = best_metrics.get('Liquidations', 0)  # Futures only

    result = {
        'pnl': best_pnl,
        'trades': trades,
        'win_rate': round(win_rate, 4),
        'sharpe_ratio': round(sharpe_ratio, 4),
        'max_drawdown': round(max_drawdown, 4),
        'execution_time': execution_time,
        'genome': best_genome,  # Incluir el mejor genoma encontrado
        'market_type': market_type  # SPOT or FUTURES
    }

    # Add liquidations for futures
    if market_type == "FUTURES":
        result['liquidations'] = liquidations

    print(f"✅ Backtest completado en {execution_time:.0f}s")
    print(f"   PnL: ${best_pnl:,.2f}")
    if market_type == "FUTURES" and liquidations > 0:
        print(f"   Trades: {trades} | Win Rate: {win_rate:.1%} | Sharpe: {sharpe_ratio:.2f} | Max DD: {max_drawdown:.2%} | Liqs: {liquidations}")
    else:
        print(f"   Trades: {trades} | Win Rate: {win_rate:.1%} | Sharpe: {sharpe_ratio:.2f} | Max DD: {max_drawdown:.2%}")

    return result

# ============================================================================
# MAIN WORKER LOOP
# ============================================================================

def main():
    """Loop principal del worker"""
    print("\n" + "="*80)
    print(f"🤖 CRYPTO WORKER - {WORKER_ID}")
    print("="*80 + "\n")

    print(f"💻 Sistema: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"🌐 Hostname: {socket.gethostname()}")
    print(f"📡 Coordinator: {COORDINATOR_URL}\n")

    # Verificar conectividad con coordinator
    print("🔍 Verificando conexión con coordinator...")
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/status", timeout=10)
        if response.status_code == 200:
            print("✅ Conexión OK\n")
        else:
            print(f"⚠️  Coordinator respondió con status {response.status_code}\n")
    except requests.exceptions.RequestException as e:
        print(f"❌ No se puede conectar al coordinator: {e}")
        print("⚠️  Verifica que el coordinator esté ejecutándose")
        print(f"   URL: {COORDINATOR_URL}\n")
        print("Presiona Ctrl+C para salir o espera para reintentar...\n")

    # Verificar datos
    if os.path.exists(DATA_FILE):
        print(f"✅ Datos encontrados: {DATA_FILE}")
        df_test = pd.read_csv(DATA_FILE)
        print(f"   {len(df_test):,} velas disponibles\n")
    else:
        print(f"❌ ADVERTENCIA: Datos no encontrados: {DATA_FILE}")
        print("   El worker no podrá ejecutar backtests\n")

    print("="*80)
    print("⚡ WORKER INICIADO - Esperando trabajo...")
    print("="*80)
    print(f"ℹ️  Poll interval: {POLL_INTERVAL}s")
    print(f"ℹ️  Presiona Ctrl+C para detener\n")

    # Main loop
    while True:
        try:
            # Solicitar trabajo
            work = get_work()

            if work:
                work_id = work['work_id']
                params = work['strategy_params']
                replica_num = work.get('replica_number', 1)
                replicas_needed = work.get('replicas_needed', 2)

                print(f"\n{'='*80}")
                print(f"📥 TRABAJO RECIBIDO - Work ID: {work_id}")
                print(f"   Réplica {replica_num}/{replicas_needed}")
                print(f"{'='*80}\n")

                # Ejecutar backtest con work_id para checkpoints
                result = execute_backtest(params, work_id=work_id)

                if result:
                    # Enviar resultado
                    print(f"\n📤 Enviando resultado al coordinator...")

                    success = submit_result(
                        work_id=work_id,
                        pnl=result['pnl'],
                        trades=result['trades'],
                        win_rate=result['win_rate'],
                        sharpe_ratio=result['sharpe_ratio'],
                        max_drawdown=result['max_drawdown'],
                        execution_time=result['execution_time'],
                        strategy_genome=result.get('genome')  # Enviar genoma para élite global
                    )

                    if success:
                        print(f"✅ Resultado enviado exitosamente")
                        clear_checkpoint()
                    else:
                        print(f"❌ Error enviando resultado - Se reintentará")

                else:
                    print(f"❌ Error ejecutando backtest")

                print(f"\n{'='*80}")
                print(f"⏳ Esperando siguiente trabajo...")
                print(f"{'='*80}\n")

            else:
                # No hay trabajo disponible
                print(f"⏳ Sin trabajo disponible - Esperando {POLL_INTERVAL}s...")

            # Esperar antes del siguiente poll
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n" + "="*80)
            print("🛑 Worker detenido por el usuario")
            print("="*80 + "\n")
            break

        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
            print(f"⏳ Reintentando en {POLL_INTERVAL}s...\n")
            time.sleep(POLL_INTERVAL)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Permitir configurar coordinator URL desde argumentos
    if len(sys.argv) > 1:
        COORDINATOR_URL = sys.argv[1]
        print(f"📡 Usando coordinator: {COORDINATOR_URL}")

    # Número total de workers en esta máquina
    NUM_WORKERS = int(os.getenv('NUM_WORKERS', '1'))

    # Detectar número total de CPUs
    total_cpus = os.cpu_count()

    # Calcular CPUs por worker (dividir entre workers, mínimo 2)
    cpus_per_worker = max(2, (total_cpus - 1) // NUM_WORKERS)

    # Modo de ejecución: force_local no necesita Ray
    USE_RAY = os.getenv('USE_RAY', 'false').lower() == 'true'

    print(f"\n{'='*80}")
    print(f"⚙️  CONFIGURACIÓN DE RECURSOS - Worker {WORKER_INSTANCE}")
    print(f"{'='*80}")
    print(f"💻 CPUs totales: {total_cpus}")
    print(f"👥 Workers en máquina: {NUM_WORKERS}")
    print(f"🚀 CPUs por worker: {cpus_per_worker}")
    print(f"⚡ Modo: {'Ray paralelo' if USE_RAY else 'Local secuencial (estable)'}")
    print(f"{'='*80}\n")

    # Solo inicializar Ray si es necesario y está disponible
    if USE_RAY and HAS_RAY:
        if not ray.is_initialized():
            if os.getenv('RAY_ADDRESS'):
                print(f"⚠️  Detectado RAY_ADDRESS existente, limpiando...")
                del os.environ['RAY_ADDRESS']
            ray.init(num_cpus=cpus_per_worker, ignore_reinit_error=True)
    else:
        print("🛡️  Ray desactivado - modo local estable (sin crashes)")

    main()
