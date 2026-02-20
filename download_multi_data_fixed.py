#!/usr/bin/env python3
"""
Multi-Timeframe Data Downloader
Descarga datos de 30+ activos en 5 timeframes desde Coinbase
"""

import pandas as pd
import time
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

class MultiTimeframeDownloader:
    def __init__(self):
        self.client = None  # CoinbaseClient()
        self.data_dir = Path("data_multi")
        self.data_dir.mkdir(exist_ok=True)
        
        self.timeframes = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
        }
        
        self.activos = [
            'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD',
            'DOGE-USD', 'MATIC-USD', 'LINK-USD', 'AVAX-USD', 'DOT-USD',
            'ATOM-USD', 'LTC-USD', 'UNI-USD', 'NEAR-USD', 'ARB-USD',
            'OP-USD', 'APE-USD', 'SAND-USD', 'MANA-USD', 'AXS-USD',
            'EOS-USD', 'XTZ-USD', 'AAVE-USD', 'MKR-USD', 'SNX-USD',
            'COMP-USD', 'YFI-USD', 'CRV-USD', 'BAL-USD', 'SUSHI-USD',
        ]
        
        self.db_path = Path("data_multi/download_tracker.db")
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS descargas (
                symbol TEXT,
                timeframe TEXT,
                inicio TIMESTAMP,
                fin TIMESTAMP,
                velas INTEGER,
                archivo TEXT,
                estado TEXT,
                descargado_el TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timeframe)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS resumen (
                total_activos INTEGER,
                total_timeframes INTEGER,
                total_archivos INTEGER,
                ultima_actualizacion TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def obtener_timestamp_inicio(self, dias=730):
        now = datetime.now()
        inicio = now - timedelta(days=dias)
        return int(inicio.timestamp())
    
    def descargar_activo_timeframe(self, symbol, timeframe, granularity):
        start_ts = self.obtener_timestamp_inicio(730)
        end_ts = int(datetime.now().timestamp())
        
        all_candles = []
        current_ts = start_ts
        
        print(f"   Descargando {symbol} ({timeframe})...")
        
        while current_ts < end_ts:
            try:
                candles = self.client.get_historical_data(
                    symbol=symbol,
                    granularity=granularity,
                    start_ts=current_ts,
                    end_ts=end_ts
                )
                
                if candles is None or len(candles) == 0:
                    break
                
                all_candles.extend(candles)
                current_ts = candles[-1]['start'] + granularity
                time.sleep(0.5)
                print(f"      {symbol}-{timeframe}: {len(all_candles)} velas...")
                
            except Exception as e:
                print(f"      Error: {e}")
                time.sleep(2)
                continue
        
        if all_candles:
            df = pd.DataFrame(all_candles)
            df['timestamp'] = pd.to_datetime(df['start'], unit='s')
            df = df.sort_values('timestamp').reset_index(drop=True)
            return df
        return None
    
    def descargar_todo(self):
        print("\n" + "="*60)
        print("MULTI-TIMEFRAME DATA DOWNLOADER")
        print("="*60)
        print(f"Activos: {len(self.activos)}")
        print(f"Timeframes: {list(self.timeframes.keys())}")
        print("="*60 + "\n")
        
        resultados = []
        total = len(self.activos) * len(self.timeframes)
        contador = 0
        
        for symbol in self.activos:
            for tf_name, granularity in self.timeframes.items():
                contador += 1
                progreso = contador / total * 100
                print(f"[{progreso:.1f}%] {contador}/{total}: {symbol} ({tf_name})")
                
                conn = sqlite3.connect(str(self.db_path))
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM descargas WHERE symbol = ? AND timeframe = ?",
                    (symbol, tf_name)
                )
                existe = c.fetchone()
                conn.close()
                
                if existe:
                    print(f"      Ya existe, saltando...")
                    continue
                
                df = self.descargar_activo_timeframe(symbol, tf_name, granularity)
                
                if df is not None and len(df) > 1000:
                    filename = f"{symbol}_{tf_name}.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=False)
                    
                    conn = sqlite3.connect(str(self.db_path))
                    c = conn.cursor()
                    c.execute(
                        "INSERT OR REPLACE INTO descargas VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            symbol, tf_name,
                            str(df['timestamp'].min()),
                            str(df['timestamp'].max()),
                            len(df),
                            str(filepath),
                            'completado'
                        )
                    )
                    conn.commit()
                    conn.close()
                    
                    print(f"      Guardado: {len(df):,} velas\n")
                    resultados.append((symbol, tf_name, len(df)))
                else:
                    print(f"      Datos insuficientes\n")
        
        print("="*60)
        print(f"Completados: {len(resultados)} archivos")
        print("="*60)
        return resultados

if __name__ == '__main__':
    try:
        from coinbase_client import CoinbaseClient
        MultiTimeframeDownloader.client = CoinbaseClient()
    except:
        pass
    
    downloader = MultiTimeframeDownloader()
    downloader.descargar_todo()
