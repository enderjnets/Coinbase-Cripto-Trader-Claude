import pandas as pd
import ray
import os
import sys

# Ensure current directory is in path
sys.path.append(os.getcwd())

from strategy_miner import StrategyMiner

def test_miner():
    print("🚀 Iniciando Simulación de Strategy Miner (Modo Standalone)...")
    
    # 1. Configurar Ray
    print("📡 Conectando al Cluster Ray existente...")
    try:
        ray.init(address='auto', ignore_reinit_error=True)
        print("✅ Conectado a Ray!")
        print(f"   Recursos CPU: {ray.cluster_resources().get('CPU')}")
    except Exception as e:
        print(f"⚠️ No se pudo conectar a cluster existente: {e}")
        print("   Iniciando Ray localmente...")
        ray.init()

    # 2. Cargar Datos
    data_path = "data/BTC-USD_ONE_HOUR.csv"
    if not os.path.exists(data_path):
        print(f"❌ Error: No se encuentra {data_path}")
        return

    print(f"📂 Cargando datos de {data_path}...")
    df = pd.read_csv(data_path)
    
    # Pre-process columns standard for this project
    df.columns = [c.lower() for c in df.columns]
    # Ensure datetime index if needed? Backtester usually handles it or just df structure.
    # We will assume CSV has valid structure (time, open, high, low, close, volume)
    
    # Limitar datos para prueba rápida
    df_small = df.tail(2000).copy() # Last 2000 hours (~3 months)
    print(f"   Datos cargados: {len(df_small)} velas.")

    # 3. Inicializar Minero
    print("🧬 Inicializando Strategy Miner...")
    miner = StrategyMiner(
        df=df_small,
        population_size=10,   # Micro población
        generations=2,        # Micro evolución
        risk_level="LOW",
        force_local=True      # <--- Avoid Ray queue
    )

    # 4. Correr Evolución
    print("🏃 Ejecutando Evolución (2 Generaciones)...")
    
    start_time = pd.Timestamp.now()
    
    def progress_callback(step, data=None):
        if step == "START_GEN":
            print(f"   Using generation {data}...")
        elif step == "BEST_GEN":
            print(f"   🌟 Generación {data['gen']} Mejor PnL: {data['pnl']:.2f}")
            print(f"      Genome: {data['genome']['entry_rules']}")

    best_genome, best_pnl = miner.run(progress_callback=progress_callback)
    
    end_time = pd.Timestamp.now()
    duration = end_time - start_time
    
    # 5. Reporte
    print("\n🎉 Simulación Completada Exitosamente!")
    print(f"⏱️ Duración: {duration}")
    print(f"🏆 Mejor Estrategia PnL: {best_pnl}")
    print(f"📜 Reglas: {best_genome['entry_rules']}")
    print(f"🔧 Params: {best_genome['params']}")

if __name__ == "__main__":
    test_miner()
