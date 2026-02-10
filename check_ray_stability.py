
import ray
import time
import os
import sys

# Configuración simplificada para prueba
os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

@ray.remote
def simple_task(x):
    time.sleep(0.1)
    return x * x

def test_ray_stability():
    print("🚀 Iniciando prueba de estabilidad de Ray...")
    
    # 1. Conexión
    try:
        ray.init(address='auto', ignore_reinit_error=True)
        print("✅ Conectado a Ray")
    except Exception as e:
        print(f"⚠️ No se pudo conectar a 'auto', iniciando local: {e}")
        ray.init(ignore_reinit_error=True)

    print(f"Cluster Resources: {ray.cluster_resources()}")

    # 2. Carga Masiva (Stress Test)
    tasks = []
    print("⏳ Lanzando 500 tareas rápidas...")
    for i in range(500):
        tasks.append(simple_task.remote(i))
    
    # 3. Recolección con verificacion de errores
    try:
        start = time.time()
        results = ray.get(tasks)
        end = time.time()
        print(f"✅ 500 tareas completadas en {end - start:.2f}s")
        print(f"Sample result: {results[0]}")
    except Exception as e:
        print(f"❌ FALLO EN TAREAS: {e}")
        return False

    print("✅ Prueba de Estabilidad EXITOSA")
    return True

if __name__ == "__main__":
    if test_ray_stability():
        sys.exit(0)
    else:
        sys.exit(1)
