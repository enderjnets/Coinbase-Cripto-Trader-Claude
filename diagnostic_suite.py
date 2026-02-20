#!/usr/bin/env python3
"""
SUITE DE DIAGNÓSTICO COMPLETO
Prueba todos los componentes del sistema paso a paso
"""
import os
import sys
import time
import pandas as pd
import ray
from datetime import datetime

print("=" * 80)
print("🔍 SUITE DE DIAGNÓSTICO DEL SISTEMA DE TRADING")
print("=" * 80)

# TEST 1: Ray Cluster Status
print("\n[TEST 1] Verificando Ray Cluster...")
try:
    if ray.is_initialized():
        print("✅ Ray ya inicializado")
    else:
        ray.init(address='auto', ignore_reinit_error=True)
        print("✅ Ray inicializado")

    resources = ray.cluster_resources()
    nodes = ray.nodes()
    active_nodes = [n for n in nodes if n['Alive']]

    print(f"   - Nodos activos: {len(active_nodes)}")
    print(f"   - CPUs totales: {int(resources.get('CPU', 0))}")
    print(f"   - Memoria: {resources.get('memory', 0) / 1e9:.2f} GB")

    for i, node in enumerate(active_nodes):
        print(f"   - Nodo {i+1}: {node.get('NodeManagerAddress', 'Unknown')}")

except Exception as e:
    print(f"❌ Error en Ray: {e}")
    sys.exit(1)

# TEST 2: Verificar que workers pueden ejecutar código simple
print("\n[TEST 2] Probando distribución de tareas simples...")

@ray.remote
def simple_task(x):
    import time
    time.sleep(0.1)  # Simular trabajo
    return x * 2

try:
    # Lanzar 22 tareas (1 por CPU)
    futures = [simple_task.remote(i) for i in range(22)]
    start = time.time()
    results = ray.get(futures)
    elapsed = time.time() - start

    print(f"✅ {len(results)} tareas completadas en {elapsed:.2f}s")
    print(f"   - Esperado ~0.1s (paralelo), Máximo ~2.2s (serial)")

    if elapsed < 0.5:
        print("   ✅ Ejecución PARALELA confirmada")
    elif elapsed > 2.0:
        print("   ⚠️  Ejecución SERIAL - Workers no están siendo usados")
    else:
        print("   ⚠️  Ejecución parcialmente paralela")

except Exception as e:
    print(f"❌ Error distribuyendo tareas: {e}")

# TEST 3: Verificar datos disponibles
print("\n[TEST 3] Verificando disponibilidad de datos...")

data_files = []
for root, dirs, files in os.walk("data"):
    for f in files:
        if f.endswith('.csv'):
            path = os.path.join(root, f)
            data_files.append(path)

if data_files:
    print(f"✅ Encontrados {len(data_files)} archivos de datos:")
    for f in data_files[:5]:
        size_mb = os.path.getsize(f) / (1024*1024)
        print(f"   - {os.path.basename(f)} ({size_mb:.2f} MB)")

    # Cargar el primer archivo para pruebas
    test_file = data_files[0]
    try:
        df = pd.read_csv(test_file)
        print(f"\n   Cargando: {os.path.basename(test_file)}")
        print(f"   - Filas: {len(df):,}")
        print(f"   - Columnas: {list(df.columns)}")

        if len(df) < 500:
            print("   ❌ DATASET DEMASIADO PEQUEÑO (<500 velas)")
            print("   El backtest NO generará trades con tan pocos datos")
        else:
            print("   ✅ Dataset suficiente para backtesting")

    except Exception as e:
        print(f"   ❌ Error leyendo datos: {e}")
        test_file = None
else:
    print("❌ No hay datos disponibles en data/")
    print("   Descarga datos primero en el Backtester")
    test_file = None

# TEST 4: Probar backtest simple en LOCAL (sin Ray)
print("\n[TEST 4] Probando Backtester en modo LOCAL...")

if test_file:
    try:
        from backtester import Backtester
        from strategy import Strategy

        df = pd.read_csv(test_file)

        # Normalizar columnas
        if 'timestamp' not in df.columns:
            if 'time' in df.columns:
                df = df.rename(columns={'time': 'timestamp'})
            elif 'start' in df.columns:
                df = df.rename(columns={'start': 'timestamp'})

        print(f"   Ejecutando backtest con {len(df)} velas...")

        bt = Backtester()
        equity, trades = bt.run_backtest(df, risk_level="LOW", initial_balance=10000)

        print(f"   ✅ Backtest completado")
        print(f"   - Total trades: {len(trades)}")

        if len(trades) > 0:
            total_pnl = trades['pnl'].sum()
            win_rate = len(trades[trades['pnl'] > 0]) / len(trades) * 100
            print(f"   - PnL Total: ${total_pnl:.2f}")
            print(f"   - Win Rate: {win_rate:.1f}%")

            if total_pnl < -1000:
                print("   ⚠️  PnL muy negativo - posible problema en la estrategia")
        else:
            print("   ⚠️  NO SE GENERARON TRADES")
            print("   Esto puede deberse a:")
            print("      - Dataset muy pequeño")
            print("      - Parámetros de estrategia muy restrictivos")
            print("      - Datos sin suficiente volatilidad")

    except Exception as e:
        print(f"   ❌ Error en backtest: {e}")
        import traceback
        print(traceback.format_exc())

# TEST 5: Probar backtest DISTRIBUIDO en Ray
print("\n[TEST 5] Probando Backtester DISTRIBUIDO en Ray...")

if test_file:
    try:
        from optimizer import run_backtest_task

        df = pd.read_csv(test_file)

        # Normalizar
        if 'timestamp' not in df.columns:
            if 'time' in df.columns:
                df = df.rename(columns={'time': 'timestamp'})

        print(f"   Colocando datos en Ray object store...")
        df_ref = ray.put(df)

        # Lanzar 3 tareas idénticas para verificar consistencia
        print(f"   Lanzando 3 tareas de prueba...")

        test_params = {
            'resistance_period': 50,
            'rsi_period': 14,
            'sl_multiplier': 1.5,
            'tp_multiplier': 3.0
        }

        futures = [
            run_backtest_task.options(scheduling_strategy="SPREAD").remote(
                df_ref, "LOW", test_params, "HYBRID"
            ) for _ in range(3)
        ]

        start = time.time()
        results = ray.get(futures, timeout=60)
        elapsed = time.time() - start

        print(f"   ✅ {len(results)} tareas completadas en {elapsed:.2f}s")

        for i, res in enumerate(results):
            if 'error' in res:
                print(f"   ❌ Tarea {i+1} falló: {res['error']}")
                if 'traceback' in res:
                    print(f"      {res['traceback'][:200]}...")
            else:
                metrics = res.get('metrics', {})
                pnl = metrics.get('Total PnL', 0)
                trades = metrics.get('Total Trades', 0)
                print(f"   ✅ Tarea {i+1}: {trades} trades, PnL ${pnl:.2f}")

        # Verificar consistencia
        pnls = [r.get('metrics', {}).get('Total PnL', -9999) for r in results if 'error' not in r]
        if len(set(pnls)) == 1:
            print(f"   ✅ Resultados CONSISTENTES entre workers")
        else:
            print(f"   ⚠️  Resultados INCONSISTENTES: {pnls}")

    except Exception as e:
        print(f"   ❌ Error en Ray backtest: {e}")
        import traceback
        print(traceback.format_exc())

# TEST 6: Verificar HTTP Server para Strategy Miner
print("\n[TEST 6] Verificando HTTP Data Server...")

try:
    import socket

    # Intentar conectar al puerto 8765
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', 8765))

    if result == 0:
        print("   ✅ HTTP Server corriendo en puerto 8765")
    else:
        print("   ⚠️  HTTP Server NO está corriendo")
        print("   Esto es necesario para Strategy Miner distribuido")

    sock.close()

except Exception as e:
    print(f"   ⚠️  No se pudo verificar HTTP server: {e}")

# TEST 7: Diagnóstico de Strategy Miner
print("\n[TEST 7] Diagnosticando Strategy Miner...")

if test_file:
    try:
        from strategy_miner import StrategyMiner

        df = pd.read_csv(test_file)

        # Normalizar
        if 'timestamp' not in df.columns:
            if 'time' in df.columns:
                df = df.rename(columns={'time': 'timestamp'})

        print(f"   Iniciando miner con dataset de {len(df)} velas...")

        if len(df) < 1000:
            print("   ❌ DATASET DEMASIADO PEQUEÑO")
            print(f"   Actual: {len(df)} velas")
            print(f"   Mínimo recomendado: 1000+ velas")
            print(f"   Para resultados realistas: 5000+ velas")
        else:
            print("   ✅ Dataset adecuado")

        # Crear miner pequeño para prueba
        print("\n   Probando generación de genoma aleatorio...")
        miner = StrategyMiner(
            df=df,
            population_size=5,  # Solo 5 para prueba rápida
            generations=1,
            risk_level="LOW",
            force_local=True  # Local para debug
        )

        genome = miner.generate_random_genome()
        print(f"   ✅ Genoma generado:")
        print(f"      - Reglas: {len(genome['entry_rules'])}")
        print(f"      - SL: {genome['params']['sl_pct']:.3f}")
        print(f"      - TP: {genome['params']['tp_pct']:.3f}")

        print("\n   Probando evaluación LOCAL de 1 genoma...")
        results = miner._evaluate_local([genome], progress_cb=None)

        if results and len(results) > 0:
            pnl = results[0].get('metrics', {}).get('Total PnL', -9999)
            print(f"   ✅ Evaluación completada: PnL ${pnl:.2f}")

            if pnl == -9999 or pnl < -5000:
                print("   ⚠️  PnL extremadamente negativo")
                print("   Posibles causas:")
                print("      1. Dataset muy pequeño → No genera trades")
                print("      2. Genoma aleatorio muy malo")
                print("      3. Error en DynamicStrategy")
        else:
            print("   ❌ Evaluación falló - Sin resultados")

    except Exception as e:
        print(f"   ❌ Error en Strategy Miner: {e}")
        import traceback
        print(traceback.format_exc())

# RESUMEN FINAL
print("\n" + "=" * 80)
print("📊 RESUMEN DEL DIAGNÓSTICO")
print("=" * 80)

print("\n💡 RECOMENDACIONES:")
print("1. Si las tareas no se distribuyen → Verificar firewall/red")
print("2. Si PnL siempre negativo → Dataset muy pequeño o estrategia mala")
print("3. Si NO hay trades → Aumentar tamaño del dataset (mínimo 1000 velas)")
print("4. Para mejores resultados del Miner → Usar 5000+ velas de datos")

print("\n✅ Diagnóstico completado")
print("=" * 80)
