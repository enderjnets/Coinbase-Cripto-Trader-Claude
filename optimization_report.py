#!/usr/bin/env python3
"""
Optimization Report Generator
Genera reportes detallados de optimización con análisis estadístico
y sugerencias de mejora basadas en los resultados.
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict
import sys

DB_PATH = "coordinator.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def analyze_results():
    """Analiza todos los resultados de optimización"""
    conn = get_db()
    c = conn.cursor()
    
    # Stats generales
    c.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) as positive,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_pnl,
            MIN(pnl) as min_pnl,
            AVG(pnl) filter (where pnl > 0) as avg_positive
        FROM results
    """)
    stats = dict(c.fetchone())
    
    # Distribución por PnL
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
        GROUP BY range
        ORDER BY avg DESC
    """)
    distribution = [dict(row) for row in c.fetchall()]
    
    # Mejores estrategias
    c.execute("""
        SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
               w.strategy_params, r.worker_id
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
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
            w.strategy_params,
            COUNT(*) as total_results,
            AVG(r.pnl) as avg_pnl,
            MAX(r.pnl) as max_pnl,
            AVG(r.pnl) filter (where r.pnl > 0) as avg_positive
        FROM work_units w
        JOIN results r ON w.id = r.work_unit_id
        WHERE r.pnl > 0
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
            'params': params,
            'total_results': row['total_results'],
            'avg_pnl': row['avg_pnl'],
            'max_pnl': row['max_pnl'],
            'avg_positive': row['avg_positive']
        })
    
    # Workers performance
    c.execute("""
        SELECT worker_id, COUNT(*) as results, AVG(pnl) as avg_pnl, MAX(pnl) as max_pnl
        FROM results
        WHERE pnl > 0
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
        'suggestion': 'Prueba risk_level=HIGH para estrategias más agresivas, o LOW para保守的 (conservadoras).'
    })
    
    return recommendations

def generate_report():
    """Genera el reporte completo"""
    data = analyze_results()
    recommendations = generate_recommendations(data)
    
    report = f"""
================================================================================
                    REPORTE DE OPTIMIZACIÓN - STRATEGY MINER
                    Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

📊 ESTADÍSTICAS GENERALES
--------------------------------------------------------------------------------
Total de resultados:        {data['stats']['total']:,}
Resultados positivos:       {data['stats']['positive']:,}
Promedio PnL (todos):       ${data['stats']['avg_pnl']:.2f}
Promedio PnL (positivos):   ${data['stats']['avg_positive']:.2f}
PnL máximo:                 ${data['stats']['max_pnl']:.2f}
PnL mínimo:                 ${data['stats']['min_pnl']:.2f}

📈 DISTRIBUCIÓN POR RANGO DE PnL
--------------------------------------------------------------------------------
"""
    for d in data['distribution']:
        bar = '█' * int(d['avg'] / 10)
        report += f"{d['range']:25} | {d['count']:5} estrategias | Avg: ${d['avg']:.2f} {bar}\n"
    
    report += f"""
🏆 TOP 10 MEJORES ESTRATEGIAS
--------------------------------------------------------------------------------
"""
    for i, s in enumerate(data['top_strategies'][:10], 1):
        params = s['params']
        pop = params.get('population_size', 'N/A')
        gen = params.get('generations', 'N/A')
        risk = params.get('risk_level', 'N/A')
        data_file = params.get('data_file', 'N/A')
        
        report += f"""
{i:2}. PnL: ${s['pnl']:.2f} | Trades: {s['trades']} | Win Rate: {s['win_rate']:.1%}
    Sharpe: {s['sharpe']:.2f} | Max Drawdown: {s['max_drawdown']:.1%}
    Params: pop={pop}, gen={gen}, risk={risk}, data={data_file.split('/')[-1] if '/' in data_file else data_file}
    Worker: {s['worker']}
"""
    
    report += f"""
📁 ANÁLISIS POR WORK UNIT
--------------------------------------------------------------------------------
"""
    for i, wu in enumerate(data['work_unit_analysis'][:5], 1):
        params = wu['params']
        report += f"""
{i}. Work Unit ID: {wu['params'].get("N/A", "N/A")}
   Params: pop={params.get('population_size')}, gen={params.get('generations')}, 
           risk={params.get('risk_level')}, candles={params.get('max_candles')}
   Resultados: {wu['total_results']} | Avg PnL: ${wu['avg_pnl']:.2f} | Max PnL: ${wu['max_pnl']:.2f}
"""
    
    report += f"""
👥 PERFORMANCE POR WORKER
--------------------------------------------------------------------------------
"""
    for w in data['worker_performance']:
        report += f"  {w['worker_id'][:40]:40} | {w['results']:4} res | Avg: ${w['avg_pnl']:.2f} | Max: ${w['max_pnl']:.2f}\n"
    
    report += f"""
💡 RECOMENDACIONES
--------------------------------------------------------------------------------
"""
    for rec in recommendations:
        report += f"""
[{rec['priority']}] {rec['area']}
    → {rec['suggestion']}
"""
    
    report += """
================================================================================
                              FIN DEL REPORTE
================================================================================
"""
    
    return report

if __name__ == "__main__":
    report = generate_report()
    print(report)
    
    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"OPTIMIZATION_REPORT_{timestamp}.txt"
    with open(filename, 'w') as f:
        f.write(report)
    print(f"\n📄 Reporte guardado en: {filename}")
