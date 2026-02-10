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
    c.execute("SELECT COUNT(*) as active FROM workers WHERE status='active'")
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
    app.run(host='0.0.0.0', port=5000, debug=False)
