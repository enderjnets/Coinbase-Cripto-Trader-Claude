#!/usr/bin/env python3
"""
F1 Racing Dashboard - With Machine Contribution
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
    <title>🧬 Strategy Miner F1 Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --red: #e10600;
            --red-dark: #a30500;
            --green: #00d65b;
            --green-glow: #00ff7f;
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
            background: linear-gradient(135deg, var(--dark) 0%, var(--dark-lighter) 50%, var(--dark) 100%);
            border-bottom: 3px solid var(--red);
            padding: 25px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo h1 {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 3px;
        }
        
        .logo h1 span {
            color: var(--red);
        }
        
        .header-stats {
            display: flex;
            gap: 30px;
        }
        
        .header-stat {
            text-align: center;
        }
        
        .header-stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--green);
            text-shadow: 0 0 15px rgba(0, 214, 91, 0.5);
        }
        
        .header-stat-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(0, 214, 91, 0.1);
            padding: 8px 20px;
            border-radius: 30px;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--green);
        }
        
        .live-dot {
            width: 8px;
            height: 8px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 10px var(--green); }
            50% { opacity: 0.5; transform: scale(0.8); box-shadow: 0 0 5px var(--green); }
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 30px;
        }
        
        .card {
            background: var(--dark-card);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid var(--gray);
            position: relative;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--red), var(--yellow), var(--green));
        }
        
        .card-title {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .card-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--text) 0%, var(--blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .card-value.green { background: linear-gradient(135deg, var(--green) 0%, var(--green-glow) 100%); -webkit-background-clip: text; background-clip: text; }
        .card-value.yellow { background: linear-gradient(135deg, var(--yellow) 0%, #ffec8b 100%); -webkit-background-clip: text; background-clip: text; }
        .card-value.red { background: linear-gradient(135deg, var(--red) 0%, #ff6b6b 100%); -webkit-background-clip: text; background-clip: text; }
        
        .gauges-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            padding: 0 30px;
        }
        
        .gauge-card {
            background: linear-gradient(145deg, var(--dark-card), var(--dark-lighter));
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            border: 1px solid var(--gray);
        }
        
        .gauge-ring {
            width: 160px;
            height: 160px;
            margin: 0 auto 20px;
            position: relative;
        }
        
        .gauge-ring svg {
            transform: rotate(-90deg);
        }
        
        .gauge-ring circle {
            fill: none;
            stroke-width: 12;
        }
        
        .gauge-ring .bg { stroke: var(--gray); }
        .gauge-ring .progress { 
            stroke: url(#gaugeGradient);
            stroke-linecap: round;
            stroke-dasharray: 408;
            stroke-dashoffset: 408;
            transition: stroke-dashoffset 1s ease;
        }
        
        .gauge-center {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }
        
        .gauge-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text);
        }
        
        .gauge-label {
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .section-title {
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .section-title .icon { font-size: 1.2rem; }
        
        .machines-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        
        .machine-card {
            background: linear-gradient(145deg, var(--dark-lighter), rgba(0,0,0,0.3));
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--gray);
            position: relative;
            overflow: hidden;
        }
        
        .machine-icon {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .machine-name {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 15px;
        }
        
        .machine-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .machine-stat {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        
        .machine-stat-value {
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--green);
        }
        
        .machine-stat-label {
            font-size: 0.6rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }
        
        .contribution-bar {
            height: 8px;
            background: var(--gray);
            border-radius: 4px;
            margin-top: 15px;
            overflow: hidden;
        }
        
        .contribution-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--green), var(--green-glow));
            border-radius: 4px;
            transition: width 1s ease;
        }
        
        .workers-section {
            grid-column: span 2;
            background: var(--dark-card);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid var(--gray);
        }
        
        .workers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .worker-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: var(--dark-lighter);
            border-radius: 10px;
            border: 1px solid var(--gray);
            transition: all 0.3s;
        }
        
        .worker-item:hover {
            border-color: var(--blue);
            transform: translateY(-2px);
        }
        
        .worker-item.active {
            border-color: var(--green);
            background: rgba(0, 214, 91, 0.1);
        }
        
        .worker-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--gray);
        }
        
        .worker-item.active .worker-status {
            background: var(--green);
            box-shadow: 0 0 15px var(--green);
        }
        
        .worker-info {
            flex: 1;
        }
        
        .worker-name {
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .worker-wus {
            font-size: 0.7rem;
            color: var(--text-muted);
        }
        
        .worker-wus strong {
            color: var(--green);
            font-weight: 700;
        }
        
        .leaderboard-section {
            grid-column: span 2;
            background: var(--dark-card);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid var(--gray);
        }
        
        .leaderboard-table {
            margin-top: 15px;
        }
        
        .leaderboard-row {
            display: grid;
            grid-template-columns: 50px 1fr 80px 80px;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .leaderboard-row:last-child { border-bottom: none; }
        
        .leaderboard-pos {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1rem;
        }
        
        .leaderboard-pos.gold { background: linear-gradient(135deg, #ffd700, #ffec8b); color: var(--dark); }
        .leaderboard-pos.silver { background: linear-gradient(135deg, #c0c0c0, #e0e0e0); color: var(--dark); }
        .leaderboard-pos.bronze { background: linear-gradient(135deg, #cd7f32, #e8a860); color: var(--dark); }
        .leaderboard-pos.default { background: var(--gray); color: var(--text-muted); }
        
        .leaderboard-name {
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        .leaderboard-wus {
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        
        .leaderboard-wus strong {
            color: var(--green);
            font-weight: 700;
        }
        
        .workers-count {
            background: linear-gradient(135deg, var(--green), var(--green-glow));
            padding: 6px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--dark);
        }
        
        @media (max-width: 1200px) {
            .main-grid { grid-template-columns: repeat(2, 1fr); }
            .workers-section, .leaderboard-section { grid-column: span 2; }
        }
        
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
            .workers-section, .leaderboard-section { grid-column: span 1; }
            .machines-grid { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 20px; }
        }
    </style>
    <style>
        svg.defs-only { display: none; }
    </style>
</head>
<body>
    <svg width="0" height="0">
        <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#00d65b"/>
                <stop offset="50%" style="stop-color:#00b4d8"/>
                <stop offset="100%" style="stop-color:#e10600"/>
            </linearGradient>
        </defs>
    </svg>
    
    <div class="header">
        <div class="logo">
            <h1>🧬 Strategy <span>Miner</span></h1>
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
                <div class="header-stat-label">Workers</div>
            </div>
        </div>
        <div class="live-indicator">
            <div class="live-dot"></div>
            LIVE
        </div>
    </div>
    
    <div class="gauges-row" style="padding: 30px 30px 0 30px;">
        <div class="gauge-card">
            <div class="gauge-ring">
                <svg width="160" height="160">
                    <circle class="bg" cx="80" cy="80" r="65"/>
                    <circle class="progress" id="gaugeWorkers" cx="80" cy="80" r="65"/>
                </svg>
                <div class="gauge-center">
                    <div class="gauge-value" id="gaugeWorkersValue">0</div>
                    <div class="gauge-label">Workers</div>
                </div>
            </div>
        </div>
        
        <div class="gauge-card">
            <div class="gauge-ring">
                <svg width="160" height="160">
                    <circle class="bg" cx="80" cy="80" r="65"/>
                    <circle class="progress" id="gaugeWus" cx="80" cy="80" r="65"/>
                </svg>
                <div class="gauge-center">
                    <div class="gauge-value" id="gaugeWusValue">0/h</div>
                    <div class="gauge-label">WU/hour</div>
                </div>
            </div>
        </div>
        
        <div class="gauge-card">
            <div class="gauge-ring">
                <svg width="160" height="160">
                    <circle class="bg" cx="80" cy="80" r="65"/>
                    <circle class="progress" id="gaugeCpu" cx="80" cy="80" r="65"/>
                </svg>
                <div class="gauge-center">
                    <div class="gauge-value" id="gaugeCpuValue">0%</div>
                    <div class="gauge-label">CPU Load</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="main-grid">
        <div class="card">
            <div class="card-title">📊 Total Work Units</div>
            <div class="card-value" id="cardTotalWus">0</div>
        </div>
        
        <div class="card">
            <div class="card-title">✅ Completed</div>
            <div class="card-value green" id="cardCompleted">0</div>
        </div>
        
        <div class="card">
            <div class="card-title">🚀 Processing</div>
            <div class="card-value yellow" id="cardInProgress">0</div>
        </div>
        
        <div class="card">
            <div class="card-title">💰 Best PnL</div>
            <div class="card-value red" id="cardPnl">$0</div>
        </div>
        
        <div class="card" style="grid-column: span 4;">
            <div class="section-title">
                <span class="icon">🏆</span>
                Machine Contribution Ranking (CPU Time)
            </div>
            <div class="machines-grid" id="machinesGrid"></div>
        </div>
        
        <div class="workers-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div class="section-title" style="margin: 0;">
                    <span class="icon">⚡</span>
                    Active Workers
                </div>
                <div class="workers-count" id="workersCount">0 Active</div>
            </div>
            <div class="workers-grid" id="workersGrid"></div>
        </div>
        
        <div class="leaderboard-section">
            <div class="section-title">
                <span class="icon">🏅</span>
                Top Workers
            </div>
            <div class="leaderboard-table" id="leaderboard"></div>
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
                document.getElementById('totalWus').textContent = status.work_units.total;
                document.getElementById('completedWus').textContent = status.work_units.completed;
                document.getElementById('activeWorkers').textContent = status.workers.active;
                document.getElementById('cardTotalWus').textContent = status.work_units.total;
                document.getElementById('cardCompleted').textContent = status.work_units.completed;
                document.getElementById('cardInProgress').textContent = status.work_units.in_progress || 0;
                document.getElementById('cardPnl').textContent = '$' + (status.best_strategy?.pnl || 0).toFixed(2);
                
                // Gauges
                const active = status.workers.active;
                const maxWorkers = 25;
                const wuPerHour = status.work_units.completed > 0 ? Math.round(status.work_units.completed / 24) : 0;
                const cpuLoad = Math.min(100, active * 5);
                
                document.getElementById('gaugeWorkers').style.strokeDashoffset = 408 - (408 * active / maxWorkers);
                document.getElementById('gaugeWorkersValue').textContent = active;
                document.getElementById('gaugeWus').style.strokeDashoffset = 408 - (408 * Math.min(1, wuPerHour / 100));
                document.getElementById('gaugeWusValue').textContent = wuPerHour + '/h';
                document.getElementById('gaugeCpu').style.strokeDashoffset = 408 - (408 * cpuLoad / 100);
                document.getElementById('gaugeCpuValue').textContent = cpuLoad + '%';
                
                // Machines Contribution
                const machinesGrid = document.getElementById('machinesGrid');
                machinesGrid.innerHTML = '';
                machines.machines.forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'machine-card';
                    div.innerHTML = `
                        <div class="machine-icon">${m.icon}</div>
                        <div class="machine-name">${m.name}</div>
                        <div class="machine-stats">
                            <div class="machine-stat">
                                <div class="machine-stat-value">${m.cpu_hours}h</div>
                                <div class="machine-stat-label">CPU Time</div>
                            </div>
                            <div class="machine-stat">
                                <div class="machine-stat-value" style="color: var(--green);">${m.wus}</div>
                                <div class="machine-stat-label">Work Units</div>
                            </div>
                        </div>
                        <div class="contribution-bar">
                            <div class="contribution-fill" style="width: ${m.contribution}%"></div>
                        </div>
                    `;
                    machinesGrid.appendChild(div);
                });
                
                // Workers Grid
                document.getElementById('workersCount').textContent = active + ' Active';
                const workersGrid = document.getElementById('workersGrid');
                workersGrid.innerHTML = '';
                workers.workers.slice(0, 16).forEach(w => {
                    const div = document.createElement('div');
                    div.className = 'worker-item ' + (w.status === 'active' ? 'active' : 'inactive');
                    div.innerHTML = `
                        <div class="worker-status"></div>
                        <div class="worker-info">
                            <div class="worker-name">${w.friendly_name}</div>
                            <div class="worker-wus"><strong>${w.work_units_completed}</strong> WUs</div>
                        </div>
                    `;
                    workersGrid.appendChild(div);
                });
                
                // Leaderboard
                const lb = document.getElementById('leaderboard');
                lb.innerHTML = '';
                leaderboard.leaderboard.slice(0, 10).forEach((w, i) => {
                    const posClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'default';
                    lb.innerHTML += `
                        <div class="leaderboard-row">
                            <div class="leaderboard-pos ${posClass}">${i + 1}</div>
                            <div class="leaderboard-name" style="grid-column: 2; display: flex; align-items: center; gap: 8px;">
                                ${w.friendly_name}
                            </div>
                            <div class="leaderboard-wus"><strong>${w.work_units}</strong> WUs</div>
                            <div class="leaderboard-wus">${w.execution_time_hours}h</div>
                        </div>
                    `;
                });
                
            } catch (e) { console.error(e); }
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
        SELECT pnl, trades, win_rate, sharpe_ratio, max_drawdown 
        FROM results 
        WHERE pnl > 0 AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
        ORDER BY pnl DESC LIMIT 1
    """)
    best = c.fetchone()
    
    conn.close()
    best_data = {}
    if best:
        best_data = {
            'pnl': best['pnl'],
            'trades': best['trades'],
            'win_rate': best['win_rate'],
            'sharpe_ratio': best['sharpe_ratio'],
            'max_drawdown': best['max_drawdown']
        }
    return jsonify({
        'work_units': {'total': total, 'completed': completed, 'pending': pending, 'in_progress': total - completed - pending},
        'workers': {'active': active},
        'best_strategy': best_data
    })

@app.route('/api/machines')
def machines():
    """Machine contribution ranking"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            SUM(total_execution_time) as total_cpu
        FROM workers
    """)
    total_cpu = c.fetchone()['total_cpu'] or 1
    
    c.execute("""
        SELECT 
            id,
            SUM(work_units_completed) as total_wus,
            SUM(total_execution_time) as cpu_time
        FROM workers 
        WHERE work_units_completed > 0
        GROUP BY 
            CASE 
                WHEN id LIKE '%MacBook-Pro%' THEN 'MacBook Pro'
                WHEN id LIKE '%MacBook-Air%' THEN 'MacBook Air'
                WHEN id LIKE '%rog%' THEN 'Linux ROG'
                WHEN id LIKE '%Asus%' THEN 'Asus Dorada'
                ELSE 'Otro'
            END
        ORDER BY cpu_time DESC
    """)
    
    machine_stats = []
    for row in c.fetchall():
        cpu_hours = row['cpu_time'] / 3600 if row['cpu_time'] else 0
        wus = row['total_wus'] or 0
        
        if 'MacBook-Pro' in row['id']:
            icon = '🍎'
            name = 'MacBook Pro'
        elif 'MacBook-Air' in row['id']:
            icon = '🪶'
            name = 'MacBook Air'
        elif 'rog' in row['id'] or 'Linux' in row['id']:
            icon = '🐧'
            name = 'Linux ROG'
        elif 'Asus' in row['id']:
            icon = '🌐'
            name = 'Asus Dorada'
        else:
            icon = '💻'
            name = 'Otro'
        
        machine_stats.append({
            'name': name,
            'icon': icon,
            'cpu_hours': round(cpu_hours, 1),
            'wus': wus,
            'contribution': round(cpu_hours * 100 / (total_cpu / 3600), 1)
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
        ws.append({
            'id': row['id'],
            'friendly_name': row['id'].replace('Enders-MacBook-Pro', '🍎 MB Pro').replace('Enders-MacBook-Air', '🪶 MBA').replace('ender-rog', '🐧 ROG').replace('Asus-Dorada', '🌐 Asus').replace('_Linux', '').replace('_Darwin', ''),
            'work_units_completed': row['work_units_completed'],
            'status': 'active' if mins < 10 else 'inactive'
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
        leaders.append({
            'friendly_name': row['id'].replace('Enders-MacBook-Pro', '🍎 MacBook Pro').replace('Enders-MacBook-Air', '🪶 MacBook Air').replace('ender-rog', '🐧 Linux ROG').replace('Asus-Dorada', '🌐 Asus Dorada').replace('_Linux', '').replace('_Darwin', ''),
            'work_units': row['work_units_completed'],
            'execution_time_hours': round(row['total_execution_time'] / 3600, 1)
        })
    conn.close()
    return jsonify({'leaderboard': leaders})

if __name__ == '__main__':
    print("🏆 Dashboard: http://localhost:5006")
    app.run(host='0.0.0.0', port=5006, debug=False)
