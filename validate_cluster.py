#!/usr/bin/env python3
"""
Script de validación del cluster Ray
Verifica conectividad, recursos y nodos
"""

import os
import sys
from dotenv import load_dotenv

# Cargar .env ANTES de importar Ray
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
    print(f"✅ Variables cargadas desde: {env_path}")
else:
    print(f"⚠️  Archivo .env no encontrado en: {env_path}")

# Mostrar variables de entorno relevantes
print(f"\n📋 Variables de Entorno:")
print(f"   RAY_ADDRESS: {os.environ.get('RAY_ADDRESS', 'NO CONFIGURADA')}")
print(f"   RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER: {os.environ.get('RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER', 'NO CONFIGURADA')}")

import ray
import time

print("\n" + "="*80)
print("🔍 VALIDACIÓN DEL CLUSTER RAY")
print("="*80 + "\n")

# Intentar conectar a Ray
try:
    print("📡 Intentando conectar al cluster...")

    # Usar la misma lógica que el código de producción
    ray_addr = os.environ.get("RAY_ADDRESS")
    if not ray_addr:
        print("❌ ERROR: RAY_ADDRESS no está configurada en .env")
        print("   Por favor, asegúrate de que .env contiene: RAY_ADDRESS=100.77.179.14:6379")
        sys.exit(1)

    print(f"   Dirección: {ray_addr}")

    ray.init(
        address=ray_addr,
        ignore_reinit_error=True,
        logging_level="INFO"  # Más verboso para diagnóstico
    )

    print("✅ Conexión exitosa a Ray\n")

    # Obtener información del cluster
    resources = ray.cluster_resources()
    nodes = ray.nodes()

    print("="*80)
    print("📊 INFORMACIÓN DEL CLUSTER")
    print("="*80 + "\n")

    # Recursos totales
    print("💻 Recursos Totales:")
    total_cpus = int(resources.get('CPU', 0))
    total_memory = resources.get('memory', 0) / (1024**3)  # GB
    total_object_store = resources.get('object_store_memory', 0) / (1024**3)  # GB

    print(f"   CPUs: {total_cpus}")
    print(f"   Memoria: {total_memory:.2f} GB")
    print(f"   Object Store: {total_object_store:.2f} GB")

    # Información de nodos
    print(f"\n🖥️  Nodos del Cluster: {len(nodes)}")
    alive_nodes = [n for n in nodes if n.get('Alive', False)]
    print(f"   Nodos Activos: {len(alive_nodes)}\n")

    for i, node in enumerate(alive_nodes):
        node_resources = node.get('Resources', {})
        node_ip = node.get('NodeManagerAddress', 'Unknown')
        node_hostname = node.get('NodeName', 'Unknown')

        print(f"   Nodo {i+1}:")
        print(f"      IP: {node_ip}")
        print(f"      Hostname: {node_hostname}")
        print(f"      CPUs: {int(node_resources.get('CPU', 0))}")
        print(f"      Memoria: {node_resources.get('memory', 0) / (1024**3):.2f} GB")
        print()

    # Test de conectividad - enviar una tarea simple
    print("="*80)
    print("🧪 TEST DE CONECTIVIDAD")
    print("="*80 + "\n")

    @ray.remote
    def test_task(x):
        import socket
        import os
        return {
            'result': x * 2,
            'hostname': socket.gethostname(),
            'pid': os.getpid(),
            'node_ip': ray.util.get_node_ip_address()
        }

    print("📤 Enviando 10 tareas de prueba al cluster...")
    start_time = time.time()

    futures = [test_task.options(scheduling_strategy="SPREAD").remote(i) for i in range(10)]
    results = ray.get(futures)

    end_time = time.time()

    print(f"✅ 10 tareas completadas en {end_time - start_time:.2f} segundos\n")

    # Verificar distribución de tareas
    nodes_used = set()
    for i, res in enumerate(results):
        print(f"   Tarea {i}: ejecutada en {res['hostname']} ({res['node_ip']}) - PID: {res['pid']}")
        nodes_used.add(res['node_ip'])

    print(f"\n📊 Resumen de Distribución:")
    print(f"   Nodos únicos utilizados: {len(nodes_used)}")
    print(f"   Distribución esperada: {len(alive_nodes)} nodos")

    if len(nodes_used) == len(alive_nodes):
        print("   ✅ Las tareas se distribuyeron correctamente en todos los nodos")
    elif len(nodes_used) == 1:
        print("   ⚠️  PROBLEMA: Todas las tareas se ejecutaron en un solo nodo")
        print("      Esto sugiere que el worker remoto no está recibiendo tareas")
    else:
        print(f"   ⚠️  Distribución parcial: {len(nodes_used)}/{len(alive_nodes)} nodos")

    # Test de carga de datos (simular lo que hace el Strategy Miner)
    print("\n" + "="*80)
    print("🧪 TEST DE TRANSFERENCIA DE DATOS")
    print("="*80 + "\n")

    import pandas as pd

    # Crear DataFrame de prueba
    test_df = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=1000, freq='5min'),
        'close': [100.0 + i*0.1 for i in range(1000)],
        'volume': [1000000] * 1000
    })

    print(f"📊 Creando DataFrame de prueba: {test_df.shape}")

    @ray.remote
    def process_dataframe(df):
        import pandas as pd
        return {
            'shape': df.shape,
            'columns': list(df.columns),
            'first_timestamp': str(df.iloc[0]['timestamp']),
            'last_timestamp': str(df.iloc[-1]['timestamp'])
        }

    print("📤 Enviando DataFrame como ObjectRef...")
    df_ref = ray.put(test_df)

    print("🔄 Ejecutando tarea en worker remoto...")
    future = process_dataframe.options(scheduling_strategy="SPREAD").remote(df_ref)
    result = ray.get(future, timeout=30)

    print(f"✅ Datos recibidos y procesados correctamente:")
    print(f"   Shape: {result['shape']}")
    print(f"   Columns: {result['columns']}")
    print(f"   Range: {result['first_timestamp']} -> {result['last_timestamp']}")

    # Resumen final
    print("\n" + "="*80)
    print("📋 RESUMEN DE VALIDACIÓN")
    print("="*80 + "\n")

    validation_status = {
        'Conexión al cluster': '✅',
        f'Recursos disponibles ({total_cpus} CPUs)': '✅' if total_cpus >= 20 else '⚠️',
        f'Nodos activos ({len(alive_nodes)}/{len(nodes)})': '✅' if len(alive_nodes) >= 2 else '⚠️',
        'Distribución de tareas': '✅' if len(nodes_used) >= 2 else '⚠️',
        'Transferencia de datos': '✅'
    }

    for check, status in validation_status.items():
        print(f"{status} {check}")

    all_passed = all(s == '✅' for s in validation_status.values())

    if all_passed:
        print("\n🎉 ¡TODAS LAS VALIDACIONES PASARON!")
        print("   El cluster está funcionando correctamente para Strategy Miner")
    else:
        print("\n⚠️  ALGUNAS VALIDACIONES FALLARON")
        print("   Revisa los problemas identificados arriba")

    print("\n" + "="*80 + "\n")

    ray.shutdown()
    sys.exit(0 if all_passed else 1)

except Exception as e:
    print(f"\n❌ ERROR durante la validación:")
    print(f"   {str(e)}")
    import traceback
    print("\nTraceback completo:")
    print(traceback.format_exc())

    if ray.is_initialized():
        ray.shutdown()

    sys.exit(1)
