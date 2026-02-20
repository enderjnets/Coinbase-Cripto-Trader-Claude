# Instrucciones para Reconectar Worker Node

## Situación Actual
El nodo Head (MacBook Pro) está operativo con 10 CPUs, pero el nodo Worker (MacBook Air) se desconectó y necesita reconexión manual.

---

## Pasos para Reconectar (Ejecutar en MacBook Air)

### Opción 1: Usando Terminal

Abre Terminal y ejecuta los siguientes comandos uno por uno:

```bash
# 1. Navegar al directorio del worker
cd ~/.bittrader_worker

# 2. Activar entorno virtual
source venv/bin/activate

# 3. Exportar variable de entorno necesaria
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1

# 4. Detener procesos Ray anteriores
ray stop --force

# 5. Esperar 2 segundos
sleep 2

# 6. Conectar al Head Node
ray start --address='100.118.215.73:6379' --disable-usage-stats
```

Deberías ver un mensaje como:
```
Ray runtime started.
Connected to Ray cluster at address: 100.118.215.73:6379
```

### Opción 2: Usando el Instalador (Más fácil)

1. En el Escritorio del MacBook Air, busca el archivo:
   - **`START_WORKER`** (acceso directo)

2. Haz doble clic en él

3. Si hay un error, ejecuta primero:
   ```bash
   cd ~/.bittrader_worker
   source venv/bin/activate
   ray stop --force
   ```

4. Luego vuelve a hacer doble clic en **START_WORKER**

---

## Verificación de Conexión

### Desde MacBook Air (Worker):
Deberías ver en la terminal:
```
✅ Ray runtime started.
Connected to Ray cluster at address: 100.118.215.73:6379
```

### Desde MacBook Pro (Head):
Ejecuta el script de verificación:

```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
source .venv/bin/activate
python3 check_cluster.py
```

Deberías ver:
```
Nodos activos: 2/X
Total CPUs: 22
  Nodo 1: 100.118.215.73 - 12 CPUs
  Nodo 2: 100.77.179.14 - 10 CPUs
```

---

## Problemas Comunes

### Problema 1: "Connection refused"
**Solución:** El Head node no está corriendo. En MacBook Pro:
```bash
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
source .venv/bin/activate
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
ray start --head --port=6379 --node-ip-address=100.118.215.73 --dashboard-host=0.0.0.0
```

### Problema 2: "Address already in use"
**Solución:** Ya hay un proceso Ray corriendo:
```bash
ray stop --force
sleep 2
# Luego vuelve a intentar el paso 6
```

### Problema 3: "Version mismatch"
**Solución:** Las versiones de Ray no coinciden. Asegúrate de usar los entornos virtuales correctos:
- MacBook Pro (Head): `.venv` con Python 3.9.6 y Ray 2.51.2
- MacBook Air (Worker): `~/.bittrader_worker/venv` con Python 3.9.6 y Ray 2.51.2

---

## Ejecutar Test Completo (Después de Reconectar)

Una vez que ambos nodos estén conectados (22 CPUs total), puedes ejecutar el test completo:

```bash
# En MacBook Pro (Head)
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
source .venv/bin/activate
python3 test_miner_heavy_load.py
```

Este test ejecutará 80 evaluaciones distribuidas entre ambos nodos.

---

## Monitoreo del Cluster

### Ver Dashboard de Ray
Abre tu navegador y ve a:
```
http://100.118.215.73:8265
```

Aquí podrás ver:
- Nodos conectados
- Uso de CPU/RAM en tiempo real
- Tareas en ejecución
- Logs de workers

### Ver Estado desde Terminal
```bash
# En MacBook Pro
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
source .venv/bin/activate
ray status
```

---

**Nota:** Si tienes problemas, revisa el archivo `STRESS_TEST_REPORT.md` para más detalles sobre la configuración del cluster.
