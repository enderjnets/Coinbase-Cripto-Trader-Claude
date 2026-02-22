#!/usr/bin/env python3
"""
🎯 GENERADOR DE ESTRATEGIAS OPTIMIZADAS
======================================

Parámetros optimizados para encontrar estrategias:
- Rentables
- Con muchos trades (day trading)
- Bajo riesgo
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

# Contratos disponibles
CONTRACTS = [
    "BIT-27FEB26-CDE", "BIT-27MAR26-CDE", "BIP-20DEC30-CDE",
    "ET-27FEB26-CDE", "ET-27MAR26-CDE", "ETP-20DEC30-CDE",
    "SOL-27FEB26-CDE", "SOL-27MAR26-CDE", "SLP-20DEC30-CDE",
]

# Configuraciones óptimas para day trading rentable
# El secreto: SL y TP más grandes para evitar ruido, 
# pero con momentum detection para más trades

CONFIGS = [
    # 1. SL moderate, TP moderate - Balance riesgo/retorno
    {
        "name": f"BALANCED_1min_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 40, "gen": 80,
        "sl": 1.0, "tp": 2.5, "lev": 3,
        "contracts": CONTRACTS[:5]
    },
    # 2. SL pequeño pero TP más grande - menos trades pero mejor ratio
    {
        "name": f"RATIO_1min_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 50, "gen": 100,
        "sl": 0.8, "tp": 3.0, "lev": 2,
        "contracts": CONTRACTS[:5]
    },
    # 3. Alta frecuencia con SL muy pequeño
    {
        "name": f"HIGH_FREQ_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 30, "gen": 50,
        "sl": 0.3, "tp": 0.8, "lev": 5,
        "contracts": CONTRACTS[:3]
    },
    # 4. Baja frecuencia con SL grande
    {
        "name": f"LOW_FREQ_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 60, "gen": 120,
        "sl": 2.0, "tp": 5.0, "lev": 2,
        "contracts": CONTRACTS
    },
    # 5. Momentum - entra en tendencias
    {
        "name": f"MOMENTUM_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 45, "gen": 90,
        "sl": 1.5, "tp": 4.0, "lev": 3,
        "contracts": CONTRACTS[:6]
    },
    # 6. Conservative - bajo riesgo
    {
        "name": f"CONSERVATIVE_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 50, "gen": 100,
        "sl": 2.5, "tp": 6.0, "lev": 2,
        "contracts": CONTRACTS[:4]
    },
    # 7. Medium risk - balance
    {
        "name": f"MEDIUM_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 40, "gen": 80,
        "sl": 1.2, "tp": 3.5, "lev": 3,
        "contracts": CONTRACTS[:5]
    },
    # 8. Aggressive pero con más capital por trade
    {
        "name": f"AGRO_1min_{datetime.now().strftime('%m%d%H%M')}",
        "pop": 35, "gen": 70,
        "sl": 1.0, "tp": 4.0, "lev": 4,
        "contracts": CONTRACTS[:4]
    },
]


def create_wu(config):
    try:
        conn = sqlite3.connect(f"{PROJECT_DIR}/coordinator.db")
        c = conn.cursor()
        
        params = {
            "name": config["name"],
            "category": "Futures",
            "population_size": config["pop"],
            "generations": config["gen"],
            "risk_level": "MEDIUM",
            "stop_loss": config["sl"],
            "take_profit": config["tp"],
            "leverage": config["lev"],
            "data_file": "bitcoin.csv",
            "max_candles": 86400,  # 60 días
            "contracts": config["contracts"]
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
    # Ver estado actual
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=10)
        status = r.json()
        wu = status.get("work_units", {})
        pending = wu.get("pending", 0)
        workers = status.get("workers", {}).get("active", 0)
    except:
        print("❌ Coordinator no disponible")
        return
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎯 GENERADOR OPTIMIZADO")
    print(f"   WUs: {wu.get('completed', 0)} completadas | {pending} pendientes")
    print(f"   Workers: {workers}")
    
    # Crear nuevas WUs si hay menos de 15 pendientes
    if pending < 15:
        created = 0
        for config in CONFIGS:
            config = config.copy()
            config["name"] = f"{config['name']}_{datetime.now().strftime('%m%d%H%M%S')}"
            
            if create_wu(config):
                created += 1
                # Mostrar config
                print(f"   ✅ {config['name']}")
                print(f"      SL: {config['sl']}% | TP: {config['tp']}% | Lev: {config['lev']}x | Contratos: {len(config['contracts'])}")
        
        print(f"   ➕ Creadas {created} nuevas WUs")
    else:
        print(f"   ✅ Suficientes WUs ({pending} pendientes)")


if __name__ == "__main__":
    main()
