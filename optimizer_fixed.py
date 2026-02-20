import itertools
import pandas as pd
import time
import os
import sys

# Enable Ray Multi-Node on macOS
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

import ray
from backtester import Backtester

# Ray Remote Function (Worker)
@ray.remote
def run_backtest_task(df, risk_level, params):
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
        return {'error': str(e), 'traceback': traceback.format_exc()}

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

            # Initialize Ray in LOCAL MODE ONLY (no cluster)
            log("\n🔍 Inicializando Ray (modo LOCAL)...")

            if ray.is_initialized():
                log("⚠️  Ray ya estaba inicializado, usando sesión existente")
            else:
                try:
                    # Start ONLY in local mode, do NOT connect to cluster
                    ray.init(
                        ignore_reinit_error=True,
                        num_cpus=None,  # Use all local CPUs
                        include_dashboard=False,  # Disable dashboard to avoid port conflicts
                        logging_level="ERROR"  # Reduce Ray logging noise
                    )
                    log("✅ Ray inicializado en modo LOCAL")
                except Exception as e:
                    log(f"❌ Error inicializando Ray: {e}")
                    raise

            # Check resources
            try:
                resources = ray.cluster_resources()
                total_cpus = int(resources.get('CPU', 0))
                log(f"💻 CPUs disponibles: {total_cpus}")
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
            completed_count = 0

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

                        # Log progress every 10%
                        pct = completed_count / total_runs
                        if completed_count % max(1, total_runs // 10) == 0 or completed_count == total_runs:
                            log(f"✓ Completadas: {completed_count}/{total_runs} ({int(pct*100)}%)")
                    except Exception as e:
                        log(f"❌ Error procesando resultado: {e}")
                        import traceback
                        log(traceback.format_exc())

                # Update Progress Bar
                if progress_callback:
                    try:
                        progress_callback(completed_count / total_runs)
                    except Exception as e:
                        log(f"Error actualizando progreso: {e}")

            end_time = time.time()
            duration = end_time - start_time
            log(f"\n🏁 Optimización finalizada en {duration:.2f} segundos")
            log(f"✅ Resultados generados: {len(results)}")

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

            # Initialize Ray in LOCAL MODE
            log("\n🔍 Inicializando Ray (modo LOCAL)...")
            if not ray.is_initialized():
                ray.init(ignore_reinit_error=True, include_dashboard=False, logging_level="ERROR")
                log("✅ Ray inicializado")
            else:
                log("✅ Ray ya inicializado")

            start_time = time.time()
            df_ref = ray.put(df)

            # Generate initial population
            population = self.generate_initial_population(param_ranges)
            best_individual = None
            best_pnl = -float('inf')
            all_results = []

            for gen in range(self.generations):
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
                    num_to_wait = min(len(unfinished), len(unfinished)) if unfinished else 1
                    done, unfinished = ray.wait(unfinished, num_returns=num_to_wait, timeout=1.0)

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
                if progress_callback:
                    progress_callback(progress)

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

            end_time = time.time()
            log(f"\n🏁 Optimización finalizada en {end_time - start_time:.2f}s")

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
