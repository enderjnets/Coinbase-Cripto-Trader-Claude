#!/usr/bin/env python3
"""
COORDINATOR - Sistema Distribuido de Strategy Mining
Inspirado en arquitectura BOINC

Este servidor coordina múltiples workers que ejecutan backtests en paralelo.
Funciona en macOS, Windows y Linux (a diferencia de Ray).

Características:
- Distribución de trabajo (work units)
- Validación por redundancia
- Monitoreo en tiempo real
- API REST simple

Autor: Strategy Miner Team
Fecha: 30 Enero 2026
"""

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import time
import json
import os
import random
import threading
from datetime import datetime
from threading import Lock

app = Flask(__name__)

# Lock para acceso thread-safe a la base de datos
db_lock = Lock()

# Configuración
DATABASE = 'coordinator.db'
REDUNDANCY_FACTOR = 2  # Cada work unit se envía a 2 workers
BACKTEST_CAPITAL = 500.0  # Capital inicial del backtester (numba_backtester.py)

# ============================================================================
# AUTO-CREACIÓN DE WORK UNITS
# ============================================================================
AUTO_CREATE_ENABLED = True
AUTO_CREATE_MIN_PENDING = 50      # Crear más WUs cuando queden < 50 pendientes
AUTO_CREATE_BATCH_SIZE = 100      # Crear 100 WUs cada vez
AUTO_CREATE_CHECK_INTERVAL = 30   # Verificar cada 30 segundos

# ============================================================================
# SISTEMA DE ÉLITE GLOBAL (Evolución Continua)
# ============================================================================
ELITE_MAX_SIZE = 100              # Máximo 100 genomas élite
ELITE_MIN_PNL = 100               # PnL mínimo para entrar a élite ($100)
ELITE_SEED_RATIO = 0.5            # 50% de población inicial desde élite

# Datos disponibles para backtests
SPOT_DATA_FILES = [
    {"file": "BTC-USD_ONE_MINUTE.csv", "asset": "BTC", "dir": "data"},
    {"file": "BTC-USD_FIVE_MINUTE.csv", "asset": "BTC", "dir": "data"},
    {"file": "BTC-USD_FIFTEEN_MINUTE.csv", "asset": "BTC", "dir": "data"},
]

FUTURES_DATA_FILES = [
    {"file": "BIP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "BTC", "contract": "BIP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "BIT-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "BTC", "contract": "BIT-27FEB26-CDE", "dir": "data_futures"},
    {"file": "ETP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "ETH", "contract": "ETP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "ET-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "ETH", "contract": "ET-27FEB26-CDE", "dir": "data_futures"},
    {"file": "SLP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "SOL", "contract": "SLP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "SOL-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "SOL", "contract": "SOL-27FEB26-CDE", "dir": "data_futures"},
    {"file": "XPP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "XRP", "contract": "XPP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "XRP-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "XRP", "contract": "XRP-27FEB26-CDE", "dir": "data_futures"},
    {"file": "ADP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "ADA", "contract": "ADP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "DOP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "DOT", "contract": "DOP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "LNP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "LINK", "contract": "LNP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "AVP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "AVAX", "contract": "AVP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "DOG-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "DOGE", "contract": "DOG-27FEB26-CDE", "dir": "data_futures"},
    {"file": "SUI-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "SUI", "contract": "SUI-27FEB26-CDE", "dir": "data_futures"},
    {"file": "XLP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "XLM", "contract": "XLP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "HEP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "HED", "contract": "HEP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "SHB-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "SHIB", "contract": "SHB-27FEB26-CDE", "dir": "data_futures"},
    {"file": "LCP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "LTC", "contract": "LCP-20DEC30-CDE", "dir": "data_futures"},
    {"file": "GOL-27MAR26-CDE_FIVE_MINUTE.csv", "asset": "GOLD", "contract": "GOL-27MAR26-CDE", "dir": "data_futures"},
    {"file": "NOL-19MAR26-CDE_FIVE_MINUTE.csv", "asset": "OIL", "contract": "NOL-19MAR26-CDE", "dir": "data_futures"},
    {"file": "MC-19MAR26-CDE_FIVE_MINUTE.csv", "asset": "SP500", "contract": "MC-19MAR26-CDE", "dir": "data_futures"},
]

GENETIC_CONFIGS = [
    {"population_size": 100, "generations": 150, "name": "enhanced"},      # NUEVO: más exploración
    {"population_size": 150, "generations": 200, "name": "intensive"},     # NUEVO: búsqueda profunda
    {"population_size": 200, "generations": 300, "name": "exhaustive"},    # NUEVO: máximo
    {"population_size": 50, "generations": 100, "name": "standard"},       # Legacy: balanceado
    {"population_size": 30, "generations": 80, "name": "fast"},            # Legacy: rápido
]

RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
CANDLE_CONFIGS = [5000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 75000, 100000]  # Más opciones = mejor exploración


def generate_random_work_unit():
    """Genera un work unit con configuración aleatoria diversa, usando élite como semilla"""
    # Elegir tipo de datos (spot o futures)
    use_futures = random.random() > 0.3  # 70% probabilidad de futuros

    if use_futures and FUTURES_DATA_FILES:
        data_info = random.choice(FUTURES_DATA_FILES)
        data_dir = data_info["dir"]
        data_file = data_info["file"]
        asset = data_info["asset"]
        contract = data_info.get("contract", "")
        category = "Futures"
        max_candles = random.choice([3000, 5000, 7500, 10000])
    else:
        data_info = random.choice(SPOT_DATA_FILES)
        data_dir = data_info["dir"]
        data_file = data_info["file"]
        asset = data_info["asset"]
        contract = ""
        category = "Spot"
        max_candles = random.choice(CANDLE_CONFIGS)

    config = random.choice(GENETIC_CONFIGS)
    risk = random.choice(RISK_LEVELS)

    strategy_params = {
        "name": f"{asset}_{category[:3]}_{config['name']}_{risk}_{max_candles//1000}K_{int(time.time())}",
        "category": category,
        "population_size": config["population_size"],
        "generations": config["generations"],
        "risk_level": risk,
        "data_file": data_file,
        "max_candles": max_candles,
        "data_dir": f"/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/{data_dir}",
    }

    # Obtener genomas élite para usar como semilla (evolución continua)
    elite = get_elite_genomes(limit=10, data_file=data_file)
    if elite:
        # Incluir hasta 5 genomas élite como semilla
        seed_genomes = []
        for e in elite[:5]:
            try:
                genome = json.loads(e['genome_json'])
                seed_genomes.append(genome)
            except:
                pass
        if seed_genomes:
            strategy_params["seed_genomes"] = seed_genomes
            strategy_params["seed_ratio"] = ELITE_SEED_RATIO  # 50% de población desde élite

    if contract:
        strategy_params["contracts"] = [contract]
        strategy_params["leverage"] = 2 if risk == "LOW" else (3 if risk == "MEDIUM" else 5)

    return {
        "strategy_params": strategy_params,
        "replicas": REDUNDANCY_FACTOR * 3  # 6 réplicas
    }


def auto_create_work_units():
    """Thread en background que crea WUs automáticamente cuando hay pocos pendientes"""
    print("🔄 Auto-creación de WUs iniciada (verificando cada {}s)".format(AUTO_CREATE_CHECK_INTERVAL))

    while True:
        try:
            time.sleep(AUTO_CREATE_CHECK_INTERVAL)

            if not AUTO_CREATE_ENABLED:
                continue

            # PASO 1: Verificar pendientes SIN lock (solo lectura)
            conn_check = get_db_connection()
            c_check = conn_check.cursor()
            c_check.execute("SELECT COUNT(*) as pending FROM work_units WHERE status = 'pending'")
            pending = c_check.fetchone()['pending']
            conn_check.close()

            if pending < AUTO_CREATE_MIN_PENDING:
                # PASO 2: Generar WUs fuera del lock (para evitar deadlock con get_elite_genomes)
                print(f"\n🔄 Auto-creando {AUTO_CREATE_BATCH_SIZE} WUs (pendientes: {pending})")
                work_units_to_create = []
                for _ in range(AUTO_CREATE_BATCH_SIZE):
                    wu = generate_random_work_unit()
                    work_units_to_create.append(wu)

                # PASO 3: Insertar con lock (operación rápida)
                with db_lock:
                    conn = get_db_connection()
                    c = conn.cursor()
                    created = 0
                    for wu in work_units_to_create:
                        c.execute("""INSERT INTO work_units
                            (strategy_params, replicas_needed, replicas_assigned, status)
                            VALUES (?, ?, 0, 'pending')""",
                            (json.dumps(wu["strategy_params"]), wu.get("replicas", REDUNDANCY_FACTOR)))
                        created += 1
                    conn.commit()
                    conn.close()

                print(f"   ✅ {created} WUs creados automáticamente")
                # Log al archivo de coordinator
                with open('/tmp/coordinator_auto_create.log', 'a') as f:
                    f.write(f"{datetime.now().isoformat()}: Creados {created} WUs (pendientes eran {pending})\n")

        except Exception as e:
            print(f"⚠️ Error en auto-creación: {e}")
            time.sleep(60)  # Esperar más tiempo si hay error

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db_connection():
    """Crea conexión a la base de datos"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    c = conn.cursor()

    # Tabla de work units (timestamps en Unix epoch)
    c.execute('''CREATE TABLE IF NOT EXISTS work_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_params TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        replicas_needed INTEGER DEFAULT 2,
        replicas_completed INTEGER DEFAULT 0,
        canonical_result_id INTEGER DEFAULT NULL
    )''')

    # Tabla de resultados (timestamps en Unix epoch)
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_unit_id INTEGER NOT NULL,
        worker_id TEXT NOT NULL,
        pnl REAL,
        trades INTEGER,
        win_rate REAL,
        sharpe_ratio REAL,
        max_drawdown REAL,
        execution_time REAL,
        submitted_at INTEGER DEFAULT (strftime('%s', 'now')),
        validated BOOLEAN DEFAULT 0,
        is_canonical BOOLEAN DEFAULT 0,
        FOREIGN KEY (work_unit_id) REFERENCES work_units (id)
    )''')

    # Tabla de workers (timestamps en Unix epoch)
    c.execute('''CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY,
        hostname TEXT,
        platform TEXT,
        last_seen INTEGER DEFAULT (strftime('%s', 'now')),
        work_units_completed INTEGER DEFAULT 0,
        total_execution_time REAL DEFAULT 0,
        status TEXT DEFAULT 'active'
    )''')

    # Tabla de estadísticas globales
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Tabla de genomas élite (timestamps en Unix epoch)
    c.execute('''CREATE TABLE IF NOT EXISTS elite_genomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        genome_json TEXT NOT NULL,
        pnl REAL,
        win_rate REAL,
        sharpe_ratio REAL,
        trades INTEGER,
        data_file TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        generation INTEGER DEFAULT 0
    )''')

    conn.commit()
    conn.close()

    print("✅ Base de datos inicializada")

# ============================================================================
# ÉLITE GLOBAL MANAGEMENT
# ============================================================================

def add_to_elite(genome_json, pnl, win_rate, sharpe_ratio, trades, data_file):
    """
    Agrega un genoma a la élite si cumple los requisitos

    Returns:
        True si se agregó, False si no cumplió requisitos
    """
    try:
        # Verificar PnL mínimo
        if pnl < ELITE_MIN_PNL:
            return False

        with db_lock:
            conn = get_db_connection()
            c = conn.cursor()

            # Verificar tamaño actual de élite
            c.execute("SELECT COUNT(*) as cnt FROM elite_genomes")
            current_count = c.fetchone()['cnt']

            # Si la élite está llena, verificar si es mejor que el peor
            if current_count >= ELITE_MAX_SIZE:
                c.execute("SELECT MIN(pnl) as min_pnl, id FROM elite_genomes")
                worst = c.fetchone()
                if pnl <= worst['min_pnl']:
                    conn.close()
                    return False
                # Eliminar el peor
                c.execute("DELETE FROM elite_genomes WHERE id = ?", (worst['id'],))

            # Agregar nuevo genoma élite
            c.execute("""INSERT INTO elite_genomes
                (genome_json, pnl, win_rate, sharpe_ratio, trades, data_file)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (genome_json, pnl, win_rate, sharpe_ratio, trades, data_file))

            conn.commit()
            conn.close()

            print(f"🏆 Nuevo genoma élite agregado: PnL=${pnl:.2f}, WinRate={win_rate*100:.1f}%")
            return True

    except Exception as e:
        print(f"⚠️ Error agregando a élite: {e}")
        return False


def get_elite_genomes(limit=50, data_file=None):
    """
    Obtiene los mejores genomas de la élite

    Args:
        limit: Máximo número de genomas a retornar
        data_file: Filtrar por archivo de datos (opcional)

    Returns:
        Lista de genomas élite
    """
    try:
        with db_lock:
            conn = get_db_connection()
            c = conn.cursor()

            if data_file:
                c.execute("""SELECT genome_json, pnl, win_rate, sharpe_ratio, trades
                    FROM elite_genomes
                    WHERE data_file = ?
                    ORDER BY pnl DESC
                    LIMIT ?""", (data_file, limit))
            else:
                c.execute("""SELECT genome_json, pnl, win_rate, sharpe_ratio, trades
                    FROM elite_genomes
                    ORDER BY pnl DESC
                    LIMIT ?""", (limit,))

            rows = c.fetchall()
            conn.close()

            return [dict(row) for row in rows]

    except Exception as e:
        print(f"⚠️ Error obteniendo élite: {e}")
        return []


def get_elite_count():
    """Retorna el número de genomas en la élite"""
    try:
        with db_lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM elite_genomes")
            count = c.fetchone()['cnt']
            conn.close()
            return count
    except:
        return 0

# ============================================================================
# WORK UNIT MANAGEMENT
# ============================================================================

def create_work_units(strategy_configs):
    """
    Crea work units a partir de configuraciones de estrategia

    Args:
        strategy_configs: Lista de diccionarios con parámetros de estrategia

    Returns:
        Lista de IDs de work units creados
    """
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        work_unit_ids = []

        for config in strategy_configs:
            c.execute("""INSERT INTO work_units
                (strategy_params, replicas_needed)
                VALUES (?, ?)""",
                (json.dumps(config), REDUNDANCY_FACTOR))

            work_unit_ids.append(c.lastrowid)

        conn.commit()
        conn.close()

    return work_unit_ids

def get_pending_work():
    """
    Obtiene un work unit pendiente o que necesita más réplicas

    Returns:
        Dict con work_unit_id y strategy_params, o None si no hay trabajo
    """
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        # Buscar work units que necesitan más réplicas
        c.execute("""SELECT id, strategy_params, replicas_needed, replicas_completed
            FROM work_units
            WHERE replicas_completed < replicas_needed
            ORDER BY created_at ASC
            LIMIT 1""")

        row = c.fetchone()
        conn.close()

        if row:
            return {
                'work_id': row['id'],
                'strategy_params': json.loads(row['strategy_params']),
                'replica_number': row['replicas_completed'] + 1,
                'replicas_needed': row['replicas_needed']
            }

        return None

def mark_work_assigned(work_id):
    """Marca un work unit como asignado e incrementa replicas_assigned"""
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("""UPDATE work_units
            SET status = 'assigned',
                replicas_assigned = replicas_assigned + 1
            WHERE id = ?""", (work_id,))

        conn.commit()
        conn.close()

# ============================================================================
# RESULT VALIDATION
# ============================================================================

def fuzzy_compare(val1, val2, tolerance=0.1):
    """
    Compara dos valores con tolerancia (para diferencias de punto flotante)

    Args:
        val1, val2: Valores a comparar
        tolerance: Tolerancia como porcentaje (0.1 = 10%)

    Returns:
        True si los valores son similares dentro de la tolerancia
    """
    if val1 == 0 and val2 == 0:
        return True

    if val1 == 0 or val2 == 0:
        return abs(val1 - val2) < 0.01

    diff_pct = abs(val1 - val2) / max(abs(val1), abs(val2))
    return diff_pct <= tolerance

def validate_work_unit(work_id):
    """
    Valida un work unit seleccionando el mejor resultado.

    Los algoritmos genéticos son estocásticos: cada ejecución produce
    resultados diferentes, por lo que el consenso exacto es imposible.
    En su lugar, seleccionamos el mejor resultado (mayor PnL) como canónico
    una vez que se tienen suficientes réplicas.

    Args:
        work_id: ID del work unit a validar

    Returns:
        True si se validó exitosamente, False si necesita más réplicas
    """
    # Número mínimo original de réplicas antes de validar
    MIN_REPLICAS = 2
    # Máximo de réplicas para evitar loops infinitos
    MAX_REPLICAS = 5

    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        # Obtener todas las réplicas de este work unit
        c.execute("""SELECT * FROM results
            WHERE work_unit_id = ?
            ORDER BY pnl DESC""", (work_id,))

        results = c.fetchall()

        # Verificar si tenemos suficientes réplicas (mínimo 2)
        if len(results) < MIN_REPLICAS:
            conn.close()
            return False  # Necesita más réplicas

        # Obtener leverage del work_unit para escalar PNL_MAX
        c.execute("SELECT strategy_params FROM work_units WHERE id = ?", (work_id,))
        work_unit_row = c.fetchone()
        leverage = 2  # Default
        if work_unit_row and work_unit_row['strategy_params']:
            try:
                params = json.loads(work_unit_row['strategy_params'])
                leverage = params.get('leverage', 2)
            except:
                pass

        # Seleccionar el mejor resultado válido como canónico
        # PNL_MAX escala con leverage: $1000 base * leverage
        PNL_MAX = 1000 * leverage
        MIN_TRADES = 5
        valid_results = [r for r in results
                         if r['pnl'] is not None
                         and r['pnl'] < PNL_MAX
                         and (r['trades'] or 0) >= MIN_TRADES]

        if valid_results:
            best_result = valid_results[0]  # Ya ordenado por pnl DESC
        else:
            # Ningún resultado pasa el filtro de sanidad — no marcar canónico
            print(f"⚠️  Work unit {work_id} descartado: todos los resultados son inválidos "
                  f"(PnL>{PNL_MAX} o trades<{MIN_TRADES}). Réplicas: {len(results)}")
            conn.commit()
            conn.close()
            return False

        c.execute("""UPDATE results
            SET is_canonical = 1, validated = 1
            WHERE id = ?""", (best_result['id'],))

        # Marcar todos los otros resultados como validados
        for r in results[1:]:
            c.execute("""UPDATE results
                SET validated = 1
                WHERE id = ?""", (r['id'],))

        # Actualizar work unit como completado
        c.execute("""UPDATE work_units
            SET status = 'completed', canonical_result_id = ?
            WHERE id = ?""", (best_result['id'], work_id))

        # Asegurar que replicas_needed no exceda el máximo
        c.execute("""UPDATE work_units
            SET replicas_needed = MIN(replicas_needed, ?)
            WHERE id = ?""", (MAX_REPLICAS, work_id))

        conn.commit()
        conn.close()

        print(f"✅ Work unit {work_id} validado - Mejor PnL: ${best_result['pnl']:,.2f} "
              f"({len(results)} réplicas evaluadas)")
        return True

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Dashboard web principal"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/mobile')
def mobile():
    """Dashboard mobile-optimizado (PWA)"""
    return render_template_string(MOBILE_HTML)

@app.route('/api/status', methods=['GET'])
def api_status():
    """Obtiene estadísticas generales del sistema"""

    # Auto-corrección: limpiar estados inconsistentes
    with db_lock:
        conn_cleanup = get_db_connection()
        c_cleanup = conn_cleanup.cursor()
        # Marcar como completed los WUs con suficientes réplicas pero estado incorrecto
        c_cleanup.execute("""
            UPDATE work_units
            SET status = 'completed'
            WHERE status IN ('assigned', 'in_progress')
            AND replicas_completed >= replicas_needed
        """)
        # Marcar como in_progress los WUs que tienen asignaciones pero no están completos
        c_cleanup.execute("""
            UPDATE work_units
            SET status = 'in_progress'
            WHERE status = 'assigned'
            AND replicas_assigned > replicas_completed
            AND replicas_completed < replicas_needed
        """)
        # Resetear WUs asignados sin progreso después de 5 minutos (300 segundos)
        # Solo si no hay resultados enviados
        c_cleanup.execute("""
            UPDATE work_units
            SET status = 'pending', replicas_assigned = replicas_completed
            WHERE status = 'assigned'
            AND replicas_assigned > 0
            AND replicas_completed = 0
        """)
        conn_cleanup.commit()
        conn_cleanup.close()

    conn = get_db_connection()
    c = conn.cursor()

    # Work units
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total_work = c.fetchone()['total']

    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed_work = c.fetchone()['completed']

    c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending'")
    pending_work = c.fetchone()['pending']

    # Contar WUs en progreso (incluye assigned e in_progress)
    c.execute("SELECT COUNT(*) as in_progress FROM work_units WHERE status IN ('assigned', 'in_progress')")
    in_progress_work = c.fetchone()['in_progress']

    # Workers (active = seen in last 5 minutes, last_seen stored as Unix timestamp)
    c.execute("SELECT COUNT(*) as active FROM workers WHERE (strftime('%s', 'now') - last_seen) < 300")
    active_workers = c.fetchone()['active']

    # Mejor estrategia
    c.execute("""SELECT r.*, w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1
        ORDER BY r.pnl DESC
        LIMIT 1""")

    best = c.fetchone()

    conn.close()

    return jsonify({
        'work_units': {
            'total': total_work,
            'completed': completed_work,
            'pending': pending_work,
            'in_progress': in_progress_work
        },
        'workers': {
            'active': active_workers
        },
        'best_strategy': {
            'pnl': best['pnl'] if best else 0,
            'trades': best['trades'] if best else 0,
            'win_rate': best['win_rate'] if best else 0
        } if best else None,
        'timestamp': time.time()
    })

@app.route('/api/get_work', methods=['GET'])
def api_get_work():
    """
    Endpoint para workers: obtener trabajo pendiente

    Query params:
        worker_id: Identificador único del worker

    Returns:
        JSON con work_id y strategy_params, o null si no hay trabajo
    """
    worker_id = request.args.get('worker_id')

    if not worker_id:
        return jsonify({'error': 'worker_id required'}), 400

    # Registrar/actualizar worker
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        # Derive real machine hostname from worker_id
        # e.g. "Enders-MacBook-Pro.local_Darwin_W1" -> "Enders-MacBook-Pro"
        # e.g. "ender-rog_Linux_W3" -> "ender-rog"
        _raw = worker_id.rsplit('_W', 1)[0] if '_W' in worker_id else worker_id
        for _sfx in ('_Darwin', '_Linux', '_Windows'):
            if _raw.endswith(_sfx):
                _raw = _raw[:-len(_sfx)]
                break
        machine_hostname = _raw.replace('.local', '')

        # First try to update existing worker (also fix hostname on each check-in)
        c.execute("UPDATE workers SET last_seen = strftime('%s', 'now'), hostname = ?, status = 'active' WHERE id = ?",
                  (machine_hostname, worker_id))

        # If no row was updated (new worker), insert
        if c.rowcount == 0:
            c.execute("""INSERT INTO workers
                (id, hostname, platform, last_seen, work_units_completed, total_execution_time, status)
                VALUES (?, ?, ?, strftime('%s', 'now'), 0, 0, 'active')""",
                (worker_id, machine_hostname,
                 request.headers.get('User-Agent', 'unknown')))

        conn.commit()
        conn.close()

    # Obtener trabajo pendiente
    work = get_pending_work()

    if work:
        mark_work_assigned(work['work_id'])
        print(f"📤 Trabajo {work['work_id']} asignado a worker {worker_id}")

        return jsonify(work)
    else:
        return jsonify({
            'work_id': None,
            'message': 'No work available'
        })

@app.route('/api/submit_result', methods=['POST'])
def api_submit_result():
    """
    Endpoint para workers: enviar resultado de backtest

    JSON body:
        work_id: ID del work unit
        worker_id: ID del worker
        pnl: PnL total
        trades: Número de trades
        win_rate: Win rate (0-1)
        sharpe_ratio: Sharpe ratio (opcional)
        max_drawdown: Max drawdown (opcional)
        execution_time: Tiempo de ejecución en segundos
        strategy_genome: Genoma de la estrategia (JSON string, opcional)

    Returns:
        JSON con status
    """
    data = request.json

    if not data or 'work_id' not in data or 'worker_id' not in data:
        return jsonify({'error': 'work_id and worker_id required'}), 400

    # Insertar resultado
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        # Obtener data_file del work unit para asociar al genoma élite
        c.execute("SELECT strategy_params FROM work_units WHERE id = ?", (data['work_id'],))
        wu_row = c.fetchone()
        data_file = ""
        if wu_row:
            try:
                params = json.loads(wu_row['strategy_params'])
                data_file = params.get('data_file', '')
            except:
                pass

        # Insertar resultado con genoma
        c.execute("""INSERT INTO results
            (work_unit_id, worker_id, pnl, trades, win_rate,
             sharpe_ratio, max_drawdown, execution_time, strategy_genome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data['work_id'], data['worker_id'],
             data.get('pnl', 0), data.get('trades', 0),
             data.get('win_rate', 0), data.get('sharpe_ratio', 0),
             data.get('max_drawdown', 0), data.get('execution_time', 0),
             data.get('strategy_genome', None)))

        # Incrementar contador de réplicas completadas
        c.execute("""UPDATE work_units
            SET replicas_completed = replicas_completed + 1
            WHERE id = ?""", (data['work_id'],))

        # Actualizar estadísticas del worker
        c.execute("""UPDATE workers
            SET work_units_completed = work_units_completed + 1,
                total_execution_time = total_execution_time + ?,
                last_seen = strftime('%s', 'now')
            WHERE id = ?""",
            (data.get('execution_time', 0), data['worker_id']))

        conn.commit()
        conn.close()

    # Agregar a élite si el resultado es bueno (fuera del lock para no bloquear)
    if data.get('strategy_genome') and data.get('pnl', 0) >= ELITE_MIN_PNL:
        add_to_elite(
            genome_json=data['strategy_genome'],
            pnl=data.get('pnl', 0),
            win_rate=data.get('win_rate', 0),
            sharpe_ratio=data.get('sharpe_ratio', 0),
            trades=data.get('trades', 0),
            data_file=data_file
        )

    print(f"📥 Resultado recibido de worker {data['worker_id']} - " +
          f"Work {data['work_id']}: PnL=${data.get('pnl', 0):,.2f}")

    # Intentar validar el work unit
    validate_work_unit(data['work_id'])

    return jsonify({'status': 'success', 'message': 'Result received'})

@app.route('/api/workers', methods=['GET'])
def api_workers():
    """Lista todos los workers registrados"""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""SELECT id, hostname, platform, last_seen,
        work_units_completed, total_execution_time, status
        FROM workers
        ORDER BY last_seen DESC""")

    now_unix = time.time()
    workers = []
    for row in c.fetchall():
        last_seen_raw = row['last_seen'] or 0
        # Handle legacy Julian Day values stored before Unix-timestamp migration
        if 0 < last_seen_raw < 2500000:
            last_seen_unix = (last_seen_raw - 2440587.5) * 86400
        else:
            last_seen_unix = last_seen_raw
        mins_ago = (now_unix - last_seen_unix) / 60.0 if last_seen_unix > 0 else 9999.0
        workers.append({
            'id': row['id'],
            'hostname': row['hostname'],
            'platform': row['platform'],
            'last_seen': last_seen_unix,
            'last_seen_minutes_ago': round(mins_ago, 1),
            'work_units_completed': row['work_units_completed'],
            'total_execution_time': row['total_execution_time'],
            'status': 'active' if mins_ago < 5 else 'inactive'
        })

    conn.close()

    return jsonify({'workers': workers})

@app.route('/api/results', methods=['GET'])
def api_results():
    """Lista todos los resultados canónicos (validados)"""
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""SELECT r.*, w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1
        ORDER BY r.pnl DESC""")

    results = []
    for row in c.fetchall():
        results.append({
            'work_id': row['work_unit_id'],
            'worker_id': row['worker_id'],
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe_ratio': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'execution_time': row['execution_time'],
            'strategy_params': json.loads(row['strategy_params'])
        })

    conn.close()

    return jsonify({'results': results})


@app.route('/api/results/all', methods=['GET'])
def api_all_results():
    """Lista todos los resultados (no solo canónicos)"""
    limit = request.args.get('limit', 100, type=int)
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""SELECT r.*, w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        ORDER BY r.submitted_at DESC
        LIMIT ?""", (limit,))
    
    results = []
    for row in c.fetchall():
        results.append({
            'id': row['id'],
            'work_unit_id': row['work_unit_id'],
            'worker_id': row['worker_id'],
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe_ratio': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'execution_time': row['execution_time'],
            'submitted_at': (row['submitted_at'] - 2440587.5) * 86400 if row['submitted_at'] and row['submitted_at'] > 2000000 else row['submitted_at'],
            'validated': row['validated'],
            'is_canonical': row['is_canonical'],
            'strategy_params': json.loads(row['strategy_params'])
        })
    
    conn.close()
    return jsonify({'results': results})

@app.route('/api/dashboard_stats', methods=['GET'])
def api_dashboard_stats():
    """Estadísticas completas para el dashboard de la interfaz"""
    import time
    from datetime import datetime
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Work units stats
    c.execute("SELECT COUNT(*) FROM work_units")
    total_wu = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
    completed_wu = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
    pending_wu = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='in_progress' OR status='assigned'")
    in_progress_wu = c.fetchone()[0]
    
    # Workers stats
    c.execute("SELECT COUNT(*) FROM workers")
    total_workers = c.fetchone()[0]
    
    # Calculate "active" workers (seen in last 5 minutes, last_seen is Unix timestamp)
    c.execute("SELECT COUNT(*) FROM workers WHERE (strftime('%s', 'now') - last_seen) < 300")
    active_workers = c.fetchone()[0]
    
    # Results stats
    c.execute("SELECT COUNT(*) FROM results")
    total_results = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM results WHERE pnl > 0 AND pnl < 5000 AND trades >= 10")
    positive_results = c.fetchone()[0]

    c.execute("SELECT AVG(pnl) FROM results WHERE pnl > 0 AND pnl < 5000 AND trades >= 10")
    avg_pnl = c.fetchone()[0] or 0

    # PnL timeline - last 24 hours (only valid results)
    c.execute("SELECT pnl, submitted_at, work_unit_id, worker_id, is_canonical FROM results WHERE submitted_at > (julianday('now') - 1) AND pnl > -10000 AND pnl < 10000 ORDER BY submitted_at DESC")
    pnl_timeline = []
    for row in c.fetchall():
        # Convert Julian day to Unix timestamp
        # Unix epoch = JD 2440587.5 (Jan 1, 1970 00:00 UTC)
        unix_ts = (row[1] - 2440587.5) * 86400
        pnl_timeline.append({
            'pnl': row[0], 
            'timestamp': unix_ts,
            'submitted_at_unix': unix_ts,
            'work_unit_id': row[2],
            'worker_id': row[3],
            'is_canonical': bool(row[4])
        })
    
    # Completion timeline - group by hour (Julian Day * 24 gives unique integer per hour)
    c.execute("""SELECT COUNT(*), MIN(submitted_at) as bucket_start
                 FROM results
                 WHERE submitted_at > (julianday('now') - 1)
                 GROUP BY CAST(submitted_at * 24 AS INT)
                 ORDER BY bucket_start ASC""")
    completion_timeline = [{'hour_unix': (row[1] - 2440587.5) * 86400, 'count': row[0]} for row in c.fetchall()]
    
    # Best strategy
    c.execute("""SELECT r.*, w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1
        ORDER BY r.pnl DESC LIMIT 1""")
    best_row = c.fetchone()
    
    best_strategy = None
    if best_row:
        best_strategy = {
            'pnl': best_row['pnl'],
            'trades': best_row['trades'],
            'win_rate': best_row['win_rate'],
            'sharpe_ratio': best_row['sharpe_ratio'],
            'max_drawdown': best_row['max_drawdown'],
            'execution_time': best_row['execution_time'],
            'work_unit_id': best_row['work_unit_id'],
            'worker_id': best_row['worker_id'],
            'is_canonical': best_row['is_canonical']
        }
    
    # Worker performance stats — pre-fetch max_pnl for ALL workers in one query
    c.execute("""SELECT worker_id, MAX(pnl) as max_pnl
                 FROM results
                 WHERE pnl < 1000 AND trades >= 5
                 GROUP BY worker_id""")
    worker_max_pnl = {row[0]: row[1] for row in c.fetchall()}

    c.execute("""SELECT id, hostname, work_units_completed, total_execution_time,
                         last_seen, status
                  FROM workers ORDER BY work_units_completed DESC""")

    now_unix = time.time()
    worker_stats = []
    for row in c.fetchall():
        row_dict = dict(row)

        # last_seen is stored as Unix timestamp from strftime('%s', 'now')
        last_seen_unix = row_dict.get('last_seen') or 0
        mins_ago = (now_unix - last_seen_unix) / 60 if last_seen_unix > 0 else 999

        # Build short_name: "MacBook-Pro W1", "ender-rog W3", "enderj W2"
        wid = row_dict['id']
        _base = wid.rsplit('_W', 1)[0] if '_W' in wid else wid
        for _sfx in ('_Darwin', '_Linux', '_Windows'):
            if _base.endswith(_sfx):
                _base = _base[:-len(_sfx)]
                break
        _base = _base.replace('.local', '')
        _inst = wid.rsplit('_W', 1)[1] if '_W' in wid else ''
        short_name = _base + (' W' + _inst if _inst else '')

        # Machine classification for Streamlit globe grouping
        _wid_l = wid.lower()
        if 'macbook-pro' in _wid_l:
            machine = 'MacBook Pro'
        elif 'macbook-air' in _wid_l:
            machine = 'MacBook Air'
        elif 'macbook' in _wid_l:
            machine = 'MacBook'
        elif 'rog' in _wid_l:
            machine = 'Linux ROG'
        elif 'enderj' in _wid_l and 'linux' in _wid_l:
            machine = 'Asus Dorada'
        elif 'linux' in _wid_l:
            machine = 'Linux ROG'
        else:
            machine = 'Otro'

        max_pnl = worker_max_pnl.get(row_dict['id'], 0) or 0

        worker_stats.append({
            'id': row_dict['id'],
            'short_name': short_name,
            'machine': machine,
            'hostname': row_dict['hostname'],
            'work_units_completed': row_dict['work_units_completed'],
            'total_execution_time': row_dict['total_execution_time'],
            'last_seen': last_seen_unix,
            'last_seen_minutes_ago': mins_ago,
            'status': 'active' if mins_ago < 5 else 'inactive',
            'max_pnl': max_pnl
        })
    
    # PnL distribution (only valid results)
    c.execute("SELECT pnl FROM results WHERE pnl > -10000 AND pnl < 10000 AND pnl IS NOT NULL")
    pnl_distribution = [row[0] for row in c.fetchall()]
    
    # Performance metrics
    c.execute("SELECT AVG(execution_time) FROM results WHERE execution_time > 0")
    avg_exec_time = c.fetchone()[0] or 0

    c.execute("SELECT SUM(execution_time) FROM results")
    total_compute_time = c.fetchone()[0] or 0

    # results_per_hour: use wall-clock time from first result submission to now
    c.execute("SELECT MIN(submitted_at) FROM results")
    first_submitted_jd = c.fetchone()[0]
    if first_submitted_jd and first_submitted_jd > 2000000:
        # Julian Day → Unix timestamp
        first_unix = (first_submitted_jd - 2440587.5) * 86400
        wall_clock_hours = max((time.time() - first_unix) / 3600, 1/60)
    else:
        wall_clock_hours = 1
    results_per_hour = total_results / wall_clock_hours

    # =====================================================
    # ESTADÍSTICAS POR ACTIVO (NUEVO)
    # =====================================================
    # Filtrar resultados válidos: PnL realista (< $5000), suficientes trades (>=10), Sharpe real (< 10)
    c.execute("""
        SELECT
            json_extract(w.strategy_params, '$.data_file') as data_file,
            COUNT(*) as total_wus,
            SUM(CASE WHEN w.status='completed' THEN 1 ELSE 0 END) as completed,
            AVG(CASE WHEN r.pnl > -5000 AND r.pnl < 5000 AND r.trades >= 10 THEN r.pnl END) as avg_pnl,
            MAX(CASE WHEN r.pnl > -5000 AND r.pnl < 5000 AND r.trades >= 10 THEN r.pnl END) as max_pnl,
            SUM(CASE WHEN r.trades >= 10 THEN r.trades END) as total_trades,
            SUM(r.execution_time) as total_time
        FROM work_units w
        LEFT JOIN results r ON w.id = r.work_unit_id
        GROUP BY data_file
        ORDER BY max_pnl DESC
        LIMIT 20
    """)
    asset_stats = []
    for row in c.fetchall():
        data_file = row[0] or 'Unknown'
        # Extraer nombre del activo del archivo
        if 'BTC' in data_file:
            asset = 'BTC'
            category = 'Spot' if 'USD' in data_file else 'Futures'
        elif 'ETH' in data_file or 'ETP' in data_file or data_file.startswith('ET'):
            asset = 'ETH'
            category = 'Futures'
        elif 'SOL' in data_file or 'SLP' in data_file:
            asset = 'SOL'
            category = 'Futures'
        elif 'XRP' in data_file or 'XPP' in data_file:
            asset = 'XRP'
            category = 'Futures'
        elif 'GOL' in data_file:
            asset = 'GOLD'
            category = 'Futures'
        elif 'MC' in data_file:
            asset = 'SP500'
            category = 'Futures'
        elif 'DOG' in data_file:
            asset = 'DOGE'
            category = 'Futures'
        elif 'SHB' in data_file:
            asset = 'SHIB'
            category = 'Futures'
        else:
            # Intentar extraer del nombre del archivo
            parts = data_file.replace('.csv', '').split('_')[0].split('-')[0]
            asset = parts[:4] if len(parts) > 4 else parts
            category = 'Futures' if '-' in data_file else 'Spot'

        asset_stats.append({
            'data_file': data_file,
            'asset': asset,
            'category': category,
            'total_wus': row[1] or 0,
            'completed': row[2] or 0,
            'avg_pnl': round(row[3] or 0, 2),
            'max_pnl': round(row[4] or 0, 2),
            'total_trades': row[5] or 0,
            'total_time': round(row[6] or 0, 1)
        })

    # Capital simulado total - solo resultados válidos (cada backtest usa $500)
    c.execute("SELECT COUNT(*) FROM results WHERE pnl > -5000 AND pnl < 5000 AND trades >= 10")
    valid_results = c.fetchone()[0]
    simulated_capital = valid_results * 500

    # Élite count
    c.execute("SELECT COUNT(*) FROM elite_genomes")
    elite_count = c.fetchone()[0]

    conn.close()

    return jsonify({
        'work_units': {
            'total': total_wu,
            'completed': completed_wu,
            'pending': pending_wu,
            'in_progress': in_progress_wu
        },
        'workers': {
            'active': active_workers,
            'total_registered': total_workers
        },
        'performance': {
            'total_results': total_results,
            'positive_pnl_count': positive_results,
            'avg_pnl': avg_pnl,
            'results_per_hour': results_per_hour,
            'avg_execution_time': avg_exec_time,
            'total_compute_time': total_compute_time,
            'simulated_capital': simulated_capital
        },
        'best_strategy': best_strategy,
        'pnl_distribution': pnl_distribution,
        'pnl_timeline': pnl_timeline,
        'completion_timeline': completion_timeline,
        'worker_stats': worker_stats,
        'asset_stats': asset_stats,
        'elite_count': elite_count,
        'timestamp': time.time()
    })

# ============================================================================
# MOBILE DASHBOARD HTML (PWA)
# ============================================================================

MOBILE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#0d1117">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Bittrader">
<title>Bittrader Monitor</title>
<style>
:root {
  --bg:      #0d1117;
  --surface: #161b22;
  --surface2:#1c2128;
  --border:  #30363d;
  --green:   #3fb950;
  --green2:  #238636;
  --yellow:  #d29922;
  --red:     #f85149;
  --blue:    #58a6ff;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --nav-h:   64px;
  --header-h:56px;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;overflow:hidden}

/* ── HEADER ── */
.app-header{
  position:fixed;top:0;left:0;right:0;height:var(--header-h);
  background:var(--surface);border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
  padding:0 16px;z-index:100;
}
.app-header h1{font-size:17px;font-weight:700;letter-spacing:.3px}
.app-header h1 span{color:var(--green)}
.header-right{display:flex;align-items:center;gap:10px}
.clock{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
.dot{width:9px;height:9px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);animation:pulse 2s infinite}
.dot.off{background:var(--red);box-shadow:0 0 6px var(--red);animation:none}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* ── SCROLL AREA ── */
.scroll-area{
  position:fixed;
  top:var(--header-h);
  bottom:var(--nav-h);
  left:0;right:0;
  overflow-y:auto;
  -webkit-overflow-scrolling:touch;
  padding:12px 12px 8px;
}

/* ── BOTTOM NAV ── */
.bottom-nav{
  position:fixed;bottom:0;left:0;right:0;height:var(--nav-h);
  background:var(--surface);border-top:1px solid var(--border);
  display:flex;z-index:100;
  padding-bottom:env(safe-area-inset-bottom);
}
.nav-btn{
  flex:1;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:4px;border:none;background:transparent;
  color:var(--muted);font-size:10px;font-weight:500;cursor:pointer;
  transition:color .15s;padding:8px 0;
}
.nav-btn.active{color:var(--green)}
.nav-btn svg{width:22px;height:22px;stroke-width:1.8}

/* ── TABS ── */
.tab{display:none}
.tab.active{display:block}

/* ── KPI GRID ── */
.kpi-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.kpi{
  background:var(--surface);border:1px solid var(--border);
  border-radius:12px;padding:14px 12px;position:relative;overflow:hidden;
}
.kpi::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:var(--accent,var(--green));border-radius:3px 3px 0 0;
}
.kpi-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.7px}
.kpi-value{font-size:32px;font-weight:800;color:var(--accent,var(--green));line-height:1.1;margin:4px 0 2px}
.kpi-sub{font-size:11px;color:var(--muted)}

/* ── CARD ── */
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:12px;overflow:hidden}
.card-title{
  font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;
  color:var(--muted);padding:12px 14px 8px;border-bottom:1px solid var(--border);
}

/* ── PROGRESS ── */
.prog-wrap{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:12px}
.prog-row{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}
.prog-title{font-size:13px;font-weight:600}
.prog-pct{font-size:20px;font-weight:800;color:var(--green)}
.prog-bg{background:#21262d;border-radius:6px;height:10px;overflow:hidden}
.prog-fill{height:100%;border-radius:6px;background:linear-gradient(90deg,var(--green2),var(--green));transition:width .6s}
.prog-sub{display:flex;gap:12px;margin-top:8px;flex-wrap:wrap}
.prog-sub span{font-size:11px;color:var(--muted)}

/* ── GOAL ── */
.goal-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:12px}
.goal-top{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.goal-pct-big{font-size:36px;font-weight:800;color:var(--gcolor,var(--red));line-height:1}
.goal-info{display:flex;flex-direction:column;gap:2px}
.goal-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.goal-badge{
  margin-left:auto;font-size:22px;font-weight:800;
  color:var(--gcolor,var(--red));
  background:rgba(255,255,255,.04);border:1px solid var(--border);
  border-radius:8px;padding:6px 12px;white-space:nowrap;
}
.goal-bg{background:#21262d;border-radius:6px;height:12px;overflow:hidden;margin-bottom:6px}
.goal-fill{height:100%;border-radius:6px;background:var(--ggradient,linear-gradient(90deg,#f85149,#d29922));transition:width .8s}
.goal-msg{font-size:11px;color:var(--muted);text-align:center;margin-top:8px}
.goal-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.gm{background:#21262d;border-radius:8px;padding:10px 12px;border-left:3px solid var(--border)}
.gm-val{font-size:18px;font-weight:700}
.gm-lbl{font-size:10px;color:var(--muted);margin-top:2px}

/* ── BEST STRATEGY ── */
.best-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:12px}
.best-item{background:var(--surface2);border-radius:8px;padding:10px;text-align:center}
.best-val{font-size:20px;font-weight:700;color:var(--green)}
.best-lbl{font-size:10px;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.5px}

/* ── WORKERS LIST ── */
.worker-item{
  display:flex;align-items:center;gap:10px;
  padding:11px 14px;border-bottom:1px solid var(--border);
}
.worker-item:last-child{border-bottom:none}
.worker-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.worker-dot.alive{background:var(--green);box-shadow:0 0 5px var(--green)}
.worker-dot.dead{background:var(--red)}
.worker-name{font-size:13px;font-weight:500;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.worker-wus{font-size:12px;color:var(--blue);font-weight:600;white-space:nowrap}
.worker-ago{font-size:11px;color:var(--muted);white-space:nowrap}

/* ── TOP RESULTS ── */
.result-item{padding:12px 14px;border-bottom:1px solid var(--border)}
.result-item:last-child{border-bottom:none}
.result-row1{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
.result-rank{font-size:12px;color:var(--muted);width:24px}
.result-pnl{font-size:18px;font-weight:700;color:var(--green)}
.result-pnl.neg{color:var(--red)}
.result-row2{display:flex;gap:12px}
.result-stat{font-size:11px;color:var(--muted)}
.result-stat b{color:var(--text)}

/* ── REFRESH INDICATOR ── */
.refresh-bar{height:2px;background:var(--border);margin-bottom:12px;border-radius:1px;overflow:hidden}
.refresh-fill{height:100%;background:var(--green);transition:width 1s linear;border-radius:1px}

/* ── EMPTY STATE ── */
.empty{text-align:center;padding:32px 16px;color:var(--muted);font-size:13px}
</style>
</head>
<body>

<header class="app-header">
  <h1>🧬 Bit<span>trader</span></h1>
  <div class="header-right">
    <span class="clock" id="clock">--:--</span>
    <div class="dot" id="dot"></div>
  </div>
</header>

<!-- TAB: DASHBOARD -->
<div class="scroll-area tab active" id="tab-dash">
  <div class="refresh-bar"><div class="refresh-fill" id="rfill" style="width:100%"></div></div>

  <!-- KPIs -->
  <div class="kpi-grid">
    <div class="kpi" style="--accent:var(--blue)">
      <div class="kpi-label">Workers</div>
      <div class="kpi-value" id="d-workers">-</div>
      <div class="kpi-sub">activos ahora</div>
    </div>
    <div class="kpi" style="--accent:var(--green)">
      <div class="kpi-label">Mejor PnL</div>
      <div class="kpi-value" id="d-pnl">$-</div>
      <div class="kpi-sub" id="d-wr">- win rate</div>
    </div>
    <div class="kpi" style="--accent:var(--yellow)">
      <div class="kpi-label">Pendientes</div>
      <div class="kpi-value" id="d-pending">-</div>
      <div class="kpi-sub">work units</div>
    </div>
    <div class="kpi" style="--accent:var(--green)">
      <div class="kpi-label">Completados</div>
      <div class="kpi-value" id="d-done">-</div>
      <div class="kpi-sub" id="d-pct">- % del total</div>
    </div>
  </div>

  <!-- PROGRESS -->
  <div class="prog-wrap">
    <div class="prog-row">
      <span class="prog-title">Progreso total</span>
      <span class="prog-pct" id="d-prog-pct">0%</span>
    </div>
    <div class="prog-bg"><div class="prog-fill" id="d-prog-fill" style="width:0%"></div></div>
    <div class="prog-sub">
      <span id="d-prog-comp">✓ 0</span>
      <span id="d-prog-inp">⚡ 0</span>
      <span id="d-prog-pend">⏳ 0</span>
    </div>
  </div>

  <!-- OBJETIVO 5% -->
  <div class="goal-card" id="goal-card">
    <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.7px;color:var(--muted);margin-bottom:10px">🎯 Objetivo: 5% Diario</div>
    <div class="goal-top">
      <div>
        <div class="goal-pct-big" id="g-daily">0.00%</div>
        <div class="goal-label">retorno diario</div>
      </div>
      <div class="goal-badge" id="g-badge">0.0%</div>
    </div>
    <div class="goal-bg"><div class="goal-fill" id="g-fill" style="width:0%"></div></div>
    <div class="goal-msg" id="g-msg">Esperando datos...</div>
    <div class="goal-metrics">
      <div class="gm"><div class="gm-val" id="g-pnl">$-</div><div class="gm-lbl">PnL total</div></div>
      <div class="gm"><div class="gm-val" id="g-dailypnl">$-</div><div class="gm-lbl">PnL/día</div></div>
      <div class="gm"><div class="gm-val" id="g-sharpe" style="color:var(--yellow)">-</div><div class="gm-lbl">Sharpe</div></div>
      <div class="gm"><div class="gm-val" id="g-dd" style="color:var(--yellow)">-%</div><div class="gm-lbl">Max Drawdown</div></div>
    </div>
  </div>

  <!-- MEJOR ESTRATEGIA -->
  <div class="card">
    <div class="card-title">🏆 Mejor Estrategia</div>
    <div class="best-grid">
      <div class="best-item"><div class="best-val" id="b-pnl">$-</div><div class="best-lbl">PnL</div></div>
      <div class="best-item"><div class="best-val" id="b-wr">-%</div><div class="best-lbl">Win Rate</div></div>
      <div class="best-item"><div class="best-val" id="b-trades">-</div><div class="best-lbl">Trades</div></div>
      <div class="best-item"><div class="best-val" id="b-sharpe">-</div><div class="best-lbl">Sharpe</div></div>
    </div>
  </div>
</div>

<!-- TAB: WORKERS -->
<div class="scroll-area tab" id="tab-workers">
  <div class="card">
    <div class="card-title">🖥️ Workers activos</div>
    <div id="workers-list"><div class="empty">Cargando...</div></div>
  </div>
</div>

<!-- TAB: RESULTADOS -->
<div class="scroll-area tab" id="tab-results">
  <div class="card">
    <div class="card-title">📊 Top Estrategias</div>
    <div id="results-list"><div class="empty">Cargando...</div></div>
  </div>
</div>

<!-- TAB: ACTIVOS -->
<div class="scroll-area tab" id="tab-assets">
  <div class="card">
    <div class="card-title">📈 Por Activo</div>
    <div id="assets-list"><div class="empty">Cargando...</div></div>
  </div>
  <div class="card" style="margin-top:12px">
    <div class="card-title">💰 Capital Simulado</div>
    <div style="padding:12px 14px">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
        <span style="color:var(--muted);font-size:12px">Por backtest</span>
        <span style="font-weight:600">$500</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
        <span style="color:var(--muted);font-size:12px">Total backtests</span>
        <span style="font-weight:600" id="m-total-tests">-</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-bottom:8px">
        <span style="color:var(--muted);font-size:12px">Capital simulado</span>
        <span style="font-weight:600;color:var(--green)" id="m-sim-cap">$-</span>
      </div>
      <div style="display:flex;justify-content:space-between">
        <span style="color:var(--muted);font-size:12px">Tiempo cómputo</span>
        <span style="font-weight:600;color:var(--yellow)" id="m-compute-time">-</span>
      </div>
    </div>
  </div>
</div>

<!-- BOTTOM NAV -->
<nav class="bottom-nav">
  <button class="nav-btn active" id="nav-dash" onclick="switchTab('dash')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
    Panel
  </button>
  <button class="nav-btn" id="nav-workers" onclick="switchTab('workers')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="9" cy="7" r="4"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/><path d="M21 21v-2a4 4 0 0 0-3-3.85"/></svg>
    Workers
  </button>
  <button class="nav-btn" id="nav-results" onclick="switchTab('results')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    Resultados
  </button>
  <button class="nav-btn" id="nav-assets" onclick="switchTab('assets')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
    Activos
  </button>
</nav>

<script>
const REFRESH_S = 10;
let countdown = REFRESH_S;
let timer = null;

// ── Tab switching ────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
}

// ── Clock ────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.getHours().toString().padStart(2,'0') + ':' +
    now.getMinutes().toString().padStart(2,'0') + ':' +
    now.getSeconds().toString().padStart(2,'0');
}
setInterval(tickClock, 1000);
tickClock();

// ── Refresh bar ──────────────────────────────────────────────────
function tickRefresh() {
  countdown--;
  const pct = (countdown / REFRESH_S * 100).toFixed(0);
  document.getElementById('rfill').style.width = pct + '%';
  if (countdown <= 0) {
    countdown = REFRESH_S;
    fetchAll();
  }
}
setInterval(tickRefresh, 1000);

// ── Helpers ──────────────────────────────────────────────────────
function fmt(n, d=2) {
  if (n === null || n === undefined) return '-';
  return Number(n).toLocaleString('es-ES', {minimumFractionDigits: d, maximumFractionDigits: d});
}
function fmtMin(m) {
  if (m < 1)   return 'ahora';
  if (m < 60)  return Math.round(m) + 'm';
  return Math.round(m/60) + 'h ' + (Math.round(m)%60) + 'm';
}
function setColor(el, val, good, warn) {
  el.style.color = val >= good ? 'var(--green)' : val >= warn ? 'var(--yellow)' : 'var(--red)';
}

// ── Main fetch ───────────────────────────────────────────────────
async function fetchAll() {
  try {
    const [s, d, r] = await Promise.all([
      fetch('/api/status').then(x => x.json()),
      fetch('/api/dashboard_stats').then(x => x.json()),
      fetch('/api/results').then(x => x.json())
    ]);

    document.getElementById('dot').className = 'dot';

    const wu = s.work_units;
    const pct = wu.total > 0 ? (wu.completed / wu.total * 100) : 0;

    // ── KPIs ──
    document.getElementById('d-workers').textContent = d.workers.active;
    document.getElementById('d-pending').textContent = wu.pending.toLocaleString();
    document.getElementById('d-done').textContent    = wu.completed.toLocaleString();
    document.getElementById('d-pct').textContent     = pct.toFixed(1) + '% del total';

    // Progress
    document.getElementById('d-prog-pct').textContent     = pct.toFixed(1) + '%';
    document.getElementById('d-prog-fill').style.width    = pct.toFixed(1) + '%';
    document.getElementById('d-prog-comp').textContent    = '✓ ' + wu.completed.toLocaleString();
    document.getElementById('d-prog-inp').textContent     = '⚡ ' + wu.in_progress;
    document.getElementById('d-prog-pend').textContent    = '⏳ ' + wu.pending.toLocaleString();

    // Best strategy
    const best = d.best_strategy || s.best_strategy;
    if (best && best.pnl) {
      document.getElementById('d-pnl').textContent = '$' + fmt(best.pnl, 0);
      document.getElementById('d-wr').textContent  = (best.win_rate*100).toFixed(0) + '% win rate';
      document.getElementById('b-pnl').textContent    = '$' + fmt(best.pnl, 2);
      document.getElementById('b-wr').textContent     = (best.win_rate*100).toFixed(1) + '%';
      document.getElementById('b-trades').textContent = best.trades || '-';
      document.getElementById('b-sharpe').textContent = fmt(best.sharpe_ratio, 2);

      // Objetivo 5%
      const CAP = 500, TARGET = 5.0, DAYS = 80000/1440;
      const totalRet  = best.pnl / CAP * 100;
      const dailyPct  = totalRet / DAYS;
      const dailyPnl  = CAP * (dailyPct / 100);
      const progress  = Math.min(dailyPct / TARGET * 100, 100);

      let gc, gg, msg;
      if (progress < 20) {
        gc='#f85149'; gg='linear-gradient(90deg,#f85149,#d29922)';
        msg = '⚡ Inicio — sigue minando estrategias';
      } else if (progress < 50) {
        gc='#d29922'; gg='linear-gradient(90deg,#d29922,#e3b341)';
        msg = '📈 Buen progreso — ' + fmt(progress,1) + '% del objetivo';
      } else if (progress < 80) {
        gc='#58a6ff'; gg='linear-gradient(90deg,#58a6ff,#3fb950)';
        msg = '🚀 Muy cerca — ' + fmt(100-progress,1) + '% restante';
      } else {
        gc='#3fb950'; gg='linear-gradient(90deg,#238636,#3fb950)';
        msg = '🏆 ¡Objetivo casi alcanzado!';
      }

      const gc_card = document.getElementById('goal-card');
      gc_card.style.setProperty('--gcolor', gc);
      gc_card.style.setProperty('--ggradient', gg);

      document.getElementById('g-daily').textContent  = fmt(dailyPct,2) + '%';
      document.getElementById('g-badge').textContent  = fmt(progress,1) + '%';
      document.getElementById('g-fill').style.width   = progress.toFixed(1) + '%';
      document.getElementById('g-msg').textContent    = msg;
      document.getElementById('g-pnl').textContent    = '$' + fmt(best.pnl,2);
      document.getElementById('g-dailypnl').textContent = '$' + fmt(dailyPnl,2) + '/día';

      const srEl = document.getElementById('g-sharpe');
      srEl.textContent = fmt(best.sharpe_ratio,2);
      setColor(srEl, best.sharpe_ratio||0, 2, 1);

      const ddEl = document.getElementById('g-dd');
      const dd = (best.max_drawdown||0)*100;
      ddEl.textContent = fmt(dd,1) + '%';
      ddEl.style.color = dd<=10 ? 'var(--green)' : dd<=25 ? 'var(--yellow)' : 'var(--red)';
    }

    // ── Workers list ──
    const now = Date.now()/1000;
    const workers = d.worker_stats || [];
    const wDiv = document.getElementById('workers-list');
    if (!workers.length) {
      wDiv.innerHTML = '<div class="empty">Sin workers registrados</div>';
    } else {
      wDiv.innerHTML = workers.map(w => {
        const minsAgo = w.last_seen_minutes_ago || 999;
        const alive = minsAgo < 5;
        const name = w.short_name || (w.id.includes('_W')
          ? w.id.replace('_Darwin','').replace('_Linux','').replace('.local','')
          : w.id);
        return `<div class="worker-item">
          <div class="worker-dot ${alive?'alive':'dead'}"></div>
          <div class="worker-name">${name}</div>
          <div class="worker-wus">${(w.work_units_completed||0).toLocaleString()} WU</div>
          <div class="worker-ago">${fmtMin(minsAgo)}</div>
        </div>`;
      }).join('');
    }

    // ── Top results ──
    const results = r.results || [];
    const rDiv = document.getElementById('results-list');
    const medals = ['🥇','🥈','🥉'];
    if (!results.length) {
      rDiv.innerHTML = '<div class="empty">Sin resultados canónicos aún</div>';
    } else {
      rDiv.innerHTML = results.slice(0,15).map((res,i) => {
        const pnlClass = res.pnl>=0 ? '' : ' neg';
        const _wid = res.worker_id || '';
        const _base = _wid.replace(/_W\d+$/, '').replace(/_Darwin$|_Linux$|_Windows$/, '').replace('.local', '');
        const _im = _wid.match(/_W(\d+)$/);
        const wkr = (_base + (_im ? ' W' + _im[1] : '')) || _wid;
        return `<div class="result-item">
          <div class="result-row1">
            <span class="result-rank">${medals[i]||('#'+(i+1))}</span>
            <span class="result-pnl${pnlClass}">$${fmt(res.pnl,2)}</span>
          </div>
          <div class="result-row2">
            <span class="result-stat">WR: <b>${(res.win_rate*100).toFixed(1)}%</b></span>
            <span class="result-stat">Sharpe: <b>${fmt(res.sharpe_ratio,2)}</b></span>
            <span class="result-stat">Trades: <b>${res.trades}</b></span>
            <span class="result-stat" style="color:var(--muted)">${wkr}</span>
          </div>
        </div>`;
      }).join('');
    }

    // ── Asset stats ──
    const assetStats = d.asset_stats || [];
    const aDiv = document.getElementById('assets-list');
    if (!assetStats.length) {
      aDiv.innerHTML = '<div class="empty">Sin datos de activos</div>';
    } else {
      aDiv.innerHTML = assetStats.slice(0,15).map(a => {
        const pnlColor = a.max_pnl >= 0 ? 'var(--green)' : 'var(--red)';
        const catBadge = a.category === 'Futures' ? '🔶' : '🔵';
        return `<div class="result-item">
          <div class="result-row1">
            <span class="result-rank">${catBadge}</span>
            <span style="font-weight:600">${a.asset}</span>
            <span class="result-pnl" style="color:${pnlColor};margin-left:auto">$${fmt(a.max_pnl,0)}</span>
          </div>
          <div class="result-row2">
            <span class="result-stat">WUs: <b>${a.total_wus}</b></span>
            <span class="result-stat">Avg: <b>$${fmt(a.avg_pnl,0)}</b></span>
            <span class="result-stat">Trades: <b>${(a.total_trades||0).toLocaleString()}</b></span>
          </div>
        </div>`;
      }).join('');
    }

    // ── Capital summary ──
    const perf = d.performance || {};
    const totalResults = perf.total_results || 0;
    const simulatedCapital = perf.simulated_capital || (totalResults * 500);
    const totalComputeTime = perf.total_compute_time || 0;
    const computeHours = totalComputeTime / 3600;

    document.getElementById('m-total-tests').textContent = totalResults.toLocaleString();
    document.getElementById('m-sim-cap').textContent = '$' + fmt(simulatedCapital, 0);
    document.getElementById('m-compute-time').textContent = fmt(computeHours, 1) + 'h';

  } catch(e) {
    document.getElementById('dot').className = 'dot off';
    console.error(e);
  }
}

fetchAll();
</script>
</body>
</html>"""

# ============================================================================
# DASHBOARD HTML
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <title>Strategy Miner — Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --bg:      #0d1117;
            --surface: #161b22;
            --border:  #30363d;
            --green:   #3fb950;
            --green2:  #238636;
            --yellow:  #d29922;
            --red:     #f85149;
            --blue:    #58a6ff;
            --text:    #e6edf3;
            --muted:   #8b949e;
            --card-r:  8px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }

        /* ── HEADER ── */
        header {
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky; top: 0; z-index: 100;
        }
        header h1 { font-size: 18px; font-weight: 600; letter-spacing: .5px; }
        header h1 span { color: var(--green); }
        .header-right { display: flex; align-items: center; gap: 16px; }
        #live-clock { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
        .status-dot {
            width: 10px; height: 10px; border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 6px var(--green);
            animation: pulse 2s infinite;
        }
        .status-dot.offline { background: var(--red); box-shadow: 0 0 6px var(--red); animation: none; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

        /* ── LAYOUT ── */
        .page { max-width: 1400px; margin: 0 auto; padding: 24px 20px; }
        .section-title {
            font-size: 13px; font-weight: 600; text-transform: uppercase;
            letter-spacing: 1px; color: var(--muted); margin: 28px 0 12px;
        }

        /* ── KPI CARDS ── */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 14px;
        }
        .kpi {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--card-r);
            padding: 18px 16px;
            position: relative;
            overflow: hidden;
        }
        .kpi::before {
            content: '';
            position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: var(--accent, var(--green));
        }
        .kpi-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .8px; }
        .kpi-value { font-size: 28px; font-weight: 700; margin: 6px 0 2px; color: var(--accent, var(--green)); line-height: 1; }
        .kpi-sub   { font-size: 12px; color: var(--muted); }

        /* ── PROGRESS ── */
        .progress-wrap {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--card-r);
            padding: 16px 20px;
        }
        .progress-header { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; }
        .progress-bar-bg { background: #21262d; border-radius: 4px; height: 10px; overflow: hidden; }
        .progress-bar-fill {
            height: 100%; border-radius: 4px;
            background: linear-gradient(90deg, var(--green2), var(--green));
            transition: width .6s ease;
        }
        .progress-sub { margin-top: 8px; font-size: 12px; color: var(--muted); display:flex; gap:20px; }

        /* ── TWO-COL ── */
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media(max-width:900px){ .two-col{ grid-template-columns:1fr; } }

        /* ── CARD ── */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--card-r);
            overflow: hidden;
        }
        .card-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            font-size: 13px; font-weight: 600;
            display: flex; align-items: center; gap: 8px;
        }
        .card-body { padding: 16px; }
        .chart-wrap { padding: 12px 16px; height: 220px; position: relative; }

        /* ── TABLES ── */
        .tbl-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        thead th {
            background: #21262d;
            padding: 9px 12px;
            text-align: left;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: .7px;
            color: var(--muted);
            white-space: nowrap;
        }
        tbody tr { border-bottom: 1px solid var(--border); transition: background .15s; }
        tbody tr:hover { background: #21262d; }
        tbody td { padding: 9px 12px; white-space: nowrap; }
        tbody tr:last-child { border-bottom: none; }

        /* ── BADGES ── */
        .badge {
            display: inline-block; padding: 2px 8px; border-radius: 12px;
            font-size: 11px; font-weight: 600;
        }
        .badge-green  { background: rgba(63,185,80,.18); color: var(--green); }
        .badge-red    { background: rgba(248,81,73,.18);  color: var(--red); }
        .badge-yellow { background: rgba(210,153,34,.18); color: var(--yellow); }
        .badge-blue   { background: rgba(88,166,255,.18); color: var(--blue); }

        /* ── GOAL PANEL ── */
        .goal-wrap {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--card-r);
            padding: 20px;
        }
        .goal-header-row {
            display: flex; align-items: center; gap: 20px; margin-bottom: 16px; flex-wrap: wrap;
        }
        .goal-title-block { display: flex; flex-direction: column; }
        .goal-main-pct {
            font-size: 36px; font-weight: 800; line-height: 1;
            color: var(--goal-color, var(--red));
        }
        .goal-main-lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing:.6px; margin-top: 4px; }
        .goal-divider { width: 1px; height: 40px; background: var(--border); }
        .goal-target-block { display: flex; flex-direction: column; }
        .goal-target-val { font-size: 22px; font-weight: 700; color: var(--green); }
        .goal-target-lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing:.6px; margin-top: 4px; }
        .goal-progress-pct {
            margin-left: auto; font-size: 28px; font-weight: 800;
            color: var(--goal-color, var(--red));
            background: rgba(255,255,255,.04);
            border: 1px solid var(--border);
            border-radius: 8px; padding: 8px 18px;
        }
        .goal-bar-bg {
            background: #21262d; border-radius: 6px; height: 16px;
            overflow: visible; position: relative; margin-bottom: 8px;
        }
        .goal-bar-fill {
            height: 100%; border-radius: 6px; transition: width .8s ease;
            background: var(--goal-gradient, linear-gradient(90deg, #f85149, #d29922));
            position: relative; z-index: 1;
        }
        .goal-bar-markers {
            position: absolute; top: 20px; left: 0; right: 0;
            pointer-events: none;
        }
        .goal-bar-markers span {
            position: absolute; transform: translateX(-50%);
            font-size: 10px; color: var(--muted);
        }
        .goal-metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 12px; margin-top: 28px;
        }
        .goal-metric {
            background: #21262d; border-radius: 6px; padding: 12px 14px;
            border-left: 3px solid var(--border);
        }
        .goal-metric-val { font-size: 20px; font-weight: 700; color: var(--text); }
        .goal-metric-lbl { font-size: 11px; color: var(--muted); margin-top: 3px; }
        .goal-metric-target { font-size: 10px; color: var(--muted); opacity:.6; margin-top: 2px; }
        .goal-footer {
            margin-top: 14px; padding-top: 12px;
            border-top: 1px solid var(--border);
            font-size: 12px; color: var(--muted); text-align: center;
        }

        /* ── BEST STRATEGY PANEL ── */
        .best-panel {
            background: var(--surface);
            border: 1px solid var(--green2);
            border-radius: var(--card-r);
            padding: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 16px;
        }
        .best-stat { text-align: center; }
        .best-stat-val { font-size: 22px; font-weight: 700; color: var(--green); }
        .best-stat-lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing:.6px; margin-top: 4px; }

        /* ── FOOTER ── */
        .footer { text-align: center; margin-top: 32px; font-size: 12px; color: var(--muted); padding-bottom: 20px; }
        #last-update { color: var(--muted); }
    </style>
</head>
<body>

<header>
    <h1>🧬 Strategy Miner <span>Coordinator</span></h1>
    <div class="header-right">
        <div id="live-clock">--:--:--</div>
        <div class="status-dot" id="status-dot"></div>
    </div>
</header>

<div class="page">

    <!-- KPIs -->
    <div class="section-title">Sistema</div>
    <div class="kpi-grid" id="kpi-grid">
        <div class="kpi" style="--accent:var(--blue)">
            <div class="kpi-label">Work Units</div>
            <div class="kpi-value" id="k-total">-</div>
            <div class="kpi-sub">total creados</div>
        </div>
        <div class="kpi" style="--accent:var(--green)">
            <div class="kpi-label">Completados</div>
            <div class="kpi-value" id="k-completed">-</div>
            <div class="kpi-sub" id="k-pct">-% progreso</div>
        </div>
        <div class="kpi" style="--accent:var(--yellow)">
            <div class="kpi-label">En Progreso</div>
            <div class="kpi-value" id="k-inprogress">-</div>
            <div class="kpi-sub" id="k-pending">- pendientes</div>
        </div>
        <div class="kpi" style="--accent:var(--green)">
            <div class="kpi-label">Workers Activos</div>
            <div class="kpi-value" id="k-workers">-</div>
            <div class="kpi-sub" id="k-workers-total">- registrados</div>
        </div>
        <div class="kpi" style="--accent:var(--green)">
            <div class="kpi-label">Mejor PnL</div>
            <div class="kpi-value" id="k-bestpnl">$-</div>
            <div class="kpi-sub" id="k-bestwr">- win rate</div>
        </div>
        <div class="kpi" style="--accent:var(--blue)">
            <div class="kpi-label">Avg PnL (válido)</div>
            <div class="kpi-value" id="k-avgpnl">$-</div>
            <div class="kpi-sub" id="k-positive">- resultados positivos</div>
        </div>
        <div class="kpi" style="--accent:var(--yellow)">
            <div class="kpi-label">Resultados/hr</div>
            <div class="kpi-value" id="k-rph">-</div>
            <div class="kpi-sub" id="k-totalres">- total resultados</div>
        </div>
    </div>

    <!-- PROGRESS -->
    <div class="section-title">Progreso</div>
    <div class="progress-wrap">
        <div class="progress-header">
            <span id="prog-label">Calculando...</span>
            <span id="prog-pct" style="color:var(--green);font-weight:600">0%</span>
        </div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" id="prog-fill" style="width:0%"></div>
        </div>
        <div class="progress-sub">
            <span id="prog-comp">✓ 0 completados</span>
            <span id="prog-pend">⏳ 0 pendientes</span>
            <span id="prog-inp">⚡ 0 en progreso</span>
        </div>
    </div>

    <!-- OBJETIVO 5% DIARIO -->
    <div class="section-title">🎯 Objetivo: 5% Diario</div>
    <div class="goal-wrap" id="goal-wrap">
        <div class="goal-header-row">
            <div class="goal-title-block">
                <span class="goal-main-pct" id="goal-current-pct">0.00%</span>
                <span class="goal-main-lbl">retorno diario actual</span>
            </div>
            <div class="goal-divider"></div>
            <div class="goal-target-block">
                <span class="goal-target-val">5.00%</span>
                <span class="goal-target-lbl">objetivo diario</span>
            </div>
            <div class="goal-progress-pct" id="goal-pct-badge">0.0%</div>
        </div>

        <div class="goal-bar-bg">
            <div class="goal-bar-fill" id="goal-fill" style="width:0%"></div>
            <div class="goal-bar-markers">
                <span style="left:20%">1%</span>
                <span style="left:40%">2%</span>
                <span style="left:60%">3%</span>
                <span style="left:80%">4%</span>
                <span style="left:100%">5%</span>
            </div>
        </div>

        <div class="goal-metrics-grid">
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-daily-pnl">$-</div>
                <div class="goal-metric-lbl">PnL diario actual</div>
                <div class="goal-metric-target" id="gm-daily-target">objetivo $25/día</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-total-pnl">$-</div>
                <div class="goal-metric-lbl">PnL total (backtest)</div>
                <div class="goal-metric-target" id="gm-total-target">objetivo $-</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-total-return">-%</div>
                <div class="goal-metric-lbl">Retorno total acumulado</div>
                <div class="goal-metric-target" id="gm-total-return-target">objetivo -%</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-capital">$500</div>
                <div class="goal-metric-lbl">Capital del backtest</div>
                <div class="goal-metric-target">% calculado sobre $500</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-days">- días</div>
                <div class="goal-metric-lbl">Período del backtest</div>
                <div class="goal-metric-target" id="gm-candles">- candles</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-multiplier" style="color:var(--yellow)">-x</div>
                <div class="goal-metric-lbl">Mejora necesaria</div>
                <div class="goal-metric-target">para alcanzar el objetivo</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-winrate">-%</div>
                <div class="goal-metric-lbl">Win Rate actual</div>
                <div class="goal-metric-target">objetivo ≥ 60%</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-sharpe">-</div>
                <div class="goal-metric-lbl">Sharpe Ratio</div>
                <div class="goal-metric-target">objetivo ≥ 2.0</div>
            </div>
            <div class="goal-metric">
                <div class="goal-metric-val" id="gm-drawdown" style="color:var(--yellow)">-%</div>
                <div class="goal-metric-lbl">Max Drawdown</div>
                <div class="goal-metric-target">límite ≤ 10%</div>
            </div>
        </div>

        <div class="goal-footer">
            <span id="goal-status-msg">Calculando...</span>
        </div>
    </div>

    <!-- BEST STRATEGY -->
    <div class="section-title">🏆 Mejor Estrategia Encontrada</div>
    <div class="best-panel" id="best-panel">
        <div class="best-stat"><div class="best-stat-val" id="b-pnl">$-</div><div class="best-stat-lbl">PnL</div></div>
        <div class="best-stat"><div class="best-stat-val" id="b-trades">-</div><div class="best-stat-lbl">Trades</div></div>
        <div class="best-stat"><div class="best-stat-val" id="b-wr">-%</div><div class="best-stat-lbl">Win Rate</div></div>
        <div class="best-stat"><div class="best-stat-val" id="b-sharpe">-</div><div class="best-stat-lbl">Sharpe Ratio</div></div>
        <div class="best-stat"><div class="best-stat-val" id="b-dd">-%</div><div class="best-stat-lbl">Max Drawdown</div></div>
        <div class="best-stat"><div class="best-stat-val" id="b-worker" style="font-size:13px;word-break:break-all">-</div><div class="best-stat-lbl">Worker</div></div>
    </div>

    <!-- CHARTS + WORKERS -->
    <div class="section-title">Análisis</div>
    <div class="two-col">

        <!-- PnL Timeline -->
        <div class="card">
            <div class="card-header">📈 PnL Timeline (últimas 24h)</div>
            <div class="chart-wrap">
                <canvas id="chart-pnl"></canvas>
            </div>
        </div>

        <!-- Workers -->
        <div class="card">
            <div class="card-header">🖥️ Workers</div>
            <div class="tbl-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Worker</th>
                            <th>Estado</th>
                            <th>WUs</th>
                            <th>Max PnL</th>
                            <th>Visto</th>
                        </tr>
                    </thead>
                    <tbody id="workers-body">
                        <tr><td colspan="5" style="color:var(--muted);text-align:center;padding:20px">Cargando...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- TOP RESULTS -->
    <div class="section-title">📊 Top 10 Estrategias (canónicas)</div>
    <div class="card">
        <div class="tbl-wrap">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>WU ID</th>
                        <th>PnL</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                        <th>Sharpe</th>
                        <th>Max DD</th>
                        <th>Worker</th>
                    </tr>
                </thead>
                <tbody id="results-body">
                    <tr><td colspan="8" style="color:var(--muted);text-align:center;padding:20px">Cargando...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- ESTADÍSTICAS POR ACTIVO -->
    <div class="section-title">📈 Estadísticas por Activo</div>
    <div class="card">
        <div class="tbl-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Activo</th>
                        <th>Categoría</th>
                        <th>Archivo</th>
                        <th>WUs</th>
                        <th>Completados</th>
                        <th>PnL Promedio</th>
                        <th>Max PnL</th>
                        <th>Total Trades</th>
                        <th>Tiempo (s)</th>
                    </tr>
                </thead>
                <tbody id="assets-body">
                    <tr><td colspan="9" style="color:var(--muted);text-align:center;padding:20px">Cargando...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- RESUMEN DE CAPITAL -->
    <div class="section-title">💰 Resumen de Capital Simulado</div>
    <div class="kpi-grid" style="margin-bottom:16px">
        <div class="kpi" style="--accent:var(--green)">
            <div class="kpi-label">Capital por Backtest</div>
            <div class="kpi-value">$500</div>
            <div class="kpi-sub">configuración fija</div>
        </div>
        <div class="kpi" style="--accent:var(--blue)">
            <div class="kpi-label">Total Backtests</div>
            <div class="kpi-value" id="cap-total-tests">-</div>
            <div class="kpi-sub">resultados</div>
        </div>
        <div class="kpi" style="--accent:var(--yellow)">
            <div class="kpi-label">Capital Simulado Total</div>
            <div class="kpi-value" id="cap-simulated">$-</div>
            <div class="kpi-sub">si fueran reales</div>
        </div>
        <div class="kpi" style="--accent:var(--green)">
            <div class="kpi-label">Tiempo Total Cómputo</div>
            <div class="kpi-value" id="cap-compute-time">-</div>
            <div class="kpi-sub" id="cap-compute-hours">- horas</div>
        </div>
    </div>

    <div class="footer">
        <span id="last-update">Última actualización: -</span> &nbsp;·&nbsp; Auto-refresh cada 10s
    </div>

</div>

<script>
// ── Chart.js setup ──────────────────────────────────────────────
const PNL_MAX_POINTS = 200;
let pnlChart = null;

function initChart() {
    const ctx = document.getElementById('chart-pnl').getContext('2d');
    pnlChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'PnL ($)',
                data: [],
                borderColor: '#3fb950',
                backgroundColor: 'rgba(63,185,80,0.08)',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#161b22',
                    borderColor: '#30363d',
                    borderWidth: 1,
                    titleColor: '#8b949e',
                    bodyColor: '#e6edf3',
                    callbacks: {
                        label: ctx => '$' + ctx.parsed.y.toFixed(2)
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    ticks: { color: '#8b949e', maxTicksLimit: 6, font: { size: 10 } },
                    grid: { color: '#21262d' }
                },
                y: {
                    display: true,
                    ticks: {
                        color: '#8b949e', font: { size: 10 },
                        callback: v => '$' + v.toFixed(0)
                    },
                    grid: { color: '#21262d' }
                }
            }
        }
    });
}

function updateChart(timeline) {
    if (!pnlChart || !timeline || timeline.length === 0) return;

    // Sort by timestamp, take last N
    const sorted = [...timeline]
        .sort((a, b) => a.timestamp - b.timestamp)
        .slice(-PNL_MAX_POINTS);

    pnlChart.data.labels = sorted.map(p => {
        const d = new Date(p.timestamp * 1000);
        return d.getHours().toString().padStart(2,'0') + ':' +
               d.getMinutes().toString().padStart(2,'0');
    });
    pnlChart.data.datasets[0].data = sorted.map(p => p.pnl);
    pnlChart.update('none');
}

// ── Helpers ─────────────────────────────────────────────────────
function fmt(n, digits=2) {
    if (n === null || n === undefined) return '-';
    return Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function fmtMin(m) {
    if (m < 1)   return 'ahora';
    if (m < 60)  return Math.round(m) + 'm';
    return Math.round(m / 60) + 'h ' + Math.round(m % 60) + 'm';
}

// ── Main update ─────────────────────────────────────────────────
async function updateDashboard() {
    try {
        const [statusRes, dashRes, resultsRes] = await Promise.all([
            fetch('/api/status'),
            fetch('/api/dashboard_stats'),
            fetch('/api/results')
        ]);
        const status  = await statusRes.json();
        const dash    = await dashRes.json();
        const resData = await resultsRes.json();

        document.getElementById('status-dot').className = 'status-dot';

        // ── KPIs ──
        const wu = status.work_units;
        const pct = wu.total > 0 ? (wu.completed / wu.total * 100) : 0;
        document.getElementById('k-total').textContent       = wu.total.toLocaleString();
        document.getElementById('k-completed').textContent   = wu.completed.toLocaleString();
        document.getElementById('k-pct').textContent         = pct.toFixed(1) + '% progreso';
        document.getElementById('k-inprogress').textContent  = wu.in_progress;
        document.getElementById('k-pending').textContent     = wu.pending + ' pendientes';
        document.getElementById('k-workers').textContent     = dash.workers.active;
        document.getElementById('k-workers-total').textContent = dash.workers.total_registered + ' registrados';

        const perf = dash.performance || {};
        document.getElementById('k-avgpnl').textContent    = '$' + fmt(perf.avg_pnl, 0);
        document.getElementById('k-positive').textContent  = (perf.positive_pnl_count || 0).toLocaleString() + ' positivos';
        document.getElementById('k-rph').textContent       = fmt(perf.results_per_hour, 1);
        document.getElementById('k-totalres').textContent  = (perf.total_results || 0).toLocaleString() + ' total';

        // Best strategy
        const best = dash.best_strategy || status.best_strategy;
        if (best && best.pnl) {
            document.getElementById('k-bestpnl').textContent = '$' + fmt(best.pnl, 0);
            document.getElementById('k-bestwr').textContent  = (best.win_rate * 100).toFixed(0) + '% win rate';
            document.getElementById('b-pnl').textContent    = '$' + fmt(best.pnl, 2);
            document.getElementById('b-trades').textContent  = best.trades;
            document.getElementById('b-wr').textContent      = (best.win_rate * 100).toFixed(1) + '%';
            document.getElementById('b-sharpe').textContent  = fmt(best.sharpe_ratio, 2);
            document.getElementById('b-dd').textContent      = ((best.max_drawdown || 0) * 100).toFixed(1) + '%';
            document.getElementById('b-worker').textContent  = (best.worker_id || '-').split('_').slice(-1)[0];
        }

        // ── Objetivo 5% Diario ──
        if (best && best.pnl) {
            // El backtester corre con $500 capital (numba_backtester.py, balance = 500).
            // Todos los cálculos de % y PnL son directamente sobre esa base.
            const BACKTEST_CAPITAL = 500;    // capital del backtester
            const TARGET_DAILY_PCT = 5.0;
            const MAX_CANDLES      = 80000;
            const CANDLES_PER_DAY  = 1440;
            const BACKTEST_DAYS    = MAX_CANDLES / CANDLES_PER_DAY;

            // % de retorno basado en $500 capital
            const totalReturn    = best.pnl / BACKTEST_CAPITAL * 100;
            const dailyReturnPct = totalReturn / BACKTEST_DAYS;
            // PnL diario equivalente sobre $500
            const dailyPnl       = BACKTEST_CAPITAL * (dailyReturnPct / 100);
            const targetDailyPnl = BACKTEST_CAPITAL * (TARGET_DAILY_PCT / 100);
            const targetTotalPnl = targetDailyPnl * BACKTEST_DAYS;
            const targetTotalReturn = TARGET_DAILY_PCT * BACKTEST_DAYS;
            const progressPct    = Math.min(dailyReturnPct / TARGET_DAILY_PCT * 100, 100);
            const multiplier     = targetTotalPnl / Math.max(BACKTEST_CAPITAL * (totalReturn/100), 0.01);

            // Color based on progress
            let goalColor, goalGradient, statusMsg;
            if (progressPct < 20) {
                goalColor = '#f85149'; goalGradient = 'linear-gradient(90deg,#f85149,#d29922)';
                statusMsg = `⚡ Inicio del camino — necesitamos ${fmt(multiplier,1)}x de mejora en PnL diario para alcanzar el objetivo.`;
            } else if (progressPct < 50) {
                goalColor = '#d29922'; goalGradient = 'linear-gradient(90deg,#d29922,#e3b341)';
                statusMsg = `📈 Buen progreso — ${fmt(progressPct,1)}% del objetivo alcanzado. Seguir optimizando indicadores y leverage.`;
            } else if (progressPct < 80) {
                goalColor = '#58a6ff'; goalGradient = 'linear-gradient(90deg,#58a6ff,#3fb950)';
                statusMsg = `🚀 Muy cerca — ${fmt(100 - progressPct, 1)}% restante para el 5% diario. Refinando la estrategia...`;
            } else {
                goalColor = '#3fb950'; goalGradient = 'linear-gradient(90deg,#238636,#3fb950)';
                statusMsg = `🏆 ¡Objetivo casi alcanzado! Retorno diario de ${fmt(dailyReturnPct,2)}%. Validar en live trading.`;
            }

            // Apply color CSS var via style
            const gw = document.getElementById('goal-wrap');
            gw.style.setProperty('--goal-color', goalColor);
            gw.style.setProperty('--goal-gradient', goalGradient);

            document.getElementById('goal-current-pct').textContent = fmt(dailyReturnPct, 2) + '%';
            document.getElementById('goal-pct-badge').textContent   = fmt(progressPct, 1) + '%';
            document.getElementById('goal-fill').style.width        = progressPct.toFixed(1) + '%';

            document.getElementById('gm-daily-pnl').textContent     = '$' + fmt(dailyPnl, 2) + '/día';
            document.getElementById('gm-total-pnl').textContent     = '$' + fmt(best.pnl, 2);
            document.getElementById('gm-total-target').textContent  = 'objetivo $' + fmt(targetTotalPnl, 0);
            document.getElementById('gm-total-return').textContent  = fmt(totalReturn, 2) + '%';
            document.getElementById('gm-total-return-target').textContent = 'objetivo ' + fmt(targetTotalReturn, 0) + '%';
            document.getElementById('gm-days').textContent          = fmt(BACKTEST_DAYS, 1) + ' días';
            document.getElementById('gm-candles').textContent       = MAX_CANDLES.toLocaleString() + ' candles 1min';
            document.getElementById('gm-multiplier').textContent    = fmt(multiplier, 1) + 'x';

            const wr = best.win_rate || 0;
            const wrEl = document.getElementById('gm-winrate');
            wrEl.textContent = (wr * 100).toFixed(1) + '%';
            wrEl.style.color = wr >= 0.6 ? 'var(--green)' : wr >= 0.5 ? 'var(--yellow)' : 'var(--red)';

            const srEl = document.getElementById('gm-sharpe');
            const sr = best.sharpe_ratio || 0;
            srEl.textContent = fmt(sr, 2);
            srEl.style.color = sr >= 2 ? 'var(--green)' : sr >= 1 ? 'var(--yellow)' : 'var(--red)';

            const ddEl = document.getElementById('gm-drawdown');
            const dd = (best.max_drawdown || 0) * 100;
            ddEl.textContent = fmt(dd, 1) + '%';
            ddEl.style.color = dd <= 10 ? 'var(--green)' : dd <= 25 ? 'var(--yellow)' : 'var(--red)';

            document.getElementById('goal-status-msg').textContent = statusMsg;
        }

        // ── Progress bar ──
        document.getElementById('prog-label').textContent = wu.completed.toLocaleString() + ' de ' + wu.total.toLocaleString() + ' work units completados';
        document.getElementById('prog-pct').textContent   = pct.toFixed(1) + '%';
        document.getElementById('prog-fill').style.width  = pct.toFixed(1) + '%';
        document.getElementById('prog-comp').textContent  = '✓ ' + wu.completed.toLocaleString() + ' completados';
        document.getElementById('prog-pend').textContent  = '⏳ ' + wu.pending + ' pendientes';
        document.getElementById('prog-inp').textContent   = '⚡ ' + wu.in_progress + ' en progreso';

        // ── PnL Chart ──
        updateChart(dash.pnl_timeline || []);

        // ── Workers table ──
        const wbody = document.getElementById('workers-body');
        const workers = dash.worker_stats || [];
        if (workers.length === 0) {
            wbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:20px">Sin workers</td></tr>';
        } else {
            wbody.innerHTML = workers.map(w => {
                const alive = (w.last_seen_minutes_ago || 999) < 5;
                const badge = alive
                    ? '<span class="badge badge-green">activo</span>'
                    : '<span class="badge badge-red">inactivo</span>';
                const name = w.short_name || ((w.id || '').includes('_W')
                    ? w.id.split('_W').slice(-1)[0] ? (w.hostname||w.id) + ' W' + w.id.split('_W').slice(-1)[0] : (w.hostname||w.id)
                    : (w.hostname || w.id));
                const maxPnl = (w.max_pnl || 0) > 0
                    ? '<span style="color:var(--green)">$' + fmt(w.max_pnl, 0) + '</span>'
                    : '<span style="color:var(--muted)">-</span>';
                return `<tr>
                    <td style="font-family:monospace;font-size:12px">${name}</td>
                    <td>${badge}</td>
                    <td>${(w.work_units_completed || 0).toLocaleString()}</td>
                    <td>${maxPnl}</td>
                    <td style="color:var(--muted)">${fmtMin(w.last_seen_minutes_ago || 999)}</td>
                </tr>`;
            }).join('');
        }

        // ── Top results table ──
        const tbody = document.getElementById('results-body');
        const results = resData.results || [];
        if (results.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:20px">Sin resultados canónicos</td></tr>';
        } else {
            tbody.innerHTML = results.slice(0, 10).map((r, i) => {
                const rankColors = ['#f1c40f','#adb5bd','#cd7f32'];
                const medal = i < 3 ? `<span style="color:${rankColors[i]}">●</span> ` : '';
                const pnlColor = r.pnl > 0 ? 'var(--green)' : 'var(--red)';
                const ddVal = r.max_drawdown != null ? ((r.max_drawdown) * 100).toFixed(1) + '%' : '-';
                return `<tr>
                    <td style="color:var(--muted)">${medal}${i+1}</td>
                    <td style="color:var(--blue)">#${r.work_id}</td>
                    <td style="color:${pnlColor};font-weight:600">$${fmt(r.pnl, 2)}</td>
                    <td>${r.trades}</td>
                    <td>${(r.win_rate * 100).toFixed(1)}%</td>
                    <td>${r.sharpe_ratio ? fmt(r.sharpe_ratio, 2) : '-'}</td>
                    <td style="color:var(--yellow)">${ddVal}</td>
                    <td style="font-size:11px;color:var(--muted)">${(()=>{const w=r.worker_id||'';const b=w.replace(/_W\d+$/,'').replace(/_Darwin$|_Linux$|_Windows$/,'').replace('.local','');const m=w.match(/_W(\d+)$/);return(b+(m?' W'+m[1]:''))||w;})()} </td>
                </tr>`;
            }).join('');
        }

        // ── Asset stats table ──
        const assetsBody = document.getElementById('assets-body');
        const assetStats = dash.asset_stats || [];
        if (assetStats.length === 0) {
            assetsBody.innerHTML = '<tr><td colspan="9" style="color:var(--muted);text-align:center;padding:20px">Sin datos de activos</td></tr>';
        } else {
            assetsBody.innerHTML = assetStats.map(a => {
                const catBadge = a.category === 'Futures'
                    ? '<span class="badge badge-yellow">Futures</span>'
                    : '<span class="badge badge-blue">Spot</span>';
                const avgPnlColor = a.avg_pnl >= 0 ? 'var(--green)' : 'var(--red)';
                const maxPnlColor = a.max_pnl >= 0 ? 'var(--green)' : 'var(--red)';
                const shortFile = a.data_file.length > 25 ? a.data_file.substring(0, 22) + '...' : a.data_file;
                return `<tr>
                    <td style="font-weight:600">${a.asset}</td>
                    <td>${catBadge}</td>
                    <td style="font-size:11px;color:var(--muted)" title="${a.data_file}">${shortFile}</td>
                    <td>${a.total_wus}</td>
                    <td style="color:var(--green)">${a.completed}</td>
                    <td style="color:${avgPnlColor}">$${fmt(a.avg_pnl, 2)}</td>
                    <td style="color:${maxPnlColor};font-weight:600">$${fmt(a.max_pnl, 2)}</td>
                    <td>${(a.total_trades || 0).toLocaleString()}</td>
                    <td style="color:var(--muted)">${fmt(a.total_time || 0, 1)}s</td>
                </tr>`;
            }).join('');
        }

        // ── Capital summary ──
        const totalResults = perf.total_results || 0;
        const simulatedCapital = perf.simulated_capital || (totalResults * 500);
        const totalComputeTime = perf.total_compute_time || 0;
        const computeHours = totalComputeTime / 3600;

        document.getElementById('cap-total-tests').textContent = totalResults.toLocaleString();
        document.getElementById('cap-simulated').textContent = '$' + fmt(simulatedCapital, 0);
        document.getElementById('cap-compute-time').textContent = fmt(totalComputeTime, 0) + 's';
        document.getElementById('cap-compute-hours').textContent = fmt(computeHours, 1) + ' horas';

        document.getElementById('last-update').textContent =
            'Última actualización: ' + new Date().toLocaleTimeString('es-ES');

    } catch (err) {
        console.error('Dashboard error:', err);
        document.getElementById('status-dot').className = 'status-dot offline';
    }
}

// ── Clock ────────────────────────────────────────────────────────
function tickClock() {
    document.getElementById('live-clock').textContent =
        new Date().toLocaleTimeString('es-ES');
}

// ── Init ─────────────────────────────────────────────────────────
initChart();
tickClock();
setInterval(tickClock, 1000);
updateDashboard();
setInterval(updateDashboard, 10000);
</script>
</body>
</html>
"""

# ============================================================================
# INITIALIZATION
# ============================================================================

def create_test_work_units():
    """Crea work units de prueba para testing"""
    test_configs = [
        {
            'population_size': 30,
            'generations': 20,
            'risk_level': 'LOW',
            'test': True
        },
        {
            'population_size': 40,
            'generations': 25,
            'risk_level': 'MEDIUM',
            'test': True
        },
        {
            'population_size': 50,
            'generations': 15,
            'risk_level': 'HIGH',
            'test': True
        }
    ]

    ids = create_work_units(test_configs)
    print(f"✅ {len(ids)} work units de prueba creados: {ids}")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🧬 COORDINATOR - Sistema Distribuido de Strategy Mining")
    print("="*80 + "\n")

    # Inicializar base de datos
    if not os.path.exists(DATABASE):
        print("🔧 Inicializando base de datos...")
        init_db()

        # Crear work units de prueba
        print("\n🧪 Creando work units de prueba...")
        create_test_work_units()
    else:
        print("✅ Base de datos existente encontrada")

    # Iniciar thread de auto-creación de WUs
    if AUTO_CREATE_ENABLED:
        auto_thread = threading.Thread(target=auto_create_work_units, daemon=True)
        auto_thread.start()
        print(f"🔄 Auto-creación de WUs activada (mínimo {AUTO_CREATE_MIN_PENDING} pendientes)")

    print("\n" + "="*80)
    print("🚀 COORDINATOR INICIADO")
    print("="*80)
    print(f"\n📡 Dashboard: http://localhost:5001")
    print(f"📡 API Status: http://localhost:5001/api/status")
    print(f"📡 API Get Work: http://localhost:5001/api/get_work?worker_id=XXX")
    print(f"📡 API Submit: POST http://localhost:5001/api/submit_result")
    print("\nPresiona Ctrl+C para detener\n")

    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=5001, debug=False)
