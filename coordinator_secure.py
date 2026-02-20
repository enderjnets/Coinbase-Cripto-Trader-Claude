#!/usr/bin/env python3
"""
COORDINATOR MEJORADO - Dashboard con nombres seguros y ordenados
"""

from flask import Flask, request, jsonify, render_template_string, send_from_directory, send_file
import sqlite3
import time
import json
import os
from datetime import datetime
from threading import Lock

app = Flask(__name__, static_folder='static')

db_lock = Lock()
DATABASE = 'coordinator.db'
REDUNDANCY_FACTOR = 2
VALIDATION_THRESHOLD = 0.9

# ═══════════════════════════════════════════════════════════════════════════════
# UTILIDADES PARA NOMBRES SEGUROS
# ═══════════════════════════════════════════════════════════════════════════════

def get_worker_friendly_name(worker_id):
    """
    Convierte worker_id a nombre amigable y seguro
    Ejemplos:
    - "Enders-MacBook-Pro.local_Darwin_W1" → "💻 MacBook Pro #1"
    - "ender-rog_Linux_W3" → "🔴 Linux ROG #3"
    - "Asus-Dorada_Linux_W2" → "🌐 Asus Dorada #2"
    """
    wid = worker_id
    instance = ""
    
    # Extraer número de instancia
    if "_W" in wid:
        parts = wid.rsplit("_W", 1)
        wid = parts[0]
        instance = parts[1] if len(parts) > 1 else ""
    elif "_" in wid:
        parts = wid.rsplit("_", 1)
        wid = parts[0]
        instance = parts[1] if len(parts) > 1 else ""
    
    wid_lower = wid.lower()
    
    # Determinar máquina y emoji
    if "macbook-pro" in wid_lower or "macbookpro" in wid_lower:
        machine = "MacBook Pro"
        emoji = "💻"
    elif "macbook-air" in wid_lower or "macbookair" in wid_lower:
        machine = "MacBook Air"
        emoji = "🪶"
    elif "asus-dorada" in wid_lower or "asusdorada" in wid_lower:
        machine = "Asus Dorada"
        emoji = "🌐"
    elif "rog" in wid_lower or "kubuntu" in wid_lower:
        machine = "Linux ROG"
        emoji = "🔴"
    elif "linux" in wid_lower:
        # Detectar otros Linux
        if "dorada" in wid_lower:
            machine = "Asus Dorada"
            emoji = "🌐"
        else:
            machine = "Linux"
            emoji = "🐧"
    else:
        machine = wid.split('.')[0] if '.' in wid else wid
        emoji = "🖥️"
    
    # Crear nombre amigable
    if instance and instance.isdigit():
        name = f"{emoji} {machine} #{instance}"
    else:
        name = f"{emoji} {machine}"
    
    return name

def get_worker_platform(worker_id):
    """Obtiene la plataforma del worker"""
    wid = worker_id.lower()
    if "darwin" in wid or "macos" in wid:
        return "macOS"
    elif "linux" in wid:
        return "Linux"
    elif "windows" in wid:
        return "Windows"
    else:
        return "Unknown"

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY,
        hostname TEXT,
        platform TEXT,
        last_seen REAL DEFAULT (julianday('now')),
        work_units_completed INTEGER DEFAULT 0,
        total_execution_time REAL DEFAULT 0,
        status TEXT DEFAULT 'active'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada")

# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """Dashboard web principal"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/secure_workers', methods=['GET'])
def api_secure_workers():
    """Lista workers con nombres seguros (sin IPs)"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""SELECT id, last_seen, work_units_completed, total_execution_time, status
        FROM workers ORDER BY last_seen DESC""")
    
    workers = []
    now = time.time()
    
    for row in c.fetchall():
        last_seen_jd = row['last_seen']
        if last_seen_jd:
            last_seen_unix = (last_seen_jd - 2440587.5) * 86400.0
            minutes_ago = (now - last_seen_unix) / 60.0
            is_alive = minutes_ago < 5.0
        else:
            minutes_ago = 9999
            is_alive = False
        
        workers.append({
            'id': row['id'],
            'friendly_name': get_worker_friendly_name(row['id']),
            'platform': get_worker_platform(row['id']),
            'work_units_completed': row['work_units_completed'],
            'status': 'active' if is_alive else 'inactive',
            'last_seen_minutes_ago': round(minutes_ago, 1)
        })
    
    conn.close()
    return jsonify({'workers': workers})

@app.route('/api/secure_results', methods=['GET'])
def api_secure_results():
    """Resultados con nombres de workers seguros"""
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
            'worker_friendly_name': get_worker_friendly_name(row['worker_id']),
            'worker_platform': get_worker_platform(row['worker_id']),
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe_ratio': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'strategy_params': json.loads(row['strategy_params']) if row['strategy_params'] else {}
        })
    
    conn.close()
    return jsonify({'results': results})

@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    """Top contributors ordenado por work units completados"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("""SELECT id, work_units_completed, total_execution_time, status
        FROM workers
        ORDER BY work_units_completed DESC""")
    
    leaders = []
    now = time.time()
    
    for row in c.fetchall():
        last_seen_jd = row['last_seen'] if 'last_seen' in row.keys() else None
        if last_seen_jd:
            last_seen_unix = (last_seen_jd - 2440587.5) * 86400.0
            minutes_ago = (now - last_seen_unix) / 60.0
            is_alive = minutes_ago < 5.0
        else:
            is_alive = False
        
        leaders.append({
            'id': row['id'],
            'friendly_name': get_worker_friendly_name(row['id']),
            'platform': get_worker_platform(row['id']),
            'work_units': row['work_units_completed'],
            'execution_time_hours': round(row['total_execution_time'] / 3600, 1),
            'status': 'active' if is_alive else 'inactive'
        })
    
    conn.close()
    return jsonify({'leaderboard': leaders})

@app.route('/api/status', methods=['GET'])
def api_status():
    """Estado general del sistema"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total_work = c.fetchone()['total']
    
    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed_work = c.fetchone()['completed']
    
    c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending'")
    pending_work = c.fetchone()['pending']
    
    c.execute("""SELECT COUNT(*) as active FROM workers
        WHERE status='active' AND (julianday('now') - last_seen) < (5.0 / 1440.0)""")
    active_workers = c.fetchone()['active']
    
    c.execute("""SELECT r.*, w.strategy_params FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1 ORDER BY r.pnl DESC LIMIT 1""")
    best = c.fetchone()
    
    if not best:
        c.execute("""SELECT r.*, w.strategy_params FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            WHERE r.pnl > 0 ORDER BY r.pnl DESC LIMIT 1""")
        best = c.fetchone()
    
    conn.close()
    
    return jsonify({
        'work_units': {
            'total': total_work,
            'completed': completed_work,
            'pending': pending_work,
            'in_progress': total_work - completed_work - pending_work
        },
        'workers': {'active': active_workers},
        'best_strategy': {
            'pnl': best['pnl'] if best else 0,
            'trades': best['trades'] if best else 0,
            'win_rate': best['win_rate'] if best else 0,
        } if best else None,
        'timestamp': time.time()
    })

@app.route('/api/get_work', methods=['GET'])
def api_get_work():
    worker_id = request.args.get('worker_id')
    if not worker_id:
        return jsonify({'error': 'worker_id required'}), 400
    
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""INSERT OR REPLACE INTO workers
            (id, hostname, platform, last_seen, work_units_completed, total_execution_time, status)
            VALUES (?, ?, ?, julianday('now'),
                COALESCE((SELECT work_units_completed FROM workers WHERE id = ?), 0),
                COALESCE((SELECT total_execution_time FROM workers WHERE id = ?), 0),
                'active')""",
            (worker_id, 'hidden', 'unknown', worker_id, worker_id))
        
        conn.commit()
        conn.close()
    
    work = get_pending_work()
    if work:
        return jsonify(work)
    else:
        return jsonify({'work_id': None, 'message': 'No work available'})

@app.route('/api/submit_result', methods=['POST'])
def api_submit_result():
    data = request.json
    if not data or 'work_id' not in data or 'worker_id' not in data:
        return jsonify({'error': 'work_id and worker_id required'}), 400
    
    with db_lock:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""INSERT INTO results
            (work_unit_id, worker_id, pnl, trades, win_rate, sharpe_ratio, max_drawdown, execution_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data['work_id'], data['worker_id'],
             data.get('pnl', 0), data.get('trades', 0),
             data.get('win_rate', 0), data.get('sharpe_ratio', 0),
             data.get('max_drawdown', 0), data.get('execution_time', 0)))
        
        c.execute("""UPDATE work_units SET replicas_completed = replicas_completed + 1 WHERE id = ?""",
            (data['work_id'],))
        
        c.execute("""UPDATE workers SET work_units_completed = work_units_completed + 1,
            total_execution_time = total_execution_time + ?, last_seen = julianday('now')
            WHERE id = ?""", (data.get('execution_time', 0), data['worker_id']))
        
        conn.commit()
        conn.close()
    
    validate_work_unit(data['work_id'])
    return jsonify({'status': 'success'})

# ═══════════════════════════════════════════════════════════════════════════════
# RESULT VALIDATION (simplificado)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_work_unit(work_id):
    pass  # Simplified - usa la función original si necesitas validación completa

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD HTML MEJORADO
# ═══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Strategy Miner - Dashboard Seguro</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
            margin-bottom: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label {
            color: #aaa;
            margin-top: 5px;
            font-size: 0.9em;
        }
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255,255,255,0.2);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th {
            background: rgba(124, 58, 237, 0.3);
            font-weight: 600;
        }
        tr:hover {
            background: rgba(255,255,255,0.05);
        }
        .emoji { font-size: 1.2em; }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
        }
        .badge-active {
            background: linear-gradient(90deg, #10b981, #059669);
        }
        .badge-inactive {
            background: rgba(255,255,255,0.1);
        }
        .machine-name {
            font-weight: 600;
        }
        .platform {
            color: #888;
            font-size: 0.85em;
        }
        .pnl-positive { color: #10b981; }
        .footer {
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Strategy Miner - Dashboard</h1>
        
        <div class="stats-grid" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="wu-total">-</div>
                <div class="stat-label">Work Units</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="wu-completed">-</div>
                <div class="stat-label">Completados</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="workers-active">-</div>
                <div class="stat-label">Workers Activos</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="best-pnl">$0</div>
                <div class="stat-label">Best PnL</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏆 Leaderboard - Top Contributors</h2>
            <table id="leaderboard">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Máquina</th>
                        <th>Plataforma</th>
                        <th>Work Units</th>
                        <th>Tiempo (hrs)</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody id="leaderboard-body">
                    <tr><td colspan="6">Cargando...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 Workers Conectados</h2>
            <table id="workers-table">
                <thead>
                    <tr>
                        <th>Máquina</th>
                        <th>Plataforma</th>
                        <th>Work Units</th>
                        <th>Última Actividad</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody id="workers-body">
                    <tr><td colspan="5">Cargando...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">💰 Mejores Resultados</h2>
            <table id="results-table">
                <thead>
                    <tr>
                        <th>Work ID</th>
                        <th>Máquina</th>
                        <th>PnL</th>
                        <th>Trades</th>
                        <th>Win Rate</th>
                    </tr>
                </thead>
                <tbody id="results-body">
                    <tr><td colspan="5">Cargando...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            Actualizado: <span id="last-update">-</span>
        </div>
    </div>
    
    <script>
        async function updateDashboard() {
            try {
                // Status
                const statusResp = await fetch('/api/status');
                const status = await statusResp.json();
                
                document.getElementById('wu-total').textContent = status.work_units.total;
                document.getElementById('wu-completed').textContent = status.work_units.completed;
                document.getElementById('workers-active').textContent = status.workers.active;
                if (status.best_strategy) {
                    document.getElementById('best-pnl').textContent = '$' + status.best_strategy.pnl.toFixed(2);
                }
                
                // Leaderboard
                const leaderResp = await fetch('/api/leaderboard');
                const leaderData = await leaderResp.json();
                const leaderBody = document.getElementById('leaderboard-body');
                leaderBody.innerHTML = '';
                leaderData.leaderboard.slice(0, 15).forEach((w, i) => {
                    const row = leaderBody.insertRow();
                    row.innerHTML = `
                        <td>${i + 1}</td>
                        <td><span class="emoji">${w.friendly_name.split(' ')[0]}</span> <span class="machine-name">${w.friendly_name.substring(2)}</span></td>
                        <td class="platform">${w.platform}</td>
                        <td><strong>${w.work_units}</strong></td>
                        <td>${w.execution_time_hours}h</td>
                        <td><span class="badge ${w.status === 'active' ? 'badge-active' : 'badge-inactive'}">${w.status}</span></td>
                    `;
                });
                
                // Workers
                const workersResp = await fetch('/api/secure_workers');
                const workersData = await workersResp.json();
                const workersBody = document.getElementById('workers-body');
                workersBody.innerHTML = '';
                workersData.workers.filter(w => w.status === 'active').forEach(w => {
                    const row = workersBody.insertRow();
                    row.innerHTML = `
                        <td><span class="emoji">${w.friendly_name.split(' ')[0]}</span> <span class="machine-name">${w.friendly_name.substring(2)}</span></td>
                        <td class="platform">${w.platform}</td>
                        <td>${w.work_units_completed}</td>
                        <td>${w.last_seen_minutes_ago < 1 ? 'Ahora' : w.last_seen_minutes_ago.toFixed(0) + ' min'}</td>
                        <td><span class="badge badge-active">Activo</span></td>
                    `;
                });
                
                // Results
                const resultsResp = await fetch('/api/secure_results');
                const resultsData = await resultsResp.json();
                const resultsBody = document.getElementById('results-body');
                resultsBody.innerHTML = '';
                resultsData.results.slice(0, 10).forEach(r => {
                    const row = resultsBody.insertRow();
                    const pnlClass = r.pnl >= 0 ? 'pnl-positive' : '';
                    row.innerHTML = `
                        <td>#${r.work_id}</td>
                        <td><span class="emoji">${r.worker_friendly_name.split(' ')[0]}</span> ${r.worker_friendly_name.substring(2)}</td>
                        <td class="${pnlClass}">$${r.pnl.toFixed(2)}</td>
                        <td>${r.trades}</td>
                        <td>${(r.win_rate * 100).toFixed(0)}%</td>
                    `;
                });
                
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        updateDashboard();
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧬 COORDINATOR MEJORADO - Dashboard Seguro")
    print("="*60 + "\n")
    
    if not os.path.exists(DATABASE):
        print("🔧 Inicializando base de datos...")
        init_db()
    else:
        print("✅ Base de datos existente")
    
    print("\n📡 Dashboard: http://localhost:5001")
    print("📡 API Segura: http://localhost:5001/api/secure_workers")
    print("📡 Leaderboard: http://localhost:5001/api/leaderboard")
    print("\nPresiona Ctrl+C para detener\n")
    
    app.run(host="0.0.0.0", port=5001, debug=False)
