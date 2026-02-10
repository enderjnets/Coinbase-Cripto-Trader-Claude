"""
Backtest Runner - Ejecuta UNA simulación en el Clúster Ray
Permite usar la 'granja' para una simulación individual y liberar la UI.
"""

import multiprocessing as mp
from multiprocessing import Queue, Process
import pandas as pd
import time
import os
import ray
from backtester import Backtester

# Ray Task for Single Backtest
@ray.remote
def run_single_backtest_task(df, risk_level, strategy_params, strategy_code):
    try:
        bt = Backtester()
        
        # Resolve Strategy Class
        strat_cls = None
        if strategy_code == "BTC_SPOT":
            from btc_spot_strategy import BitcoinSpotStrategy
            strat_cls = BitcoinSpotStrategy
        # Add others if needed
        
        # Run Backtest
        # strategy_cls defaults to None -> Hybrid or handles generic
        equity, trades = bt.run_backtest(
            df, 
            risk_level=risk_level, 
            strategy_params=strategy_params, 
            strategy_cls=strat_cls
        )
        
        # Return results as dictionaries/lists for easy serialization
        return {
            'equity': equity.to_dict('records'),
            'trades': trades.to_dict('records')
        }
    except Exception as e:
        import traceback
        return {'error': str(e), 'traceback': traceback.format_exc()}


def run_backtest_process(df_dict, risk_level, strategy_params, strategy_code, progress_queue, result_queue):
    """
    Background process that manages the Ray Task.
    """
    try:
        # Reconstruct DataFrame
        df = pd.DataFrame(df_dict)
        
        def log(msg):
            progress_queue.put(("log", msg))
            
        log("🚀 Iniciando Backtest Distribuido (Ray)...")
        
        # Initialize Ray if needed
        if not ray.is_initialized():
            log("🔌 Conectando al Clúster Ray...")
            connected = False
            
            # 1. Try Cluster
            if not False: # force_local logic can stay simple here
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    # --- OPTIMIZED CONTEXT BUILDER (SHARED) ---
                    import shutil
                    temp_context_dir = os.path.expanduser("~/.bittrader_head/ray_context")
                    
                    log("📦 Preparando contexto ligero para Ray...")
                    
                    if os.path.exists(temp_context_dir):
                        try: shutil.rmtree(temp_context_dir)
                        except: pass
                    os.makedirs(temp_context_dir, exist_ok=True)
                    
                    files_copied = 0
                    for root, dirs, files in os.walk(current_dir):
                        dirs[:] = [d for d in dirs if d not in 
                                   ['data', 'vps_package', '.venv', 'worker_env', '.git', '__pycache__', 'optimization_checkpoints']]
                        for file in files:
                            if file.endswith(".py") or file in ["requirements.txt", ".env"]:
                                src = os.path.join(root, file)
                                rel_path = os.path.relpath(src, current_dir)
                                dst = os.path.join(temp_context_dir, rel_path)
                                os.makedirs(os.path.dirname(dst), exist_ok=True)
                                shutil.copy2(src, dst)
                                files_copied += 1
                                
                    log(f"📋 Contexto creado con {files_copied} archivos.")
                    
                    runtime_env = {"working_dir": temp_context_dir}
                    ray.init(address='auto', ignore_reinit_error=True, logging_level="ERROR", runtime_env=runtime_env)
                    log("✅ Conectado a Clúster Ray con Sincronización")
                    connected = True
                except Exception as e:
                    log(f"⚠️ Cluster no encontrado o error: {e}")
                    connected = False

            # 2. Local Fallback
            if not connected:
                log("⚠️ Iniciando Ray LOCAL...")
                total_cores = os.cpu_count() or 4
                safe_cores = max(1, total_cores - 2)
                log(f"⚙️ Configurando Ray LOCAL ({safe_cores} CPUs)")
                ray.init(ignore_reinit_error=True, num_cpus=safe_cores)

        # Log Cluster Resources
        try:
            resources = ray.cluster_resources()
            total_cpus = int(resources.get('CPU', 0))
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

        # Push Data
        log("📦 Enviando datos al Clúster...")
        df_ref = ray.put(df)
        
        # Submit Task
        log(f"⚡ Ejecutando estrategia {strategy_code} en la granja...")
        future = run_single_backtest_task.remote(df_ref, risk_level, strategy_params, strategy_code)
        
        # Wait for result
        while True:
            done, _ = ray.wait([future], timeout=0.5)
            if done:
                result = ray.get(done[0])  # Get from 'done' list, not 'future'
                break
            # Fake progress pulse to UI doesn't think it's dead
            # (Real progress inside a remote task is hard to stream back cheaply without actors)
            # We just show "Running..."
            progress_queue.put(("progress", 0.5))
            
        if 'error' in result:
             raise Exception(result['error'])
             
        log("✅ Backtest Finalizado Exitosamente.")
        progress_queue.put(("progress", 1.0))
        result_queue.put(("success", result))
        
    except Exception as e:
        progress_queue.put(("log", f"❌ Error: {e}"))
        result_queue.put(("error", str(e)))


class BacktestRunner:
    def __init__(self):
        self.process = None
        self.progress_queue = None
        self.result_queue = None
        
    def start(self, df, risk_level, strategy_params, strategy_code):
        self.progress_queue = Queue()
        self.result_queue = Queue()
        
        df_dict = df.to_dict('records')
        
        self.process = Process(
            target=run_backtest_process,
            args=(df_dict, risk_level, strategy_params, strategy_code, self.progress_queue, self.result_queue)
        )
        self.process.start()
        return self.progress_queue, self.result_queue

    def is_alive(self):
        return self.process and self.process.is_alive()
        
    def cleanup(self):
        if self.process and self.process.is_alive():
            self.process.terminate()
