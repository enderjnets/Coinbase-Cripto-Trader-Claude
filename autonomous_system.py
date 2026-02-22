#!/usr/bin/env python3
"""
SISTEMA DE TRADING AUTONOMO COMPLETO
Objetivo: 5% diario = 2x mensual
"""

import sqlite3
import json
import subprocess
import time
from datetime import datetime

DB = "coordinator.db"

def get_stats():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    stats = {
        'wu_total': c.execute("SELECT COUNT(*) FROM work_units").fetchone()[0],
        'wu_pending': c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'").fetchone()[0],
        'max_pnl': c.execute("SELECT MAX(pnl) FROM results").fetchone()[0],
        'workers': c.execute("SELECT COUNT(*) FROM workers").fetchone()[0],
        'positive': c.execute("SELECT COUNT(*) FROM results WHERE pnl > 0").fetchone()[0]
    }
    
    conn.close()
    return stats

def generate_wus():
    """Genera WUs optimizados"""
    try:
        subprocess.run(["python3", "generate_advanced_wus.py"], capture_output=True, timeout=60)
        return True
    except Exception as e:
        return False

def analyze_results():
    """Analiza resultados"""
    try:
        subprocess.run(["python3", "analyze_performance_advanced.py"], capture_output=True, timeout=30)
        return True
    except:
        return False

def main():
    cycle = 0
    print("="*60)
    print("SISTEMA DE TRADING AUTONOMO")
    print("Objetivo: 5% diario")
    print("="*60)
    
    while True:
        cycle += 1
        now = datetime.now().strftime("%H:%M:%S")
        stats = get_stats()
        
        print(f"[{now}] WU: {stats['wu_total']} | PnL: ${stats['max_pnl']} | Workers: {stats['workers']}")
        
        if cycle % 10 == 0:
            generate_wus()
            print("WUs generados")
        
        if cycle % 5 == 0:
            analyze_results()
        
        time.sleep(30)

if __name__ == "__main__":
    main()
