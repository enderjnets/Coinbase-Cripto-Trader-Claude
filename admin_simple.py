#!/usr/bin/env python3
"""
Servidor web simple para administración del cluster
"""

from flask import Flask, jsonify, request
import sqlite3
import subprocess
import os

app = Flask(__name__)
DATABASE = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db'
PROJECT_DIR = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Administracion - Bittrader Cluster</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #1a1d29 0%, #0f111a 100%); 
            color: #fff; 
            min-height: 100vh; 
            padding: 20px;
        }
        h1 { 
            background: linear-gradient(90deg, #60a5fa, #3b82f6); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent;
            margin-bottom: 30px;
        }
        .header {
            background: linear-gradient(180deg, #1e2433 0%, #151820 100%);
            border-radius: 15px;
            padding: 20px 30px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .live {
            background: rgba(0, 214, 91, 0.15);
            padding: 8px 20px;
            border-radius: 20px;
            color: #00d65b;
            font-weight: bold;
        }
        .section {
            background: linear-gradient(145deg, #1a1d29, #1f2937);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid #374151;
        }
        .section h2 { color: #60a5fa; margin-bottom: 20px; }
        .buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }
        .btn {
            padding: 20px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        .btn:hover { transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .btn-green { background: linear-gradient(135deg, #059669, #10b981); color: white; }
        .btn-blue { background: linear-gradient(135deg, #2563eb, #3b82f6); color: white; }
        .btn-yellow { background: linear-gradient(135deg, #d97706, #f59e0b); color: white; }
        .btn-red { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; }
        .btn-icon { font-size: 28px; }
        .btn-desc { font-size: 11px; opacity: 0.8; font-family: monospace; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .status-box {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .status-value { font-size: 28px; font-weight: bold; color: #00d65b; }
        .status-label { font-size: 12px; color: #9ca3af; margin-top: 5px; }
        .log {
            background: #0d1117;
            padding: 15px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 13px;
            max-height: 200px;
            overflow-y: auto;
            color: #00d65b;
        }
        .log-entry { padding: 5px 0; border-bottom: 1px solid #21262d; }
        .log-entry:last-child { border-bottom: none; }
        .log-time { color: #6e7681; margin-right: 10px; }
        .links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 15px; }
        .link {
            display: flex; align-items: center; gap: 10px;
            padding: 15px; background: rgba(0,0,0,0.3);
            border-radius: 10px; color: white; text-decoration: none;
            transition: all 0.3s;
        }
        .link:hover { background: rgba(59, 130, 246, 0.2); }
    </style>
</head>
<body>
    <div class="header">
        <h1>Panel de Administracion del Cluster</h1>
        <div class="live">LIVE</div>
    </div>
    
    <div class="section">
        <h2>Acciones de Mantenimiento</h2>
        <div class="buttons">
            <button class="btn btn-green" onclick="runCmd('status')">
                <span class="btn-icon">📊</span>
                <span>Ver Estado</span>
                <span class="btn-desc">quick_status.sh</span>
            </button>
            <button class="btn btn-green" onclick="runCmd('repair')">
                <span class="btn-icon">🔧</span>
                <span>Reparar Workers</span>
                <span class="btn-desc">autonomous_worker_fix.py</span>
            </button>
            <button class="btn btn-yellow" onclick="runCmd('restart_daemon')">
                <span class="btn-icon">🔄</span>
                <span>Reiniciar Daemon</span>
                <span class="btn-desc">worker_daemon.sh</span>
            </button>
            <button class="btn btn-green" onclick="runCmd('heartbeat')">
                <span class="btn-icon">💓</span>
                <span>Forzar Heartbeat</span>
                <span class="btn-desc">Actualizar BD</span>
            </button>
            <button class="btn btn-blue" onclick="runCmd('check')">
                <span class="btn-icon">🔍</span>
                <span>Verificar Workers</span>
                <span class="btn-desc">ps aux | grep</span>
            </button>
            <button class="btn btn-red" onclick="runCmd('restart_all')">
                <span class="btn-icon">⚠️</span>
                <span>Reiniciar Todo</span>
                <span class="btn-desc">Reinicio completo</span>
            </button>
        </div>
        
        <div class="status-grid" id="statusGrid">
            <div class="status-box">
                <div class="status-value" id="workersActive">--</div>
                <div class="status-label">Workers Activos</div>
            </div>
            <div class="status-box">
                <div class="status-value" id="workersTotal">--</div>
                <div class="status-label">Workers Totales</div>
            </div>
            <div class="status-box">
                <div class="status-value" id="wusCompleted">--</div>
                <div class="status-label">WUs Completados</div>
            </div>
            <div class="status-box">
                <div class="status-value" id="bestPnl">--</div>
                <div class="status-label">Mejor PnL</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Registro de Acciones</h2>
        <div class="log" id="log">
            <div class="log-entry"><span class="log-time">[--:--:--]</span>Sistema listo</div>
        </div>
    </div>
    
    <div class="section">
        <h2>Enlaces Rapidos</h2>
        <div class="links">
            <a href="http://localhost:8501" class="link" target="_blank">
                <span>🌐</span>
                <span>Streamlit Interface</span>
            </a>
            <a href="http://localhost:5006" class="link" target="_blank">
                <span>🏎️</span>
                <span>F1 Dashboard</span>
            </a>
            <a href="http://localhost:5005" class="link" target="_blank">
                <span>📊</span>
                <span>Coordinator Simple</span>
            </a>
        </div>
    </div>
    
    <script>
        function addLog(msg, type='success') {
            const log = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            const colors = {success: '#00d65b', error: '#ef4444', warning: '#f59e0b', info: '#3b82f6'};
            log.innerHTML = '<div class="log-entry"><span class="log-time">[' + time + ']</span><span style="color:' + colors[type] + '">' + msg + '</span></div>' + log.innerHTML;
        }
        
        async function runCmd(cmd) {
            const msgs = {
                'status': 'Verificando estado del sistema...',
                'repair': 'Ejecutando reparacion de workers...',
                'restart_daemon': 'Reiniciando worker daemon...',
                'heartbeat': 'Forzando heartbeats en base de datos...',
                'check': 'Verificando procesos de workers...',
                'restart_all': 'Reiniciando sistema completo...'
            };
            addLog(msgs[cmd], 'info');
            
            try {
                const res = await fetch('/api/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({command: cmd})
                });
                const data = await res.json();
                addLog(data.message, data.success ? 'success' : 'error');
                setTimeout(updateStatus, 500);
            } catch (e) {
                addLog('Error: ' + e, 'error');
            }
        }
        
        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('workersActive').textContent = data.workers.active;
                document.getElementById('workersTotal').textContent = data.workers.total;
                document.getElementById('wusCompleted').textContent = data.work_units.completed;
                document.getElementById('bestPnl').textContent = '$' + data.best_strategy.pnl.toFixed(2);
            } catch (e) {
                console.log('Error actualizando estado');
            }
        }
        
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return HTML

@app.route('/api/status')
def api_status():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM work_units")
    total = c.fetchone()['total']
    c.execute("SELECT COUNT(*) as completed FROM work_units WHERE status='completed'")
    completed = c.fetchone()['completed']
    c.execute("SELECT COUNT(*) as active FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
    active = c.fetchone()['active']
    c.execute("SELECT MAX(pnl) as best FROM results WHERE pnl > 0")
    best = c.fetchone()['best'] or 0
    conn.close()
    return jsonify({
        'workers': {'active': active, 'total': 35},
        'work_units': {'completed': completed, 'total': total},
        'best_strategy': {'pnl': best}
    })

@app.route('/api/execute', methods=['POST'])
def execute_cmd():
    data = request.get_json()
    cmd = data.get('command', '')
    
    cmds = {
        'status': f'cd "{PROJECT_DIR}" && bash quick_status.sh 2>&1',
        'repair': f'cd "{PROJECT_DIR}" && python3 autonomous_worker_fix.py 2>&1',
        'restart_daemon': 'cd ~/.bittrader_worker && bash worker_daemon.sh > /dev/null 2>&1 &',
        'heartbeat': f'sqlite3 "{PROJECT_DIR}/coordinator.db" "UPDATE workers SET last_seen = julianday(\'now\') WHERE id LIKE \'%MacBook%\' OR id LIKE \'%enderj%\'" 2>&1',
        'check': 'ps aux | grep crypto_worker | grep -v grep | head -10',
        'restart_all': 'pkill -f crypto_worker; sleep 2; cd ~/.bittrader_worker && bash worker_daemon.sh > /dev/null 2>&1 &'
    }
    
    if cmd in cmds:
        try:
            result = subprocess.run(cmds[cmd], shell=True, capture_output=True, text=True, timeout=10)
            return jsonify({'success': True, 'message': f'{cmd.capitalize()} ejecutado'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': False, 'message': 'Comando no reconocido'})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  PANEL DE ADMINISTRACION DEL CLUSTER")
    print("="*50)
    print("\n Abriendo en: http://localhost:5007")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5007, debug=False)
