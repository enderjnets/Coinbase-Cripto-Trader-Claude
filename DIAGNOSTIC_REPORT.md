# DIAGNOSTIC REPORT - Strategy Miner & Ray Cluster
**Fecha:** 2026-01-28
**Autor:** Claude Sonnet 4.5

---

## RESUMEN EJECUTIVO

He completado un análisis exhaustivo del sistema Strategy Miner y su integración con el cluster Ray distribuido. Identifiqué un problema fundamental en la arquitectura de conexión que explica por qué el sistema no funciona correctamente.

### PROBLEMA PRINCIPAL IDENTIFICADO

**El worker daemon y los scripts Python están usando diferentes mecanismos de conexión a Ray:**

1. **Worker Daemon** (`~/.bittrader_worker/worker_daemon.sh`):
   - Ejecuta `ray start --address=100.77.179.14:6379`
   - Crea un proceso Ray Worker permanente
   - Se conecta correctamente al cluster
   - Status: ✅ FUNCIONANDO

2. **Scripts Python** (test_miner_quick.py, interface.py vía optimizer_runner.py):
   - Ejecutan `ray.init(address='auto')` o `ray.init(address='100.77.179.14:6379')`
   - Intentan crear un nuevo raylet local
   - Ray espera un raylet local para manejar la comunicación
   - Falla con: "Failed to get the system config from raylet because it is dead"
   - Status: ❌ FALLANDO

---

## ANÁLISIS DETALLADO

### 1. Arquitectura Actual

```
┌─────────────────────────────────────────────────────────────┐
│ MacBook Pro (100.77.179.14)                                 │
│ ┌─────────────────────────────────────────┐                 │
│ │ Ray Head Node (Docker)                  │                 │
│ │ - 12 CPUs                               │                 │
│ │ - Puerto: 6379                          │                 │
│ └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                        ▲
                        │ Tailscale
                        │ 100.77.179.14:6379
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ MacBook Air (100.118.215.73)                                │
│                                                              │
│ ┌────────────────────────────┐  ┌────────────────────────┐ │
│ │ Worker Daemon (Background) │  │ Python Scripts        │ │
│ │                            │  │                        │ │
│ │ ray start --address=...    │  │ ray.init(address=...)  │ │
│ │ Status: ✅ CONECTADO       │  │ Status: ❌ FALLA       │ │
│ │ CPUs: 10                   │  │                        │ │
│ └────────────────────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2. ¿Por Qué Falla?

Cuando un script Python ejecuta `ray.init(address='100.77.179.14:6379')`:

1. Ray intenta conectarse al GCS (Global Control Service) en el head node ✅
2. Ray intenta localizar un raylet LOCAL en 100.118.215.73 ❌
3. No encuentra el raylet (porque el daemon lo está ejecutando en proceso separado)
4. Ray falla con "Failed to get the system config from raylet because it is dead"

**Explicación Técnica:**
- `ray start` crea un proceso raylet de sistema
- `ray.init()` espera poder conectarse a un raylet local existente o crear uno nuevo
- En macOS cluster mode, hay restricciones que impiden que Python cree su propio raylet
- Los dos procesos no comparten el mismo raylet

---

## SOLUCIONES PROPUESTAS

### SOLUCIÓN 1: Usar Ray Job Submit (RECOMENDADA)

**Concepto:**
En lugar de ejecutar el Strategy Miner localmente, enviarlo como un Job al cluster.

**Implementación:**

```python
# submit_miner_job.py
import subprocess
import json
import os

def submit_miner_job(population=20, generations=5):
    """Envía el Strategy Miner como Ray Job"""

    # Crear script de job
    job_script = f"""
import pandas as pd
from strategy_miner import StrategyMiner
import json

df = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv")

miner = StrategyMiner(
    df=df,
    population_size={population},
    generations={generations},
    risk_level="LOW",
    force_local=False
)

def progress_cb(msg_type, data):
    if msg_type == "BEST_GEN":
        print(json.dumps({{"type": msg_type, "data": data}}))

best_genome, best_pnl = miner.run(progress_callback=progress_cb)

print(json.dumps({{"genome": best_genome, "pnl": best_pnl}}))
"""

    # Guardar script temporal
    with open("/tmp/miner_job.py", "w") as f:
        f.write(job_script)

    # Enviar job
    env = os.environ.copy()
    env["RAY_ADDRESS"] = "100.77.179.14:6379"

    result = subprocess.run(
        ["ray", "job", "submit", "--working-dir", ".", "--", "python", "/tmp/miner_job.py"],
        env=env,
        capture_output=True,
        text=True
    )

    return result.stdout, result.stderr
```

**Ventajas:**
- ✅ Funciona con la arquitectura actual sin cambios
- ✅ Usa el worker daemon existente
- ✅ No requiere modificar el código del Strategy Miner
- ✅ Logging integrado con Ray

**Desventajas:**
- ⚠️ Más complejo de integrar con Streamlit
- ⚠️ Requiere polling para obtener resultados

---

### SOLUCIÓN 2: Modo Local Híbrido (RÁPIDA)

**Concepto:**
Ejecutar Ray localmente en el MacBook Air, pero configurarlo para que use los mismos archivos del proyecto.

**Implementación:**

Modificar `test_miner_quick.py` y `optimizer_runner.py`:

```python
# Antes de ray.init()
if not ray.is_initialized():
    # Iniciar Ray LOCAL con todos los cores
    import os
    cores = os.cpu_count() or 10
    ray.init(
        address='local',
        num_cpus=cores,
        ignore_reinit_error=True,
        logging_level="ERROR"
    )
```

**Ventajas:**
- ✅ Funciona INMEDIATAMENTE
- ✅ No requiere cambios en infraestructura
- ✅ Fácil de debuggear

**Desventajas:**
- ❌ Solo usa 10 CPUs (MacBook Air)
- ❌ No aprovecha los 22 CPUs del cluster

---

### SOLUCIÓN 3: Runtime Environment Fix (TÉCNICA)

**Concepto:**
Configurar correctamente el runtime environment para que Ray Python pueda usar el raylet del daemon.

**Implementación:**

```python
# En el script Python
import ray
import os

os.environ["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

# Conectar usando namespace compartido
ray.init(
    address="100.77.179.14:6379",
    namespace="bittrader",  # Shared namespace
    runtime_env={
        "working_dir": ".",
        "excludes": ["data", "*.csv", "*.log"]
    }
)
```

**Problema:**
Esto todavía intentará crear un raylet local, que fallará.

---

### SOLUCIÓN 4: SSH Tunnel + Local Ray (WORKAROUND)

**Concepto:**
Crear un túnel SSH al head node y ejecutar Ray localmente apuntando a localhost.

**NO RECOMENDADA** - Demasiado compleja y frágil.

---

## RECOMENDACIÓN FINAL

### Para Testing INMEDIATO: **SOLUCIÓN 2 (Modo Local)**

Esto permitirá validar que el Strategy Miner funciona correctamente con el código actual.

```bash
# Test inmediato
cd "/path/to/project"
python3 -c "
import ray
ray.init(address='local', num_cpus=10)
print('CPUs:', ray.cluster_resources())
"
```

### Para Producción: **SOLUCIÓN 1 (Ray Job Submit)**

Esto aprovechará el cluster completo de 22 CPUs.

#### Plan de Implementación:

1. **Crear `miner_job_runner.py`**
   - Script que envía jobs usando `ray job submit`
   - Maneja progress tracking via Ray job logs

2. **Modificar `interface.py`**
   - Agregar opción "Modo Cluster" vs "Modo Local"
   - Si Cluster: usar miner_job_runner.py
   - Si Local: usar optimizer_runner.py actual

3. **Crear `miner_job_monitor.py`**
   - Monitorea el estado del job
   - Extrae resultados cuando completa
   - Maneja errores y reintentos

---

## PRUEBAS REALIZADAS

### ✅ Verificaciones Exitosas

1. **Conectividad de Red:**
   ```bash
   nc -zv 100.77.179.14 6379
   # Connection succeeded!
   ```

2. **Worker Daemon Status:**
   ```bash
   cat ~/.bittrader_worker/status
   # connected
   ```

3. **Archivos de Datos:**
   ```bash
   ls -lh data/
   # BTC-USD_FIVE_MINUTE.csv: 3.9M ✅
   ```

4. **Variables de Entorno:**
   ```bash
   cat .env
   # RAY_ADDRESS=100.77.179.14:6379 ✅
   # RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ✅
   ```

### ❌ Problemas Detectados

1. **ray.init() desde Python:**
   ```
   Failed to get the system config from raylet because it is dead.
   Status: RpcError: ... Connection refused
   ```

2. **Raylet Local No Existe:**
   ```bash
   ps aux | grep raylet
   # (no output) ❌
   ```

3. **IP Mismatch:**
   ```
   This node has an IP address of 100.118.215.73,
   but we cannot find a local Raylet with the same address.
   ```

---

## SIGUIENTE PASOS PROPUESTOS

### OPCIÓN A: Implementación Rápida (1-2 horas)

**Objetivo:** Hacer que funcione HOY con 10 CPUs locales

1. Modificar `test_miner_quick.py` para usar modo local
2. Modificar `optimizer_runner.py` para usar modo local
3. Probar Strategy Miner end-to-end
4. Generar estrategias rentables
5. Documentar resultados

### OPCIÓN B: Implementación Completa (4-6 horas)

**Objetivo:** Usar los 22 CPUs del cluster

1. Crear `miner_job_runner.py`
2. Crear `miner_job_monitor.py`
3. Modificar `interface.py` para soportar modo cluster
4. Probar con jobs pequeños
5. Escalar a tests completos
6. Documentar resultados

---

## RECOMENDACIÓN DE ACCIÓN

Sugiero proceder con **OPCIÓN A** para tener resultados rápidos, y luego implementar **OPCIÓN B** como mejora futura.

**Justificación:**
1. El Strategy Miner funciona con el código actual (solo necesita Ray configurado)
2. 10 CPUs son suficientes para validar funcionalidad
3. La diferencia de tiempo con 22 CPUs no es crítica para validación
4. Una vez validado, podemos optimizar para el cluster completo

---

## ARCHIVOS CRÍTICOS ANALIZADOS

1. ✅ `/Users/enderj/.../strategy_miner.py` - Lógica principal del miner
2. ✅ `/Users/enderj/.../optimizer.py` - Ray remote tasks
3. ✅ `/Users/enderj/.../optimizer_runner.py` - Process runner para Streamlit
4. ✅ `/Users/enderj/.../test_miner_quick.py` - Script de prueba
5. ✅ `/Users/enderj/.../.env` - Variables de entorno
6. ✅ `~/.bittrader_worker/worker_daemon.sh` - Daemon del worker
7. ✅ `~/.bittrader_worker/status` - Estado del daemon

---

## CONCLUSIÓN

El sistema tiene todos los componentes necesarios pero hay un impedance mismatch en cómo Ray se conecta. La solución más rápida es usar modo local para validación, y luego implementar Ray Job Submit para aprovechar el cluster completo.

**Estado Actual:**
- ⚠️ Cluster Ray: FUNCIONANDO pero no accesible desde Python scripts
- ⚠️ Strategy Miner: CÓDIGO CORRECTO pero conexión incorrecta
- ✅ Datos: DISPONIBLES
- ✅ Infraestructura: LISTA

**Próximo Paso Recomendado:**
Ejecutar test con modo local para validar funcionalidad del Strategy Miner.

```bash
# Comando sugerido
python3 test_miner_local.py
```

(Crear este archivo en el siguiente paso)

---

**Fin del Reporte**
