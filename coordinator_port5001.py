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
from datetime import datetime
from threading import Lock

app = Flask(__name__)

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
    """Marca un work unit como asignado"""
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute("""UPDATE work_units
            SET status = 'assigned'
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

        # Seleccionar el mejor resultado válido como canónico
        # Filtramos resultados imposibles: PnL > 5000 con < 10 trades es bug del backtester
        PNL_MAX = 5000
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
            'in_progress': total_work - completed_work - pending_work
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

        # First try to update existing worker
        c.execute("UPDATE workers SET last_seen = strftime('%s', 'now'), status = 'active' WHERE id = ?", (worker_id,))
        
        # If no row was updated (new worker), insert
        if c.rowcount == 0:
            c.execute("""INSERT INTO workers
                (id, hostname, platform, last_seen, work_units_completed, total_execution_time, status)
                VALUES (?, ?, ?, julianday('now'), 0, 0, 'active')""",
                (worker_id, request.headers.get('Host', 'unknown'),
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
                last_seen = strftime('%s', 'now')
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
        workers.append({
            'id': row['id'],
            'hostname': row['hostname'],
            'platform': row['platform'],
            'last_seen': row['last_seen'],
            'work_units_completed': row['work_units_completed'],
            'total_execution_time': row['total_execution_time'],
            'status': row['status']
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
            'submitted_at': row['submitted_at'],
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
        # Unix epoch = julian 2440588
        unix_ts = (row[1] - 2440588) * 86400
        pnl_timeline.append({
            'pnl': row[0], 
            'timestamp': unix_ts,
            'submitted_at_unix': unix_ts,
            'work_unit_id': row[2],
            'worker_id': row[3],
            'is_canonical': bool(row[4])
        })
    
    # Completion timeline - group by hour
    c.execute("""SELECT COUNT(*), submitted_at FROM results 
                 WHERE submitted_at > (julianday('now') - 1) 
                 GROUP BY CAST(submitted_at * 24 AS INT) % 24
                 ORDER BY submitted_at DESC""")
    completion_timeline = [{'hour_unix': (row[1] - 2440588) * 86400, 'count': row[0]} for row in c.fetchall()]
    
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
    
    # Worker performance stats
    c.execute("""SELECT id, hostname, work_units_completed, total_execution_time, 
                         last_seen, status
                  FROM workers ORDER BY work_units_completed DESC""")
    
    worker_stats = []
    for row in c.fetchall():
        # Convert sqlite3.Row to dict for easier access
        row_dict = dict(row)
        
        # last_seen is now stored as Unix timestamp from strftime('%s', 'now')
        last_seen_unix = row_dict.get('last_seen') or 0
        if last_seen_unix > 0:
            now_unix = time.time()
            mins_ago = (now_unix - last_seen_unix) / 60
        else:
            mins_ago = 999
        
        short_name = row_dict['id'].split('_W')[0].split('_')[-1] if '_W' in row_dict['id'] else row_dict['id'][:10]
        
        # Get max_pnl for this worker
        c2 = conn.cursor()
        c2.execute("SELECT MAX(pnl) FROM results WHERE worker_id = ? AND pnl < 5000", (row_dict['id'],))
        max_pnl = c2.fetchone()[0] or 0
        
        worker_stats.append({
            'id': row_dict['id'],
            'short_name': short_name,
            'hostname': row_dict['hostname'],
            'work_units_completed': row_dict['work_units_completed'],
            'total_execution_time': row_dict['total_execution_time'],
            'last_seen': row_dict['last_seen'],
            'last_seen_minutes_ago': mins_ago,
            'status': 'active' if mins_ago < 30 else 'inactive',
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
            'results_per_hour': total_results / max(1, total_compute_time / 3600),
            'avg_execution_time': avg_exec_time,
            'total_compute_time': total_compute_time
        },
        'best_strategy': best_strategy,
        'pnl_distribution': pnl_distribution,
        'pnl_timeline': pnl_timeline,
        'completion_timeline': completion_timeline,
        'worker_stats': worker_stats,
        'timestamp': time.time()
    })

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
        const best = status.best_strategy || dash.best_strategy;
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
                const name = (w.id || '').includes('_W')
                    ? w.id.split('_W').slice(-1)[0] ? w.hostname + ' W' + w.id.split('_W').slice(-1)[0] : w.hostname
                    : (w.short_name || w.hostname || w.id);
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
                    <td style="font-size:11px;color:var(--muted)">${(r.worker_id || '').split('_Darwin_').pop() || r.worker_id}</td>
                </tr>`;
            }).join('');
        }

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

    print("\n" + "="*80)
    print("🚀 COORDINATOR INICIADO")
    print("="*80)
    print(f"\n📡 Dashboard: http://localhost:5000")
    print(f"📡 API Status: http://localhost:5000/api/status")
    print(f"📡 API Get Work: http://localhost:5000/api/get_work?worker_id=XXX")
    print(f"📡 API Submit: POST http://localhost:5000/api/submit_result")
    print("\nPresiona Ctrl+C para detener\n")

    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=5001, debug=False)
