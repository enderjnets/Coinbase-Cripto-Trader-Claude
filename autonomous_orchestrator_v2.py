#!/usr/bin/env python3
"""
🤖 AUTONOMOUS ORCHESTRATOR - V2
==========================

Usa TODOS los contratos de futuros disponibles
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

# TODOS los contratos disponibles de Coinbase Futures
ALL_CONTRACTS = [
    "BIT-27FEB26-CDE", "BIT-27MAR26-CDE", "BIT-24APR26-CDE", "BIT-22MAY26-CDE", "BIP-20DEC30-CDE",
    "ET-27FEB26-CDE", "ET-27MAR26-CDE", "ET-24APR26-CDE", "ETP-20DEC30-CDE",
    "SOL-27FEB26-CDE", "SOL-27MAR26-CDE", "SOL-24APR26-CDE", "SLP-20DEC30-CDE", "SLR-25FEB26-CDE",
    "XRP-27FEB26-CDE", "XPP-20DEC30-CDE",
    "ADA-27FEB26-CDE", "ADP-20DEC30-CDE",
    "DOG-27FEB26-CDE", "DOP-20DEC30-CDE",
    "AVP-20DEC30-CDE",
    "GOL-27MAR26-CDE",
    "NOL-19MAR26-CDE",
    "MC-19MAR26-CDE", "MC-18JUN26-CDE",
]

# Configuraciones para DAY TRADING (más trades)
CONFIGS = [
    # Config 1: BTC con todos los contratos BTC
    {
        "name": f"BTC_ALL_1min_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 30, "gen": 50, "sl": 0.5, "tp": 1.5, "lev": 5,
        "contracts": ["BIT-27FEB26-CDE", "BIT-27MAR26-CDE", "BIP-20DEC30-CDE"]
    },
    # Config 2: ETH
    {
        "name": f"ETH_ALL_1min_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 30, "gen": 50, "sl": 0.5, "tp": 1.5, "lev": 5,
        "contracts": ["ET-27FEB26-CDE", "ETP-20DEC30-CDE"]
    },
    # Config 3: SOL
    {
        "name": f"SOL_ALL_1min_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 30, "gen": 50, "sl": 0.5, "tp": 1.5, "lev": 5,
        "contracts": ["SOL-27FEB26-CDE", "SLP-20DEC30-CDE", "SLR-25FEB26-CDE"]
    },
    # Config 4: Multi-activo
    {
        "name": f"MULTI_ALL_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 40, "gen": 80, "sl": 0.3, "tp": 1.0, "lev": 3,
        "contracts": ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE", "XRP-27FEB26-CDE", "ADA-27FEB26-CDE"]
    },
    # Config 5: AGGRESIVO - más trades
    {
        "name": f"AGGR_DAILY_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 50, "gen": 100, "sl": 0.2, "tp": 0.8, "lev": 10,
        "contracts": ["BIT-27FEB26-CDE", "ET-27FEB26-CDE", "SOL-27FEB26-CDE"]
    },
    # Config 6: Todos los contratos
    {
        "name": f"ALL_CONTRACTS_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 40, "gen": 60, "sl": 0.3, "tp": 1.2, "lev": 3,
        "contracts": ALL_CONTRACTS[:10]  # Primeros 10
    },
]


def get_status():
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=10)
        return r.json()
    except:
        return {}


def create_wu(config):
    try:
        conn = sqlite3.connect(f"{PROJECT_DIR}/coordinator.db")
        c = conn.cursor()
        
        params = {
            "name": config["name"],
            "category": "Futures",
            "population_size": config["pop"],
            "generations": config["gen"],
            "risk_level": "HIGH",
            "stop_loss": config["sl"],
            "take_profit": config["tp"],
            "leverage": config["lev"],
            "data_file": "BTC-USD_ONE_MINUTE.csv",
            "max_candles": 86400,  # 60 días * 1 min
            "contracts": config["contracts"],
            "min_trades_per_day": 1,  # Al menos 1 trade por día
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
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🤖 AUTONOMOUS ORCHESTRATOR V2")
    
    status = get_status()
    if not status:
        print("❌ Coordinator no disponible")
        return
    
    wu = status.get("work_units", {})
    pending = wu.get("pending", 0)
    completed = wu.get("completed", 0)
    workers = status.get("workers", {}).get("active", 0)
    
    print(f"   📊 WUs: {completed} completadas | {pending} pendientes")
    print(f"   👷 Workers: {workers}")
    
    # Mantener al menos 10 WUs pendientes
    needed = max(0, 10 - pending)
    
    if needed > 0:
        print(f"   ➕ Creando {needed} work units con TODOS los contratos...")
        
        for i in range(needed):
            config = CONFIGS[i % len(CONFIGS)].copy()
            config["name"] = f"{config['name']}_{datetime.now().strftime('%m%d%H%M%S')}"
            
            if create_wu(config):
                print(f"      ✅ {config['name']}")
                print(f"         Contratos: {len(config['contracts'])}")
            
            time.sleep(0.3)
    else:
        print(f"   ✅ Suficientes WUs pendientes")


if __name__ == "__main__":
    main()
