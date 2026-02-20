# 🔧 INSTRUCCIONES - CONECTAR WORKER (MacBook Air)

**Fecha:** 30 Enero 2026, 16:53 PM
**HEAD Node:** MacBook Pro (100.118.215.73)
**Worker Node:** MacBook Air (a conectar)

---

## ✅ PASO 1: VERIFICAR HEAD (YA HECHO)

El HEAD de Ray ya está corriendo en la MacBook Pro:

```
✅ IP del HEAD: 100.118.215.73
✅ Puerto: 6379
✅ CPUs disponibles: 12
✅ Estado: ACTIVO
```

---

## 🖥️ PASO 2: CONECTAR WORKER DESDE MACBOOK AIR

### Opción A: Usando SSH (RECOMENDADO) ⭐

**Desde la MacBook Air, ejecuta estos comandos:**

```bash
# 1. Conectarse por SSH a la MacBook Air
ssh enderj@MacBookAir.local

# 2. Navegar al directorio del Worker
cd ~/.bittrader_worker

# 3. Activar el entorno virtual
source venv/bin/activate

# 4. Conectar el Worker al HEAD
ray start \
  --address='100.118.215.73:6379' \
  --num-cpus=6 \
  --node-ip-address=$(tailscale ip -4)
```

**Deberías ver:**
```
✅ Ray runtime started.
✅ Connected to Ray cluster at 100.118.215.73:6379
```

---

### Opción B: Script automático (MÁS FÁCIL) ⭐⭐⭐

**1. Desde esta MacBook Pro, ejecuta:**

```bash
ssh enderj@MacBookAir.local "cd ~/.bittrader_worker && source venv/bin/activate && ray start --address='100.118.215.73:6379' --num-cpus=6"
```

**2. Verificar conexión:**

```bash
cd ~/.bittrader_head && source venv/bin/activate && python3 -c "import ray; ray.init(address='auto'); print('Recursos totales:', ray.cluster_resources())"
```

**Deberías ver:**
```
CPU: 18.0  (12 HEAD + 6 Worker)
```

---

## 🔍 PASO 3: VERIFICAR QUE EL CLUSTER FUNCIONA

**Ejecuta este test desde la MacBook Pro:**

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

python3 -c "
import ray
ray.init(address='auto')

@ray.remote
def test_task(x):
    import socket
    return f'Task {x} ejecutada en {socket.gethostname()}'

# Ejecutar 10 tareas
futures = [test_task.remote(i) for i in range(10)]
results = ray.get(futures)

for r in results:
    print(r)

print(f'\n✅ Cluster funcionando: {ray.cluster_resources()}')
ray.shutdown()
"
```

**Si funciona correctamente, verás:**
- Tareas ejecutadas en ambas máquinas
- CPU: 18.0 en el cluster

---

## ⚠️ PROBLEMAS COMUNES

### Problema 1: "Connection refused"

**Solución:**
```bash
# En MacBook Pro - Verificar que el HEAD esté corriendo
ps aux | grep "ray start --head"

# Si no está corriendo, iniciarlo:
cd ~/.bittrader_head && source venv/bin/activate
ray start --head --port=6379 --node-ip-address=100.118.215.73 --include-dashboard=false --num-cpus=12
```

### Problema 2: "Worker no conecta"

**Solución:**
```bash
# En MacBook Air - Limpiar Ray y reintentar
ray stop
sleep 5
ray start --address='100.118.215.73:6379' --num-cpus=6
```

### Problema 3: "Solo ve 12 CPUs (no 18)"

**Causas posibles:**
- Worker no está conectado
- Worker tuvo un error al iniciar
- Firewall bloqueando el puerto 6379

**Solución:**
```bash
# En MacBook Pro - Ver estado del cluster
cd ~/.bittrader_head && source venv/bin/activate
ray status

# Debería mostrar 2 nodos activos
```

---

## 🎯 DESPUÉS DE CONECTAR

Una vez que el Worker esté conectado (18 CPUs totales), puedes:

### 1. Ejecutar búsqueda con cluster

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Ejecutar con el cluster completo (18 CPUs)
python3 test_miner_cluster.py
```

### 2. Ejecutar búsqueda larga optimizada

```bash
# Búsqueda masiva con todo el cluster
python3 run_optimized_miner.py
```

### 3. Verificar que usa ambos nodos

Mientras corre, abre otra terminal y ejecuta:

```bash
cd ~/.bittrader_head && source venv/bin/activate
python3 -c "
import ray
ray.init(address='auto')
import time
while True:
    print(ray.cluster_resources())
    time.sleep(5)
"
```

---

## 📊 RENDIMIENTO ESPERADO

| Configuración | CPUs | Población | Generaciones | Tiempo Estimado |
|--------------|------|-----------|--------------|-----------------|
| Solo HEAD | 12 | 40 | 30 | ~35 min |
| HEAD + Worker | 18 | 60 | 40 | ~35 min |
| HEAD + Worker | 18 | 90 | 50 | ~60 min |

**Beneficio:** 3x más estrategias evaluadas en el mismo tiempo

---

## 🔌 DESCONECTAR EL WORKER

Cuando termines:

```bash
# En MacBook Air
ray stop

# En MacBook Pro (si quieres apagar todo)
ray stop
```

---

## ✅ CHECKLIST DE CONEXIÓN

- [ ] HEAD iniciado en MacBook Pro (100.118.215.73:6379)
- [ ] Worker conectado desde MacBook Air
- [ ] Cluster muestra 18 CPUs totales
- [ ] Test ejecuta tareas en ambos nodos
- [ ] Listo para ejecutar búsquedas

---

## 💡 TIPS

1. **Mantén el HEAD activo:** El HEAD debe estar corriendo ANTES de conectar el Worker

2. **Verifica Tailscale:** Ambas máquinas deben estar conectadas a Tailscale

3. **SSH debe funcionar:** Prueba `ssh enderj@MacBookAir.local` primero

4. **Worker puede reconectarse:** Si se desconecta, solo vuelve a ejecutar `ray start`

5. **Monitorea recursos:** Usa `ray status` para ver el estado del cluster

---

**¿Necesitas ayuda? Dime en qué paso estás y te guío.**

