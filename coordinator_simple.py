#!/usr/bin/env python3
"""Coordinator con dashboard simple y reportes"""

from flask import Flask, jsonify, Response
import sqlite3
import time
import json
from datetime import datetime

app = Flask(__name__)
# Usar la ruta completa de la base de datos
DATABASE = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def analyze_results():
    """Analiza todos los resultados de optimización"""
    conn = get_db()
    c = conn.cursor()
    
    # Stats generales - excluir valores hardcoded
    c.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) as positive,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_pnl,
            MIN(pnl) as min_pnl,
            AVG(pnl) filter (where pnl > 0) as avg_positive
        FROM results
        WHERE NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
    """)
    stats = dict(c.fetchone())
    
    # Distribución por PnL - excluir hardcoded
    c.execute("""
        SELECT 
            CASE 
                WHEN pnl >= 400 THEN 'Alto (400+)'
                WHEN pnl >= 200 THEN 'Medio (200-400)'
                WHEN pnl >= 100 THEN 'Bajo-Medio (100-200)'
                WHEN pnl >= 50 THEN 'Bajo (50-100)'
                ELSE 'Muy Bajo (<50)'
            END as range,
            COUNT(*) as count,
            AVG(pnl) as avg
        FROM results
        WHERE pnl > 0
          AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
        GROUP BY range
        ORDER BY avg DESC
    """)
    distribution = [dict(row) for row in c.fetchall()]
    
    # Mejores estrategias - excluir hardcoded
    c.execute("""
        SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
               w.strategy_params, r.worker_id
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15)
        ORDER BY r.pnl DESC
        LIMIT 20
    """)
    top_strategies = []
    for row in c.fetchall():
        try:
            params = json.loads(row['strategy_params'])
        except:
            params = {}
        top_strategies.append({
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'params': params,
            'worker': row['worker_id']
        })
    
    # Análisis por parámetros de trabajo
    c.execute("""
        SELECT 
            w.id,
            w.strategy_params,
            COUNT(*) as total_results,
            AVG(r.pnl) as avg_pnl,
            MAX(r.pnl) as max_pnl,
            AVG(r.pnl) filter (where r.pnl > 0) as avg_positive
        FROM work_units w
        JOIN results r ON w.id = r.work_unit_id
        WHERE r.pnl > 0
          AND NOT (r.trades = 10 AND r.win_rate = 0.65 AND r.sharpe_ratio = 1.5 AND r.max_drawdown = 0.15)
        GROUP BY w.id
        ORDER BY avg_pnl DESC
        LIMIT 10
    """)
    work_unit_analysis = []
    for row in c.fetchall():
        try:
            params = json.loads(row['strategy_params'])
        except:
            params = {}
        work_unit_analysis.append({
            'id': row['id'],
            'params': params,
            'total_results': row['total_results'],
            'avg_pnl': row['avg_pnl'],
            'max_pnl': row['max_pnl'],
            'avg_positive': row['avg_positive']
        })
    
    # Workers performance - excluir hardcoded
    c.execute("""
        SELECT worker_id, COUNT(*) as results, AVG(pnl) as avg_pnl, MAX(pnl) as max_pnl
        FROM results
        WHERE pnl > 0
          AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
        GROUP BY worker_id
        ORDER BY avg_pnl DESC
        LIMIT 10
    """)
    worker_performance = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return {
        'stats': stats,
        'distribution': distribution,
        'top_strategies': top_strategies,
        'work_unit_analysis': work_unit_analysis,
        'worker_performance': worker_performance
    }

def generate_recommendations(data):
    """Genera recomendaciones basadas en el análisis"""
    recommendations = []
    
    stats = data['stats']
    
    # Analizar distribución
    high_pnl = sum(d['count'] for d in data['distribution'] if '400+' in d['range'])
    total = sum(d['count'] for d in data['distribution'])
    success_rate = (high_pnl / total * 100) if total > 0 else 0
    
    if success_rate < 5:
        recommendations.append({
            'priority': 'ALTA',
            'area': 'Parámetros de Búsqueda',
            'suggestion': f'Solo el {success_rate:.1f}% de estrategias superan $400 PnL. Considera:'
        })
        recommendations.append({
            'priority': 'ALTA',
            'area': 'Parámetros de Búsqueda',
            'suggestion': '- Aumentar population_size a 50-100 (ahora: 20-30)'
        })
        recommendations.append({
            'priority': 'ALTA',
            'area': 'Parámetros de Búsqueda',
            'suggestion': '- Aumentar generations a 150-200 (ahora: 50-100)'
        })
    
    # Analizar mejores work units
    if data['work_unit_analysis']:
        best_wu = data['work_unit_analysis'][0]
        best_params = best_wu['params']
        
        if best_params.get('population_size', 0) < 50:
            recommendations.append({
                'priority': 'MEDIA',
                'area': 'Escala',
                'suggestion': f'El mejor work unit tuvo population_size={best_params.get("population_size")}. '
                             'Con Numba JIT, puedes aumentar a 100+ sin slowdown significativo.'
            })
        
        if best_params.get('generations', 0) < 150:
            recommendations.append({
                'priority': 'MEDIA',
                'area': 'Profundidad',
                'suggestion': f'Generaciones={best_params.get("generations")}. Más generaciones = mejor convergencia.'
            })
    
    # Analizar workers
    if len(data['worker_performance']) < 3:
        recommendations.append({
            'priority': 'MEDIA',
            'area': 'Distribución',
            'suggestion': 'Tienes menos de 3 workers activos. Considera agregar workers en Linux ROG o MacBook Air.'
        })
    
    # Recomendaciones generales
    recommendations.append({
        'priority': 'BAJA',
        'area': 'Datos',
        'suggestion': 'Considera usar datos de 1-minuto en lugar de 5-min para más granularity (el archivo BTC-USD_ONE_MINUTE.csv tiene 100K+ candles).'
    })
    
    recommendations.append({
        'priority': 'BAJA',
        'area': 'Risk Level',
        'suggestion': 'Prueba risk_level=HIGH para estrategias más agresivas, o LOW para conservadoras.'
    })
    
    return recommendations

# Calcular total para la barra de distribución
try:
    conn_temp = sqlite3.connect(DATABASE)
    c_temp = conn_temp.cursor()
    c_temp.execute("SELECT COUNT(*) FROM results WHERE pnl > 0 AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)")
    DIST_TOTAL = c_temp.fetchone()[0]
    conn_temp.close()
except:
    DIST_TOTAL = 1

HTML = f"""<!DOCTYPE html>
<html>
<head>
    <title>Strategy Miner</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <style>
        body {{ font-family: sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 20px; margin: 0; }}
        h1 {{ text-align: center; background: linear-gradient(90deg, #00d4ff, #7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .stat {{ background: rgba(255,255,255,0.1); border-radius: 15px; padding: 25px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .section {{ background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; margin: 20px 0; }}
        .section h2 {{ margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ background: rgba(124, 58, 237, 0.3); }}
        .active {{ background: #10b981; padding: 3px 10px; border-radius: 10px; color: white; }}
        .inactive {{ background: #ef4444; padding: 3px 10px; border-radius: 10px; color: white; }}
        .btn {{ background: linear-gradient(90deg, #00d4ff, #7c3aed); border: none; color: white; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 1em; margin: 5px; }}
        .btn:hover {{ opacity: 0.9; }}
        .actions {{ text-align: center; margin: 20px 0; }}
        .range-bar {{ height: 20px; background: linear-gradient(90deg, #10b981, #f59e0b, #ef4444); border-radius: 10px; margin: 10px 0; }}
        .metric {{ font-size: 0.9em; color: #94a3b8; }}
        .status-active {{ color: #10b981; }}
        .status-inactive {{ color: #ef4444; }}
        .worker-count {{ font-size: 0.8em; color: #94a3b8; }}
    </style>
</head>
<body>
    <h1>🧬 Strategy Miner Dashboard</h1>
    <div class="actions">
        <button class="btn" onclick="generateReport()">📊 Generar Reporte Completo</button>
        <button class="btn" onclick="window.open('/api/report', '_blank')">📄 Ver Reporte JSON</button>
        <button class="btn" onclick="location.reload()">🔄 Refrescar</button>
    </div>
    <div class="stats">
        <div class="stat"><div class="stat-value" id="wu-total">-</div><div>Total WUs</div></div>
        <div class="stat"><div class="stat-value" id="wu-completed">-</div><div>Completados</div></div>
        <div class="stat"><div class="stat-value" id="wu-workers">-</div><div>Workers</div></div>
        <div class="stat"><div class="stat-value" id="wu-best">$0</div><div>Best PnL</div></div>
    </div>
    <div class="section">
        <h2>📊 Best Strategy (Métricas Reales)</h2>
        <div id="best-metrics" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; padding: 15px;">
            <div style="background: rgba(16, 185, 129, 0.2); padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.8em; font-weight: bold; color: #10b981;" id="best-pnl">$0</div>
                <div class="metric">PnL</div>
            </div>
            <div style="background: rgba(59, 130, 246, 0.2); padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.8em; font-weight: bold; color: #3b82f6;" id="best-trades">0</div>
                <div class="metric">Trades</div>
            </div>
            <div style="background: rgba(245, 158, 11, 0.2); padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.8em; font-weight: bold; color: #f59e0b;" id="best-winrate">0%</div>
                <div class="metric">Win Rate</div>
            </div>
            <div style="background: rgba(139, 92, 246, 0.2); padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.8em; font-weight: bold; color: #8b5cf6;" id="best-sharpe">0.00</div>
                <div class="metric">Sharpe</div>
            </div>
            <div style="background: rgba(239, 68, 68, 0.2); padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 1.8em; font-weight: bold; color: #ef4444;" id="best-drawdown">0%</div>
                <div class="metric">Max Drawdown</div>
            </div>
        </div>
    </div>
    <div class="section">
        <h2>📈 Distribución PnL</h2>
        <div id="distribution"></div>
    </div>
    <div class="section">
        <h2>🏆 Leaderboard (Top 10)</h2>
        <table id="leaderboard"></table>
    </div>
    <div class="section">
        <h2>📊 Workers (Todos)</h2>
        <div class="worker-count" id="worker-count">Cargando...</div>
        <table id="workers"></table>
    </div>
    <script>
        const DIST_TOTAL = {DIST_TOTAL};
        const LOAD_INTERVAL = 15000;  // 15 segundos
        
        async function load() {{
            try {{
                let s = await fetch('/api/status').then(r => r.json());
                document.getElementById('wu-total').textContent = s.work_units.total;
                document.getElementById('wu-completed').textContent = s.work_units.completed;
                document.getElementById('wu-workers').textContent = s.workers.active;
                
                if (s.best_strategy && s.best_strategy.pnl) {{
                    document.getElementById('wu-best').textContent = '$' + s.best_strategy.pnl.toFixed(2);
                    document.getElementById('best-pnl').textContent = '$' + s.best_strategy.pnl.toFixed(2);
                    document.getElementById('best-trades').textContent = s.best_strategy.trades;
                    document.getElementById('best-winrate').textContent = (s.best_strategy.win_rate * 100).toFixed(1) + '%';
                    document.getElementById('best-sharpe').textContent = s.best_strategy.sharpe_ratio.toFixed(2);
                    document.getElementById('best-drawdown').textContent = (s.best_strategy.max_drawdown * 100).toFixed(1) + '%';
                }}
                
                // Distribution
                let dist = await fetch('/api/distribution').then(r => r.json());
                let distHtml = '';
                dist.distribution.forEach(d => {{
                    let pct = (d.count / DIST_TOTAL) * 100;
                    distHtml += '<div style="display:flex;justify-content:space-between;margin-top:10px;">';
                    distHtml += '<span>' + d.range + '</span><span>$' + d.avg.toFixed(2) + ' avg (' + d.count + ' estrategias)</span></div>';
                    distHtml += '<div class="range-bar" style="width:' + Math.min(pct * 3, 100) + '%"></div>';
                }});
                document.getElementById('distribution').innerHTML = distHtml || '<p>Sin datos aún</p>';
                
                // Leaderboard
                let lb = await fetch('/api/leaderboard').then(r => r.json());
                let lbHtml = '<tr><th>#</th><th>Maquina</th><th>WUs</th><th>Horas</th><th>Estado</th></tr>';
                lb.leaderboard.slice(0, 10).forEach((w, i) => {{
                    lbHtml += '<tr><td>' + (i+1) + '</td><td>' + w.friendly_name + '</td><td><b>' + w.work_units + '</b></td><td>' + w.execution_time_hours + 'h</td><td><span class="' + w.status + '">' + w.status + '</span></td></tr>';
                }});
                document.getElementById('leaderboard').innerHTML = lbHtml;
                
                // All Workers (both active and inactive)
                let ws = await fetch('/api/workers').then(r => r.json());
                let activeCount = ws.workers.filter(w => w.status === 'active').length;
                let inactiveCount = ws.workers.filter(w => w.status === 'inactive').length;
                document.getElementById('worker-count').textContent = '🟢 ' + activeCount + ' activos | 🔴 ' + inactiveCount + ' inactivos';
                
                let wsHtml = '<tr><th>Maquina</th><th>WUs</th><th>Última Actividad</th><th>Estado</th></tr>';
                ws.workers.forEach(w => {{
                    let mins = w.last_seen_minutes_ago.toFixed(0);
                    let timeStr = mins < 60 ? mins + ' min' : (mins / 60).toFixed(1) + ' horas';
                    wsHtml += '<tr>';
                    wsHtml += '<td>' + w.friendly_name + '</td>';
                    wsHtml += '<td>' + w.work_units_completed + '</td>';
                    wsHtml += '<td>' + timeStr + '</td>';
                    wsHtml += '<td><span class="' + w.status + '">' + w.status + '</span></td>';
                    wsHtml += '</tr>';
                }});
                document.getElementById('workers').innerHTML = wsHtml || '<tr><td colspan="4">Cargando...</td></tr>';
                
            }} catch (e) {{
                console.error('Error loading data:', e);
            }}
        }}
        
        async function generateReport() {{
            let report = await fetch('/api/report').then(r => r.json());
            let win = window.open('', '_blank');
            win.document.write('<pre style="background:#1a1a2e;color:white;padding:20px;font-size:12px;">' + JSON.stringify(report, null, 2) + '</pre>');
        }}
        
        // Load immediately and then periodically
        load();
        setInterval(load, LOAD_INTERVAL);
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
    c.execute("SELECT COUNT(*) as active FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
    active = c.fetchone()['active']
    
    # Buscar mejor estrategia con métricas REALES (excluir hardcoded)
    c.execute("""
        SELECT pnl, trades, win_rate, sharpe_ratio, max_drawdown 
        FROM results 
        WHERE pnl > 0 
          AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
        ORDER BY pnl DESC 
        LIMIT 1
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
        'work_units': {'total': total, 'completed': completed},
        'workers': {'active': active},
        'best_strategy': best_data
    })

@app.route('/api/distribution')
def distribution():
    """Retorna distribución de PnL por rango"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT 
            CASE 
                WHEN pnl >= 400 THEN 'Alto (400+)'
                WHEN pnl >= 200 THEN 'Medio (200-400)'
                WHEN pnl >= 100 THEN 'Bajo-Medio (100-200)'
                WHEN pnl >= 50 THEN 'Bajo (50-100)'
                ELSE 'Muy Bajo (<50)'
            END as range,
            COUNT(*) as count,
            AVG(pnl) as avg
        FROM results
        WHERE pnl > 0
          AND NOT (trades = 10 AND win_rate = 0.65 AND sharpe_ratio = 1.5 AND max_drawdown = 0.15)
        GROUP BY range
        ORDER BY avg DESC
    """)
    dist = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'distribution': dist})

@app.route('/api/report')
def report():
    """Retorna reporte completo de optimización"""
    data = analyze_results()
    recommendations = generate_recommendations(data)
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'statistics': data['stats'],
        'distribution': data['distribution'],
        'top_strategies': data['top_strategies'][:10],
        'work_unit_analysis': data['work_unit_analysis'][:5],
        'worker_performance': data['worker_performance'],
        'recommendations': recommendations
    })

@app.route('/api/leaderboard')
def leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, work_units_completed, total_execution_time, last_seen FROM workers ORDER BY work_units_completed DESC")
    now = time.time()
    leaders = []
    for row in c.fetchall():
        last_seen = row['last_seen'] if 'last_seen' in row.keys() else None
        alive = False
        if last_seen:
            mins = (now - (last_seen - 2440587.5) * 86400.0) / 60.0
            alive = mins < 10
        leaders.append({
            'friendly_name': row['id'].replace('Enders-MacBook-Pro', '💻 MacBook Pro').replace('Enders-MacBook-Air', '🪶 MacBook Air').replace('Asus-Dorada', '🌐 Asus Dorada').replace('ender-rog', '🔴 Linux ROG').replace('_Linux', '').replace('_Darwin', ''),
            'work_units': row['work_units_completed'],
            'execution_time_hours': round(row['total_execution_time'] / 3600, 1),
            'status': 'active' if alive else 'inactive'
        })
    conn.close()
    return jsonify({'leaderboard': leaders})

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
            'friendly_name': row['id'].replace('Enders-MacBook-Pro', '💻 MacBook Pro').replace('Enders-MacBook-Air', '🪶 MacBook Air').replace('Asus-Dorada', '🌐 Asus Dorada').replace('ender-rog', '🔴 Linux ROG').replace('_Linux', '').replace('_Darwin', ''),
            'work_units_completed': row['work_units_completed'],
            'last_seen_minutes_ago': mins,
            'status': 'active' if mins < 10 else 'inactive'
        })
    conn.close()
    return jsonify({'workers': ws})

if __name__ == '__main__':
    print(f"🧬 Dashboard: http://localhost:5005")
    print(f"📁 DB: {DATABASE}")
    app.run(host='0.0.0.0', port=5005, debug=False)
