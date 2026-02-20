#!/usr/bin/env python3
"""
📥 SISTEMA DE DESCARGA DE DATOS COMPLETO
Descarga datos de 30+ criptomonedas en 5 timeframes desde Coinbase

Activos: Top 30 por liquidez
Timeframes: 1m, 5m, 15m, 30m, 1h
Período: 24-36 meses
Formato: CSV optimizado para workers

Autor: Ultimate Trading System
Fecha: Febrero 2026
"""

import requests
import time
import json
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os

# Configuración
PROJECT_DIR = Path("/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude")
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = PROJECT_DIR / "market_data.db"

# Top 30 criptomonedas por liquidez (aproximado)
TOP_ASSETS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "ADA-USD",
    "DOGE-USD", "MATIC-USD", "LINK-USD", "AVAX-USD", "DOT-USD",
    "ATOM-USD", "LTC-USD", "UNI-USD", "NEAR-USD", "ARB-USD",
    "OP-USD", "APE-USD", "SAND-USD", "MANA-USD", "AXS-USD",
    "EOS-USD", "XTZ-USD", "AAVE-USD", "MKR-USD", "SNX-USD",
    "COMP-USD", "YFI-USD", "CRV-USD", "BAL-USD", "SUSHI-USD"
]

# Timeframes soportados
TIMEFRAMES = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600
}

class CoinbaseDataDownloader:
    """Descargador de datos desde Coinbase Advanced Trade"""
    
    def __init__(self):
        self.base_url = "https://api.exchange.coinbase.com"
        self.session = requests.Session()
        self.session.headers.update({
            "CB-ACCESS-KEY": os.environ.get("COINBASE_API_KEY", ""),
            "CB-ACCESS-SIGN": os.environ.get("COINBASE_API_SECRET", ""),
            "CB-VERSION": "2024-01-01"
        })
        self.rate_limit = 0.5  # Segundos entre requests
    
    def get_candles(self, product_id: str, granularity: int, 
                    start: int, end: int, limit: int = 300) -> list:
        """Obtener velas desde Coinbase"""
        url = f"{self.base_url}/products/{product_id}/candles"
        params = {
            "granularity": granularity,
            "start": str(start),
            "end": str(end),
            "limit": limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Coinbase devuelve: [time, low, high, open, close, volume]
            candles = []
            for c in data:
                candles.append({
                    'timestamp': c[0],
                    'open': float(c[3]),
                    'high': float(c[2]),
                    'low': float(c[1]),
                    'close': float(c[4]),
                    'volume': float(c[5])
                })
            
            return candles
        except Exception as e:
            print(f"   ❌ Error descargando {product_id}: {e}")
            return []
    
    def download_full_history(self, product_id: str, timeframe: str,
                               start_days: int = 730) -> pd.DataFrame:
        """Descargar historial completo"""
        print(f"\n📥 Descargando {product_id} ({timeframe})...")
        
        granularity = TIMEFRAMES[timeframe]
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=start_days)).timestamp())
        
        all_candles = []
        current_start = start_time
        
        max_retries = 3
        while current_start < end_time:
            for retry in range(max_retries):
                candles = self.get_candles(
                    product_id, granularity, 
                    current_start, end_time
                )
                
                if candles:
                    all_candles.extend(candles)
                    current_start = candles[-1]['timestamp'] + granularity
                    print(f"   📊 {len(all_candles):,} velas descargadas", end="\r")
                    break
                else:
                    time.sleep(1)
            else:
                print(f"   ⚠️ Error después de {max_retries} intentos")
                break
            
            time.sleep(self.rate_limit)
        
        print(f"   ✅ {len(all_candles):,} velas totales")
        
        if all_candles:
            df = pd.DataFrame(all_candles)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.sort_values('timestamp')
            return df
        
        return pd.DataFrame()


class MarketDataManager:
    """Gestor de datos de mercado"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializar base de datos"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Tabla de productos
        c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                base_currency TEXT,
                quote_currency TEXT,
                status TEXT,
                last_updated TIMESTAMP
            )
        ''')
        
        # Tabla de velas
        c.execute('''
            CREATE TABLE IF NOT EXISTS candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                timeframe TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                UNIQUE(product_id, timeframe, timestamp)
            )
        ''')
        
        # Tabla de resumen
        c.execute('''
            CREATE TABLE IF NOT EXISTS download_status (
                product_id TEXT,
                timeframe TEXT,
                total_candles INTEGER,
                date_start INTEGER,
                date_end INTEGER,
                last_download TIMESTAMP,
                PRIMARY KEY (product_id, timeframe)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_candles(self, df: pd.DataFrame, product_id: str, timeframe: str):
        """Guardar velas en base de datos"""
        if df.empty:
            return
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for _, row in df.iterrows():
            try:
                c.execute('''
                    INSERT OR REPLACE INTO candles 
                    (product_id, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_id, timeframe, row['timestamp'],
                    row['open'], row['high'], row['low'], row['close'], row['volume']
                ))
            except:
                pass
        
        # Actualizar status
        c.execute('''
            INSERT OR REPLACE INTO download_status 
            (product_id, timeframe, total_candles, date_start, date_end, last_download)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            product_id, timeframe, len(df),
            df['timestamp'].min(), df['timestamp'].max(),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_download_status(self) -> pd.DataFrame:
        """Ver estado de descargas"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM download_status", conn)
        conn.close()
        return df
    
    def export_to_csv(self, product_id: str, timeframe: str, output_dir: Path):
        """Exportar a CSV optimizado para workers"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(f'''
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE product_id = '{product_id}' AND timeframe = '{timeframe}'
            ORDER BY timestamp
        ''', conn)
        conn.close()
        
        if df.empty:
            return None
        
        # Formatear para workers
        filename = f"{product_id.replace('-', '_')}_{timeframe.upper()}.csv"
        filepath = output_dir / filename
        
        df.to_csv(filepath, index=False)
        
        return filepath


class DataPipeline:
    """Pipeline completo de datos"""
    
    def __init__(self):
        self.downloader = CoinbaseDataDownloader()
        self.manager = MarketDataManager(str(DB_PATH))
        
    def download_all(self, assets: List[str] = TOP_ASSETS,
                     timeframes: List[str] = list(TIMEFRAMES.keys()),
                     start_days: int = 730):
        """Descargar todos los activos y timeframes"""
        
        print("\n" + "="*60)
        print("📥 INICIANDO DESCARGA DE DATOS")
        print("="*60)
        print(f"   📦 Activos: {len(assets)}")
        print(f"   ⏱️ Timeframes: {len(timeframes)}")
        print(f"   📅 Período: {start_days} días")
        print(f"   💾 Destino: {DATA_DIR}")
        
        total_files = len(assets) * len(timeframes)
        current = 0
        
        for asset in assets:
            for tf in timeframes:
                current += 1
                print(f"\n[{current}/{total_files}] {asset} ({tf})")
                
                # Descargar
                df = self.downloader.download_full_history(asset, tf, start_days)
                
                if not df.empty:
                    # Guardar en DB
                    self.manager.save_candles(df, asset, tf)
                    
                    # Exportar a CSV
                    filepath = self.manager.export_to_csv(asset, tf, DATA_DIR)
                    if filepath:
                        size_mb = filepath.stat().st_size / (1024*1024)
                        print(f"   💾 Guardado: {filepath.name} ({size_mb:.1f} MB)")
        
        print("\n" + "="*60)
        print("✅ DESCARGA COMPLETADA")
        print("="*60)
        
        # Mostrar resumen
        status = self.manager.get_download_status()
        if not status.empty:
            print(f"\n📊 RESUMEN:")
            print(f"   📦 Total archivos: {len(status)}")
            print(f"   📈 Velas totales: {status['total_candles'].sum():,}")
    
    def verify_data(self):
        """Verificar integridad de datos"""
        print("\n" + "="*60)
        print("🔍 VERIFICANDO INTEGRIDAD DE DATOS")
        print("="*60)
        
        status = self.manager.get_download_status()
        
        if status.empty:
            print("   ⚠️ No hay datos descargados")
            return False
        
        print(f"\n📊 Estado de Descargas:")
        print(f"   Total: {len(status)} archivos")
        
        for _, row in status.iterrows():
            start_date = datetime.fromtimestamp(row['date_start']).strftime('%Y-%m-%d')
            end_date = datetime.fromtimestamp(row['date_end']).strftime('%Y-%m-%d')
            print(f"   ✅ {row['product_id']} ({row['timeframe']}): "
                  f"{row['total_candles']:,} velas | {start_date} -> {end_date}")
        
        return True


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("📥 SISTEMA DE DESCARGA DE DATOS COMPLETO")
    print("   Para Ultimate Trading System")
    print("="*60)
    
    # Crear directorio de datos
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    pipeline = DataPipeline()
    
    # Verificar datos existentes
    pipeline.verify_data()
    
    # Preguntar si descargar más
    print("\n" + "="*60)
    print("¿Qué quieres hacer?")
    print("   [1] Descargar todos los activos")
    print("   [2] Descargar solo BTC, ETH, SOL")
    print("   [3] Verificar datos existentes")
    print("   [0] Salir")
    
    choice = input("\n👉 Opción: ").strip()
    
    if choice == "1":
        pipeline.download_all()
    elif choice == "2":
        pipeline.download_all(assets=["BTC-USD", "ETH-USD", "SOL-USD"])
    elif choice == "3":
        pipeline.verify_data()


if __name__ == "__main__":
    main()
