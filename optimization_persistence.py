#!/usr/bin/env python3
"""
Optimization Persistence System
Guarda automáticamente reportes, estrategias y estadísticas para no perder nada.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

# Rutas
PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
DB_PATH = os.path.join(PROJECT_DIR, "coordinator.db")
BACKUP_DIR = os.path.join(PROJECT_DIR, "optimization_history")
REPORTS_DIR = os.path.join(BACKUP_DIR, "reports")
STRATEGIES_DIR = os.path.join(BACKUP_DIR, "strategies")
STATS_DIR = os.path.join(BACKUP_DIR, "statistics")

# Crear directorios
Path(BACKUP_DIR).mkdir(exist_ok=True)
Path(REPORTS_DIR).mkdir(exist_ok=True)
Path(STRATEGIES_DIR).mkdir(exist_ok=True)
Path(STATS_DIR).mkdir(exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def save_snapshot():
    """Guarda un snapshot completo del estado actual"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    conn = get_db()
    c = conn.cursor()
    
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'work_units': {},
        'results_summary': {},
        'top_strategies': [],
        'workers': {}
    }
    
    # Work units
    c.execute("SELECT id, strategy_params, status, replicas_needed, replicas_completed, created_at FROM work_units ORDER BY id")
    for row in c.fetchall():
        snapshot['work_units'][row['id']] = {
            'params': json.loads(row['strategy_params']),
            'status': row['status'],
            'replicas_needed': row['replicas_needed'],
            'replicas_completed': row['replicas_completed'],
            'created_at': row['created_at']
        }
    
    # Results summary
    c.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) as positive,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_pnl,
            AVG(pnl) filter (where pnl > 0) as avg_positive,
            AVG(trades) as avg_trades,
            AVG(win_rate) as avg_win_rate,
            AVG(sharpe_ratio) as avg_sharpe,
            AVG(max_drawdown) as avg_drawdown
        FROM results
    """)
    stats = dict(c.fetchone())
    snapshot['results_summary'] = stats
    
    # Top 50 strategies (excluyendo hardcoded)
    c.execute("""
        SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
               w.strategy_params, r.worker_id, r.work_unit_id, r.id as result_id
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.pnl > 0 AND r.trades != 10
        ORDER BY r.pnl DESC
        LIMIT 50
    """)
    for row in c.fetchall():
        snapshot['top_strategies'].append({
            'result_id': row['result_id'],
            'work_unit_id': row['work_unit_id'],
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe_ratio': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'worker': row['worker_id'],
            'params': json.loads(row['strategy_params'])
        })
    
    # Workers
    c.execute("SELECT id, work_units_completed, total_execution_time, last_seen FROM workers ORDER BY work_units_completed DESC")
    for row in c.fetchall():
        snapshot['workers'][row['id']] = {
            'work_units_completed': row['work_units_completed'],
            'total_execution_time': row['total_execution_time'],
            'last_seen': row['last_seen']
        }
    
    conn.close()
    
    # Guardar snapshot
    snapshot_file = os.path.join(STATS_DIR, f"snapshot_{timestamp}.json")
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot, f, indent=2)
    
    print(f"📸 Snapshot guardado: {snapshot_file}")
    return snapshot_file

def save_best_strategies():
    """Guarda las mejores estrategias en un archivo histórico"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    conn = get_db()
    c = conn.cursor()
    
    # Top 100 estrategias por PnL
    c.execute("""
        SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
               w.strategy_params, r.worker_id, r.work_unit_id, r.id as result_id,
               r.submitted_at
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.pnl > 0 AND r.trades != 10
        ORDER BY r.pnl DESC
        LIMIT 100
    """)
    
    strategies = {
        'saved_at': datetime.now().isoformat(),
        'total_saved': 0,
        'strategies': []
    }
    
    for row in c.fetchall():
        strategies['strategies'].append({
            'result_id': row['result_id'],
            'work_unit_id': row['work_unit_id'],
            'pnl': row['pnl'],
            'trades': row['trades'],
            'win_rate': row['win_rate'],
            'sharpe_ratio': row['sharpe_ratio'],
            'max_drawdown': row['max_drawdown'],
            'worker': row['worker_id'],
            'submitted_at': row['submitted_at'],
            'params': json.loads(row['strategy_params'])
        })
    
    strategies['total_saved'] = len(strategies['strategies'])
    conn.close()
    
    # Guardar como JSON
    strategy_file = os.path.join(STRATEGIES_DIR, f"best_strategies_{timestamp}.json")
    with open(strategy_file, 'w') as f:
        json.dump(strategies, f, indent=2)
    
    # También sobrescribir el "latest" para fácil acceso
    latest_file = os.path.join(STRATEGIES_DIR, "best_strategies_latest.json")
    with open(latest_file, 'w') as f:
        json.dump(strategies, f, indent=2)
    
    print(f"⭐ Mejores estrategias guardadas: {strategy_file}")
    return strategy_file

def generate_text_report():
    """Genera un reporte en texto plano"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    conn = get_db()
    c = conn.cursor()
    
    # Stats
    c.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN pnl > 0 THEN 1 END) as positive,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_pnl,
            AVG(pnl) filter (where pnl > 0) as avg_positive
        FROM results
    """)
    stats = dict(c.fetchone())
    
    # Top 20
    c.execute("""
        SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
               w.strategy_params, r.worker_id
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.pnl > 0 AND r.trades != 10
        ORDER BY r.pnl DESC
        LIMIT 20
    """)
    
    report = f"""
================================================================================
                    REPORTE DE OPTIMIZACIÓN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

📊 ESTADÍSTICAS GENERALES
--------------------------------------------------------------------------------
Total de resultados:        {stats['total']:,}
Resultados positivos:       {stats['positive']:,}
Promedio PnL (todos):       ${stats['avg_pnl']:.2f}
Promedio PnL (positivos):   ${stats['avg_positive']:.2f}
PnL máximo:                 ${stats['max_pnl']:.2f}

🏆 TOP 20 MEJORES ESTRATEGIAS (MÉTRICAS REALES)
--------------------------------------------------------------------------------
"""
    
    for i, row in enumerate(c.fetchall(), 1):
        params = json.loads(row['strategy_params'])
        pop = params.get('population_size', 'N/A')
        gen = params.get('generations', 'N/A')
        risk = params.get('risk_level', 'N/A')
        
        report += f"""
{i:2}. PnL: ${row['pnl']:.2f} | Trades: {row['trades']} | Win Rate: {row['win_rate']*100:.1f}%
    Sharpe: {row['sharpe_ratio']:.2f} | Max Drawdown: {row['max_drawdown']*100:.1f}%
    Params: pop={pop}, gen={gen}, risk={risk}
    Worker: {row['worker_id']}
"""
    
    conn.close()
    
    report_file = os.path.join(REPORTS_DIR, f"OPTIMIZATION_REPORT_{timestamp}.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"📄 Reporte guardado: {report_file}")
    return report_file

def export_best_genome():
    """Exporta el mejor genoma encontrado para uso futuro"""
    conn = get_db()
    c = conn.cursor()
    
    # Mejor estrategia
    c.execute("""
        SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown,
               w.strategy_params, r.worker_id
        FROM results r
        JOIN work_units w ON r.work_unit_id = w.id
        WHERE r.pnl > 0 AND r.trades != 10
        ORDER BY r.pnl DESC
        LIMIT 1
    """)
    best = c.fetchone()
    
    if not best:
        print("❌ No hay estrategias para exportar")
        return None
    
    genome_file = os.path.join(STRATEGIES_DIR, "BEST_GENOME.json")
    genome = {
        'exported_at': datetime.now().isoformat(),
        'pnl': best['pnl'],
        'trades': best['trades'],
        'win_rate': best['win_rate'],
        'sharpe_ratio': best['sharpe_ratio'],
        'max_drawdown': best['max_drawdown'],
        'worker': best['worker_id'],
        'work_unit_params': json.loads(best['strategy_params']),
        'note': 'Este genoma puede ser usado directamente en crypto_worker.py para trading real'
    }
    
    with open(genome_file, 'w') as f:
        json.dump(genome, f, indent=2)
    
    print(f"🧬 Mejor genoma exportado: {genome_file}")
    return genome_file

def run_full_backup():
    """Ejecuta un backup completo"""
    print(f"\n{'='*60}")
    print(f"💾 INICIANDO BACKUP COMPLETO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    files = []
    files.append(save_snapshot())
    files.append(save_best_strategies())
    files.append(generate_text_report())
    files.append(export_best_genome())
    
    print(f"\n{'='*60}")
    print(f"✅ BACKUP COMPLETADO - {len(files)} archivos guardados")
    print(f"{'='*60}")
    
    return files

if __name__ == "__main__":
    run_full_backup()
