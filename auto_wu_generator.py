#!/usr/bin/env python3
"""
🤖 Auto-Generador de Work Units
================================

Monitorea los WUs pendientes y genera más automáticamente cuando
están bajos para mantener a los workers siempre ocupados.

Uso:
    python auto_wu_generator.py                    # Una vez
    python auto_wu_generator.py --daemon           # Corre continuamente
    python auto_wu_generator.py --status           # Ver estado
"""

import os
import sys
import json
import sqlite3
import time
import argparse
from pathlib import Path
from datetime import datetime

# Configuración
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DATA_DIR = PROJECT_DIR / "data"
DATA_FUTURES_DIR = PROJECT_DIR / "data_futures"
DB_PATH = PROJECT_DIR / "coordinator.db"
LOG_FILE = PROJECT_DIR / "auto_wu.log"

# Configuración por defecto
DEFAULT_CONFIG = {
    "min_pending": 50,      # Generar más cuando pendientes < 50
    "wu_to_generate": 100,  # Crear 100 WUs cada vez
    "check_interval": 300,  # Revisar cada 5 minutos
}

def log(msg):
    """Log con timestamp"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_wu_counts():
    """Obtener conteo de WUs por estado"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM work_units
        GROUP BY status
    """)

    counts = {row["status"]: row["count"] for row in cursor.fetchall()}
    conn.close()

    return {
        "pending": counts.get("pending", 0),
        "in_progress": counts.get("in_progress", 0),
        "completed": counts.get("completed", 0),
        "assigned": counts.get("assigned", 0),
    }

def get_available_data_files():
    """Obtener archivos de datos disponibles"""
    spot_files = []
    futures_files = []

    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.csv"):
            if f.is_file() and not f.is_symlink() and f.stat().st_size > 1024:
                spot_files.append({
                    "filename": f.name,
                    "path": str(DATA_DIR),
                    "type": "spot"
                })

    if DATA_FUTURES_DIR.exists():
        for f in DATA_FUTURES_DIR.glob("*.csv"):
            if f.is_file() and f.stat().st_size > 1024:
                contract = f.stem.split("_")[0]
                futures_files.append({
                    "filename": f.name,
                    "path": str(DATA_FUTURES_DIR),
                    "type": "futures",
                    "contract": contract
                })

    return spot_files, futures_files

def get_existing_data_files_in_wus():
    """Obtener archivos que ya tienen WUs"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT json_extract(strategy_params, '$.data_file') as data_file
        FROM work_units
        WHERE data_file IS NOT NULL
    """)

    existing = {row["data_file"] for row in cursor.fetchall()}
    conn.close()
    return existing

def generate_work_units(count, spot_files, futures_files):
    """Generar work units"""
    conn = get_db_connection()
    cursor = conn.cursor()

    timestamp = int(datetime.now().timestamp())
    created = 0

    # Configuraciones de WU
    spot_configs = [
        {"risk": "LOW", "pop": 100, "gen": 150, "max_candles": 10000},
        {"risk": "MEDIUM", "pop": 100, "gen": 150, "max_candles": 10000},
        {"risk": "HIGH", "pop": 80, "gen": 100, "max_candles": 5000},
    ]

    futures_configs = [
        {"risk": "LOW", "pop": 150, "gen": 200, "max_candles": 5000, "leverage": 2},
        {"risk": "MEDIUM", "pop": 150, "gen": 200, "max_candles": 5000, "leverage": 3},
    ]

    # Generar WUs SPOT
    for sf in spot_files:
        if created >= count:
            break

        for cfg in spot_configs:
            if created >= count:
                break

            wu_name = f"{sf['filename'].split('_')[0]}_auto_{cfg['risk']}_{timestamp}"

            strategy_params = {
                "name": wu_name,
                "category": "Spot",
                "population_size": cfg["pop"],
                "generations": cfg["gen"],
                "risk_level": cfg["risk"],
                "data_file": sf["filename"],
                "max_candles": cfg["max_candles"],
                "data_dir": sf["path"],
                "market_type": "SPOT",
                "auto_generated": True
            }

            try:
                cursor.execute("""
                    INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_assigned, replicas_completed, created_at)
                    VALUES (?, 'pending', 2, 0, 0, ?)
                """, (json.dumps(strategy_params), timestamp))
                created += 1
            except Exception as e:
                pass

    # Generar WUs FUTURES
    for ff in futures_files:
        if created >= count:
            break

        for cfg in futures_configs:
            if created >= count:
                break

            base = ff["contract"].split("-")[0]
            wu_name = f"{base}_auto_{cfg['risk']}_L{cfg['leverage']}_{timestamp}"

            strategy_params = {
                "name": wu_name,
                "category": "Futures",
                "population_size": cfg["pop"],
                "generations": cfg["gen"],
                "risk_level": cfg["risk"],
                "data_file": ff["filename"],
                "max_candles": cfg["max_candles"],
                "data_dir": ff["path"],
                "contract": ff["contract"],
                "market_type": "FUTURES",
                "leverage": cfg["leverage"],
                "auto_generated": True
            }

            try:
                cursor.execute("""
                    INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_assigned, replicas_completed, created_at)
                    VALUES (?, 'pending', 2, 0, 0, ?)
                """, (json.dumps(strategy_params), timestamp))
                created += 1
            except Exception as e:
                pass

    conn.commit()
    conn.close()

    return created

def check_and_generate(config):
    """Verificar y generar WUs si es necesario"""
    counts = get_wu_counts()

    log(f"📊 Estado: {counts['pending']} pendientes, {counts['in_progress']} en progreso")

    if counts["pending"] < config["min_pending"]:
        log(f"⚠️ Pendientes ({counts['pending']}) < mínimo ({config['min_pending']})")

        spot_files, futures_files = get_available_data_files()
        log(f"📁 Datos disponibles: {len(spot_files)} SPOT, {len(futures_files)} FUTURES")

        created = generate_work_units(config["wu_to_generate"], spot_files, futures_files)
        log(f"✅ {created} Work Units generados")

        return created
    else:
        log(f"✅ WUs suficientes")
        return 0

def run_daemon(config):
    """Correr como daemon"""
    log("="*50)
    log("🤖 AUTO-WU GENERATOR - MODO DAEMON")
    log("="*50)
    log(f"   Min pendientes: {config['min_pending']}")
    log(f"   WUs a generar: {config['wu_to_generate']}")
    log(f"   Intervalo: {config['check_interval']}s")
    log("="*50)

    while True:
        try:
            check_and_generate(config)
        except Exception as e:
            log(f"❌ Error: {e}")

        time.sleep(config["check_interval"])

def show_status():
    """Mostrar estado actual"""
    counts = get_wu_counts()
    spot_files, futures_files = get_available_data_files()

    print("\n" + "="*50)
    print("📊 ESTADO DEL SISTEMA")
    print("="*50)

    print(f"\n📋 Work Units:")
    print(f"   Pendientes:   {counts['pending']}")
    print(f"   En progreso:  {counts['in_progress']}")
    print(f"   Completados:  {counts['completed']}")
    print(f"   Asignados:    {counts['assigned']}")

    print(f"\n📁 Datos:")
    print(f"   SPOT:    {len(spot_files)} archivos")
    print(f"   FUTURES: {len(futures_files)} archivos")

    if counts["pending"] < 50:
        print(f"\n⚠️ ATENCIÓN: WUs pendientes bajos ({counts['pending']})")
        print("   Ejecuta: python auto_wu_generator.py")
    else:
        print(f"\n✅ Sistema OK")

    print()

def main():
    parser = argparse.ArgumentParser(description="Auto-Generador de Work Units")
    parser.add_argument("--daemon", action="store_true", help="Correr como daemon")
    parser.add_argument("--status", action="store_true", help="Mostrar estado")
    parser.add_argument("--min", type=int, default=50, help="Mínimo WUs pendientes")
    parser.add_argument("--count", type=int, default=100, help="WUs a generar")
    parser.add_argument("--interval", type=int, default=300, help="Intervalo en segundos")

    args = parser.parse_args()

    config = {
        "min_pending": args.min,
        "wu_to_generate": args.count,
        "check_interval": args.interval,
    }

    if args.status:
        show_status()
    elif args.daemon:
        run_daemon(config)
    else:
        # Una sola ejecución
        log("="*50)
        log("🤖 AUTO-WU GENERATOR")
        log("="*50)
        check_and_generate(config)

if __name__ == "__main__":
    main()
