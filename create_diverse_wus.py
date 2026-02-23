#!/usr/bin/env python3
"""
🎯 Creador de Work Units Diversificados
=======================================

Crea Work Units con máxima diversidad para explorar el espacio de búsqueda:
- Múltiples criptomonedas (BTC, ETH, SOL, XRP, etc.)
- Diferentes contratos de futuros
- Varias configuraciones de algoritmo genético
- Diferentes timeframes

Uso:
    python create_diverse_wus.py --preview  # Ver qué se crearía
    python create_diverse_wus.py --create   # Crear los WUs
    python create_diverse_wus.py --create --batch 50  # Crear 50 WUs
"""

import os
import sys
import json
import time
import sqlite3
import requests
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Configuración
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DB_PATH = PROJECT_DIR / "coordinator.db"
DATA_DIR = PROJECT_DIR / "data"
DATA_FUTURES_DIR = PROJECT_DIR / "data_futures"
COORDINATOR_URL = "http://localhost:5001"

# ============================================================
# CONFIGURACIÓN DE DIVERSIDAD
# ============================================================

# Datos SPOT disponibles
SPOT_DATA = [
    {"file": "BTC-USD_ONE_MINUTE.csv", "asset": "BTC", "timeframe": "1m", "candles": 100000},
    {"file": "BTC-USD_FIVE_MINUTE.csv", "asset": "BTC", "timeframe": "5m", "candles": 200000},
    {"file": "BTC-USD_FIFTEEN_MINUTE.csv", "asset": "BTC", "timeframe": "15m", "candles": 50000},
]

# Datos de FUTUROS disponibles - DATOS REALES (FIVE_MINUTE)
# 34 contratos de 22 activos diferentes
FUTURES_DATA = [
    # === CRYPTO PRINCIPALES ===
    # Bitcoin
    {"file": "BIP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "BTC", "contract": "BIP-20DEC30-CDE", "expiry": "PERP", "candles": 8500},
    {"file": "BIT-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "BTC", "contract": "BIT-27FEB26-CDE", "expiry": "2026-02-27", "candles": 7000},

    # Ethereum
    {"file": "ETP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "ETH", "contract": "ETP-20DEC30-CDE", "expiry": "PERP", "candles": 8400},
    {"file": "ET-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "ETH", "contract": "ET-27FEB26-CDE", "expiry": "2026-02-27", "candles": 6600},

    # Solana
    {"file": "SLP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "SOL", "contract": "SLP-20DEC30-CDE", "expiry": "PERP", "candles": 8000},
    {"file": "SOL-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "SOL", "contract": "SOL-27FEB26-CDE", "expiry": "2026-02-27", "candles": 5600},

    # XRP
    {"file": "XPP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "XRP", "contract": "XPP-20DEC30-CDE", "expiry": "PERP", "candles": 8100},
    {"file": "XRP-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "XRP", "contract": "XRP-27FEB26-CDE", "expiry": "2026-02-27", "candles": 5800},

    # === ALTCOINS ===
    # ADA
    {"file": "ADP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "ADA", "contract": "ADP-20DEC30-CDE", "expiry": "PERP", "candles": 5000},

    # DOT
    {"file": "DOP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "DOT", "contract": "DOP-20DEC30-CDE", "expiry": "PERP", "candles": 4100},

    # LINK
    {"file": "LNP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "LINK", "contract": "LNP-20DEC30-CDE", "expiry": "PERP", "candles": 4800},

    # AVAX
    {"file": "AVP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "AVAX", "contract": "AVP-20DEC30-CDE", "expiry": "PERP", "candles": 4000},

    # DOGE
    {"file": "DOG-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "DOGE", "contract": "DOG-27FEB26-CDE", "expiry": "2026-02-27", "candles": 3000},

    # SUI
    {"file": "SUI-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "SUI", "contract": "SUI-27FEB26-CDE", "expiry": "2026-02-27", "candles": 1400},

    # XLM
    {"file": "XLP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "XLM", "contract": "XLP-20DEC30-CDE", "expiry": "PERP", "candles": 2000},

    # HED (Hedera)
    {"file": "HEP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "HED", "contract": "HEP-20DEC30-CDE", "expiry": "PERP", "candles": 3800},

    # SHIB
    {"file": "SHB-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "SHIB", "contract": "SHB-27FEB26-CDE", "expiry": "2026-02-27", "candles": 3000},

    # LTC
    {"file": "LCP-20DEC30-CDE_FIVE_MINUTE.csv", "asset": "LTC", "contract": "LCP-20DEC30-CDE", "expiry": "PERP", "candles": 3800},

    # BCH
    {"file": "BCH-27FEB26-CDE_FIVE_MINUTE.csv", "asset": "BCH", "contract": "BCH-27FEB26-CDE", "expiry": "2026-02-27", "candles": 1600},

    # === COMMODITIES ===
    # Oro
    {"file": "GOL-27MAR26-CDE_FIVE_MINUTE.csv", "asset": "GOLD", "contract": "GOL-27MAR26-CDE", "expiry": "2026-03-27", "candles": 4900},

    # Petróleo
    {"file": "NOL-19MAR26-CDE_FIVE_MINUTE.csv", "asset": "OIL", "contract": "NOL-19MAR26-CDE", "expiry": "2026-03-19", "candles": 550},

    # Gas Natural
    {"file": "NGS-24FEB26-CDE_FIVE_MINUTE.csv", "asset": "NATGAS", "contract": "NGS-24FEB26-CDE", "expiry": "2026-02-24", "candles": 2000},

    # Cobre
    {"file": "CU-25FEB26-CDE_FIVE_MINUTE.csv", "asset": "COPPER", "contract": "CU-25FEB26-CDE", "expiry": "2026-02-25", "candles": 2400},

    # Platino
    {"file": "PT-27MAR26-CDE_FIVE_MINUTE.csv", "asset": "PLATINUM", "contract": "PT-27MAR26-CDE", "expiry": "2026-03-27", "candles": 2400},

    # === ÍNDICES ===
    # S&P 500
    {"file": "MC-19MAR26-CDE_FIVE_MINUTE.csv", "asset": "SP500", "contract": "MC-19MAR26-CDE", "expiry": "2026-03-19", "candles": 1700},
]

# Configuraciones de algoritmo genético (diversas)
GENETIC_CONFIGS = [
    # Configuración estándar
    {"population_size": 30, "generations": 80, "name": "standard"},

    # Exploración rápida
    {"population_size": 20, "generations": 50, "name": "fast"},

    # Exploración profunda
    {"population_size": 50, "generations": 100, "name": "deep"},

    # Alta presión selectiva
    {"population_size": 100, "generations": 80, "name": "high_pressure"},

    # Búsqueda extensa
    {"population_size": 40, "generations": 150, "name": "extensive"},
]

# Niveles de riesgo
RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]

# Configuración de max_candles
CANDLE_CONFIGS = [30000, 50000, 80000, 100000]


def get_available_data() -> Dict[str, List[Path]]:
    """Obtiene lista de archivos de datos disponibles."""
    data_files = {"spot": [], "futures": []}

    # Spot data
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.csv"):
            if "ONE_MINUTE" in f.name or "FIVE_MINUTE" in f.name or "FIFTEEN_MINUTE" in f.name:
                data_files["spot"].append(f)

    # Futures data
    if DATA_FUTURES_DIR.exists():
        for f in DATA_FUTURES_DIR.glob("*.csv"):
            data_files["futures"].append(f)

    return data_files


def verify_data_files() -> Dict[str, bool]:
    """Verifica qué archivos de datos existen."""
    status = {}

    for data in SPOT_DATA:
        path = DATA_DIR / data["file"]
        status[data["file"]] = path.exists()

    for data in FUTURES_DATA:
        path = DATA_FUTURES_DIR / data["file"]
        status[data["file"]] = path.exists()

    return status


def generate_work_units(batch_size: int = 30) -> List[Dict]:
    """Genera una lista diversa de work units."""

    work_units = []
    wu_id = 0

    # 1. Work Units con datos SPOT
    for spot in SPOT_DATA:
        for config in GENETIC_CONFIGS:
            for risk in RISK_LEVELS:
                for candles in CANDLE_CONFIGS[:3]:  # Solo 3 variantes de candles
                    if candles > spot["candles"]:
                        continue

                    wu_id += 1
                    wu = {
                        "strategy_params": {
                            "name": f"{spot['asset']}_SPOT_{config['name']}_{risk}_{candles//1000}K",
                            "category": "Spot",
                            "population_size": config["population_size"],
                            "generations": config["generations"],
                            "risk_level": risk,
                            "data_file": spot["file"],
                            "max_candles": candles,
                            "data_dir": str(DATA_DIR),
                        },
                        "replicas": 6,
                    }
                    work_units.append(wu)

    # 2. Work Units con datos de FUTUROS (DATOS REALES FIVE_MINUTE)
    for futures in FUTURES_DATA:
        for config in GENETIC_CONFIGS[:3]:  # Solo 3 configs para futuros
            for risk in ["MEDIUM", "HIGH"]:  # Futuros = más riesgo
                # Usar candles disponibles según el archivo
                max_available = futures.get("candles", 5000)
                for candles in [min(3000, max_available), min(5000, max_available)]:
                    if candles > max_available:
                        continue
                    wu_id += 1
                    wu = {
                        "strategy_params": {
                            "name": f"{futures['asset']}_FUT_{futures['contract']}_{config['name']}_{risk}_{candles//1000}K",
                            "category": "Futures",
                            "population_size": config["population_size"],
                            "generations": config["generations"],
                            "risk_level": risk,
                            "data_file": futures["file"],
                            "max_candles": candles,
                            "data_dir": str(DATA_FUTURES_DIR),
                            "contracts": [futures["contract"]],
                            "leverage": 2 if risk == "MEDIUM" else 3,
                        },
                        "replicas": 6,
                    }
                    work_units.append(wu)

    # Limitar al batch size
    if batch_size and len(work_units) > batch_size:
        # Mezclar para diversidad
        import random
        random.seed(42)
        random.shuffle(work_units)
        work_units = work_units[:batch_size]

    return work_units


def create_work_unit_db(wu: Dict) -> bool:
    """Crea un work unit directamente en la base de datos."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()

        # Insertar work unit
        c.execute("""
            INSERT INTO work_units (strategy_params, replicas_needed, replicas_assigned, status)
            VALUES (?, ?, 0, 'pending')
        """, (json.dumps(wu["strategy_params"]), wu.get("replicas", 2)))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Error DB: {e}")
        return False


def create_work_unit(wu: Dict) -> bool:
    """Crea un work unit via API o DB directa."""
    # Intentar primero con DB directa (más confiable)
    return create_work_unit_db(wu)


def preview_work_units(batch_size: int = 30):
    """Muestra preview de los work units que se crearían."""
    work_units = generate_work_units(batch_size)

    print(f"\n{'='*70}")
    print(f"📋 PREVIEW: {len(work_units)} Work Units Diversificados")
    print(f"{'='*70}\n")

    # Agrupar por tipo
    by_category = {"Spot": [], "Futures": []}
    by_asset = {}

    for wu in work_units:
        params = wu["strategy_params"]
        cat = params.get("category", "Spot")
        asset = params.get("name", "").split("_")[0]

        by_category[cat].append(wu)

        if asset not in by_asset:
            by_asset[asset] = []
        by_asset[asset].append(wu)

    # Mostrar resumen
    print("📊 RESUMEN POR CATEGORÍA:")
    print(f"   • Spot: {len(by_category['Spot'])} WUs")
    print(f"   • Futures: {len(by_category['Futures'])} WUs")

    print("\n📊 RESUMEN POR ACTIVO:")
    for asset, wus in sorted(by_asset.items()):
        print(f"   • {asset}: {len(wus)} WUs")

    print("\n📊 PRIMEROS 15 WORK UNITS:")
    print("-" * 70)

    for i, wu in enumerate(work_units[:15]):
        params = wu["strategy_params"]
        print(f"{i+1:2}. {params['name']}")
        print(f"    pop={params['population_size']}, gen={params['generations']}, risk={params['risk_level']}, candles={params['max_candles']}")

    if len(work_units) > 15:
        print(f"\n   ... y {len(work_units) - 15} más")

    # Verificar datos disponibles
    print(f"\n{'='*70}")
    print("📁 VERIFICACIÓN DE DATOS:")
    print("-" * 70)

    status = verify_data_files()
    missing = [f for f, exists in status.items() if not exists]

    if missing:
        print(f"⚠️  Archivos faltantes ({len(missing)}):")
        for f in missing[:10]:
            print(f"   ❌ {f}")
        if len(missing) > 10:
            print(f"   ... y {len(missing) - 10} más")
    else:
        print("✅ Todos los archivos de datos están disponibles")


def create_all_work_units(batch_size: int = 30, dry_run: bool = False):
    """Crea todos los work units diversificados."""

    work_units = generate_work_units(batch_size)

    print(f"\n{'='*70}")
    print(f"🚀 CREANDO {len(work_units)} WORK UNITS DIVERSIFICADOS")
    print(f"{'='*70}\n")

    if dry_run:
        print("🧪 DRY RUN - No se crearán WUs reales\n")

    success = 0
    failed = 0

    for i, wu in enumerate(work_units):
        params = wu["strategy_params"]
        name = params["name"]

        if dry_run:
            print(f"[{i+1}/{len(work_units)}] ✅ {name}")
            success += 1
            continue

        # Crear WU real
        if create_work_unit(wu):
            print(f"[{i+1}/{len(work_units)}] ✅ {name}")
            success += 1
        else:
            print(f"[{i+1}/{len(work_units)}] ❌ {name}")
            failed += 1

        # Rate limiting
        time.sleep(0.1)

    print(f"\n{'='*70}")
    print(f"{'DRY RUN' if dry_run else 'RESULTADO'}: {success} ✅ | {failed} ❌")
    print(f"{'='*70}\n")


def download_missing_data():
    """Descarga datos faltantes para futuros."""

    print(f"\n{'='*70}")
    print("📥 DESCARGANDO DATOS FALTANTES")
    print(f"{'='*70}\n")

    # Verificar qué falta
    status = verify_data_files()
    missing = [f for f, exists in status.items() if not exists and "FUTURES" not in f]

    if not missing:
        print("✅ No faltan datos")
        return

    print(f"⚠️  {len(missing)} archivos faltantes - usa download_futures_data.py")


def show_current_status():
    """Muestra el estado actual del sistema."""
    try:
        response = requests.get(f"{COORDINATOR_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            wu = data.get("work_units", {})
            print(f"\n📊 ESTADO ACTUAL:")
            print(f"   • Total WUs: {wu.get('total', 0)}")
            print(f"   • Completados: {wu.get('completed', 0)}")
            print(f"   • En progreso: {wu.get('in_progress', 0)}")
            print(f"   • Pendientes: {wu.get('pending', 0)}")

            best = data.get("best_strategy", {})
            if best:
                print(f"\n🏆 MEJOR ESTRATEGIA:")
                print(f"   • PnL: ${best.get('pnl', 0):.2f}")
                print(f"   • Win Rate: {best.get('win_rate', 0)*100:.1f}%")
                print(f"   • Trades: {best.get('trades', 0)}")
        else:
            print("⚠️  Coordinator no responde")
    except:
        print("⚠️  No se puede conectar al coordinator")


def main():
    parser = argparse.ArgumentParser(description="Creador de Work Units Diversificados")
    parser.add_argument("--preview", action="store_true", help="Ver preview sin crear")
    parser.add_argument("--create", action="store_true", help="Crear los WUs")
    parser.add_argument("--dry-run", action="store_true", help="Simular creación sin API")
    parser.add_argument("--batch", type=int, default=50, help="Número de WUs a crear")
    parser.add_argument("--status", action="store_true", help="Ver estado actual")
    parser.add_argument("--download", action="store_true", help="Descargar datos faltantes")

    args = parser.parse_args()

    print("\n🎯 WORK UNIT DIVERSITY GENERATOR")
    print("=" * 40)

    if args.status:
        show_current_status()
        return

    if args.preview:
        preview_work_units(args.batch)
        return

    if args.download:
        download_missing_data()
        return

    if args.create:
        create_all_work_units(args.batch, args.dry_run)
        return

    # Default: mostrar ayuda
    parser.print_help()


if __name__ == "__main__":
    main()
