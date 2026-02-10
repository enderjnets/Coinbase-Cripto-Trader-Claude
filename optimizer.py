import itertools
import pandas as pd
import time
import os
import sys

import json
import hashlib
from datetime import datetime
import glob

# Enable Ray Multi-Node on macOS
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

import ray
from backtester import Backtester

# --- CHECKPOINT SYSTEM ---
CHECKPOINT_DIR = "optimization_checkpoints"

def ensure_checkpoint_dir():
    if not os.path.exists(CHECKPOINT_DIR):
        os.makedirs(CHECKPOINT_DIR)

def get_params_hash(params, optimizer_type):
    """Generate a unique hash for the optimization parameters."""
    # Convert to string, sort keys to ensure consistency
    s = json.dumps({
        'params': params,
        'type': optimizer_type
    }, sort_keys=True)
    return hashlib.md5(s.encode()).hexdigest()

def find_compatible_checkpoint(optimizer_type, param_ranges, risk_level):
    """Find a checkpoint that matches the current parameters."""
    ensure_checkpoint_dir()
    p_hash = get_params_hash({'ranges': param_ranges, 'risk': risk_level}, optimizer_type)
    
    files = glob.glob(os.path.join(CHECKPOINT_DIR, f"checkpoint_{optimizer_type}_*.json"))
    
    for f in files:
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                if data.get('params_hash') == p_hash:
                    return f, data
        except:
            continue
    return None, None

def save_checkpoint(optimizer_type, param_ranges, risk_level, results, metadata, file_path=None):
    """Save the current state of optimization."""
    ensure_checkpoint_dir()
    p_hash = get_params_hash({'ranges': param_ranges, 'risk': risk_level}, optimizer_type)
    
    if not file_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(CHECKPOINT_DIR, f"checkpoint_{optimizer_type}_{timestamp}.json")
    
    data = {
        'optimizer_type': optimizer_type,
        'params_hash': p_hash,
        'param_ranges': param_ranges,
        'risk_level': risk_level,
        'results': results,
        'metadata': metadata,
        'last_updated': str(datetime.now())
    }
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return file_path

def delete_checkpoint(file_path):
    """Delete a checkpoint file after successful completion."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass

# Ray Remote Function (Worker)
@ray.remote(num_cpus=1, scheduling_strategy="SPREAD")
def run_backtest_task(data_payload, risk_level, params, strategy_code="HYBRID"):
    import signal
    import pandas as pd
    import os
    import io

    # ⚡ FORCE RELOAD MODULES (Fix for Ray code caching)
    import sys
    import importlib
    if 'backtester' in sys.modules:
        importlib.reload(sys.modules['backtester'])
    if 'dynamic_strategy' in sys.modules:
        importlib.reload(sys.modules['dynamic_strategy'])

    # Re-import after reload to get updated code
    from backtester import Backtester as BacktesterReloaded

    # LOAD DATA ROBUSTLY (HTTP Strategy)
    try:
        # 0. HTTP Side-Load (Bypasses Ray Object Store & Drive)
        if isinstance(data_payload, str) and data_payload.startswith("http"):
            # Pandas can read directly from URL (uses urllib/requests)
            # storage_options might be needed if auth was required, but we use open internal port
            df = pd.read_parquet(data_payload)
            
        elif isinstance(data_payload, str) and data_payload.startswith("FILE:"):
             # Shared Drive Fallback (Legacy)
             filename = data_payload.split(":", 1)[1]
             file_path = os.path.abspath(filename)
             if os.path.exists(file_path):
                 df = pd.read_parquet(file_path)
             else:
                 base_dir = os.path.dirname(os.path.abspath(__file__))
                 file_path = os.path.join(base_dir, filename)
                 df = pd.read_parquet(file_path)

        elif isinstance(data_payload, bytes):
            # 1. Bytes Strategy (Compressed Parquet Blob) -> Universal
            with io.BytesIO(data_payload) as buffer:
                df = pd.read_parquet(buffer)
                
        elif isinstance(data_payload, str):
            # 2. Legacy File Path Strategy
            if data_payload.endswith(".parquet"):
                df = pd.read_parquet(data_payload)
            elif data_payload.endswith(".csv"):
                 df = pd.read_csv(data_payload)
            elif data_payload.endswith(".pkl"):
                 df = pd.read_pickle(data_payload)
            else:
                 raise ValueError("Unknown data format")
        else:
            # 3. Direct Object (Local Mode / Standard Ray)
            df = data_payload
    except Exception as e:
        return {'error': f"Failed to load data payload ({str(data_payload)[:50]}...): {str(e)}"}
    
    # Timeout Handler per task (600 seconds max)
    def handler(signum, frame):
        raise TimeoutError("Backtest exceeded 600s execution time limit")
    
    # Register signal for Timeout (Unix/Mac only)
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(600) # 600 seconds limit
    
    try:
        # Re-instantiate backtester locally in the worker (use reloaded version)
        bt = BacktesterReloaded()
        
        # Resolve Strategy Class
        strat_cls = None
        if strategy_code == "BTC_SPOT":
            from btc_spot_strategy import BitcoinSpotStrategy
            strat_cls = BitcoinSpotStrategy
        elif strategy_code == "DYNAMIC":
            # Import DynamicStrategy (already reloaded at function start)
            from dynamic_strategy import DynamicStrategy
            strat_cls = DynamicStrategy
            print(f"🔍 RAY WORKER: Using DynamicStrategy with genome: {params}")
        # else default is Hybrid (handled by Backtester if None, or explicit)
        if strategy_code == "HYBRID":
            from strategy import Strategy
            strat_cls = Strategy

        _, trades = bt.run_backtest(df, risk_level=risk_level, strategy_params=params, strategy_cls=strat_cls)

        total_trades = len(trades)
        print(f"🔍 RAY WORKER: Backtest returned {total_trades} trades")
        win_rate = 0.0
        total_pnl = 0.0
        final_balance = 10000.0

        if total_trades > 0:
            wins = trades[trades['pnl'] > 0]
            win_rate = (len(wins) / total_trades) * 100
            total_pnl = trades['pnl'].sum()
            final_balance = trades['balance'].iloc[-1]

        return {
            'params': params,
            'metrics': {
                'Total Trades': total_trades,
                'Win Rate %': round(win_rate, 2),
                'Total PnL': round(total_pnl, 2),
                'Final Balance': round(final_balance, 2)
            }
        }
    except Exception as e:
        import traceback
        err_type = "Timeout" if isinstance(e, TimeoutError) else "Error"
        return {'error': f"{err_type}: {str(e)}", 'traceback': traceback.format_exc()}
    finally:
        signal.alarm(0) # Disable alarm

class GridOptimizer:
    def __init__(self, force_local=False):
        self.backtester = Backtester()
        self.force_local = force_local

    def generate_grid(self, param_ranges):
        keys = param_ranges.keys()
        values = param_ranges.values()
        combinations = list(itertools.product(*values))
        grid = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            grid.append(params)
        return grid

    def optimize(self, df, param_ranges, risk_level="LOW", progress_callback=None, cancel_event=None, log_callback=None, strategy_code="HYBRID"):
        def log(msg):
            print(msg, flush=True)
            sys.stdout.flush()
            try:
                with open("debug_optimizer_trace.log", "a", encoding='utf-8') as f:
                    f.write(f"{datetime.now()} - {msg}\n")
            except Exception as e:
                print(f"Log error: {e}")

            if log_callback:
                try:
                    log_callback(msg)
                except Exception as e:
                    print(f"Error in log_callback: {e}", flush=True)

        try:
            log("=" * 60)
            log("GRID SEARCH OPTIMIZER - INICIANDO")
            log("=" * 60)

            log("Generando grid de parámetros...")
            grid = self.generate_grid(param_ranges)
            total_runs = len(grid)
            results = []

            log(f"Total de combinaciones: {total_runs}")
            log(f"Parámetros: {param_ranges}")

            # --- CHECKPOINT CHECK ---
            checkpoint_path, checkpoint_data = find_compatible_checkpoint("grid", param_ranges, risk_level)
            completed_params_hashes = set()
            
            if checkpoint_data:
                log(f"\n💾 CHECKPOINT DETECTADO: {checkpoint_data['last_updated']}")
                results = checkpoint_data['results']
                completed_count = len(results)
                
                # Create a set of already processed params to skip
                for r in results:
                    # Create signature from params
                    p_sig = json.dumps(r, sort_keys=True)
                    completed_params_hashes.add(p_sig)
                
                log(f"✅ Recuperados {completed_count} resultados previos. Continuando...")
                
                # Filter grid to run only missing
                new_grid = []
                for p in grid:
                    # Extract only the params part if 'r' has metrics mingled, 
                    # but usually 'r' in results has metrics. 
                    # We need to reconstruct the param dict to check.
                    # Actually, results contain keys like 'metrics' and params. 
                    # Let's adjust the hash check above.
                    pass
                
                # Re-do specific hash set for results
                completed_params_hashes = set()
                for r in results:
                    # Remove metrics/traceback to get pure params
                    clean_p = {k: v for k, v in r.items() if k not in ['metrics', 'error', 'traceback']}
                    completed_params_hashes.add(json.dumps(clean_p, sort_keys=True))

                grid = [p for p in grid if json.dumps(p, sort_keys=True) not in completed_params_hashes]
                log(f"🚀 Tareas restantes: {len(grid)}")
                
            else:
                completed_count = 0


            # Initialize Ray - Supports both CLUSTER and LOCAL modes
            log("\n🔍 Inicializando Ray...")

            if ray.is_initialized():
                log("✅ Ray ya está inicializado, reusando sesión existente")
            else:
                connected = False
                
                # 1. Try Cluster (if not forced local)
                if not self.force_local:
                    try:
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        
                        # WORKAROUND FOR SPACES IN PATH
                        if " " in current_dir:
                            safe_path = os.path.expanduser("~/.ray_safe_project_link")
                            if os.path.exists(safe_path) or os.path.islink(safe_path):
                                try: os.remove(safe_path)
                                except: pass
                            try:
                                os.symlink(current_dir, safe_path)
                                log(f"🔗 Enlace seguro creado para Ray: {safe_path}")
                                current_dir = safe_path
                            except: pass

                        runtime_env = {
                            "working_dir": current_dir,
                            "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv", "*.zip", "*.log"]
                        }
                        
                        ray_addr = os.environ.get("RAY_ADDRESS")
                        if ray_addr:
                            log(f"🌍 Conectando a Cluster remoto: {ray_addr}")
                        else:
                            log("⚠️  'RAY_ADDRESS' no detectada. Intentando autodescubrimiento local...")

                        ray.init(
                            address='auto', 
                            ignore_reinit_error=True, 
                            logging_level="ERROR",
                            runtime_env=runtime_env
                        )
                        
                        resources = ray.cluster_resources()
                        total_cpus = int(resources.get('CPU', 0))
                        
                        if total_cpus > 0:
                            log(f"✅ Conectado a Cluster Ray (Modo Distribuido). CPUs: {total_cpus}")
                            connected = True
                        else:
                            log(f"❌ ERROR: El cluster tiene 0 CPUs. Abortando modo distribuido.")
                            ray.shutdown()
                            connected = False
                    except Exception as e:
                        log(f"⚠️ No se encontró cluster o falló conexión: {e}")
                        if ray.is_initialized():
                            ray.shutdown()
                        connected = False
                
                # 2. Fallback to Local
                if not connected:
                    if self.force_local:
                         log("🔒 Modo Local Forzado por el usuario.")
                    else:
                         log("⚠️ Iniciando modo LOCAL (Fallback)...")
                         
                    try:
                        total_cores = os.cpu_count() or 4
                        safe_cores = max(1, total_cores - 2)
                        
                        ray.init(
                            address='local',
                            ignore_reinit_error=True,
                            num_cpus=safe_cores,
                            include_dashboard=False,
                            logging_level="ERROR"
                        )
                        log(f"✅ Ray inicializado en modo LOCAL ({safe_cores} CPUs)")
                    except Exception as e:
                        log(f"❌ Error inicializando Ray Local: {e}")
                        raise

            # Check cluster resources
            try:
                resources = ray.cluster_resources()
                total_cpus = int(resources.get('CPU', 0))
                total_nodes = int(resources.get('node:127.0.0.1', 0)) # Simple check, might be inaccurate for nodes
                # Better node count check
                nodes = ray.nodes()
                alive_nodes = [n for n in nodes if n['Alive']]
                
                log(f"💻 Recursos del Cluster:")
                log(f"   - Nodos Activos: {len(alive_nodes)}")
                log(f"   - CPUs Totales : {total_cpus}")
                
                for node in alive_nodes:
                    node_ip = node.get('NodeManagerAddress', 'Unknown')
                    log(f"     • Nodo: {node_ip}")
                    
            except Exception as e:
                log(f"⚠️  No se pudo verificar recursos: {e}")

            # Check local resources
            try:
                resources = ray.cluster_resources()
                total_cpus = int(resources.get('CPU', 0))
                log(f"💻 CPUs disponibles para workers: {total_cpus}")
            except Exception as e:
                log(f"⚠️  No se pudo verificar recursos: {e}")

            log(f"\n🎯 Iniciando optimización: {total_runs} combinaciones...")
            start_time = time.time()

            # Place the DataFrame in Ray's object store ONCE
            log("📦 Enviando datos al object store de Ray...")
            df_ref = ray.put(df)
            log("✅ Datos enviados")

            # Dispatch ALL tasks - FORCE SPREAD to use Worker immediately
            log(f"🚀 Despachando {len(grid)} tareas a los workers (Estrategia: {strategy_code}, Mode: SPREAD)...")
            futures = [run_backtest_task.options(scheduling_strategy="SPREAD").remote(df_ref, risk_level, params, strategy_code) for params in grid]
            log(f"✅ {len(futures)} tareas despachadas")

            
            unfinished = futures
            # completed_count handled before
            last_progress_update = 0
            tasks_since_save = 0
            last_heartbeat_time = time.time()
            
            # WAIT LOOP WITH RETRIES
            retry_counts = {} # index -> count
            
            while unfinished:
                # Check User Cancellation
                if cancel_event and cancel_event.is_set():
                    log("🛑 Optimización cancelada por el usuario")
                    for ref in unfinished:
                        ray.cancel(ref)
                    return pd.DataFrame(results)

                # Wait for completed tasks
                num_to_wait = min(5, len(unfinished)) if unfinished else 1
                done, unfinished = ray.wait(unfinished, num_returns=num_to_wait, timeout=1.0)

                if not done:
                    # Heartbeat log every 30 seconds
                    if time.time() - last_heartbeat_time > 30:
                         log(f"⏳ Procesando en paralelo... (Completados: {completed_count}/{total_runs})")
                         last_heartbeat_time = time.time()
                    continue

                for ref in done:
                    try:
                        res = ray.get(ref)
                        if 'error' in res:
                            log(f"❌ Error en worker: {res['error']}")
                            if 'traceback' in res:
                                log(f"Traceback:\n{res['traceback']}")
                            # Don't retry logic errors here yet, just log
                            completed_count += 1 # Count as done but failed
                            continue

                        full_res = res['params'].copy()
                        full_res.update(res['metrics'])
                        results.append(full_res)
                        completed_count += 1

                        # Calculate progress percentage
                        pct = completed_count / total_runs
                        
                        current_time = time.time()
                        should_update = (current_time - last_progress_update > 0.5) or (completed_count == total_runs)

                        # Log progress
                        log_interval = max(1, min(total_runs // 10, 50))
                        if should_update and (completed_count % log_interval == 0 or completed_count == total_runs):
                            log(f"✓ Completadas: {completed_count}/{total_runs} ({int(pct*100)}%)")

                        # Callback update
                        if progress_callback and should_update:
                            try:
                                progress_callback(pct)
                                last_progress_update = current_time
                            except: pass

                        # --- INCREMENTAL SAVE ---
                        tasks_since_save += 1
                        if tasks_since_save >= 10:
                            checkpoint_path = save_checkpoint(
                                "grid", param_ranges, risk_level, results, 
                                {'completed': completed_count, 'total': total_runs}, 
                                file_path=checkpoint_path
                            )
                            tasks_since_save = 0

                    except Exception as e:
                        # HANDLE CRASH / LOST OBJECT
                        log(f"❌ Error crítico obteniendo resultado: {e}")

            end_time = time.time()
            duration = end_time - start_time
            log(f"\n🏁 Optimización finalizada en {duration:.2f} segundos")
            log(f"✅ Resultados generados: {len(results)}")
            
            # Cleanup checkpoint on success ONLY if not cancelled
            if checkpoint_path and not (cancel_event and cancel_event.is_set()):
                delete_checkpoint(checkpoint_path)
                log("🗑️ Checkpoint temporal eliminado")


            df_results = pd.DataFrame(results)
            if not df_results.empty:
                df_results = df_results.sort_values(by='Total PnL', ascending=False)
                log(f"🏆 Mejor PnL: ${df_results.iloc[0]['Total PnL']:.2f}")
            else:
                log("⚠️  No se generaron resultados")

            return df_results

        except Exception as e:
            log(f"\n❌ ERROR CRÍTICO EN OPTIMIZER: {e}")
            import traceback
            log(traceback.format_exc())
            raise

import random

class GeneticOptimizer:
    def __init__(self, population_size=50, generations=10, mutation_rate=0.1, force_local=False):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.backtester = Backtester()
        self.force_local = force_local

    def _random_param(self, key, range_vals):
        """Generate a random parameter value from the range."""
        if isinstance(range_vals, list):
             return random.choice(range_vals)
        return random.choice(list(range_vals))

    def generate_initial_population(self, param_ranges):
        """Create random initial population."""
        population = []
        keys = list(param_ranges.keys())
        for _ in range(self.population_size):
            individual = {}
            for k in keys:
                individual[k] = self._random_param(k, param_ranges[k])
            population.append(individual)
        return population

    def selection(self, population_with_fitness):
        """Tournament selection to choose parents."""
        tournament_size = 3
        parents = []

        for _ in range(self.population_size):
            competitors = random.sample(population_with_fitness, k=min(tournament_size, len(population_with_fitness)))
            winner = max(competitors, key=lambda x: x['metrics']['Total PnL'])
            parents.append(winner['params'])

        return parents

    def crossover(self, parent1, parent2):
        """Single-point crossover."""
        if parent1 == parent2:
            return parent1.copy()

        keys = list(parent1.keys())
        point = random.randint(1, len(keys) - 1)

        child = {}
        for i, k in enumerate(keys):
            if i < point:
                child[k] = parent1[k]
            else:
                child[k] = parent2[k]
        return child

    def mutate(self, individual, param_ranges):
        """Randomly mutate genes."""
        mutated = individual.copy()
        for k in individual.keys():
            if random.random() < self.mutation_rate:
                mutated[k] = self._random_param(k, param_ranges[k])
        return mutated

    def optimize(self, df, param_ranges, risk_level="LOW", progress_callback=None, cancel_event=None, log_callback=None, strategy_code="HYBRID"):
        def log(msg):
            print(msg, flush=True)
            sys.stdout.flush()
            try:
                with open("debug_optimizer_trace.log", "a", encoding='utf-8') as f:
                    f.write(f"{datetime.now()} - {msg}\n")
            except: pass

            if log_callback:
                try:
                    log_callback(msg)
                except:
                    pass

        try:
            log("=" * 60)
            log("GENETIC ALGORITHM OPTIMIZER - INICIANDO")
            log("=" * 60)
            log(f"🧬 Población: {self.population_size}")
            log(f"🧬 Generaciones: {self.generations}")
            log(f"🧬 Tasa Mutación: {self.mutation_rate}")

            # --- CHECKPOINT CHECK ---
            checkpoint_path, checkpoint_data = find_compatible_checkpoint("genetic", param_ranges, risk_level)
            start_gen = 0
            population = None
            best_individual = None
            best_pnl = -float('inf')
            all_results = []

            if checkpoint_data:
                log(f"\n💾 CHECKPOINT DETECTADO: {checkpoint_data['last_updated']}")
                if 'current_gen' in checkpoint_data['metadata']:
                    start_gen = checkpoint_data['metadata']['current_gen'] + 1
                    population = checkpoint_data['metadata'].get('next_population')
                    best_individual = checkpoint_data['metadata'].get('best_individual')
                    best_pnl = checkpoint_data['metadata'].get('best_pnl', -float('inf'))
                    all_results = checkpoint_data['results']
                    log(f"✅ Recuperadas {start_gen} generaciones. Continuando desde Generación {start_gen + 1}...")
            


            # Initialize Ray - Supports both CLUSTER and LOCAL modes
            log("\n🔍 Inicializando Ray...")
            
            if ray.is_initialized():
                log("✅ Ray ya está inicializado, reusando sesión existente")
            else:
                connected = False
                
                if not self.force_local:
                    try:
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        runtime_env = {
                            "working_dir": current_dir,
                            "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv", "*.zip", "*.log"]
                        }
                        
                        ray_addr = os.environ.get("RAY_ADDRESS")
                        if ray_addr:
                            log(f"🌍 Conectando a Cluster remoto: {ray_addr}")
                        else:
                            log("⚠️  'RAY_ADDRESS' no detectada. Intentando autodescubrimiento local...")

                        ray.init(
                            address='auto', 
                            ignore_reinit_error=True, 
                            logging_level="ERROR",
                            runtime_env=runtime_env
                        )
                        
                        resources = ray.cluster_resources()
                        total_cpus = int(resources.get('CPU', 0))
                        
                        if total_cpus > 0:
                            log(f"✅ Conectado a Cluster Ray (Modo Distribuido). CPUs: {total_cpus}")
                            connected = True
                        else:
                            log(f"❌ ERROR: El cluster tiene 0 CPUs. Abortando modo distribuido.")
                            ray.shutdown()
                            time.sleep(1)
                            connected = False
                    except Exception as e:
                        log(f"⚠️ No se encontró cluster o falló conexión: {e}")
                        if ray.is_initialized():
                            ray.shutdown()
                            time.sleep(1)
                        connected = False
                
                if not connected:
                    if self.force_local:
                         log("🔒 Modo Local Forzado por el usuario.")
                    else:
                         log("⚠️ Iniciando modo LOCAL (Fallback)...")
                         
                    try:
                        # CALCULATE SAFE CPU LIMIT (Total - 2)
                        total_cores = os.cpu_count() or 4
                        safe_cores = max(1, total_cores - 2)
                        
                        log(f"⚙️ Configurando Ray LOCAL con {safe_cores}/{total_cores} CPUs (dejando 2 libres)")

                        ray.init(
                            address='local',
                            ignore_reinit_error=True,
                            num_cpus=safe_cores,
                            include_dashboard=False,
                            logging_level="ERROR"
                        )
                        log("✅ Ray inicializado en modo LOCAL")
                    except Exception as e:
                        log(f"❌ Error inicializando Ray: {e}")
                        raise
            
            # Check resources log
            try:
                resources = ray.cluster_resources()
                total_cpus = int(resources.get('CPU', 0))
                nodes = ray.nodes()
                alive_nodes = [n for n in nodes if n['Alive']]
                log(f"💻 Recursos del Cluster: {len(alive_nodes)} Nodos | {total_cpus} CPUs")
            except:
                pass

            start_time = time.time()
            df_ref = ray.put(df)

            # Generate initial population ONLY IF NOT RECOVERED
            if population is None:
                population = self.generate_initial_population(param_ranges)
            
            # best_individual etc initialized above
            
            last_progress_update = 0

            for gen in range(start_gen, self.generations):
                if cancel_event and cancel_event.is_set():
                     log("🛑 Optimización cancelada")
                     break

                log(f"\n🧬 Generación {gen + 1}/{self.generations}")

                # Evaluate population - FORCE SPREAD
                futures = [run_backtest_task.options(scheduling_strategy="SPREAD").remote(df_ref, risk_level, params, strategy_code) for params in population]
                gen_results = []

                # Wait for all results
                unfinished = futures

                while unfinished:
                    if cancel_event and cancel_event.is_set():
                         break
                    num_to_wait = min(5, len(unfinished)) if unfinished else 1
                    done, unfinished = ray.wait(unfinished, num_returns=num_to_wait, timeout=0.2)

                    for ref in done:
                        res = ray.get(ref)
                        if 'error' not in res:
                            full_res = res['params'].copy()
                            full_res.update(res['metrics'])
                            gen_results.append({
                                'params': res['params'],
                                'metrics': res['metrics']
                            })
                            all_results.append(full_res)

                        # REAL-TIME PROGRESS UPDATE
                        # Calculate total progress across generations
                        total_tasks_completed = (gen * self.population_size) + len(gen_results)
                        total_tasks_global = self.generations * self.population_size
                        progress = total_tasks_completed / total_tasks_global
                        
                        current_time = time.time()
                        should_update = (current_time - last_progress_update > 0.1) or (len(gen_results) == self.population_size)

                        if progress_callback and should_update:
                            try:
                                progress_callback(progress)
                                last_progress_update = current_time
                            except:
                                pass

                if cancel_event and cancel_event.is_set():
                     break

                # Check for best
                if gen_results:
                    gen_best = max(gen_results, key=lambda x: x['metrics']['Total PnL'])
                    if gen_best['metrics']['Total PnL'] > best_pnl:
                        best_pnl = gen_best['metrics']['Total PnL']
                        best_individual = gen_best
                        log(f"🏆 Nuevo mejor PnL: ${best_pnl:.2f}")

                # Update progress
                progress = (gen + 1) / self.generations
                current_time = time.time()
                should_update = (current_time - last_progress_update > 0.5) or (gen == self.generations - 1)

                if progress_callback and should_update:
                    progress_callback(progress)
                    last_progress_update = current_time

                if gen == self.generations - 1:
                    break

                # Selection, Crossover, Mutation
                parents = self.selection(gen_results)
                next_population = [best_individual['params']]  # Elitism

                while len(next_population) < self.population_size:
                    p1 = random.choice(parents)
                    p2 = random.choice(parents)
                    child = self.crossover(p1, p2)
                    child = self.mutate(child, param_ranges)
                    next_population.append(child)

                population = next_population
                
                # --- SAVE CHECKPOINT AFTER GEN ---
                checkpoint_path = save_checkpoint(
                    "genetic",
                    param_ranges,
                    risk_level,
                    all_results,
                    {
                        'current_gen': gen,
                        'next_population': population,
                        'best_individual': best_individual,
                        'best_pnl': best_pnl
                    },
                    file_path=checkpoint_path
                )
                log(f"💾 Checkpoint guardado (Gen {gen+1})")

            end_time = time.time()
            log(f"\n🏁 Optimización finalizada en {end_time - start_time:.2f}s")
            
            # Cleanup checkpoint ONLY if not cancelled
            if checkpoint_path and not (cancel_event and cancel_event.is_set()):
                delete_checkpoint(checkpoint_path)
                log("🗑️ Checkpoint temporal eliminado")

            df_results = pd.DataFrame(all_results)
            if not df_results.empty:
                df_results = df_results.sort_values(by='Total PnL', ascending=False)
                log(f"🏆 Mejor PnL: ${df_results.iloc[0]['Total PnL']:.2f}")

            return df_results

        except Exception as e:
            log(f"\n❌ ERROR CRÍTICO: {e}")
            import traceback
            log(traceback.format_exc())
            raise


# --- BAYESIAN OPTIMIZER (Optuna) ---
class BayesianOptimizer:
    """
    Bayesian Optimization using Optuna's TPE (Tree-structured Parzen Estimator).
    More intelligent than Grid/Genetic - learns from each evaluation to suggest better parameters.
    """
    
    def __init__(self, n_trials=100, pruning=True, force_local=False):
        self.n_trials = n_trials
        self.pruning = pruning
        self.backtester = Backtester()
        self.force_local = force_local
    
    def optimize(self, df, param_ranges, risk_level="LOW", progress_callback=None, cancel_event=None, log_callback=None, strategy_code="HYBRID"):
        def log(msg):
            print(msg, flush=True)
            sys.stdout.flush()
            try:
                with open("debug_optimizer_trace.log", "a", encoding='utf-8') as f:
                    f.write(f"{datetime.now()} - {msg}\n")
            except: pass

            if log_callback:
                try:
                    log_callback(msg)
                except:
                    pass
        
        try:
            import optuna
            from optuna.samplers import TPESampler
            
            # Suppress Optuna's verbose logging
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            
            log("=" * 60)
            log("🧠 BAYESIAN OPTIMIZER (Optuna TPE) - INICIANDO")
            log("=" * 60)
            log(f"🎯 Trials: {self.n_trials}")
            log(f"✂️ Pruning: {'Enabled' if self.pruning else 'Disabled'}")
            log(f"📊 Estrategia: {strategy_code}")
            
            all_results = []
            best_pnl = -float('inf')
            best_params = None
            start_time = time.time()
            
            # Initialize Ray
            log("\n🔍 Inicializando Ray...")
            
            if ray.is_initialized():
                log("✅ Ray ya está inicializado, reusando sesión existente")
            else:
                connected = False
                
                if not self.force_local:
                    try:
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        runtime_env = {
                            "working_dir": current_dir,
                            "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv", "*.zip", "*.log"]
                        }
                        
                        ray_addr = os.environ.get("RAY_ADDRESS")
                        if ray_addr:
                            log(f"🌍 Conectando a Cluster remoto: {ray_addr}")
                        else:
                            log("⚠️  'RAY_ADDRESS' no detectada. Intentando autodescubrimiento local...")

                        ray.init(
                            address='auto', 
                            ignore_reinit_error=True, 
                            logging_level="ERROR",
                            runtime_env=runtime_env
                        )
                        
                        # Verify we actually have resources
                        resources = ray.cluster_resources()
                        total_cpus = int(resources.get('CPU', 0))
                        
                        if total_cpus > 0:
                            log(f"✅ Conectado a Cluster Ray (Distribuido). CPUs: {total_cpus}")
                            connected = True
                        else:
                            log(f"❌ ERROR: El cluster tiene 0 CPUs. Abortando modo distribuido.")
                            ray.shutdown()
                            time.sleep(1)
                            connected = False
                            
                    except Exception as e:
                        log(f"⚠️ No se encontró cluster o falló conexión: {e}")
                        if ray.is_initialized():
                            ray.shutdown()
                            time.sleep(1)
                        connected = False
                
                if not connected:
                    if self.force_local:
                         log("🔒 Modo Local Forzado por el usuario.")
                    else:
                         log("⚠️ Iniciando modo LOCAL (Fallback)...")
                         
                    try:
                        total_cores = os.cpu_count() or 4
                        safe_cores = max(1, total_cores - 2)
                        
                        ray.init(
                            address='local',
                            ignore_reinit_error=True,
                            num_cpus=safe_cores,
                            include_dashboard=False,
                            logging_level="ERROR"
                        )
                        log(f"✅ Ray inicializado en modo LOCAL ({safe_cores} CPUs)")
                    except Exception as e:
                        log(f"⚠️ No se pudo inicializar Ray: {e}")
                        log("Continuando en modo secuencial...")
            
            # Log cluster resources
            if ray.is_initialized():
                resources = ray.cluster_resources()
                nodes = ray.nodes()
                active_nodes = [n for n in nodes if n.get('alive', False)]
                log(f"📡 Cluster: {len(active_nodes)} nodos activos, {int(resources.get('CPU', 0))} CPUs totales")
            
            # Prepare data reference for Ray
            df_ref = ray.put(df) if ray.is_initialized() else df
            
            # Create the objective function for Optuna
            trial_count = [0]  # Mutable counter
            
            class UserCancelled(BaseException):
                pass
                
            def objective(trial):
                # Check cancellation at start of trial
                if cancel_event and cancel_event.is_set():
                    raise UserCancelled("Optimization cancelled by user")
                
                # Sample parameters from the search space
                params = {}
                for key, values in param_ranges.items():
                    if isinstance(values[0], float):
                        # Float parameter
                        params[key] = trial.suggest_float(key, min(values), max(values))
                    elif isinstance(values[0], int):
                        # Integer parameter
                        params[key] = trial.suggest_int(key, min(values), max(values))
                    else:
                        # Categorical parameter
                        params[key] = trial.suggest_categorical(key, values)
                
                trial_count[0] += 1
                current_trial = trial_count[0]
                
                log(f"\n🔬 Trial {current_trial}/{self.n_trials}")
                log(f"   Params: {params}")
                
                # Run backtest using Ray
                # Run backtest using Ray
                try:
                    if ray.is_initialized():
                        # Run as remote task
                        future = run_backtest_task.remote(df_ref, risk_level, params, strategy_code)
                        result = ray.get(future, timeout=300)
                    else:
                        # Run locally (bypass Ray remote wrapper)
                        try:
                            result = run_backtest_task._function(df, risk_level, params, strategy_code)
                        except AttributeError:
                             # Fallback if _function is not available (older Ray versions)
                             # In this case we might fail if we can't call the underlying function
                             # But we will simulate an error return
                             log("⚠️ Cannot run remote function locally without access to underlying function")
                             result = None
                    
                    if result is None:
                        log(f"   ⚠️ Sin resultado (timeout o error)")
                        return -float('inf')
                    
                    if 'error' in result:
                        log(f"   ⚠️ Error en backtest: {result['error']}")
                        return -float('inf')
                    
                    # Extract metrics correctly (nested in 'metrics' key)
                    metrics = result.get('metrics', {})
                    
                    # Ensure minimal keys exist to prevent DataFrame sort errors
                    if 'Total PnL' not in metrics:
                        metrics['Total PnL'] = 0.0
                    
                    pnl = metrics.get('Total PnL', 0.0)
                    trades = metrics.get('Total Trades', 0)
                    
                    # Store result (FLATTENED for DataFrame)
                    # Merge params and metrics into a single flat dictionary
                    flat_result = {**result.get('params', {}), **metrics}
                    all_results.append(flat_result)
                    
                    log(f"   💰 PnL: ${pnl:.2f} | Trades: {trades}")
                    
                    # Store metrics in trial for persistence using correct Optuna API
                    for k, v in metrics.items():
                        trial.set_user_attr(k, v)
                    
                    # Update progress
                    if progress_callback:
                        progress = current_trial / self.n_trials
                        try:
                            progress_callback(progress)
                        except:
                            pass
                    
                    # Return PnL as the objective (Optuna will maximize)
                    return pnl
                    
                except Exception as e:
                    log(f"   ❌ Error: {e}")
                    return -float('inf')
            
            # Create study with storage for checkpointing
            ensure_checkpoint_dir()
            storage_path = f"sqlite:///{CHECKPOINT_DIR}/optuna_study.db"
            study_name = f"bayesian_{hashlib.md5(str(param_ranges).encode()).hexdigest()[:8]}"
            
            # Try to load existing study or create new
            try:
                study = optuna.create_study(
                    study_name=study_name,
                    storage=storage_path,
                    sampler=TPESampler(seed=42),
                    direction="maximize",
                    load_if_exists=True
                )
                
                if len(study.trials) > 0:
                    log(f"\n💾 ESTUDIO EXISTENTE DETECTADO: {len(study.trials)} trials previos")
                    log(f"   Mejor PnL histórico: ${study.best_value:.2f}")
                    remaining_trials = max(0, self.n_trials - len(study.trials))
                    log(f"   Trials restantes: {remaining_trials}")
                    self.n_trials = remaining_trials
                    
            except Exception as e:
                log(f"⚠️ No se pudo crear storage SQL, usando memoria: {e}")
                study = optuna.create_study(
                    sampler=TPESampler(seed=42),
                    direction="maximize"
                )
            
            # Run optimization
            log(f"\n🚀 Iniciando {self.n_trials} trials de optimización Bayesiana...")
            
            # Determine n_jobs for parallel execution
            n_jobs = 1
            if ray.is_initialized():
                try:
                    cluster_cpus = int(ray.cluster_resources().get('CPU', 1))
                    if self.force_local:
                         # Use local safe count
                         n_jobs = max(1, os.cpu_count() - 2)
                    else:
                        # Use CLUSTER cores. 
                        # Optuna uses threading (TPE is thread safe).
                        # We launch N threads, each waits on a Ray remote task.
                        n_jobs = cluster_cpus
                        
                    log(f"🚀 Ejecutando Optuna en paralelo con n_jobs={n_jobs}")
                except:
                    n_jobs = 1
            
            if self.n_trials > 0:
                study.optimize(
                    objective, 
                    n_trials=self.n_trials,
                    n_jobs=n_jobs, # Enable Parallelism
                    show_progress_bar=False,
                    catch=(Exception,)
                )
            
            end_time = time.time()
            
            # Get best results
            log(f"\n🏁 Optimización Bayesiana finalizada en {end_time - start_time:.2f}s")
            log(f"📊 Total trials ejecutados: {len(study.trials)}")
            
            if len(study.trials) > 0:
                best_trial = study.best_trial
                log(f"\n🏆 MEJORES PARÁMETROS ENCONTRADOS:")
                log(f"   PnL: ${study.best_value:.2f}")
                for k, v in best_trial.params.items():
                    log(f"   {k}: {v}")
                
                # Log optimization insights
                log(f"\n📈 INSIGHTS DE LA OPTIMIZACIÓN:")
                log(f"   Trials completados: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
                log(f"   Trials fallidos: {len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL])}")
            
            # Reconstruct results from ALL trials (including recovered ones)
            # This ensures we return a full DataFrame even if we resumed a finished study
            all_results = []
            for t in study.trials:
                if t.state == optuna.trial.TrialState.COMPLETE:
                    # Start with params
                    row = t.params.copy()
                    
                    # Add PnL (Objective Value)
                    row['Total PnL'] = t.value
                    
                    # Add stored metrics (if any) - handles recovery from DB
                    for k, v in t.user_attrs.items():
                        row[k] = v
                        
                    all_results.append(row)

            # Return results as DataFrame
            df_results = pd.DataFrame(all_results)
            if not df_results.empty:
                # Ensure Total PnL is float
                if 'Total PnL' in df_results.columns:
                     df_results['Total PnL'] = df_results['Total PnL'].astype(float)
                
                df_results = df_results.sort_values(by='Total PnL', ascending=False)
            
            return df_results
            
        except Exception as e:
            log(f"\n❌ ERROR CRÍTICO: {e}")
            import traceback
            log(traceback.format_exc())
            raise
