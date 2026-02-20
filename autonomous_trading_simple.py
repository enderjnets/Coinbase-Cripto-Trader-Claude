#!/usr/bin/env python3
"""AUTONOMOUS TRADING SYSTEM - Capital $500 | Meta: Doblar mensualmente"""

import requests
import time
from datetime import datetime

COORDINATOR_URL = "http://localhost:5006"
CONFIG = {'capital_base': 500.0}

def get_status():
    try:
        return requests.get(f"{COORDINATOR_URL}/api/status", timeout=5).json()
    except:
        return {'workers': {'active': 0}, 'best_strategy': {'pnl': 0}, 'work_units': {'completed': 0}}

def get_leaderboard():
    try:
        return requests.get(f"{COORDINATOR_URL}/api/leaderboard").json().get('leaderboard', [])
    except:
        return []

def get_machines():
    try:
        return requests.get(f"{COORDINATOR_URL}/api/machines").json().get('machines', [])
    except:
        return []

def main():
    print("\n" + "="*60)
    print("  TRADING AUTONOMO v1.0")
    print("="*60)
    print(f"\nCapital: ${CONFIG['capital_base']}")
    print("Meta: Doblar mensualmente")
    print("Risk: 2% | Stop: 5% | Take: 10%")
    
    while True:
        status = get_status()
        leaderboard = get_leaderboard()
        machines = get_machines()
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Workers: {status['workers']['active']} | WUs: {status['work_units']['completed']} | Best: ${status['best_strategy']['pnl']:.2f}")
        
        print("\nTOP 5 STRATEGIES:")
        for i, s in enumerate(leaderboard[:5]):
            name = s.get('friendly_name', 'N/A')[:20]
            wus = s.get('work_units', 0)
            cpu = s.get('execution_time_hours', 0)
            print(f"  {i+1}. {name:20s} | {wus:,} WUs | {cpu:.1f}h CPU")
        
        print("\nMACHINES:")
        for m in machines[:4]:
            icon = m.get('icon', 'C')
            name = m.get('name', 'N/A')
            contrib = m.get('contribution', 0)
            print(f"  {icon} {name:18s} | {contrib}%")
        
        time.sleep(30)

if __name__ == '__main__':
    main()
