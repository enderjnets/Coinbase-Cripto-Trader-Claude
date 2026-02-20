#!/usr/bin/env python3
"""
COORDINADOR SEGURO - Dashboard corregido
"""

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import time
import json
import os
from datetime import datetime
from threading import Lock

app = Flask(__name__)

db_lock = Lock()
DATABASE = 'coordinator.db'

# ═══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════

def get_worker_friendly_name(worker_id):
    wid = worker_id
    instance = ""
    
    if "_W" in wid:
        parts = wid.rsplit("_W", 1)
        wid = parts[0]
        instance = parts[1] if len(parts) > 1 else ""
    elif "_" in wid:
        parts = wid.rsplit("_", 1)
        wid = parts[0]
        instance = parts[1] if len(parts) > 1 else ""
    
    wid_lower = wid.lower()
    
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
        if "dorada" in wid_lower:
            machine = "Asus Dorada"
            emoji = "🌐"
        else:
            machine = "Linux"
            emoji = "🐧"
    else:
        machine = wid.split('.')[0] if '.' in wid else wid
        emoji = "🖥️"
    
    if instance and instance.isdigit():
        name = f"{emoji} {machine} #{instance}"
    else:
        name = f"{emoji} {machine}"
    
    return name

def get_worker_platform(worker_id):
    wid = worker_id.lower()
    if "darwin" in wid or "macos" in wid:
        return "macOS"
    elif "linux" in wid:
        return "Linux"
    elif "windows" in wid:
        return "Windows"
    return "Unknown"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def api_status():
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total_work = c.fetchone()['total']
    
    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed_work = c.fetchone()['completed']
    
    c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending'")
    pending_work = c.fetchone()['pending']
    
    # Workers activos (últimos 10 minutos para ser más permisivo)
    c.execute("""SELECT COUNT(*) as active FROM workers
        WHERE (julianday('now') - last_seen) < (10.0 / 1440.0)""")
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
        'work_units': {'total': total_work, 'completed': completed_work, 'pending': pending_work},
        'workers': {'active': active_workers},
        'best_strategy': {
            'pnl': best['pnl'] if best else 0,
            'trades': best['trades'] if best else 0,
            'win_rate': best['win_rate'] if best else 0,
        } if best else None,
        'timestamp': time.time()
    })

@app.route('/api/workers')
def api_workers():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, last_seen, work_units_completed, total_execution_time FROM workers ORDER BY last_seen DESC")
    
    workers = []
    now = time.time()
    
    for row in c.fetchall():
        last_seen_jd = row['last_seen']
        if last_seen_jd:
            last_seen_unix = (last_seen_jd - 2440587.5) * 86400.0
            minutes_ago = (now - last_seen_unix) / 60.0
            is_alive = minutes_ago < 10  # 10 minutos
        else:
            minutes_ago = 9999
            is_alive = False
        
        workers.append({
            'id': row['id'],
            'friendly_name': get_worker_friendly_name(row['id']),
            'platform': get_worker_platform(row['id']),
            'work_units_completed': row['work_units_completed'],
            'execution_time_hours': round(row['total_execution_time'] / 3600, 1),
            'last_seen_minutes_ago': round(minutes_ago, 1),
            'status': 'active' if is_alive else 'inactive'
        })
    
    conn.close()
    return jsonify({'workers': workers})

@app.route('/api/leaderboard')
def api_leaderboard():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, work_units_completed, total_execution_time, last_seen FROM workers ORDER BY work_units_completed DESC")
    
    leaders = []
    now = time.time()
    
    for row in c.fetchall():
        last_seen_jd = row['last_seen'] if 'last_seen' in row.keys() else None
        if last_seen_jd:
            last_seen_unix = (last_seen_jd - 2440587.5) * 86400.0
            minutes_ago = (now - last_seen_unix) / 60.0
            is_alive = minutes_ago < 10
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

@app.route('/api/results')
def api_results():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""SELECT r.*, w.strategy_params FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.is_canonical = 1 ORDER BY r.pnl DESC""")
    
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
        })
    
    conn.close()
    return jsonify({'results': results})

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD HTML
# ═══════════════════════════════════════════════════════════════════════════════

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Strategy Miner - Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="30">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            text-align: center;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em;
            margin-bottom: 30px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
        }
        .section h2 {
            font-size: 1.5em;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255,255,255,0.2);
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { background: rgba(124, 58, 237, 0.3); font-weight: 600; }
        tr:hover { background: rgba(255,255,255,0.05); }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
        }
        .active { background: linear-gradient(90deg, #10b981, #059669); }
        .inactive { background: rgba(255,255,255,0.15); }
        .positive { color: #10b981; }
        .footer { text-align: center; color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Strategy Miner - Dashboard</h1>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="wu-total">-</div>
                <div>Work Units</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="wu-completed">-</div>
                <div>Completados</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="workers-active">-</div>
                <div>Workers Activos</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="best-pnl">$0</div>
                <div>Best PnL</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 Leaderboard - Top Contributors</h2>
            <table>
                <thead>
                    <tr><th>#</th><th>Máquina</th><th>Plataforma</th><th>Work Units</th><th>Horas</th><th>Estado</th></tr>
                </thead>
                <tbody id="leaderboard"></tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📊 Workers Conectados</h2>
            <table>
                <thead>
                    <tr><th>Máquina</th><th>Plataforma</th><th>Work Units</th><th>Última Actividad</th><th>Estado</th></tr>
                </thead>
                <tbody id="workers"></tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>💰 Mejores Resultados</h2>
            <table>
                <thead>
                    <tr><th>Work</th><th>Máquina</th><th>PnL</th><th>Trades</th><th>Win Rate</th></tr>
                </thead>
                <tbody id="results"></tbody>
            </table>
        </div>
        
        <div class="footer">Actualizado: <span id="time">-</span></div>
    </div>
    
    <script>
        async function update() {
            // Status
            let s = await fetch('/api/status').then(r => r.json());
            document.getElementById('wu-total').textContent = s.work_units.total;
            document.getElementById('wu-completed').textContent = s.work_units.completed;
            document.getElementById('workers-active').textContent = s.workers.active;
            if (s.best_strategy) {
                document.getElementById('best-pnl').textContent = '$' + s.best_strategy.pnl.toFixed(2);
            }
            
            // Leaderboard
            let lb = await fetch('/api/leaderboard').then(r => r.json());
            let lbHtml = '';
            lb.leaderboard.slice(0, 15).forEach((w, i) => {
                let emoji = w.friendly_name.split(' ')[0];
                let name = w.friendly_name.substring(2);
                lbHtml += `<tr>
                    <td>${i+1}</td>
                    <td>${emoji} <b>${name}</b></td>
                    <td>${w.platform}</td>
                    <td><b>${w.work_units}</b></td>
                    <td>${w.execution_time_hours}h</td>
                    <td><span class="badge ${w.status}">${w.status}</span></td>
                </tr>`;
            });
            document.getElementById('leaderboard').innerHTML = lbHtml;
            
            // Workers activos
            let ws = await fetch('/api/workers').then(r => r.json());
            let wsHtml = '';
            ws.workers.filter(w => w.status === 'active').forEach(w => {
                let emoji = w.friendly_name.split(' ')[0];
                let name = w.friendly_name.substring(2);
                wsHtml += `<tr>
                    <td>${emoji} <b>${name}</b></td>
                    <td>${w.platform}</td>
                    <td>${w.work_units_completed}</td>
                    <td>${w.last_seen_minutes_ago < 1 ? 'Ahora' : w.last_seen_minutes_ago.toFixed(0) + ' min'}</td>
                    <td><span class="badge active">Activo</span></td>
                </tr>`;
            });
            document.getElementById('workers').innerHTML = wsHtml || '<tr><td colspan="5">Cargando...</td></tr>';
            
            // Results
            let rs = await fetch('/api/results').then(r => r.json());
            let rsHtml = '';
            rs.results.slice(0, 10).forEach(r => {
                let emoji = r.worker_friendly_name.split(' ')[0];
                let name = r.worker_friendly_name.substring(2);
                rsHtml += `<tr>
                    <td>#${r.work_id}</td>
                    <td>${emoji} ${name}</td>
                    <td class="${r.pnl >= 0 ? 'positive'}">$${r.pnl.toFixed(2)}</td>
                    <td>${r.trades}</td>
                    <td>${(r.win_rate * 100).toFixed(0)}%</td>
                </tr>`;
            });
            document.getElementById('results').innerHTML = rsHtml;
            
            document.getElementById('time').textContent = new Date().toLocaleTimeString();
        }
        
        update();
        setInterval(update, 30000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("🧬 Coordinator Dashboard Iniciado")
    print("http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
