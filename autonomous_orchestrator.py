#!/usr/bin/env python3
"""
🤖 AUTONOMOUS ORCHESTRATOR
===========================

Mantiene el sistema ejecutando:
- Crea work units cuando hay menos de 5 pendientes
- Analiza resultados
- Optimiza automáticamente

Se ejecuta cada 5 minutos via cron o daemon
"""

import os
import sys
import time
import json
import sqlite3
import requests
from datetime import datetime

PROJECT_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_URL = "http://localhost:5001"

# Configuraciones de WU
CONFIGS = [
    {"name": "BTC_Hgh_Lev", "pop": 30, "gen": 80, "sl": 1.0, "tp": 5.0, "lev": 3, "risk": "HIGH"},
    {"name": "ETH_Med_Lev", "pop": 30, "gen": 80, "sl": 1.5, "tp": 4.0, "lev": 2, "risk": "MEDIUM"},
    {"name": "SOL_Hgh_Lev", "pop": 25, "gen": 60, "sl": 1.0, "tp": 5.0, "lev": 5, "risk": "HIGH"},
    {"name": "BTC_Aggr", "pop": 40, "gen": 100, "sl": 0.8, "tp": 6.0, "lev": 4, "risk": "HIGH"},
    {"name": "ETH_Safe", "pop": 20, "gen": 50, "sl": 2.0, "tp": 3.0, "lev": 1, "risk": "LOW"},
]


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
        print(f"Error: {e}")
        return False


def main():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🤖 Autonomous Orchestrator")
    
    # Obtener estado
    status = get_status()
    
    if not status:
        print("❌ Coordinator no disponible")
        return
    
    wu = status.get("work_units", {})
    pending = wu.get("pending", 0)
    in_progress = wu.get("in_progress", 0)
    completed = wu.get("completed", 0)
    workers = status.get("workers", {}).get("active", 0)
    
    print(f"   📊 WUs: {pending} pend | {in_progress} proc | {completed} done")
    print(f"   👷 Workers: {workers}")
    
    # Mantener al menos 5 WUs pendientes
    needed = max(0, 5 - pending)
    
    if needed > 0:
        print(f"   ➕ Creando {needed} work units...")
        
        for i in range(needed):
            config = CONFIGS[i % len(CONFIGS)]
            
            # Variar un poco
            config = {**config}
            config["name"] = f"{config['name']}_{datetime.now().strftime('%m%d%H%M')}"
            
            if create_wu(config):
                print(f"      ✅ {config['name']}")
            
            time.sleep(0.5)
    else:
        print(f"   ✅ Suficientes WUs pendientes")
    
    # Ver mejores resultados
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/results?limit=5", timeout=10)
        results = r.json().get("results", [])
        
        if results:
            best = max(results, key=lambda x: x.get("pnl", 0))
            print(f"   🏆 Mejor: ${best.get('pnl', 0):.2f}")
    except:
        pass
    
    print()


if __name__ == "__main__":
    main()
