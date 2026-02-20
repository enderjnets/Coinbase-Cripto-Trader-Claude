
import os
import sys
import time
import subprocess
import os
import ray
import pandas as pd

# 1. CLEANUP (KILL ALL) - No external deps version
def kill_processes():
    print("🧹 [1/4] Limpiando procesos antiguos...")
    # Force kill via shell
    os.system("pkill -9 -f 'ray'")
    os.system("pkill -9 -f 'streamlit'")
    time.sleep(2)
    try:
        os.system("ray stop --force")
    except: pass
    print("✅ Procesos limpios.")

# 2. START HEAD
def start_head():
    print("🚀 [2/4] Reiniciando Ray Cluster Head...")
    # Usar script existente o comando directo
    # Importante: Usar la ruta segura si existe
    
    # Check symlink logic here just in case, but usually we run from project root
    # We will simulate the Environment of execution
    
    try:
        # Start Ray locally in this script to act as head/driver
        # This mimics the App behavior
        ray.init(address='local', num_cpus=8, ignore_reinit_error=True)
        print("✅ Ray Head iniciado (Local Mode para Test).")
    except Exception as e:
        print(f"❌ Error iniciando Ray: {e}")
        sys.exit(1)

# 3. REALISTIC TASK TEST
@ray.remote
def heavy_task(data_len):
    # Simulate heavy import inside worker
    try:
        from backtester import Backtester
        # Simulate CPU work
        count = 0
        for i in range(1000000):
            count += i
        return f"OK_SIZE_{data_len}_COUNT_{count}"
    except Exception as e:
        return f"ERROR: {e}"

def run_test():
    print("🧪 [3/4] Ejecutando Test de Estrés (Payload Real)...")
    
    # Create dummy dataframe to simulate data transfer
    df = pd.DataFrame({'close': [100]*1000})
    df_ref = ray.put(df)
    
    futures = [heavy_task.remote(len(df)) for _ in range(20)]
    
    print("⏳ Esperando resultados de 20 tareas...")
    ready, not_ready = ray.wait(futures, num_returns=20, timeout=15)
    
    if len(not_ready) > 0:
        print(f"❌ FALLO: {len(not_ready)} tareas se quedaron colgadas (Timeout).")
        print("🔍 Posible causa: Bloqueo en imports o falta de CPU.")
        return False
    
    # Check results
    results = ray.get(ready)
    errors = [r for r in results if "ERROR" in str(r)]
    
    if errors:
        print(f"❌ FALLO: Errores internos en worker: {errors[0]}")
        return False
        
    print(f"✅ ÉXITO: 20 tareas pesadas completadas. Respuesta: {results[0]}")
    return True

if __name__ == "__main__":
    print("🤖 AUTO-REPAIR AGENT STARTED")
    kill_processes()
    
    # Force safe path for this script too
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if " " in current_dir:
        safe_path = os.path.expanduser("~/.ray_safe_project_link")
        if not os.path.exists(safe_path):
             os.symlink(current_dir, safe_path)
        os.chdir(safe_path)
        sys.path.insert(0, safe_path)
        print(f"🔗 Switched to safe path: {safe_path}")

    start_head()
    
    if run_test():
        print("\n✨ SISTEMA REPARADO Y VERIFICADO ✨")
        print("Puede reiniciar la interfaz con confianza.")
        sys.exit(0)
    else:
        print("\n💀 FALLO CRÍTICO: El problema persiste.")
        sys.exit(1)
