#!/usr/bin/env python3
"""
🌐 Servidor Web para Panel de Administración
Ejecuta este script para abrir el panel de administración
"""

from flask import Flask, jsonify, request
import sqlite3
import subprocess
import os
import time
from datetime import datetime

app = Flask(__name__, template_folder='.')
DATABASE = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db'
PROJECT_DIR = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎛️ Panel de Administración - Bittrader Cluster</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Orbitron:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --green: #00d65b;
            --blue: #00b4d8;
            --yellow: #ffd700;
            --red: #e10600;
            --orange: #ff6600;
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
            border-bottom: 4px solid var(--blue);
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
            background: linear-gradient(90deg, var(--blue), var(--green), var(--yellow), var(--red));
        }
        
        .logo { display: flex; align-items: center; gap: 15px; }
        
        .logo h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--text) 0%, var(--blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
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
        
        .container { padding: 30px; max-width: 1600px; margin: 0 auto; }
        
        .admin-section {
            background: var(--dark-card);
            border-radius: 20px;
            padding: 30px;
            border: 2px solid var(--blue);
            margin-bottom: 25px;
            position: relative;
        }
        
        .admin-section::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--blue), var(--green));
        }
        
        .admin-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .admin-icon {
            font-size: 2.5rem;
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, var(--blue), var(--green));
            border-radius: 15px;
        }
        
        .admin-title {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--blue);
        }
        
        .admin-subtitle { font-size: 0.9rem; color: var(--text-muted); }
        
        .buttons-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .admin-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            padding: 25px 20px;
            background: linear-gradient(145deg, var(--dark-lighter), rgba(0,0,0,0.4));
            border: 1px solid var(--gray);
            border-radius: 15px;
            cursor: pointer;
            transition: all 0.3s;
            font-family: 'Rajdhani', sans-serif;
            color: var(--text);
        }
        
        .admin-btn:hover {
            transform: translateY(-5px);
            border-color: var(--blue);
            box-shadow: 0 15px 40px rgba(0, 180, 216, 0.3);
        }
        
        .admin-btn:active { transform: translateY(0); }
        
        .admin-btn.btn-success:hover { border-color: var(--green); box-shadow: 0 15px 40px rgba(0, 214, 91, 0.3); }
        .admin-btn.btn-warning:hover { border-color: var(--yellow); box-shadow: 0 15px 40px rgba(255, 215, 0, 0.3); }
        .admin-btn.btn-danger:hover { border-color: var(--red); box-shadow: 0 15px 40px rgba(225, 6, 0, 0.3); }
        
        .btn-icon { font-size: 2.2rem; }
        .btn-text { font-size: 1.1rem; font-weight: 700; }
        .btn-desc { font-size: 0.75rem; color: var(--text-muted); font-family: monospace; }
        
        .log-section {
            background: var(--dark);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid var(--gray);
            max-height: 300px;
            overflow-y: auto;
        }
        
        .log-entry {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85rem;
            display: flex;
            gap: 15px;
        }
        
        .log-entry:last-child { border-bottom: nonelog-time { color; }
        .: var(--text-muted); min-width: 90px; }
        .log-success { color: var(--green); }
        .log-error { color: var(--red); }
        .log-warning { color: var(--yellow); }
        .log-info { color: var(--blue); }
        
        .log-section::-webkit-scrollbar { width: 8px; }
        .log-section::-webkit-scrollbar-track { background: var(--dark); border-radius: 4px; }
        .log-section::-webkit-scrollbar-thumb { background: var(--gray); border-radius: 4px; }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--gray);
        }
        
        .status-item {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        
        .status-value {
            font-family: 'Orbitron', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--green);
        }
        
        .status-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-top: 5px;
        }
        
        .quick-links {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .quick-link {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px 20px;
            background: linear-gradient(145deg, var(--dark-lighter), rgba(0,0,0,0.3));
            border: 1px solid var(--gray);
            border-radius: 12px;
            color: var(--text);
            text-decoration: none;
            transition: all 0.3s;
        }
        
        .quick-link:hover {
            border-color: var(--blue);
            transform: translateX(5px);
        }
        
        .quick-link-icon { font-size: 1.5rem; }
        .quick-link-text { font-weight: 600; }
        .quick-link-desc { font-size: 0.75rem; color: var(--text-muted); }

        /* Goal Section */
        .goal-section {
            background: var(--dark-card); border-radius: 20px;
            padding: 25px 30px; border: 2px solid var(--green);
            margin-bottom: 25px; position: relative;
        }
        .goal-section::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, var(--red), var(--yellow), var(--green));
            border-radius: 20px 20px 0 0;
        }
        .goal-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 12px; }
        .goal-pct-big { font-family: 'Orbitron', sans-serif; font-size: 2.8rem; font-weight: 700; }
        .goal-target { font-size: 1rem; color: var(--text-muted); }
        .goal-badge { font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 700; padding: 8px 20px; border-radius: 10px; background: rgba(0,0,0,0.4); border: 1px solid var(--gray); }
        .goal-bar-bg { background: rgba(0,0,0,0.5); border-radius: 8px; height: 14px; overflow: hidden; margin-bottom: 8px; }
        .goal-bar-fill { height: 100%; border-radius: 8px; transition: width 1s ease; }
        .goal-bar-marks { display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-bottom: 16px; }
        .goal-kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-top: 4px; }
        .goal-kpi { background: rgba(0,0,0,0.35); border-radius: 10px; padding: 12px 14px; border-left: 3px solid var(--gray); }
        .goal-kpi-val { font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 700; }
        .goal-kpi-lbl { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; margin-top: 3px; }
        .goal-kpi-sub { font-size: 0.65rem; color: var(--text-muted); opacity: .6; }
        .goal-msg { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--gray); font-size: 0.85rem; color: var(--text-muted); text-align: center; }

        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 20px; }
            .buttons-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="header" style="position: relative;">
        <div class="logo">
            <h1>🎛️ ADMINISTRACIÓN DEL CLUSTER</h1>
        </div>
        <div class="live-indicator">
            <div class="live-dot"></div>
            <span style="font-family: 'Orbitron'; font-size: 0.8rem;">LIVE</span>
        </div>
    </div>
    
    <div class="container">

        <!-- OBJETIVO 5% DIARIO -->
        <div class="goal-section">
            <div class="admin-header" style="margin-bottom:16px">
                <div class="admin-icon">🎯</div>
                <div>
                    <div class="admin-title">Objetivo: 5% Diario</div>
                    <div class="admin-subtitle">Capital base $500 · Backtest 80,000 candles 1min (55.6 días)</div>
                </div>
            </div>
            <div class="goal-top">
                <div>
                    <div class="goal-pct-big" id="g-daily-pct" style="color:var(--red)">0.00%</div>
                    <div class="goal-target">retorno diario actual &nbsp;/&nbsp; <span style="color:var(--green)">5.00% objetivo</span></div>
                </div>
                <div class="goal-badge" id="g-badge" style="color:var(--red)">0.0%</div>
            </div>
            <div class="goal-bar-bg">
                <div class="goal-bar-fill" id="g-fill" style="width:0%;background:linear-gradient(90deg,var(--red),var(--yellow))"></div>
            </div>
            <div class="goal-bar-marks"><span>0%</span><span>1%</span><span>2%</span><span>3%</span><span>4%</span><span>5%</span></div>
            <div class="goal-kpis">
                <div class="goal-kpi"><div class="goal-kpi-val" id="g-daily-pnl" style="color:var(--green)">$-</div><div class="goal-kpi-lbl">PnL diario</div><div class="goal-kpi-sub">obj: $25/día</div></div>
                <div class="goal-kpi"><div class="goal-kpi-val" id="g-total-pnl" style="color:var(--green)">$-</div><div class="goal-kpi-lbl">PnL total</div><div class="goal-kpi-sub" id="g-total-target">obj: $-</div></div>
                <div class="goal-kpi"><div class="goal-kpi-val" id="g-total-ret">-%</div><div class="goal-kpi-lbl">Retorno total</div><div class="goal-kpi-sub" id="g-total-ret-sub">obj: -%</div></div>
                <div class="goal-kpi"><div class="goal-kpi-val" id="g-mult" style="color:var(--yellow)">-x</div><div class="goal-kpi-lbl">Mejora necesaria</div><div class="goal-kpi-sub">para el objetivo</div></div>
                <div class="goal-kpi"><div class="goal-kpi-val" id="g-wr">-%</div><div class="goal-kpi-lbl">Win Rate</div><div class="goal-kpi-sub">obj: ≥60%</div></div>
                <div class="goal-kpi"><div class="goal-kpi-val" id="g-avg">$-</div><div class="goal-kpi-lbl">Avg PnL válido</div><div class="goal-kpi-sub" id="g-valid-count">- resultados</div></div>
            </div>
            <div class="goal-msg" id="g-msg">Cargando datos...</div>
        </div>

        <!-- Panel de Control -->
        <div class="admin-section">
            <div class="admin-header">
                <div class="admin-icon">🎛️</div>
                <div>
                    <div class="admin-title">Panel de Control Principal</div>
                    <div class="admin-subtitle">Administra tu cluster de trading distribuido</div>
                </div>
            </div>
            
            <div class="buttons-grid">
                <button class="admin-btn btn-success" onclick="runCommand('status')">
                    <span class="btn-icon">📊</span>
                    <span class="btn-text">Ver Estado</span>
                    <span class="btn-desc">quick_status.sh</span>
                </button>
                
                <button class="admin-btn btn-success" onclick="runCommand('repair')">
                    <span class="btn-icon">🔧</span>
                    <span class="btn-text">Reparar Workers</span>
                    <span class="btn-desc">autonomous_worker_fix.py</span>
                </button>
                
                <button class="admin-btn btn-warning" onclick="runCommand('restart_daemon')">
                    <span class="btn-icon">🔄</span>
                    <span class="btn-text">Reiniciar Daemon</span>
                    <span class="btn-desc">worker_daemon.sh</span>
                </button>
                
                <button class="admin-btn btn-success" onclick="runCommand('heartbeat')">
                    <span class="btn-icon">💓</span>
                    <span class="btn-text">Forzar Heartbeat</span>
                    <span class="btn-desc">Actualizar BD</span>
                </button>
                
                <button class="admin-btn btn-info" onclick="runCommand('check')">
                    <span class="btn-icon">🔍</span>
                    <span class="btn-text">Verificar Workers</span>
                    <span class="btn-desc">Ver procesos</span>
                </button>
                
                <button class="admin-btn btn-danger" onclick="runCommand('restart_all')">
                    <span class="btn-icon">⚠️</span>
                    <span class="btn-text">Reiniciar Todo</span>
                    <span class="btn-desc">Reinicio completo</span>
                </button>
            </div>
            
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-value" id="workersActive">--</div>
                    <div class="status-label">Workers Activos</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="workersTotal">--</div>
                    <div class="status-label">Workers Totales</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="wusCompleted">--</div>
                    <div class="status-label">WUs Completados</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="bestPnl">--</div>
                    <div class="status-label">Mejor PnL</div>
                </div>
            </div>
        </div>
        
        <!-- Logs -->
        <div class="admin-section">
            <div class="admin-header">
                <div class="admin-icon">📋</div>
                <div>
                    <div class="admin-title">Registro de Acciones</div>
                    <div class="admin-subtitle">Historial de comandos ejecutados</div>
                </div>
            </div>
            <div class="log-section" id="actionLog">
                <div class="log-entry">
                    <span class="log-time">[--:--:--:--]</span>
                    <span class="log-info">🎯 Panel de administración listo</span>
                </div>
            </div>
        </div>
        
        <!-- Enlaces -->
        <div class="admin-section">
            <div class="admin-header">
                <div class="admin-icon">🔗</div>
                <div>
                    <div class="admin-title">Enlaces Rápidos</div>
                    <div class="admin-subtitle">Acceso directo a los dashboards</div>
                </div>
            </div>
            
            <div class="quick-links">
                <a href="http://localhost:8501" class="quick-link" target="_blank">
                    <span class="quick-link-icon">🌐</span>
                    <div>
                        <div class="quick-link-text">Streamlit Interface</div>
                        <div class="quick-link-desc">Interfaz principal</div>
                    </div>
                </a>
                
                <a href="http://localhost:5001" class="quick-link" target="_blank">
                    <span class="quick-link-icon">📊</span>
                    <div>
                        <div class="quick-link-text">Coordinator Dashboard</div>
                        <div class="quick-link-desc">Stats, workers, PnL charts</div>
                    </div>
                </a>
            </div>
        </div>
    </div>
    
    <script>
        function fmt(n, d=2) { return Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}); }

        async function updateSystemStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                document.getElementById('workersActive').textContent = data.workers.active;
                document.getElementById('workersTotal').textContent  = data.workers.total;
                document.getElementById('wusCompleted').textContent  = data.work_units.completed.toLocaleString();
                document.getElementById('bestPnl').textContent       = '$' + fmt(data.best_strategy.pnl, 2);

                // Goal calculations
                // NOTA: el backtester usa $10,000 fijo. El % se calcula sobre esa base.
                // REAL_CAPITAL ($500) solo se usa para mostrar dolares equivalentes.
                const BACKTEST_CAPITAL = 10000;
                const REAL_CAPITAL     = 500;
                const TARGET_DAILY_PCT = 5.0;
                const BACKTEST_DAYS    = 80000 / 1440;
                const bestPnl          = data.best_strategy.pnl || 0;
                const totalReturn      = bestPnl / BACKTEST_CAPITAL * 100;
                const dailyReturnPct   = totalReturn / BACKTEST_DAYS;
                const dailyPnl         = REAL_CAPITAL * (dailyReturnPct / 100);
                const targetTotal      = REAL_CAPITAL * (TARGET_DAILY_PCT/100) * BACKTEST_DAYS;
                const progress         = Math.min(dailyReturnPct / TARGET_DAILY_PCT * 100, 100);
                const multiplier       = targetTotal / Math.max(REAL_CAPITAL*(totalReturn/100), 0.01);
                const wr               = (data.best_strategy.win_rate || 0) * 100;
                const avgPnl           = data.performance.avg_pnl || 0;
                const validCount       = data.performance.valid_results || 0;

                let color, gradient, msg;
                if (progress < 20)      { color='var(--red)';    gradient='linear-gradient(90deg,var(--red),var(--yellow))';  msg=`⚡ Inicio — necesitamos ${fmt(multiplier,1)}x de mejora en PnL diario.`; }
                else if (progress < 50) { color='var(--yellow)'; gradient='linear-gradient(90deg,var(--yellow),var(--blue))'; msg=`📈 Progreso ${fmt(progress,1)}% — seguir optimizando indicadores y leverage.`; }
                else if (progress < 80) { color='var(--blue)';   gradient='linear-gradient(90deg,var(--blue),var(--green))';  msg=`🚀 Muy cerca — ${fmt(100-progress,1)}% restante para el objetivo.`; }
                else                    { color='var(--green)';  gradient='linear-gradient(90deg,#00a845,var(--green))';       msg=`🏆 ¡Objetivo alcanzado! ${fmt(dailyReturnPct,2)}%/día. Listo para live trading.`; }

                document.getElementById('g-daily-pct').style.color  = color;
                document.getElementById('g-badge').style.color      = color;
                document.getElementById('g-daily-pct').textContent  = fmt(dailyReturnPct,2) + '%';
                document.getElementById('g-badge').textContent      = fmt(progress,1) + '%';
                document.getElementById('g-fill').style.width       = progress.toFixed(1) + '%';
                document.getElementById('g-fill').style.background  = gradient;
                document.getElementById('g-daily-pnl').textContent  = '$' + fmt(dailyPnl,2) + '/día';
                document.getElementById('g-total-pnl').textContent  = '$' + fmt(bestPnl,2);
                document.getElementById('g-total-target').textContent = 'obj: $' + fmt(targetTotal,0);
                document.getElementById('g-total-ret').textContent  = fmt(totalReturn,2) + '%';
                document.getElementById('g-total-ret-sub').textContent = 'obj: ' + fmt(TARGET_DAILY_PCT * BACKTEST_DAYS,0) + '%';
                document.getElementById('g-mult').textContent       = fmt(multiplier,1) + 'x';
                document.getElementById('g-wr').textContent         = fmt(wr,1) + '%';
                document.getElementById('g-wr').style.color         = wr>=60?'var(--green)':wr>=50?'var(--yellow)':'var(--red)';
                document.getElementById('g-avg').textContent        = '$' + fmt(avgPnl,2);
                document.getElementById('g-valid-count').textContent = validCount.toLocaleString() + ' resultados';
                document.getElementById('g-msg').textContent        = msg;

            } catch (e) {
                console.log('No se pudo actualizar estado:', e);
            }
        }
        
        function runCommand(cmd) {
            const log = document.getElementById('actionLog');
            const time = new Date().toLocaleTimeString();
            
            const commands = {
                'status': { msg: '📊 Verificando estado...', type: 'info' },
                'repair': { msg: '🔧 Reparando workers...', type: 'warning' },
                'restart_daemon': { msg: '🔄 Reiniciando daemon...', type: 'warning' },
                'heartbeat': { msg: '💓 Forzando heartbeats...', type: 'info' },
                'check': { msg: '🔍 Verificando procesos...', type: 'info' },
                'restart_all': { msg: '⚠️ Reiniciando sistema...', type: 'error' }
            };
            
            const cmdData = commands[cmd] || { msg: 'Ejecutando...', type: 'info' };
            
            log.innerHTML = `
                <div class="log-entry">
                    <span class="log-time">[${time}]</span>
                    <span class="log-${cmdData.type}">${cmdData.msg}</span>
                </div>
            ` + log.innerHTML;
            
            // Execute via API
            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            }).then(r => r.json()).then(data => {
                setTimeout(() => {
                    const resultLog = document.getElementById('actionLog');
                    const resultTime = new Date().toLocaleTimeString();
                    resultLog.innerHTML = `
                        <div class="log-entry">
                            <span class="log-time">[${resultTime}]</span>
                            <span class="log-success">✅ ${data.message}</span>
                        </div>
                    ` + resultLog.innerHTML;
                    updateSystemStatus();
                }, 1000);
            });
        }
        
        updateSystemStatus();
        setInterval(updateSystemStatus, 5000);
    </script>
</body>
</html>"""

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
    
    c.execute("SELECT COUNT(*) as active FROM workers WHERE (CAST(strftime('%s','now') AS INTEGER) - last_seen) < 300")
    active = c.fetchone()['active']

    c.execute("SELECT COUNT(*) as total_w FROM workers")
    total_w = c.fetchone()['total_w']

    c.execute("SELECT MAX(pnl) as best FROM results WHERE pnl > 0 AND pnl < 5000 AND trades >= 5")
    best = c.fetchone()['best'] or 0

    c.execute("SELECT AVG(pnl) FROM results WHERE pnl > 0 AND pnl < 5000 AND trades >= 5")
    avg_pnl = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM results WHERE pnl > 0 AND pnl < 5000 AND trades >= 5")
    valid_results = c.fetchone()[0]

    c.execute("SELECT MAX(win_rate) FROM results WHERE pnl > 0 AND pnl < 5000 AND trades >= 5")
    best_wr = c.fetchone()[0] or 0

    conn.close()

    return jsonify({
        'workers': {'active': active, 'total': total_w},
        'work_units': {'completed': completed, 'total': total},
        'best_strategy': {'pnl': best, 'win_rate': best_wr},
        'performance': {'avg_pnl': avg_pnl, 'valid_results': valid_results}
    })

@app.route('/api/execute', methods=['POST'])
def execute_command():
    data = request.json
    cmd = data.get('command', '')
    
    project_dir = PROJECT_DIR
    
    commands = {
        'status': f'cd "{project_dir}" && bash quick_status.sh',
        'repair': f'cd "{project_dir}" && python3 autonomous_worker_fix.py',
        'restart_daemon': 'cd ~/.bittrader_worker && bash worker_daemon.sh',
        'heartbeat': f'cd "{project_dir}" && sqlite3 coordinator.db "UPDATE workers SET last_seen = julianday(\'now\') WHERE id LIKE \'%MacBook%\'"',
        'check': 'ps aux | grep crypto_worker | grep -v grep',
        'restart_all': 'pkill -f crypto_worker; sleep 2; cd ~/.bittrader_worker && bash worker_daemon.sh &'
    }
    
    if cmd in commands:
        try:
            os.system(commands[cmd])
            return jsonify({'success': True, 'message': f'Comando {cmd} ejecutado'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    return jsonify({'success': False, 'message': 'Comando no reconocido'})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  🎛️ PANEL DE ADMINISTRACIÓN DEL CLUSTER")
    print("="*60)
    print("\n🌐 Abriendo en: http://localhost:5007")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5007, debug=False)
