# 🌐 SISTEMA DISTRIBUIDO - Guía Completa

**Sistema:** Strategy Miner Distribuido (inspirado en BOINC)
**Fecha:** 30 Enero 2026
**Estado:** Implementado y listo para testing ✅

---

## 📋 ÍNDICE

1. [Arquitectura del Sistema](#arquitectura-del-sistema)
2. [Instalación del Coordinator](#instalación-del-coordinator)
3. [Instalación de Workers](#instalación-de-workers)
4. [Uso del Sistema](#uso-del-sistema)
5. [Dashboard Web](#dashboard-web)
6. [Troubleshooting](#troubleshooting)
7. [Escalado](#escalado)

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Concepto General

```
┌─────────────────────────────────────────────────────────────┐
│         COORDINATOR (MacBook Pro)                           │
│                                                             │
│  Flask API Server (Puerto 5000)                            │
│  SQLite Database                                           │
│  Dashboard Web                                             │
│  Validación por Redundancia                                │
└────────────┬──────────────┬──────────────┬─────────────────┘
             │              │              │
             │   HTTP/REST  │              │
             │              │              │
             ↓              ↓              ↓
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  WORKER 1        │  │  WORKER 2        │  │  WORKER N        │
│  MacBook Air     │  │  PC Gamer        │  │  Mac Amiga       │
│                  │  │                  │  │                  │
│  crypto_worker   │  │  crypto_worker   │  │  crypto_worker   │
│  .py             │  │  .py             │  │  .py             │
│                  │  │                  │  │                  │
│  Loop:           │  │  Loop:           │  │  Loop:           │
│  1. GET /work    │  │  1. GET /work    │  │  1. GET /work    │
│  2. Backtest     │  │  2. Backtest     │  │  2. Backtest     │
│  3. POST result  │  │  3. POST result  │  │  3. POST result  │
│  4. Sleep 30s    │  │  4. Sleep 30s    │  │  4. Sleep 30s    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Componentes

#### 1. **Coordinator (`coordinator.py`)**

Servidor central que:
- ✅ Mantiene cola de work units (trabajos pendientes)
- ✅ Distribuye trabajo a workers disponibles
- ✅ Recibe y almacena resultados
- ✅ Valida resultados por redundancia (2+ réplicas)
- ✅ Identifica resultado canónico (ground truth)
- ✅ Sirve dashboard web en tiempo real

#### 2. **Workers (`crypto_worker.py`)**

Clientes que:
- ✅ Se registran con el coordinator
- ✅ Solicitan trabajo periódicamente (polling cada 30s)
- ✅ Ejecutan backtests localmente
- ✅ Envían resultados al coordinator
- ✅ Funcionan en macOS, Windows y Linux
- ✅ Implementan checkpoints para recuperación

#### 3. **Base de Datos (SQLite)**

Almacena:
- `work_units` - Trabajos pendientes/completados
- `results` - Resultados de backtests
- `workers` - Workers registrados y estadísticas
- `stats` - Estadísticas globales

---

## 🚀 INSTALACIÓN DEL COORDINATOR

### Paso 1: Preparar MacBook Pro

El coordinator se ejecuta en tu MacBook Pro (o la máquina que elijas como servidor central).

```bash
# 1. Navegar al proyecto
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# 2. Instalar dependencia (Flask)
pip3 install flask

# 3. Verificar que coordinator.py existe
ls -lh coordinator.py
```

### Paso 2: Configurar Work Units

El coordinator viene con 3 work units de prueba pre-configurados. Para crear tus propios work units:

**Opción A:** Editar `coordinator.py` función `create_test_work_units()`

```python
def create_test_work_units():
    test_configs = [
        {
            'population_size': 40,
            'generations': 30,
            'risk_level': 'MEDIUM',
            'description': 'Búsqueda MacBook Pro'
        },
        {
            'population_size': 50,
            'generations': 25,
            'risk_level': 'LOW',
            'description': 'Búsqueda MacBook Air'
        },
        # Agregar más configuraciones aquí
    ]

    ids = create_work_units(test_configs)
    print(f"✅ {len(ids)} work units creados")
```

**Opción B:** Usar el API después de iniciar (avanzado)

```bash
curl -X POST http://localhost:5000/api/create_work \
  -H "Content-Type: application/json" \
  -d '{"population_size": 40, "generations": 30, "risk_level": "MEDIUM"}'
```

### Paso 3: Iniciar Coordinator

```bash
python3 coordinator.py
```

**Salida esperada:**

```
================================================================================
🧬 COORDINATOR - Sistema Distribuido de Strategy Mining
================================================================================

🔧 Inicializando base de datos...
✅ Base de datos inicializada

🧪 Creando work units de prueba...
✅ 3 work units de prueba creados: [1, 2, 3]

================================================================================
🚀 COORDINATOR INICIADO
================================================================================

📡 Dashboard: http://localhost:5000
📡 API Status: http://localhost:5000/api/status
📡 API Get Work: http://localhost:5000/api/get_work?worker_id=XXX
📡 API Submit: POST http://localhost:5000/api/submit_result

Presiona Ctrl+C para detener

 * Running on http://0.0.0.0:5000
```

### Paso 4: Verificar Dashboard

Abre tu navegador en: **http://localhost:5000**

Deberías ver el dashboard verde estilo terminal con:
- Total Work Units
- Workers activos
- Mejor PnL encontrado

---

## 💻 INSTALACIÓN DE WORKERS

### Workers en macOS (MacBook Air, Mac Amiga)

#### Paso 1: Copiar Archivos

```bash
# Desde MacBook Pro (coordinator), copiar a MacBook Air:
scp crypto_worker.py enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"

scp strategy_miner.py enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"

scp backtester.py enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"

scp dynamic_strategy.py enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"

scp -r data/ enderj@100.77.179.14:"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/"
```

#### Paso 2: Configurar URL del Coordinator

```bash
# En MacBook Air (conectarse vía SSH)
ssh enderj@100.77.179.14

# Navegar al proyecto
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Configurar variable de entorno con IP del coordinator
export COORDINATOR_URL="http://100.118.215.73:5000"

# O pasar como argumento al ejecutar (más fácil)
# python3 crypto_worker.py http://100.118.215.73:5000
```

#### Paso 3: Instalar Dependencias

```bash
pip3 install pandas numpy requests
```

#### Paso 4: Ejecutar Worker

```bash
# Opción A: Con variable de entorno
export COORDINATOR_URL="http://100.118.215.73:5000"
python3 crypto_worker.py

# Opción B: Con argumento
python3 crypto_worker.py http://100.118.215.73:5000

# Opción C: En background con nohup
nohup python3 crypto_worker.py http://100.118.215.73:5000 > worker.log 2>&1 &
```

### Workers en Windows (PC Gamer)

#### Paso 1: Preparar Archivos

**Opción A:** Comprimir y transferir

```bash
# Desde MacBook Pro
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

# Crear paquete para Windows
tar -czf crypto_worker_package.tar.gz \
  crypto_worker.py \
  strategy_miner.py \
  backtester.py \
  dynamic_strategy.py \
  data/

# Transferir por Google Drive, WeTransfer, o USB
```

**Opción B:** Clonar repositorio Git (si tienes uno)

#### Paso 2: Instalar Python en Windows

1. Descargar Python 3.9+ desde https://python.org
2. Durante instalación, marcar "Add Python to PATH"
3. Verificar: `python --version`

#### Paso 3: Instalar Dependencias

```powershell
# En PowerShell o CMD
pip install pandas numpy requests
```

#### Paso 4: Configurar y Ejecutar

```powershell
# En PowerShell
cd C:\BittraderMiner

# Ejecutar worker (ajustar IP del coordinator)
python crypto_worker.py http://192.168.1.10:5000
```

**Nota:** En Windows usa `python` (no `python3`)

### Workers en Linux

```bash
# Similar a macOS
pip3 install pandas numpy requests

python3 crypto_worker.py http://COORDINATOR_IP:5000
```

---

## 🎯 USO DEL SISTEMA

### Flujo Básico

#### 1. Iniciar Coordinator

```bash
# En MacBook Pro
cd "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"

python3 coordinator.py
```

#### 2. Iniciar Workers

```bash
# En MacBook Air (vía SSH)
ssh enderj@100.77.179.14
cd "..."
python3 crypto_worker.py http://100.118.215.73:5000

# En PC Gamer (Windows)
python crypto_worker.py http://192.168.1.10:5000

# En MacBook Pro (local worker adicional)
python3 crypto_worker.py http://localhost:5000
```

#### 3. Monitorear Progreso

**Opción A:** Dashboard Web

Abrir en navegador: `http://localhost:5000`

**Opción B:** API Status

```bash
curl http://localhost:5000/api/status | python3 -m json.tool
```

**Opción C:** Consultar Base de Datos

```bash
sqlite3 coordinator.db "SELECT * FROM workers"
sqlite3 coordinator.db "SELECT * FROM work_units"
sqlite3 coordinator.db "SELECT * FROM results WHERE is_canonical=1"
```

#### 4. Ver Resultados

```bash
# Mejores estrategias
curl http://localhost:5000/api/results | python3 -m json.tool
```

### Agregar Más Work Units

#### Mientras el coordinator está ejecutando:

**Método 1:** Parar coordinator, editar `create_test_work_units()`, reiniciar

**Método 2:** Insertar directamente en DB

```bash
sqlite3 coordinator.db
```

```sql
INSERT INTO work_units (strategy_params, replicas_needed)
VALUES ('{"population_size": 60, "generations": 40, "risk_level": "HIGH"}', 2);
```

**Método 3:** Crear endpoint de API (avanzado)

Agregar a `coordinator.py`:

```python
@app.route('/api/create_work', methods=['POST'])
def api_create_work():
    data = request.json
    ids = create_work_units([data])
    return jsonify({'work_ids': ids})
```

---

## 📊 DASHBOARD WEB

El dashboard se actualiza automáticamente cada 10 segundos y muestra:

### Sección de Estadísticas

- **Total Work Units:** Número total de trabajos creados
- **Completed:** Trabajos completados y validados
- **Active Workers:** Número de workers actualmente activos
- **Best PnL:** Mejor PnL encontrado hasta ahora

### Tabla de Resultados

Muestra top 10 estrategias validadas:
- Work ID
- PnL
- Número de trades
- Win Rate
- Sharpe Ratio
- Worker que lo encontró

### Estilo Visual

- Terminal verde estilo Matrix
- Actualización automática
- No requiere JavaScript avanzado
- Funciona en cualquier navegador

---

## 🔧 TROUBLESHOOTING

### Problema: Worker no puede conectar al Coordinator

**Síntomas:**
```
❌ No se puede conectar al coordinator: Connection refused
```

**Soluciones:**

1. **Verificar que el coordinator está ejecutando:**
   ```bash
   # En MacBook Pro
   ps aux | grep coordinator.py
   ```

2. **Verificar IP del coordinator:**
   ```bash
   # En MacBook Pro
   ifconfig | grep "inet "

   # O si usas Tailscale
   tailscale ip
   ```

3. **Verificar puerto 5000 abierto:**
   ```bash
   # En MacBook Pro
   lsof -i :5000
   ```

4. **Probar conectividad:**
   ```bash
   # Desde worker
   curl http://COORDINATOR_IP:5000/api/status
   ```

5. **Firewall:**
   - macOS: System Preferences → Security → Firewall → permitir Python
   - Windows: Firewall → permitir puerto 5000

### Problema: Worker ejecuta pero no recibe trabajo

**Síntomas:**
```
⏳ Sin trabajo disponible - Esperando 30s...
```

**Soluciones:**

1. **Verificar work units en coordinator:**
   ```bash
   sqlite3 coordinator.db "SELECT * FROM work_units WHERE status='pending'"
   ```

2. **Crear work units:**
   - Ver sección "Agregar Más Work Units"

3. **Verificar logs del coordinator:**
   - Debería mostrar: `📤 Trabajo X asignado a worker Y`

### Problema: Resultados no se validan

**Síntomas:**
Dashboard muestra work units completados pero ninguno validado

**Causas:**

1. **Redundancia insuficiente:**
   - Cada work unit necesita 2 réplicas (por defecto)
   - Si solo 1 worker completó, falta 1 réplica más

2. **Resultados muy diferentes:**
   - Si 2 workers obtienen resultados distintos (>10% diferencia)
   - Sistema solicita réplica adicional

**Solución:**

Ejecutar más workers o reducir `REDUNDANCY_FACTOR` en `coordinator.py`:

```python
REDUNDANCY_FACTOR = 1  # Solo 1 réplica (no recomendado para producción)
```

### Problema: Worker crashea durante backtest

**Síntomas:**
```
❌ Error inesperado: ...
⏳ Reintentando en 30s...
```

**Soluciones:**

1. **Verificar datos:**
   ```bash
   ls -lh data/BTC-USD_FIVE_MINUTE.csv
   ```

2. **Verificar dependencias:**
   ```bash
   python3 -c "import pandas, numpy; print('OK')"
   ```

3. **Ver logs detallados:**
   - Worker imprime stack trace completo
   - Revisar error específico

4. **Checkpoint recovery:**
   - Worker guarda checkpoint cada 5 generaciones
   - Si crashea, puede recuperar progreso (implementación básica)

---

## 🚀 ESCALADO

### Agregar Más Workers

Para escalar el sistema, simplemente:

1. **Preparar nueva máquina**
   - Instalar Python 3.9+
   - Copiar archivos del proyecto
   - Copiar datos BTC

2. **Ejecutar worker**
   ```bash
   python3 crypto_worker.py http://COORDINATOR_IP:5000
   ```

¡Eso es todo! El coordinator automáticamente:
- Detecta nuevo worker
- Asigna trabajo
- Agrega resultados

### Capacidad Teórica

Con la configuración actual:

| Workers | Work Units/hora | Estrategias/hora |
|---------|----------------|------------------|
| 2 | 4-6 | 2,500 |
| 4 | 8-12 | 5,000 |
| 10 | 20-30 | 12,500 |
| 20 | 40-60 | 25,000 |

**Asumiendo:**
- Cada work unit: 40 población × 25 generaciones = 1,000 estrategias
- Tiempo por work unit: ~30-40 minutos

### Optimizaciones Avanzadas

#### 1. **Balanceo de Carga**

Modificar `get_pending_work()` para considerar capacidad del worker:

```python
# Asignar work units grandes a workers potentes
if worker_specs['cpu_cores'] >= 8:
    # Work units de 60 población × 40 generaciones
else:
    # Work units de 30 población × 20 generaciones
```

#### 2. **Priorización de Work Units**

```sql
-- Ordenar por prioridad en vez de FIFO
SELECT * FROM work_units
WHERE replicas_completed < replicas_needed
ORDER BY priority DESC, created_at ASC
LIMIT 1
```

#### 3. **Checkpoint Distribuido**

Guardar checkpoints en servidor compartido (Google Drive, Dropbox):

```python
CHECKPOINT_DIR = "/path/to/google/drive/checkpoints/"
```

---

## 📊 COMPARACIÓN: Sistema Distribuido vs Búsquedas Paralelas

| Aspecto | Búsquedas Paralelas | Sistema Distribuido |
|---------|-------------------|-------------------|
| **Setup Inicial** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐⭐ Moderado |
| **Escalabilidad** | ⭐⭐ Manual (2-3 máquinas) | ⭐⭐⭐⭐⭐ Automática (10+ máquinas) |
| **Validación** | ❌ Manual | ✅ Automática (redundancia) |
| **Monitoreo** | ⭐⭐⭐ STATUS files | ⭐⭐⭐⭐⭐ Dashboard web |
| **Checkpoint** | ❌ No | ✅ Sí |
| **Recuperación** | ❌ Reiniciar desde cero | ✅ Resume desde checkpoint |
| **Coordinación** | Manual (SSH, copiar archivos) | Automática (API) |
| **Multiplataforma** | ✅ macOS, Linux | ✅ macOS, Windows, Linux |

---

## 🎉 RESUMEN

**Has implementado un sistema distribuido estilo BOINC que:**

✅ Funciona en macOS, Windows y Linux
✅ Escala a 10+ máquinas fácilmente
✅ Valida resultados por redundancia
✅ Dashboard web en tiempo real
✅ API REST simple
✅ Checkpoints para recuperación
✅ Sin dependencia de Ray (evita problemas de macOS)

**Próximos pasos:**

1. ✅ Iniciar coordinator
2. ✅ Conectar 2-3 workers
3. ✅ Ejecutar búsqueda distribuida de prueba
4. ✅ Validar resultados
5. ✅ Escalar a más máquinas

---

**🤖 Sistema implementado - 30 Enero 2026**

Para preguntas o problemas, consulta la sección Troubleshooting o revisa los logs del coordinator/workers.
