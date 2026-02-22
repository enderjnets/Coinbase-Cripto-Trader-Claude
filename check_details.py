#!/usr/bin/env python3
"""
Dashboard actualizado con más detalles
"""

import sqlite3
import json

DB = "coordinator.db"

# Actualizar la consulta para incluir más detalles
conn = sqlite3.connect(DB)
c = conn.cursor()

# Ver estructura de resultados
print("=== ESTRUCTURE ===")

# Ver mejor resultado con estrategia
c.execute("""
    SELECT r.pnl, r.trades, r.win_rate, r.sharpe_ratio, r.max_drawdown, w.strategy_params
    FROM results r
    JOIN work_units w ON r.work_unit_id = w.id
    WHERE r.is_canonical = 1
    ORDER BY r.pnl DESC
    LIMIT 5
""")

print("\n=== BEST STRATEGIES ===")
for row in c.fetchall():
    pnl, trades, win_rate, sharpe, max_dd, params_json = row
    params = json.loads(params_json)
    
    print(f"\n---")
    print(f"PnL: ${pnl:.2f}")
    print(f"Trades: {trades}")
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Sharpe: {sharpe:.2f}")
    print(f"Max DD: {max_dd*100:.2f}%")
    print(f"\nStrategy Details:")
    print(f"  Name: {params.get('name', 'N/A')}")
    print(f"  Category: {params.get('category', 'N/A')}")
    print(f"  Population: {params.get('population_size', 'N/A')}")
    print(f"  Generations: {params.get('generations', 'N/A')}")
    print(f"  Risk: {params.get('risk_level', 'N/A')}")
    print(f"  Stop Loss: {params.get('stop_loss', 'N/A')}%")
    print(f"  Take Profit: {params.get('take_profit', 'N/A')}%")
    print(f"  Leverage: {params.get('leverage', 'N/A')}x")
    print(f"  Data File: {params.get('data_file', 'N/A')}")
    print(f"  Max Candles: {params.get('max_candles', 'N/A')}")
    print(f"  Contracts: {params.get('contracts', [])}")

conn.close()
