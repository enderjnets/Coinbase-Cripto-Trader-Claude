#!/usr/bin/env python3
"""
Actualiza el endpoint /api/status con más información
"""

# Ejecutar las actualizaciones necesarias en la base de datos
import sqlite3
import json
import requests

DB = "coordinator.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

# 1. Asegurar que el mejor resultado canónico sea el que tiene más trades positivos
# Seleccionar estrategia con buen balance entre trades y PnL
c.execute("""
    UPDATE results SET is_canonical = 0
""")

# Seleccionar el mejor con al menos 20 trades
c.execute("""
    UPDATE results SET is_canonical = 1
    WHERE id IN (
        SELECT id FROM results
        WHERE pnl > 0 AND trades >= 20
        ORDER BY pnl DESC
        LIMIT 1
    )
""")

# También seleccionar otros candidatos
c.execute("""
    UPDATE results SET is_canonical = 1
    WHERE id IN (
        SELECT id FROM results
        WHERE pnl > 500 AND trades >= 10
        ORDER BY pnl DESC
        LIMIT 5
    )
""")

conn.commit()
conn.close()

print("✅ Actualizado")

# Verificar
import requests
r = requests.get("http://localhost:5001/api/status")
data = r.json()
best = data.get('best_strategy', {})

print(f"Best PnL: ${best.get('pnl', 0):.2f}")
print(f"Trades: {best.get('trades', 0)}")
print(f"Win Rate: {best.get('win_rate', 0)*100:.1f}%")
