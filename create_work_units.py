#!/usr/bin/env python3
"""
📋 Creador de Work Units para Strategy Miner
=============================================

Genera work units en coordinator.db para todos los activos SPOT y FUTURES
que tienen datos disponibles.

Uso:
    python create_work_units.py --spot              # Work units para SPOT
    python create_work_units.py --futures           # Work units para FUTURES
    python create_work_units.py --all               # Ambos
    python create_work_units.py --status            # Ver estado actual
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Configuración
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DATA_DIR = PROJECT_DIR / "data"
DATA_FUTURES_DIR = PROJECT_DIR / "data_futures"
DB_PATH = PROJECT_DIR / "coordinator.db"

# Configuración de work units por defecto
DEFAULT_SPOT_CONFIG = {
    "population_size": 100,
    "generations": 150,
    "risk_levels": ["LOW", "MEDIUM", "HIGH"],
    "max_candles": [5000, 10000, 20000],
    "replicas": 2
}

DEFAULT_FUTURES_CONFIG = {
    "population_size": 150,
    "generations": 200,
    "risk_levels": ["LOW", "MEDIUM"],
    "max_candles": [5000, 10000],
    "replicas": 2,
    "leverage_options": [1, 2, 3]
}


class WorkUnitCreator:
    """Creador de work units para el sistema de mining."""

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or DB_PATH)
        if not self.db_path.exists():
            print(f"❌ Base de datos no encontrada: {self.db_path}")
            sys.exit(1)

    def get_db_connection(self):
        """Obtener conexión a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_available_spot_data(self) -> List[Dict]:
        """Obtener lista de archivos SPOT disponibles."""
        files = []
        if not DATA_DIR.exists():
            return files

        for f in DATA_DIR.glob("*.csv"):
            if f.is_file() and not f.is_symlink():
                # Parsear nombre: BTC-USD_FIVE_MINUTE.csv
                parts = f.stem.split("_")
                if len(parts) >= 2:
                    symbol = parts[0]
                    timeframe = "_".join(parts[1:])
                    size = f.stat().st_size / 1024  # KB

                    files.append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "filename": f.name,
                        "size_kb": size,
                        "path": str(DATA_DIR)
                    })

        return sorted(files, key=lambda x: x["filename"])

    def get_available_futures_data(self) -> List[Dict]:
        """Obtener lista de archivos FUTURES disponibles."""
        files = []
        if not DATA_FUTURES_DIR.exists():
            return files

        for f in DATA_FUTURES_DIR.glob("*.csv"):
            if f.is_file():
                # Parsear nombre: BIT-27FEB26-CDE_FIVE_MINUTE.csv
                parts = f.stem.split("_")
                if len(parts) >= 2:
                    contract = parts[0]
                    timeframe = "_".join(parts[1:])
                    size = f.stat().st_size / 1024

                    # Determinar tipo de contrato
                    contract_type = "dated" if any(c.isdigit() for c in contract.split("-")[1] if len(contract.split("-")) > 1) else "perpetual"
                    if "-P-" in contract or contract.endswith("-PERP"):
                        contract_type = "perpetual"

                    # Determinar leverage máximo
                    base = contract.split("-")[0]
                    leverage_map = {
                        "BIP": 10, "ETP": 10, "SLP": 5, "XPP": 5, "ADP": 5,
                        "DOP": 5, "LNP": 5, "AVP": 5, "BIT": 10, "ET": 10,
                        "SOL": 10, "XRP": 5, "ADA": 5, "DOG": 5, "GOL": 3
                    }
                    max_leverage = leverage_map.get(base, 3)

                    files.append({
                        "contract": contract,
                        "timeframe": timeframe,
                        "filename": f.name,
                        "size_kb": size,
                        "path": str(DATA_FUTURES_DIR),
                        "contract_type": contract_type,
                        "max_leverage": max_leverage
                    })

        return sorted(files, key=lambda x: x["filename"])

    def get_existing_work_units(self) -> Dict[str, int]:
        """Obtener work units existentes agrupados por data_file."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT json_extract(strategy_params, '$.data_file') as data_file, COUNT(*) as count
            FROM work_units
            GROUP BY data_file
        """)

        result = {row["data_file"]: row["count"] for row in cursor.fetchall()}
        conn.close()
        return result

    def create_spot_work_units(self, config: Dict = None) -> int:
        """Crear work units para activos SPOT."""
        config = config or DEFAULT_SPOT_CONFIG
        data_files = self.get_available_spot_data()
        existing = self.get_existing_work_units()

        conn = self.get_db_connection()
        cursor = conn.cursor()

        created = 0
        timestamp = int(datetime.now().timestamp())

        for df in data_files:
            # Saltar archivos muy pequeños (< 100KB probablemente vacíos)
            if df["size_kb"] < 10:
                continue

            for risk in config["risk_levels"]:
                for max_candles in config["max_candles"]:
                    # Nombre del work unit
                    wu_name = f"{df['symbol']}_Spo_enhanced_{risk}_{max_candles//1000}K_{timestamp}"

                    # Verificar si ya existe
                    if df["filename"] in existing:
                        continue

                    strategy_params = {
                        "name": wu_name,
                        "category": "Spot",
                        "population_size": config["population_size"],
                        "generations": config["generations"],
                        "risk_level": risk,
                        "data_file": df["filename"],
                        "max_candles": max_candles,
                        "data_dir": df["path"],
                        "market_type": "SPOT"
                    }

                    try:
                        cursor.execute("""
                            INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_assigned, replicas_completed, created_at)
                            VALUES (?, 'pending', ?, 0, 0, ?)
                        """, (json.dumps(strategy_params), config["replicas"], timestamp))

                        created += 1
                    except Exception as e:
                        print(f"   ⚠️ Error creando {wu_name}: {e}")

        conn.commit()
        conn.close()
        return created

    def create_futures_work_units(self, config: Dict = None) -> int:
        """Crear work units para contratos FUTURES."""
        config = config or DEFAULT_FUTURES_CONFIG
        data_files = self.get_available_futures_data()
        existing = self.get_existing_work_units()

        conn = self.get_db_connection()
        cursor = conn.cursor()

        created = 0
        timestamp = int(datetime.now().timestamp())

        for df in data_files:
            # Saltar archivos muy pequeños
            if df["size_kb"] < 10:
                continue

            for risk in config["risk_levels"]:
                for max_candles in config["max_candles"]:
                    for leverage in config["leverage_options"]:
                        if leverage > df["max_leverage"]:
                            continue

                        # Nombre del work unit
                        base = df["contract"].split("-")[0]
                        wu_name = f"{base}_Fut_intensive_{risk}_{max_candles//1000}K_L{leverage}_{timestamp}"

                        # Verificar si ya existe
                        if df["filename"] in existing:
                            continue

                        strategy_params = {
                            "name": wu_name,
                            "category": "Futures",
                            "population_size": config["population_size"],
                            "generations": config["generations"],
                            "risk_level": risk,
                            "data_file": df["filename"],
                            "max_candles": max_candles,
                            "data_dir": df["path"],
                            "contract": df["contract"],
                            "contract_type": df["contract_type"],
                            "is_perpetual": df["contract_type"] == "perpetual",
                            "max_leverage": df["max_leverage"],
                            "market_type": "FUTURES",
                            "contracts": [df["contract"]],
                            "leverage": leverage
                        }

                        try:
                            cursor.execute("""
                                INSERT INTO work_units (strategy_params, status, replicas_needed, replicas_assigned, replicas_completed, created_at)
                                VALUES (?, 'pending', ?, 0, 0, ?)
                            """, (json.dumps(strategy_params), config["replicas"], timestamp))

                            created += 1
                        except Exception as e:
                            print(f"   ⚠️ Error creando {wu_name}: {e}")

        conn.commit()
        conn.close()
        return created

    def show_status(self):
        """Mostrar estado actual del sistema."""
        spot_files = self.get_available_spot_data()
        futures_files = self.get_available_futures_data()
        existing_wus = self.get_existing_work_units()

        print("\n" + "="*60)
        print("📊 ESTADO DEL SISTEMA")
        print("="*60)

        print(f"\n📁 DATOS SPOT ({len(spot_files)} archivos):")
        for f in spot_files[:15]:
            has_wu = "✅" if f["filename"] in existing_wus else "⬜"
            print(f"   {has_wu} {f['filename']:40} {f['size_kb']:>8.1f} KB")
        if len(spot_files) > 15:
            print(f"   ... y {len(spot_files) - 15} más")

        print(f"\n📁 DATOS FUTURES ({len(futures_files)} archivos):")
        for f in futures_files[:15]:
            has_wu = "✅" if f["filename"] in existing_wus else "⬜"
            print(f"   {has_wu} {f['filename']:40} {f['size_kb']:>8.1f} KB")
        if len(futures_files) > 15:
            print(f"   ... y {len(futures_files) - 15} más")

        # Contar WUs en DB
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM work_units GROUP BY status")
        status_counts = {row["status"]: row[1] for row in cursor.fetchall()}
        conn.close()

        print(f"\n📋 WORK UNITS EN DB:")
        for status, count in sorted(status_counts.items()):
            print(f"   {status}: {count:,}")

        print(f"\n📊 Total data files: {len(spot_files) + len(futures_files)}")
        print(f"📊 Files with WUs: {len([f for f in existing_wus if f])}")


def main():
    parser = argparse.ArgumentParser(description="Crear Work Units para Strategy Miner")
    parser.add_argument("--spot", action="store_true", help="Crear WUs para SPOT")
    parser.add_argument("--futures", action="store_true", help="Crear WUs para FUTURES")
    parser.add_argument("--all", action="store_true", help="Crear WUs para ambos")
    parser.add_argument("--status", action="store_true", help="Mostrar estado actual")
    parser.add_argument("--replicas", type=int, default=2, help="Réplicas por WU")

    args = parser.parse_args()

    creator = WorkUnitCreator()

    if args.status or (not args.spot and not args.futures and not args.all):
        creator.show_status()
        return

    if args.all:
        args.spot = True
        args.futures = True

    total_created = 0

    if args.spot:
        print("\n📥 Creando Work Units SPOT...")
        created = creator.create_spot_work_units({"replicas": args.replicas, **DEFAULT_SPOT_CONFIG})
        print(f"   ✅ {created} WUs creados para SPOT")
        total_created += created

    if args.futures:
        print("\n📥 Creando Work Units FUTURES...")
        created = creator.create_futures_work_units({"replicas": args.replicas, **DEFAULT_FUTURES_CONFIG})
        print(f"   ✅ {created} WUs creados para FUTURES")
        total_created += created

    print(f"\n{'='*60}")
    print(f"✅ TOTAL: {total_created} Work Units creados")
    print(f"{'='*60}")

    # Mostrar estado actualizado
    creator.show_status()


if __name__ == "__main__":
    main()
