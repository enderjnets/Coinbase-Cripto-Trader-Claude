#!/usr/bin/env python3
"""
🛑 CANCELAR TODOS LOS WORK UNITS ACTUALES
Limpia el sistema para comenzar con el nuevo plan ULTIMATE

ADVERTENCIA: Esta acción NO se puede deshacer

Autor: Ultimate Trading System
Fecha: Febrero 2026
"""

import sqlite3
from datetime import datetime

# Configuración
DB_PATH = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"

def show_current_state():
    """Mostrar estado actual"""
    print("\n" + "="*60)
    print("📊 ESTADO ACTUAL DEL SISTEMA")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Work Units
    print("\n📦 WORK UNITS:")
    c.execute("SELECT status, COUNT(*) as cantidad FROM work_units GROUP BY status")
    for status, count in c.fetchall():
        emoji = {"completed": "✅", "in_progress": "🔄", "pending": "⏳", "cancelled": "❌"}[status]
        print(f"   {emoji} {status}: {count}")
    
    # Total resultados
    c.execute("SELECT COUNT(*) FROM results")
    total_results = c.fetchone()[0]
    print(f"\n📊 Resultados totales: {total_results:,}")
    
    # Workers
    c.execute("SELECT COUNT(*) FROM workers")
    total_workers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
    active_workers = c.fetchone()[0]
    print(f"👥 Workers: {active_workers}/{total_workers} activos")
    
    # Mejor PnL
    c.execute("SELECT MAX(pnl) FROM results")
    best_pnl = c.fetchone()[0] or 0
    print(f"\n💰 Mejor PnL histórico: ${best_pnl:.2f}")
    
    conn.close()
    
    return {
        'results': total_results,
        'workers': total_workers,
        'best_pnl': best_pnl
    }


def cancel_work_units():
    """Cancelar todos los work units"""
    print("\n" + "="*60)
    print("🛑 CANCELANDO WORK UNITS")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Contar antes de cancelar
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='in_progress'")
    in_progress = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
    pending = c.fetchone()[0]
    
    print(f"\n   🔄 Cancelando {in_progress} WUs en progreso...")
    print(f"   ⏳ Cancelando {pending} WUs pendientes...")
    
    # Cancelar WUs
    c.execute("UPDATE work_units SET status='cancelled' WHERE status IN ('in_progress', 'pending')")
    
    # Registrar en log
    c.execute('''
        CREATE TABLE IF NOT EXISTS wu_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            timestamp TEXT,
            details TEXT
        )
    ''')
    
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO wu_log (action, timestamp, details) VALUES (?, ?, ?)",
              ('CANCEL_ALL', timestamp, f'Cancelled {in_progress} in_progress + {pending} pending'))
    
    conn.commit()
    conn.close()
    
    print(f"\n   ✅ {in_progress + pending} Work Units cancelados")


def reset_workers():
    """Resetear workers"""
    print("\n" + "="*60)
    print("🔄 RESETENDO WORKERS")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Contar workers
    c.execute("SELECT COUNT(*) FROM workers")
    total = c.fetchone()[0]
    
    print(f"\n   📊 Workers registrados: {total}")
    
    # No eliminamos workers, solo actualizamos last_seen para que parezcan inactivos
    c.execute("UPDATE workers SET last_seen = julianday('now') - 1")
    
    conn.commit()
    conn.close()
    
    print(f"   ✅ Workers reseteados (aparecerán como inactivos)")


def backup_results():
    """Respaldar resultados antes de eliminar"""
    print("\n" + "="*60)
    print("💾 RESPALDANDO RESULTADOS")
    print("="*60)
    
    import shutil
    import os
    
    backup_dir = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/coordinator_backup_{timestamp}.db"
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        size_mb = os.path.getsize(backup_file) / (1024*1024)
        print(f"\n   ✅ Backup creado: {backup_file}")
        print(f"   📦 Tamaño: {size_mb:.2f} MB")
        return True
    except Exception as e:
        print(f"\n   ❌ Error creando backup: {e}")
        return False


def clean_results():
    """Limpiar resultados (mantener solo los mejores)"""
    print("\n" + "="*60)
    print("🧹 LIMPIANDO RESULTADOS")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Contar antes
    c.execute("SELECT COUNT(*) FROM results")
    before = c.fetchone()[0]
    print(f"\n   📊 Resultados antes: {before:,}")
    
    # Mantener solo los top 1000 por PnL
    # Crear tabla temporal con mejores resultados
    c.execute('''
        CREATE TABLE results_backup AS
        SELECT r.* FROM results r
        WHERE r.id IN (
            SELECT id FROM results
            ORDER BY pnl DESC
            LIMIT 10000
        )
    ''')
    
    # Eliminar tabla original y renombrar
    c.execute("DROP TABLE results")
    c.execute("ALTER TABLE results_backup RENAME TO results")
    
    # Contar después
    c.execute("SELECT COUNT(*) FROM results")
    after = c.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    print(f"   📊 Resultados después: {after:,}")
    print(f"   🗑️ Eliminados: {before - after:,}")


def create_new_wus():
    """Crear nuevos WUs para el plan ULTIMATE"""
    print("\n" + "="*60)
    print("🆕 CREANDO NUEVOS WORK UNITS")
    print("="*60)
    
    import json
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Nuevos parámetros optimizados
    new_strategies = [
        {
            "name": "VWAP Scalping Ultimate",
            "category": "Scalping",
            "timeframes": ["1m", "5m"],
            "population_size": 200,
            "generations": 150,
            "mutation_rate": 0.15,
            "crossover_rate": 0.8,
            "risk_level": "HIGH",
            "target_pnl_percent": 5
        },
        {
            "name": "Order Block & FVG Confluence",
            "category": "SMC",
            "timeframes": ["15m", "1h"],
            "population_size": 150,
            "generations": 100,
            "mutation_rate": 0.2,
            "crossover_rate": 0.85,
            "risk_level": "MEDIUM",
            "target_pnl_percent": 5
        },
        {
            "name": "Multi-Timeframe Trend Following",
            "category": "Trend",
            "timeframes": ["1h", "4h"],
            "population_size": 100,
            "generations": 80,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "risk_level": "LOW",
            "target_pnl_percent": 3
        },
        {
            "name": "RSI Divergence + Volume",
            "category": "Technical",
            "timeframes": ["15m", "1h", "4h"],
            "population_size": 120,
            "generations": 100,
            "mutation_rate": 0.15,
            "crossover_rate": 0.8,
            "risk_level": "MEDIUM",
            "target_pnl_percent": 4
        },
        {
            "name": "Opening Range Breakout Pro",
            "category": "Day Trading",
            "timeframes": ["5m", "15m"],
            "population_size": 180,
            "generations": 120,
            "mutation_rate": 0.18,
            "crossover_rate": 0.82,
            "risk_level": "HIGH",
            "target_pnl_percent": 5
        }
    ]
    
    print(f"\n   📝 Creando {len(new_strategies)} nuevos Work Units...")
    
    for i, strategy in enumerate(new_strategies):
        c.execute('''
            INSERT INTO work_units (strategy_params, replicas_needed, status, created_at)
            VALUES (?, 3, 'pending', ?)
        ''', (json.dumps(strategy), datetime.now().isoformat()))
        print(f"      ✅ WU #{i+1}: {strategy['name']}")
    
    conn.commit()
    
    # Verificar
    c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
    pending = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM work_units")
    total = c.fetchone()[0]
    
    conn.close()
    
    print(f"\n   📊 Total WUs pendientes: {pending}")
    print(f"   📊 Total WUs en sistema: {total}")


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🛑 SISTEMA DE CANCELACIÓN DE WUs")
    print("   Para ULTIMATE TRADING SYSTEM")
    print("="*60)
    
    # Mostrar estado actual
    state = show_current_state()
    
    print("\n" + "="*60)
    print("⚠️  ACCIONES DISPONIBLES")
    print("="*60)
    print("\n   [1] Solo cancelar WUs (mantener resultados)")
    print("   [2] Cancelar WUs + Limpiar resultados (mantener top 10K)")
    print("   [3] Cancelar WUs + Backup completo + Limpiar TODO")
    print("   [4] Cancelar + Reset Workers + Nuevos WUs")
    print("   [5] Solo ver estado (sin cambios)")
    print("   [0] Cancelar operación")
    
    choice = input("\n👉 Opción: ").strip()
    
    if choice == "1":
        cancel_work_units()
        print("\n✅ WUs cancelados. Resultados preservados.")
        
    elif choice == "2":
        backup_results()
        cancel_work_units()
        clean_results()
        print("\n✅ WUs cancelados y resultados limpiados.")
        
    elif choice == "3":
        backup_results()
        cancel_work_units()
        
        # Eliminar resultados completamente
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM results")
        conn.commit()
        conn.close()
        print("\n✅ WUs cancelados y TODOS los resultados eliminados.")
        
    elif choice == "4":
        print("\n🛑 CANCELANDO TODO Y REINICIANDO CON NUEVO PLAN")
        print("\n   Esto eliminará:")
        print("   ❌ Todos los WUs actuales")
        print("   ❌ Todos los resultados")
        print("   ❌ Workers parecerán inactivos")
        print("\n   Y creará:")
        print("   ✅ 5 nuevos WUs optimizados")
        
        confirm = input("\n   Escribe 'YES' para confirmar: ").strip()
        
        if confirm == "YES":
            backup_results()
            cancel_work_units()
            reset_workers()
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM results")
            conn.commit()
            conn.close()
            
            create_new_wus()
            print("\n🎉 SISTEMA REINICIADO CON NUEVOS WUs")
        else:
            print("\n   Operación cancelada.")
            
    elif choice == "5":
        print("\n   No se realizaron cambios.")
        
    elif choice == "0":
        print("\n   Operación cancelada.")
        
    else:
        print("\n   Opción no válida.")
    
    # Mostrar nuevo estado
    print("\n" + "="*60)
    print("📊 NUEVO ESTADO")
    print("="*60)
    show_current_state()


if __name__ == "__main__":
    main()
