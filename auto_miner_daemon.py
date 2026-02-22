#!/usr/bin/env python3
"""
🚀 AUTO-MINER DAEMON
=====================

Mantiene el sistema ejecutándose continuamente.
Se ejecuta en background y crea WUs según sea necesario.

Uso:
    python auto_miner_daemon.py
    python auto_miner_daemon.py --stop
"""

import os
import sys
import time
import json
import sqlite3
import requests
import signal
import atexit
from datetime import datetime
from pathlib import Path

PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_URL = "http://localhost:5001"
PID_FILE = "/tmp/auto_miner_daemon.pid"
LOG_FILE = f"{PROJECT_DIR}/auto_miner_daemon.log"

# Configuraciones
MIN_PENDING = 5
CHECK_INTERVAL = 60  # 1 minuto

CONFIGS = [
    {"name": "BTC_MOM_3x", "pop": 30, "gen": 80, "sl": 1.0, "tp": 5.0, "lev": 3, "risk": "HIGH"},
    {"name": "ETH_MACD_2x", "pop": 30, "gen": 80, "sl": 1.5, "tp": 4.0, "lev": 2, "risk": "MEDIUM"},
    {"name": "SOL_BRK_5x", "pop": 25, "gen": 60, "sl": 1.0, "tp": 5.0, "lev": 5, "risk": "HIGH"},
    {"name": "BTC_AGR_4x", "pop": 40, "gen": 100, "sl": 0.8, "tp": 6.0, "lev": 4, "risk": "HIGH"},
    {"name": "BTC_RSI_2x", "pop": 35, "gen": 90, "sl": 2.0, "tp": 4.0, "lev": 2, "risk": "MEDIUM"},
    {"name": "SOL_VOL_3x", "pop": 30, "gen": 70, "sl": 1.2, "tp": 4.5, "lev": 3, "risk": "HIGH"},
]


def log(msg):
    """Escribe al log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(line)
    
    print(line.strip())


def get_status():
    """Obtiene estado."""
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=10)
        return r.json()
    except:
        return {}


def create_wu(config):
    """Crea work unit."""
    try:
        conn = sqlite3.connect(f"{PROJECT_DIR}/coordinator.db")
        c = conn.cursor()
        
        params = {
            "name": config["name"],
            "category": "Futures",
            "population_size": config["pop"],
            "generations": config["gen"],
            "risk_level": config["risk"],
            "stop_loss": config["sl"],
            "take_profit": config["tp"],
            "leverage": config["lev"],
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 80000,
            "contracts": ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"]
        }
        
        c.execute('''
            INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_completed, replicas_assigned, created_at)
            VALUES (?, ?, ?, 0, 0, datetime('now'))
        ''', (json.dumps(params), "pending", 2))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        log(f"Error creando WU: {e}")
        return False


def run_cycle():
    """Ejecuta un ciclo."""
    status = get_status()
    
    if not status:
        log("⚠️ Coordinator no disponible")
        return
    
    wu = status.get("work_units", {})
    pending = wu.get("pending", 0)
    in_progress = wu.get("in_progress", 0)
    completed = wu.get("completed", 0)
    workers = status.get("workers", {}).get("active", 0)
    
    # Verificar workers activos
    if workers < 5:
        log(f"⚠️ Pocos workers activos: {workers}")
    
    # Mantener WUs pendientes
    needed = max(0, MIN_PENDING - pending)
    
    if needed > 0:
        log(f"➕ Creando {needed} WUs (pend: {pending}, proc: {in_progress})")
        
        for i in range(needed):
            config = CONFIGS[i % len(CONFIGS)].copy()
            config["name"] = f"{config['name']}_{datetime.now().strftime('%m%d%H%M%S')}"
            
            if create_wu(config):
                log(f"   ✅ {config['name']}")
            
            time.sleep(0.3)
    else:
        log(f"📊 WUs OK: {pending} pend | {in_progress} proc | {completed} done | {workers} workers")


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    
    if args.stop:
        # Detener daemon
        if os.path.exists(PID_FILE):
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            
            try:
                os.kill(pid, signal.SIGTERM)
                log(f"✅ Daemon detenido (PID: {pid})")
            except:
                log("❌ Error deteniendo")
            
            os.remove(PID_FILE)
        return
    
    # Verificar si ya está corriendo
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        
        try:
            os.kill(pid, 0)
            log(f"⚠️ Ya está corriendo (PID: {pid})")
            return
        except:
            os.remove(PID_FILE)
    
    # Escribir PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    # Cleanup al salir
    def cleanup():
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    
    atexit.register(cleanup)
    
    log("🚀 AUTO-MINER DAEMON INICIADO")
    log(f"   Mínimo WUs pendientes: {MIN_PENDING}")
    log(f"   Intervalo: {CHECK_INTERVAL}s")
    
    # Loop principal
    while True:
        try:
            run_cycle()
        except Exception as e:
            log(f"❌ Error: {e}")
        
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
