#!/usr/bin/env python3
"""
📥 Descargador de Datos SPOT de Coinbase - Mejorado
====================================================

Descarga datos reales en chunks de 350 velas para todos los TOP activos.

Uso:
    python download_spot_data.py                    # Descarga todos los faltantes
    python download_spot_data.py --assets BTC,ETH   # Solo activos específicos
    python download_spot_data.py --force            # Re-descargar aunque existan
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
import argparse

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_URL = "https://api.exchange.coinbase.com"
DATA_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/data"

# TOP 20 activos por liquidez (BTC ya tiene datos, se incluye para completar)
ASSETS = {
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "ADA": "ADA-USD",
    "DOGE": "DOGE-USD",
    "LINK": "LINK-USD",
    "AVAX": "AVAX-USD",
    "DOT": "DOT-USD",
    "ATOM": "ATOM-USD",
    "LTC": "LTC-USD",
    "UNI": "UNI-USD",
    "NEAR": "NEAR-USD",
    "ARB": "ARB-USD",
    "OP": "OP-USD",
    "APE": "APE-USD",
    "SAND": "SAND-USD",
    "MANA": "MANA-USD",
    "AXS": "AXS-USD",
}

# Mapeo de granularidad a nombre de archivo
GRANULARITY_MAP = {
    60: "ONE_MINUTE",
    300: "FIVE_MINUTE",
    900: "FIFTEEN_MINUTE",
}


class SpotDataDownloader:
    """Descargador de datos spot."""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print("📥 DESCARGADOR DE DATOS SPOT - COINBASE")
        print(f"{'='*60}")
        print(f"   📁 Directorio: {self.data_dir}")
        print(f"{'='*60}\n")

    def download_candles(self, product_id: str, granularity: int = 300,
                       days: int = 90) -> pd.DataFrame:
        """
        Descarga velas paginando hacia atrás en el tiempo.

        La API devuelve máximo 350 velas por request.
        Para 90 días de datos 5-min: 90*24*60/5 = 25,920 velas
        """
        url = f"{API_URL}/products/{product_id}/candles"

        all_candles = []
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())

        # Calcular velas esperadas
        expected_candles = (end_time - start_time) // granularity
        print(f"   Esperando ~{expected_candles:,} velas...")

        current_end = end_time
        request_count = 0
        max_requests = 200  # Safety limit

        while current_end > start_time and request_count < max_requests:
            params = {
                "granularity": granularity,
                "end": str(current_end)
            }

            try:
                response = requests.get(url, params=params, timeout=30)

                if response.status_code == 404:
                    print(f"   ⚠️ Producto no encontrado: {product_id}")
                    break

                if response.status_code != 200:
                    print(f"   ❌ Error HTTP {response.status_code}")
                    break

                candles = response.json()

                if not candles:
                    break

                all_candles.extend(candles)
                request_count += 1

                # El timestamp más antiguo es el último (ordenados desc)
                oldest_ts = min(c[0] for c in candles)
                current_end = oldest_ts - 1

                if request_count % 10 == 0:
                    print(f"   📊 {len(all_candles):,} velas descargadas...", end="\r")

                # Rate limiting
                time.sleep(0.3)

            except Exception as e:
                print(f"   ❌ Error: {e}")
                break

        if not all_candles:
            return pd.DataFrame()

        # Convertir a DataFrame
        df = pd.DataFrame(all_candles, columns=[
            "timestamp", "low", "high", "open", "close", "volume"
        ])

        # Convertir timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

        # Ordenar y dedup
        df = df.sort_values("timestamp").drop_duplicates().reset_index(drop=True)

        return df

    def download_all(self, assets: List[str] = None, granularities: List[int] = None,
                     force: bool = False, days: int = 90) -> Dict[str, pd.DataFrame]:
        """Descarga todos los activos."""

        if assets:
            to_download = {k: v for k, v in ASSETS.items() if k in assets}
        else:
            to_download = ASSETS

        if granularities is None:
            granularities = [300, 900]  # 5min y 15min por defecto

        results = {}
        skipped = 0
        downloaded = 0
        failed = []

        total = len(to_download) * len(granularities)
        current = 0

        print(f"\n📥 DESCARGANDO DATOS:")
        print(f"   Activos: {len(to_download)}")
        print(f"   Timeframes: {[GRANULARITY_MAP[g] for g in granularities]}")
        print(f"   Período: {days} días")
        print()

        for symbol, product_id in to_download.items():
            for granularity in granularities:
                current += 1
                tf_name = GRANULARITY_MAP.get(granularity, f"{granularity}s")
                filename = f"{product_id}_{tf_name}.csv"
                filepath = self.data_dir / filename

                # Verificar si ya existe
                if filepath.exists() and not force:
                    size_kb = filepath.stat().st_size / 1024
                    print(f"[{current}/{total}] ⏭️  {filename} ({size_kb:.1f} KB)")
                    skipped += 1
                    continue

                print(f"[{current}/{total}] 🔄 {symbol} ({tf_name})...", end=" ")

                df = self.download_candles(product_id, granularity, days)

                if not df.empty:
                    # Guardar
                    df.to_csv(filepath, index=False)
                    size_kb = filepath.stat().st_size / 1024
                    results[f"{product_id}_{tf_name}"] = df
                    print(f"✅ {len(df):,} velas ({size_kb:.1f} KB)")
                    downloaded += 1
                else:
                    print(f"❌ Sin datos")
                    failed.append(f"{product_id}_{tf_name}")

                time.sleep(0.5)

        print(f"\n{'='*60}")
        print(f"📊 RESUMEN")
        print(f"{'='*60}")
        print(f"   ✅ Descargados: {downloaded}")
        print(f"   ⏭️  Saltados (ya existían): {skipped}")
        print(f"   ❌ Fallidos: {len(failed)}")

        if failed:
            print(f"\n⚠️ Fallidos: {failed}")

        return results


def main():
    parser = argparse.ArgumentParser(description="Descargar datos SPOT de Coinbase")
    parser.add_argument("--assets", type=str, help="Activos separados por coma: ETH,SOL,XRP")
    parser.add_argument("--granularity", type=str, default="5m,15m",
                       help="Timeframes: 1m,5m,15m (default: 5m,15m)")
    parser.add_argument("--days", type=int, default=90, help="Días de historial (default: 90)")
    parser.add_argument("--force", action="store_true", help="Re-descargar aunque existan")

    args = parser.parse_args()

    # Parsear assets
    assets = args.assets.split(",") if args.assets else None

    # Parsear granularidades
    gran_map = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}
    granularities = [gran_map.get(g, 300) for g in args.granularity.split(",")]

    downloader = SpotDataDownloader()
    results = downloader.download_all(assets, granularities, args.force, args.days)

    print(f"\n📁 Archivos guardados en: {DATA_DIR}")

    # Listar archivos
    print(f"\n📂 Contenido de data/:")
    for f in sorted(Path(DATA_DIR).glob("*.csv")):
        size = f.stat().st_size / 1024
        print(f"   {f.name:40} {size:>8.1f} KB")


if __name__ == "__main__":
    main()
