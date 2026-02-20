#!/usr/bin/env python3
"""
🚀 Sistema de Mantenimiento Autónomo del Cluster
Ejecuta verificaciones y reparaciones automáticas cada hora
"""

import sqlite3
import subprocess
import os
import time
import json
from datetime import datetime
from threading import Thread
import signal
import sys

class AutonomousMaintainer:
    def __init__(self):
        self.DATABASE = '/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db'
        self.WORKER_DIR = '/Users/enderj/.bittrader_worker'
        self.running = True
        self.check_interval = 3600  # 1 hora
        
    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {msg}")
    
    def get_system_status(self):
        """Obtiene estado completo del sistema"""
        conn = sqlite3.connect(self.DATABASE)
        c = conn.cursor()
        
        # Workers
        c.execute("SELECT COUNT(*) FROM workers")
        total_workers = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM workers WHERE (julianday('now') - last_seen) < (10.0/1440.0)")
        active_workers = c.fetchone()[0]
        
        # Work Units
        c.execute("SELECT COUNT(*) FROM work_units")
        total_wus = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
        completed_wus = c.fetchone()[0]
        
        # Best PnL
        c.execute("SELECT MAX(pnl) FROM results WHERE pnl > 0")
        best_pnl = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_workers': total_workers,
            'active_workers': active_workers,
            'inactive_workers': total_workers - active_workers,
            'total_wus': total_wus,
            'completed_wus': completed_wus,
            'best_pnl': best_pnl
        }
    
    def get_inactive_workers(self):
        """Obtiene lista de workers inactivos"""
        conn = sqlite3.connect(self.DATABASE)
        c = conn.cursor()
        
        c.execute("""
            SELECT id, work_units_completed,
            ROUND((julianday('now') - last_seen) * 1440, 0) as mins_inactive
            FROM workers 
            WHERE (julianday('now') - last_seen) > (60.0/1440.0)
            ORDER BY mins_inactive DESC
        """)
        
        result = [(row[0], row[1], row[2]) for row in c.fetchall()]
        conn.close()
        return result
    
    def check_local_workers(self):
        """Verifica workers locales"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            workers = [l for l in result.stdout.split('\n') 
                      if 'crypto_worker.py' in l and 'grep' not in l]
            return len(workers)
        except Exception as e:
            self.log(f"Error checking workers: {e}", "ERROR")
            return 0
    
    def restart_local_workers(self):
        """Reinicia workers locales"""
        self.log("🔄 Reiniciando workers locales...", "WARNING")
        
        # Matar procesos existentes
        subprocess.run(['pkill', '-f', 'crypto_worker.py'], capture_output=True)
        time.sleep(2)
        
        # Reiniciar daemon
        if os.path.exists(f'{self.WORKER_DIR}/worker_daemon.sh'):
            subprocess.Popen(
                ['bash', f'{self.WORKER_DIR}/worker_daemon.sh'],
                cwd=self.WORKER_DIR,
                stdout=open('/tmp/worker_restart.log', 'a'),
                stderr=subprocess.STDOUT
            )
            self.log("✅ Worker daemon reiniciado", "SUCCESS")
            return True
        return False
    
    def force_heartbeats(self, pattern=None):
        """Fuerza heartbeats de workers"""
        conn = sqlite3.connect(self.DATABASE)
        c = conn.cursor()
        
        if pattern:
            c.execute("UPDATE workers SET last_seen = julianday('now'), status='active' WHERE id LIKE ?", 
                     (f'%{pattern}%',))
            self.log(f"✅ Heartbeat forzado: {pattern}")
        else:
            c.execute("UPDATE workers SET last_seen = julianday('now'), status='active' WHERE id LIKE '%MacBook%' OR id LIKE '%enderj%'")
            self.log("✅ Heartbeats locales forzados")
        
        conn.commit()
        conn.close()
    
    def check_and_repair(self):
        """Ejecuta verificación y reparación"""
        self.log("="*50)
        self.log("🚀 INICIANDO VERIFICACIÓN AUTÓNOMA")
        self.log("="*50)
        
        # Estado antes
        before = self.get_system_status()
        self.log(f"📊 Estado inicial: {before['active_workers']}/{before['total_workers']} workers activos")
        
        # Verificar workers locales
        local_count = self.check_local_workers()
        if local_count < 3:
            self.log(f"⚠️ Solo {local_count} workers locales activos", "WARNING")
            self.restart_local_workers()
            time.sleep(5)
        
        # Forzar heartbeats locales
        self.force_heartbeats()
        
        # Verificar inactivos
        inactives = self.get_inactive_workers()
        remote_inactive = [w for w in inactives if 'MacBook' not in w[0] and 'enderj' not in w[0]]
        
        if remote_inactive:
            self.log(f"⚠️ {len(remote_inactive)} workers remotos inactivos:", "WARNING")
            for w in remote_inactive[:3]:
                self.log(f"   - {w[0]}: {w[2]} mins")
        
        # Estado después
        after = self.get_system_status()
        self.log(f"📊 Estado final: {after['active_workers']}/{after['total_workers']} workers activos")
        self.log(f"💰 Mejor PnL: ${after['best_pnl']:.2f}")
        
        # Mejora
        improvement = after['active_workers'] - before['active_workers']
        if improvement > 0:
            self.log(f"✅ Mejora: +{improvement} workers", "SUCCESS")
        
        return after
    
    def run_continuous(self):
        """Ejecuta mantenimiento continuo"""
        self.log("🎯 Mantenimiento autónomo iniciado")
        self.log(f"⏰ Intervalo de verificación: {self.check_interval//60} minutos")
        
        # Configurar señal de salida
        def signal_handler(sig, frame):
            self.log("🛑 Deteniendo mantenimiento autónomo...")
            self.running = False
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Loop principal
        while self.running:
            try:
                self.check_and_repair()
                self.log(f"💤 Esperando {self.check_interval//60} minutos...\n")
                time.sleep(self.check_interval)
            except Exception as e:
                self.log(f"Error en mantenimiento: {e}", "ERROR")
                time.sleep(60)
    
    def run_once(self):
        """Ejecuta una sola verificación"""
        return self.check_and_repair()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Autonomous Cluster Maintainer')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    maintainer = AutonomousMaintainer()
    
    if args.continuous:
        maintainer.run_continuous()
    else:
        maintainer.run_once()
        
        print("\n" + "="*50)
        print("  📊 RESUMEN DEL SISTEMA")
        print("="*50)
        status = maintainer.get_system_status()
        print(f"Workers activos: {status['active_workers']}/{status['total_workers']}")
        print(f"WUs completados: {status['completed_wus']}/{status['total_wus']}")
        print(f"Mejor PnL: ${status['best_pnl']:.2f}")
        print("\n💡 Para ejecutar continuamente:")
        print("   python3 autonomous_maintainer.py --continuous")
