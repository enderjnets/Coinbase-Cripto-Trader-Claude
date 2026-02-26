import random
import copy
import json
try:
    import ray
    HAS_RAY = True
except ImportError:
    HAS_RAY = False
import pandas as pd
import time
from datetime import datetime
from collections import Counter

try:
    from optimizer import run_backtest_task
except ImportError:
    pass

try:
    from numba_backtester import numba_evaluate_population, HAS_NUMBA, warmup_jit
    if HAS_NUMBA:
        warmup_jit()
except ImportError:
    HAS_NUMBA = False

# Futures support
try:
    from numba_futures_backtester import (
        numba_evaluate_futures_population,
        warmup_jit_futures,
        FEE_MAKER as FUTURES_FEE
    )
    HAS_FUTURES_NUMBA = HAS_NUMBA
    if HAS_FUTURES_NUMBA:
        warmup_jit_futures()
except ImportError:
    HAS_FUTURES_NUMBA = False
    FUTURES_FEE = 0.0002

class StrategyMiner:
    """
    Genetic Algorithm to discover optimal trading strategies.
    NOW WITH:
    - Advanced indicators (Stochastic, Ichimoku, OBV, VWAP, ROC, CCI, Williams %R)
    - Optimized Genetic Algorithm (adaptive mutation, population diversity)
    - Risk Management (trailing stop, breakeven)
    - Multi-timeframe support
    - ML-enhanced fitness function
    - FUTURES SUPPORT: Long/Short, Leverage 1-10x, Funding rates
    """
    def __init__(self, df, population_size=100, generations=20, risk_level="LOW",
                 force_local=False, ray_address="auto", ml_enhanced=False,
                 seed_genomes=None, seed_ratio=0.5, market_type="SPOT",
                 max_leverage=10, is_perpetual=True):
        self.df = df
        self.pop_size = population_size
        self.generations = generations
        self.risk_level = risk_level
        self.force_local = force_local
        self.ml_enhanced = ml_enhanced
        self.seed_genomes = seed_genomes or []
        self.seed_ratio = seed_ratio

        # Futures support
        self.market_type = market_type.upper() if market_type else "SPOT"
        self.is_futures = self.market_type == "FUTURES"
        self.max_leverage = min(max_leverage, 10)  # Coinbase max 10x
        self.is_perpetual = is_perpetual

        ray_init = HAS_RAY and ray.is_initialized()
        
        # === TODOS LOS INDICADORES DISPONIBLES ===
        self.basic_indicators = ["RSI", "SMA", "EMA", "VOLSMA"]
        self.macd_indicators = ["MACD", "MACD_Signal", "MACD_Hist"]
        self.atr_indicators = ["ATR", "ATR_Pct"]
        self.bb_indicators = ["BB_Upper", "BB_Lower", "BB_Width", "BB_Position"]
        self.adx_indicators = ["ADX", "DI_Plus", "DI_Minus"]
        self.stoch_indicators = ["STOCH_K", "STOCH_D"]
        self.ichimoku_indicators = ["ICHIMOKU_Conv", "ICHIMOKU_Base", "ICHIMOKU_SpanA", "ICHIMOKU_SpanB"]
        self.volume_indicators = ["OBV", "VWAP"]
        self.momentum_indicators = ["ROC", "CCI", "WILLIAMS_R"]
        
        self.all_indicators = (self.basic_indicators + self.macd_indicators + 
                               self.atr_indicators + self.bb_indicators + 
                               self.adx_indicators + self.stoch_indicators +
                               self.ichimoku_indicators + self.volume_indicators +
                               self.momentum_indicators)
        
        self.operators = [">", "<", ">=", "<=", "=="]
        self.periods = [5, 7, 9, 10, 14, 20, 25, 30, 50, 100, 200]
        
        # Constantes por indicador
        self.constants_rsi = [20, 25, 30, 35, 40, 45, 55, 60, 65, 70, 75, 80]
        self.constants_macd = [-5, -2, -1, 0, 1, 2, 5, 10]
        self.constants_bb = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        self.constants_adx = [15, 20, 25, 30, 35, 40, 45, 50]
        self.constants_atr = [0.5, 1, 2, 3, 4, 5, 7, 10]
        self.constants_stoch = [10, 20, 30, 70, 80, 90]
        self.constants_cci = [-100, -50, 0, 50, 100]
        self.constants_williams = [-80, -70, -50, -30, -20]
        
        # Tracking de diversidad poblacional
        self.generation_history = []
        
    def generate_random_genome(self):
        """Create a random strategy with any combination of indicators."""
        genome = {
            "entry_rules": [],
            "params": {
                "sl_pct": random.uniform(0.01, 0.05),
                "tp_pct": random.uniform(0.02, 0.10),
                "size_pct": random.uniform(0.05, 0.50),
                "max_positions": random.randint(1, 3),
                # Risk Management
                "trailing_stop_pct": random.choice([0, 0.01, 0.015, 0.02, 0.025, 0.03]),
                "breakeven_after": random.choice([0, 0.01, 0.015, 0.02]),
                # Multi-timeframe
                "timeframe": random.choice(["1m", "5m", "15m", "30m", "1h"]),
            }
        }

        # Futures-specific parameters
        if self.is_futures:
            genome["params"]["leverage"] = random.randint(1, self.max_leverage)
            genome["params"]["direction"] = random.choice(["LONG", "SHORT", "BOTH"])
            genome["params"]["funding_threshold"] = random.choice([0.0005, 0.001, 0.002, 0.005])
            genome["params"]["market_type"] = "FUTURES"

        # 1 to 5 rules
        num_rules = random.randint(1, 5)
        for _ in range(num_rules):
            genome["entry_rules"].append(self._random_rule())

        return genome

    def _random_rule(self):
        """Generate a random rule with any indicator."""
        ind = random.choice(self.all_indicators)
        period = random.choice(self.periods)
        op = random.choice(self.operators)
        
        left = {"indicator": ind, "period": period}
        
        # Choose right side value based on indicator type
        if ind == "RSI":
            right = {"value": random.choice(self.constants_rsi)}
        elif ind in ["SMA", "EMA"]:
            if random.random() < 0.3:
                period2 = random.choice([p for p in self.periods if p != period])
                left = {"indicator": ind, "period": min(period, period2)}
                right = {"indicator": ind, "period": max(period, period2)}
            else:
                left = {"field": "close"}
                right = {"indicator": ind, "period": period}
        elif ind == "VOLSMA":
            left = {"field": "volume"}
            right = {"indicator": ind, "period": period}
        elif ind in ["MACD", "MACD_Signal", "MACD_Hist"]:
            right = {"value": random.choice(self.constants_macd)}
        elif ind in ["BB_Upper", "BB_Lower", "BB_Width"]:
            right = {"value": random.choice(self.constants_bb)}
        elif ind == "BB_Position":
            right = {"value": random.choice([10, 20, 30, 40, 50, 60, 70, 80, 90])}
        elif ind == "ATR":
            right = {"value": random.choice(self.constants_atr)}
        elif ind == "ATR_Pct":
            right = {"value": random.choice([0.5, 1, 1.5, 2, 2.5, 3, 4, 5])}
        elif ind in ["ADX", "DI_Plus", "DI_Minus"]:
            right = {"value": random.choice(self.constants_adx)}
        elif ind in ["STOCH_K", "STOCH_D"]:
            right = {"value": random.choice(self.constants_stoch)}
        elif ind == "CCI":
            right = {"value": random.choice(self.constants_cci)}
        elif ind == "WILLIAMS_R":
            right = {"value": random.choice(self.constants_williams)}
        elif ind in ["ROC"]:
            right = {"value": random.choice([-10, -5, -2, -1, 0, 1, 2, 5, 10])}
        else:
            right = {"value": 50}
            
        return {"left": left, "op": op, "right": right}
        
    def mutate(self, genome, generation=0, diversity_score=0.5):
        """Adaptive mutation based on generation and diversity."""
        mutated = copy.deepcopy(genome)

        # Adaptive mutation rate: decreases with generations
        base_mutation_rate = 0.25
        adaptive_rate = base_mutation_rate * (1 - (generation / max(self.generations, 1)) * 0.5)

        # Boost mutation if diversity is low
        if diversity_score < 0.3:
            adaptive_rate = min(0.5, adaptive_rate * 1.5)

        roll = random.random()

        if roll < adaptive_rate * 0.3:
            # Mutate core param
            key = random.choice(["sl_pct", "tp_pct"])
            change = random.uniform(0.8, 1.2)
            mutated["params"][key] *= change
        elif roll < adaptive_rate * 0.5:
            # Mutate size_pct
            change = random.uniform(0.8, 1.2)
            mutated["params"]["size_pct"] = max(0.05, min(0.95,
                mutated["params"].get("size_pct", 0.10) * change))
        elif roll < adaptive_rate * 0.65:
            # Mutate max_positions
            mutated["params"]["max_positions"] = random.randint(1, 3)
        elif roll < adaptive_rate * 0.75:
            # Mutate risk management
            mutated["params"]["trailing_stop_pct"] = random.choice([0, 0.01, 0.015, 0.02, 0.025, 0.03])
            mutated["params"]["breakeven_after"] = random.choice([0, 0.01, 0.015, 0.02])
            # Futures-specific: mutate leverage and direction
            if self.is_futures:
                mutated["params"]["leverage"] = random.randint(1, self.max_leverage)
                if random.random() < 0.3:
                    mutated["params"]["direction"] = random.choice(["LONG", "SHORT", "BOTH"])
        elif roll < adaptive_rate * 0.9:
            # Mutate existing rule
            if mutated["entry_rules"]:
                idx = random.randint(0, len(mutated["entry_rules"]) - 1)
                mutated["entry_rules"][idx] = self._random_rule()
        else:
            # Add new rule
            mutated["entry_rules"].append(self._random_rule())
            if len(mutated["entry_rules"]) > 5:
                mutated["entry_rules"] = mutated["entry_rules"][:5]

        return mutated
        
    def crossover(self, p1, p2):
        """Enhanced crossover with multi-point support."""
        child = {"entry_rules": [], "params": {}}

        # Mix Params
        for key in ["sl_pct", "tp_pct", "size_pct", "max_positions",
                     "trailing_stop_pct", "breakeven_after"]:
            if key in p1["params"] and key in p2["params"]:
                child["params"][key] = (p1["params"][key] + p2["params"][key]) / 2
            else:
                child["params"][key] = p1["params"].get(key, p2["params"].get(key, 0))

        # Futures-specific params crossover
        if self.is_futures:
            # Leverage: average of parents
            lev1 = p1["params"].get("leverage", 3)
            lev2 = p2["params"].get("leverage", 3)
            child["params"]["leverage"] = int((lev1 + lev2) / 2)
            child["params"]["leverage"] = max(1, min(self.max_leverage, child["params"]["leverage"]))

            # Direction: inherit from better parent or random
            child["params"]["direction"] = random.choice([
                p1["params"].get("direction", "BOTH"),
                p2["params"].get("direction", "BOTH")
            ])

            # Funding threshold: average
            ft1 = p1["params"].get("funding_threshold", 0.001)
            ft2 = p2["params"].get("funding_threshold", 0.001)
            child["params"]["funding_threshold"] = (ft1 + ft2) / 2
            child["params"]["market_type"] = "FUTURES"

        rules1 = p1["entry_rules"]
        rules2 = p2["entry_rules"]

        # Multi-point crossover
        if len(rules1) > 1 and len(rules2) > 1:
            split1 = len(rules1) // 3
            split2 = len(rules2) // 3
            child["entry_rules"] = rules1[:split1] + rules2[split2:2*split2] + rules1[2*split1:]
        else:
            split1 = len(rules1) // 2
            split2 = len(rules2) // 2
            child["entry_rules"] = rules1[:split1] + rules2[split2:]

        if not child["entry_rules"]:
            child["entry_rules"] = rules1 if rules1 else [self._random_rule()]

        return child

    def calculate_diversity(self, population):
        """Calculate population diversity based on rule similarity."""
        if len(population) < 2:
            return 1.0
        
        # Extract rule patterns
        patterns = []
        for g in population:
            rules_str = str(sorted([str(r) for r in g["entry_rules"]]))
            params_hash = hash(json.dumps(g["params"], sort_keys=True))
            patterns.append((rules_str, params_hash))
        
        unique = len(set(patterns))
        return unique / len(population)

    def calculate_fitness(self, item):
        """ML-enhanced fitness function."""
        genome, pnl, metrics = item
        num_trades = metrics.get('Total Trades', 0)
        win_rate = metrics.get('Win Rate %', 0)
        sharpe = metrics.get('Sharpe Ratio', 0)
        max_dd = metrics.get('Max Drawdown', 0)

        # Base PnL
        fitness = pnl

        # Trade count bonus (needs minimum trades)
        trade_bonus = min(num_trades * 10, 150) if num_trades >= 5 else 0
        fitness += trade_bonus

        # Win rate bonus (>50%)
        winrate_bonus = (win_rate - 50) * 3 if win_rate > 50 else 0
        fitness += winrate_bonus

        # Sharpe bonus
        sharpe_bonus = sharpe * 25 if sharpe > 0 else 0
        fitness += sharpe_bonus

        # Drawdown penalty (low drawdown is good)
        dd_penalty = max_dd * 200 if max_dd > 0.02 else 0
        fitness -= dd_penalty

        # Penalty for too many trades (overfitting risk)
        if num_trades > 100:
            fitness -= (num_trades - 100) * 2

        # Reward for risk management settings
        if genome.get("params", {}).get("trailing_stop_pct", 0) > 0:
            fitness += 10
        if genome.get("params", {}).get("breakeven_after", 0) > 0:
            fitness += 10

        # Futures-specific penalties/bonuses
        if self.is_futures:
            # Penalty for liquidations
            liquidations = metrics.get('Liquidations', 0)
            fitness -= liquidations * 100

            # Bonus for moderate leverage (avoid overleveraged strategies)
            leverage = genome.get("params", {}).get("leverage", 1)
            if 2 <= leverage <= 5:
                fitness += 15
            elif leverage > 7:
                fitness -= 20  # High leverage penalty

        return fitness

    def evaluate_population(self, population, progress_cb=None, cancel_event=None):
        """Run backtests on Ray Cluster."""
        results = []
        
        if HAS_RAY and ray.is_initialized() and not self.force_local:
            import os
            import threading
            import http.server
            import socketserver
            
            PORT = 8765
            STATIC_DIR = os.path.join(os.getcwd(), "static_payloads")
            os.makedirs(STATIC_DIR, exist_ok=True)
            
            if not hasattr(self, "http_server_started"):
                filename = "payload_v1.parquet"
                file_path = os.path.join(STATIC_DIR, filename)
                print(f"Saving data to HTTP Static Dir: {file_path}")
                try:
                    self.df.to_parquet(file_path)
                    
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
                            print(f"Port {PORT} busy")

                    t = threading.Thread(target=start_server, daemon=True)
                    t.start()
                    
                    self.http_server_started = True
                    
                    def get_reachable_ip():
                        import socket
                        try:
                            ray_ip = ray.util.get_node_ip_address()
                            if ray_ip and ray_ip != '127.0.0.1' and ray_ip != '0.0.0.0':
                                return ray_ip
                        except: pass

                        try:
                            hostname = socket.gethostname()
                            ips = socket.gethostbyname_all(hostname)[2]
                            for ip in ips:
                                if ip.startswith('100.'): return ip
                            for ip in ips:
                                if ip.startswith('192.168.') or ip.startswith('10.'): return ip
                        except: pass

                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            s.connect(('10.255.255.255', 1))
                            ip = s.getsockname()[0]
                            s.close()
                            if ip and ip != '0.0.0.0' and ip != '127.0.0.1':
                                return ip
                        except: pass

                        return '127.0.0.1'

                    head_ip = get_reachable_ip()
                    self.cached_payload = f"http://{head_ip}:{PORT}/{filename}"
                    
                except Exception as e:
                    print(f"Error setting up HTTP strategy: {e}")
                    self.cached_payload = self.df
            
            data_payload = self.cached_payload

            def debug_log(msg):
                with open("miner_debug.log", "a") as f:
                    f.write(f"{datetime.now()} - [EVAL] {msg}\n")

            debug_log(f"Starting evaluation with {len(population)} genomes")
            
            futures = [run_backtest_task.options(scheduling_strategy="SPREAD").remote(data_payload, self.risk_level, genome, "DYNAMIC") for genome in population]
            
            unfinished = futures
            completed = 0
            results_list = [None] * len(population)
            future_to_index = {f: i for i, f in enumerate(futures)}
            retries = {}
            
            if len(self.df) < 500:
                  print("ERROR: Dataset too small (< 500 candles)")
                  return [] 

            while unfinished:
                if cancel_event and cancel_event.is_set():
                    debug_log("Cancelled by user during wait.")
                    return []
                    
                done, unfinished = ray.wait(unfinished, num_returns=1, timeout=5.0)
                
                for ref in done:
                    idx = future_to_index.get(ref)
                    if idx is None:
                        continue
                        
                    try:
                        res = ray.get(ref)
                        results_list[idx] = res
                        completed += 1
                        if progress_cb:
                            progress_cb(completed / len(population))
                        
                    except Exception as e:
                        r_count = retries.get(idx, 0)
                        
                        if r_count < 3:
                            print(f"Task {idx} failed (Retry {r_count+1}/3): {e}")
                            retries[idx] = r_count + 1
                            
                            genome = population[idx]
                            new_ref = run_backtest_task.options(scheduling_strategy="SPREAD").remote(data_payload, self.risk_level, genome, "DYNAMIC")
                            
                            future_to_index[new_ref] = idx
                            unfinished.append(new_ref)
                            
                        else:
                            print(f"Task {idx} failed permanently: {e}")
                            results_list[idx] = {'metrics': {'Total PnL': -9999}, 'error': str(e)}
                            completed += 1
                            if progress_cb:
                                progress_cb(completed / len(population))
            
            results_raw = results_list
        else:
            results_raw = self._evaluate_local(population, progress_cb, cancel_event)

        fitness_scores = []
        for i, res in enumerate(results_raw):
            if isinstance(res, dict) and 'metrics' in res:
                pnl = res['metrics'].get('Total PnL', -9999)
                fitness_scores.append((population[i], pnl, res['metrics']))
            else:
                default_metrics = {'Total PnL': -9999, 'Total Trades': 0, 'Win Rate %': 0}
                fitness_scores.append((population[i], -9999, default_metrics))

        return fitness_scores

    def run(self, progress_callback=None, cancel_event=None, return_metrics=False):
        """Main Evolution Loop with adaptive optimization and elite seeding."""

        def debug_log(msg):
            with open("miner_debug.log", "a") as f:
                f.write(f"{datetime.now()} - {msg}\n")

        debug_log("Strategy Miner RUN started with ML-enhanced fitness.")

        # Initialize Population with elite seeding support
        debug_log(f"Generating initial population ({self.pop_size})...")

        # Calculate how many individuals come from elite seeds
        num_from_seeds = 0
        if self.seed_genomes:
            num_from_seeds = min(len(self.seed_genomes), int(self.pop_size * self.seed_ratio))
            debug_log(f"Using {num_from_seeds} elite seed genomes from {len(self.seed_genomes)} available")

        # Build population: first from seeds, rest random
        population = []

        # Add seed genomes (élite from previous best results)
        for i in range(num_from_seeds):
            seed = self.seed_genomes[i]
            if isinstance(seed, dict):
                # Validate seed has required keys
                if 'entry_rules' in seed or 'params' in seed:
                    population.append(seed)
                    debug_log(f"Added elite seed genome {i+1}")
                else:
                    # Invalid seed, generate random
                    population.append(self.generate_random_genome())
            else:
                population.append(self.generate_random_genome())

        # Fill rest with random genomes
        remaining = self.pop_size - len(population)
        for _ in range(remaining):
            population.append(self.generate_random_genome())

        debug_log(f"Population initialized: {len(population)} total ({num_from_seeds} from elite, {remaining} random)")

        best_genome = None
        best_pnl = -float('inf')
        best_metrics = {}
        
        for gen in range(self.generations):
            if cancel_event and cancel_event.is_set():
                debug_log("Cancelled by user.")
                break
            
            debug_log(f"Starting Generation {gen}...")    
            if progress_callback:
                progress_callback("START_GEN", gen)
                
            # Calculate diversity for this generation
            diversity = self.calculate_diversity(population)
            self.generation_history.append(diversity)
            
            def eval_cb(batch_pct):
                if progress_callback:
                    global_pct = (gen + batch_pct) / self.generations
                    progress_callback("BATCH_PROGRESS", global_pct)
                    
            scored_pop = self.evaluate_population(population, progress_cb=eval_cb, cancel_event=cancel_event)
            
            if not scored_pop:
                debug_log("Population Evaluation returned empty.")
                break
            
            # Calculate fitness for all individuals
            scored_pop = [(g, self.calculate_fitness((g, p, m)), m) 
                         for g, p, m in scored_pop]
            
            scored_pop.sort(key=lambda x: x[1], reverse=True)

            current_best = scored_pop[0]
            debug_log(f"Gen {gen} Best PnL: {current_best[1]}")

            if current_best[1] > best_pnl:
                best_pnl = current_best[1]
                best_genome = current_best[0]
                best_metrics = current_best[2] if len(current_best) > 2 else {}

            if progress_callback:
                best_metrics = current_best[2] if len(current_best) > 2 else {}
                progress_callback("BEST_GEN", {
                    'gen': gen,
                    'pnl': current_best[1],
                    'num_trades': best_metrics.get('Total Trades', 0),
                    'win_rate': best_metrics.get('Win Rate %', 0) / 100,
                    'sharpe': best_metrics.get('Sharpe Ratio', 0),
                    'diversity': diversity,
                    'genome': current_best[0]
                })

            # Selection (Top 20%)
            survivors = [x[0] for x in scored_pop[:int(self.pop_size * 0.2)]]
            
            # Elitism: Keep top 5% unchanged
            elite_count = int(self.pop_size * 0.05)
            next_pop = [scored_pop[i][0] for i in range(elite_count)]
            
            # Generate offspring
            while len(next_pop) < self.pop_size:
                # Tournament selection
                tournament_size = 3
                p1 = max(random.sample(survivors, min(tournament_size, len(survivors))), 
                        key=lambda x: self._get_fitness_estimate(x, scored_pop))
                p2 = max(random.sample(survivors, min(tournament_size, len(survivors))), 
                        key=lambda x: self._get_fitness_estimate(x, scored_pop))
                
                child = self.crossover(p1, p2)
                child = self.mutate(child, generation=gen, diversity_score=diversity)
                next_pop.append(child)
                
            population = next_pop
            
        debug_log("Mining Complete.")
        if return_metrics:
            return best_genome, best_pnl, best_metrics
        return best_genome, best_pnl

    def _get_fitness_estimate(self, genome, scored_pop):
        """Get fitness estimate for a genome from scored population."""
        for g, fitness, m in scored_pop:
            if g == genome:
                return fitness
        return -9999

    def _evaluate_local(self, population, progress_cb, cancel_event=None):
        """Run backtests locally."""

        # Use futures backtester if market_type is FUTURES
        if self.is_futures and HAS_FUTURES_NUMBA:
            try:
                return numba_evaluate_futures_population(
                    self.df, population, risk_level=self.risk_level,
                    progress_cb=progress_cb, cancel_event=cancel_event,
                    is_perpetual=self.is_perpetual
                )
            except Exception as e:
                print(f"Numba futures evaluation failed ({e}), falling back to Python...")

        # Use spot backtester for SPOT market
        if HAS_NUMBA and not self.is_futures:
            try:
                return numba_evaluate_population(
                    self.df, population, risk_level=self.risk_level,
                    progress_cb=progress_cb, cancel_event=cancel_event
                )
            except Exception as e:
                print(f"Numba evaluation failed ({e}), falling back to Python...")

        results = []
        from backtester import Backtester
        from dynamic_strategy import DynamicStrategy

        total = len(population)
        for i, genome in enumerate(population):
            if cancel_event and cancel_event.is_set():
                return []

            bt = Backtester()
            try:
                _, trades = bt.run_backtest(self.df, risk_level=self.risk_level, 
                                           strategy_params=genome, strategy_cls=DynamicStrategy)

                total_trades = len(trades)

                if total_trades > 0:
                    total_pnl = trades['pnl'].sum()
                    wins = len(trades[trades['pnl'] > 0])
                    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

                    cum_pnl = trades['pnl'].cumsum()
                    peak = cum_pnl.cummax()
                    drawdown = (peak - cum_pnl)
                    max_dd = (drawdown / (10000.0 + peak)).max() if peak.max() > 0 else 0.0

                    if 'pnl_pct' in trades.columns and total_trades > 1:
                        ret_mean = trades['pnl_pct'].mean()
                        ret_std = trades['pnl_pct'].std()
                        sharpe = (ret_mean / ret_std) * (252 ** 0.5) if ret_std > 1e-10 else 0.0
                    elif total_trades > 1:
                        rets = trades['pnl'] / 1000.0
                        ret_mean = rets.mean()
                        ret_std = rets.std()
                        sharpe = (ret_mean / ret_std) * (252 ** 0.5) if ret_std > 1e-10 else 0.0
                    else:
                        sharpe = 0.0
                else:
                    total_pnl = -10000
                    win_rate = 0.0
                    max_dd = 0.0
                    sharpe = 0.0

                results.append({
                    'metrics': {
                        'Total PnL': total_pnl,
                        'Total Trades': total_trades,
                        'Win Rate %': win_rate,
                        'Sharpe Ratio': round(sharpe, 4),
                        'Max Drawdown': round(max_dd, 4)
                    }
                })
            except Exception as e:
                print(f"Local Backtest Error: {e}")
                results.append({
                    'metrics': {
                        'Total PnL': -10000,
                        'Total Trades': 0,
                        'Win Rate %': 0.0,
                        'Sharpe Ratio': 0.0,
                        'Max Drawdown': 0.0
                    }
                })

            if progress_cb:
                progress_cb((i + 1) / total)

        return results
