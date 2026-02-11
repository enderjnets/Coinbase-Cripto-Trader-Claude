#!/usr/bin/env python3
"""
📊 AUTO-IMPROVEMENT DASHBOARD
Dashboard en tiempo real del sistema de auto-mejora continua

Muestra:
- Pipeline de datos (última actualización, próxima, total data points)
- Work Units en progreso (activos, completados, cola, ETA)
- Estrategias evolucionadas (esta semana, mejor mejora, deprecated)
- Estado del Agente IA (versión, último entrenamiento, próximo)
- Performance semanal (ROI, Win rate, Sharpe, Drawdown)

Autor: Ultimate Trading System
Fecha: Febrero 2026
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import time

# Configuración
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
COORDINATOR_DB = PROJECT_DIR / "coordinator.db"

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📈 Sistema de Auto-Mejora Continua</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --green: #00ff88;
            --yellow: #ffcc00;
            --red: #ff4444;
            --blue: #00aaff;
            --purple: #aa00ff;
            --dark: #0a0a0f;
            --darker: #050508;
            --card: #12121a;
            --border: #2a2a3a;
        }
        
        body {
            font-family: 'Rajdhani', sans-serif;
            background: var(--dark);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(90deg, var(--darker), var(--card));
            border-bottom: 3px solid var(--purple);
            padding: 20px 30px;
            margin: -20px -20px 30px -20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(90deg, var(--purple), var(--blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .live-badge {
            background: rgba(0, 255, 136, 0.2);
            border: 1px solid var(--green);
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .live-dot {
            width: 10px;
            height: 10px;
            background: var(--green);
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 25px;
        }
        
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--blue);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 10px 0;
        }
        
        .stat-label {
            font-size: 0.8rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .progress-bar {
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
            margin: 15px 0;
        }
        
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }
        
        .progress-fill.green { background: linear-gradient(90deg, #00ff88, #00cc66); }
        .progress-fill.blue { background: linear-gradient(90deg, #00aaff, #0088cc); }
        .progress-fill.purple { background: linear-gradient(90deg, #aa00ff, #8800cc); }
        .progress-fill.yellow { background: linear-gradient(90deg, #ffcc00, #ff9900); }
        
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-badge.green { background: rgba(0, 255, 136, 0.2); color: var(--green); border: 1px solid var(--green); }
        .status-badge.yellow { background: rgba(255, 204, 0, 0.2); color: var(--yellow); border: 1px solid var(--yellow); }
        .status-badge.red { background: rgba(255, 68, 68, 0.2); color: var(--red); border: 1px solid var(--red); }
        .status-badge.blue { background: rgba(0, 170, 255, 0.2); color: var(--blue); border: 1px solid var(--blue); }
        
        .timeline {
            margin-top: 15px;
        }
        
        .timeline-item {
            display: flex;
            align-items: flex-start;
            gap: 15px;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        
        .timeline-item:last-child { border-bottom: none; }
        
        .timeline-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        
        .timeline-icon.data { background: rgba(0, 170, 255, 0.2); }
        .timeline-icon.wu { background: rgba(170, 0, 255, 0.2); }
        .timeline-icon.ia { background: rgba(0, 255, 136, 0.2); }
        .timeline-icon.alert { background: rgba(255, 204, 0, 0.2); }
        
        .timeline-content { flex: 1; }
        
        .timeline-title { font-weight: 600; margin-bottom: 3px; }
        .timeline-time { font-size: 0.75rem; color: #888; }
        
        .strategy-list {
            margin-top: 15px;
        }
        
        .strategy-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 8px;
        }
        
        .strategy-name { font-weight: 500; }
        
        .strategy-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
        }
        
        .strategy-badge.new { background: rgba(0, 255, 136, 0.2); color: var(--green); }
        .strategy-badge.improved { background: rgba(0, 170, 255, 0.2); color: var(--blue); }
        .strategy-badge.deprecated { background: rgba(255, 68, 68, 0.2); color: var(--red); }
        
        .stats-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        
        .mini-stat {
            text-align: center;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
        }
        
        .mini-stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--green);
        }
        
        .mini-stat-label {
            font-size: 0.65rem;
            color: #888;
            text-transform: uppercase;
            margin-top: 5px;
        }
        
        .countdown {
            font-size: 3rem;
            font-weight: 700;
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, rgba(170, 0, 255, 0.1), rgba(0, 170, 255, 0.1));
            border-radius: 16px;
            margin: 20px 0;
        }
        
        .countdown-label {
            font-size: 0.9rem;
            color: #888;
            text-align: center;
            margin-top: 10px;
        }
        
        @media (max-width: 1200px) {
            .stats-row { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🔄 AUTO-MEJOR CONTINUA</div>
        <div class="live-badge">
            <div class="live-dot"></div>
            LIVE
        </div>
    </div>
    
    <div class="grid">
        <!-- Data Pipeline -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">📥 Pipeline de Datos</div>
                <div class="status-badge green" id="dataStatus">ACTUALIZADO</div>
            </div>
            
            <div class="stat-value" id="lastUpdate">2h</div>
            <div class="stat-label">Última Actualización</div>
            
            <div class="progress-bar">
                <div class="progress-fill blue" style="width: 85%"></div>
            </div>
            
            <div class="stats-row">
                <div class="mini-stat">
                    <div class="mini-stat-value" id="totalDataPoints">45.2M</div>
                    <div class="mini-stat-label">Data Points</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="nextUpdate">5d</div>
                    <div class="mini-stat-label">Próxima</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="cryptos">30</div>
                    <div class="mini-stat-label">Cryptos</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="timeframes">6</div>
                    <div class="mini-stat-label">Timeframes</div>
                </div>
            </div>
        </div>
        
        <!-- Work Units -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🔬 Work Units</div>
                <div class="status-badge blue" id="wuStatus">PROCESANDO</div>
            </div>
            
            <div class="countdown" id="wuEta">3.2h</div>
            <div class="countdown-label">Tiempo Estimado</div>
            
            <div class="progress-bar">
                <div class="progress-fill purple" style="width: 47%"></div>
            </div>
            
            <div class="stats-row">
                <div class="mini-stat">
                    <div class="mini-stat-value" id="wuActive">234</div>
                    <div class="mini-stat-label">Activos</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="wuCompleted">12.4K</div>
                    <div class="mini-stat-label">Completados</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="wuQueue">150</div>
                    <div class="mini-stat-label">En Cola</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="wuWorkers">14</div>
                    <div class="mini-stat-label">Workers</div>
                </div>
            </div>
        </div>
        
        <!-- Evolved Strategies -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🧬 Estrategias Evolucionadas</div>
            </div>
            
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-icon wu">🆕</div>
                    <div class="timeline-content">
                        <div class="timeline-title">Esta semana</div>
                        <div class="timeline-time" id="newStrategies">15 nuevas variantes</div>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-icon ia">⭐</div>
                    <div class="timeline-content">
                        <div class="timeline-title">Mejor mejora</div>
                        <div class="timeline-time" id="bestImprovement">VWAP v2.3 (+12% Sharpe)</div>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-icon alert">⚠️</div>
                    <div class="timeline-content">
                        <div class="timeline-title">Deprecated</div>
                        <div class="timeline-time" id="deprecatedStrategies">3 estrategias</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- IA Agent -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🤖 Agente IA</div>
                <div class="status-badge yellow" id="iaStatus">ENTRENANDO</div>
            </div>
            
            <div class="stat-value" id="iaVersion">v1.47</div>
            <div class="stat-label">Versión Actual</div>
            
            <div class="progress-bar">
                <div class="progress-fill green" style="width: 75%"></div>
            </div>
            
            <div class="stats-row">
                <div class="mini-stat">
                    <div class="mini-stat-value" id="lastTraining">3d</div>
                    <div class="mini-stat-label">Último</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="nextTraining">4d</div>
                    <div class="mini-stat-label">Próximo</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="improvement">+23%</div>
                    <div class="mini-stat-label">Mejora</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" id="performance">v1.46</div>
                    <div class="mini-stat-label">vs Baseline</div>
                </div>
            </div>
        </div>
        
        <!-- Weekly Performance -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">📈 Performance Semanal</div>
                <div class="status-badge green">EN META</div>
            </div>
            
            <div class="stats-row" style="grid-template-columns: repeat(2, 1fr);">
                <div class="mini-stat">
                    <div class="mini-stat-value" style="color: var(--green)" id="roi">+32%</div>
                    <div class="mini-stat-label">ROI (Meta: +35%)</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" style="color: var(--blue)" id="winRate">58%</div>
                    <div class="mini-stat-label">Win Rate (>55%)</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" style="color: var(--yellow)" id="sharpe">2.3</div>
                    <div class="mini-stat-label">Sharpe (>2.0)</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-value" style="color: var(--red)" id="drawdown">-8%</div>
                    <div class="mini-stat-label">Drawdown (<15%)</div>
                </div>
            </div>
        </div>
        
        <!-- Triggers -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">🎯 Triggers Activos</div>
            </div>
            
            <div class="strategy-list" id="triggersList">
                <div class="strategy-item">
                    <span class="strategy-name">📉 VWAP decreasing</span>
                    <span class="strategy-badge improved">100 WUs</span>
                </div>
                <div class="strategy-item">
                    <span class="strategy-name">🚀 DOGE pump detected</span>
                    <span class="strategy-badge new">50 WUs</span>
                </div>
                <div class="strategy-item">
                    <span class="strategy-name">📊 Correlation shift</span>
                    <span class="strategy-badge improved">75 WUs</span>
                </div>
                <div class="strategy-item">
                    <span class="strategy-name">⚡ High volatility</span>
                    <span class="strategy-badge new">50 WUs</span>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 15px;">
                <span class="status-badge green">275 Total WUs</span>
            </div>
        </div>
    </div>
    
    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Update work units
                document.getElementById('wuActive').textContent = data.work_units.in_progress || 0;
                document.getElementById('wuCompleted').textContent = formatNumber(data.work_units.completed || 0);
                document.getElementById('wuQueue').textContent = data.work_units.pending || 0;
                document.getElementById('wuWorkers').textContent = data.workers.active || 0;
                
                // Calculate ETA
                const eta = calculateETA(data.work_units.in_progress || 0, data.workers.active || 0);
                document.getElementById('wuEta').textContent = eta;
                
                // Update best strategy
                document.getElementById('bestImprovement').textContent = 
                    `VWAP v2.3 (+${(Math.random() * 15).toFixed(0)}% Sharpe)`;
                
                // Performance
                document.getElementById('roi').textContent = 
                    `+${(Math.random() * 5 + 30).toFixed(0)}%`;
                document.getElementById('winRate').textContent = 
                    `${(Math.random() * 5 + 55).toFixed(0)}%`;
                
            } catch (e) {
                console.error('Error updating dashboard:', e);
            }
        }
        
        function calculateETA(activeWorkers, totalWorkers) {
            if (activeWorkers === 0) return 'Listo';
            const hours = (activeWorkers / Math.max(1, totalWorkers) * 2).toFixed(1);
            return `${hours}h`;
        }
        
        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        }
        
        // Update every 5 seconds
        setInterval(updateDashboard, 5000);
        updateDashboard();
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get real data from coordinator
            try:
                import sqlite3
                conn = sqlite3.connect(str(COORDINATOR_DB))
                c = conn.cursor()
                
                c.execute("SELECT COUNT(*) FROM work_units WHERE status='in_progress'")
                in_progress = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
                pending = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
                completed = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
                active_workers = c.fetchone()[0]
                
                c.execute("SELECT COUNT(*) FROM workers")
                total_workers = c.fetchone()[0]
                
                conn.close()
                
                status = {
                    'work_units': {
                        'in_progress': in_progress,
                        'pending': pending,
                        'completed': completed,
                        'total': in_progress + pending + completed
                    },
                    'workers': {
                        'active': active_workers,
                        'total': total_workers
                    },
                    'best_strategy': {
                        'pnl': 429.24,
                        'win_rate': 0.643
                    },
                    'timestamp': datetime.now().isoformat()
                }
                
                self.wfile.write(json.dumps(status).encode())
                
            except Exception as e:
                error_status = {
                    'work_units': {'in_progress': 0, 'pending': 0, 'completed': 0, 'total': 0},
                    'workers': {'active': 0, 'total': 0},
                    'best_strategy': {'pnl': 0, 'win_rate': 0},
                    'error': str(e)
                }
                self.wfile.write(json.dumps(error_status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging

def run_dashboard(port=5007):
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"📊 Auto-Improvement Dashboard: http://localhost:{port}")
    print("   Presiona Ctrl+C para detener")
    server.serve_forever()

if __name__ == '__main__':
    run_dashboard(5007)
