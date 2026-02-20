"""
Optimizer Runner - Ejecuta optimización en proceso separado
Permite comunicación bidireccional con Streamlit usando multiprocessing.Queue
"""

import multiprocessing as mp
from multiprocessing import Queue, Process
import pandas as pd
import time
import traceback
import os
import ray



def run_optimizer_process(data_dict, param_ranges, risk_level, opt_method,
                          ga_params, progress_queue, result_queue, stop_event, strategy_code="HYBRID", force_local=False):
    """
    Función que corre en un proceso separado.
    Ejecuta la optimización y envía actualizaciones via Queue.

    Args:
        data_dict: DataFrame convertido a dict
        param_ranges: Diccionario de rangos de parámetros
        risk_level: Nivel de riesgo
        opt_method: "grid" o "genetic"
        ga_params: (generations, population, mutation_rate) si es genetic
        progress_queue: Queue para enviar (tipo, mensaje) al UI
        result_queue: Queue para enviar resultado final
        stop_event: Event para señalar detención
    """
    try:
        # Reconstruir DataFrame desde dict of records
        df = pd.DataFrame(data_dict)

        # Log callback que envía a Queue con timestamp
        def log_cb(msg):
            if not stop_event.is_set():
                progress_queue.put(("log", f"[{time.strftime('%H:%M:%S')}] {msg}"))

        # --- RAY INITIALIZATION ---
        log_cb("🔍 Iniciando Entorno Ray...")
        
        # Sincronizar contexto de Streamlit si es posible (oculta avisos)
        try:
            from streamlit.runtime.scriptrunner import add_script_run_ctx
            import threading
            add_script_run_ctx(threading.current_thread())
        except:
            pass

        if ray.is_initialized():
            log_cb("✅ Ray ya está inicializado (Sesión Heredada)")
            connected = True
        else:
            connected = False
            # 1. Try Cluster
            if not force_local:
                try:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    # --- OPTIMIZED CONTEXT BUILDER ---
                    import shutil
                    temp_context_dir = os.path.expanduser("~/.bittrader_head/ray_context")
                    
                    log_cb("📦 Preparando contexto ligero (Code Sync)...")
                    
                    if os.path.exists(temp_context_dir):
                        shutil.rmtree(temp_context_dir)
                    os.makedirs(temp_context_dir, exist_ok=True)
                    
                    # Copy only .py files and strictly necessary assets
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
                                
                    log_cb(f"📋 Contexto con {files_copied} archivos en dir temporal.")
                    
                    ray_addr = os.environ.get("RAY_ADDRESS", "auto")
                    log_cb(f"🌍 Conectando a Ray en: {ray_addr}...")
                    
                    runtime_env = {"working_dir": temp_context_dir}
                    
                    # Timeout guard for init
                    import threading
                    init_done = threading.Event()
                    init_error = []

                    def do_init():
                        try:
                            ray.init(
                                address=ray_addr, 
                                ignore_reinit_error=True, 
                                logging_level="ERROR",
                                runtime_env=runtime_env
                            )
                            init_done.set()
                        except Exception as e:
                            init_error.append(e)
                            init_done.set()

                    init_thread = threading.Thread(target=do_init, daemon=True)
                    init_thread.start()
                    
                    if not init_done.wait(timeout=20):
                        log_cb("⚠️ Timeout conectando al cluster (Posible discrepancia de versiones o saturación).")
                        raise RuntimeError("Ray init timeout")
                    
                    if init_error:
                        raise init_error[0]

                    resources = ray.cluster_resources()
                    cpus = int(resources.get('CPU', 0))
                    log_cb(f"✅ CONECTADO AL CLUSTER ({cpus} CPUs)")
                    connected = True
                except Exception as e:
                    log_cb(f"⚠️ Error Cluster: {str(e)}")
                    if ray.is_initialized(): ray.shutdown()
                    connected = False
            
            # 2. Fallback to Local
            if not connected:
                if force_local:
                     log_cb("🔒 Modo Local Forzado.")
                else:
                     log_cb("⚠️ Iniciando Ray Local...")
                
                try:
                    cores = os.cpu_count() or 4
                    # Use all cores minus 1 for UI responsiveness if running locally
                    ray.init(address='local', num_cpus=max(1, cores), ignore_reinit_error=True, logging_level="ERROR")
                    log_cb(f"✅ Ray Local Iniciado ({max(1, cores)} CPUs)")
                except Exception as e:
                     log_cb(f"❌ Error Ray Init: {e}")


        # Progress callback
        def prog_cb(pct):
            if not stop_event.is_set():
                progress_queue.put(("progress", pct))

        # Importar optimizer (dentro del proceso)
        if opt_method == "genetic":
            from optimizer import GeneticOptimizer
            gens, pop, mut = ga_params
            optimizer = GeneticOptimizer(
                population_size=pop,
                generations=gens,
                mutation_rate=mut,
                force_local=force_local
            )
        elif opt_method == "bayesian":
            from optimizer import BayesianOptimizer
            n_trials = ga_params[0] if ga_params else 100  # Reuse first param as n_trials
            optimizer = BayesianOptimizer(
                n_trials=n_trials,
                force_local=force_local
            )
        elif opt_method == "miner":
            from strategy_miner import StrategyMiner
            gens, pop = ga_params[0], ga_params[1] # Reuse mapping: generations=gens, population=pop
            optimizer = StrategyMiner(
                df=df,
                population_size=pop,
                generations=gens,
                risk_level=risk_level,
                force_local=force_local
            )
        else:
            from optimizer import GridOptimizer
            optimizer = GridOptimizer(force_local=force_local)

        # Ejecutar optimización
        log_cb("🚀 Iniciando optimización en proceso separado...")

        if opt_method == "miner":
            # Strategy Miner Run
            log_cb("🧬 Iniciando Minería de Estrategias con Algoritmos Genéticos...")
            best_genome, best_pnl = optimizer.run(
                progress_callback=lambda type, data: prog_cb((type, data)), 
                cancel_event=stop_event
            )
            
            # Format results to match expected structure or new structure
            # For now, let's wrap it in a DataFrame-like structure or just raw
            results = pd.DataFrame([{
                'params': best_genome,
                'metrics': {'Total PnL': best_pnl, 'Type': 'Best Strategy found'}
            }])
        else:
             # Standard Optimizers
             results = optimizer.optimize(
                df,
                param_ranges,
                risk_level=risk_level,
                progress_callback=prog_cb,
                log_callback=log_cb,
                strategy_code=strategy_code,
                cancel_event=stop_event
             )

        # Enviar resultado
        if not stop_event.is_set():
            # GUARDAR RESULTADO EN DISCO PARA EVITAR SIGSEGV EN QUEUE
            # El DataFrame puede ser muy grande para multiprocessing.Queue en Mac
            import uuid
            
            temp_file = f"temp_opt_results_{uuid.uuid4().hex}.json"
            results.to_json(temp_file, orient='records', indent=2)
            
            # Enviar solo la ruta del archivo
            result_queue.put(("success", temp_file))
            log_cb(f"✅ Optimización completada. Resultados guardados en {temp_file}")
        else:
            result_queue.put(("stopped", None))
            log_cb("⚠️ Optimización detenida por el usuario")

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}\n{traceback.format_exc()}"
        
        # PERSIST CRASH LOG TO FILE
        try:
            with open("OPTIMIZER_CRASH.txt", "w") as f:
                f.write(error_msg)
        except:
            pass
            
        progress_queue.put(("log", error_msg))
        result_queue.put(("error", str(e)))

    finally:
        # ALWAYS shut down Ray to kill remote tasks
        try:
            if ray.is_initialized():
                log_cb("🛑 Cerrando conexión Ray y cancelando tareas...")
                ray.shutdown()
        except:
            pass


class OptimizerRunner:
    """
    Gestiona la ejecución del optimizer en un proceso separado.
    """

    def __init__(self):
        self.process = None
        self.progress_queue = None
        self.result_queue = None
        self.stop_event = None
        self.is_running = False

    def start(self, df, param_ranges, risk_level, opt_method="grid", ga_params=(10, 50, 0.1), strategy_code="HYBRID", force_local=False):
        """
        Inicia la optimización en un proceso separado.

        Returns:
            (progress_queue, result_queue) para leer actualizaciones
        """
        if self.is_running:
            raise RuntimeError("Ya hay una optimización corriendo")

        # Crear queues y event
        self.progress_queue = Queue()
        self.result_queue = Queue()
        self.stop_event = mp.Event()

        # Convertir DataFrame a dict para serialización
        data_dict = df.to_dict('records')

        # Crear y lanzar proceso
        self.process = Process(
            target=run_optimizer_process,
            args=(data_dict, param_ranges, risk_level, opt_method,
                  ga_params, self.progress_queue, self.result_queue, self.stop_event, strategy_code, force_local)
        )

        self.process.start()
        self.is_running = True

        return self.progress_queue, self.result_queue

    def stop(self):
        """Solicita detener la optimización."""
        if self.is_running and self.stop_event:
            self.stop_event.set()

    def is_alive(self):
        """Verifica si el proceso sigue corriendo."""
        if self.process:
            return self.process.is_alive()
        return False

    def cleanup(self):
        """Limpia recursos de forma segura."""
        # Cerrar Queues explícitamente para evitar BrokenPipe/Segfault
        try:
            if self.progress_queue:
                self.progress_queue.close()
                self.progress_queue.join_thread()
            if self.result_queue:
                self.result_queue.close()
                self.result_queue.join_thread()
        except:
            pass

        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=8)

        self.is_running = False
        self.process = None
        self.progress_queue = None
        self.result_queue = None
        self.stop_event = None
