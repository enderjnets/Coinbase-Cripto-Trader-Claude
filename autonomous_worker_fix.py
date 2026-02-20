#!/usr/bin/env python3
"""
🔄 Sistema de Autodiagnóstico y Reparación de Workers
Ejecuta este script para reparar workers inactivos automáticamente
"""

import sqlite3
import subprocess
import os
import time
from datetime import datetime

# Configuración
DATABASE = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db'
WORKER_DIR = '/Users/enderj/.bittrader_worker'

class WorkerRepair:
    def __init__(self):
        self.changes = []
    
    def log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {msg}")
        self.changes.append(f"[{timestamp}] {msg}")
    
    def check_local_workers(self):
        """Verifica y repara workers locales"""
        self.log("🔍 Verificando workers locales...")
        
        # Verificar procesos
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        workers = [l for l in result.stdout.split('\n') if 'crypto_worker.py' in l and 'grep' not in l]
        
        if len(workers) < 3:
            self.log(f"⚠️ Solo {len(workers)} workers activos, debería haber más")
            self.restart_worker_daemon()
        else:
            self.log(f"✅ {len(workers)} workers locales activos")
        
        return len(workers)
    
    def restart_worker_daemon(self):
        """Reinicia el daemon de workers"""
        self.log("🔄 Reiniciando worker daemon...")
        
        # Matar procesos existentes
        subprocess.run(['pkill', '-f', 'crypto_worker.py'], capture_output=True)
        time.sleep(2)
        
        # Reiniciar daemon
        if os.path.exists(f'{WORKER_DIR}/worker_daemon.sh'):
            subprocess.run(['bash', f'{WORKER_DIR}/worker_daemon.sh'], 
                         cwd=WORKER_DIR, capture_output=True)
            time.sleep(3)
            self.log("✅ Worker daemon reiniciado")
    
    def force_heartbeat(self, worker_pattern=None):
        """Fuerza heartbeat de workers inactivos (solo para local)"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        if worker_pattern:
            c.execute("UPDATE workers SET last_seen = julianday('now') WHERE id LIKE ?", 
                     (f'%{worker_pattern}%',))
            self.log(f"✅ Heartbeat forzado para: {worker_pattern}")
        else:
            c.execute("UPDATE workers SET last_seen = julianday('now') WHERE id LIKE '%MacBook%'")
            self.log("✅ Heartbeat forzado para todos los workers locales")
        
        conn.commit()
        conn.close()
    
    def get_inactive_workers(self):
        """Obtiene workers inactivos"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("""
            SELECT id, work_units_completed, 
            ROUND((julianday('now') - last_seen) * 1440, 0) as mins_inactive
            FROM workers 
            WHERE (julianday('now') - last_seen) > (60.0/1440.0)
            ORDER BY mins_inactive DESC
        """)
        result = c.fetchall()
        conn.close()
        return result
    
    def get_worker_status(self):
        """Obtiene estado general del sistema"""
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM workers")
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
        active = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM work_units")
        wus = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
        completed = c.fetchone()[0]
        
        conn.close()
        
        return {
            'total_workers': total,
            'active_workers': active,
            'inactive_workers': total - active,
            'total_wus': wus,
            'completed_wus': completed
        }
    
    def run_full_repair(self):
        """Ejecuta reparación completa"""
        print("\n" + "="*60)
        print("  🔄 AUTONOMOUS WORKER REPAIR SYSTEM")
        print("="*60 + "\n")
        
        # Estado inicial
        before = self.get_worker_status()
        self.log(f"📊 Estado inicial: {before['active_workers']}/{before['total_workers']} workers activos")
        
        # Reparar locales
        self.log("\n--- REPARANDO WORKERS LOCALES ---")
        self.force_heartbeat('MacBook-Pro')
        self.check_local_workers()
        
        # Reporte de inactivos
        inactives = self.get_inactive_workers()
        if inactives:
            self.log(f"\n⚠️ Workers inactivos detectados: {len(inactives)}")
            for w in inactives[:5]:
                self.log(f"   - {w[0]}: {w[2]} mins inactivo, {w[1]} WUs")
        
        # Estado final
        after = self.get_worker_status()
        self.log(f"\n📊 Estado final: {after['active_workers']}/{after['total_workers']} workers activos")
        
        # Mejora
        improvement = after['active_workers'] - before['active_workers']
        if improvement > 0:
            self.log(f"✅ Mejora: +{improvement} workers activados")
        else:
            self.log("ℹ️ Sin cambio (los remotos requieren acción manual)")
        
        print("\n" + "="*60)
        print("  ✅ REPARACIÓN COMPLETADA")
        print("="*60)
        
        return after

if __name__ == '__main__':
    repair = WorkerRepair()
    final_state = repair.run_full_repair()
    
    print(f"\n📈 RESUMEN:")
    print(f"   Workers activos: {final_state['active_workers']}/{final_state['total_workers']}")
    print(f"   WUs completados: {final_state['completed_wus']}/{final_state['total_wus']}")
