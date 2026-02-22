#!/usr/bin/env python3
"""
📥 Descargador de Datos SPOT de Coinbase - Mejorado
====================================================

Descarga datos reales en chunks de 350 velas.

Uso:
    python download_spot_data.py --assets BTC,ETH,SOL --days 30
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
DATA_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude/data_spot"

ASSETS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "ADA": "ADA-USD",
    "DOGE": "DOGE-USD",
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
                       max_requests: int = 10) -> pd.DataFrame:
        """
        Descarga velas en múltiples requests.
        
        La API devuelve máximo 350 velas por request.
        """
        url = f"{API_URL}/products/{product_id}/candles"
        
        all_candles = []
        
        # La API devuelve las velas más recientes primero
        for i in range(max_requests):
            params = {"granularity": granularity}
            
            try:
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    print(f"Error: {response.status_code}")
                    break
                
                candles = response.json()
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                print(f"   Request {i+1}: {len(candles)} velas")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error: {e}")
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
    
    def download_all(self, assets: List[str] = None, granularity: int = 300) -> Dict[str, pd.DataFrame]:
        """Descarga todos los activos."""
        
        if assets:
            to_download = {k: v for k, v in ASSETS.items() if k in assets}
        else:
            to_download = ASSETS
        
        results = {}
        
        print(f"\n📥 DESCARGANDO DATOS:")
        print(f"   Granularidad: {granularity}s")
        print(f"   Max requests: 10 x 350 velas = ~3500 velas")
        print()
        
        for symbol, product_id in to_download.items():
            print(f"🔄 {symbol} ({product_id})...", end=" ")
            
            df = self.download_candles(product_id, granularity)
            
            if not df.empty:
                # Guardar
                filename = f"{product_id}_{granularity}s.csv"
                filepath = self.data_dir / filename
                df.to_csv(filepath, index=False)
                
                results[product_id] = df
                print(f"✅ {len(df)} velas")
            else:
                print(f"❌ Sin datos")
            
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETADO: {len(results)} activos")
        
        return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=str, help="BTC,ETH,SOL")
    parser.add_argument("--granularity", type=int, default=300, choices=[60, 300, 900, 3600])
    
    args = parser.parse_args()
    
    downloader = SpotDataDownloader()
    
    assets = args.assets.split(",") if args.assets else None
    
    results = downloader.download_all(assets, args.granularity)
    
    print(f"\n📊 Archivos guardados en: {DATA_DIR}")


if __name__ == "__main__":
    main()
