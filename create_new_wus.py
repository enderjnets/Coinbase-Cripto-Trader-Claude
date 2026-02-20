#!/usr/bin/env python3
"""Create new optimized work units for ULTIMATE trading system"""
import sqlite3
import json
from datetime import datetime

DB = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("="*60)
print("🆕 CREANDO NUEVOS WORK UNITS - ULTIMATE PLAN")
print("="*60)

# New optimized strategies for ULTIMATE trading
new_strategies = [
    {
        "name": "VWAP Scalping Ultimate",
        "category": "Scalping",
        "description": "VWAP bounce with RSI confirmation",
        "timeframes": ["1m", "5m"],
        "parameters": {
            "population_size": 200,
            "generations": 150,
            "mutation_rate": 0.15,
            "crossover_rate": 0.8,
            "elite_rate": 0.1,
            "risk_level": "HIGH",
            "stop_loss": 2.0,
            "take_profit": 5.0
        }
    },
    {
        "name": "Order Block & FVG Confluence",
        "category": "SMC",
        "description": "Smart Money Concepts - Order blocks + Fair Value Gaps",
        "timeframes": ["15m", "1h"],
        "parameters": {
            "population_size": 150,
            "generations": 100,
            "mutation_rate": 0.2,
            "crossover_rate": 0.85,
            "elite_rate": 0.1,
            "risk_level": "MEDIUM",
            "stop_loss": 3.0,
            "take_profit": 6.0
        }
    },
    {
        "name": "Multi-Timeframe Trend Following",
        "category": "Trend",
        "description": "Follow trends across 1h, 4h, 1d timeframes",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "population_size": 100,
            "generations": 80,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "elite_rate": 0.1,
            "risk_level": "LOW",
            "stop_loss": 5.0,
            "take_profit": 10.0
        }
    },
    {
        "name": "RSI Divergence + Volume",
        "category": "Technical",
        "description": "RSI divergences with volume confirmation",
        "timeframes": ["15m", "1h", "4h"],
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
    },
    {
        "name": "Opening Range Breakout Pro",
        "category": "Day Trading",
        "description": "ORB with volume confirmation and SMC filters",
        "timeframes": ["5m", "15m"],
        "parameters": {
            "population_size": 180,
            "generations": 120,
            "mutation_rate": 0.18,
            "crossover_rate": 0.82,
            "elite_rate": 0.1,
            "risk_level": "HIGH",
            "stop_loss": 2.0,
            "take_profit": 5.0
        }
    },
    {
        "name": "Supertrend + EMA Confluence",
        "category": "Technical",
        "description": "Supertrend with EMA crossovers for trend direction",
        "timeframes": ["5m", "15m", "1h"],
        "parameters": {
            "population_size": 150,
            "generations": 100,
            "mutation_rate": 0.15,
            "crossover_rate": 0.8,
            "elite_rate": 0.1,
            "risk_level": "MEDIUM",
            "stop_loss": 3.0,
            "take_profit": 6.0
        }
    },
    {
        "name": "Mean Reversion 1min",
        "category": "Scalping",
        "description": "Bollinger Band bounces with RSI filter",
        "timeframes": ["1m"],
        "parameters": {
            "population_size": 250,
            "generations": 200,
            "mutation_rate": 0.2,
            "crossover_rate": 0.85,
            "elite_rate": 0.1,
            "risk_level": "HIGH",
            "stop_loss": 1.5,
            "take_profit": 3.0
        }
    },
    {
        "name": "Gap & Go Crypto",
        "category": "Day Trading",
        "description": "Gap trading with volume profile confirmation",
        "timeframes": ["15m", "1h"],
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
    }
]

print(f"\n📝 Creando {len(new_strategies)} nuevos Work Units...\n")

for i, strategy in enumerate(new_strategies):
    params = {
        **strategy["parameters"],
        "name": strategy["name"],
        "category": strategy["category"],
        "description": strategy["description"],
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

# Verificar
c.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
pending = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM work_units")
total = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM work_units WHERE status='completed'")
completed = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM work_units WHERE status='cancelled'")
cancelled = c.fetchone()[0]

print(f"\n" + "="*60)
print("📊 RESUMEN FINAL")
print("="*60)
print(f"\n   ⏳ Pending: {pending}")
print(f"   ✅ Completed: {completed}")
print(f"   ❌ Cancelled: {cancelled}")
print(f"   📦 Total: {total}")

conn.close()

print("\n🎉 Nuevos WUs creados para el ULTIMATE TRADING SYSTEM")
