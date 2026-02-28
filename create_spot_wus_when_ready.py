#!/usr/bin/env python3
"""
Espera que los archivos SPOT tengan suficientes datos (>= 5000 filas)
y luego crea automáticamente work units para cada par.
"""
import sqlite3, json, time, os
from pathlib import Path

PROJECT = Path(__file__).parent
DATA_DIR = PROJECT / "data"
DB_PATH = PROJECT / "coordinator.db"

MIN_ROWS = 5000  # Mínimo para backtesting útil (~17 días de 5min)

SPOT_ASSETS = [
    "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
    "LTC-USD", "ATOM-USD"
]

TIMEFRAMES = ["FIVE_MINUTE", "FIFTEEN_MINUTE"]

WU_CONFIGS = [
    {"population_size": 300, "generations": 350, "mutation_rate": 0.18, "crossover_rate": 0.87,
     "elite_rate": 0.12, "risk_level": "HIGH", "stop_loss": 1.8, "take_profit": 4.5},
    {"population_size": 280, "generations": 320, "mutation_rate": 0.20, "crossover_rate": 0.88,
     "elite_rate": 0.10, "risk_level": "HIGH", "stop_loss": 1.5, "take_profit": 4.0},
    {"population_size": 250, "generations": 300, "mutation_rate": 0.17, "crossover_rate": 0.86,
     "elite_rate": 0.10, "risk_level": "HIGH", "stop_loss": 2.0, "take_profit": 5.0},
]


def count_rows(filepath):
    try:
        with open(filepath) as f:
            return sum(1 for _ in f) - 1  # minus header
    except:
        return 0


def create_wus_for_file(data_file, conn):
    created = 0
    for wu_cfg in WU_CONFIGS:
        params = {**wu_cfg, "data_file": data_file, "max_candles": 100000,
                  "name": f"{data_file.replace('.csv','')}_p{wu_cfg['population_size']}_g{wu_cfg['generations']}"}
        conn.execute(
            "INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_assigned, replicas_completed) VALUES (?, 'pending', 2, 0, 0)",
            (json.dumps(params),)
        )
        created += 1
    return created


def main():
    print("Watching for completed data downloads...")
    created_for = set()

    while True:
        pending = []
        for asset in SPOT_ASSETS:
            for tf in TIMEFRAMES:
                fname = f"{asset}_{tf}.csv"
                fpath = DATA_DIR / fname
                rows = count_rows(fpath)
                if rows >= MIN_ROWS and fname not in created_for:
                    pending.append((fname, rows))

        if pending:
            conn = sqlite3.connect(DB_PATH)
            total_created = 0
            for fname, rows in pending:
                n = create_wus_for_file(fname, conn)
                total_created += n
                created_for.add(fname)
                print(f"  Created {n} WUs for {fname} ({rows:,} rows)")
            conn.commit()
            conn.close()
            print(f"Total created: {total_created} WUs")

        # Check if all files are done
        all_done = all(
            count_rows(DATA_DIR / f"{asset}_{tf}.csv") >= MIN_ROWS
            for asset in SPOT_ASSETS for tf in TIMEFRAMES
        )

        if all_done and len(created_for) >= len(SPOT_ASSETS) * len(TIMEFRAMES):
            print("\nAll files downloaded and WUs created!")
            break

        # Status update
        ready = sum(1 for a in SPOT_ASSETS for tf in TIMEFRAMES
                    if count_rows(DATA_DIR / f"{a}_{tf}.csv") >= MIN_ROWS)
        total = len(SPOT_ASSETS) * len(TIMEFRAMES)
        print(f"Progress: {ready}/{total} files ready | {len(created_for)} WU sets created")
        time.sleep(30)


if __name__ == "__main__":
    main()
