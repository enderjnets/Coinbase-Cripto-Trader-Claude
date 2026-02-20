import random
import copy
try:
    import ray
    HAS_RAY = True
except ImportError:
    HAS_RAY = False
import pandas as pd
import time
from datetime import datetime

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

class StrategyMiner:
    """
    Genetic Algorithm to discover optimal trading strategies.
    Evolves a population of 'Genomes' (logic rules).
    
    INDICADORES DISPONIBLES:
    - Básicos: RSI, SMA, EMA, VOLSMA
    - Avanzados: MACD, MACD_Signal, MACD_Hist, ATR, ATR_Pct
    - Bollinger Bands: BB_Upper, BB_Lower, BB_Width, BB_Position
    - ADX: ADX, DI_Plus, DI_Minus
    """
    def __init__(self, df, population_size=100, generations=20, risk_level="LOW", force_local=False, ray_address="auto"):
        self.df = df
        self.pop_size = population_size
        self.generations = generations
        self.risk_level = risk_level
        self.force_local = force_local
        ray_init = HAS_RAY and ray.is_initialized()
        print(f"🔥 DEBUG: StrategyMiner INIT | force_local={self.force_local} | Ray Init={ray_init}")
        
        # === INDICADORES DISPONIBLES ===
        # Básicos
        self.basic_indicators = ["RSI", "SMA", "EMA", "VOLSMA"]
        
        # MACD indicators
        self.macd_indicators = ["MACD", "MACD_Signal", "MACD_Hist"]
        
        # ATR indicators  
        self.atr_indicators = ["ATR", "ATR_Pct"]
        
        # Bollinger Bands
        self.bb_indicators = ["BB_Upper", "BB_Lower", "BB_Width", "BB_Position"]
        
        # ADX indicators
        self.adx_indicators = ["ADX", "DI_Plus", "DI_Minus"]
        
        # All indicators combined
        self.all_indicators = (self.basic_indicators + self.macd_indicators + 
                               self.atr_indicators + self.bb_indicators + 
                               self.adx_indicators)
        
        self.operators = [">", "<", ">=", "<="]
        self.periods = [7, 10, 14, 20, 25, 30, 50, 100, 200]
        
        # Constantes por indicador
        self.constants_rsi = [20, 25, 30, 35, 40, 45, 55, 60, 65, 70, 75, 80]
        self.constants_macd = [-5, -2, -1, 0, 1, 2, 5, 10]
        self.constants_bb = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        self.constants_adx = [15, 20, 25, 30, 35, 40, 45, 50]
        self.constants_atr = [0.5, 1, 2, 3, 4, 5, 7, 10]
        
    def generate_random_genome(self):
        """Create a random strategy with any combination of indicators."""
        genome = {
            "entry_rules": [],
            "params": {
                "sl_pct": random.uniform(0.01, 0.05),
                "tp_pct": random.uniform(0.02, 0.10),
                "size_pct": random.uniform(0.05, 0.50),
                "max_positions": random.randint(1, 3)
            }
        }

        # 1 to 4 rules (now with more indicators, up to 4 rules)
        num_rules = random.randint(1, 4)
        for _ in range(num_rules):
            genome["entry_rules"].append(self._random_rule())

        return genome

    def _random_rule(self):
        """Generate a random rule with any indicator."""
        # Choose indicator type with weighted probability
        # Give slight preference to basic indicators, then advanced
        indicator_pool = self.all_indicators
        ind = random.choice(indicator_pool)
        period = random.choice(self.periods)
        op = random.choice(self.operators)
        
        left = {"indicator": ind, "period": period}
        
        # Choose right side value based on indicator type
        if ind == "RSI":
            right = {"value": random.choice(self.constants_rsi)}
        elif ind == "SMA":
            # Price vs MA or MA crossover
            if random.random() < 0.3:
                period2 = random.choice([p for p in self.periods if p != period])
                left = {"indicator": ind, "period": min(period, period2)}
                right = {"indicator": ind, "period": max(period, period2)}
            else:
                left = {"field": "close"}
                right = {"indicator": ind, "period": period}
        elif ind == "EMA":
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
            if ind == "BB_Position":
                right = {"value": random.choice([10, 20, 30, 40, 50, 60, 70, 80, 90])}
        elif ind == "ATR":
            right = {"value": random.choice(self.constants_atr)}
        elif ind == "ATR_Pct":
            right = {"value": random.choice([0.5, 1, 1.5, 2, 2.5, 3, 4, 5])}
        elif ind in ["ADX", "DI_Plus", "DI_Minus"]:
            right = {"value": random.choice(self.constants_adx)}
        else:
            right = {"value": 50}  # Default
            
        return {"left": left, "op": op, "right": right}
        
    def mutate(self, genome):
        """Randomly change a parameter or rule."""
        mutated = copy.deepcopy(genome)

        roll = random.random()
        if roll < 0.3:
            # Mutate core param
            key = random.choice(["sl_pct", "tp_pct"])
            change = random.uniform(0.8, 1.2)
            mutated["params"][key] *= change
        elif roll < 0.5:
            # Mutate size_pct
            change = random.uniform(0.8, 1.2)
            mutated["params"]["size_pct"] = max(0.05, min(0.95,
                mutated["params"].get("size_pct", 0.10) * change))
        elif roll < 0.65:
            # Mutate max_positions
            mutated["params"]["max_positions"] = random.randint(1, 3)
        elif roll < 0.8:
            # Mutate existing rule
            if mutated["entry_rules"]:
                idx = random.randint(0, len(mutated["entry_rules"]) - 1)
                mutated["entry_rules"][idx] = self._random_rule()
        else:
            # Add new rule
            mutated["entry_rules"].append(self._random_rule())
            # Limit to 5 rules
            if len(mutated["entry_rules"]) > 5:
                mutated["entry_rules"] = mutated["entry_rules"][:5]

        return mutated
        
    def crossover(self, p1, p2):
        """Mix rules from two parents."""
        child = {"entry_rules": [], "params": {}}

        # Mix Params
        child["params"]["sl_pct"] = (p1["params"]["sl_pct"] + p2["params"]["sl_pct"]) / 2
        child["params"]["tp_pct"] = (p1["params"]["tp_pct"] + p2["params"]["tp_pct"]) / 2
        child["params"]["size_pct"] = (p1["params"].get("size_pct", 0.10) + p2["params"].get("size_pct", 0.10)) / 2
        child["params"]["max_positions"] = random.choice([
            p1["params"].get("max_positions", 1),
            p2["params"].get("max_positions", 1)
        ])

        rules1 = p1["entry_rules"]
        rules2 = p2["entry_rules"]

        split1 = len(rules1) // 2
        split2 = len(rules2) // 2

        child["entry_rules"] = rules1[:split1] + rules2[split2:]
        if not child["entry_rules"]:
            child["entry_rules"] = rules1 if rules1 else [self._random_rule()]

        return child

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
                print(f"📦 Saving data to HTTP Static Dir: {file_path}")
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
                                print(f"🌍 HTTP Data Server running on port {PORT}")
                                httpd.serve_forever()
                        except OSError:
                            print(f"⚠️ Port {PORT} busy")

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
                    print(f"✅ Data Server: {self.cached_payload}")
                    
                except Exception as e:
                    print(f"❌ Error setting up HTTP strategy: {e}")
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
                  print("❌ ERROR: Dataset too small (< 500 candles)")
                  return [] 

            while unfinished:
                if cancel_event and cancel_event.is_set():
                    debug_log("Cancelled by user during wait.")
                    return []
                    
                done, unfinished = ray.wait(unfinished, num_returns=1, timeout=5.0)
                debug_log(f"ray.wait() returned: {len(done)} done, {len(unfinished)} unfinished")
                
                for ref in done:
                    idx = future_to_index.get(ref)
                    if idx is None:
                        continue
                        
                    try:
                        res = ray.get(ref)
                        debug_log(f"Task {idx} result: {res}")
                        results_list[idx] = res
                        completed += 1
                        if progress_cb:
                            progress_cb(completed / len(population))
                        
                    except Exception as e:
                        r_count = retries.get(idx, 0)
                        
                        if r_count < 3:
                            print(f"⚠️ Task {idx} failed (Retry {r_count+1}/3): {e}")
                            retries[idx] = r_count + 1
                            
                            genome = population[idx]
                            new_ref = run_backtest_task.options(scheduling_strategy="SPREAD").remote(data_payload, self.risk_level, genome, "DYNAMIC")
                            
                            future_to_index[new_ref] = idx
                            unfinished.append(new_ref)
                            
                        else:
                            print(f"❌ Task {idx} failed permanently: {e}")
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
        """Main Evolution Loop."""

        def debug_log(msg):
            with open("miner_debug.log", "a") as f:
                f.write(f"{datetime.now()} - {msg}\n")

        debug_log("🚀 Strategy Miner RUN started.")

        # Initialize Population
        debug_log(f"Generating initial population ({self.pop_size})...")
        population = [self.generate_random_genome() for _ in range(self.pop_size)]
        best_genome = None
        best_pnl = -float('inf')
        best_metrics = {}
        
        for gen in range(self.generations):
            if cancel_event and cancel_event.is_set():
                debug_log("❌ Cancelled by user.")
                break
            
            debug_log(f"🧬 Starting Generation {gen}...")    
            if progress_callback:
                progress_callback("START_GEN", gen)
                
            def eval_cb(batch_pct):
                if progress_callback:
                    global_pct = (gen + batch_pct) / self.generations
                    progress_callback("BATCH_PROGRESS", global_pct)
                    
            scored_pop = self.evaluate_population(population, progress_cb=eval_cb, cancel_event=cancel_event)
            
            if not scored_pop:
                debug_log("⚠️ Population Evaluation returned empty. Stopping.")
                break
            
            def calculate_fitness(item):
                genome, pnl, metrics = item
                num_trades = metrics.get('Total Trades', 0)
                win_rate = metrics.get('Win Rate %', 0)
                sharpe = metrics.get('Sharpe Ratio', 0)

                trade_bonus = min(num_trades * 10, 100) if num_trades >= 5 else 0
                winrate_bonus = (win_rate - 50) * 2 if win_rate > 50 else 0
                sharpe_bonus = sharpe * 20 if sharpe > 0 else 0

                fitness = pnl + trade_bonus + winrate_bonus + sharpe_bonus
                return fitness

            scored_pop.sort(key=calculate_fitness, reverse=True)

            current_best = scored_pop[0]
            debug_log(f"🏆 Gen {gen} Best PnL: {current_best[1]}")

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
                    'genome': current_best[0]
                })

            # Selection (Top 20%)
            survivors = [x[0] for x in scored_pop[:int(self.pop_size * 0.2)]]
            
            # Next Gen
            next_pop = survivors[:]
            
            while len(next_pop) < self.pop_size:
                p1 = random.choice(survivors)
                p2 = random.choice(survivors)
                child = self.crossover(p1, p2)
                child = self.mutate(child)
                next_pop.append(child)
                
            population = next_pop
            
        debug_log("✅ Mining Complete.")
        if return_metrics:
            return best_genome, best_pnl, best_metrics
        return best_genome, best_pnl

    def _evaluate_local(self, population, progress_cb, cancel_event=None):
        """Run backtests locally. Uses Numba JIT if available."""

        if HAS_NUMBA:
            try:
                return numba_evaluate_population(
                    self.df, population, risk_level=self.risk_level,
                    progress_cb=progress_cb, cancel_event=cancel_event
                )
            except Exception as e:
                print(f"   Numba evaluation failed ({e}), falling back to Python...")

        results = []
        from backtester import Backtester
        from dynamic_strategy import DynamicStrategy

        total = len(population)
        for i, genome in enumerate(population):
            if cancel_event and cancel_event.is_set():
                return []

            bt = Backtester()
            try:
                _, trades = bt.run_backtest(self.df, risk_level=self.risk_level, strategy_params=genome, strategy_cls=DynamicStrategy)

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
