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
try:
    from numba_backtester import numba_evaluate_population
    HAS_NUMBA_BACKTESTER = True
except ImportError:
    HAS_NUMBA_BACKTESTER = False

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

# Mínimo de velas para backtest confiable (train+test)
MIN_TOTAL_CANDLES = 1000

# Train/Test split ratio (70% train, 30% test)
TRAIN_RATIO = 0.70

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
            with open(CHECKPOINT_FILE, 'r') as fh:
                return json.load(fh)
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

            # Shutdown remoto desde coordinator
            if data.get('shutdown'):
                print(f"\n🛑 SHUTDOWN solicitado por el coordinator. Deteniendo worker...")
                import sys
                sys.exit(0)

            if data.get('work_id'):
                return data

        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error contactando coordinator: {e}")
        return None

def submit_result(work_id, pnl, trades, win_rate, sharpe_ratio, max_drawdown,
                   execution_time, strategy_genome=None,
                   oos_pnl=0, oos_trades=0, oos_degradation=0,
                   robustness_score=0, is_overfitted=False,
                   actual_candles=0, train_candles=0, test_candles=0):
    """
    Envía resultado al coordinator (incluye genoma y métricas OOS)

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
            'execution_time': execution_time,
            # OOS metrics
            'oos_pnl': oos_pnl,
            'oos_trades': oos_trades,
            'oos_degradation': oos_degradation,
            'robustness_score': robustness_score,
            'is_overfitted': is_overfitted,
            # Data quality
            'actual_candles': actual_candles,
            'train_candles': train_candles,
            'test_candles': test_candles,
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
        os.path.expanduser("~/trader_data/data/" + data_file_name),
        os.path.expanduser("~/trader_data/data_futures/" + data_file_name),
        os.path.expanduser("~/crypto_worker/data/" + data_file_name),
    ])

    data_file_path = None
    
    # First check if any path contains Google Drive (macOS security blocks this)
    # and try local alternatives first
    for path in possible_paths:
        if 'GoogleDrive' in path or 'Google Drive' in path:
            filename = os.path.basename(path)
            local_paths = [
                os.path.expanduser(f"~/trader_data/data_futures/{filename}"),
                os.path.expanduser(f"~/trader_data/data/{filename}"),
                os.path.expanduser(f"~/crypto_worker/data/{filename}"),
            ]
            for lp in local_paths:
                if os.path.exists(lp):
                    data_file_path = lp
                    break
            if data_file_path:
                break
    
    # If no local alternative found, try original paths
    if not data_file_path:
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

    # Pre-check de calidad: mínimo de velas
    if total_available < MIN_TOTAL_CANDLES:
        print(f"   ⚠️  SKIP: Solo {total_available:,} velas (mínimo {MIN_TOTAL_CANDLES:,})")
        return None

    # ===== TRAIN/TEST SPLIT (70/30) =====
    split_idx = int(total_available * TRAIN_RATIO)
    df_train = df.iloc[:split_idx].copy().reset_index(drop=True)
    df_test = df.iloc[split_idx:].copy().reset_index(drop=True)
    print(f"   🔀 Train: {len(df_train):,} velas | Test: {len(df_test):,} velas (70/30 split)")

    # Extract market type and leverage from work unit
    market_type = strategy_params.get('market_type', 'SPOT')
    max_leverage = strategy_params.get('max_leverage', 1)
    leverage = strategy_params.get('leverage', 1)
    if max_leverage < leverage:
        max_leverage = leverage

    print(f"   Market Type: {market_type}" + (f" (leverage: {max_leverage}x)" if max_leverage > 1 else ""))

    # Crear miner con soporte para seed_genomes (élite global)
    # IMPORTANTE: force_local=False permite que Ray paralelice usando los 9 cores
    seed_genomes = strategy_params.get('seed_genomes', [])
    seed_ratio = strategy_params.get('seed_ratio', 0.5)

    if seed_genomes:
        print(f"   🌱 Usando {len(seed_genomes)} genomas élite como semilla ({seed_ratio*100:.0f}% de población)")

    # Force LONG for spot (no short selling in spot market)
    if market_type == "SPOT":
        for sg in seed_genomes:
            if isinstance(sg, dict) and 'params' in sg:
                sg['params']['direction'] = 'LONG'
                sg['params']['leverage'] = 1

    miner = StrategyMiner(
        df=df_train,
        population_size=strategy_params.get('population_size', 30),
        generations=strategy_params.get('generations', 20),
        risk_level=strategy_params.get('risk_level', 'MEDIUM'),
        force_local=True,  # Procesamiento secuencial estable (Ray inestable en este sistema)
        seed_genomes=seed_genomes,
        seed_ratio=seed_ratio,
        market_type=market_type,
        max_leverage=max_leverage,
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

    # Extract real metrics from miner (TRAIN metrics)
    train_trades = best_metrics.get('Total Trades', 0)
    train_win_rate_pct = best_metrics.get('Win Rate %', 0.0)
    train_win_rate = train_win_rate_pct / 100.0 if train_win_rate_pct > 1 else train_win_rate_pct
    train_sharpe = best_metrics.get('Sharpe Ratio', 0.0)
    train_max_dd = best_metrics.get('Max Drawdown', 0.0)
    train_pnl = best_pnl

    # ===== OOS EVALUATION =====
    oos_pnl = 0.0
    oos_trades = 0
    oos_win_rate = 0.0
    oos_sharpe = 0.0
    oos_max_dd = 0.0
    oos_degradation = 1.0
    robustness_score = 0
    is_overfitted = True

    if best_genome and HAS_NUMBA_BACKTESTER and len(df_test) >= 100:
        try:
            oos_results = numba_evaluate_population(
                df_test, [best_genome],
                risk_level=strategy_params.get('risk_level', 'MEDIUM'),
                market_type=market_type,
                max_leverage=max_leverage
            )
            if oos_results and len(oos_results) > 0:
                oos_m = oos_results[0].get('metrics', {})
                oos_pnl = oos_m.get('Total PnL', 0.0)
                oos_trades = oos_m.get('Total Trades', 0)
                oos_wr_pct = oos_m.get('Win Rate %', 0.0)
                oos_win_rate = oos_wr_pct / 100.0 if oos_wr_pct > 1 else oos_wr_pct
                oos_sharpe = oos_m.get('Sharpe Ratio', 0.0)
                oos_max_dd = oos_m.get('Max Drawdown', 0.0)

                # Degradation: cuánto peor es OOS vs Train
                if train_pnl > 0:
                    oos_degradation = round(1.0 - (oos_pnl / train_pnl), 4)
                else:
                    oos_degradation = 1.0  # Train negativo = no se puede calcular

                # Robustness score (0-100)
                score = 0
                if oos_pnl > 0:
                    score += 30       # OOS PnL positivo
                if oos_degradation < 0.35:
                    score += 30       # Degradation < 35%
                if oos_trades >= 15:
                    score += 20       # Suficientes trades OOS
                if oos_sharpe > 0:
                    score += 20       # Sharpe positivo en OOS
                robustness_score = score

                is_overfitted = (oos_pnl < 0) or (oos_degradation > 0.50)

                print(f"   🔬 OOS: PnL=${oos_pnl:,.2f} | Trades={oos_trades} | "
                      f"WR={oos_win_rate:.1%} | Degradation={oos_degradation:.1%} | "
                      f"Robustness={robustness_score}/100 | "
                      f"{'❌ OVERFITTED' if is_overfitted else '✅ ROBUST'}")
        except Exception as e:
            print(f"   ⚠️  OOS evaluation failed: {e}")
    elif not HAS_NUMBA_BACKTESTER:
        print(f"   ⚠️  OOS skipped: numba_backtester not available")
    elif len(df_test) < 100:
        print(f"   ⚠️  OOS skipped: test set too small ({len(df_test)} velas)")

    result = {
        'pnl': train_pnl,
        'trades': train_trades,
        'win_rate': round(train_win_rate, 4),
        'sharpe_ratio': round(train_sharpe, 4),
        'max_drawdown': round(train_max_dd, 4),
        'execution_time': execution_time,
        'genome': best_genome,
        # OOS metrics
        'oos_pnl': round(oos_pnl, 2),
        'oos_trades': oos_trades,
        'oos_win_rate': round(oos_win_rate, 4),
        'oos_sharpe': round(oos_sharpe, 4),
        'oos_max_dd': round(oos_max_dd, 4),
        'oos_degradation': round(oos_degradation, 4),
        'robustness_score': robustness_score,
        'is_overfitted': is_overfitted,
        # Data quality metrics
        'actual_candles': total_available,
        'train_candles': len(df_train),
        'test_candles': len(df_test),
    }

    print(f"✅ Backtest completado en {execution_time:.0f}s")
    print(f"   Train PnL: ${train_pnl:,.2f} | OOS PnL: ${oos_pnl:,.2f}")
    print(f"   Trades: {train_trades} | Win Rate: {train_win_rate:.1%} | Sharpe: {train_sharpe:.2f} | Max DD: {train_max_dd:.2%}")

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
                        strategy_genome=result.get('genome'),
                        # OOS metrics
                        oos_pnl=result.get('oos_pnl', 0),
                        oos_trades=result.get('oos_trades', 0),
                        oos_degradation=result.get('oos_degradation', 0),
                        robustness_score=result.get('robustness_score', 0),
                        is_overfitted=result.get('is_overfitted', False),
                        # Data quality
                        actual_candles=result.get('actual_candles', 0),
                        train_candles=result.get('train_candles', 0),
                        test_candles=result.get('test_candles', 0),
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
