import itertools
import pandas as pd
import time
import os

# Enable Ray Multi-Node on macOS
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

import ray
from backtester import Backtester

# Ray Remote Function (Worker)
@ray.remote
def run_backtest_task(df, risk_level, params):
    try:
        # Re-instantiate backtester locally in the worker
        # This ensures thread-safety and proper state
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
        return {'error': str(e)}

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
            print(msg)
            if log_callback:
                log_callback(msg)

        log("Generando grid de parámetros...")
        grid = self.generate_grid(param_ranges)
        total_runs = len(grid)
        results = []

        log(f"🔍 Detectando cluster distribuido...")
        
        # Smart Cluster Detection
        cluster_mode = "local"  # default
        remote_workers = 0
        
        if not ray.is_initialized():
            try:
                # Try connecting to existing cluster first
                current_dir = os.path.dirname(os.path.abspath(__file__))
                ray.init(
                    address='auto',
                    ignore_reinit_error=True,
                    runtime_env={
                        "working_dir": current_dir,
                        "excludes": [".venv", "__pycache__", "data", "*.log", ".git"]  # Exclude large files
                    }
                )
                log("✅ Conectado a cluster Ray existente")
                cluster_mode = "distributed"
            except Exception as e:
                # No cluster found, start local
                log("⚠️  No se detectó cluster distribuido, iniciando modo local...")
                current_dir = os.path.dirname(os.path.abspath(__file__))
                ray.init(
                    ignore_reinit_error=True,
                    num_cpus=None,  # Use all local CPUs
                    runtime_env={
                        "working_dir": current_dir,
                        "excludes": [".venv", "__pycache__", "data", "*.log", ".git"]
                    }
                )
                cluster_mode = "local"
        
        # Check cluster resources and remote workers
        try:
            nodes = ray.nodes()
            resources = ray.cluster_resources()
            total_cpus = resources.get('CPU', 0)
            
            # Count remote workers (nodes that are NOT the head node)
            local_node_count = 0
            remote_node_count = 0
            for node in nodes:
                if node.get('alive', False):
                    # Check if this is the head node
                    if 'node:__internal_head__' in node.get('Resources', {}):
                        local_node_count += 1
                    else:
                        remote_node_count += 1
                        remote_workers += node.get('Resources', {}).get('CPU', 0)
            
            # Determine actual mode based on worker availability
            if remote_node_count > 0 and cluster_mode == "distributed":
                log(f"🚀 MODO DISTRIBUIDO ACTIVADO")
                log(f"   └─ Nodos remotos: {remote_node_count}")
                log(f"   └─ CPUs remotas: {int(remote_workers)}")
                log(f"   └─ CPUs totales: {int(total_cpus)}")
            else:
                cluster_mode = "local"
                log(f"💻 MODO LOCAL (solo esta Mac)")
                log(f"   └─ CPUs disponibles: {int(total_cpus)}")
                
        except Exception as e:
            log(f"⚠️  Error verificando cluster: {e}")
            cluster_mode = "local"

        log(f"\n🎯 Iniciando optimización: {total_runs} combinaciones...")
        start_time = time.time()

        # Place the large Dataframe into the Ray Object Store ONCE.
        # This is much faster than pickling it for every single task.
        df_ref = ray.put(df)
        
        # Dispatch ALL tasks to the cluster
        # Ray will handle scheduling them across all available cores/nodes.
        futures = [run_backtest_task.remote(df_ref, risk_level, params) for params in grid]
        log(f"Dispatched {len(futures)} tasks to the cluster...")

        unfinished = futures
        completed_count = 0
        
        while unfinished:
            # Check User Cancellation
            if cancel_event and cancel_event.is_set():
                log("Optimization Cancelled by User.")
                # Cancel pending tasks to free resources
                for ref in unfinished:
                    ray.cancel(ref)
                return pd.DataFrame(results)

            # Wait for completed tasks (timeout ensures we check cancel loop often)
            # return when at least 1 task is done or 0.5s passed
            # FIX: num_returns must not exceed number of unfinished tasks
            num_to_wait = min(5, len(unfinished)) if unfinished else 1
            done, unfinished = ray.wait(unfinished, num_returns=num_to_wait, timeout=0.5)
            
            if not done:
                continue
                
            for ref in done:
                try:
                    res = ray.get(ref)
                    if 'error' in res:
                        log(f"Worker Error: {res['error']}")
                        continue
                    
                    full_res = res['params'].copy()
                    full_res.update(res['metrics'])
                    results.append(full_res)
                    completed_count += 1
                except Exception as e:
                    log(f"Task Execution Error: {e}")

            # Update Progress Bar
            if progress_callback:
                 progress_callback(completed_count / total_runs)

        end_time = time.time()
        duration = end_time - start_time
        log(f"Optimization finished in {duration:.2f} seconds.")
        
        df_results = pd.DataFrame(results)
        if not df_results.empty:
            df_results = df_results.sort_values(by='Total PnL', ascending=False)
            
        return df_results

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
             # Check if it's a fixed list of options or a range
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
        # Tournament size = 3
        tournament_size = 3
        parents = []
        
        for _ in range(self.population_size):
            # Select random competitors
            competitors = random.sample(population_with_fitness, k=min(tournament_size, len(population_with_fitness)))
            # Choose the one with highest Total PnL
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
            print(msg)
            if log_callback:
                log_callback(msg)

        log(f"🧬 Iniciando Algoritmo Genético")
        log(f"   └─ Población: {self.population_size}")
        log(f"   └─ Generaciones: {self.generations}")
        log(f"   └─ Tasa Mutación: {self.mutation_rate}")

        # --- Ray Cluster Setup (Same as GridOptimizer) ---
        log(f"🔍 Verificando cluster distribuido...")
        if not ray.is_initialized():
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                ray.init(
                    address='auto',
                    ignore_reinit_error=True,
                    runtime_env={
                        "working_dir": current_dir,
                        "excludes": [".venv", "__pycache__", "data", "*.log", ".git"]
                    }
                )
                log("✅ Conectado a cluster Ray existente")
            except:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                ray.init(
                    ignore_reinit_error=True,
                    runtime_env={
                        "working_dir": current_dir,
                        "excludes": [".venv", "__pycache__", "data", "*.log", ".git"]
                    }
                )
                log("💻 Iniciando modo local (Head Node)")
        else:
             log("✅ Ray ya inicializado")

        # Smart Cluster Info
        try:
             nodes = ray.nodes()
             remote_nodes = sum(1 for n in nodes if n.get('alive') and 'node:__internal_head__' not in n.get('Resources', {}))
             total_cpus = ray.cluster_resources().get('CPU', 0)
             if remote_nodes > 0:
                 log(f"🚀 CLUSTER ACTIVO: {remote_nodes} workers remotos ({int(total_cpus)} CPUs total)")
             else:
                 log(f"💻 MODO LOCAL: {int(total_cpus)} CPUs")
        except:
             pass

        start_time = time.time()
        
        # Put Dataframe in Object Store
        df_ref = ray.put(df)

        # 1. Initialization
        population = self.generate_initial_population(param_ranges)
        best_individual = None
        best_pnl = -float('inf')
        all_results = []

        for gen in range(self.generations):
            if cancel_event and cancel_event.is_set():
                 log("🛑 Optimización cancelada por el usuario.")
                 break

            log(f"\n🧬 Generación {gen + 1}/{self.generations} evaluando...")
            
            # 2. Evaluation (Distributed)
            futures = [run_backtest_task.remote(df_ref, risk_level, params) for params in population]
            
            # Prepare generation results
            gen_results = []
            
            # Wait for results
            unfinished = futures
            while unfinished:
                if cancel_event and cancel_event.is_set():
                     break
                # FIX: Only wait for available tasks
                num_to_wait = min(len(unfinished), len(unfinished)) if unfinished else 1
                done, unfinished = ray.wait(unfinished, num_returns=num_to_wait, timeout=0.5)
                for ref in done:
                    res = ray.get(ref)
                    if 'error' not in res:
                        full_res = res['params'].copy()
                        full_res.update(res['metrics'])
                        # Structure for internal GA logic
                        gen_results.append({
                            'params': res['params'],
                            'metrics': res['metrics']
                        })
                        # Structure for final dataframe (flattened)
                        all_results.append(full_res)
            
            if cancel_event and cancel_event.is_set():
                 break

            # Check for best in this generation
            gen_best = max(gen_results, key=lambda x: x['metrics']['Total PnL'])
            if gen_best['metrics']['Total PnL'] > best_pnl:
                best_pnl = gen_best['metrics']['Total PnL']
                best_individual = gen_best
                log(f"🏆 Nuevo Mejor PnL: ${best_pnl:.2f} (Trades: {gen_best['metrics']['Total Trades']})")

            # Update Progress
            overall_progress = (gen + 1) / self.generations
            if progress_callback:
                progress_callback(overall_progress)

            # If last generation, stop
            if gen == self.generations - 1:
                break

            # 3. Selection
            parents = self.selection(gen_results)

            # 4. Crossover & 5. Mutation
            next_population = []
            # Elitism: Keep the absolute best
            next_population.append(best_individual['params'])
            
            while len(next_population) < self.population_size:
                p1 = random.choice(parents)
                p2 = random.choice(parents)
                child = self.crossover(p1, p2)
                child = self.mutate(child, param_ranges)
                next_population.append(child)
            
            population = next_population

        end_time = time.time()
        log(f"\n🏁 Optimización Genética Finalizada en {end_time - start_time:.2f}s")
        
        df_results = pd.DataFrame(all_results)
        if not df_results.empty:
            df_results = df_results.sort_values(by='Total PnL', ascending=False)
            
        return df_results
