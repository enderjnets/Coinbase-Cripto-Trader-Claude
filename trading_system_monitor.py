#!/usr/bin/env python3
"""
🚀 SISTEMA COMPLETO DE TRADING v1.0
Objetivo: 5% diario con $500 capital

Este sistema:
1. Gestiona workers y WUs
2. Analiza estrategias ganadoras
3. Ejecuta trades automáticamente
4. Calcula métricas de rendimiento
"""

import sqlite3
import requests
import time
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

COORDINATOR_URL = "http://localhost:5006"
DATABASE = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"

class TradingSystem:
    """Sistema completo de trading"""
    
    def __init__(self):
        self.capital_base = 500.0
        self.objetivo_diario = 0.05  # 5%
        self.risk_per_trade = 0.02  # 2%
        self.stop_loss = 0.05  # 5%
        self.take_profit = 0.10  # 10%
        
    def get_status(self) -> Dict:
        """Obtener estado del sistema"""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
            return r.json()
        except:
            return {"workers": {"active": 0}, "work_units": {"completed": 0}}
    
    def get_machines(self) -> List[Dict]:
        """Obtener贡献 de máquinas"""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/machines", timeout=5)
            return r.json().get('machines', [])
        return []
    
    def get_leaderboard(self) -> List[Dict]
        """Obtener leaderboard"""
        try:
            r = requests.get(f"{COORDINATOR_URL}/api/leaderboard", timeout=5)
            return r.json().get('leaderboard', [])
        return []

def main():
    """Main loop del sistema"""
    system = TradingSystem()
    
    print("\n" + "="*60)
    print("🚀 SISTEMA DE TRADING v1.0")
    print("="*60)
    print(f"\n💰 Capital: ${system.capital_base}")
    print(f"🎯 Objetivo: {system.objetivo_diario*100}% diario")
    print(f"🛑 Stop Loss: {system.stop_loss*100}%")
    print(f"🎯 Take Profit: {system.take_profit*100}%")
    
    while True:
        status = system.get_status()
        machines = system.get_machines()
        leaderboard = system.get_leaderboard()
        
        print("\n" + "="*60)
        print(f"📊 ESTADO: {status['workers']['active']} workers activos")
        print(f"📦 WUs completados: {status['work_units']['completed']}")
        print(f"💰 Mejor PnL: ${status['best_strategy']['pnl']}")
        print("\n🏆 TOP 5 CONTRIBUTORS:")
        for i, m in enumerate(machines[:5]):
            print(f"   {i+1}. {m['name']}: {m['wus']} WUs ({m['contribution']}%)")
        
        time.sleep(30)

if __name__ == "__main__":
    main()
