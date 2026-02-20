#!/usr/bin/env python3
"""
🚀 AUTONOMOUS TRADING SYSTEM v1.0
Capital: $500 | Meta: Doblar mensualmente (~5% diario)
Risk: 2% por trade | Stop Loss: 5% | Take Profit: 10%
"""

import requests
import time
import json
from datetime import datetime

COORDINATOR_URL = "http://localhost:5006"

# Configuración
CONFIG = {
    'capital_base': 500.0,
    'risk_per_trade': 0.02,  # 2%
    'stop_loss': 0.05,
    'take_profit': 0.10,
    'min_confidence': 0.6,
}

def get_status():
    """Estado del coordinator"""
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
        return r.json()
    except:
        return {'workers': {'active': 0}, 'best_strategy': {'pnl': 0}, 'work_units': {'completed': 0}}

def get_leaderboard():
    """Mejores estrategias"""
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/leaderboard")
        return r.json().get('leaderboard', [])
    except:
        return []

def get_machines():
    """Contribución por máquina"""
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/machines")
        return r.json().get('machines', [])
    except:
        return []

def main():
    """Loop principal"""
    print("\n" + "="*60)
    print("🚀 AUTONOMOUS TRADING SYSTEM v1.0")
    print("="*60)
    print(f"\n💰 Capital: ${CONFIG['capital_base']}")
    print(f"🎯 Meta: Doblar mensualmente")
    print(f"Risk: 2% | Stop: 5% | Take: 10%")
    
    while True:
        status = get_status()
        leaderboard = get_leaderboard()
        machines = get_machines()
        
        print(f"\n📊 [{datetime.now().strftime('%H:%M:%S')}")
        print("-"*60)
        print(f"Workers activos: {status['workers']['active']}")
        print(f"WUs completados: {status['work_units']['completed']}")
        print(f"Mejor PnL: ${status['best_strategy']['pnl']:.2f}")
        
        print(f"\n🏆 TOP 5 ESTRATEGIAS:")
        for i, s in enumerate(leaderboard[:5]):
            print(f"   {i+1}. {s.get('friendly_name', 'N/A')[:25]:25s} | {s.get('work_units', 0):,} WUs | {s.get('execution_time_hours', 0):.1f}h CPU")
        
        print(f"\n🤖 MÁQUINAS CONTRIBUYENDO:")
        for m in machines[:4]:
            print(f"   {m.get('icon', '💻') {m.get('name', 'N/A'):20s} | {m.get('contribution', 0)}%")
        
        time.sleep(30)

if __name__ == '__main__':
    main()
