#!/usr/bin/env python3
"""
📥 Descargador de Datos de Futuros - Coinbase
==============================================

Descarga datos históricos de TODOS los contratos de futuros
disponibles en Coinbase para entrenar estrategias.

Uso:
    python download_futures_data.py
    python download_futures_data.py --contracts BTC,ETH,SOL
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import argparse

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_URL = "https://api.coinbase.com"
DATA_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/data_futures"

# Granos de tiempo disponibles
TIME_GRANULARITIES = ["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"]

# Contratos por activo
CONTRACTS_CONFIG = {
    "BTC": ["BIT-27FEB26-CDE", "BIT-27MAR26-CDE", "BIT-24APR26-CDE", "BIT-22MAY26-CDE", "BIP-20DEC30-CDE"],
    "ETH": ["ET-27FEB26-CDE", "ET-27MAR26-CDE", "ET-24APR26-CDE", "ETP-20DEC30-CDE"],
    "SOL": ["SOL-27FEB26-CDE", "SOL-27MAR26-CDE", "SOL-24APR26-CDE", "SLP-20DEC30-CDE", "SLR-25FEB26-CDE"],
    "XRP": ["XRP-27FEB26-CDE", "XPP-20DEC30-CDE"],
    "ADA": ["ADA-27FEB26-CDE", "ADP-20DEC30-CDE"],
    "DOGE": ["DOG-27FEB26-CDE", "DOP-20DEC30-CDE"],
    "AVAX": ["AVP-20DEC30-CDE"],
    "DOT": ["DOP-20DEC30-CDE"],
    "LINK": ["LNP-20DEC30-CDE"],
    "MATIC": ["MAP-20DEC30-CDE"],
    "GOL": ["GOL-27MAR26-CDE"],
    "NOL": ["NOL-19MAR26-CDE"],
    "NGS": ["NGS-24FEB26-CDE"],
    "CU": ["CU-25FEB26-CDE"],
    "PT": ["PT-27MAR26-CDE"],
    "MC": ["MC-19MAR26-CDE", "MC-18JUN26-CDE"],
}

# API endpoints para datos históricos
HISTORICAL_URL = "https://api.exchange.coinbase.com/products/{product_id}/candles"


class FuturesDataDownloader:
    """
    Descargador de datos de futuros.
    
    Uso:
        downloader = FuturesDataDownloader()
        downloader.download_all_contracts()
    """
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache de productos
        self.products_cache = {}
        
        print(f"\n{'='*60}")
        print("📥 DESCARGADOR DE DATOS DE FUTUROS")
        print(f"{'='*60}")
        print(f"   📁 Directorio: {self.data_dir}")
        print(f"   📊 Activos: {len(CONTRACTS_CONFIG)}")
        
        # Contar contratos
        total = sum(len(v) for v in CONTRACTS_CONFIG.values())
        print(f"   📋 Contratos: {total}")
        print(f"{'='*60}\n")
    
    def get_products_from_api(self) -> List[Dict]:
        """Obtiene lista de productos de la API."""
        try:
            url = f"{API_URL}/api/v3/brokerage/market/products"
            params = {"product_type": "FUTURE", "limit": 200}
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                
                # Guardar en cache
                for p in products:
                    self.products_cache[p["product_id"]] = p
                
                return products
            else:
                print(f"❌ Error: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"❌ Error obteniendo productos: {e}")
            return []
    
    def get_contract_size(self, product_id: str) -> float:
        """Obtiene el tamaño del contrato."""
        # Extraer prefijo
        prefix = product_id.split("-")[0]
        
        # Mapear prefijos a tamaños
        sizes = {
            "BIT": 0.01,   # Nano Bitcoin
            "BIP": 0.01,   # Perpetuo Bitcoin
            "ET": 0.10,    # Nano Ether
            "ETP": 0.10,   # Perpetuo Ether
            "SOL": 5.0,    # Nano Solana
            "SLP": 5.0,    # Perpetuo Solana
            "SLR": 5.0,    # Rolling Solana
            "XRP": 500.0,  # Nano XRP
            "XPP": 500.0,  # Perpetuo XRP
            "ADA": 100.0,  # Nano ADA
            "ADP": 100.0,  # Perpetuo ADA
            "DOG": 1000.0, # Nano DOGE
            "DOP": 1000.0, # Perpetuo DOGE
            "AVP": 1.0,    # Perpetuo AVAX
            "DOP": 1.0,    # Perpetuo DOT
            "LNP": 1.0,    # Perpetuo LINK
            "MAP": 10.0,   # Perpetuo MATIC
            "GOL": 1.0,    # Oro
            "NOL": 100.0,  # Petróleo
            "NGS": 1000.0, # Gas natural
            "CU": 100.0,   # Cobre
            "PT": 10.0,    # Platino
            "MC": 1.0,     # Micro S&P
            "BCP": 0.10,   # Bitcoin Cash Nano
            "BCH": 0.10,   # Bitcoin Cash
            "LCP": 10.0,   # Litecoin
        }
        
        return sizes.get(prefix, 1.0)
    
    def download_candles(self, product_id: str, granularity: int = 300,
                        days: int = 30) -> pd.DataFrame:
        """
        Descarga datos de velas REALES para un contrato de futuros.

        Args:
            product_id: ID del producto (ej: BIT-27FEB26-CDE)
            granularity: Segundos por vela (60=1min, 300=5min, etc)
            days: Días de historial

        Returns:
            DataFrame con datos OHLCV
        """
        # Granularity mapping
        gran_map = {
            "ONE_MINUTE": 60,
            "FIVE_MINUTE": 300,
            "FIFTEEN_MINUTE": 900,
            "ONE_HOUR": 3600,
            "ONE_DAY": 86400,
        }

        if isinstance(granularity, str):
            granularity = gran_map.get(granularity, 300)

        # Usar endpoint público de Coinbase Exchange para datos de futuros
        url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"

        end_time = int(time.time())
        start_time = int(end_time - (days * 86400))

        all_candles = []
        current_end = end_time
        request_count = 0
        max_requests = 100

        while current_end > start_time and request_count < max_requests:
            params = {
                "granularity": granularity,
                "end": str(current_end)
            }

            try:
                response = requests.get(url, params=params, timeout=30)

                if response.status_code == 404:
                    # Intentar con endpoint alternativo de CDE
                    return self._download_candles_cde(product_id, granularity, days)

                if response.status_code != 200:
                    break

                candles = response.json()

                if not candles:
                    break

                all_candles.extend(candles)
                request_count += 1

                # El timestamp más antiguo es el último (ordenados desc)
                oldest_ts = min(c[0] for c in candles)
                current_end = oldest_ts - 1

                if request_count % 5 == 0:
                    print(f"📊 {len(all_candles):,} velas...", end="\r")

                time.sleep(0.3)

            except Exception as e:
                break

        if not all_candles:
            return pd.DataFrame()

        # Formato Coinbase: [time, low, high, open, close, volume]
        df = pd.DataFrame(all_candles, columns=[
            "timestamp", "low", "high", "open", "close", "volume"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp").drop_duplicates().reset_index(drop=True)

        return df

    def _download_candles_cde(self, product_id: str, granularity: int, days: int) -> pd.DataFrame:
        """Endpoint alternativo para contratos CDE de futuros."""
        url = f"{API_URL}/api/v3/brokerage/market/products/{product_id}/candles"

        end_time = int(time.time())
        start_time = int(end_time - (days * 86400))

        all_candles = []
        current_end = end_time

        for _ in range(50):
            params = {
                "granularity": granularity,
                "end": str(current_end)
            }

            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code != 200:
                    break

                data = response.json()
                candles = data.get("candles", [])

                if not candles:
                    break

                all_candles.extend(candles)
                oldest_ts = min(int(c.get("start", c.get("timestamp", 0))) for c in candles)
                current_end = oldest_ts - granularity

                time.sleep(0.3)
            except:
                break

        if not all_candles:
            return pd.DataFrame()

        # Normalizar formato
        normalized = []
        for c in all_candles:
            normalized.append({
                "timestamp": int(c.get("start", c.get("timestamp", 0))),
                "open": float(c.get("open", 0)),
                "high": float(c.get("high", 0)),
                "low": float(c.get("low", 0)),
                "close": float(c.get("close", 0)),
                "volume": float(c.get("volume", 0))
            })

        df = pd.DataFrame(normalized)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.sort_values("timestamp").drop_duplicates().reset_index(drop=True)

        return df
    
    def generate_synthetic_data(self, product_id: str, days: int = 90, 
                               granularity: str = "ONE_MINUTE") -> pd.DataFrame:
        """
        Genera datos sintéticos basados en el precio actual.
        Útil cuando no hay datos históricos disponibles.
        
        Args:
            product_id: ID del producto
            days: Días de datos a generar
            granularity: Granularidad
            
        Returns:
            DataFrame con datos OHLCV
        """
        import numpy as np
        
        # Obtener precio base
        price = self.get_current_price(product_id)
        
        if price == 0:
            print(f"   ❌ {product_id}: Sin precio base")
            return pd.DataFrame()
        
        # Calcular número de velas
        gran_map = {
            "ONE_MINUTE": 1440,
            "FIVE_MINUTE": 288,
            "FIFTEEN_MINUTE": 96,
            "ONE_HOUR": 24,
            "ONE_DAY": 1,
        }
        
        candles_per_day = gran_map.get(granularity, 1440)
        num_candles = days * candles_per_day
        
        # Generar precios con movimiento browniano
        np.random.seed(hash(product_id) % 10000)
        
        # Volatilidad diaria típica (2-5%)
        daily_volatility = 0.03
        volatility = daily_volatility / np.sqrt(candles_per_day)
        
        # Generar retornos
        returns = np.random.normal(0.0001, volatility, num_candles)
        
        # Calcular precios
        prices = [price]
        for r in returns:
            prices.append(prices[-1] * (1 + r))
        
        prices = np.array(prices[:-1])
        
        # Generar OHLC
        high = prices * (1 + np.abs(np.random.normal(0, volatility/2, num_candles)))
        low = prices * (1 - np.abs(np.random.normal(0, volatility/2, num_candles)))
        open_prices = prices * (1 + np.random.normal(0, volatility/4, num_candles))
        
        # Asegurar OHLC válido
        high = np.maximum.reduce([open_prices, prices, high])
        low = np.minimum.reduce([open_prices, prices, low])
        
        # Generar timestamps
        end_time = int(time.time())
        if granularity == "ONE_MINUTE":
            start_time = end_time - (num_candles * 60)
            timestamps = list(range(start_time, end_time, 60))
        elif granularity == "FIVE_MINUTE":
            start_time = end_time - (num_candles * 300)
            timestamps = list(range(start_time, end_time, 300))
        elif granularity == "ONE_HOUR":
            start_time = end_time - (num_candles * 3600)
            timestamps = list(range(start_time, end_time, 3600))
        else:
            start_time = end_time - (num_candles * 86400)
            timestamps = list(range(start_time, end_time, 86400))
        
        # Volume (simulado)
        base_volume = price * 1000  # Volumen base
        volume = np.random.lognormal(np.log(base_volume), 0.5, num_candles)
        
        # Crear DataFrame
        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": open_prices,
            "high": high,
            "low": low,
            "close": prices,
            "volume": volume
        })
        
        return df
    
    def get_current_price(self, product_id: str) -> float:
        """Obtiene precio actual de un producto."""
        try:
            # Intentar con endpoint público
            url = f"{API_URL}/api/v3/brokerage/market/products"
            params = {"product_type": "FUTURE", "limit": 200}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for p in data.get("products", []):
                    if p.get("product_id") == product_id:
                        price_str = p.get("price", "0")
                        return float(price_str) if price_str else 0
            
            return 0
        except:
            return 0
    
    def download_all_contracts(self, assets: List[str] = None,
                               granularity: str = "FIVE_MINUTE",
                               days: int = 30,
                               force: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Descarga datos REALES para todos los contratos disponibles.

        Args:
            assets: Lista de activos a descargar (None = todos los disponibles en API)
            granularity: Granularidad de datos
            days: Días de historial
            force: Re-descargar aunque existan

        Returns:
            Dict con product_id -> DataFrame
        """
        # Obtener productos disponibles de la API
        print("🔍 Obteniendo contratos disponibles de API...")
        api_products = self.get_products_from_api()

        if not api_products:
            print("   ⚠️ No se pudieron obtener productos de API, usando config estática")
            if assets:
                contracts = {a: CONTRACTS_CONFIG.get(a, []) for a in assets}
            else:
                contracts = CONTRACTS_CONFIG
        else:
            # Usar productos de la API
            contracts = {}
            for p in api_products:
                pid = p.get("product_id", "")
                base = p.get("base_currency_id", pid.split("-")[0] if "-" in pid else "")
                if base not in contracts:
                    contracts[base] = []
                contracts[base].append(pid)

        # Verificar archivos existentes
        existing = set()
        for f in os.listdir(self.data_dir):
            if f.endswith('.csv'):
                contract = f.split('_')[0]
                existing.add(contract)

        results = {}
        skipped = 0
        downloaded = 0
        failed = []

        total = sum(len(v) for v in contracts.values())
        current = 0

        print(f"\n📥 DESCARGANDO DATOS REALES:")
        print(f"   Activos: {len(contracts)}")
        print(f"   Contratos totales: {total}")
        print(f"   Ya existentes: {len(existing)}")
        print(f"   Granularidad: {granularity}")
        print(f"   Días: {days}")
        print()

        for asset, product_ids in contracts.items():
            for product_id in product_ids:
                current += 1

                # Nombre de archivo
                filename = f"{product_id}_{granularity}.csv"
                filepath = self.data_dir / filename

                # Verificar si ya existe
                if product_id in existing and not force:
                    print(f"[{current}/{total}] ⏭️  {product_id}")
                    skipped += 1
                    continue

                print(f"[{current}/{total}] 🔄 {product_id}...", end=" ")

                # Descargar datos REALES
                df = self.download_candles(product_id, granularity, days)

                if not df.empty:
                    df.to_csv(filepath, index=False)
                    size_kb = filepath.stat().st_size / 1024
                    results[product_id] = df
                    print(f"✅ {len(df):,} velas ({size_kb:.1f} KB)")
                    downloaded += 1
                else:
                    print(f"❌ Sin datos")
                    failed.append(product_id)

                time.sleep(0.3)

        print(f"\n{'='*60}")
        print(f"📊 RESUMEN")
        print(f"{'='*60}")
        print(f"   ✅ Descargados: {downloaded}")
        print(f"   ⏭️  Saltados: {skipped}")
        print(f"   ❌ Fallidos: {len(failed)}")

        if failed:
            print(f"\n⚠️ Contratos sin datos: {failed[:20]}")

        return results
    
    def list_available_data(self) -> List[str]:
        """Lista archivos de datos disponibles."""
        if not self.data_dir.exists():
            return []
        
        files = list(self.data_dir.glob("*.csv"))
        return [f.name for f in files]
    
    def load_data(self, product_id: str, granularity: str = "ONE_MINUTE") -> pd.DataFrame:
        """Carga datos de un contrato."""
        filename = f"{product_id}_{granularity}.csv"
        filepath = self.data_dir / filename
        
        if filepath.exists():
            return pd.read_csv(filepath)
        
        return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Descargador de Datos de Futuros")
    parser.add_argument("--assets", type=str, help="Activos a descargar (BTC,ETH,SOL)")
    parser.add_argument("--granularity", type=str, default="FIVE_MINUTE",
                       choices=["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"],
                       help="Granularidad de datos")
    parser.add_argument("--days", type=int, default=30, help="Días de historial")
    parser.add_argument("--force", action="store_true", help="Re-descargar aunque existan")
    parser.add_argument("--list", action="store_true", help="Listar datos disponibles")
    parser.add_argument("--list-api", action="store_true", help="Listar contratos de la API")

    args = parser.parse_args()

    downloader = FuturesDataDownloader()

    if args.list:
        files = downloader.list_available_data()
        print(f"\n📁 DATOS DISPONIBLES ({len(files)} archivos):")
        for f in sorted(files)[:30]:
            print(f"   {f}")
        if len(files) > 30:
            print(f"   ... y {len(files) - 30} más")
        return

    if args.list_api:
        products = downloader.get_products_from_api()
        print(f"\n📋 CONTRATOS EN API ({len(products)}):")
        for p in products:
            pid = p.get("product_id", "")
            exp = p.get("contract_expiry_date", "PERP") or "PERP"
            lev = p.get("max_leverage", 1)
            print(f"   {pid:25} exp: {str(exp)[:12]} leverage: {lev}x")
        return

    # Descargar
    assets = args.assets.split(",") if args.assets else None

    results = downloader.download_all_contracts(
        assets=assets,
        granularity=args.granularity,
        days=args.days,
        force=args.force
    )

    # Listar archivos finales
    print(f"\n📁 Contenido de data_futures/:")
    for f in sorted(Path(DATA_DIR).glob("*.csv"))[:20]:
        size = f.stat().st_size / 1024
        print(f"   {f.name:40} {size:>8.1f} KB")


if __name__ == "__main__":
    main()
