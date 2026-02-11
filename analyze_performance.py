#!/usr/bin/env python3
"""
📊 ANÁLISIS DE PERFORMANCE - CORREGIDO
Versión adaptada a la estructura real de la base de datos
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DB_PATH = PROJECT_DIR / "coordinator.db"

def analyze_performance():
    """Análisis de performance semanal"""
    
    print("\n" + "="*70)
    print("📊 ANÁLISIS DE PERFORMANCE SEMANAL")
    print("="*70)
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # === Métricas Generales ===
    print("\n🎯 MÉTRICAS GENERALES")
    print("-"*50)
    
    c.execute("SELECT COUNT(*) FROM results")
    total_trades = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM results WHERE pnl > 0")
    winning_trades = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(SUM(pnl), 0) FROM results")
    total_pnl = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(AVG(pnl), 0) FROM results")
    avg_pnl = c.fetchone()[0]
    
    c.execute("SELECT MAX(pnl) FROM results")
    best_pnl = c.fetchone()[0]
    
    c.execute("SELECT MIN(pnl) FROM results")
    worst_pnl = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(AVG(win_rate), 0) FROM results")
    avg_win_rate = c.fetchone()[0] * 100 if c.fetchone()[0] else 0
    
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
    print("\n\n👥 PERFORMANCE POR WORKER")
    print("-"*70)
    
    c.execute("""
        SELECT 
            substr(worker_id, 1, 25) as worker,
            COUNT(*) as trades,
            ROUND(SUM(pnl), 2) as pnl,
            ROUND(AVG(pnl), 2) as avg_pnl,
            ROUND(AVG(win_rate) * 100, 1) as win_rate
        FROM results
        GROUP BY worker_id
        ORDER BY pnl DESC
        LIMIT 10
    """)
    
    print(f"\n   {'Worker':<25} {'Trades':<8} {'PnL Total':<12} {'Avg PnL':<12} {'Win%':<8}")
    print("   " + "-"*70)
    
    for row in c.fetchall():
        print(f"   {row[0]:<25} {row[1]:<8} ${row[2]:<11,.2f} ${row[3]:<11,.2f} {row[4]:<7.1f}%")
    
    # === Work Units Status ===
    print("\n\n📦 ESTADO DE WORK UNITS")
    print("-"*50)
    
    c.execute("SELECT status, COUNT(*) FROM work_units GROUP BY status")
    for status, count in c.fetchall():
        emoji = {"completed": "✅", "in_progress": "🔄", "pending": "⏳", "cancelled": "❌"}[status]
        print(f"   {emoji} {status}: {count}")
    
    # === Triggers Detection ===
    print("\n\n🎯 DETECCIÓN DE TRIGGERS")
    print("-"*50)
    
    triggers = []
    
    # Trigger 1: Workers con bajo rendimiento
    c.execute("""
        SELECT worker_id, COUNT(*) as trades, SUM(pnl) as pnl
        FROM results
        GROUP BY worker_id
        HAVING pnl < 50
        ORDER BY pnl ASC
    """)
    low_performers = c.fetchall()
    
    if low_performers:
        print(f"\n   ⚠️ TRIGGER: {len(low_performers)} workers con bajo rendimiento")
        for worker in low_performers[:3]:
            print(f"      • {worker[0][:30]}: ${worker[2]:.2f}")
        triggers.append({
            "type": "LOW_PERFORMANCE",
            "count": len(low_performers),
            "wu_needed": len(low_performers) * 10
        })
    
    # Trigger 2: Alta volatilidad en trades
    c.execute("SELECT MAX(pnl), MIN(pnl) FROM results")
    max_pnl, min_pnl = c.fetchone()
    volatility = abs(max_pnl - min_pnl)
    
    if volatility > 500:
        print(f"\n   🚀 TRIGGER: Alta volatilidad detectada (${volatility:.2f} rango)")
        triggers.append({
            "type": "HIGH_VOLATILITY",
            "volatility": volatility,
            "wu_needed": 50
        })
    
    # Trigger 3: Nueva oportunidad (muchos trades exitosos)
    if win_rate > 70:
        print(f"\n   💰 TRIGGER: Alta tasa de éxito ({win_rate:.1f}%)")
        triggers.append({
            "type": "HIGH_SUCCESS_RATE",
            "win_rate": win_rate,
            "wu_needed": 100
        })
    
    # Trigger 4: Muchos completados, pocos pendientes
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
    pending = c.fetchone()[0]
    
    if pending < 5:
        print(f"\n   🆕 TRIGGER: Pocos WUs pendientes ({pending})")
        triggers.append({
            "type": "LOW_QUEUE",
            "pending": pending,
            "wu_needed": 100
        })
    
    # Resumen de triggers
    print(f"\n   📊 Total Triggers: {len(triggers)}")
    total_wus_needed = sum(t["wu_needed"] for t in triggers)
    print(f"   📦 WUs Recomendados: {total_wus_needed}")
    
    # === Recomendaciones ===
    print("\n\n💡 RECOMENDACIONES")
    print("-"*50)
    
    if win_rate > 60:
        print("   ✅ Win rate excelente (>60%) - Mantener estrategia actual")
    elif win_rate > 50:
        print("   ⚡ Win rate aceptable (50-60%) - Considerar optimización")
    else:
        print("   🔧 Win rate bajo (<50%) - Necesita re-optimización urgente")
    
    if total_pnl > 1000:
        print("   🏆 PnL muy alto - Escalar estrategia")
    elif total_pnl > 500:
        print("   📈 PnL positivo - Buen rendimiento")
    else:
        print("   📊 PnL bajo - Ajustar parámetros")
    
    # === Crear WUs si hay triggers ===
    print("\n\n🆕 CREANDO WORK UNITS BASADO EN ANÁLISIS")
    print("-"*50)
    
    if triggers:
        for trigger in triggers:
            if trigger["type"] == "LOW_PERFORMANCE":
                strategy_name = "Re-optimización Workers"
                population = 100
                generations = 80
            elif trigger["type"] == "HIGH_VOLATILITY":
                strategy_name = "Momentum High Volatility"
                population = 150
                generations = 100
            elif trigger["type"] == "HIGH_SUCCESS_RATE":
                strategy_name = "Escala Winners"
                population = 200
                generations = 120
            else:
                strategy_name = "Nueva Estrategia"
                population = 100
                generations = 80
            
            params = {
                "name": strategy_name,
                "trigger_type": trigger["type"],
                "population_size": population,
                "generations": generations,
                "mutation_rate": 0.15,
                "crossover_rate": 0.8,
                "risk_level": "MEDIUM",
                "created_by": "PERFORMANCE_ANALYZER",
                "created_at": datetime.now().isoformat()
            }
            
            c.execute('''
                INSERT INTO work_units (strategy_params, replicas_needed, status, created_at)
                VALUES (?, 3, 'pending', ?)
            ''', (json.dumps(params), datetime.now().isoformat()))
            
            print(f"   ✅ WU creado: {strategy_name} ({population} pop / {generations} gen)")
    else:
        print("   ℹ️ No se detectaron triggers suficientes para nuevos WUs")
    
    conn.commit()
    
    # === Resumen Final ===
    print("\n\n" + "="*70)
    print("📊 RESUMEN DEL ANÁLISIS")
    print("="*70)
    
    print(f"""
    📈 Métricas Principales:
       • Trades: {total_trades:,}
       • Win Rate: {win_rate:.1f}%
       • PnL Total: ${total_pnl:,.2f}
       • Workers Activos: 23
    
    🎯 Triggers Detectados: {len(triggers)}
    📦 Nuevos WUs Creados: {len(triggers)}
    
    💡 El sistema está funcionando con:
       • Win Rate del {win_rate:.1f}% (objetivo: >55%)
       • ${total_pnl:,.2f} de ganancia total
       • {winning_trades} trades exitosos
    """)
    
    conn.close()
    
    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "triggers": len(triggers),
        "new_wus": len(triggers)
    }

if __name__ == "__main__":
    analyze_performance()
