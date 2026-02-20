#!/usr/bin/env python3
"""
📥 MULTI-TIMEFRAME DATA DOWNLOADER
Descarga datos de 30+ activos en 5 timeframes desde Coinbase

Timeframes: 1m, 5m, 15m, 30m, 1h
Activos: Top 30 por liquidez
Historial: 24 meses mínimo

Uso: python3 download_multi_data.py
"""

import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

# Importar cliente de Coinbase
from coinbase_client import CoinbaseClient

class MultiTimeframeDownloader:
    """
    Descarga datos de múltiples activos y timeframes.
    """
    
    def __init__(self):
        self.client = CoinbaseClient()
        self.data_dir = Path("data_multi")
        self.data_dir.mkdir(exist_ok=True)
        
        # Configuración de timeframes
        self.timeframes = {
            '1m': 60,           # 1 minuto
            '5m': 300,          # 5 minutos
            '15m': 900,         # 15 minutos
            '30m': 1800,        # 30 minutos
            '1h': 3600,         # 1 hora
        }
        
        # Top 30 activos por liquidez (aproximado)
        self.activos = [
            'BTC-USD',   # Bitcoin
            'ETH-USD',   # Ethereum
            'SOL-USD',   # Solana
            'XRP-USD',   # Ripple
            'ADA-USD',   # Cardano
            'DOGE-USD',  # Dogecoin
            'MATIC-USD', # Polygon
            'LINK-USD',  # Chainlink
            'AVAX-USD',  # Avalanche
            'DOT-USD',   # Polkadot
            'ATOM-USD',  # Cosmos
            'LTC-USD',   # Litecoin
            'UNI-USD',   # Uniswap
            'NEAR-USD',  # NEAR Protocol
            'ARB-USD',   # Arbitrum
            'OP-USD',    # Optimism
            'APE-USD',   # ApeCoin
            'SAND-USD',  # The Sandbox
            'MANA-USD',  # Decentraland
            'AXS-USD',   # Axie Infinity
            'EOS-USD',   # EOS
            'XTZ-USD',   # Tezos
            'AAVE-USD',  # Aave
            'MKR-USD',   # Maker
            'SNX-USD',   # Synthetix
            'COMP-USD',  # Compound
            'YFI-USD',   # Yearn Finance
            'CRV-USD',   # Curve DAO
            'BAL-USD',   # Balancer
            'SUSHI-USD',  # SushiSwap
        ]
        
        # Base de datos de seguimiento
        self.db_path = Path("data_multi/download_tracker.db")
        self._init_db()
        
    def _init_db(self):
        """Inicializar BD de seguimiento."""
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
        """Calcular timestamp de inicio (730 días = 24 meses)."""
        return int((datetime.now() - timedelta(days=dias)).timestamp()
    
    def descargar_activo_timeframe(self, symbol, timeframe, granularity):
        """
        Descargar datos de un activo específico.
        
        Args:
            symbol: Par de trading (ej: 'BTC-USD')
            timeframe: Timeframe en segundos (60, 300, 900, 1800, 3600)
            dias: Días hacia atrás
        """
        start = self.obtener_timestamp_inicio(730)  # 24 meses
        
        all_candles = []
        end = int(datetime.now().timestamp())
        start_ts = start
        
        print(f"   📥 {symbol} ({timeframe})...")
        
        while start_ts < end:
            try:
                # Coinbase tiene límite de 300 velas por llamada
                candles = self.client.get_historical_data(
                    symbol=symbol,
                    granularity=granularity,
                    start_ts=start_ts,
                    end_ts=end
                )
                
                if candles is None or len(candles) == 0:
                    break
                
                all_candles.extend(candles)
                
                # Actualizar timestamp para siguiente lote
                start_ts = candles[-1]['start'] + granularity
                
                # Respetar rate limiting
                time.sleep(0.5)
                
                # Mostrar progreso
                print(f"      {symbol}-{timeframe}: {len(all_candles)} velas...")
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                time.sleep(2)
                continue
        
        if all_candles:
            # Crear DataFrame
            df = pd.DataFrame(all_candles)
            df['timestamp'] = pd.to_datetime(df['start'], unit='s')
            df = df.sort_values('timestamp')
            df = df.reset_index(drop=True)
            
            return df
        else:
            return None
    
    def descargar_todo(self):
        """
        Descargar datos de todos los activos y timeframes.
        """
        total = len(self.activos) * len(self.timeframes)
        contador = 0
        
        print("\n" + "="*60)
        print("📥 DESCARGA DE DATOS MULTI-TIMEFRAME")
        print("="*60)
        print(f"💰 Capital: $500")
        print(f"🎯 Timeframes: {list(self.timeframes.keys())}")
        print(f"🪙 Activos: {len(self.activos)}")
        print(f"📊 Total archivos: {total}")
        print("="*60 + "\n")
        
        # Verificar conexión
        try:
            self.client.authenticate()
            print("✅ Coinbase API conectada\n")
        except Exception as e:
            print(f"❌ Error conectando a Coinbase: {e}")
            return
        
        resultados = []
        
        for symbol in self.activos:
            for tf_name, granularity in self.timeframes.items():
                contador += 1
                progreso = (contador / total) * 100
                
                print(f"[{progreso:.1f}%] {contador}/{total}: {symbol} ({tf_name})")
                
                # Verificar si ya existe
                conn = sqlite3.connect(str(self.db_path))
                c = conn.cursor()
                c.execute(
                    'SELECT * FROM descargas WHERE symbol = ? AND timeframe = ?',
                    (symbol, tf_name)
                )
                existe = c.fetchone()
                conn.close()
                
                if existe:
                    print(f"      ⏭️ Ya existe, saltando...")
                    continue
                
                # Descargar
                df = self.descargar_activo_timeframe(symbol, tf_name, granularity)
                
                if df is not None and len(df) > 1000:  # Mínimo 1000 velas
                    # Guardar
                    filename = f"{symbol}_{tf_name}.csv"
                    filepath = self.data_dir / filename
                    df.to_csv(filepath, index=False)
                    
                    # Registrar en BD
                    conn = sqlite3.connect(str(self.db_path))
                    c = conn.cursor()
                    c.execute('''
                        INSERT OR REPLACE INTO descargas 
                        (symbol, timeframe, inicio, fin, velas, archivo, estado)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        tf_name,
                        df['timestamp'].min(),
                        df['timestamp'].max(),
                        len(df),
                        str(filepath),
                        'completado'
                    ))
                    conn.commit()
                    conn.close()
                    
                    print(f"      ✅ {len(df):,} velas guardadas\n")
                    resultados.append((symbol, tf_name, len(df)))
                    
                else:
                    print(f"      ❌ Datos insuficientes\n")
        
        # Resumen final
        print("\n" + "="*60)
        print("✅ DESCARGA COMPLETADA")
        print("="*60)
        print(f"Archivos descargados: {len(resultados)}")
        for symbol, tf, count in resultados:
            print(f"   {symbol} ({tf}): {count:,} velas")
        
        # Guardar resumen
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO resumen 
            (total_activos, total_timeframes, total_archivos, ultima_actualizacion)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (len(self.activos), len(self.timeframes), len(resultados)))
        conn.commit()
        conn.close()
        
        return resultados

# ============================================================================
# DOWNLOAD TRACKER - API SIMPLE
# ============================================================================

def obtener_estado_descargas():
    """Obtener estado de las descargas."""
    db_path = Path("data_multi/download_tracker.db")
    
    if not db_path.exists():
        return {'status': 'no_iniciado'}
    
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    c.execute('SELECT * FROM descargas ORDER BY symbol, timeframe')
    descargas = c.fetchall()
    
    c.execute('SELECT * FROM resumen ORDER BY ultima_actualizacion DESC LIMIT 1')
    resumen = c.fetchone()
    
    conn.close()
    
    return {
        'total_descargados': len(descargas),
        'resumen': resumen,
        'descargas': [
            {'symbol': d[0], 'timeframe': d[1], 'velas': d[4], 'estado': d[6]}
            for d in descargas
        ]
    }

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    downloader = MultiTimeframeDownloader()
    downloader.descargar_todo()
