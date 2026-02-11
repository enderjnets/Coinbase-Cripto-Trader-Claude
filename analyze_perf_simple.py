#!/usr/bin/env python3
"""
📊 ANÁLISIS DE PERFORMANCE SIMPLIFICADO
"""
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DB_PATH = PROJECT_DIR / "coordinator.db"

def analyze_performance():
    """Análisis de performance semanal"""
    
    print("\n" + "="*70)
    print("📊 ANÁLISIS DE PERFORMANCE SEMANAL")
    print("="*70)
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # === Métricas Generales ===
    print("\n🎯 MÉTRICAS GENERALES")
    print("-"*50)
    
    c.execute("SELECT COUNT(*) as total FROM results")
    row = c.fetchone()
    total_trades = row['total']
    
    c.execute("SELECT COUNT(*) as total FROM results WHERE pnl > 0")
    row = c.fetchone()
    winning_trades = row['total']
    
    c.execute("SELECT SUM(pnl) as total FROM results")
    row = c.fetchone()
    total_pnl = row['total'] or 0
    
    c.execute("SELECT AVG(pnl) as avg FROM results")
    row = c.fetchone()
    avg_pnl = row['avg'] or 0
    
    c.execute("SELECT MAX(pnl) as max FROM results")
    row = c.fetchone()
    best_pnl = row['max'] or 0
    
    c.execute("SELECT MIN(pnl) as min FROM results")
    row = c.fetchone()
    worst_pnl = row['min'] or 0
    
    c.execute("SELECT AVG(win_rate) as avg FROM results")
    row = c.fetchone()
    avg_win_rate = (row['avg'] or 0) * 100
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    print(f"   📈 Total Trades: {total_trades:,}")
    print(f"   ✅ Trades Ganadores: {winning_trades:,}")
    print(f"   📉 Trades Perdedores: {total_trades - winning_trades:,}")
    print(f"   💰 Win Rate: {win_rate:.1f}%")
    print(f"   💵 Total PnL: ${total_pnl:,.2f}")
    print(f"   📊 PnL Promedio: ${avg_pnl:,.2f}")
    print(f"   🏆 Mejor Trade: ${best_pnl:,.2f}")
    print(f"   ⚠️ Peor Trade: ${worst_pnl:,.2f}")
    
    # === Performance por Worker ===
    print("\n\n👥 PERFORMANCE POR WORKER (TOP 10)")
    print("-"*70)
    
    c.execute("""
        SELECT 
            worker_id,
            COUNT(*) as trades,
            SUM(pnl) as pnl,
            AVG(pnl) as avg_pnl,
            AVG(win_rate) * 100 as win_rate
        FROM results
        GROUP BY worker_id
        ORDER BY pnl DESC
        LIMIT 10
    """)
    
    print(f"\n   {'Worker':<25} {'Trades':<8} {'PnL Total':<12} {'Avg PnL':<12} {'Win%':<8}")
    print("   " + "-"*70)
    
    for row in c.fetchall():
        print(f"   {row['worker_id'][:25]:<25} {row['trades']:<8} ${row['pnl']:<11,.2f} ${row['avg_pnl']:<11,.2f} {row['win_rate']:<7.1f}%")
    
    # === Work Units Status ===
    print("\n\n📦 ESTADO DE WORK UNITS")
    print("-"*50)
    
    c.execute("SELECT status, COUNT(*) as total FROM work_units GROUP BY status")
    for row in c.fetchall():
        emoji = {"completed": "✅", "in_progress": "🔄", "pending": "⏳", "cancelled": "❌"}.get(row['status'], "📦")
        print(f"   {emoji} {row['status']}: {row['total']}")
    
    # === Workers Status ===
    print("\n\n👥 ESTADO DE WORKERS")
    print("-"*50)
    
    c.execute("SELECT COUNT(*) as total FROM workers")
    row = c.fetchone()
    total_workers = row['total']
    
    c.execute("SELECT COUNT(*) as total FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
    row = c.fetchone()
    active_workers = row['total']
    
    print(f"   👥 Total Workers: {total_workers}")
    print(f"   🟢 Workers Activos: {active_workers}")
    print(f"   💤 Workers Inactivos: {total_workers - active_workers}")
    
    # === Triggers Detection ===
    print("\n\n🎯 DETECCIÓN DE TRIGGERS")
    print("-"*50)
    
    triggers = []
    
    # Trigger 1: Workers con bajo rendimiento
    c.execute("""
        SELECT worker_id, SUM(pnl) as pnl
        FROM results
        GROUP BY worker_id
        HAVING SUM(pnl) < 50
        ORDER BY SUM(pnl) ASC
    """)
    low_performers = c.fetchall()
    
    if low_performers:
        print(f"\n   ⚠️ TRIGGER: {len(low_performers)} workers con bajo rendimiento")
        for worker in low_performers[:3]:
            print(f"      • {worker['worker_id'][:30]}: ${worker['pnl']:.2f}")
        triggers.append({"type": "LOW_PERFORMANCE", "count": len(low_performers), "wu_needed": len(low_performers) * 10})
    else:
        print(f"\n   ✅ Todos los workers tienen buen rendimiento")
    
    # Trigger 2: Alta volatilidad
    c.execute("SELECT MAX(pnl) - MIN(pnl) as vol FROM results")
    row = c.fetchone()
    volatility = row['vol'] or 0
    
    if volatility > 500:
        print(f"\n   🚀 TRIGGER: Alta volatilidad (${volatility:.2f} rango)")
        triggers.append({"type": "HIGH_VOLATILITY", "volatility": volatility, "wu_needed": 50})
    
    # Trigger 3: Pocos WUs pendientes
    c.execute("SELECT COUNT(*) as total FROM work_units WHERE status='pending'")
    row = c.fetchone()
    pending = row['total']
    
    if pending < 5:
        print(f"\n   🆕 TRIGGER: Pocos WUs pendientes ({pending})")
        triggers.append({"type": "LOW_QUEUE", "pending": pending, "wu_needed": 100})
    
    # Resumen de triggers
    print(f"\n   📊 Total Triggers: {len(triggers)}")
    total_wus_needed = sum(t['wu_needed'] for t in triggers)
    print(f"   📦 WUs Recomendados: {total_wus_needed}")
    
    # === Recomendaciones ===
    print("\n\n💡 RECOMENDACIONES")
    print("-"*50)
    
    if win_rate > 60:
        print("   ✅ Win rate EXCELENTE (>60%)")
    elif win_rate > 50:
        print("   ⚡ Win rate ACEPTABLE (50-60%)")
    else:
        print("   🔧 Win rate BAJO (<50%)")
    
    if total_pnl > 1000:
        print("   🏆 PnL MUY ALTO")
    elif total_pnl > 500:
        print("   📈 PnL positivo")
    else:
        print("   📊 PnL bajo")
    
    # === Crear WUs ===
    print("\n\n🆕 CREANDO WORK UNITS")
    print("-"*50)
    
    wus_created = 0
    
    if triggers:
        for trigger in triggers:
            if trigger['type'] == "LOW_PERFORMANCE":
                name = f"Re-optimización Low Performers"
                pop, gen, risk = 100, 80, "HIGH"
            elif trigger['type'] == "HIGH_VOLATILITY":
                name = "Momentum High Volatility"
                pop, gen, risk = 150, 100, "HIGH"
            else:
                name = "Nueva Estrategia General"
                pop, gen, risk = 200, 120, "MEDIUM"
            
            params = {
                "name": name,
                "trigger_type": trigger['type'],
                "population_size": pop,
                "generations": gen,
                "mutation_rate": 0.15,
                "crossover_rate": 0.8,
                "risk_level": risk,
                "created_by": "PERFORMANCE_ANALYZER",
                "created_at": datetime.now().isoformat()
            }
            
            c.execute('''
                INSERT INTO work_units (strategy_params, replicas_needed, status, created_at)
                VALUES (?, 3, 'pending', ?)
            ''', (str(params), datetime.now().isoformat()))
            
            print(f"   ✅ WU #{wus_created + 1}: {name} ({pop} pop / {gen} gen)")
            wus_created += 1
    else:
        print("   ℹ️ No se detectaron triggers para nuevos WUs")
    
    conn.commit()
    
    # === Resumen ===
    print("\n\n" + "="*70)
    print("📊 RESUMEN DEL ANÁLISIS")
    print("="*70)
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║  📈 Métricas                                               ║
    ║     • Trades: {total_trades:,}                                      ║
    ║     • Win Rate: {win_rate:.1f}%                                      ║
    ║     • PnL Total: ${total_pnl:,.2f}                                ║
    ║     • Workers: {active_workers}/{total_workers}                                ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  🎯 Triggers: {len(triggers)}                                          ║
    ║  📦 Nuevos WUs: {wus_created}                                          ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  💡 Estado: {'EXCELENTE' if win_rate > 60 else 'BUENO' if win_rate > 50 else 'ATENCIÓN'}                                                ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    conn.close()

if __name__ == "__main__":
    analyze_performance()
