# 🛸 SETI@home y BOINC - Investigación para Estrategia Mining Distribuida

**Fecha:** 30 Enero 2026

---

## 📚 RESUMEN EJECUTIVO

SETI@home fue un proyecto pionero de **computación voluntaria distribuida** (1999-2020) que analizó datos de radiotelescopios buscando señales extraterrestres usando millones de computadoras personales.

**Framework:** BOINC (Berkeley Open Infrastructure for Network Computing)
**Código:** 100% Open Source (LGPL License)
**Plataformas:** Windows, macOS, Linux, Android
**Repositorio:** https://github.com/BOINC/boinc

**APLICABILIDAD A NUESTRO PROYECTO:** ⭐⭐⭐⭐⭐ ALTA

---

## 🎯 ¿QUÉ ERA SETI@HOME?

### Concepto

**Search for ExtraTerrestrial Intelligence @ Home**

- Proyecto de UC Berkeley (1999-2020)
- Análisis de datos del radiotelescopio de Arecibo
- Buscaba patrones de señales inteligentes en el ruido espacial
- Usaba **computadoras voluntarias** de usuarios en todo el mundo

### ¿Cómo Funcionaba?

```
┌─────────────────────────────────────────────────────────┐
│          RADIOTELESCOPIO ARECIBO (Puerto Rico)          │
│  Captura señales de radio del espacio (petabytes/día)  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ Datos guardados en discos duros
                  │ y enviados por correo postal (!)
                  │ (No había internet de alta velocidad)
                  ↓
┌─────────────────────────────────────────────────────────┐
│        SERVIDOR CENTRAL UC BERKELEY (California)        │
│                                                         │
│  1. Divide datos en "Work Units" (~350 KB cada uno)   │
│  2. Distribuye a computadoras voluntarias              │
│  3. Recibe resultados                                  │
│  4. Valida por redundancia (2-3 réplicas)             │
│  5. Agrega resultados en base de datos                │
└───────────┬──────────────┬──────────────┬──────────────┘
            │              │              │
            ↓              ↓              ↓
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ VOLUNTARIO 1│  │ VOLUNTARIO 2│  │ VOLUNTARIO N│
│   Windows   │  │    macOS    │  │    Linux    │
│             │  │             │  │             │
│ • Descarga  │  │ • Descarga  │  │ • Descarga  │
│   work unit │  │   work unit │  │   work unit │
│ • Analiza   │  │ • Analiza   │  │ • Analiza   │
│ • Envía     │  │ • Envía     │  │ • Envía     │
│   resultados│  │   resultados│  │   resultados│
└─────────────┘  └─────────────┘  └─────────────┘

    Millones de computadoras trabajando simultáneamente
```

### Logros

- **5.2 millones** de usuarios registrados (pico)
- **145,000** voluntarios activos al cierre (2020)
- Primera demostración exitosa de **computación voluntaria masiva**
- Inspiró proyectos similares: Folding@home (proteínas), Einstein@Home (ondas gravitacionales)

---

## 🏗️ ARQUITECTURA: BOINC

SETI@home evolucionó a **BOINC** - un framework genérico para cualquier proyecto de computación distribuida.

### Componentes Principales

```
SERVIDOR BOINC
├── Feeder Daemon          → Mantiene cache de ~1000 jobs listos
├── Scheduler (CGI)        → Asigna jobs a clientes
├── Validator Daemon       → Compara resultados redundantes
├── Assimilator Daemon     → Procesa resultados validados
├── Transitioner Daemon    → Mueve jobs entre estados
├── File Deleter          → Limpia archivos viejos
└── Database (MySQL)       → Almacena work units, resultados, users

CLIENTE BOINC
├── Client Core (C++)      → Motor de ejecución
├── Scheduler             → Decide qué job ejecutar
├── Checkpoint System     → Guarda estado periódicamente
├── GUI (WxWidgets)       → Interfaz multiplataforma
└── App Executables       → Aplicación científica específica
```

---

## 🔧 SOLUCIONES TÉCNICAS CLAVE

### 1. **MULTIPLATAFORMA REAL** ✅

BOINC funciona **nativamente** en:
- ✅ Windows (todas las versiones)
- ✅ macOS (Intel y Apple Silicon)
- ✅ Linux (todas las distros)
- ✅ Android
- ✅ FreeBSD

**Cómo lo logran:**

```cpp
// Core cliente en C++ multiplataforma
// UI en WxWidgets (compatible con todos los OS)

#ifdef _WIN32
    // Código específico Windows
#elif __APPLE__
    // Código específico macOS
#elif __linux__
    // Código específico Linux
#endif

// Servidor detecta plataforma del cliente
// y envía el ejecutable correcto
```

**Diferencia con Ray:**
- ❌ Ray: Multi-nodo NO soportado en macOS/Windows
- ✅ BOINC: Multi-nodo SÍ funciona en macOS/Windows

---

### 2. **DISTRIBUCIÓN DE TAREAS**

**Server-Side: Feeder + Scheduler**

```python
# PSEUDO-CÓDIGO del Scheduler

def handle_client_request(client):
    # 1. Recibir resultados completados
    received_results = client.upload_results()

    # 2. Verificar plataforma y hardware
    platform = client.get_platform()  # "windows_x86_64", "darwin_arm64", etc.

    # 3. Buscar trabajo compatible
    available_jobs = feeder.get_jobs_from_cache(
        platform=platform,
        max_jobs=10
    )

    # 4. Aplicar "locality scheduling"
    # (preferir jobs con archivos ya descargados)
    optimized_jobs = prioritize_cached_files(available_jobs, client)

    # 5. Asignar y enviar
    for job in optimized_jobs:
        client.send_work_unit(job)
        mark_as_sent(job, client)
```

**Client-Side: Round-Robin con Deadlines**

```python
# PSEUDO-CÓDIGO del Client Scheduler

def schedule_tasks():
    # 1. Calcular prioridad de cada proyecto
    for project in projects:
        # Más negativo = mayor prioridad
        priority = -REC(project) / resource_share(project)
        # REC = Recent Estimated Credit (trabajo hecho vs asignado)

    # 2. Weighted Round-Robin (1 hora por turno)
    # Proyecto con 60% share → 36 min cada hora
    # Proyecto con 40% share → 24 min cada hora

    # 3. Deadline-Aware Override
    # Si un task está cerca de deadline → ejecutar PRIMERO (EDF)
    critical_tasks = [t for t in tasks if t.deadline_approaching()]
    if critical_tasks:
        return sorted(critical_tasks, key=lambda t: t.deadline)[0]

    # 4. Ejecutar por prioridad
    return highest_priority_task()
```

---

### 3. **VALIDACIÓN POR REDUNDANCIA**

**El Problema:** ¿Cómo confiar en resultados de computadoras desconocidas?

**Solución BOINC:** Redundancia + Consenso

```
Work Unit: "Analizar frecuencia 1420 MHz"

Enviado a 3 voluntarios diferentes:
├── Voluntario A (Windows) → Resultado: "Señal encontrada en 1420.405 MHz"
├── Voluntario B (macOS)   → Resultado: "Señal encontrada en 1420.405 MHz"
└── Voluntario C (Linux)   → Resultado: "Sin señal"

Validator compara:
- A y B coinciden → VÁLIDO
- C difiere → INVÁLIDO (posible falla de hardware o malicioso)

Resultado Canónico: "Señal encontrada en 1420.405 MHz"
Crédito otorgado a: A y B
```

**Algoritmo de Validación:**

```python
def validate_work_unit(work_unit):
    results = get_all_results(work_unit)

    if len(results) < 2:
        return "WAITING"  # Esperar más réplicas

    # Comparación "fuzzy" (tolerancia a diferencias numéricas)
    matches = []
    for r1 in results:
        for r2 in results:
            if r1 == r2:
                continue
            if fuzzy_compare(r1, r2, tolerance=0.01):
                matches.append((r1, r2))

    # ¿Hay consenso?
    if len(matches) >= quorum_threshold:
        canonical_result = most_common(matches)

        # Asignar crédito
        for result in results:
            if fuzzy_compare(result, canonical_result):
                grant_credit(result.user)

        return canonical_result
    else:
        # No hay consenso → enviar más réplicas
        send_more_replicas(work_unit)
        return "NEED_MORE_DATA"
```

**Aplicado a Crypto Mining:**

```
Work Unit: "Backtest Estrategia X en BTC 2024-01-01 to 2024-12-31"

Enviado a 2 workers:
├── MacBook PRO → PnL: $1,254.32 | Sharpe: 1.85 | Trades: 42
└── PC Gamer    → PnL: $1,254.32 | Sharpe: 1.85 | Trades: 42

Validator: ✅ Resultados coinciden → Estrategia válida
```

---

### 4. **TOLERANCIA A FALLOS**

**Problema:** Computadoras se apagan, internet falla, procesos crashean.

**Solución BOINC:**

#### A. **Checkpoints (Puntos de Control)**

```cpp
// Aplicación científica guarda estado cada X minutos

void analyze_data(work_unit) {
    for (i = 0; i < total_samples; i++) {
        process_sample(i);

        // Checkpoint cada 10 minutos
        if (i % 10000 == 0) {
            save_checkpoint(i, current_state);
        }
    }
}

// Si el proceso se interrumpe:
void resume_work(work_unit) {
    checkpoint = load_last_checkpoint();
    i = checkpoint.last_processed_index;

    // Continuar desde donde quedó
    for (; i < total_samples; i++) {
        process_sample(i);
    }
}
```

**Aplicado a Crypto Mining:**

```python
# Backtest largo (30,000 velas × 5 min = 104 días)

def backtest_with_checkpoint(strategy, df):
    checkpoint = load_checkpoint_if_exists()

    if checkpoint:
        start_index = checkpoint['last_index']
        equity = checkpoint['equity']
        trades = checkpoint['trades']
    else:
        start_index = 0
        equity = 10000
        trades = []

    for i in range(start_index, len(df)):
        # Ejecutar estrategia
        signal = strategy.generate_signal(df.iloc[i])

        # Checkpoint cada 1000 velas (~3.5 días)
        if i % 1000 == 0:
            save_checkpoint({
                'last_index': i,
                'equity': equity,
                'trades': trades,
                'timestamp': time.time()
            })

        # Continuar backtest...
```

#### B. **Deadlines y Retry**

```
Work Unit asignado a Cliente A:
├── Deadline: 7 días
├── Cliente A offline por 5 días
│   → Servidor detecta "stalled"
│   → Asigna réplica a Cliente B
├── Cliente A regresa
│   → Completa trabajo (aún dentro de deadline)
├── Cliente B también completa
│   → Servidor ahora tiene 2 resultados
└── Validator compara y valida
```

---

### 5. **DESCUBRIMIENTO DE WORKERS**

**SETI@home/BOINC:** NO hay descubrimiento automático

**Modelo:**
1. Usuario **voluntariamente** descarga e instala cliente BOINC
2. Usuario **manualmente** se registra en proyecto (ej: SETI@home)
3. Cliente contacta servidor del proyecto
4. Servidor asigna trabajo

**No es peer-to-peer** - es modelo **cliente-servidor centralizado**

```
❌ Workers NO se descubren entre sí
❌ NO hay "broadcast" en red local
❌ NO hay DHT (Distributed Hash Table)

✅ Workers contactan servidor central
✅ Servidor coordina todo
✅ Simple y confiable
```

**Aplicado a nuestro proyecto:**

```bash
# Setup en cada máquina worker:

# 1. Instalar Python + dependencias
pip3 install pandas numpy requests

# 2. Descargar worker client script
wget https://mi-servidor.com/crypto_worker.py

# 3. Configurar servidor
python3 crypto_worker.py --server https://mi-servidor.com:8080

# 4. Worker loop:
while True:
    job = request_work_from_server()
    if job:
        result = execute_backtest(job)
        send_result_to_server(result)
    sleep(60)
```

---

## 🚀 COMPARACIÓN: BOINC vs RAY vs CUSTOM

| Aspecto | BOINC | Ray | Custom |
|---------|-------|-----|--------|
| **Multiplataforma** | ✅ Win/Mac/Linux | ⚠️ Linux OK, Mac/Win limitado | 🔧 Tú lo implementas |
| **Descubrimiento** | Manual (usuario instala) | Automático (cluster config) | 🔧 Tú lo implementas |
| **Validación** | Redundancia integrada | No incluido | 🔧 Tú lo implementas |
| **Checkpoints** | Integrado | Limitado | 🔧 Tú lo implementas |
| **Overhead** | Alto (framework completo) | Medio | Bajo (solo lo necesario) |
| **Setup Tiempo** | 2-3 horas | 1 hora | 4-6 horas |
| **Código Abierto** | ✅ LGPL | ✅ Apache 2.0 | ✅ Tuyo |
| **Python-friendly** | ⚠️ C++ nativo | ✅ 100% Python | ✅ Python |
| **Documentación** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A |
| **Mantenimiento** | Activo (UC Berkeley) | Muy activo (Anyscale) | Tú |
| **Escalabilidad** | Millones de nodos | Miles de nodos | Depende de ti |

---

## 💡 PROPUESTA: ARQUITECTURA HÍBRIDA PARA CRYPTO MINING

### Concepto: "BOINC-Like" en Python

Tomar **conceptos de BOINC**, implementar **simple en Python**, sin toda la complejidad.

```
┌─────────────────────────────────────────────────────────┐
│         SERVIDOR COORDINATOR (MacBook Pro)              │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Flask API Server (Puerto 8080)                  │  │
│  │                                                   │  │
│  │  Endpoints:                                       │  │
│  │    GET  /get_work         → Devuelve work unit  │  │
│  │    POST /submit_result    → Recibe resultado     │  │
│  │    GET  /status           → Estado del sistema   │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Work Queue (SQLite DB)                          │  │
│  │                                                   │  │
│  │  work_units:                                      │  │
│  │    - id, strategy_params, data_range, status     │  │
│  │                                                   │  │
│  │  results:                                         │  │
│  │    - id, work_unit_id, worker_id, pnl, metrics  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Validator                                        │  │
│  │    - Compara resultados redundantes              │  │
│  │    - Valida por consenso                         │  │
│  └──────────────────────────────────────────────────┘  │
└───────────┬──────────────┬──────────────┬──────────────┘
            │              │              │
            │   HTTP/REST  │              │
            │              │              │
            ↓              ↓              ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  WORKER 1       │  │  WORKER 2       │  │  WORKER N       │
│  MacBook Air    │  │  PC Gamer       │  │  Mac Amiga      │
│                 │  │                 │  │                 │
│  crypto_worker  │  │  crypto_worker  │  │  crypto_worker  │
│  .py            │  │  .py            │  │  .py            │
│                 │  │                 │  │                 │
│  Loop:          │  │  Loop:          │  │  Loop:          │
│  1. GET /work   │  │  1. GET /work   │  │  1. GET /work   │
│  2. Backtest    │  │  2. Backtest    │  │  2. Backtest    │
│  3. POST result │  │  3. POST result │  │  3. POST result │
│  4. Sleep 30s   │  │  4. Sleep 30s   │  │  4. Sleep 30s   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

### Implementación Simplificada

#### **Servidor (coordinator.py)**

```python
#!/usr/bin/env python3
from flask import Flask, request, jsonify
import sqlite3
import time
import json

app = Flask(__name__)

# Inicializar DB
def init_db():
    conn = sqlite3.connect('coordinator.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS work_units (
        id INTEGER PRIMARY KEY,
        strategy_params TEXT,
        status TEXT,
        created_at REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY,
        work_unit_id INTEGER,
        worker_id TEXT,
        pnl REAL,
        trades INTEGER,
        win_rate REAL,
        submitted_at REAL
    )''')
    conn.commit()
    conn.close()

@app.route('/get_work', methods=['GET'])
def get_work():
    worker_id = request.args.get('worker_id')

    conn = sqlite3.connect('coordinator.db')
    c = conn.cursor()

    # Buscar trabajo pendiente
    c.execute("SELECT * FROM work_units WHERE status='pending' LIMIT 1")
    work = c.fetchone()

    if work:
        work_id = work[0]
        c.execute("UPDATE work_units SET status='assigned' WHERE id=?", (work_id,))
        conn.commit()
        conn.close()

        return jsonify({
            'work_id': work_id,
            'strategy_params': json.loads(work[1])
        })
    else:
        conn.close()
        return jsonify({'work_id': None, 'message': 'No work available'})

@app.route('/submit_result', methods=['POST'])
def submit_result():
    data = request.json

    conn = sqlite3.connect('coordinator.db')
    c = conn.cursor()

    c.execute("""INSERT INTO results
        (work_unit_id, worker_id, pnl, trades, win_rate, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (data['work_id'], data['worker_id'], data['pnl'],
         data['trades'], data['win_rate'], time.time()))

    c.execute("UPDATE work_units SET status='completed' WHERE id=?",
              (data['work_id'],))

    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080)
```

#### **Worker (crypto_worker.py)**

```python
#!/usr/bin/env python3
import requests
import time
import socket
from strategy_miner import StrategyMiner
import pandas as pd

SERVER = "http://100.118.215.73:8080"  # IP del MacBook Pro
WORKER_ID = socket.gethostname()

# Cargar datos localmente
df = pd.read_csv("data/BTC-USD_FIVE_MINUTE.csv").tail(30000)

def get_work():
    try:
        r = requests.get(f"{SERVER}/get_work", params={'worker_id': WORKER_ID})
        return r.json()
    except:
        return None

def submit_result(work_id, pnl, trades, win_rate):
    try:
        requests.post(f"{SERVER}/submit_result", json={
            'work_id': work_id,
            'worker_id': WORKER_ID,
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate
        })
    except:
        pass

print(f"🤖 Worker {WORKER_ID} iniciado")
print(f"📡 Conectando a: {SERVER}")

while True:
    work = get_work()

    if work and work.get('work_id'):
        print(f"\n✅ Trabajo recibido: {work['work_id']}")

        # Ejecutar backtest
        params = work['strategy_params']
        miner = StrategyMiner(
            df=df,
            population_size=params['pop_size'],
            generations=params['generations'],
            risk_level=params['risk_level']
        )

        best_genome, best_pnl = miner.run()

        # Enviar resultado
        submit_result(work['work_id'], best_pnl, 10, 0.65)
        print(f"📤 Resultado enviado: PnL=${best_pnl:,.2f}")
    else:
        print("⏳ Sin trabajo disponible, esperando 30s...")
        time.sleep(30)
```

---

## 🎯 RECOMENDACIÓN FINAL

### Para tu proyecto de Crypto Strategy Mining:

**OPCIÓN 1: SIMPLE Y RÁPIDO** ⭐⭐⭐⭐⭐

**Implementar sistema "BOINC-like" simplificado en Python:**

✅ **Ventajas:**
- Funciona en macOS/Windows/Linux (solo Python + requests)
- No depende de Ray (evitas limitación macOS multi-nodo)
- Control total del código
- Fácil de extender
- Setup en 2-3 horas

❌ **Desventajas:**
- No tiene todas las features de BOINC (pero no las necesitas)
- Debes implementar validación/checkpoints tú mismo

**OPCIÓN 2: USAR BOINC COMPLETO** ⭐⭐⭐

**Fork BOINC y adaptar para tu proyecto:**

✅ **Ventajas:**
- Framework probado (20+ años)
- Validación/redundancia/checkpoints incluidos
- Escalable a millones de nodos
- Multiplataforma 100% funcional

❌ **Desventajas:**
- Curva de aprendizaje alta (C++, configuración compleja)
- Overhead grande (demasiadas features que no necesitas)
- Setup inicial: 1-2 semanas

**OPCIÓN 3: HÍBRIDO** ⭐⭐⭐⭐

**Usar conceptos de BOINC + Ray para ejecución local:**

- Coordinator en Python (inspirado en BOINC)
- Workers usan Ray en modo local (fuerza bruta en cada máquina)
- Comunicación vía REST API simple

---

## 📦 PRÓXIMOS PASOS

Si quieres implementar sistema distribuido estilo BOINC:

1. **Crear servidor coordinator** (Flask API + SQLite)
2. **Crear worker script** (requests + StrategyMiner)
3. **Probar con 2 máquinas** (MacBook Pro + Air)
4. **Agregar validación** (redundancia 2x)
5. **Agregar checkpoints** (guardar estado cada N velas)
6. **Escalar** (PC Gamer, Mac amiga, más...)

**Tiempo estimado:** 1 día de desarrollo + testing

---

## 📚 RECURSOS

### BOINC

- **Repositorio:** https://github.com/BOINC/boinc
- **Documentación:** https://boinc.berkeley.edu/
- **Wiki:** https://github.com/BOINC/boinc/wiki
- **Source Code Map:** https://github.com/BOINC/boinc/wiki/Source-code-map

### Papers

- **SETI@home - An Experiment in Public-Resource Computing**
  https://setiathome.berkeley.edu/sah_papers/cacm.php

- **High-Performance Task Distribution for Volunteer Computing**
  https://boinc.berkeley.edu/boinc_papers/server_perf/server_perf.pdf

### Alternativas

- **Ray:** https://www.ray.io/
- **Dask:** https://www.dask.org/
- **Folding@home:** https://foldingathome.org/

---

## ❓ PREGUNTAS PARA DECIDIR SIGUIENTE PASO

1. **¿Quieres implementar sistema distribuido AHORA?**
   - Sí → Creo coordinator.py + crypto_worker.py
   - No → Seguimos con búsquedas paralelas simples

2. **¿Cuántas máquinas vas a usar eventualmente?**
   - 2-3 → Sistema simple es suficiente
   - 5+ → Vale la pena sistema más robusto

3. **¿Prefieres simplicidad o features avanzadas?**
   - Simplicidad → Sistema custom en Python
   - Features → Fork BOINC completo

4. **¿Qué tan importante es la validación por redundancia?**
   - Crítico → Implementar validación estilo BOINC
   - No crítico → Confiar en workers

---

**🤖 En resumen:** SETI@home/BOINC es **100% aplicable** a tu proyecto. El concepto de computación voluntaria distribuida funciona perfecto para minería de estrategias. Podemos implementar una versión simplificada en Python que soluciona el problema de Ray en macOS.

¿Quieres que implemente el sistema distribuido estilo BOINC?
