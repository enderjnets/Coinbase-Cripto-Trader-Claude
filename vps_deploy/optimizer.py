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
@ray.remote
def run_backtest_task(df, risk_level, params):
    import signal
    
    # Timeout Handler per task (30 seconds max)
    def handler(signum, frame):
        raise TimeoutError("Backtest exceeded 30s execution time limit")
    
    # Register signal for Timeout (Unix/Mac only)
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(30) # 30 seconds limit
    
    try:
        # Re-instantiate backtester locally in the worker
        bt = Backtester()
        _, trades = bt.run_backtest(df, risk_level=risk_level, strategy_params=params)

        total_trades = len(trades)
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
    def __init__(self):
        self.backtester = Backtester()

    def generate_grid(self, param_ranges):
        keys = param_ranges.keys()
        values = param_ranges.values()
        combinations = list(itertools.product(*values))
        grid = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            grid.append(params)
        return grid

    def optimize(self, df, param_ranges, risk_level="LOW", progress_callback=None, cancel_event=None, log_callback=None):
        def log(msg):
            print(msg, flush=True)
            sys.stdout.flush()
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
                log("✅ Ray ya está inicializado, reusando sesión existente (Cluster o Local)")
            else:
                # Check if we should connect to an existing cluster (e.g. started via start_cluster_head.py)
                try:
                    # Try connecting to existing local cluster first
                    # Auto-ship code to workers so they don't need manual copy
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    runtime_env = {
                        "working_dir": current_dir,
                        "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv"]
                    }
                    
                    ray.init(
                        address='auto', 
                        ignore_reinit_error=True, 
                        logging_level="ERROR",
                        runtime_env=runtime_env
                    )
                    log("✅ Conectado a Cluster Ray existente (Modo Distribuido + Code Sync)")
                except:
                    # Fallback to Local Mode if no cluster found
                    log("⚠️ No se encontró cluster, iniciando modo LOCAL...")
                    try:
                        # CALCULATE SAFE CPU LIMIT (Total - 2)
                        total_cores = os.cpu_count() or 4
                        safe_cores = max(1, total_cores - 2)
                        
                        log(f"⚙️ Configurando Ray LOCAL con {safe_cores}/{total_cores} CPUs (dejando 2 libres)")

                        # FORCE LOCAL MODE ONLY - no cluster, no distributed
                        ray.init(
                            ignore_reinit_error=True,
                            num_cpus=safe_cores,  # Use safe limit
                            include_dashboard=False,  # Disable dashboard
                            logging_level="ERROR",  # Reduce noise
                            _temp_dir="/tmp/ray"  # Use standard temp dir
                        )
                        log("✅ Ray inicializado en modo LOCAL")
                    except Exception as e:
                        log(f"❌ Error inicializando Ray: {e}")
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

            # Dispatch ALL tasks
            log(f"🚀 Despachando {len(grid)} tareas a los workers...")
            futures = [run_backtest_task.remote(df_ref, risk_level, params) for params in grid]
            log(f"✅ {len(futures)} tareas despachadas")

            
            unfinished = futures
            # completed_count handled before
            last_progress_update = 0
            tasks_since_save = 0
            
            log("\n⏳ Esperando resultados...")
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
                    continue

                for ref in done:
                    try:
                        res = ray.get(ref)
                        if 'error' in res:
                            log(f"❌ Error en worker: {res['error']}")
                            if 'traceback' in res:
                                log(f"Traceback:\n{res['traceback']}")
                            continue

                        full_res = res['params'].copy()
                        full_res.update(res['metrics'])
                        results.append(full_res)
                        completed_count += 1

                        # Calculate progress percentage
                        pct = completed_count / total_runs
                        
                        current_time = time.time()
                        should_update = (current_time - last_progress_update > 0.5) or (completed_count == total_runs)

                        # Log progress more frequently (every 10% OR every 50 tasks)
                        log_interval = max(1, min(total_runs // 10, 50))
                        if should_update and (completed_count % log_interval == 0 or completed_count == total_runs):
                            log(f"✓ Completadas: {completed_count}/{total_runs} ({int(pct*100)}%)")

                        # RATE LIMITED progress bar update
                        if progress_callback and should_update:
                            try:
                                progress_callback(pct)
                                last_progress_update = current_time
                            except Exception as e:
                                # Don't spam errors
                                if completed_count % 10 == 0:
                                    log(f"⚠️ Error actualizando progreso: {e}")

                        # --- INCREMENTAL SAVE ---
                        tasks_since_save += 1
                        if tasks_since_save >= 10:
                            save_checkpoint(
                                "grid", 
                                param_ranges, 
                                risk_level, 
                                results, 
                                {'completed': completed_count, 'total': total_runs},
                                file_path=checkpoint_path
                            )
                            tasks_since_save = 0
                            # Update checkpoint_path if it was None (first save)
                            if not checkpoint_path:
                                # Find it again or we need to capture the return from save_checkpoint
                                # Better: just find it via hash/glob or assign it. 
                                # Since save_checkpoint returns path, we should use it.
                                # But save_checkpoint helper calls are simple.
                                # Let's fix save_checkpoint usage above or just re-search.
                                # Actually, save_checkpoint is called, but we didn't assign return.
                                # Let's fix that.
                                pass 
                            # Re-save properly assigning path
                            checkpoint_path = save_checkpoint(
                                "grid", 
                                param_ranges, 
                                risk_level, 
                                results, 
                                {'completed': completed_count, 'total': total_runs},
                                file_path=checkpoint_path
                            )

                    except Exception as e:
                        log(f"❌ Error procesando resultado: {e}")
                        import traceback
                        log(traceback.format_exc())

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
    def __init__(self, population_size=50, generations=10, mutation_rate=0.1):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.backtester = Backtester()

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

    def optimize(self, df, param_ranges, risk_level="LOW", progress_callback=None, cancel_event=None, log_callback=None):
        def log(msg):
            print(msg, flush=True)
            sys.stdout.flush()
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
                try:
                     # Try connecting to existing local cluster first
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    runtime_env = {
                        "working_dir": current_dir,
                        "excludes": ["data", "vps_package", ".venv", "worker_env", ".git", "__pycache__", "*.csv"]
                    }
                    
                    ray.init(
                        address='auto', 
                        ignore_reinit_error=True, 
                        logging_level="ERROR",
                        runtime_env=runtime_env
                    )
                    log("✅ Conectado a Cluster Ray existente (Modo Distribuido + Code Sync)")
                except:
                    try:
                        # CALCULATE SAFE CPU LIMIT (Total - 2)
                        total_cores = os.cpu_count() or 4
                        safe_cores = max(1, total_cores - 2)
                        
                        log(f"⚙️ Configurando Ray LOCAL con {safe_cores}/{total_cores} CPUs (dejando 2 libres)")

                        ray.init(
                            ignore_reinit_error=True,
                            num_cpus=safe_cores,
                            include_dashboard=False,
                            logging_level="ERROR",
                            _temp_dir="/tmp/ray"
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

                # Evaluate population
                futures = [run_backtest_task.remote(df_ref, risk_level, params) for params in population]
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
