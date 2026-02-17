#!/usr/bin/env python3
"""
F1 Racing Dashboard - Premium Design with Machine Contribution
"""

from flask import Flask, jsonify
import sqlite3
import time

app = Flask(__name__)
DATABASE = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏎️ F1 Strategy Racing Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --red: #e10600;
            --green: #00d65b;
            --blue: #00b4d8;
            --yellow: #ffd700;
            --dark: #0a0a0f;
            --dark-lighter: #14141f;
            --dark-card: #1a1a24;
            --gray: #2a2a36;
            --text: #ffffff;
            --text-muted: #888899;
        }
        
        body {
            font-family: 'Rajdhani', sans-serif;
            background: var(--dark);
            color: var(--text);
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(180deg, var(--dark) 0%, var(--dark-lighter) 100%);
            border-bottom: 4px solid var(--red);
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header::after {
            content: '';
            position: absolute;
            bottom: -4px;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, var(--yellow), var(--green), var(--blue), var(--red), transparent);
        }
        
        .logo h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: 3px;
            background: linear-gradient(135deg, var(--text) 0%, var(--red) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header-stats {
            display: flex;
            gap: 40px;
        }
        
        .header-stat {
            text-align: center;
        }
        
        .header-stat-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--green);
            text-shadow: 0 0 20px rgba(0, 214, 91, 0.5);
        }
        
        .header-stat-label {
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(0, 214, 91, 0.15);
            padding: 10px 25px;
            border-radius: 30px;
            border: 1px solid rgba(0, 214, 91, 0.3);
        }
        
        .live-dot {
            width: 10px;
            height: 10px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 1s infinite;
            box-shadow: 0 0 15px var(--green);
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.8; }
        }
        
        .main-container { padding: 30px; max-width: 1800px; margin: 0 auto; }
        
        .gauges-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .gauge-card {
            background: linear-gradient(145deg, var(--dark-card), var(--dark-lighter));
            border-radius: 20px;
            padding: 25px;
            text-align: center;
            border: 1px solid var(--gray);
        }
        
        .gauge-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--red), var(--yellow), var(--green));
        }
        
        .gauge-ring {
            width: 140px;
            height: 140px;
            margin: 0 auto 15px;
            position: relative;
        }
        
        .gauge-ring svg { transform: rotate(-90deg); }
        
        .gauge-ring circle {
            fill: none;
            stroke-width: 10;
        }
        
        .gauge-ring .bg { stroke: var(--gray); }
        .gauge-ring .progress { 
            stroke: url(#gaugeGradient);
            stroke-linecap: round;
            stroke-dasharray: 377;
            stroke-dashoffset: 377;
            transition: stroke-dashoffset 1s ease;
        }
        
        .gauge-center {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        
        .gauge-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
        }
        
        .gauge-label {
            font-size: 0.6rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: var(--dark-card);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--gray);
        }
        
        .card:hover {
            transform: translateY(-5px);
            border-color: var(--blue);
        }
        
        .card-title {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 10px;
        }
        
        .card-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--text) 0%, var(--blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .card-value.green { background: linear-gradient(135deg, var(--green) 0%, #00ff7f 100%); }
        .card-value.yellow { background: linear-gradient(135deg, var(--yellow) 0%, #ff6600 100%); }
        .card-value.red { background: linear-gradient(135deg, var(--red) 0%, #ff6b6b 100%); }
        
        .section {
            background: var(--dark-card);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid var(--gray);
            margin-bottom: 25px;
        }
        
        .section-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 20px;
        }
        
        .machines-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
        }
        
        .machine-card {
            background: linear-gradient(145deg, var(--dark-lighter), rgba(0,0,0,0.4));
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--gray);
        }
        
        .machine-card:hover {
            transform: scale(1.02);
            border-color: var(--green);
        }
        
        .machine-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .machine-icon {
            font-size: 2.5rem;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--dark);
            border-radius: 12px;
        }
        
        .machine-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 15px;
        }
        
        .machine-stat {
            background: rgba(0,0,0,0.3);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
        }
        
        .machine-stat-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            color: var(--blue);
        }
        
        .contribution-bar {
            height: 10px;
            background: var(--gray);
            border-radius: 5px;
            overflow: hidden;
        }
        
        .contribution-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--red), var(--yellow), var(--green));
            border-radius: 5px;
            transition: width 1s ease;
        }
        
        .two-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
        }
        
        .workers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 10px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .worker-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 15px;
            background: var(--dark-lighter);
            border-radius: 12px;
            border: 1px solid var(--gray);
        }
        
        .worker-item:hover {
            border-color: var(--blue);
            transform: translateX(5px);
        }
        
        .worker-item.active {
            border-color: var(--green);
            background: rgba(0, 214, 91, 0.1);
        }
        
        .worker-status {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--gray);
        }
        
        .worker-item.active .worker-status {
            background: var(--green);
            box-shadow: 0 0 15px var(--green);
        }
        
        .leaderboard-table { margin-top: 15px; }
        
        .leaderboard-row {
            display: grid;
            grid-template-columns: 50px 1fr 100px 100px;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            margin-bottom: 5px;
        }
        
        .leaderboard-row:hover { background: rgba(255,255,255,0.02); }
        
        .leaderboard-pos {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
        }
        
        .leaderboard-pos.gold { 
            background: linear-gradient(135deg, #ffd700, #ffec8b); 
            color: var(--dark);
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.4);
        }
        
        .leaderboard-pos.silver { 
            background: linear-gradient(135deg, #c0c0c0, #e0e0e0); 
            color: var(--dark);
        }
        
        .leaderboard-pos.bronze { 
            background: linear-gradient(135deg, #cd7f32, #e8a860); 
            color: var(--dark);
        }
        
        .leaderboard-pos.default { 
            background: var(--gray); 
            color: var(--text-muted);
        }
        
        .leaderboard-wus strong {
            color: var(--blue);
            font-family: 'Orbitron', sans-serif;
        }
        
        @media (max-width: 1400px) {
            .two-columns { grid-template-columns: 1fr; }
        }
        
        @media (max-width: 1024px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .header { flex-direction: column; gap: 20px; }
        }
    </style>
</head>
<body>
    <svg width="0" height="0">
        <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#e10600"/>
                <stop offset="50%" style="stop-color:#ffd700"/>
                <stop offset="100%" style="stop-color:#00d65b"/>
            </linearGradient>
        </defs>
    </svg>
    
    <div class="header" style="position: relative;">
        <div class="logo">
            <h1>🏎️ F1 STRATEGY RACER</h1>
        </div>
        <div class="header-stats">
            <div class="header-stat">
                <div class="header-stat-value" id="totalWus">0</div>
                <div class="header-stat-label">Total WUs</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" id="completedWus">0</div>
                <div class="header-stat-label">Completed</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" id="activeWorkers">0</div>
                <div class="header-stat-label">Active</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" id="bestPnl">$0</div>
                <div class="header-stat-label">Best PnL</div>
            </div>
        </div>
        <div class="live-indicator">
            <div class="live-dot"></div>
            <span style="font-family: 'Orbitron'; font-size: 0.75rem;">LIVE</span>
        </div>
    </div>
    
    <div class="main-container">
        <div class="gauges-row">
            <div class="gauge-card">
                <div class="gauge-ring">
                    <svg width="140" height="140">
                        <circle class="bg" cx="70" cy="70" r="60"/>
                        <circle class="progress" id="gaugeWorkers" cx="70" cy="70" r="60"/>
                    </svg>
                    <div class="gauge-center">
                        <div class="gauge-value" id="gaugeWorkersValue">0</div>
                        <div class="gauge-label">Workers</div>
                    </div>
                </div>
            </div>
            
            <div class="gauge-card">
                <div class="gauge-ring">
                    <svg width="140" height="140">
                        <circle class="bg" cx="70" cy="70" r="60"/>
                        <circle class="progress" id="gaugeWus" cx="70" cy="70" r="60"/>
                    </svg>
                    <div class="gauge-center">
                        <div class="gauge-value" id="gaugeWusValue">0/h</div>
                        <div class="gauge-label">WU/hour</div>
                    </div>
                </div>
            </div>
            
            <div class="gauge-card">
                <div class="gauge-ring">
                    <svg width="140" height="140">
                        <circle class="bg" cx="70" cy="70" r="60"/>
                        <circle class="progress" id="gaugeCpu" cx="70" cy="70" r="60"/>
                    </svg>
                    <div class="gauge-center">
                        <div class="gauge-value" id="gaugeCpuValue">0%</div>
                        <div class="gauge-label">CPU Load</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="card">
                <div class="card-title">📊 Total Work Units</div>
                <div class="card-value" id="cardTotalWus">0</div>
            </div>
            <div class="card">
                <div class="card-title">✅ Completed</div>
                <div class="card-value green" id="cardCompleted">0</div>
            </div>
            <div class="card">
                <div class="card-title">🚀 In Progress</div>
                <div class="card-value yellow" id="cardInProgress">0</div>
            </div>
            <div class="card">
                <div class="card-title">💰 Best Strategy</div>
                <div class="card-value red" id="cardPnl">$0</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">🏆 Machine Championship (CPU Time)</div>
            <div class="machines-grid" id="machinesGrid"></div>
        </div>
        
        <div class="two-columns">
            <div class="section">
                <div class="section-title">⚡ Active Workers</div>
                <div class="workers-grid" id="workersGrid"></div>
            </div>
            
            <div class="section">
                <div class="section-title">🥇 Podium Leaders</div>
                <div class="leaderboard-table" id="leaderboard"></div>
            </div>
        </div>
    </div>
    
    <script>
        async function update() {
            try {
                const status = await fetch('/api/status').then(r => r.json());
                const workers = await fetch('/api/workers').then(r => r.json());
                const leaderboard = await fetch('/api/leaderboard').then(r => r.json());
                const machines = await fetch('/api/machines').then(r => r.json());
                
                // Header
                document.getElementById('totalWus').textContent = formatNumber(status.work_units.total);
                document.getElementById('completedWus').textContent = formatNumber(status.work_units.completed);
                document.getElementById('activeWorkers').textContent = status.workers.active;
                document.getElementById('bestPnl').textContent = '$' + formatNumber(status.best_strategy?.pnl || 0);
                
                // Cards
                document.getElementById('cardTotalWus').textContent = formatNumber(status.work_units.total);
                document.getElementById('cardCompleted').textContent = formatNumber(status.work_units.completed);
                document.getElementById('cardInProgress').textContent = formatNumber(status.work_units.in_progress || 0);
                document.getElementById('cardPnl').textContent = '$' + formatNumber(status.best_strategy?.pnl || 0);
                
                // Gauges
                const active = status.workers.active;
                const maxWorkers = 25;
                const wuPerHour = status.work_units.completed > 0 ? Math.round(status.work_units.completed / 24) : 0;
                const cpuLoad = Math.min(100, active * 5);
                
                document.getElementById('gaugeWorkers').style.strokeDashoffset = 377 - (377 * active / maxWorkers);
                document.getElementById('gaugeWorkersValue').textContent = active;
                
                document.getElementById('gaugeWus').style.strokeDashoffset = 377 - (377 * Math.min(1, wuPerHour / 100));
                document.getElementById('gaugeWusValue').textContent = wuPerHour + '/h';
                
                document.getElementById('gaugeCpu').style.strokeDashoffset = 377 - (377 * cpuLoad / 100);
                document.getElementById('gaugeCpuValue').textContent = cpuLoad + '%';
                
                // Machines
                const machinesGrid = document.getElementById('machinesGrid');
                machinesGrid.innerHTML = '';
                machines.machines.forEach((m, i) => {
                    machinesGrid.innerHTML += `
                        <div class="machine-card">
                            <div class="machine-header">
                                <div class="machine-icon">${m.icon}</div>
                                <div>
                                    <div style="font-weight: 600;">${m.name}</div>
                                    <div style="font-size: 0.65rem; color: var(--text-muted);">Position #${i + 1}</div>
                                </div>
                            </div>
                            <div class="machine-stats">
                                <div class="machine-stat">
                                    <div class="machine-stat-value">${m.cpu_hours}h</div>
                                    <div style="font-size: 0.55rem; color: var(--text-muted);">CPU Time</div>
                                </div>
                                <div class="machine-stat">
                                    <div class="machine-stat-value" style="color: var(--green);">${formatNumber(m.wus)}</div>
                                    <div style="font-size: 0.55rem; color: var(--text-muted);">Work Units</div>
                                </div>
                            </div>
                            <div class="contribution-bar">
                                <div class="contribution-fill" style="width: ${m.contribution}%"></div>
                            </div>
                        </div>
                    `;
                });
                
                // Workers
                const workersGrid = document.getElementById('workersGrid');
                workersGrid.innerHTML = '';
                workers.workers.slice(0, 20).forEach(w => {
                    workersGrid.innerHTML += `
                        <div class="worker-item ${w.status}">
                            <div class="worker-status"></div>
                            <div style="flex: 1;">
                                <div style="font-size: 0.85rem; font-weight: 600;">${w.friendly_name}</div>
                                <div style="font-size: 0.7rem; color: var(--text-muted);"><strong>${formatNumber(w.work_units_completed)}</strong> WUs</div>
                            </div>
                        </div>
                    `;
                });
                
                // Leaderboard
                const lb = document.getElementById('leaderboard');
                lb.innerHTML = '';
                leaderboard.leaderboard.slice(0, 8).forEach((w, i) => {
                    const posClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'default';
                    lb.innerHTML += `
                        <div class="leaderboard-row">
                            <div class="leaderboard-pos ${posClass}">${i + 1}</div>
                            <div style="font-weight: 600;">${w.friendly_name}</div>
                            <div class="leaderboard-wus"><strong>${formatNumber(w.work_units)}</strong></div>
                            <div style="font-family: 'Orbitron';">${w.execution_time_hours}h</div>
                        </div>
                    `;
                });
            } catch (e) { console.error(e); }
        }
        
        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        }
        
        update();
        setInterval(update, 3000);
    </script>
</body>
</html>"""

@app.route('/')
def home():
    return HTML

@app.route('/api/status')
def status():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total = c.fetchone()['total']
    
    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed = c.fetchone()['completed']
    
    c.execute("SELECT COUNT(*) as pending FROM work_units WHERE status='pending'")
    pending = c.fetchone()['pending']
    
    c.execute("SELECT COUNT(*) as active FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
    active = c.fetchone()['active']
    
    c.execute("""
        SELECT pnl FROM results 
        WHERE pnl > 0 AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
        ORDER BY pnl DESC LIMIT 1
    """)
    best = c.fetchone()
    
    conn.close()
    
    return jsonify({
        'work_units': {'total': total, 'completed': completed, 'pending': pending, 'in_progress': total - completed - pending},
        'workers': {'active': active},
        'best_strategy': {'pnl': best['pnl'] if best else 0}
    })

@app.route('/api/machines')
def machines():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT SUM(total_execution_time) as total_cpu FROM workers")
    total_cpu = c.fetchone()['total_cpu'] or 1
    
    c.execute("""
        SELECT id, SUM(work_units_completed) as total_wus, SUM(total_execution_time) as cpu_time
        FROM workers WHERE work_units_completed > 0
        GROUP BY 
            CASE 
                WHEN id LIKE '%MacBook-Pro%' THEN 'MacBook Pro'
                WHEN id LIKE '%MacBook-Air%' THEN 'MacBook Air'
                WHEN id LIKE '%rog%' THEN 'Linux ROG'
                WHEN id LIKE '%Asus%' THEN 'Asus Dorada'
                ELSE 'Worker'
            END
        ORDER BY cpu_time DESC
    """)
    
    machine_stats = []
    total_hours = total_cpu / 3600
    
    for row in c.fetchall():
        cpu_hours = row['cpu_time'] / 3600 if row['cpu_time'] else 0
        wus = row['total_wus'] or 0
        contribution = round((cpu_hours / total_hours) * 100, 1) if total_hours > 0 else 0
        
        if 'MacBook-Pro' in row['id']:
            icon = '🍎'
            name = '🍎 MacBook Pro'
        elif 'MacBook-Air' in row['id']:
            icon = '🪶'
            name = '🪶 MacBook Air'
        elif 'rog' in row['id'] or 'Linux' in row['id']:
            icon = '🐧'
            name = '🐧 Linux ROG'
        elif 'Asus' in row['id']:
            icon = '🌐'
            name = '🌐 Asus Dorada'
        else:
            icon = '💻'
            name = '💻 Worker'
        
        machine_stats.append({
            'name': name, 'icon': icon,
            'cpu_hours': round(cpu_hours, 1),
            'wus': wus,
            'contribution': contribution
        })
    
    conn.close()
    return jsonify({'machines': machine_stats})

@app.route('/api/workers')
def workers():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, work_units_completed, last_seen FROM workers ORDER BY last_seen DESC")
    now = time.time()
    ws = []
    
    for row in c.fetchall():
        last_seen = row['last_seen']
        mins = (now - (last_seen - 2440587.5) * 86400.0) / 60.0 if last_seen else 9999
        
        name = row['id']
        name = name.replace('Enders-MacBook-Pro', '🍎 MB Pro')
        name = name.replace('Enders-MacBook-Air', '🪶 MB Air')
        name = name.replace('ender-rog', '🐧 ROG')
        name = name.replace('Asus-Dorada', '🌐 Asus')
        name = name.replace('_Linux', '').replace('_Darwin', '').replace('local', '')
        
        ws.append({
            'id': row['id'],
            'friendly_name': name.strip(),
            'work_units_completed': row['work_units_completed'],
            'status': 'active' if mins < 10 else ''
        })
    
    conn.close()
    return jsonify({'workers': ws})

@app.route('/api/leaderboard')
def leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, work_units_completed, total_execution_time FROM workers ORDER BY work_units_completed DESC LIMIT 10")
    leaders = []
    
    for row in c.fetchall():
        name = row['id']
        name = name.replace('Enders-MacBook-Pro', '🍎 MacBook Pro')
        name = name.replace('Enders-MacBook-Air', '🪶 MacBook Air')
        name = name.replace('ender-rog', '🐧 Linux ROG')
        name = name.replace('Asus-Dorada', '🌐 Asus Dorada')
        name = name.replace('_Linux', '').replace('_Darwin', '')
        
        leaders.append({
            'friendly_name': name.strip(),
            'work_units': row['work_units_completed'],
            'execution_time_hours': round(row['total_execution_time'] / 3600, 1)
        })
    
    conn.close()
    return jsonify({'leaderboard': leaders})

if __name__ == '__main__':
    print("🏎️ F1 Dashboard: http://localhost:5006")
    app.run(host='0.0.0.0', port=5006, debug=False)
