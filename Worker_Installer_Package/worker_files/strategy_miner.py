import random
import copy
import ray
import pandas as pd
import time
from datetime import datetime

# Import the Ray task from optimizer
try:
    from optimizer import run_backtest_task
except ImportError:
    # If optimizer.py is not importable due to circular imports or structure, 
    # we might need to redefine or refactor. But usually it works.
    pass

class StrategyMiner:
    """
    Genetic Algorithm to discover optimal trading strategies.
    Evolves a population of 'Genomes' (logic rules).
    """
    def __init__(self, df, population_size=100, generations=20, risk_level="LOW", force_local=False, ray_address="auto"):
        self.df = df
        self.pop_size = population_size
        self.generations = generations
        self.risk_level = risk_level
        self.force_local = force_local
        print(f"🔥 DEBUG: StrategyMiner INIT | force_local={self.force_local} | Ray Init={ray.is_initialized()}")
        
        # DNA Building Blocks
        self.indicators = ["RSI", "SMA", "EMA", "VOLSMA"]
        self.operators = [">", "<"]
        self.periods = [10, 14, 20, 50, 100, 200]
        self.constants_rsi = [20, 25, 30, 35, 40, 60, 65, 70, 75, 80]
        
    def generate_random_genome(self):
        """Create a random strategy."""
        genome = {
            "entry_rules": [],
            "params": {
                "sl_pct": random.uniform(0.01, 0.05),
                "tp_pct": random.uniform(0.02, 0.10)
            }
        }
        
        # 1 to 3 rules
        num_rules = random.randint(1, 3)
        for _ in range(num_rules):
            genome["entry_rules"].append(self._random_rule())
            
        return genome

    def _random_rule(self):
        ind = random.choice(self.indicators)
        period = random.choice(self.periods)
        op = random.choice(self.operators)
        
        left = {"indicator": ind, "period": period}
        
        # Right side: Constant or Indicator?
        # For simplicity, mostly constants, or Price for SMA
        if ind == "RSI":
            right = {"value": random.choice(self.constants_rsi)}
        elif ind in ["SMA", "EMA"]:
            # Compare Price vs MA
            left = {"field": "close"}
            right = {"indicator": ind, "period": period}
            # Or MA vs MA crossover
            if random.random() < 0.3:
                 period2 = random.choice([p for p in self.periods if p != period])
                 left = {"indicator": ind, "period": min(period, period2)} # fast
                 right = {"indicator": ind, "period": max(period, period2)} # slow
        elif ind == "VOLSMA":
            left = {"field": "volume"}
            right = {"indicator": "VOLSMA", "period": period}
            
        return {"left": left, "op": op, "right": right}
        
    def mutate(self, genome):
        """Randomly change a parameter or rule."""
        mutated = copy.deepcopy(genome)
        
        if random.random() < 0.5:
            # Mutate Param
            key = random.choice(["sl_pct", "tp_pct"])
            change = random.uniform(0.8, 1.2)
            mutated["params"][key] *= change
        else:
            # Mutate Rule
            if mutated["entry_rules"]:
                idx = random.randint(0, len(mutated["entry_rules"]) - 1)
                mutated["entry_rules"][idx] = self._random_rule()
                
        return mutated
        
    def crossover(self, p1, p2):
        """Mix rules from two parents."""
        child = {"entry_rules": [], "params": {}}
        
        # Mix Params
        child["params"]["sl_pct"] = (p1["params"]["sl_pct"] + p2["params"]["sl_pct"]) / 2
        child["params"]["tp_pct"] = (p1["params"]["tp_pct"] + p2["params"]["tp_pct"]) / 2
        
        # Mix Rules
        rules1 = p1["entry_rules"]
        rules2 = p2["entry_rules"]
        
        # Take half from each (approx)
        split1 = len(rules1) // 2
        split2 = len(rules2) // 2
        
        child["entry_rules"] = rules1[:split1] + rules2[split2:]
        if not child["entry_rules"]: # Safety
            child["entry_rules"] = rules1 if rules1 else [self._random_rule()]
            
        return child

    def evaluate_population(self, population, progress_cb=None, cancel_event=None):
        """Run backtests on Ray Cluster."""
        results = []
        
        # Prepare Tasks
        if ray.is_initialized() and not self.force_local:
            # HTTP SIDE-LOAD STRATEGY (True Distributed / No-Drive)
            # We serve the data file via a lightweight HTTP server on the Head Node.
            # Workers fetch it via URL. This bypasses Ray Object Store and Filesystem dependencies.
            
            import os
            import threading
            import http.server
            import socketserver
            
            PORT = 8765
            STATIC_DIR = os.path.join(os.getcwd(), "static_payloads")
            os.makedirs(STATIC_DIR, exist_ok=True)
            
            if not hasattr(self, "http_server_started"):
                # Save data to static dir
                filename = "payload_v1.parquet"
                file_path = os.path.join(STATIC_DIR, filename)
                print(f"📦 Saving data to HTTP Static Dir: {file_path}")
                try:
                    self.df.to_parquet(file_path)
                    
                    # Start HTTP Server in background thread (Daemon)
                    # Use a custom handler to serve from the specific directory
                    class Handler(http.server.SimpleHTTPRequestHandler):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, directory=STATIC_DIR, **kwargs)
                        def log_message(self, format, *args):
                            pass # Silence logs
                            
                    def start_server():
                        try:
                            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                                print(f"🌍 HTTP Data Server running on port {PORT}")
                                httpd.serve_forever()
                        except OSError:
                            print(f"⚠️ Port {PORT} busy, assuming server already running.")

                    t = threading.Thread(target=start_server, daemon=True)
                    t.start()
                    
                    self.http_server_started = True
                    
                    # Construct URL
                    # Use a more robust way to find the non-loopback Tailscale/Network IP
                    def get_reachable_ip():
                        import socket
                        # 1. Try to find a Tailscale IP (starts with 100.)
                        try:
                            import subprocess
                            output = subprocess.check_output(["networksetup", "-listallnetworkservices"], text=True)
                            # This is Mac specific, but let's try a more universal socket approach first
                        except: pass
                        
                        # Priority 1: Use Ray's node IP (respects how Ray was started)
                        try:
                            ray_ip = ray.util.get_node_ip_address()
                            if ray_ip and ray_ip != '127.0.0.1' and ray_ip != '0.0.0.0':
                                return ray_ip
                        except: pass

                        try:
                            # Priority 2: Get all IPs and pick Tailscale or LAN
                            import socket
                            hostname = socket.gethostname()
                            ips = socket.gethostbyname_all(hostname)[2]
                            # Tailscale first
                            for ip in ips:
                                if ip.startswith('100.'): return ip
                            # LAN second
                            for ip in ips:
                                if ip.startswith('192.168.') or ip.startswith('10.'): return ip
                        except: pass

                        # Priority 3: Standard socket trick
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
                    
                    # Force Tailscale if we know it exists (user has it)
                    # We can also try to grep from ifconfig/tailscale status
                    
                    self.cached_payload = f"http://{head_ip}:{PORT}/{filename}"
                    print(f"✅ Data Server: {self.cached_payload} (Reachable IP: {head_ip})")
                    
                except Exception as e:
                    print(f"❌ Error setting up HTTP strategy: {e}")
                    self.cached_payload = self.df
            
            # The payload is now a URL STRING or DataFrame
            data_payload = self.cached_payload

            # 🔍 DEBUG: Log payload type
            print(f"\n🔍 PAYLOAD DEBUG:")
            print(f"   Type: {type(data_payload)}")
            if isinstance(data_payload, str):
                print(f"   Value: {data_payload}")
            elif hasattr(data_payload, 'shape'):
                print(f"   Shape: {data_payload.shape}")
            print()

            # DEBUG HELPER
            def debug_log(msg):
                with open("miner_debug.log", "a") as f:
                    f.write(f"{datetime.now()} - [EVAL] {msg}\n")

            debug_log(f"Starting evaluation - Payload type: {type(data_payload)}, value: {str(data_payload)[:100]}")
            
            # Pass the URL explicitly - FORCE SPREAD to use Worker immediately
            futures = [run_backtest_task.options(scheduling_strategy="SPREAD").remote(data_payload, self.risk_level, genome, "DYNAMIC") for genome in population]
            debug_log(f"Tasks submitted: {len(futures)}")
            
            # Restore Loop State Variables
            unfinished = futures
            completed = 0
            results_list = [None] * len(population)
            future_to_index = {f: i for i, f in enumerate(futures)}
            retries = {}
            
            # VALIDATION LOGGING
            print(f"DEBUG: Miner received DataFrame. Shape: {self.df.shape}")
            if not self.df.empty:
                 print(f"DEBUG: Columns: {self.df.columns.tolist()}")
                 print(f"DEBUG: First Row Date: {self.df.iloc[0].get('timestamp', 'Unknown')}")
                 print(f"DEBUG: Last Row Date: {self.df.iloc[-1].get('timestamp', 'Unknown')}")
            
            if len(self.df) < 500:
                 print("❌ ERROR CRÍTICO: El dataset es demasiado pequeño (< 500 velas). El backtest no generará operaciones.")
                 # Returning an empty list of fitness scores to indicate failure/no results
                 return [] 
            
            while unfinished:
                if cancel_event and cancel_event.is_set():
                    debug_log("Cancelled by user during wait.")
                    return []
                    
                # Wait for at least 1
                debug_log(f"ray.wait() with {len(unfinished)} unfinished tasks...")
                done, unfinished = ray.wait(unfinished, num_returns=1, timeout=5.0) # Increased timeout for debug
                debug_log(f"ray.wait() returned: {len(done)} done, {len(unfinished)} unfinished")
                
                for ref in done:
                    # Retrieve index
                    idx = future_to_index.get(ref)
                    if idx is None:
                        # Should not happen
                        continue
                        
                    try:
                        # Try to get result
                        res = ray.get(ref)
                        debug_log(f"Task {idx} result: {res}")
                        results_list[idx] = res
                        completed += 1
                        if progress_cb:
                            # Use count of non-None results as progress
                            progress_cb(completed / len(population))
                        
                    except Exception as e:
                        # Handle Worker Death/Crash
                        r_count = retries.get(idx, 0)
                        
                        if r_count < 3: # Max 3 retries
                            print(f"⚠️ Task {idx} failed (Retry {r_count+1}/3): {e}")
                            retries[idx] = r_count + 1
                            
                            # Resubmit
                            genome = population[idx]
                            # Resubmit with same payload (path or df)
                            new_ref = run_backtest_task.options(scheduling_strategy="SPREAD").remote(data_payload, self.risk_level, genome, "DYNAMIC")
                            
                            # Update mapping and unfinished list
                            future_to_index[new_ref] = idx
                            unfinished.append(new_ref)
                            
                            # Remove old ref from mapping using values? No need, logic handles key lookup.
                        else:
                            print(f"❌ Task {idx} failed permanently: {e}")
                            # Return dummy result
                            results_list[idx] = {'metrics': {'Total PnL': -9999}, 'error': str(e)}
                            completed += 1
                            if progress_cb:
                                progress_cb(completed / len(population))
            
            results_raw = results_list
        else:
            # Local Execution Fallback
            results_raw = self._evaluate_local(population, progress_cb, cancel_event)


        # Parse fitness
        fitness_scores = []
        for i, res in enumerate(results_raw):
            if isinstance(res, dict) and 'metrics' in res:
                pnl = res['metrics'].get('Total PnL', -9999)
                # Store tuple of (genome, pnl, full_metrics)
                fitness_scores.append((population[i], pnl, res['metrics']))
            else:
                # Default metrics for failed evaluations
                default_metrics = {'Total PnL': -9999, 'Total Trades': 0, 'Win Rate %': 0}
                fitness_scores.append((population[i], -9999, default_metrics))

        return fitness_scores

    def run(self, progress_callback=None, cancel_event=None):
        """Main Evolution Loop."""
        
        # DEBUG LOGGER
        def debug_log(msg):
            with open("miner_debug.log", "a") as f:
                f.write(f"{datetime.now()} - {msg}\n")
        
        debug_log("🚀 Strategy Miner RUN started.")
        
        # 1. Initialize Population
        debug_log(f"Generating initial population ({self.pop_size})...")
        population = [self.generate_random_genome() for _ in range(self.pop_size)]
        best_genome = None
        best_pnl = -float('inf')
        
        for gen in range(self.generations):
            if cancel_event and cancel_event.is_set():
                debug_log("❌ Cancelled by user.")
                break
            
            debug_log(f"🧬 Starting Generation {gen}...")    
            if progress_callback:
                progress_callback("START_GEN", gen)
                
            # 2. Evaluate
            # GLOBAL PROGRESS CALCULATION
            # Global Progress = ((Current Gen) + (Batch %)) / Total Gens
            def eval_cb(batch_pct):
                # debug_log(f"   Batch Progress: {batch_pct:.2f}") # Too verbose?
                if progress_callback:
                    # Calculate global percentage
                    global_pct = (gen + batch_pct) / self.generations
                    progress_callback("BATCH_PROGRESS", global_pct)
                    
            scored_pop = self.evaluate_population(population, progress_cb=eval_cb, cancel_event=cancel_event)
            
            if not scored_pop: # Cancelled or empty
                debug_log("⚠️ Population Evaluation returned empty. Stopping.")
                break
            
            # Sort by Fitness (improved scoring)
            # Fitness = PnL + bonus por trades de calidad
            def calculate_fitness(item):
                genome, pnl, metrics = item
                num_trades = metrics.get('Total Trades', 0)
                win_rate = metrics.get('Win Rate %', 0)

                # Bonus por tener trades (al menos 5)
                trade_bonus = min(num_trades * 10, 100) if num_trades >= 5 else 0

                # Bonus por win rate alto (> 50%)
                winrate_bonus = (win_rate - 50) * 2 if win_rate > 50 else 0

                fitness = pnl + trade_bonus + winrate_bonus
                return fitness

            scored_pop.sort(key=calculate_fitness, reverse=True)

            current_best = scored_pop[0]
            debug_log(f"🏆 Gen {gen} Best PnL: {current_best[1]}")

            if current_best[1] > best_pnl:
                best_pnl = current_best[1]
                best_genome = current_best[0]

            if progress_callback:
                # current_best is (genome, pnl, metrics)
                best_metrics = current_best[2] if len(current_best) > 2 else {}
                progress_callback("BEST_GEN", {
                    'gen': gen,
                    'pnl': current_best[1],
                    'num_trades': best_metrics.get('Total Trades', 0),
                    'win_rate': best_metrics.get('Win Rate %', 0) / 100,  # Convert back to 0-1 range
                    'genome': current_best[0]
                })

            # 3. Selection (Top 20%)
            survivors = [x[0] for x in scored_pop[:int(self.pop_size * 0.2)]]
            
            # 4. Next Gen
            next_pop = survivors[:] # Elitism
            
            while len(next_pop) < self.pop_size:
                p1 = random.choice(survivors)
                p2 = random.choice(survivors)
                child = self.crossover(p1, p2)
                child = self.mutate(child)
                next_pop.append(child)
                
            population = next_pop
            
        debug_log("✅ Mining Complete.")
        return best_genome, best_pnl

    def _evaluate_local(self, population, progress_cb, cancel_event=None):
        """Run backtests locally (sequential)."""
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
                else:
                    # PENALIZACIÓN FUERTE: Estrategias sin trades son inútiles
                    total_pnl = -10000
                    win_rate = 0.0

                results.append({
                    'metrics': {
                        'Total PnL': total_pnl,
                        'Total Trades': total_trades,
                        'Win Rate %': win_rate
                    }
                })
            except Exception as e:
                print(f"Local Backtest Error: {e}")
                results.append({
                    'metrics': {
                        'Total PnL': -10000,
                        'Total Trades': 0,
                        'Win Rate %': 0.0
                    }
                })
            
            if progress_cb:
                progress_cb((i + 1) / total)
                
        return results
