#!/usr/bin/env python3
"""
🚀 LIVE MONITORING DASHBOARD v2.0
Monitorea el progreso de los Work Units en tiempo real
Detecta cuando se supera el récord de $443.99

Uso: python3 live_monitor.py
"""

import sqlite3
import time
import os
from datetime import datetime

class LiveMonitor:
    """Monitor en tiempo real del sistema de trading"""
    
    def __init__(self):
        self.db_path = "coordinator.db"
        self.target_pnl = 443.99
        self.refresh_interval = 10  # segundos
    
    def get_db_connection(self):
        """Crea conexión a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_current_stats(self):
        """Obtiene estadísticas actuales"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # Work Units
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
        completed = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
        pending = c.fetchone()[0]
        
        # Mejor PnL actual
        c.execute("SELECT MAX(pnl) FROM results WHERE pnl IS NOT NULL")
        max_pnl = c.fetchone()[0] or 0
        
        # Últimos resultados
        c.execute('''
            SELECT r.pnl, r.trades, r.win_rate, w.strategy_params, r.submitted_at
            FROM results r
            JOIN work_units w ON r.work_unit_id = w.id
            ORDER BY r.submitted_at DESC
            LIMIT 5
        ''')
        recent_results = []
        for row in c.fetchall():
            params = json.loads(row[3])
            recent_results.append({
                'pnl': row[0],
                'trades': row[1],
                'win_rate': row[2],
                'name': params.get('name', 'Unknown'),
                'timestamp': row[4]
            })
        
        # Workers activos
        c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < 0.01")
        active_workers = c.fetchone()[0]
        
        conn.close()
        
        return {
            'completed': completed,
            'pending': pending,
            'max_pnl': max_pnl,
            'recent_results': recent_results,
            'active_workers': active_workers
        }
    
    def check_new_record(self, old_max, new_max):
        """Verifica si hay un nuevo récord"""
        if new_max > old_max and new_max > self.target_pnl:
            return True, new_max
        return False, new_max
    
    def format_timestamp(self, julian_ts):
        """Convierte timestamp de SQLite a datetime"""
        try:
            unix_ts = (julian_ts - 2440588) * 86400
            return datetime.fromtimestamp(unix_ts).strftime('%H:%M:%S')
        except:
            return "Unknown"

def clear_screen():
    """Limpia la pantalla"""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("\n" + "="*80)
    print("🚀 LIVE MONITORING DASHBOARD v2.0")
    print(f"   Objetivo: Superar ${443.99} PnL")
    print("="*80 + "\n")
    
    monitor = LiveMonitor()
    
    prev_max_pnl = 0
    record_broken = False
    
    try:
        while True:
            stats = monitor.get_current_stats()
            
            clear_screen()
            
            print("="*80)
            print(f"🕐 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)
            
            print(f"\n📊 ESTADO DEL SISTEMA")
            print("-" * 40)
            print(f"   Work Units Completados: {stats['completed']}")
            print(f"   Work Units Pendientes:  {stats['pending']}")
            print(f"   Workers Activos:        {stats['active_workers']}")
            
            print(f"\n💰 RENDIMIENTO")
            print("-" * 40)
            print(f"   Mejor PnL Actual: ${stats['max_pnl']:,.2f}")
            
            if stats['max_pnl'] >= monitor.target_pnl:
                print(f"   🏆 ¡RÉCORD ALCANZADO! (Objetivo: ${monitor.target_pnl})")
                if not record_broken:
                    record_broken = True
                    print(f"\n   🎉 ¡FELICIDADES! ¡Se ha superado el récord de ${monitor.target_pnl}!")
            else:
                remaining = monitor.target_pnl - stats['max_pnl']
                print(f"   Objetivo: ${monitor.target_pnl}")
                print(f"   Faltan: ${remaining:,.2f} para alcanzar el récord")
            
            # Verificar nuevo récord
            is_new_record, new_max = monitor.check_new_record(prev_max_pnl, stats['max_pnl'])
            if is_new_record:
                print(f"\n   🆕 ¡NUEVO RÉCORD: ${new_max:,.2f}!")
            prev_max_pnl = stats['max_pnl']
            
            print(f"\n📈 ÚLTIMOS RESULTADOS")
            print("-" * 40)
            if stats['recent_results']:
                for i, r in enumerate(stats['recent_results'], 1):
                    timestamp = monitor.format_timestamp(r['timestamp'])
                    pnl_str = f"${r['pnl']:,.2f}"
                    if r['pnl'] >= stats['max_pnl'] * 0.9:
                        pnl_str = f"🎯 {pnl_str}"
                    print(f"   {i}. [{timestamp}] {r['name'][:30]:30s} | PnL: {pnl_str:>12s} | {r['trades']} trades")
            else:
                print("   Sin resultados aún...")
            
            print(f"\n⏱️ Actualizando cada {monitor.refresh_interval} segundos...")
            print(f"   Presiona Ctrl+C para salir")
            
            time.sleep(monitor.refresh_interval)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoreo detenido")

if __name__ == '__main__':
    import json
    main()
