#!/usr/bin/env python3
"""Fix the database state"""
import sqlite3

DB = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/coordinator.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

print("=== ESTADO ANTES ===")
c.execute("SELECT status, COUNT(*) FROM work_units GROUP BY status")
for s, n in c.fetchall():
    print(f"  {s}: {n}")

print(f"\nResultados: {c.execute('SELECT COUNT(*) FROM results').fetchone()[0]}")

# Cancel all non-completed WUs
c.execute("UPDATE work_units SET status='cancelled' WHERE status!='completed'")

# Delete all results
c.execute("DELETE FROM results")

print("\n=== ESTADO DESPUÉS ===")
c.execute("SELECT status, COUNT(*) FROM work_units GROUP BY status")
for s, n in c.fetchall():
    print(f"  {s}: {n}")

print(f"\nResultados: {c.execute('SELECT COUNT(*) FROM results').fetchone()[0]}")

conn.commit()
conn.close()
print("\n✅ Base de datos limpiada")
