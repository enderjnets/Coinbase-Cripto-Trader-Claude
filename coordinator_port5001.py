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

from flask import Flask, request, jsonify, render_template_string, send_from_directory, send_file
import sqlite3
import time
import json
import os
from datetime import datetime
from threading import Lock

app = Flask(__name__, static_folder='static')

# ============================================================================
# STATIC FILES & MOBILE DASHBOARD
# ============================================================================

@app.route('/dashboard')
def mobile_dashboard():
    """Serve the mobile-friendly dashboard PWA"""
    return send_file('static/dashboard.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (icons, manifest, service worker)"""
    return send_from_directory('static', filename)

# Lock para acceso thread-safe a la base de datos
db_lock = Lock()

# Configuración
DATABASE = 'coordinator.db'
REDUNDANCY_FACTOR = 2  # Cada work unit se envía a 2 workers
VALIDATION_THRESHOLD = 0.9  # 90% de similitud para considerar válido

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

    # Tabla de work units
    c.execute('''CREATE TABLE IF NOT EXISTS work_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_params TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at REAL DEFAULT (julianday('now')),
        replicas_needed INTEGER DEFAULT 2,
        replicas_completed INTEGER DEFAULT 0,
        replicas_assigned INTEGER DEFAULT 0,
        canonical_result_id INTEGER DEFAULT NULL
    )''')

    # Tabla de resultados
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
        submitted_at REAL DEFAULT (julianday('now')),
        validated BOOLEAN DEFAULT 0,
        is_canonical BOOLEAN DEFAULT 0,
        FOREIGN KEY (work_unit_id) REFERENCES work_units (id)
    )''')

    # Tabla de workers
    c.execute('''CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY,
        hostname TEXT,
        platform TEXT,
        last_seen REAL DEFAULT (julianday('now')),
        work_units_completed INTEGER DEFAULT 0,
        total_execution_time REAL DEFAULT 0,
        status TEXT DEFAULT 'active'
    )''')

    # Tabla de estadísticas globales
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Migration: add replicas_assigned if missing (for existing databases)
    try:
        c.execute("SELECT replicas_assigned FROM work_units LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE work_units ADD COLUMN replicas_assigned INTEGER DEFAULT 0")
        print("  📦 Migration: added replicas_assigned column")

    conn.commit()
    conn.close()

    print("✅ Base de datos inicializada")

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
    Obtiene un work unit pendiente o que necesita más réplicas.
    Usa replicas_assigned para evitar que múltiples workers tomen el mismo trabajo.

    Returns:
        Dict con work_unit_id y strategy_params, o None si no hay trabajo
    """
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        # Buscar work units que necesitan más réplicas (usando replicas_assigned)
        c.execute("""SELECT id, strategy_params, replicas_needed, replicas_assigned
            FROM work_units
            WHERE replicas_assigned < replicas_needed
            AND status != 'completed'
            ORDER BY created_at ASC
            LIMIT 1""")

        row = c.fetchone()

        if row:
            work_id = row['id']
            replica_num = row['replicas_assigned'] + 1

            # Incrementar replicas_assigned INMEDIATAMENTE para evitar race conditions
            c.execute("""UPDATE work_units
                SET replicas_assigned = replicas_assigned + 1,
                    status = 'in_progress'
                WHERE id = ?""", (work_id,))
            conn.commit()
            conn.close()

            return {
                'work_id': work_id,
                'strategy_params': json.loads(row['strategy_params']),
                'replica_number': replica_num,
                'replicas_needed': row['replicas_needed']
            }

        conn.close()
        return None

def mark_work_assigned(work_id):
    """Marca un work unit como asignado (ya se hace en get_pending_work)"""
    # Ya no necesario - replicas_assigned se incrementa en get_pending_work
    pass

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
    Valida un work unit comparando todas sus réplicas
    Marca el resultado canónico si hay consenso

    Args:
        work_id: ID del work unit a validar

    Returns:
        True si se validó exitosamente, False si necesita más réplicas
    """
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        # Obtener todas las réplicas de este work unit
        c.execute("""SELECT * FROM results
            WHERE work_unit_id = ?""", (work_id,))

        results = c.fetchall()

        # Verificar si tenemos suficientes réplicas
        c.execute("""SELECT replicas_needed FROM work_units WHERE id = ?""",
                  (work_id,))
        replicas_needed = c.fetchone()['replicas_needed']

        if len(results) < replicas_needed:
            conn.close()
            return False  # Necesita más réplicas

        # Comparar resultados para encontrar consenso
        consensus_groups = []

        for i, r1 in enumerate(results):
            matched = False

            # Buscar en grupos existentes
            for group in consensus_groups:
                reference = results[group[0]]

                # Comparar métricas clave
                pnl_match = fuzzy_compare(r1['pnl'], reference['pnl'], 0.05)
                trades_match = r1['trades'] == reference['trades']

                if pnl_match and trades_match:
                    group.append(i)
                    matched = True
                    break

            if not matched:
                consensus_groups.append([i])

        # Encontrar el grupo más grande (consenso)
        if consensus_groups:
            largest_group = max(consensus_groups, key=len)
            consensus_size = len(largest_group) / len(results)

            if consensus_size >= VALIDATION_THRESHOLD:
                # Hay consenso - marcar resultado canónico
                canonical_idx = largest_group[0]
                canonical_result = results[canonical_idx]

                c.execute("""UPDATE results
                    SET is_canonical = 1, validated = 1
                    WHERE id = ?""", (canonical_result['id'],))

                # Marcar otros resultados del grupo como validados
                for idx in largest_group:
                    if idx != canonical_idx:
                        c.execute("""UPDATE results
                            SET validated = 1
                            WHERE id = ?""", (results[idx]['id'],))

                # Actualizar work unit
                c.execute("""UPDATE work_units
                    SET status = 'completed', canonical_result_id = ?
                    WHERE id = ?""", (canonical_result['id'], work_id))

                conn.commit()
                conn.close()

                print(f"✅ Work unit {work_id} validado - Consenso: {consensus_size*100:.0f}%")
                return True
            else:
                # No hay consenso suficiente - enviar más réplicas
                c.execute("""UPDATE work_units
                    SET replicas_needed = replicas_needed + 1
                    WHERE id = ?""", (work_id,))

                conn.commit()
                conn.close()

                print(f"⚠️  Work unit {work_id} - Sin consenso, solicitando réplica adicional")
                return False

        conn.close()
        return False

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Dashboard web principal"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status', methods=['GET'])
def api_status():
    """Obtiene estadísticas generales del sistema"""
    conn = get_db_connection()
    c = conn.cursor()

    # Work units
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total_work = c.fetchone()['total']

    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed_work = c.fetchone()['completed']

    c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending'")
    pending_work = c.fetchone()['pending']

    # Workers
    # Workers active only if seen within last 5 minutes
    c.execute("""SELECT COUNT(*) as active FROM workers
        WHERE status='active'
        AND (julianday('now') - last_seen) < (5.0 / 1440.0)""")
    active_workers = c.fetchone()['active']

    # Mejor estrategia: prefer canonical, fallback to best overall
    c.execute("""SELECT r.*, w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1 AND NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15)
        ORDER BY r.pnl DESC
        LIMIT 1""")
    best = c.fetchone()

    if not best:
        c.execute("""SELECT r.*, w.strategy_params
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl > 0 AND NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15)
            ORDER BY r.pnl DESC
            LIMIT 1""")
        best = c.fetchone()

    conn.close()

    return jsonify({
        'work_units': {
            'total': total_work,
            'completed': completed_work,
            'pending': pending_work,
            'in_progress': total_work - completed_work - pending_work
        },
        'workers': {
            'active': active_workers
        },
        'best_strategy': {
            'pnl': best['pnl'] if best else 0,
            'trades': best['trades'] if best else 0,
            'win_rate': best['win_rate'] if best else 0,
            'is_canonical': bool(best['is_canonical']) if best else False
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

        c.execute("""INSERT OR REPLACE INTO workers
            (id, hostname, platform, last_seen, work_units_completed, total_execution_time, status)
            VALUES (?, ?, ?, julianday('now'),
                COALESCE((SELECT work_units_completed FROM workers WHERE id = ?), 0),
                COALESCE((SELECT total_execution_time FROM workers WHERE id = ?), 0),
                'active')""",
            (worker_id, request.headers.get('Host', 'unknown'),
             request.headers.get('User-Agent', 'unknown'),
             worker_id, worker_id))

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

        c.execute("""INSERT INTO results
            (work_unit_id, worker_id, pnl, trades, win_rate,
             sharpe_ratio, max_drawdown, execution_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data['work_id'], data['worker_id'],
             data.get('pnl', 0), data.get('trades', 0),
             data.get('win_rate', 0), data.get('sharpe_ratio', 0),
             data.get('max_drawdown', 0), data.get('execution_time', 0)))

        # Incrementar contador de réplicas completadas
        c.execute("""UPDATE work_units
            SET replicas_completed = replicas_completed + 1
            WHERE id = ?""", (data['work_id'],))

        # Actualizar estadísticas del worker
        c.execute("""UPDATE workers
            SET work_units_completed = work_units_completed + 1,
                total_execution_time = total_execution_time + ?,
                last_seen = julianday('now')
            WHERE id = ?""",
            (data.get('execution_time', 0), data['worker_id']))

        conn.commit()
        conn.close()

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

    workers = []
    for row in c.fetchall():
        last_seen_jd = row['last_seen']
        if last_seen_jd:
            last_seen_unix = (last_seen_jd - 2440587.5) * 86400.0
            from datetime import datetime as dt
            last_seen_str = dt.fromtimestamp(last_seen_unix).strftime('%Y-%m-%d %H:%M:%S')
            minutes_ago = (time.time() - last_seen_unix) / 60.0
            is_alive = minutes_ago < 5.0
        else:
            last_seen_str = 'Never'
            minutes_ago = 9999
            is_alive = False

        workers.append({
            'id': row['id'],
            'hostname': row['hostname'],
            'platform': row['platform'],
            'last_seen': last_seen_str,
            'last_seen_minutes_ago': round(minutes_ago, 1),
            'work_units_completed': row['work_units_completed'],
            'total_execution_time': row['total_execution_time'],
            'status': 'active' if is_alive else 'inactive'
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
        WHERE r.is_canonical = 1 AND NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15)
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
            'strategy_params': json.loads(row['strategy_params'])
        })

    conn.close()

    return jsonify({'results': results})

@app.route('/api/results/all', methods=['GET'])
def api_results_all():
    """Lista TODOS los resultados (no solo canónicos) - útil para debugging y monitoreo"""
    conn = get_db_connection()
    c = conn.cursor()

    # Get limit from query params (default 100)
    limit = request.args.get('limit', 100, type=int)

    c.execute("""SELECT r.*, w.strategy_params
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        ORDER BY r.id DESC
        LIMIT ?""", (limit,))

    results = []
    for row in c.fetchall():
        results.append({
            'work_unit_id': row['work_unit_id'],
            'worker_id': row['worker_id'],
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe_ratio': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'is_canonical': row['is_canonical'],
            'submitted_at': row['submitted_at'],
            'strategy_params': json.loads(row['strategy_params'])
        })

    conn.close()

    return jsonify(results)

# ============================================================================
# DASHBOARD STATS (consolidated endpoint for Streamlit charts)
# ============================================================================

def _get_short_name(worker_id):
    """Convert worker_id to short display name for charts"""
    instance = ""
    if "_W" in worker_id:
        instance = worker_id.split("_W")[-1]
    if "MacBook-Pro" in worker_id or "macbook-pro" in worker_id.lower():
        return f"MacPro W{instance}" if instance else "MacPro"
    elif "MacBook-Air" in worker_id or "macbook-air" in worker_id.lower():
        return f"Air W{instance}" if instance else "Air"
    elif "rog" in worker_id.lower() or "Linux" in worker_id:
        return f"Linux W{instance}" if instance else "Linux"
    return worker_id[:20]

def _get_machine_name(worker_id):
    """Derive machine name from worker_id"""
    wid = worker_id.lower()
    if "macbook-pro" in wid or "macbookpro" in wid:
        return "MacBook Pro"
    elif "macbook-air" in wid or "macbookair" in wid:
        return "MacBook Air"
    elif "rog" in wid or "linux" in wid:
        return "Linux ROG"
    return "Otro"

@app.route('/api/dashboard_stats', methods=['GET'])
def api_dashboard_stats():
    """Consolidated endpoint for Streamlit dashboard charts"""
    conn = get_db_connection()
    c = conn.cursor()

    # --- Work Units ---
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total_work = c.fetchone()['total']
    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed_work = c.fetchone()['completed']
    c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending'")
    pending_work = c.fetchone()['pending']
    in_progress_work = total_work - completed_work - pending_work

    # --- Workers ---
    c.execute("""SELECT COUNT(*) as active FROM workers
        WHERE status='active'
        AND (julianday('now') - last_seen) < (5.0 / 1440.0)""")
    active_workers = c.fetchone()['active']
    c.execute("SELECT COUNT(*) as total FROM workers")
    total_workers = c.fetchone()['total']

    # --- Best Strategy (two-pass: canonical first, then fallback) ---
    c.execute("""SELECT r.*, w.strategy_params
        FROM results r JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1 AND NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15) ORDER BY r.pnl DESC LIMIT 1""")
    best = c.fetchone()
    if not best:
        c.execute("""SELECT r.*, w.strategy_params
            FROM results r JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl > 0 AND NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15) ORDER BY r.pnl DESC LIMIT 1""")
        best = c.fetchone()

    best_strategy = None
    if best:
        # Parse strategy params
        try:
            params = json.loads(best['strategy_params']) if best['strategy_params'] else {}
        except:
            params = {}

        # Parse strategy genome
        try:
            genome_str = best['strategy_genome'] if 'strategy_genome' in best.keys() else None
            genome = json.loads(genome_str) if genome_str else None
        except:
            genome = None

        # Convert submitted_at from Julian Day to unix timestamp
        submitted_unix = None
        try:
            if best['submitted_at']:
                submitted_unix = (best['submitted_at'] - 2440587.5) * 86400.0
        except:
            pass

        # Get execution_time safely
        try:
            exec_time = best['execution_time'] if 'execution_time' in best.keys() else 0
        except:
            exec_time = 0

        best_strategy = {
            'pnl': best['pnl'],
            'trades': best['trades'],
            'win_rate': best['win_rate'],
            'sharpe_ratio': best['sharpe_ratio'],
            'max_drawdown': best['max_drawdown'],
            'worker_id': best['worker_id'],
            'work_unit_id': best['work_unit_id'],
            'is_canonical': bool(best['is_canonical']),
            'execution_time': exec_time,
            'submitted_at_unix': submitted_unix,
            # Backtest parameters
            'initial_capital': 10000.0,
            'data_file': params.get('data_file', 'N/A'),
            'max_candles': params.get('max_candles', 0),
            'generations': params.get('generations', 0),
            'population_size': params.get('population_size', 0),
            'risk_level': params.get('risk_level', 'N/A'),
            # Strategy genome (trading rules)
            'genome': genome
        }

    # --- PnL Timeline (all results with converted timestamps) ---
    c.execute("""SELECT
        (submitted_at - 2440587.5) * 86400.0 as submitted_at_unix,
        pnl, worker_id, work_unit_id, is_canonical
        FROM results
        WHERE pnl > -9000
        ORDER BY submitted_at ASC""")
    pnl_timeline = []
    for row in c.fetchall():
        pnl_timeline.append({
            'submitted_at_unix': row['submitted_at_unix'],
            'pnl': row['pnl'],
            'worker_id': row['worker_id'],
            'work_unit_id': row['work_unit_id'],
            'is_canonical': bool(row['is_canonical'])
        })

    # --- PnL Distribution ---
    pnl_distribution = [r['pnl'] for r in pnl_timeline]

    # --- Worker Stats (aggregated from workers + results) ---
    c.execute("""SELECT
        w.id as worker_id, w.hostname, w.platform,
        w.work_units_completed, w.total_execution_time,
        (julianday('now') - w.last_seen) < (5.0 / 1440.0) as is_alive,
        (w.last_seen - 2440587.5) * 86400.0 as last_seen_unix,
        COUNT(r.id) as result_count,
        AVG(CASE WHEN r.pnl > -9000 THEN r.pnl END) as avg_pnl,
        MAX(r.pnl) as max_pnl
        FROM workers w
        LEFT JOIN results r ON w.id = r.worker_id
        GROUP BY w.id
        ORDER BY w.work_units_completed DESC""")
    worker_stats = []
    for row in c.fetchall():
        wid = row['worker_id']
        wuc = row['work_units_completed'] or 0
        tet = row['total_execution_time'] or 0
        worker_stats.append({
            'worker_id': wid,
            'short_name': _get_short_name(wid),
            'machine': _get_machine_name(wid),
            'work_units_completed': wuc,
            'total_execution_time': tet,
            'avg_execution_time': tet / wuc if wuc > 0 else 0,
            'result_count': row['result_count'] or 0,
            'avg_pnl': row['avg_pnl'] or 0,
            'max_pnl': row['max_pnl'] or 0,
            'status': 'active' if row['is_alive'] else 'inactive',
            'last_seen_unix': row['last_seen_unix']
        })

    # --- Completion Timeline (results per hour) ---
    c.execute("""SELECT
        CAST((submitted_at - 2440587.5) * 24 AS INTEGER) as hour_bin,
        COUNT(*) as count
        FROM results
        GROUP BY hour_bin
        ORDER BY hour_bin""")
    completion_timeline = []
    for row in c.fetchall():
        completion_timeline.append({
            'hour_unix': row['hour_bin'] * 3600.0,
            'count': row['count']
        })

    # --- Performance Aggregates ---
    c.execute("""SELECT
        COUNT(*) as total_results,
        AVG(execution_time) as avg_execution_time,
        SUM(execution_time) as total_compute_time,
        SUM(CASE WHEN pnl > 0 AND pnl < 9000 THEN 1 ELSE 0 END) as positive_pnl_count,
        SUM(CASE WHEN pnl <= 0 AND pnl > -9000 THEN 1 ELSE 0 END) as negative_pnl_count,
        MAX(pnl) as best_pnl,
        MAX(sharpe_ratio) as best_sharpe
        FROM results""")
    perf = c.fetchone()

    # Calculate results per hour
    c.execute("""SELECT
        MIN((submitted_at - 2440587.5) * 86400.0) as first_ts,
        MAX((submitted_at - 2440587.5) * 86400.0) as last_ts
        FROM results""")
    ts_range = c.fetchone()
    time_span_hours = 0
    if ts_range and ts_range['first_ts'] and ts_range['last_ts']:
        time_span_hours = (ts_range['last_ts'] - ts_range['first_ts']) / 3600.0

    performance = {
        'total_results': perf['total_results'] or 0,
        'avg_execution_time': perf['avg_execution_time'] or 0,
        'total_compute_time': perf['total_compute_time'] or 0,
        'results_per_hour': (perf['total_results'] or 0) / time_span_hours if time_span_hours > 0 else 0,
        'positive_pnl_count': perf['positive_pnl_count'] or 0,
        'negative_pnl_count': perf['negative_pnl_count'] or 0,
        'best_pnl': perf['best_pnl'] or 0,
        'best_sharpe': perf['best_sharpe'] or 0
    }

    conn.close()

    return jsonify({
        'work_units': {
            'total': total_work,
            'completed': completed_work,
            'in_progress': in_progress_work,
            'pending': pending_work
        },
        'workers': {
            'active': active_workers,
            'total_registered': total_workers
        },
        'best_strategy': best_strategy,
        'pnl_timeline': pnl_timeline,
        'pnl_distribution': pnl_distribution,
        'worker_stats': worker_stats,
        'completion_timeline': completion_timeline,
        'performance': performance,
        'timestamp': time.time()
    })

# ============================================================================
# DASHBOARD HTML
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Strategy Miner - Coordinator Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="10">
    <style>
        body {
            font-family: 'Monaco', 'Courier New', monospace;
            background: #1a1a1a;
            color: #0f0;
            padding: 20px;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #0f0;
            padding-bottom: 10px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-box {
            background: #0a0a0a;
            border: 2px solid #0f0;
            padding: 20px;
            text-align: center;
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            color: #0f0;
        }
        .stat-label {
            font-size: 14px;
            color: #0f0;
            opacity: 0.7;
            margin-top: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #0f0;
            padding: 10px;
            text-align: left;
        }
        th {
            background: #0f0;
            color: #000;
        }
        .timestamp {
            text-align: center;
            margin-top: 20px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 STRATEGY MINER - COORDINATOR DASHBOARD</h1>

        <div class="stats" id="stats">
            <div class="stat-box">
                <div class="stat-value" id="total-work">-</div>
                <div class="stat-label">Total Work Units</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="completed-work">-</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="active-workers">-</div>
                <div class="stat-label">Active Workers</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="best-pnl">$-</div>
                <div class="stat-label">Best PnL</div>
            </div>
        </div>

        <h2>📊 Top Results</h2>
        <table id="results-table">
            <thead>
                <tr>
                    <th>Work ID</th>
                    <th>PnL</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>Sharpe</th>
                    <th>Worker</th>
                </tr>
            </thead>
            <tbody id="results-body">
                <tr><td colspan="6">Loading...</td></tr>
            </tbody>
        </table>

        <div class="timestamp" id="timestamp">Last update: -</div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                // Get status
                const statusResp = await fetch('/api/status');
                const status = await statusResp.json();

                document.getElementById('total-work').textContent = status.work_units.total;
                document.getElementById('completed-work').textContent = status.work_units.completed;
                document.getElementById('active-workers').textContent = status.workers.active;

                if (status.best_strategy) {
                    document.getElementById('best-pnl').textContent =
                        '$' + status.best_strategy.pnl.toFixed(2);
                }

                // Get results
                const resultsResp = await fetch('/api/results');
                const resultsData = await resultsResp.json();

                const tbody = document.getElementById('results-body');
                tbody.innerHTML = '';

                if (resultsData.results.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6">No results yet</td></tr>';
                } else {
                    resultsData.results.slice(0, 10).forEach(r => {
                        const row = tbody.insertRow();
                        row.insertCell(0).textContent = r.work_id;
                        row.insertCell(1).textContent = '$' + r.pnl.toFixed(2);
                        row.insertCell(2).textContent = r.trades;
                        row.insertCell(3).textContent = (r.win_rate * 100).toFixed(1) + '%';
                        row.insertCell(4).textContent = r.sharpe_ratio ? r.sharpe_ratio.toFixed(2) : '-';
                        row.insertCell(5).textContent = r.worker_id;
                    });
                }

                document.getElementById('timestamp').textContent =
                    'Last update: ' + new Date().toLocaleTimeString();

            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }

        // Update every 10 seconds
        setInterval(updateDashboard, 10000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ============================================================================
# INITIALIZATION
# ============================================================================

def create_test_work_units():
    """Crea work units PEQUEÑOS de prueba para testing rápido"""
    test_configs = [
        {
            'population_size': 5,
            'generations': 3,
            'risk_level': 'LOW',
            'test': True
        },
        {
            'population_size': 5,
            'generations': 3,
            'risk_level': 'MEDIUM',
            'test': True
        }
    ]

    ids = create_work_units(test_configs)
    print(f"✅ {len(ids)} work units de PRUEBA RÁPIDA creados: {ids}")
    print(f"⚡ Configuración: 5 población × 3 generaciones (~1-2 min cada uno)")

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

    print("\n" + "="*80)
    print("🚀 COORDINATOR INICIADO")
    print("="*80)
    print(f"\n📡 Dashboard: http://localhost:5001")
    print(f"📡 API Status: http://localhost:5001/api/status")
    print(f"📡 API Get Work: http://localhost:5001/api/get_work?worker_id=XXX")
    print(f"📡 API Submit: POST http://localhost:5001/api/submit_result")
    print("\nPresiona Ctrl+C para detener\n")

    # Iniciar servidor Flask
    app.run(host="0.0.0.0", port=5001, debug=False)
