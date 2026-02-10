#!/usr/bin/env python3
"""
Script de diagnóstico para el cluster Ray
Muestra información detallada sobre recursos, nodos y tareas activas
"""

import ray
import time
from pprint import pprint

print("=" * 70)
print("🔍 DIAGNÓSTICO DEL CLUSTER RAY")
print("=" * 70)

# Conectar al cluster
ray.init(address='auto', ignore_reinit_error=True)

# 1. Recursos del Cluster
print("\n📊 RECURSOS DEL CLUSTER")
print("-" * 70)
cluster_resources = ray.cluster_resources()
print(f"Total CPUs: {cluster_resources.get('CPU', 0)}")
print(f"Total Memory: {cluster_resources.get('memory', 0) / (1024**3):.2f} GB")
print(f"Total Object Store: {cluster_resources.get('object_store_memory', 0) / (1024**3):.2f} GB")

# 2. Recursos Disponibles
print("\n✅ RECURSOS DISPONIBLES (LIBRES)")
print("-" * 70)
available = ray.available_resources()
print(f"CPUs Libres: {available.get('CPU', 0)}")
print(f"Memory Libre: {available.get('memory', 0) / (1024**3):.2f} GB")
print(f"Object Store Libre: {available.get('object_store_memory', 0) / (1024**3):.2f} GB")

# 3. Información de Nodos
print("\n🖥️  NODOS EN EL CLUSTER")
print("-" * 70)
nodes = ray.nodes()
for idx, node in enumerate(nodes):
    if not node['Alive']:
        continue
    
    print(f"\nNodo {idx + 1}:")
    print(f"  IP: {node.get('NodeManagerAddress', 'Unknown')}")
    print(f"  Hostname: {node.get('NodeManagerHostname', 'Unknown')}")
    print(f"  Estado: {'✅ Activo' if node['Alive'] else '❌ Inactivo'}")
    print(f"  Recursos:")
    
    resources = node.get('Resources', {})
    print(f"    - CPUs: {resources.get('CPU', 0)}")
    print(f"    - Memory: {resources.get('memory', 0) / (1024**3):.2f} GB")
    print(f"    - Object Store: {resources.get('object_store_memory', 0) / (1024**3):.2f} GB")

# 4. Cálculo de CPUs en Uso
print("\n⚙️  ANÁLISIS DE USO DE CPUs")
print("-" * 70)
total_cpus = cluster_resources.get('CPU', 0)
available_cpus = available.get('CPU', 0)
used_cpus = total_cpus - available_cpus

print(f"CPUs Totales: {total_cpus}")
print(f"CPUs Libres:  {available_cpus}")
print(f"CPUs en Uso:  {used_cpus}")
print(f"Porcentaje de Uso: {(used_cpus / total_cpus) * 100:.1f}%")

if used_cpus > (total_cpus * 0.8):
    print("\n⚠️  ALERTA: Más del 80% de las CPUs están en uso")
    print("    Posibles causas:")
    print("    - Tareas bloqueadas o en deadlock")
    print("    - Object Store lleno")
    print("    - Tareas esperando por dependencias")

# 5. Estado del Object Store
print("\n💾 ESTADO DEL OBJECT STORE")
print("-" * 70)
total_object_store = cluster_resources.get('object_store_memory', 0)
available_object_store = available.get('object_store_memory', 0)
used_object_store = total_object_store - available_object_store

print(f"Object Store Total: {total_object_store / (1024**3):.2f} GB")
print(f"Object Store Libre: {available_object_store / (1024**3):.2f} GB")
print(f"Object Store en Uso: {used_object_store / (1024**3):.2f} GB")
print(f"Porcentaje de Uso: {(used_object_store / total_object_store) * 100:.1f}%")

# 6. Recomendaciones
print("\n💡 RECOMENDACIONES")
print("-" * 70)

if used_cpus > (total_cpus * 0.8) and available_cpus < 3:
    print("🔴 PROBLEMA DETECTADO: Alta utilización de CPUs pero pocas tareas completándose")
    print("\nAcciones recomendadas:")
    print("1. Detener la optimización actual en la interfaz")
    print("2. Reiniciar el cluster Ray:")
    print("   - En MacBook Air y MacBook Pro: ray stop")
    print("   - En MacBook Air (HEAD): python3 start_cluster_head.py")
    print("   - En MacBook Pro (WORKER): ray start --address='10.0.0.239:6379'")
else:
    print("✅ El cluster parece estar funcionando normalmente")

print("\n" + "=" * 70)
print("Diagnóstico completado")
print("=" * 70)
