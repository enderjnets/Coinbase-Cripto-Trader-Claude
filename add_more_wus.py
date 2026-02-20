#!/usr/bin/env python3
"""Add more work units to complete the ULTIMATE plan"""
import sqlite3
import json
from datetime import datetime

DB = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

# Check current pending
c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
current = c.fetchone()[0]
print(f"📊 WUs pendientes actuales: {current}")

# Add more strategies
additional_strategies = [
    {
        "name": "Bull Flag & Bear Flag Master",
        "category": "Patterns",
        "timeframes": ["15m", "1h"],
        "parameters": {
            "population_size": 150,
            "generations": 120,
            "mutation_rate": 0.18,
            "crossover_rate": 0.82,
            "elite_rate": 0.1,
            "risk_level": "MEDIUM",
            "stop_loss": 3.0,
            "take_profit": 6.0
        }
    },
    {
        "name": "Volume Profile + SMC",
        "category": "Volume",
        "timeframes": ["1h", "4h"],
        "parameters": {
            "population_size": 100,
            "generations": 80,
            "mutation_rate": 0.15,
            "crossover_rate": 0.8,
            "elite_rate": 0.1,
            "risk_level": "MEDIUM",
            "stop_loss": 4.0,
            "take_profit": 8.0
        }
    },
    {
        "name": "Liquidity Sweeps & Reversals",
        "category": "SMC",
        "timeframes": ["5m", "15m"],
        "parameters": {
            "population_size": 180,
            "generations": 100,
            "mutation_rate": 0.2,
            "crossover_rate": 0.85,
            "elite_rate": 0.1,
            "risk_level": "HIGH",
            "stop_loss": 2.0,
            "take_profit": 5.0
        }
    },
    {
        "name": "ICT Premium/Discount Zones",
        "category": "ICT",
        "timeframes": ["1h", "4h"],
        "parameters": {
            "population_size": 120,
            "generations": 100,
            "mutation_rate": 0.15,
            "crossover_rate": 0.8,
            "elite_rate": 0.1,
            "risk_level": "MEDIUM",
            "stop_loss": 3.0,
            "take_profit": 7.0
        }
    }
]

print(f"\n📝 Agregando {len(additional_strategies)} estrategias adicionales...\n")

for i, strategy in enumerate(additional_strategies):
    params = {
        **strategy["parameters"],
        "name": strategy["name"],
        "category": strategy["category"],
        "timeframes": strategy["timeframes"],
        "target_pnl_percent": 5.0,
        "created_for": "ULTIMATE_TRADING_SYSTEM"
    }
    
    c.execute('''
        INSERT INTO work_units (strategy_params, replicas_needed, status, created_at)
        VALUES (?, 3, 'pending', ?)
    ''', (json.dumps(params), datetime.now().isoformat()))
    
    print(f"   ✅ WU #{i+1}: {strategy['name']}")
    print(f"       📊 Pop: {params['population_size']} | Gen: {params['generations']} | Risk: {params['risk_level']}")

conn.commit()

# Final count
c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
pending = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM work_units")
total = c.fetchone()[0]

print(f"\n" + "="*60)
print("📊 RESUMEN FINAL")
print("="*60)
print(f"\n   ⏳ Pending: {pending}")
print(f"   ✅ Total WUs: {total}")
print(f"\n🎉 Sistema listo para procesar {pending} nuevos WUs!")

conn.close()
