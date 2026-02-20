#!/usr/bin/env python3
"""
Sistema de Trading Simple
Monitorea el sistema y muestra métricas
"""

import requests
import time
import json

COORDINATOR_URL = "http://localhost:5006"

def get_status():
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
        return r.json()
    except:
        return {"workers": {"active": 0}, "work_units": {"completed": 0, "total": 0}}

def get_machines():
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/machines", timeout=5)
        return r.json().get("machines", [])
    except:
        return []

def get_leaderboard():
    try:
        r = requests.get(f"{COORDINATOR_URL}/api/leaderboard", timeout=5)
        return r.json().get("leaderboard", [])
    except:
        return []

print("\n" + "="*60)
print("🚀 SISTEMA DE TRADING v1.0")
print("="*60)
print("\n💰 Capital: $500")
print("🎯 Objetivo: 5% diario")
print("🛑 Stop Loss: 5%")
print("🎯 Take Profit: 10%")
print("📊 Riesgo por trade: 2%")

while True:
    status = get_status()
    machines = get_machines()
    lb = get_leaderboard()
    
    print("\n" + "-"*60)
    print(f"📊 Workers activos: {status['workers']['active']}")
    print(f"📦 WUs completados: {status['work_units']['completed']}/{status['work_units']['total']}")
    print(f"💰 Mejor PnL: ${status['best_strategy']['pnl']:.2f}")
    
    print("\n🏆 CONTRIBUCION:")
    for i, m in enumerate(machines[:5]):
        print(f"   {i+1}. {m['name']}: {m['wus']:,} WUs ({m['contribution']}%)")
    
    print("\n" + "="*60)
    print("Esperando 30 segundos...")
    time.sleep(30)
