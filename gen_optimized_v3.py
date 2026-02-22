#!/usr/bin/env python3
"""
GENERADOR DE WUs OPTIMIZADOS v3
Basado en estrategias ganadoras
"""

import sqlite3
import json

DB = "coordinator.db"
conn = sqlite3.connect(DB)
c = conn.cursor()

strategies = [
    {"name": "OPTIMIZED_VolumeProfile_v3", "pop": 250, "gen": 300, "sl": 1.8, "tp": 4.5},
    {"name": "OPTIMIZED_BB_RSI_v3", "pop": 200, "gen": 250, "sl": 1.7, "tp": 4.6},
    {"name": "OPTIMIZED_CCI_v3", "pop": 280, "gen": 320, "sl": 1.9, "tp": 4.8},
    {"name": "OPTIMIZED_Stochastic_v3", "pop": 260, "gen": 300, "sl": 1.75, "tp": 4.7},
    {"name": "OPTIMIZED_ADX_v3", "pop": 275, "gen": 315, "sl": 1.85, "tp": 4.65},
]

print("="*60)
print("GENERANDO WUs OPTIMIZADOS")
print("="*60)

created = 0
for s in strategies:
    name = s["name"]
    
    c.execute("SELECT id FROM work_units WHERE strategy_params LIKE ?", (f"%{name}%",))
    if c.fetchone():
        print(f"⏭️  {name}: Ya existe")
        continue
    
    strategy = {
        "name": name,
        "category": "Optimized",
        "population_size": s["pop"],
        "generations": s["gen"],
        "mutation_rate": 0.20,
        "crossover_rate": 0.85,
        "elite_rate": 0.12,
        "risk_level": "HIGH",
        "stop_loss": s["sl"],
        "take_profit": s["tp"],
        "data_file": "BTC-USD_FIVE_MINUTE.csv",
        "max_candles": 200000
    }
    
    c.execute("INSERT INTO work_units (strategy_params, replicas_needed, status) VALUES (?, 2, 'pending')", (json.dumps(strategy),))
    print(f"✅ {name}")
    created += 1

conn.commit()
conn.close()

print(f"\n{created} WUs creados")
